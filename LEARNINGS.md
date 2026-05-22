# Learnings & Concepts

A living document. Updated every phase.
For every "wait, why did that happen?" moment and every tool we use.

---

## Components we are using

### OpenAI API
**What it does:** Powers two things in this project. gpt-4o handles all reasoning — planning, synthesising, writing reports. text-embedding-3-small converts text into vectors for semantic search.
**Why we chose it:** Key was available. The swap to another provider is one line in config.py — that's the point of keeping the model layer clean.
**Key config:** `CHAT_MODEL = "gpt-4o"`, `EMBEDDING_MODEL = "text-embedding-3-small"`, `EMBEDDING_DIMS = 1536`

---

### SerpApi
**What it does:** Web search. The agent sends a query, SerpApi hits Google and returns structured results — titles, URLs, snippets.
**Why we chose it:** DuckDuckGo blocked scraping. Brave Search has no free tier. SerpApi gives 100 free searches/month, no card needed.
**Where it lives:** `src/mcp_servers/search_mcp.py`

---

### MCP (Model Context Protocol)
**What it does:** A standard interface for defining and calling tools. The agent calls tools through MCP servers without knowing how they work internally.
**Why it matters:** Before MCP every framework had its own tool format. MCP is the USB connector for AI tools — build once, use with any agent.
**Where it lives:** `src/mcp_servers/` — each file is one MCP server exposing one or more tools.
**Key concept:** `TOOL_DEFINITION` describes the tool. `handle_tool_call` executes it. The agent only sees the definition.

---

### PostgreSQL 17 + pgvector
**What it does:** Stores text chunks and their vector embeddings. Powers semantic search via cosine similarity.
**Why we chose it:** pgvector turns Postgres into a vector database. No new infrastructure — it's just Postgres with an extension. Add a dedicated vector DB only when pgvector's performance limits become real.
**Key operator:** `<=>` computes cosine distance between two vectors directly in SQL.
**Where it lives:** `src/memory/vector_store.py`

---

### Arize Phoenix
**What it does:** Observability for LLM calls. Every call to gpt-4o gets traced — input, output, token count, latency. Visible in a local UI at localhost:6006.
**Why we chose it:** Self-hosted, open source, no vendor lock-in. Works by monkey-patching the OpenAI SDK so every call is automatically traced without changing any other code.
**How to start it:** Always run Phoenix in a separate terminal tab before running anything else.
**Where it lives:** `src/eval/tracer.py`

---

### NetworkX (coming in Phase 5)
**What it does:** In-memory knowledge graph. Stores entities and relationships extracted from sources. Powers Graph RAG.
**Why we start here:** Learn the concept on a simple in-memory graph before migrating to Neo4j. NetworkX is pure Python — no setup, no server.
**When we migrate:** When the graph needs to persist properly across sessions or gets too large for memory.

---

### Google ADK (coming in Phase 6)
**What it does:** Orchestration framework. Wires all layers into a state graph — plan → search → retrieve → synthesise.
**Why we chose it:** Already used in InsightsMix. State graph model maps cleanly to an agent loop.

---

## Doubts & explanations

### Why did retrieval return 0 results even though storage worked?
**Phase:** 4 — RAG
**What happened:** We created an ivfflat index on the chunks table at the same time as the table itself. ivfflat is an approximate nearest neighbour index — it works by dividing all vectors into clusters and only searching within the nearest cluster. The problem is it needs a minimum amount of data to build those clusters. We had 1 row. With no clusters to search, retrieval returned nothing.
**Fix:** Dropped the index. Plain cosine scan works fine with small data. ivfflat comes back when we have thousands of rows and full scans get slow.
**Lesson:** Don't add performance optimisations before you have the data to justify them.

---

### Why did pgvector fail to install even though brew installed it?
**Phase:** 4 — RAG setup
**What happened:** pgvector brew package ships compiled versions for Postgres 17 and 18 only. We were running Postgres 16. The `.dylib` file (compiled plugin) is built against a specific Postgres version's internal APIs — you can't load a Postgres 17 plugin into Postgres 16.
**Fix:** Upgraded to Postgres 17, then manually copied three files from pgvector's brew directory into Postgres 17's extension directory — `vector.dylib` (the compiled plugin), `vector.control` (metadata), and `vector--*.sql` files (the SQL that defines vector types and operators).
**Lesson:** Postgres extensions are version-specific compiled code, not generic plugins.

---

### Why does Phoenix throw port 4317 errors but still work?
**Phase:** 3 — tracing
**What happened:** Phoenix needs two ports — 6006 for the UI and 4317 for the gRPC trace receiver. When you run a second script while Phoenix is already running in another tab, the second instance tries to start its own Phoenix server and fails to grab port 4317 because the first instance already has it.
**Fix:** Always start Phoenix once in a dedicated terminal tab and leave it running. All other scripts send traces to the already-running instance. The errors are the second instance failing to start — the traces still go through fine.
**Lesson:** Phoenix is a server, not a library. Run it like one.

---

### Why did DuckDuckGo return no results?
**Phase:** 2 — search MCP server
**What happened:** DuckDuckGo blocks automated requests. Both their HTML endpoint and JSON API returned empty results when called from a script.
**Fix:** Switched to SerpApi.
**Lesson:** Free search APIs that work in a browser often block non-browser clients. Always test with a real HTTP client before building on top of them.

---

### What is the embedding vector actually storing?
**Phase:** 4 — RAG
**What it is:** A list of 1536 floats like `[-0.007, 0.011, 0.045, ...]`. Each number means nothing individually. The pattern across all 1536 numbers together encodes the semantic meaning of the text in a high-dimensional space.
**How search works:** When you query "who adopted MCP?", OpenAI converts that to its own 1536-number vector. pgvector computes the cosine distance between your query vector and every stored chunk vector. Chunks whose vectors point in a similar direction get returned as relevant — even if they use completely different words.
**Why 1536 dims:** That is the output size of text-embedding-3-small. Larger = more expressive but slower and more storage. 1536 is a good balance for most use cases.

---

## Reminder
Every time something breaks or a new concept comes up — add it here.
Every time a new tool gets added to the stack — add it to Components.

### Why did retrieval return duplicate results?
**Phase:** 4 — RAG
**What happened:** test_rag.py calls store_document every time it runs.
Running it twice inserted the same chunk twice. pgvector has no
built-in deduplication — it stores whatever you give it.
**Fix:** Added DELETE deduplication in psql for now. Will add a
content hash check in store_document in a later phase so duplicates
never get inserted in the first place.
**Lesson:** Vector stores don't deduplicate. You have to handle that yourself.