import asyncio
from dataclasses import dataclass, field
from typing import Optional
from openai import OpenAI
from src.config import OPENAI_API_KEY, CHAT_MODEL
from src.mcp_servers.search_mcp import search_web
from src.memory.memory_manager import store_source, retrieve
from src.guardrails.input_filter import check_input
from src.guardrails.output_validator import check_output

client = OpenAI(api_key=OPENAI_API_KEY)


# AgentState — carries everything the agent knows through the graph
# skip_search flag set by check_memory_node to avoid unnecessary web calls
# Phase 7: blocked, block_reason, groundedness_score, context_text added
@dataclass
class AgentState:
    question: str
    search_queries: list[str] = field(default_factory=list)
    search_results: list[dict] = field(default_factory=list)
    retrieved_context: dict = field(default_factory=dict)
    skip_search: bool = False
    report: Optional[str] = None
    error: Optional[str] = None
    # Phase 7 — guardrail state
    blocked: bool = False
    block_reason: Optional[str] = None
    groundedness_score: Optional[float] = None
    context_text: str = ""  # populated by synthesise_node, read by output_validator_node


# input_filter_node — first gate. Two-stage check (regex + LLM classifier).
# If blocked, the agent loop short-circuits and returns without spending API calls.
async def input_filter_node(state: AgentState) -> AgentState:
    print(f"\n[INPUT FILTER] Validating question...")

    allowed, reason = check_input(state.question)
    if not allowed:
        state.blocked = True
        state.block_reason = reason
        state.report = f"Request blocked by input filter.\n\nReason: {reason}"
        print(f"[INPUT FILTER] BLOCKED — {reason}")
    else:
        print(f"[INPUT FILTER] Passed.")
    return state


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
# always pulls vector context as a baseline even when graph is the primary route
# Phase 7: stores assembled context_text on state for the output_validator to read
async def synthesise_node(state: AgentState) -> AgentState:
    print(f"\n[SYNTHESISE] Writing report...")
    print(f"[SYNTHESISE] Primary route: {state.retrieved_context.get('type')}")

    context_text = ""

    if state.retrieved_context.get("type") == "graph":
        graph_results = state.retrieved_context.get("results", [])
        if graph_results:
            context_text += "Relationships found:\n"
            for r in graph_results:
                context_text += f"  {r['subject']} → {r['relation']} → {r['object']}\n"
            context_text += "\n"

        from src.memory.vector_store import retrieve as vector_retrieve
        vector_results = vector_retrieve(state.question, top_k=3)
        if vector_results:
            print(f"[SYNTHESISE] Also pulling {len(vector_results)} vector chunks as background")
            context_text += "Background context:\n"
            for r in vector_results:
                context_text += f"  Source: {r.get('source_title', '')}\n"
                context_text += f"  Content: {r.get('content', '')}\n\n"

    elif state.retrieved_context.get("type") == "vector":
        vector_results = state.retrieved_context.get("results", [])
        print(f"[SYNTHESISE] Using {len(vector_results)} vector chunks")
        for r in vector_results:
            context_text += f"Source: {r.get('source_title', '')}\n"
            context_text += f"Content: {r.get('content', '')}\n\n"

    if not context_text and state.search_results:
        print(f"[SYNTHESISE] No memory context, falling back to search results")
        for r in state.search_results[:5]:
            context_text += f"Source: {r.get('title', '')}\n"
            context_text += f"Content: {r.get('snippet', '')}\n\n"

    # Phase 7: stash for the validator
    state.context_text = context_text

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": """You are a research analyst. Write a clear structured report answering the question.
Format:
## Summary
2-3 sentence direct answer.

## Key findings
Bullet points of the most important facts.

## Sources
List the sources used.

Be factual. Only use information from the provided context.
Never expand abbreviations unless the full form is explicitly stated in the context."""
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


# output_validator_node — LLM judge groundedness check
# scores 0.0-1.0, blocks if below threshold (default 0.5)
# blocked reports get replaced with a user-facing block message
async def output_validator_node(state: AgentState) -> AgentState:
    print(f"\n[OUTPUT VALIDATOR] Scoring groundedness...")

    is_grounded, score, reasoning = check_output(
        question=state.question,
        context=state.context_text,
        report=state.report or "",
    )

    state.groundedness_score = score

    if not is_grounded:
        state.blocked = True
        state.block_reason = f"groundedness {score:.2f} below threshold — {reasoning}"
        # keep the original report available on state but show user the block message
        original = state.report
        state.report = (
            f"Response blocked by output validator.\n\n"
            f"Groundedness score: {score:.2f}\n"
            f"Reason: {reasoning}\n\n"
            f"---\nOriginal draft (for debugging):\n{original}"
        )
        print(f"[OUTPUT VALIDATOR] BLOCKED — score={score:.2f}, {reasoning}")
    else:
        print(f"[OUTPUT VALIDATOR] Passed — score={score:.2f}")

    return state


# run_agent — executes the full pipeline
# input_filter → check memory → plan (if needed) → search (if needed) → retrieve → synthesise → output_validator
async def run_agent(question: str) -> AgentState:
    print(f"\n{'='*50}")
    print(f"ResearchAgent starting")
    print(f"Question: {question}")
    print(f"{'='*50}")

    state = AgentState(question=question)

    try:
        # Phase 7: input filter is the first gate
        state = await input_filter_node(state)
        if state.blocked:
            return state

        state = await check_memory_node(state)

        if not state.skip_search:
            state = await plan_node(state)
            state = await search_node(state)
            state = await retrieve_node(state)

        state = await synthesise_node(state)

        # Phase 7: output validator is the last gate
        state = await output_validator_node(state)

    except Exception as e:
        state.error = str(e)
        print(f"[ERROR] {e}")

    return state