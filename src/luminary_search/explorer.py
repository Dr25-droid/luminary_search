"""Phase 2 — ReAct web-probe researcher agent.

Iteratively calls web_probe and reason_tool to gather evidence on a
focused topic, then distils all findings into a compressed, cited report.

Author: Deepthi R
"""

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, filter_messages
from langgraph.graph import END, START, StateGraph

from luminary_search.config import get_model
from luminary_search.schemas import ExplorerOutput, ExplorerState
from luminary_search.templates import DISTILL_HUMAN_PROMPT, DISTILL_SYSTEM_PROMPT, EXPLORER_SYSTEM_PROMPT
from luminary_search.toolkit import current_date_str, reason_tool, web_probe

# ---------------------------------------------------------------------------
# Models and tool registry
# ---------------------------------------------------------------------------

explorer_model = get_model()
distill_model = get_model(max_tokens=32000)

_tools = [web_probe, reason_tool]
tools_registry = {t.name: t for t in _tools}
explorer_model_with_tools = explorer_model.bind_tools(_tools)

# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def reason_step(state: ExplorerState) -> dict:
    """Invoke the explorer model; it decides whether to call a tool or conclude."""
    system = SystemMessage(content=EXPLORER_SYSTEM_PROMPT.format(date=current_date_str()))
    response = explorer_model_with_tools.invoke([system] + list(state["explorer_messages"]))
    return {"explorer_messages": [response]}


def execute_tools(state: ExplorerState) -> dict:
    """Execute every tool call emitted by the last explorer model response."""
    last_message = state["explorer_messages"][-1]
    tool_messages = []
    for tool_call in last_message.tool_calls:
        tool_fn = tools_registry[tool_call["name"]]
        observation = tool_fn.invoke(tool_call["args"])
        tool_messages.append(
            ToolMessage(
                content=observation,
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
        )
    return {"explorer_messages": tool_messages}


def distill_findings(state: ExplorerState) -> dict:
    """Compress the explorer's raw message history into a clean, cited findings document."""
    system = SystemMessage(content=DISTILL_SYSTEM_PROMPT.format(date=current_date_str()))
    human_reminder = HumanMessage(
        content=DISTILL_HUMAN_PROMPT.format(probe_topic=state.get("probe_topic", ""))
    )
    messages = [system] + list(state["explorer_messages"]) + [human_reminder]
    response = distill_model.invoke(messages)

    raw_msgs = filter_messages(state["explorer_messages"], include_types=["tool", "ai"])
    raw_text = "\n".join(
        m.content if isinstance(m.content, str) else str(m.content) for m in raw_msgs
    )

    return {
        "distilled_research": str(response.content),
        "raw_findings": [raw_text],
    }


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def _route_after_reason(state: ExplorerState) -> Literal["execute_tools", "distill_findings"]:
    last = state["explorer_messages"][-1]
    if getattr(last, "tool_calls", None):
        return "execute_tools"
    return "distill_findings"


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

explorer_builder = StateGraph(ExplorerState, output=ExplorerOutput)
explorer_builder.add_node("reason_step", reason_step)
explorer_builder.add_node("execute_tools", execute_tools)
explorer_builder.add_node("distill_findings", distill_findings)

explorer_builder.add_edge(START, "reason_step")
explorer_builder.add_conditional_edges("reason_step", _route_after_reason)
explorer_builder.add_edge("execute_tools", "reason_step")
explorer_builder.add_edge("distill_findings", END)

explorer_agent = explorer_builder.compile()
