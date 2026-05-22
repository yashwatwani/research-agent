import asyncio
from src.agent.researcher import run_agent
from src.eval.tracer import init_tracing

init_tracing()


async def main():
    question = "What companies have adopted MCP and why does it matter?"

    state = await run_agent(question)

    if state.error:
        print(f"\nError: {state.error}")
        return

    print(f"\n{'='*50}")
    print("FINAL REPORT")
    print(f"{'='*50}")
    print(state.report)
    print(f"\nSearch queries used: {state.search_queries}")
    print(f"Results retrieved: {len(state.search_results)}")
    print(f"Memory route: {state.retrieved_context.get('type')}")


if __name__ == "__main__":
    asyncio.run(main())