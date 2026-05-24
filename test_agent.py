# test_agent.py — CLI entry point for the research agent
#
# Usage:
#   python test_agent.py --question "What is the Model Context Protocol?"
#   python test_agent.py                    # uses default question
#
# Output: report printed to terminal + logged to data/logs/YYYY-MM-DD.log

import argparse
import asyncio
from src.eval.tracer import init_tracing
from src.agent.researcher import run_agent
from src.agent.logger import log_interaction
from src.agent.suggestions import get_suggestions

DEFAULT_QUESTION = "What is the Model Context Protocol and why was it introduced?"


def print_report(state):
    print("\n" + "=" * 60)
    print("RESEARCH AGENT REPORT")
    print("=" * 60)
    print(f"Question: {state.question}")
    print("-" * 60)

    if state.blocked:
        # out-of-scope or injection — show clean message + suggestions
        print("\nThis question was blocked.\n")

        # figure out why and tailor the message
        reason = state.block_reason or ""
        if "out_of_scope" in reason:
            print("This agent is built for research questions — topics like AI,")
            print("technology, science, geopolitics, current events, and factual")
            print("deep-dives. Simple lookups, trivia, and casual questions are")
            print("outside its scope.\n")
        elif "injection" in reason.lower() or "block" in reason.lower():
            print("This question was flagged as a potential prompt injection attempt.")
            print("If this was a legitimate question, try rephrasing it.\n")
        else:
            print(f"Reason: {reason}\n")

        # suggest research-style alternatives
        suggestions = get_suggestions(state.question)
        if suggestions:
            print("You could try asking:")
            for s in suggestions:
                print(f"  • {s}")
        print()

    else:
        print(state.report)
        if state.groundedness_score is not None:
            print(f"\n[Groundedness: {state.groundedness_score:.2f}]")

    print("=" * 60)


async def main(question: str):
    init_tracing()

    print(f"\nResearching: {question}")
    state = await run_agent(question)

    print_report(state)

    # log every interaction — blocked or not
    log_interaction(
        question=state.question,
        report=state.report or "",
        groundedness_score=state.groundedness_score,
        blocked=state.blocked,
        block_reason=state.block_reason,
        context=getattr(state, "context_text", "") or "",
        source="cli",
    )

    if state.error:
        print(f"\n[ERROR] {state.error}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Research Agent CLI")
    parser.add_argument(
        "--question", "-q",
        type=str,
        default=DEFAULT_QUESTION,
        help="The research question to answer",
    )
    args = parser.parse_args()
    asyncio.run(main(args.question))