# Evaluation Suite

A test set + runner + scorers + reporter that measures how the research-agent performs across a fixed set of questions. Run it before and after a change to see if the change made the agent better or worse.

This document covers what the eval suite is, why it exists, the file structure, what each file does, and how to run it.

---

## Why evals exist

The agent is non-deterministic. The same change can look fine on one question and break another. Without a way to measure quality across a *fixed set* of questions, every change is a guess.

Two concepts often get confused:

| | Guardrails | Evals |
|---|---|---|
| When they run | Every request, in real time | When you decide to, in batch |
| What they do | Block one bad output | Measure aggregate quality |
| Output | A pass/block decision | A score for each dimension |
| Cost | Pennies per request | ~$0.30 per full run |
| Used for | Production safety | Engineering decisions |

You don't run evals to block traffic. You run them to answer questions like:

- "Did changing the synthesis prompt make the agent better?"
- "Can I switch to gpt-4o-mini and still meet quality bar?"
- "Is the Graph RAG path actually outperforming vector RAG for relationship questions?"

---

## What gets scored

Three dimensions, each scored 0.0 to 1.0 by an LLM judge (gpt-4o):

### Relevance
Does the report answer the actual question asked? Catches the failure mode where the agent grounds claims perfectly but rambles off-topic.

### Groundedness
Are the claims in the report supported by the retrieved context? Reuses the same scoring criterion as the runtime output validator in `src/guardrails/output_validator.py`. If you change one, change both.

### Completeness
Does the report cover the key aspects implied by the question? Catches the failure mode where the agent is relevant and grounded but only addresses half of what was asked.

A per-question average is also computed.

---

## File structure

```
research-agent/
├── run_eval.py                          # top-level entry point
└── src/
    └── eval/
        ├── __init__.py
        ├── tracer.py                    # existed already — Phoenix tracing setup
        ├── dataset.py                   # the test questions
        ├── runner.py                    # orchestrates agent runs + scoring
        ├── reporter.py                  # writes JSON, markdown, Phoenix dataset
        └── scorers/
            ├── __init__.py
            ├── base.py                  # shared judge call + JSON parsing
            ├── relevance.py
            ├── groundedness.py
            └── completeness.py

data/
└── eval_results/                        # output (auto-created on first run)
    ├── eval_<run_id>.json               # per-run structured data
    ├── eval_<run_id>.md                 # per-run human-readable report
    └── run_<timestamp>.log              # full stdout capture (via tee)
```

---

## What each file does

### `run_eval.py` (top-level)
The command-line entry point. Initialises tracing, parses args, runs the eval, calls the reporter.

Two usage modes:
- `python run_eval.py` — runs the full dataset
- `python run_eval.py --subset edge` — runs only one category

### `src/eval/dataset.py`
The list of test questions, each tagged with a category. Mix of:
- **concept** — generic AI/ML topics (transformers, RAG, vector search)
- **domain** — project-specific topics (MCP, pgvector, Phoenix, NetworkX)
- **comparison** — "X vs Y" questions, tests synthesis across sources
- **relationship** — "who uses X" type questions, exercises the graph route
- **current** — time-sensitive questions, exercises the web search path
- **edge** — out-of-scope or unusual questions, tests guardrails

Two helpers:
- `get_dataset()` returns the full list
- `get_by_category(category)` returns only one category

### `src/eval/runner.py`
The orchestrator. Three responsibilities:

1. For each question in the dataset, call `run_agent()` and capture the full state.
2. For each agent output, call all three scorers and capture scores + reasoning.
3. Aggregate results into mean scores overall and per-category.

Key function: `run_eval(subset=None)` returns the full result dict that the reporter consumes.

### `src/eval/scorers/base.py`
Shared LLM judge mechanism. All three scorers send a system prompt + user prompt to gpt-4o, expect back `{"score": float, "reasoning": str}`, parse it, clamp the score to [0, 1], and return.

Centralised here so model choice, temperature, and JSON parsing logic only exist in one place.

### `src/eval/scorers/relevance.py`
Scores whether the report answers the question asked. Sees only `(question, report)` — does not see the retrieved context.

### `src/eval/scorers/groundedness.py`
Scores whether the claims in the report are supported by the retrieved context. Sees `(question, context, report)`. Returns 0.0 immediately if context is empty (a report based on no context cannot be grounded by definition).

### `src/eval/scorers/completeness.py`
Scores whether the report covers the key aspects of the question. Sees only `(question, report)`. Identifies multi-part questions and judges coverage breadth, not depth.

### `src/eval/reporter.py`
Writes three artifacts after every run:

1. **JSON** at `data/eval_results/eval_<run_id>.json` — full structured data for diffing or reprocessing.
2. **Markdown** at `data/eval_results/eval_<run_id>.md` — human-readable report with aggregate scores, per-category breakdown, and per-question detail.
3. **Phoenix dataset** named `research-agent-eval-<run_id>` — uploaded to the running Phoenix instance for visual comparison across runs.

The Phoenix upload tries the modern `phoenix.client` API first, falls back to the legacy `px.Client()` API, and skips gracefully if neither works. JSON and markdown are never lost just because Phoenix upload broke.

### `src/eval/tracer.py`
Pre-existing. Initialises OpenTelemetry tracing so OpenAI calls and guardrail spans flow into Phoenix. Called from `run_eval.py` before anything else runs.

---

## How to run

### Pre-requisites

1. Phoenix must be running in a dedicated terminal tab:
   ```bash
   python -c "import phoenix as px; import time; px.launch_app(); [time.sleep(10) for _ in iter(int, 1)]"
   ```

2. PostgreSQL must be running (for the agent's memory layer).

### Run commands

```bash
# Quick subset — 2 edge-case questions, ~30 sec, ~$0.05
make eval-edge

# Full dataset — 15 questions, ~5-10 min, ~$0.30
make eval

# Just one category
make eval-domain
make eval-concept
```

Or directly without the Makefile:

```bash
python run_eval.py --subset edge
python run_eval.py
```

If using the direct commands and you want logs saved:

```bash
python run_eval.py 2>&1 | tee data/eval_results/run_$(date +%Y%m%d_%H%M%S).log
```

### Reading results

After a run, three places to look:

```bash
# 1. The terminal output — live console summary
# 2. The markdown report — human-readable per-question detail
cat data/eval_results/eval_<latest>.md

# 3. The Phoenix UI — visual comparison of this run vs previous runs
open http://localhost:6006/datasets
```

The markdown is the most useful day-to-day. The JSON is for tooling. Phoenix is for comparing two runs side-by-side.

---

## When to run

| Situation | Run what |
|---|---|
| Daily/weekly use of the agent | Nothing. Trust the guardrails. |
| Just tweaked a prompt | `make eval-edge` first, then `make eval` if the subset looks fine |
| Switched model or chunking strategy | `make eval` (full run) before and after |
| Added a new tool or data source | `make eval` (full run) |
| Monthly regression check | `make eval` (full run) |
| Something feels off | `make eval` and inspect per-question scores |

Do not run evals on every commit. They cost money and time and the variance between runs makes small differences meaningless.

---

## Interpreting scores

Two things to keep in mind:

### Variance is real
The LLM judge is non-deterministic even at temperature=0. Running the same eval twice can give 0.78 then 0.81. Some variation is noise, not signal.

Rule of thumb:
- Difference under 0.05 → probably noise
- Difference of 0.05 to 0.10 → suggestive, look at per-question details
- Difference over 0.10 → real change, investigate or celebrate

### Look per-category
The aggregate average hides things. If the overall score went from 0.75 to 0.78 but `relationship` category dropped from 0.65 to 0.45, you broke Graph RAG and need to fix it. Always scan the per-category table in the markdown.

### Look at low scorers
The most useful section of the markdown report is the per-question detail. Sort by lowest average. Read the judge's reasoning. The judge tells you exactly why it scored low — that is your debugging signal.

---

## Cost

Per question: 1 agent run (~3 to 6 LLM calls depending on cache hits) + 3 judge calls = roughly 6 to 9 calls of varying sizes.

Per full run (15 questions): roughly 90 to 130 LLM calls.

At gpt-4o pricing, one full run lands around $0.30 to $0.50 with current chunk sizes. SerpApi calls add a few cents on cache misses (limited by the free 100/month allowance — be mindful of this if you run multiple evals in a day).

---

## Adding new test questions

Just append to `EVAL_DATASET` in `src/eval/dataset.py`:

```python
{
    "id": "dom-005",
    "category": "domain",
    "question": "How does the agent's memory-first architecture reduce SerpApi cost?",
},
```

Use existing categories or add a new one. The runner picks up changes automatically.

---

## Adding a new scorer

Three steps:

1. Create `src/eval/scorers/<your_scorer>.py` following the same shape as the existing three. Export a `score(...)` function that returns `(float, str)`.

2. Import and call it from `src/eval/runner.py` inside `_eval_one`, add it to the `scores` dict returned.

3. Update `src/eval/reporter.py` to include the new scorer in the markdown output and Phoenix dataset metadata.

Resist the urge to add too many scorers. Three is enough to triangulate quality. More scorers means more LLM calls, more noise in the average, and more debugging when one of them gives weird results.

---

## Known limitations

### Reference answers are not used
This eval suite is reference-free — the judge sees the question and the agent's output but no "ideal answer." This works well for research questions where many valid answers exist, but it means the judge cannot catch factual errors the agent and judge both make. For domains where there is a single right answer, reference-based scoring would be more reliable.

### Same model judges itself
gpt-4o is being judged by gpt-4o. Both share blind spots. A separate judge model (e.g. Claude) would be more independent but adds another API dependency.

### Web-search-dependent questions are noisy
Questions in the `current` category depend on what SerpApi returns that day. Two runs of the same question can produce different reports because the web results differ. This is real-world behaviour — the eval reflects it, but cross-run comparisons on these specific questions should be interpreted carefully.

---

## Future improvements

Things deliberately out of scope for now but worth considering later:

- **Reference-based scoring** for domain questions where a single ideal answer exists
- **Multi-judge ensemble** (gpt-4o + claude + gpt-4o-mini) to reduce judge variance
- **Cost per run** tracked in the JSON output for budget visibility
- **Latency percentiles** in the aggregate stats (p50, p95) to catch performance regressions
- **CI integration** — run `make eval-edge` automatically on every PR to catch obvious regressions