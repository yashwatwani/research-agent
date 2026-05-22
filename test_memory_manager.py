from src.memory.memory_manager import store_source, retrieve
from src.eval.tracer import init_tracing
from visualize_graph import export_to_json

init_tracing()

# source 1 — MCP ecosystem
store_source(
    text="""
    Model Context Protocol (MCP) is an open standard developed by Anthropic.
    OpenAI adopted MCP in early 2026. Microsoft adopted MCP shortly after.
    Google integrated MCP into their ADK framework. LangChain supports MCP.
    MCP was donated to the Linux Foundation in December 2025.
    Anthropic also makes Claude, a large language model.
    """,
    source_url="https://example.com/mcp",
    source_title="MCP Ecosystem"
)

# source 2 — RAG landscape
store_source(
    text="""
    RAG stands for Retrieval Augmented Generation. It was popularized by Meta AI research.
    pgvector is a Postgres extension that enables vector similarity search.
    Pinecone is a dedicated vector database used for RAG applications.
    Weaviate is another vector database that supports hybrid search.
    LangChain provides RAG pipelines that connect to multiple vector stores.
    OpenAI embeddings are commonly used with pgvector for semantic search.
    """,
    source_url="https://example.com/rag",
    source_title="RAG Landscape"
)

print("\nRetrieving: 'who created RAG?'")
result = retrieve("who created RAG?")
print(f"Route: {result['type']}")
for r in result['results']:
    if result['type'] == 'graph':
        print(f"  {r['subject']} → {r['relation']} → {r['object']}")
    else:
        print(f"  [{r['similarity']:.3f}] {r['content'][:120]}")

print("\nRetrieving: 'what is pgvector?'")
result = retrieve("what is pgvector?")
print(f"Route: {result['type']}")
for r in result['results']:
    if result['type'] == 'graph':
        print(f"  {r['subject']} → {r['relation']} → {r['object']}")
    else:
        print(f"  [{r['similarity']:.3f}] {r['content'][:120]}")

print("\nExporting updated graph...")
export_to_json()