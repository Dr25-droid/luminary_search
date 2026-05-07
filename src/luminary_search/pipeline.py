"""Full end-to-end research pipeline.

Chains all three phases into a single LangGraph agent:
  1. assess_scope   — clarify or accept the user's request
  2. draft_mandate  — convert conversation to a research mandate
  3. conductor_subgraph — parallel web-probe agents gather evidence
  4. synthesize_report  — write the final comprehensive report

Author: Deepthi R
"""

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from luminary_search.clarifier import assess_scope, draft_mandate
from luminary_search.conductor import conductor_agent
from luminary_search.config import get_model
from luminary_search.schemas import BeaconState, InquiryInput
from luminary_search.templates import SYNTHESIS_PROMPT
from luminary_search.toolkit import current_date_str

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

author_model = get_model(max_tokens=32000)

# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------


async def synthesize_report(state: BeaconState) -> dict:
    """Synthesise all distilled probe findings into a final cited report."""
    notes = state.get("distilled_notes", [])
    findings = "\n\n".join(notes)
    prompt = SYNTHESIS_PROMPT.format(
        research_mandate=state.get("research_mandate", ""),
        findings=findings,
        date=current_date_str(),
    )
    response = await author_model.ainvoke([HumanMessage(content=prompt)])
    report = str(response.content)
    return {
        "synthesis_report": report,
        "messages": [HumanMessage(content=f"Research complete. Here is your report:\n\n{report}")],
    }


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

pipeline_builder = StateGraph(BeaconState, input=InquiryInput)
pipeline_builder.add_node("assess_scope", assess_scope)
pipeline_builder.add_node("draft_mandate", draft_mandate)
pipeline_builder.add_node("conductor_subgraph", conductor_agent)
pipeline_builder.add_node("synthesize_report", synthesize_report)

pipeline_builder.add_edge(START, "assess_scope")
pipeline_builder.add_edge("draft_mandate", "conductor_subgraph")
pipeline_builder.add_edge("conductor_subgraph", "synthesize_report")
pipeline_builder.add_edge("synthesize_report", END)

luminary_agent = pipeline_builder.compile()
