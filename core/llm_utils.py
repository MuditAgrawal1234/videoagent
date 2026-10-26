"""
core/llm_utils.py
─────────────────
Shared LLM helpers for the AI Video Assistant.

LLM Priority:
  1. Groq (if GROQ_API_KEY is set) — free tier: 14,400 req/day, 30 RPM, very fast
  2. Mistral (if MISTRAL_API_KEY is set) — fallback

Provides:
  - get_llm()           : returns best available LLM instance
  - invoke_with_retry() : calls a chain with automatic retry on rate-limit errors
"""

import os
import time


def get_llm(temperature: float = 0.3):
    """
    Return the best available LLM instance.
    Prefers Groq (generous free tier) over Mistral (very restrictive free tier).
    """
    groq_key = os.getenv("GROQ_API_KEY")
    mistral_key = os.getenv("MISTRAL_API_KEY")

    if groq_key:
        # Groq: free tier, fast — use first available model
        from langchain_groq import ChatGroq
        # Models confirmed available on this account (checked via API)
        groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        print(f"  [LLM] Using Groq ({groq_model})")
        return ChatGroq(
            model=groq_model,
            groq_api_key=groq_key,
            temperature=temperature,
        )
    elif mistral_key:
        # Mistral: fallback (restrictive free tier)
        from langchain_mistralai import ChatMistralAI
        print("  [LLM] Using Mistral (mistral-small-latest)")
        return ChatMistralAI(
            model="mistral-small-latest",
            mistral_api_key=mistral_key,
            temperature=temperature,
        )
    else:
        raise RuntimeError(
            "No LLM API key found. Please set either GROQ_API_KEY or MISTRAL_API_KEY in your .env file.\n"
            "Get a FREE Groq API key at: https://console.groq.com"
        )


def invoke_with_retry(chain, input_data, max_retries: int = 5, base_delay: float = 20.0):
    """
    Invoke a LangChain chain and automatically retry on rate-limit (429) errors.

    Args:
        chain:        Any LangChain Runnable (prompt | llm | parser, etc.)
        input_data:   The input to pass to chain.invoke()
        max_retries:  Maximum number of retry attempts (default 5)
        base_delay:   Starting delay in seconds between retries (default 20s).
                      Each retry doubles the delay (exponential back-off).

    Returns:
        The string output from the chain.

    Raises:
        RuntimeError if all retries are exhausted.
    """
    last_exc = None
    delay = base_delay

    for attempt in range(1, max_retries + 1):
        try:
            return chain.invoke(input_data)
        except Exception as exc:
            error_str = str(exc)

            # Only retry on rate-limit (429) responses
            is_rate_limit = (
                "429" in error_str
                or "rate_limit" in error_str.lower()
                or "rate limit" in error_str.lower()
                or "too many requests" in error_str.lower()
            )

            if is_rate_limit:
                last_exc = exc
                if attempt < max_retries:
                    print(
                        f"  [LLM] Rate limit hit (attempt {attempt}/{max_retries}). "
                        f"Waiting {delay:.0f}s before retry..."
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, 120)  # cap at 2 minutes
                    continue
                else:
                    print(f"  [LLM] All {max_retries} retry attempts exhausted.")
                    raise RuntimeError(
                        "LLM API rate limit exceeded after multiple retries. "
                        "If using Mistral free tier, consider switching to Groq "
                        "(free at https://console.groq.com — 14,400 requests/day)."
                    ) from exc
            else:
                # Not a rate-limit error — raise immediately
                raise

    # Safety fallback (should not normally be reached)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("invoke_with_retry: exhausted all attempts with no result.")
