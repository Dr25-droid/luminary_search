"""luminary_search — AI-powered deep research agent system.

A three-phase pipeline that clarifies your research question,
dispatches parallel web-probe agents to gather evidence, and
synthesises all findings into a comprehensive cited report.

    from luminary_search import luminary_agent
    from langchain_core.messages import HumanMessage
    import asyncio

    result = asyncio.run(
        luminary_agent.ainvoke({"messages": [HumanMessage(content="...")]})
    )
    print(result["synthesis_report"])

Author: Deepthi R
"""

__author__ = "Deepthi R"
__version__ = "0.1.0"

from luminary_search.clarifier import scope_graph
from luminary_search.conductor import conductor_agent
from luminary_search.explorer import explorer_agent
from luminary_search.pipeline import luminary_agent

__all__ = [
    "scope_graph",
    "explorer_agent",
    "conductor_agent",
    "luminary_agent",
]
