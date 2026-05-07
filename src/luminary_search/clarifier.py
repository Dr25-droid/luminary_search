"""Phase 1 — Scope clarification graph.

Assesses whether the user's request is specific enough, optionally asks
one clarifying question, then drafts a detailed research mandate.

Author: Deepthi R
"""

from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, get_buffer_string
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from luminary_search.config import get_model
from luminary_search.schemas import BeaconState, InquiryInput, ResearchMandate, ScopeCheck
from luminary_search.templates import MANDATE_GENERATION_PROMPT, SCOPE_ASSESSMENT_PROMPT
from luminary_search.toolkit import current_date_str

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

scope_model = get_model(temperature=0.0)

# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def assess_scope(
    state: BeaconState,
) -> Command[Literal["draft_mandate", "__end__"]]:
    """Decide whether to ask a clarifying question or proceed to mandate drafting."""
    structured = scope_model.with_structured_output(ScopeCheck)
    prompt = SCOPE_ASSESSMENT_PROMPT.format(
        messages=get_buffer_string(state["messages"]),
        date=current_date_str(),
    )
    response: ScopeCheck = structured.invoke([HumanMessage(content=prompt)])

    if response.need_clarification:
        return Command(
            goto=END,
            update={"messages": [AIMessage(content=response.question)]},
        )
    return Command(
        goto="draft_mandate",
        update={"messages": [AIMessage(content=response.verification)]},
    )


def draft_mandate(state: BeaconState) -> dict:
    """Convert the conversation into a detailed research mandate."""
    structured = scope_model.with_structured_output(ResearchMandate)
    prompt = MANDATE_GENERATION_PROMPT.format(
        messages=get_buffer_string(state["messages"]),
        date=current_date_str(),
    )
    response: ResearchMandate = structured.invoke([HumanMessage(content=prompt)])

    return {
        "research_mandate": response.research_mandate,
        "conductor_messages": [HumanMessage(content=response.research_mandate + ".")],
    }


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

clarifier_builder = StateGraph(BeaconState, input=InquiryInput)
clarifier_builder.add_node("assess_scope", assess_scope)
clarifier_builder.add_node("draft_mandate", draft_mandate)
clarifier_builder.add_edge(START, "assess_scope")
clarifier_builder.add_edge("draft_mandate", END)

scope_graph = clarifier_builder.compile()
