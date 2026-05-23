import asyncio
from src.agent.researcher import run_agent
from src.eval.tracer import init_tracing

init_tracing()


async def main():
    question = "What are the security vulnerabilities in MCP servers found in 2026?"

    state = await run_agent(question)

    if state.error:
        print(f"\nError: {state.error}")
        return

    print(f"\n{'='*50}")
    print("FINAL REPORT")
    print(f"{'='*50}")
    print(state.report)
    print(f"\nSearch queries used: {state.search_queries}")
    print(f"Web results fetched: {len(state.search_results)}")
    print(f"Primary memory route: {state.retrieved_context.get('type')}")
    print(f"Web search skipped: {state.skip_search}")


if __name__ == "__main__":
    asyncio.run(main())