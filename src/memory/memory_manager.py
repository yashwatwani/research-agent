# memory_manager.py — single entry point for storing anything the agent reads
# all other code calls this instead of vector_store or graph_store directly

from src.memory.vector_store import store_document as vector_store_document
from src.memory.graph_store import store_document_in_graph
from src.memory.retriever import retrieve as memory_retrieve


# store_source — chunks, embeds and stores in pgvector AND extracts
# entities and stores in NetworkX graph, from a single call
# Phase 7: both stores now do dedup independently
#   - vector_store: chunk-level (skips duplicate paragraphs even across URLs)
#   - graph_store: source-level (skips entity extraction for seen URLs)
def store_source(text: str, source_url: str = "", source_title: str = ""):
    print(f"\nStoring: {source_title or source_url}")

    # store in vector db — returns dedup stats
    vector_result = vector_store_document(
        text=text,
        source_url=source_url,
        source_title=source_title
    )

    # store in knowledge graph — returns [] if source was already ingested
    triples = store_document_in_graph(
        text=text,
        source_url=source_url,
        source_title=source_title
    )

    print(
        f"Done. Vector: {vector_result['chunks_inserted']} new, "
        f"{vector_result['chunks_skipped']} skipped. "
        f"Graph: {len(triples)} triples added."
    )

    # return both pieces so callers (e.g. tests, the agent loop) can inspect them
    return {
        "vector": vector_result,
        "triples": triples,
    }


# retrieve — unified retrieval, query router decides vector or graph
def retrieve(question: str, top_k: int = 5) -> dict:
    return memory_retrieve(question, top_k=top_k)