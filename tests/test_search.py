import asyncio
from src.mcp_servers.search_mcp import search_web

async def test():
    results = await search_web("MCP protocol AI agents 2026", num_results=3)

    if not results:
        print("No results returned. Serpapi may have blocked the request.")
        return

    for r in results:
        print(r["title"])
        print(r["url"])
        print(r["snippet"][:120])
        print()

if __name__ == "__main__":
    asyncio.run(test())