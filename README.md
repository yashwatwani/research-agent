# ResearchAgent

A production AI agent built layer by layer, in public. Takes a research question, searches the web, reads sources, builds a knowledge graph, and writes a structured report. Remembers what it learned across sessions.

Built to understand every layer of the AI agent stack — not just use it.

**Follow the build on LinkedIn:** [your LinkedIn URL here]

---

## What this covers

- Layer 1: OpenAI API (gpt-4o for reasoning, text-embedding-3-small for embeddings)
- Layer 2: MCP servers built from scratch (web search via SerpApi)
- Layer 3: Three-tier memory — in-context state, RAG via pgvector, Graph RAG via NetworkX
- Layer 4: Google ADK orchestration (plan → search → retrieve → synthesise)
- Layer 5: Arize Phoenix tracing and evals
- Layer 6: guardrails — input filtering, tool allow-list, output validation

---

## Prerequisites

- Python 3.12+
- PostgreSQL 17 (via Homebrew)
- pgvector 0.8.2 (via Homebrew)
- Homebrew (Mac)

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/yashwatwani/research-agent.git
cd research-agent
```

### 2. Create and activate virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your keys:

OPENAI_API_KEY=your_openai_key_here
SERPAPI_KEY=your_serpapi_key_here
DATABASE_URL=postgresql://YOUR_MAC_USERNAME@localhost:5432/research_agent
PHOENIX_PORT=6006

Get your keys here:
- OpenAI: https://platform.openai.com/api-keys
- SerpApi: https://serpapi.com (100 free searches/month)

### 5. Install and set up PostgreSQL 17 with pgvector

**Install Postgres 17:**

```bash
brew install postgresql@17
brew services start postgresql@17
```

**Add Postgres 17 to your PATH:**

```bash
echo 'export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Verify you're on 17:**

```bash
psql --version
# should print: psql (PostgreSQL) 17.x
```

**Install pgvector:**

```bash
brew install pgvector
```

**Copy pgvector files into Postgres 17's extension directory:**

```bash
cp /opt/homebrew/Cellar/pgvector/0.8.2/lib/postgresql@17/vector.dylib \
   /opt/homebrew/opt/postgresql@17/lib/postgresql/

cp /opt/homebrew/Cellar/pgvector/0.8.2/share/postgresql@17/extension/* \
   /opt/homebrew/opt/postgresql@17/share/postgresql/extension/
```

**Restart Postgres 17:**

```bash
brew services restart postgresql@17
```

**Create the database and enable the extension:**

```bash
psql postgres
```

Then inside psql, one command at a time:

```sql
CREATE DATABASE research_agent;
\c research_agent
CREATE EXTENSION vector;
\q
```

You should see `CREATE EXTENSION` — that means pgvector is working.

---

## Verify everything works

**Test OpenAI connection:**

```bash
python test_connection.py
```

**Test web search:**

```bash
python test_search.py
```

**Test Phoenix tracing (open a separate terminal tab first):**

```bash
# Tab 1 — keep this running
python -c "
import phoenix as px
import time
session = px.launch_app()
print(f'Phoenix running at {session.url}')
while True:
    time.sleep(10)
"

# Tab 2
python test_tracing.py
```

Then visit http://localhost:6006 to see traces.

**Test RAG:**

```bash
python test_rag.py
```

---

## Project structure

research-agent/
├── src/
│   ├── agent/
│   │   └── researcher.py       # main agent loop (Phase 6)
│   ├── mcp_servers/
│   │   └── search_mcp.py       # web search MCP tool
│   ├── memory/
│   │   ├── vector_store.py     # RAG via pgvector
│   │   ├── graph_store.py      # Graph RAG via NetworkX
│   │   └── session.py          # in-context session state
│   ├── guardrails/
│   │   └── filters.py          # input/output safety checks
│   ├── eval/
│   │   └── tracer.py           # Phoenix tracing setup
│   └── config.py               # all settings in one place
├── data/
│   ├── vector_store/
│   └── graph/
├── tests/
├── .env.example
├── requirements.txt
└── README.md

---

## Build phases

| Phase | What gets built | Status |
|-------|----------------|--------|
| 1 | Project structure + OpenAI connection | Done |
| 2 | Search MCP server | Done |
| 3 | Phoenix tracing | Done |
| 4 | RAG via pgvector | In progress |
| 5 | Graph RAG via NetworkX | Upcoming |
| 6 | ADK agent loop | Upcoming |
| 7 | guardrails + full evals | Upcoming |

---

## Why each tool was chosen

**OpenAI over Anthropic:** Key availability. Swap is one line in config.py.

**SerpApi over DuckDuckGo/Brave:** DuckDuckGo blocked scraping. Brave has no free tier. SerpApi gives 100 free searches/month.

**pgvector over a dedicated vector DB:** It's just Postgres with an extension. No new infrastructure, no new operational burden. Add a dedicated vector DB when pgvector's performance limits become real, not before.

**NetworkX over Neo4j:** Learn the concept first on an in-memory graph. Migrate to Neo4j when NetworkX runs out of road.

**Arize Phoenix over LangSmith:** Self-hosted, open source, no vendor lock-in.

---

## Follow the build

All concepts and architecture decisions explained on LinkedIn as each phase is built.
Full code lives here.

