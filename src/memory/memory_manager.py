# memory_manager.py — single entry point for storing anything the agent reads
# all other code calls this instead of vector_store or graph_store directly

from src.memory.vector_store import store_document as vector_store_document
from src.memory.graph_store import store_document_in_graph
from src.memory.retriever import retrieve as memory_retrieve


# store_source — chunks, embeds and stores in pgvector AND extracts
# entities and stores in NetworkX graph, from a single call
def store_source(text: str, source_url: str = "", source_title: str = ""):
    print(f"\nStoring: {source_title or source_url}")

    # store in vector db
    vector_store_document(
        text=text,
        source_url=source_url,
        source_title=source_title
    )

    # store in knowledge graph
    triples = store_document_in_graph(
        text=text,
        source_url=source_url,
        source_title=source_title
    )

    print(f"Done. Chunks stored in pgvector. {len(triples)} triples added to graph.")
    return triples


# retrieve — unified retrieval, query router decides vector or graph
def retrieve(question: str, top_k: int = 5) -> dict:
    return memory_retrieve(question, top_k=top_k)