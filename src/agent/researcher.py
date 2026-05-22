import asyncio
from dataclasses import dataclass, field
from typing import Optional
from openai import OpenAI
from src.config import OPENAI_API_KEY, CHAT_MODEL
from src.mcp_servers.search_mcp import search_web
from src.memory.memory_manager import store_source, retrieve

client = OpenAI(api_key=OPENAI_API_KEY)


# AgentState — carries everything the agent knows through the graph
# skip_search flag set by check_memory_node to avoid unnecessary web calls
@dataclass
class AgentState:
    question: str
    search_queries: list[str] = field(default_factory=list)
    search_results: list[dict] = field(default_factory=list)
    retrieved_context: dict = field(default_factory=dict)
    skip_search: bool = False
    report: Optional[str] = None
    error: Optional[str] = None


# check_memory_node — retrieves from memory first before hitting the internet
# skips web search if similarity > 0.6 (vector) or > 2 graph results found
async def check_memory_node(state: AgentState) -> AgentState:
    print(f"\n[MEMORY CHECK] Checking existing knowledge...")

    result = retrieve(state.question, top_k=3)
    state.retrieved_context = result

    has_vector = (
        result["type"] == "vector" and
        len(result["results"]) > 0 and
        result["results"][0].get("similarity", 0) > 0.6
    )

    has_graph = (
        result["type"] == "graph" and
        len(result["results"]) > 2
    )

    if has_vector or has_graph:
        state.skip_search = True
        print(f"[MEMORY CHECK] Good context found in memory. Skipping web search.")
    else:
        state.skip_search = False
        print(f"[MEMORY CHECK] Not enough context. Will search the web.")

    return state


# plan_node — takes the question, generates 2-3 focused search queries
async def plan_node(state: AgentState) -> AgentState:
    print(f"\n[PLAN] Question: {state.question}")

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a research planner. Given a question, generate 2-3 focused search queries that together would answer it. Return only the queries, one per line, no numbering or bullets."
            },
            {
                "role": "user",
                "content": f"Question: {state.question}"
            }
        ],
        temperature=0
    )

    queries = [
        q.strip()
        for q in response.choices[0].message.content.strip().split("\n")
        if q.strip()
    ]

    state.search_queries = queries[:3]
    print(f"[PLAN] Generated {len(state.search_queries)} queries: {state.search_queries}")
    return state


# search_node — runs each query, stores results in vector + graph via memory_manager
async def search_node(state: AgentState) -> AgentState:
    print(f"\n[SEARCH] Running {len(state.search_queries)} queries...")
    all_results = []

    for query in state.search_queries:
        results = await search_web(query, num_results=3)
        print(f"[SEARCH] '{query}' → {len(results)} results")

        for r in results:
            if r.get("snippet"):
                store_source(
                    text=r["snippet"],
                    source_url=r.get("url", ""),
                    source_title=r.get("title", "")
                )
            all_results.append(r)

    state.search_results = all_results
    print(f"[SEARCH] Total results stored: {len(all_results)}")
    return state


# retrieve_node — queries memory for relevant context using the query router
async def retrieve_node(state: AgentState) -> AgentState:
    print(f"\n[RETRIEVE] Retrieving context for: {state.question}")

    result = retrieve(state.question, top_k=5)
    state.retrieved_context = result

    print(f"[RETRIEVE] Route: {result['type']} | Results: {len(result['results'])}")
    return state


# synthesise_node — combines question + context into a structured report
async def synthesise_node(state: AgentState) -> AgentState:
    print(f"\n[SYNTHESISE] Writing report...")

    context_text = ""

    if state.retrieved_context.get("type") == "vector":
        for r in state.retrieved_context.get("results", []):
            context_text += f"Source: {r.get('source_title', '')}\n"
            context_text += f"Content: {r.get('content', '')}\n\n"

    elif state.retrieved_context.get("type") == "graph":
        for r in state.retrieved_context.get("results", []):
            context_text += f"{r['subject']} → {r['relation']} → {r['object']}\n"

    if not context_text and state.search_results:
        for r in state.search_results[:5]:
            context_text += f"Source: {r.get('title', '')}\n"
            context_text += f"Content: {r.get('snippet', '')}\n\n"

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": """You are a research analyst. Write a clear, structured report answering the question.
Format:
## Summary
2-3 sentence direct answer.

## Key findings
Bullet points of the most important facts.

## Sources
List the sources used.

Be factual. Only use information from the provided context."""
            },
            {
                "role": "user",
                "content": f"Question: {state.question}\n\nContext:\n{context_text}"
            }
        ]
    )

    state.report = response.choices[0].message.content
    print("[SYNTHESISE] Report written.")
    return state


# run_agent — executes the full pipeline
# check memory → plan (if needed) → search (if needed) → retrieve → synthesise
async def run_agent(question: str) -> AgentState:
    print(f"\n{'='*50}")
    print(f"ResearchAgent starting")
    print(f"Question: {question}")
    print(f"{'='*50}")

    state = AgentState(question=question)

    try:
        state = await check_memory_node(state)

        if not state.skip_search:
            state = await plan_node(state)
            state = await search_node(state)
            state = await retrieve_node(state)

        state = await synthesise_node(state)

    except Exception as e:
        state.error = str(e)
        print(f"[ERROR] {e}")

    return state