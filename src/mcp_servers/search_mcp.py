import json
from serpapi import GoogleSearch
from src.config import SERPAPI_KEY, MAX_SEARCH_RESULTS
from src.guardrails.tool_allowlist import check_tool

TOOL_DEFINITION = {
    "name": "search_web",
    "description": "Search the web for current information on a topic. Returns titles, URLs and snippets from the top results.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query"
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return. Defaults to 5.",
                "default": 5
            }
        },
        "required": ["query"]
    }
}


async def search_web(query: str, num_results: int = MAX_SEARCH_RESULTS) -> list[dict]:
    #  hits SerpApi with a query, returns titles, URLs and snippets
    params = {
        "q": query,
        "num": num_results,
        "api_key": SERPAPI_KEY
    }

    search = GoogleSearch(params)
    data = search.get_dict()

    results = []
    for item in data.get("organic_results", [])[:num_results]:
        results.append({
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "snippet": item.get("snippet", "")
        })

    return results


async def handle_tool_call(tool_name: str, arguments: dict) -> str:
    # MCP entry point, routes tool name to the right function
    # Phase 7: soft allow-list — log violations, return error string (don't raise)

    is_allowed, reason = check_tool(tool_name)
    if not is_allowed:
        # we *could* still execute here (true "soft" mode), but for unknown tools
        # we have nothing to execute — there's no dispatch path. Return error.
        return json.dumps({"error": reason})

    if tool_name == "search_web":
        results = await search_web(
            query=arguments["query"],
            num_results=arguments.get("num_results", MAX_SEARCH_RESULTS)
        )
        return json.dumps(results, indent=2)

    # safety net — if a tool is in the allow-list but has no dispatch case,
    # log as violation and return error (different from "unknown tool" above)
    return json.dumps({"error": f"tool '{tool_name}' is allow-listed but has no dispatcher"})