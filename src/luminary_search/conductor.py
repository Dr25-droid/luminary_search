"""Phase 3 — Async multi-agent conductor (supervisor).

The conductor analyses the research mandate, dispatches parallel explorer
sub-agents via AssignProbe, aggregates their distilled findings, and stops
when satisfied or when iteration limits are reached.

Author: Deepthi R
"""

import asyncio
from typing import Literal

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage, filter_messages
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from luminary_search.config import get_model
from luminary_search.explorer import explorer_agent
from luminary_search.schemas import AssignProbe, ConductorState, ProbesDone
from luminary_search.templates import CONDUCTOR_SYSTEM_PROMPT
from luminary_search.toolkit import current_date_str, reason_tool

# Jupyter / nest_asyncio compatibility guard
try:
    import nest_asyncio

    try:
        from IPython import get_ipython

        if get_ipython() is not None:
            nest_asyncio.apply()
    except ImportError:
        pass
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_CONDUCTOR_ITERATIONS = 6
MAX_PARALLEL_PROBES = 3

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

conductor_model = get_model()
conductor_tools = [AssignProbe, ProbesDone, reason_tool]
conductor_model_with_tools = conductor_model.bind_tools(conductor_tools)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def extract_probe_results(messages: list[BaseMessage]) -> list[str]:
    """Return the content of every ToolMessage in the conductor's history."""
    return [
        msg.content
        for msg in filter_messages(messages, include_types="tool")
        if isinstance(msg, ToolMessage)
    ]


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


async def conductor_step(
    state: ConductorState,
) -> Command[Literal["conductor_dispatch"]]:
    """Ask the conductor model what to do next."""
    conductor_messages = state.get("conductor_messages", [])
    system = SystemMessage(
        content=CONDUCTOR_SYSTEM_PROMPT.format(
            date=current_date_str(),
            max_concurrent_research_units=MAX_PARALLEL_PROBES,
            max_conductor_iterations=MAX_CONDUCTOR_ITERATIONS,
        )
    )
    response = await conductor_model_with_tools.ainvoke([system] + list(conductor_messages))
    return Command(
        goto="conductor_dispatch",
        update={
            "conductor_messages": [response],
            "conductor_iterations": state.get("conductor_iterations", 0) + 1,
        },
    )


async def conductor_dispatch(
    state: ConductorState,
) -> Command[Literal["conductor_step", "__end__"]]:
    """Execute the conductor's tool calls or stop if exit conditions are met."""
    conductor_messages = state.get("conductor_messages", [])
    conductor_iterations = state.get("conductor_iterations", 0)
    most_recent = conductor_messages[-1]

    tool_messages: list[ToolMessage] = []
    all_raw_findings: list[str] = []
    should_end = False

    # --- Exit conditions ---
    exceeded_iterations = conductor_iterations >= MAX_CONDUCTOR_ITERATIONS
    no_tool_calls = not getattr(most_recent, "tool_calls", None)
    probes_done = any(
        tc["name"] == ProbesDone.name for tc in (most_recent.tool_calls or [])
    )

    if exceeded_iterations or no_tool_calls or probes_done:
        should_end = True
    else:
        try:
            reason_calls = [
                tc for tc in most_recent.tool_calls if tc["name"] == reason_tool.name
            ]
            assign_calls = [
                tc for tc in most_recent.tool_calls if tc["name"] == AssignProbe.name
            ]

            # Handle reason_tool calls synchronously
            for tc in reason_calls:
                obs = reason_tool.invoke(tc["args"])
                tool_messages.append(
                    ToolMessage(content=obs, name=tc["name"], tool_call_id=tc["id"])
                )

            # Launch explorer sub-agents in parallel
            if assign_calls:
                coros = [
                    explorer_agent.ainvoke(
                        {
                            "explorer_messages": [HumanMessage(content=tc["args"]["probe_topic"])],
                            "probe_topic": tc["args"]["probe_topic"],
                        }
                    )
                    for tc in assign_calls
                ]
                probe_results = await asyncio.gather(*coros)

                for result, tc in zip(probe_results, assign_calls):
                    distilled = result.get("distilled_research", "No findings returned.")
                    tool_messages.append(
                        ToolMessage(content=distilled, name=tc["name"], tool_call_id=tc["id"])
                    )
                    raw = result.get("raw_findings", [])
                    all_raw_findings.append("\n".join(raw))

        except Exception as e:
            print(f"Conductor dispatch error: {e}")
            should_end = True

    if should_end:
        return Command(
            goto=END,
            update={
                "distilled_notes": extract_probe_results(conductor_messages),
                "research_mandate": state.get("research_mandate", ""),
            },
        )

    return Command(
        goto="conductor_step",
        update={
            "conductor_messages": tool_messages,
            "raw_findings": all_raw_findings,
        },
    )


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

conductor_builder = StateGraph(ConductorState)
conductor_builder.add_node("conductor_step", conductor_step)
conductor_builder.add_node("conductor_dispatch", conductor_dispatch)
conductor_builder.add_edge(START, "conductor_step")

conductor_agent = conductor_builder.compile()
