"""
core/analyzer.py
────────────────
Single-call transcript analyzer.

Combines title, summary, action items, key decisions, and open questions
into ONE Mistral API call instead of five separate calls.
This avoids rate-limit issues on the free tier.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.llm_utils import get_llm, invoke_with_retry


# ── Prompt that extracts EVERYTHING in one shot ────────────────────────────────
COMBINED_SYSTEM_PROMPT = """You are an expert meeting analyst and summarizer.
Analyze the transcript below and return ALL of the following sections.
Use EXACTLY these section headers (including the ## prefix):

## TITLE
A short professional meeting/video title (max 8 words). Return only the title text.

## SUMMARY
A concise professional summary in bullet points (use • for bullets).

## ACTION ITEMS
A numbered list of action items. For each include: task, owner, deadline (or "Not specified").
If none found, write: No action items found.

## KEY DECISIONS
A numbered list of key decisions made.
If none found, write: No key decisions found.

## OPEN QUESTIONS
A numbered list of unresolved questions or topics needing follow-up.
If none found, write: No open questions found.

Keep each section focused and concise."""


def _parse_sections(text: str) -> dict:
    """
    Parse the combined LLM response into individual sections.
    Returns a dict with keys: title, summary, action_items, key_decisions, open_questions
    """
    sections = {
        "title": "Untitled Meeting",
        "summary": "Summary not available.",
        "action_items": "No action items found.",
        "key_decisions": "No key decisions found.",
        "open_questions": "No open questions found.",
    }

    # Map section header → dict key
    header_map = {
        "## TITLE": "title",
        "## SUMMARY": "summary",
        "## ACTION ITEMS": "action_items",
        "## KEY DECISIONS": "key_decisions",
        "## OPEN QUESTIONS": "open_questions",
    }

    headers = list(header_map.keys())
    current_key = None
    current_lines = []

    for line in text.splitlines():
        stripped = line.strip()

        # Check if this line is a known section header
        matched_header = None
        for header in headers:
            if stripped.upper() == header.upper() or stripped.upper().startswith(header.upper()):
                matched_header = header
                break

        if matched_header:
            # Save previous section
            if current_key and current_lines:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = header_map[matched_header]
            current_lines = []
        elif current_key is not None:
            current_lines.append(line)

    # Save the last section
    if current_key and current_lines:
        sections[current_key] = "\n".join(current_lines).strip()

    # Clean up title (remove surrounding quotes if any)
    sections["title"] = sections["title"].strip().strip('"').strip("'")
    if not sections["title"]:
        sections["title"] = "Untitled Meeting"

    return sections


def _truncate_for_api(transcript: str, max_chars: int = 8000) -> str:
    """
    Truncate transcript to fit within Mistral free-tier token limits.
    Keeps the beginning and end of the transcript for context.
    """
    if len(transcript) <= max_chars:
        return transcript

    half = max_chars // 2
    beginning = transcript[:half]
    ending = transcript[-half:]
    return (
        beginning
        + "\n\n[... transcript truncated for length ...]\n\n"
        + ending
    )


def analyze_transcript(transcript: str) -> dict:
    """
    Run the complete analysis on a transcript in a SINGLE Mistral API call.

    Returns a dict with keys:
        title, summary, action_items, key_decisions, open_questions

    This replaces the 5 separate calls previously made by:
        generate_title() + summarize() + extract_action_items()
        + extract_key_decisions() + extract_questions()
    """
    llm = get_llm(temperature=0.3)

    prompt = ChatPromptTemplate.from_messages([
        ("system", COMBINED_SYSTEM_PROMPT),
        ("human", "Transcript:\n\n{transcript}"),
    ])

    chain = (
        RunnablePassthrough()
        | RunnableLambda(lambda x: {"transcript": x})
        | prompt
        | llm
        | StrOutputParser()
    )

    # Truncate to avoid hitting token limits on free tier
    truncated = _truncate_for_api(transcript, max_chars=8000)
    print(f"  [Analyzer] Transcript length: {len(transcript):,} chars "
          f"(sending {len(truncated):,} chars to Mistral)")
    print("  [Analyzer] Running single combined analysis call ...")

    raw_response = invoke_with_retry(chain, truncated)

    print("  [Analyzer] Parsing response sections ...")
    result = _parse_sections(raw_response)

    print(f"  [Analyzer] Title    : {result['title']}")
    print(f"  [Analyzer] Summary  : {len(result['summary'])} chars")
    print(f"  [Analyzer] Actions  : {len(result['action_items'])} chars")
    print(f"  [Analyzer] Decisions: {len(result['key_decisions'])} chars")
    print(f"  [Analyzer] Questions: {len(result['open_questions'])} chars")

    return result
