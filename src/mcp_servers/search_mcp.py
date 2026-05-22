import json
from serpapi import GoogleSearch
from src.config import SERPAPI_KEY, MAX_SEARCH_RESULTS

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
    if tool_name == "search_web":
        results = await search_web(
            query=arguments["query"],
            num_results=arguments.get("num_results", MAX_SEARCH_RESULTS)
        )
        return json.dumps(results, indent=2)

    raise ValueError(f"Unknown tool: {tool_name}")