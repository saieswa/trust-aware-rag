"""
Shared LLM Client — Groq Cloud.

Every LLM call in this project (query decomposition, contradiction
detection, evidence labeling, answer synthesis, sentence verification)
gets its client from this one function, rather than each of the five
call sites duplicating the same instantiation logic.

Groq Cloud's API is deliberately OpenAI-compatible — same request/response
shape, same authentication style — so this reuses `langchain_openai`'s
`ChatOpenAI` class pointed at Groq's `base_url` instead of needing a
separate LangChain integration package (`langchain-groq`). This is the
entire reason switching providers here was a small, contained change
rather than a rewrite: nothing about `.with_structured_output()`, message
formatting, or error handling differs from how the code was written for
OpenAI.
"""

from __future__ import annotations

from app.core.config import get_settings


def get_groq_llm(temperature: float = 0.0, timeout: int = 20):
    """
    Returns a configured ChatOpenAI instance pointed at Groq Cloud.

    Raises RuntimeError if no API key is configured — every call site
    catches this (along with any other failure — timeouts, rate limits,
    malformed responses) and falls back to its documented heuristic path,
    exactly like every other LLM call in this project.
    """
    settings = get_settings()
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        base_url=settings.GROQ_BASE_URL,
        temperature=temperature,
        timeout=timeout,
    )
