"""Entry point — run luminary_search from the command line.

Usage:
    python main.py

Author: Deepthi R
"""

import asyncio

from langchain_core.messages import HumanMessage

from luminary_search import luminary_agent


async def main() -> None:
    print("\n=== luminary_search — Deep Research Agent ===")
    print("By Deepthi R\n")
    print("Type your research question and press Enter.")
    print("(Ctrl+C to exit)\n")

    question = input("Your question: ").strip()
    if not question:
        print("No question provided. Exiting.")
        return

    print("\nResearching... this may take a minute.\n")

    result = await luminary_agent.ainvoke(
        {"messages": [HumanMessage(content=question)]},
        config={"configurable": {"thread_id": "cli-session", "recursion_limit": 50}},
    )

    # If the agent asked a clarifying question, show it and continue
    messages = result.get("messages", [])
    if messages and not result.get("synthesis_report"):
        clarification = messages[-1].content
        print(f"Clarification needed:\n{clarification}\n")
        answer = input("Your answer: ").strip()

        result = await luminary_agent.ainvoke(
            {"messages": [HumanMessage(content=question), HumanMessage(content=answer)]},
            config={"configurable": {"thread_id": "cli-session-2", "recursion_limit": 50}},
        )

    report = result.get("synthesis_report", "")
    if report:
        print("\n" + "=" * 60)
        print(report)
        print("=" * 60)
    else:
        print("No report generated.")


if __name__ == "__main__":
    asyncio.run(main())
