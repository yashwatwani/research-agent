from src.memory.vector_store import setup_table, store_document, retrieve
from src.eval.tracer import init_tracing

init_tracing()

setup_table()

sample_text = """
Model Context Protocol (MCP) is an open standard developed by Anthropic that 
enables AI models to connect with external tools and data sources. MCP was 
donated to the Linux Foundation in December 2025. It has been adopted by 
OpenAI, Google, and Microsoft. The protocol defines a standard way for AI 
agents to discover and call tools through MCP servers. Before MCP, every 
framework had its own tool format. MCP solved this fragmentation problem by 
providing one universal interface. By early 2026 it had over 97 million 
monthly SDK downloads. Security remains an open challenge with MCP servers 
vulnerable to prompt injection attacks if not properly locked down.
"""

store_document(
    text=sample_text,
    source_url="https://example.com/mcp-overview",
    source_title="MCP Overview",
    metadata={"topic": "MCP", "year": 2026}
)

results = retrieve("who adopted MCP protocol", top_k=3)

print(f"\nTop {len(results)} chunks for query 'who adopted MCP protocol':\n")
for i, r in enumerate(results):
    print(f"Result {i+1} (similarity: {r['similarity']:.3f})")
    print(f"Source: {r['source_title']}")
    print(f"Content: {r['content'][:200]}")
    print()