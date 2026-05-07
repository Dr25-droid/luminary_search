"""State definitions and structured-output schemas for luminary_search.

All TypedDict graph states and Pydantic models live here so that
the rest of the package can import them without circular dependencies.

Author: Deepthi R
"""

import operator
from typing import Annotated, List, Optional, Sequence

from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Graph states
# ---------------------------------------------------------------------------


class InquiryInput(MessagesState):
    """Input-only state — carries the user's opening messages into the pipeline."""


class BeaconState(MessagesState):
    """Top-level state that flows through the full end-to-end pipeline."""

    research_mandate: Optional[str]
    conductor_messages: Annotated[Sequence[BaseMessage], add_messages]
    raw_findings: Annotated[list[str], operator.add]
    distilled_notes: Annotated[list[str], operator.add]
    synthesis_report: str


class ExplorerState(dict):
    """State for a single web-probe (researcher) sub-agent."""

    explorer_messages: Annotated[Sequence[BaseMessage], add_messages]
    probe_iterations: int
    probe_topic: str
    distilled_research: str
    raw_findings: Annotated[List[str], operator.add]


class ExplorerOutput(dict):
    """Output returned by the explorer sub-agent to its caller."""

    distilled_research: str
    raw_findings: Annotated[List[str], operator.add]
    explorer_messages: Annotated[Sequence[BaseMessage], add_messages]


class ConductorState(dict):
    """State for the conductor (supervisor) agent that orchestrates probes."""

    conductor_messages: Annotated[Sequence[BaseMessage], add_messages]
    research_mandate: str
    distilled_notes: Annotated[list[str], operator.add]
    conductor_iterations: int
    raw_findings: Annotated[List[str], operator.add]


# ---------------------------------------------------------------------------
# Pydantic structured-output schemas
# ---------------------------------------------------------------------------


class ScopeCheck(BaseModel):
    """Decision returned by the scope-assessment step."""

    need_clarification: bool
    question: str
    verification: str


class ResearchMandate(BaseModel):
    """Detailed research mandate generated from the conversation."""

    research_mandate: str


class PageDigest(BaseModel):
    """Condensed summary of a single web page."""

    summary: str
    key_excerpts: str


# ---------------------------------------------------------------------------
# Tool schemas used by the conductor
# ---------------------------------------------------------------------------


@tool
class AssignProbe(BaseModel):
    """Delegate a focused research task to a dedicated explorer sub-agent."""

    probe_topic: str = Field(
        ...,
        description=(
            "Complete, standalone description of the research topic for this probe. "
            "Write at least one full paragraph. Do not use acronyms. "
            "The explorer agent has no visibility into other probes."
        ),
    )


@tool
class ProbesDone(BaseModel):
    """Signal that the conductor is satisfied with the gathered evidence."""
