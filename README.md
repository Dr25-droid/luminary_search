# luminary_search

An AI-powered deep research agent that clarifies your question, deploys parallel web-probe
agents to gather evidence, and synthesises everything into a comprehensive cited report —
all in one call.

**Author: Deepthi R**

---

## How It Works

```
User message
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 1 — SCOPE                                            │
│  Assess whether the request is clear enough.                │
│  Ask one clarifying question if needed, then draft a        │
│  detailed research mandate from the conversation.           │
└──────────────────────────┬──────────────────────────────────┘
                           │  research mandate
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 2 — EXPLORE  (runs in parallel)                      │
│  The conductor breaks the mandate into sub-topics and        │
│  dispatches up to 3 explorer agents simultaneously.          │
│  Each explorer runs a ReAct loop:                           │
│    web_probe → reason → web_probe → … → distil findings     │
└──────────────────────────┬──────────────────────────────────┘
                           │  distilled findings from all probes
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 3 — SYNTHESISE                                       │
│  Merge all findings into a structured markdown report        │
│  with inline citations and a full sources section.          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                    Final Report
```

---

## Use Cases

Each example below is a prompt you can paste directly.

| Use case | Example prompt |
|---|---|
| **Market research** | `"Compare the top 5 electric vehicle manufacturers by sales volume, range, and pricing in 2025"` |
| **Academic background** | `"Summarise the current state of research on GLP-1 drugs for obesity treatment"` |
| **Competitive analysis** | `"How does Netflix's content strategy compare to Disney+ and Apple TV+ in 2025?"` |
| **Travel planning** | `"Plan a 10-day trip to Japan in April — best cities, must-see spots, and practical tips"` |
| **Health & nutrition** | `"What does current science say about the long-term effects of intermittent fasting?"` |
| **Investment research** | `"What are the key risks and opportunities for investing in renewable energy infrastructure in 2025?"` |

---

## Setup

### 1. Install

```bash
cd luminary_search
pip install -e .
```

### 2. Set up your API keys

Copy the example env file and fill in your keys:

```bash
cp .env.example .env       # Mac/Linux
copy .env.example .env     # Windows
```

Open `.env` — it looks like this:

```
# Copy this file to .env and fill in your API keys

# Required for web search
TAVILY_API_KEY=tvly-...

# --- Choose ONE provider and set its key ---

# OpenAI  (default model: openai:gpt-4.1)
OPENAI_API_KEY=sk-...

# Anthropic  (to use: set DEFAULT_MODEL in config.py)
ANTHROPIC_API_KEY=sk-ant-...

# Google  (to use: set DEFAULT_MODEL in config.py)
GOOGLE_API_KEY=...
```

Fill in `TAVILY_API_KEY` and the key for whichever model provider you choose.
Keys are loaded automatically at startup — no `export` commands needed.
`.env` is git-ignored so your keys stay private.

### 3. Change the model (optional)

Open `src/luminary_search/config.py` and change one line:

```python
# Change this one line to switch the model for the whole pipeline
DEFAULT_MODEL = "openai:gpt-4.1"   # ← edit this
```

Available options:

| Model string | Provider key needed |
|---|---|
| `openai:gpt-4.1` *(default)* | `OPENAI_API_KEY` |
| `openai:gpt-4o` | `OPENAI_API_KEY` |
| `openai:gpt-4.1-mini` | `OPENAI_API_KEY` |
| `anthropic:claude-sonnet-4-20250514` | `ANTHROPIC_API_KEY` |
| `anthropic:claude-opus-4-20250514` | `ANTHROPIC_API_KEY` |
| `google_genai:gemini-2.0-flash` | `GOOGLE_API_KEY` |

---

## Running from the Command Line

The fastest way to use luminary_search is `main.py` — it takes your question interactively and prints the full report.

```bash
cd luminary_search
python main.py
```

Example session:

```
=== luminary_search — Deep Research Agent ===
Type your research question and press Enter.
(Ctrl+C to exit)

Your question: Plan a 10-day trip to Japan in April

Researching... this may take a minute.

============================================================
# 10-Day Japan Itinerary — April

## Overview
...
[full cited report printed here]
============================================================
```

If your question is ambiguous the agent will ask one clarifying question before starting research. Answer it and the full run continues automatically.

---

## Quick Start (Python API)

```python
import asyncio
from langchain_core.messages import HumanMessage
from luminary_search import luminary_agent

async def main():
    result = await luminary_agent.ainvoke(
        {"messages": [HumanMessage(content="Compare Netflix, Disney+, and Apple TV+ content strategies")]},
        config={"configurable": {"thread_id": "run-1", "recursion_limit": 50}},
    )
    print(result["synthesis_report"])

asyncio.run(main())
```

You can also use individual components:

```python
from luminary_search import scope_graph, explorer_agent, conductor_agent

# Just clarify + mandate
result = scope_graph.invoke({"messages": [HumanMessage(content="...")]})

# Just one research probe
result = asyncio.run(explorer_agent.ainvoke({
    "explorer_messages": [HumanMessage(content="What is retrieval-augmented generation?")],
    "probe_topic": "What is retrieval-augmented generation?",
}))
print(result["distilled_research"])
```

---

## Package Structure

| File | Purpose |
|---|---|
| `main.py` | CLI entry point — prompts for a question and prints the report |
| `config.py` | **Single place to change the model** — edit `DEFAULT_MODEL` here |
| `schemas.py` | All state classes (`BeaconState`, `ExplorerState`, …) and Pydantic schemas |
| `templates.py` | All prompt string constants — no logic |
| `toolkit.py` | Tavily search helpers + `web_probe` and `reason_tool` tools |
| `clarifier.py` | Phase 1 graph — scope assessment and mandate drafting |
| `explorer.py` | Phase 2 graph — ReAct web-probe loop with finding distillation |
| `conductor.py` | Phase 3 graph — async supervisor dispatching parallel probes |
| `pipeline.py` | Full end-to-end graph — entry point for most users |

---

## Model

All pipeline stages — scope assessment, web-probe explorer, conductor, distillation,
and report synthesis — use a single model configured in `src/luminary_search/config.py`.

Default: `openai:gpt-4.1`

To switch, edit one line in `config.py` and set the matching API key in `.env`.

---

*luminary_search — built by Deepthi R*
