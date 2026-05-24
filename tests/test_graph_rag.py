from src.memory.graph_store import store_document_in_graph, get_graph_stats
from src.memory.retriever import retrieve
from src.eval.tracer import init_tracing

init_tracing()

sample_text = """
Model Context Protocol (MCP) is an open standard developed by Anthropic.
MCP was donated to the Linux Foundation in December 2025.
OpenAI adopted MCP in early 2026. Microsoft adopted MCP shortly after.
Google adopted MCP and integrated it into their ADK framework.
Anthropic also makes Claude, which is a large language model.
pgvector is a Postgres extension created by the pgvector team.
LangChain integrated MCP into their tooling in 2025.
"""

print("Storing in graph...")
triples = store_document_in_graph(
    text=sample_text,
    source_url="https://example.com/mcp",
    source_title="MCP Overview"
)

print(f"\nExtracted {len(triples)} triples:")
for t in triples:
    print(f"  {t['subject']} → {t['relation']} → {t['object']}")

print("\nGraph stats:")
stats = get_graph_stats()
print(f"  Nodes: {stats['nodes']}")
print(f"  Edges: {stats['edges']}")
print(f"  Entities: {stats['entities']}")

print("\nQuery 1 (should go to graph): 'who adopted MCP?'")
result = retrieve("who adopted MCP?")
print(f"  Route: {result['type']}")
for r in result['results']:
    print(f"  {r['subject']} → {r['relation']} → {r['object']}")

print("\nQuery 2 (should go to vector): 'what is MCP?'")
result = retrieve("what is MCP?")
print(f"  Route: {result['type']}")
for r in result['results']:
    print(f"  Similarity: {r['similarity']:.3f} | {r['content'][:100]}")