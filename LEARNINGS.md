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


---

### What is 1536 and why that specific number?
**Phase:** 4 — RAG
**What it is:** 1536 is the output dimension of text-embedding-3-small.
OpenAI chose it, not us. Every piece of text gets converted to exactly
1536 numbers regardless of how long or short the text is.
**Why not fewer:** Less expressive. Nearby concepts start overlapping,
similarity search gets less accurate.
**Why not more:** OpenAI's larger model uses 3072. More accurate but
costs more per call, more storage, slower search. 1536 is the sweet spot.
**Why 1536 specifically:** It is a multiple of 512, which is
computationally efficient for matrix operations on modern hardware.
**Lesson:** The dimension is baked into the model. If you switch models
the number changes — that is why EMBEDDING_DIMS lives in config.py.

---

### What is NetworkX and how does it store a graph?
**Phase:** 5 — Graph RAG
**What it is:** A pure Python library for creating and querying graphs.
No database, no server. The graph lives in memory as Python objects.
**How it works:** Nodes are entities like "Anthropic" or "MCP". Edges
are directed relationships like "adopted" connecting two nodes. We
persist the graph to disk as a pickle file between sessions.
**Why pickle:** Simple, fast, zero setup. Not suitable for production
(pickle is not human readable and not queryable with SQL) but perfect
for learning the concept before migrating to Neo4j.
**Lesson:** NetworkX is for understanding graph concepts. Neo4j is for
production. Build on NetworkX first, migrate when you need persistence,
concurrent access, or complex graph queries.

---

### What does the query router actually do?
**Phase:** 5 — Graph RAG
**What it is:** A small classifier that reads a question and returns
either "graph" or "vector" before any retrieval happens.
**How it decides:**
- "what is X?" "explain Y" "how does Z work" → vector
- "who uses X?" "which companies" "how are X and Y related" → graph
**Why it matters:** Without the router, every question would go to
vector search. Relationship questions would return nothing because
"who adopted MCP" does not match any stored text closely enough.
**Lesson:** The router is what makes RAG and Graph RAG complementary
rather than competing. Each handles the questions the other misses.

---

### Why does graph retrieval return all connected edges not just matching ones?
**Phase:** 5 — Graph RAG
**What happened:** Querying "who adopted MCP?" returned all edges
connected to MCP — donated to, developed, integrated — not just
"adopted" ones.
**Why:** query_graph returns ALL incoming and outgoing edges for the
matched node, not just edges matching the relation word in the question.
**Is this a bug:** No. It gives the full picture of everything connected
to the entity. Filtering by specific relation type is a future enhancement.
**Lesson:** Graph traversal returns neighbourhood context. Design
queries with that in mind.

---

### Why check memory before searching the internet?
**Phase:** 6 — agent loop
**What happened:** Original pipeline always searched the web even if
the answer was already in memory. Every run cost a SerpApi call and
added 2 seconds of latency.
**Fix:** Added check_memory_node as the first step. If similarity > 0.6
in vector store or more than 2 graph results found, skip web search.
The internet becomes a fallback for things the agent does not already know.
**Lesson:** Retrieval first, search second. The agent gets faster and
cheaper the more it runs because memory fills up over time.

---

### What is AgentState and why use a dataclass?
**Phase:** 6 — agent loop
**What it is:** A Python dataclass that carries everything the agent
knows as it moves through the pipeline nodes.
**Why not just pass variables:** The pipeline has 4 nodes. Without a
shared state object you would pass dozens of variables between functions.
With AgentState you pass one thing and every node can read and write
everything.
**Fields:**
- question — the original input, never changes
- search_queries — generated by plan_node
- search_results — fetched by search_node
- retrieved_context — filled by check_memory or retrieve_node
- skip_search — flag set by check_memory_node
- report — final output from synthesise_node
- error — catches any exception without crashing
**Lesson:** State objects make pipelines readable. You can see exactly
what each node needs and what it produces.

---

### Why is everything async?
**Phase:** 6 — agent loop
**What it is:** async/await is a Python pattern for non-blocking I/O.
**Why we use it:** Web search and OpenAI calls spend most of their time
waiting for a network response. Async lets Python do other things while
waiting instead of blocking the entire program.
**Practical impact:** In a future phase when we run multiple search
queries in parallel, async is what makes that possible without threading
complexity. Right now it runs sequentially but the foundation is there.
**Lesson:** Write async from the start even if you run sequentially now.
Retrofitting async onto sync code later is painful.

---

### NetworkX
**What it does:** In-memory knowledge graph. Stores entities and
relationships extracted from sources as nodes and edges. Powers Graph RAG.
**Why we chose it:** Pure Python, zero setup, no server. Learn the
concept here before migrating to Neo4j when the graph needs production
grade persistence.
**Where it lives:** `src/memory/graph_store.py`
**Persisted as:** `data/graph/knowledge_graph.pkl`

---

### Google ADK
**What it does:** Orchestration framework. Wires all layers into a
sequential pipeline — check memory → plan → search → retrieve → synthesise.
**Why we chose it:** Already familiar from InsightsMix. Clean state
graph model that maps directly to an agent loop.
**Where it lives:** `src/agent/researcher.py`
**Key concept:** Each node takes AgentState, adds something, returns
AgentState. The pipeline is just four function calls in sequence.

### Why did one run generate 3 queries and another generate none?
**Phase:** 6 — agent loop
**What happened:** "What companies adopted MCP?" generated no queries.
"What are MCP security vulnerabilities?" generated 3 queries.
**Why:** plan_node only runs when check_memory_node decides there is
not enough context in memory. The adoption question had good graph
context already stored so skip_search was set to True and plan_node
was never called. The security question had no relevant context so
the full pipeline ran.
**The two paths:**
- Memory hit: check_memory → synthesise (2 steps)
- Memory miss: check_memory → plan → search → retrieve → synthesise (5 steps)
**Lesson:** Conditional branching is what makes the agent efficient.
It only does work that is necessary. The more memory fills up the
more often the short path gets taken.

---

### Why does the agent store duplicates from web search?
**Phase:** 6 — agent loop
**What happened:** Running the same query twice stores the same
chunks again. "Model Context Protocol: Security Risks" appeared
twice in the stored results.
**Why:** store_source has no deduplication check. It stores whatever
it receives regardless of whether that content already exists.
**Fix needed:** Add a content hash check in store_source — hash the
text before storing and skip if the hash already exists in the db.
This is a Phase 7 task.
**Lesson:** Always deduplicate before storing. Vector stores do not
do this automatically.

---

### How does the agent decide when to search the web vs use memory?
**Phase:** 6 — agent loop
**The logic in check_memory_node:**
- Classify the question (graph or vector)
- Run retrieval against existing memory
- If vector route and top result similarity > 0.6 → skip search
- If graph route and more than 2 results found → skip search
- Otherwise → search the web
**Why 0.6 threshold:** Below 0.6 the match is too weak to trust.
The agent might synthesise a report based on loosely related chunks
and produce a misleading answer. 0.6 is conservative — tune it higher
if you want the agent to search more often, lower if you want it to
rely on memory more.
**Lesson:** The threshold is the key tuning parameter for the
memory vs search tradeoff. It directly controls cost and freshness.

# --- PHASE 7 ADDITIONS — append to bottom of LEARNINGS.md ---

## Components added in Phase 7

### OpenTelemetry
**What it does:** Industry standard for emitting traces and spans from
applications. Phoenix is just one OTel consumer. By emitting spans
through OTel we get vendor neutrality — same instrumentation works
with Phoenix, Datadog, Honeycomb, or anything else that speaks OTel.
**Where we use it:** `src/guardrails/logger.py` emits spans for every
guardrail event so they show up in the Phoenix UI alongside the agent
traces.
**Why it matters:** The OpenAI SDK is already auto-instrumented by
Phoenix's `register()` call. Manually emitting our own spans lets us
trace logic that is not an API call — guardrail decisions, dedup
skips, query routing.

---

### SHA-256 hashing
**What it does:** Deterministic one-way function that converts any text
into a fixed 64-character hex string. Same input always produces the
same output. Different input almost certainly produces a different
output (collisions are astronomically rare).
**Why we use it:** Dedup. We hash each chunk and each source so the
database can answer "have I seen this exact text before?" in O(1) via
an indexed lookup.
**Where it lives:** `_hash()` helper in `vector_store.py` and
`graph_store.py`.
**Lesson:** Hashing is the right tool when you need to compare large
blobs of text for exact equality without storing or scanning the
original text.

---

## Doubts & explanations

### Why dedupe on content hash and not on URL?
**Phase:** 7 — dedup
**What happened:** The first instinct was to check "have I seen this
URL before?" — simpler, one column to compare. But that breaks two
real cases:
- Same URL, content changed (article was updated since last visit) →
  URL-based check skips the update, vector store stays stale.
- Different URLs quoting the same text (two news sites republishing
  the same Reuters paragraph) → URL-based check stores the duplicate
  paragraph twice, polluting retrieval with redundant chunks.
**Fix:** Hash the content itself. URL is metadata only.
**Lesson:** Dedup on what you actually stored, not on where it came from.

---

### Why two layers of dedup — source AND chunk?
**Phase:** 7 — dedup
**What it is:**
- Source-level dedup lives in `graph_store.py`. Hashes the full source
  text. If seen → skip entity extraction (the expensive gpt-4o call).
- Chunk-level dedup lives in `vector_store.py`. Hashes each chunk. If
  seen → skip embedding + insert.
**Why both:** They catch different failure modes.
- Source-level catches "same article ingested twice" — fast, blocks the
  most expensive call (gpt-4o entity extraction).
- Chunk-level catches "different articles sharing a paragraph" — keeps
  the vector store clean of duplicate text even when source hashes
  differ.
**Lesson:** Defence in depth. The two layers are not redundant — they
catch genuinely different cases.

---

### Why pre-check before embed instead of just relying on ON CONFLICT?
**Phase:** 7 — dedup
**What happened:** First instinct was to embed every chunk and let
Postgres reject duplicates via `ON CONFLICT (content_hash) DO NOTHING`.
Simpler code. But by the time the conflict fires we have already paid
for the OpenAI embedding API call.
**Fix:** Pre-check with a SELECT before embed. Skip the embedding
entirely if the hash already exists.
**Lesson:** When the expensive operation is the API call, not the DB
write, do the lookup first. `ON CONFLICT` is the atomic safety net
(handles race conditions if two processes insert simultaneously) but
should not be the only line of defence.

---

### What does the UNIQUE index on content_hash actually do?
**Phase:** 7 — dedup
**What it is:** A Postgres database constraint that physically prevents
two rows from sharing the same content_hash. Enforced at the storage
engine level — not optional, not application logic.
**Why it matters:** Without it, two parallel processes calling
store_document with the same chunk could both pass the SELECT check
(neither sees the other yet), both call embed_text, and both try to
INSERT — getting two duplicate rows. The UNIQUE index makes the
second INSERT fail (or with `ON CONFLICT DO NOTHING`, silently skip).
**Lesson:** Application-level checks are an optimisation. The
database-level constraint is the actual guarantee.

---

### What are guardrails and why do we need them?
**Phase:** 7 — guardrails
**What they are:** Deterministic checks that wrap around the
non-deterministic LLM. They sit at three points: before the LLM sees
the input, between the LLM and any tool it wants to call, and after
the LLM produces output.
**Why:** An LLM is non-deterministic by design. Same input can produce
different outputs. Guardrails are the deterministic floor that makes
the system predictable enough to ship.
**What they catch:**
- Input filter: prompt injection, out-of-scope questions, garbage input.
- Tool allow-list: unknown or hallucinated tool names.
- Output validator: hallucinated claims not grounded in retrieved context.
**Lesson:** LLMs alone are not production systems. Guardrails are what
turn an LLM into a system you can rely on.

---

### Why two-stage input filtering (regex then LLM)?
**Phase:** 7 — guardrails
**What happens:** Stage 1 runs a list of regex patterns against the
question. Cheap, no API call. Catches obvious injection attempts like
"ignore previous instructions" or fake system headers. Stage 2, only
if stage 1 passes, calls gpt-4o-mini to classify the input as allow,
block, or out_of_scope.
**Why both:** Regex is free but only catches what you anticipated.
LLM classifier catches paraphrased attacks regex would miss
("forget what you were told before" instead of "ignore previous
instructions") but costs an API call per question. Running regex
first means most legitimate questions skip the LLM call entirely.
**Lesson:** Stack cheap deterministic checks first, expensive LLM
checks second. Most traffic terminates at the cheap layer.

---

### What does fail open mean and why use it for classifier errors?
**Phase:** 7 — guardrails
**What it is:** If the LLM classifier returns garbage that we cannot
parse, we let the request through anyway and log a warning. The
alternative — failing closed — would block the request.
**Why fail open here:** A classifier returning malformed JSON is a
transient LLM jitter, not evidence of a real attack. Blocking
legitimate users due to model variance creates more harm than letting
an occasional edge case through.
**Why NOT fail open everywhere:** For high-stakes systems (financial
transactions, medical advice) you fail closed — better to refuse than
risk wrong actions. For a research agent reading public web data,
fail open is the right tradeoff.
**Lesson:** Fail mode is a product decision, not just an engineering one.

---

### What is LLM-as-judge and how does the output validator use it?
**Phase:** 7 — guardrails
**What it is:** Using one LLM call to evaluate the output of another.
Here gpt-4o sees the question, the retrieved context, and the
generated report — and returns a groundedness score from 0.0 to 1.0
plus a one-sentence reasoning.
**Why it works:** Judging whether claims are supported by source text
is a simpler task than generating the report in the first place. The
judge can be the same model size — gpt-4o judging gpt-4o output works
fine in practice because the criterion is "is this claim in the
context, yes or no."
**Threshold:** Starts at 0.5. The actual right threshold depends on
how strict you want to be — tune by inspecting the JSONL logs after
running real queries.
**Lesson:** Same model used as a judge often catches mistakes the
generator made. The two tasks (generate vs verify) are different
enough that the judge is not just confirming its own bias.

---

### What is the difference between guardrails and evals?
**Phase:** 7 — guardrails
**Same scoring logic, different jobs.**
- Guardrails run every time, in production, on a single response, and
  block or warn based on the result.
- Evals run in batch on a test set, give aggregate metrics, and tell
  you whether the agent got better or worse between versions.
**Practical impact:** The groundedness scoring code in
`output_validator.py` is the same logic the eval suite will use.
Guardrail = "block this one bad response now." Eval = "measure how
often this kind of response happens across 100 test questions."
**Lesson:** Build the scoring logic once. Use it twice. Online for
guardrails, offline for evals.

---

### Why log to both JSONL and Phoenix?
**Phase:** 7 — guardrails
**Two sinks, two jobs:**
- JSONL at `data/logs/guardrails.jsonl` is for batch analysis. Grep,
  jq, feed into eval datasets, count violation types over time.
- Phoenix spans are for debugging individual requests. When a specific
  user request fails, see the guardrail span alongside the LLM calls
  in the same trace.
**Why not pick one:** JSONL alone means you cannot see violations in
the context of a full agent run. Phoenix alone means you cannot do
historical analysis across thousands of past requests.
**Lesson:** Logging is not a single concern. Use the right sink for
the right question.

---

### Why is the tool allow-list a soft check instead of a hard block?
**Phase:** 7 — guardrails
**What we chose:** Soft check, log violations only. If the agent tries
to call a tool not in ALLOWED_TOOLS, we log the violation and return
an error string. We do not raise an exception.
**Why soft for this project:** The agent currently has one tool
(search_web). Hard blocking would crash the agent loop. Soft logging
captures the signal — when you later add a calculator tool and the
agent suddenly tries to call weather_api (hallucinated), the JSONL
log tells you exactly what happened.
**When to go hard:** Production systems handling money, user data, or
external side effects. Anywhere "wrong tool called" is a security
issue, not a debugging signal.
**Lesson:** Strictness is a function of blast radius. Match enforcement
to consequences.

---

### Why does the validator run AFTER synthesise and not during?
**Phase:** 7 — guardrails
**Alternative considered:** Make the synthesise prompt enforce
groundedness directly ("only use claims supported by the context").
Cheaper — one LLM call instead of two.
**Why we use a separate validator anyway:** Two reasons.
- The generator is biased toward producing a complete answer. It has
  an incentive to fill gaps with plausible-sounding inferences. The
  validator is a fresh call with no such incentive.
- The validator gives an explicit score we can log and tune against.
  A prompt-only approach gives no signal — you cannot tell whether
  the system is getting better or worse over time.
**Lesson:** Verification and generation should be separate steps.
Combining them hides failure signals.

---

### Why does the dedup function save only chunk hashes and source hashes, not the full source text?
**Phase:** 7 — dedup
**What happened:** A natural question — if we are hashing the full
source text for dedup, why not store it too? Then we could re-chunk
later with different settings without re-fetching from the web.
**Why we did not:** Storage discipline. The full source is already
represented across the chunks table (as ~5-10 chunk rows). Storing
the original full text again would roughly double storage. The
hashes alone are sufficient for the dedup job.
**Tradeoff worth knowing:** If you ever want to experiment with
different chunking strategies (chunk size 500 vs 300, different
overlap), you cannot do that without re-fetching the source from
the web — because the original is gone. For a learning project this
is fine. For production at scale, store the full content too.
**Lesson:** Store only what you need for the current job. Add storage
later when a new use case justifies it.

# --- END PHASE 7 ADDITIONS ---