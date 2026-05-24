alias eval-edge='python run_eval.py --subset edge 2>&1 | tee data/eval_results/run_$(date +%Y%m%d_%H%M%S).log'
alias eval-full='python run_eval.py 2>&1 | tee data/eval_results/run_$(date +%Y%m%d_%H%M%S).log'

# Running the System

Everything you need to start, use, test, and evaluate the research-agent.

---

## What needs to be running

The agent depends on three things. All three must be up before you run anything.

```
Terminal 1 (background)    Terminal 2 (background)    Terminal 3 (your work)
───────────────────────    ───────────────────────    ───────────────────────
PostgreSQL                 Phoenix                    python test_agent.py
brew service               dedicated python process   python run_eval.py
always on                  keep the tab open          make eval-edge
                                                      etc.
```

---

## Starting the system

### Step 1: PostgreSQL

PostgreSQL runs as a Homebrew background service. Start it once and it stays running across reboots.

```bash
brew services start postgresql@17
```

Verify it's up and your database exists:

```bash
psql -d research_agent -c "SELECT COUNT(*) FROM chunks;"
```

If this returns a number (even 0), you're good. If it errors, PostgreSQL isn't running or the database doesn't exist — see `POSTGRES.md` for setup.

### Step 2: Phoenix (dedicated terminal tab)

Open a new terminal tab. Keep it open for the entire session.

```bash
cd ~/research-agent
source venv/bin/activate
python -c "
import phoenix as px
import time
session = px.launch_app()
print(f'Phoenix running at {session.url}')
[time.sleep(10) for _ in iter(int, 1)]
"
```

Phoenix is now at `http://localhost:6006`. Every LLM call and every guardrail event will appear here as traces.

If you see a port 4317 error, Phoenix is already running in another tab — that's fine, the traces still flow through.

### Step 3: Activate your virtual environment

In your working terminal tab:

```bash
cd ~/research-agent
source venv/bin/activate
```

---

## Running the agent

```bash
python test_agent.py
```

This runs the full pipeline end-to-end on a hardcoded question. Watch the terminal to see which path the agent takes.

**Two possible paths:**

```
Memory hit (fast):
input_filter → check_memory → synthesise → output_validator

Memory miss (full):
input_filter → check_memory → plan → search → retrieve → synthesise → output_validator
```

The agent gets faster the more you use it — memory fills up over time and more questions take the short path.

---

## Running tests

```bash
make test-dedup         # verify chunk + source dedup is working
make test-guardrails    # verify input filter, allow-list, output validator
python test_rag.py      # verify vector store retrieval
python test_graph_rag.py    # verify graph store + entity extraction
python test_memory_manager.py   # verify unified retrieval routing
python test_tracing.py  # verify Phoenix tracing is active
```

Run the first two after any code change. Run the rest if you've changed the specific layer they cover.

---

## Running evals

Evals measure agent quality across a fixed set of 15 questions. Run them before and after a meaningful change to see if the change helped or hurt.

```bash
make eval-edge      # 2 edge-case questions, ~30 sec, ~$0.05 — use as a smoke test
make eval-domain    # 4 domain questions, ~2 min
make eval-concept   # 4 concept questions, ~2 min
make eval           # full 15-question run, ~5-10 min, ~$0.30
```

Results land in `data/eval_results/`:

```bash
cat data/eval_results/eval_<latest>.md     # human-readable report
open http://localhost:6006/datasets         # Phoenix visual comparison
```

See `EVAL.md` for a full guide to interpreting results and deciding when to run evals.

---

## Inspecting the data stores

### Check what's in the vector store

```bash
# total chunks stored
psql -d research_agent -c "SELECT COUNT(*) FROM chunks;"

# most recently stored sources
psql -d research_agent -c "SELECT source_title, source_url, ingested_at FROM sources ORDER BY ingested_at DESC LIMIT 10;"

# sample chunks from a specific source
psql -d research_agent -c "SELECT content FROM chunks WHERE source_url LIKE '%wikipedia%' LIMIT 3;"
```

### Check the knowledge graph

```bash
python -c "
from src.memory.graph_store import get_graph_stats
stats = get_graph_stats()
print(f'Nodes: {stats[\"nodes\"]}')
print(f'Edges: {stats[\"edges\"]}')
print(f'Sample entities: {stats[\"entities\"][:10]}')
"
```

### Check guardrail logs

```bash
# all events
cat data/logs/guardrails.jsonl

# blocks only
cat data/logs/guardrails.jsonl | python -c "
import sys, json
for line in sys.stdin:
    e = json.loads(line)
    if e['event_type'] == 'block':
        print(e)
"

# count by event type
cat data/logs/guardrails.jsonl | python -c "
import sys, json
from collections import Counter
events = [json.loads(l)['event_type'] for l in sys.stdin]
print(Counter(events))
"
```

### Visualise the knowledge graph

```bash
python visualize_graph.py
```

Opens an interactive D3 graph in your browser showing all stored entities and relationships.

---

## Stopping the system

```bash
# stop PostgreSQL
brew services stop postgresql@17

# Phoenix — just close the terminal tab
# there is no persistent state in Phoenix; traces are in-memory only

# venv — just close the terminal tab or deactivate
deactivate
```

You don't need to stop PostgreSQL at the end of every session. It's designed to run as a background service continuously.

---

## Quick reference

| Task | Command |
|---|---|
| **Start Postgres** | `brew services start postgresql@17` |
| **Stop Postgres** | `brew services stop postgresql@17` |
| **Start Phoenix** | See Step 2 above |
| **Activate venv** | `source venv/bin/activate` |
| **Run agent** | `python test_agent.py` |
| **Test dedup** | `make test-dedup` |
| **Test guardrails** | `make test-guardrails` |
| **Quick eval** | `make eval-edge` |
| **Full eval** | `make eval` |
| **View traces** | `open http://localhost:6006` |
| **View eval report** | `cat data/eval_results/eval_<latest>.md` |
| **Chunk count** | `psql -d research_agent -c "SELECT COUNT(*) FROM chunks;"` |
| **Source count** | `psql -d research_agent -c "SELECT COUNT(*) FROM sources;"` |
| **Graph stats** | `python -c "from src.memory.graph_store import get_graph_stats; print(get_graph_stats())"` |
| **Guardrail log** | `cat data/logs/guardrails.jsonl` |
| **Visualise graph** | `python visualize_graph.py` |

---

## Daily workflow

```bash
# start of session
brew services start postgresql@17      # if not already running
# open Phoenix tab, paste the python command
source venv/bin/activate

# use the agent
python test_agent.py

# after a code change
make test-dedup
make test-guardrails

# after a meaningful change (prompt, model, chunk size, etc.)
make eval-edge                         # quick check
make eval                              # full run if subset looked fine

# end of session
# nothing required — postgres keeps running, close the Phoenix tab
```

---

## Troubleshooting

### "connection refused" on psql
PostgreSQL isn't running. Run `brew services start postgresql@17`.

### Port 4317 error when starting Phoenix
Phoenix is already running in another tab. Ignore the error — traces flow through fine. Check `localhost:6006` to confirm.

### "No module named src"
You're running from the wrong directory or the venv isn't active. Make sure you're in `~/research-agent` and have run `source venv/bin/activate`.

### Retrieval returns 0 results
Either the vector store is empty (run the agent on a few questions first to populate it) or the ivfflat index is blocking results with too little data. See `LEARNINGS.md` for the full explanation.

### SerpApi returns no results
You've used your 100 free searches for the month. The agent will fall back to whatever is in memory. Check `https://serpapi.com/dashboard` to see usage.

### Groundedness score always low
The output validator threshold is 0.5. If legitimate responses keep getting blocked, the agent's synthesis prompt may be too loose or the retrieval quality is low. Run `make eval` to get aggregate scores and identify which question categories are underperforming.