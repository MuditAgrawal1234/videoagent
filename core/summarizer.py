from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
import time

from core.llm_utils import get_llm, invoke_with_retry


def split_transcript(transcript: str) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,
        chunk_overlap=200,
    )
    return splitter.split_text(transcript)


def summarize(transcript: str) -> str:
    llm = get_llm(temperature=0.3)

    map_prompt = ChatPromptTemplate.from_messages([
        ("system", "Summarize this portion of a meeting transcript concisely."),
        ("human", "{text}"),
    ])
    map_chain = map_prompt | llm | StrOutputParser()

    chunks = split_transcript(transcript)

    # Summarize each chunk with retry, adding a small pause between calls
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        print(f"  [Summarizer] Summarizing chunk {i + 1}/{len(chunks)} ...")
        summary = invoke_with_retry(map_chain, {"text": chunk})
        chunk_summaries.append(summary)
        if i < len(chunks) - 1:
            time.sleep(3)  # small pause between chunks to avoid burst rate-limit

    combined = "\n\n".join(chunk_summaries)

    combined_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an expert meeting summarizer. Combine these partial summaries "
            "into one final professional meeting summary in bullet points.",
        ),
        ("human", "{text}"),
    ])
    combined_chain = (
        RunnablePassthrough()
        | RunnableLambda(lambda x: {"text": x})
        | combined_prompt
        | llm
        | StrOutputParser()
    )

    print("  [Summarizer] Combining chunk summaries ...")
    return invoke_with_retry(combined_chain, combined)


def generate_title(transcript: str) -> str:
    llm = get_llm(temperature=0.3)

    title_chain = (
        RunnablePassthrough()
        | RunnableLambda(lambda x: {"text": x})
        | ChatPromptTemplate.from_messages([
            (
                "system",
                "Based on the meeting transcript, generate a short professional meeting title "
                "(max 8 words). Only return the title, nothing else.",
            ),
            ("human", "{text}"),
        ])
        | llm
        | StrOutputParser()
    )

    print("  [Title] Generating title ...")
    return invoke_with_retry(title_chain, transcript[:2000])
