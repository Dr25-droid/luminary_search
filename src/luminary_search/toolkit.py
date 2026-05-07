"""Shared utilities, search helpers, and LangChain tools.

This module provides:
- Date and path utilities
- Tavily-based web search helpers
- The web_probe and reason_tool LangChain tools

Author: Deepthi R
"""

from datetime import datetime
from pathlib import Path
from typing import Annotated, List, Literal

from langchain_core.messages import HumanMessage
from langchain_core.tools import InjectedToolArg, tool
from tavily import TavilyClient

from luminary_search.config import get_model
from luminary_search.schemas import PageDigest
from luminary_search.templates import PAGE_DIGEST_PROMPT

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def current_date_str() -> str:
    """Return the current date as a human-readable string."""
    return datetime.now().strftime("%B %d, %Y")


def package_dir() -> Path:
    """Return the directory containing this package."""
    return Path(__file__).parent


# ---------------------------------------------------------------------------
# Model + client initialisation
# ---------------------------------------------------------------------------

digest_model = get_model()
tavily_client = TavilyClient()

# ---------------------------------------------------------------------------
# Internal search helpers (used by web_probe)
# ---------------------------------------------------------------------------


def _run_web_probes(
    queries: List[str],
    max_results: int = 3,
    topic: str = "general",
) -> List[dict]:
    """Execute one Tavily search per query and collect raw results."""
    all_results: List[dict] = []
    for query in queries:
        response = tavily_client.search(
            query=query,
            max_results=max_results,
            topic=topic,
            include_raw_content=True,
        )
        all_results.extend(response.get("results", []))
    return all_results


def _digest_page_content(webpage_content: str) -> str:
    """Summarise a single page using the digest model.

    Falls back to a plain truncation if the model call fails.
    """
    try:
        structured = digest_model.with_structured_output(PageDigest)
        prompt = PAGE_DIGEST_PROMPT.format(
            webpage_content=webpage_content[:8000],
            date=current_date_str(),
        )
        result: PageDigest = structured.invoke([HumanMessage(content=prompt)])
        return f"<summary>{result.summary}</summary>\n<key_excerpts>{result.key_excerpts}</key_excerpts>"
    except Exception:
        return webpage_content[:2000]


def _dedup_probe_results(results: List[dict]) -> dict:
    """Deduplicate search results by URL, keeping the first occurrence."""
    seen: dict[str, dict] = {}
    for item in results:
        url = item.get("url", "")
        if url and url not in seen:
            seen[url] = item
    return seen


def _enrich_probe_results(unique_results: dict) -> dict:
    """Summarise the raw page content for each unique result."""
    enriched: dict[str, dict] = {}
    for url, item in unique_results.items():
        raw = item.get("raw_content") or item.get("content", "")
        enriched[url] = {**item, "processed_content": _digest_page_content(raw) if raw else ""}
    return enriched


def _render_probe_output(enriched_results: dict) -> str:
    """Format enriched results into a readable block for the explorer LLM."""
    lines: List[str] = []
    for idx, (url, item) in enumerate(enriched_results.items(), start=1):
        title = item.get("title", "Untitled")
        content = item.get("processed_content") or item.get("content", "")
        lines.append(f"--- SOURCE {idx}: {title} ---")
        lines.append(f"URL: {url}")
        lines.append(f"SUMMARY:\n{content}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LangChain tools exposed to the explorer agent
# ---------------------------------------------------------------------------


@tool(parse_docstring=True)
def web_probe(
    query: str,
    max_results: Annotated[int, InjectedToolArg] = 3,
    topic: Annotated[Literal["general", "news", "finance"], InjectedToolArg] = "general",
) -> str:
    """Search the web for information on a specific query.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return.
        topic: Search domain — general, news, or finance.

    Returns:
        Formatted string of source titles, URLs, and summarised content.
    """
    raw = _run_web_probes([query], max_results=max_results, topic=topic)
    unique = _dedup_probe_results(raw)
    enriched = _enrich_probe_results(unique)
    return _render_probe_output(enriched)


@tool(parse_docstring=True)
def reason_tool(reflection: str) -> str:
    """Record a strategic reflection to pause and plan the next research step.

    Args:
        reflection: Your analysis of what you found and what to do next.

    Returns:
        Confirmation that the reflection was recorded.
    """
    return f"Reflection recorded: {reflection}"
