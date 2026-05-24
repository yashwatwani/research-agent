# reporter.py — turns eval results into a JSON file, a markdown report,
# and uploads the run to Phoenix as a dataset for visual comparison.
#
# Phoenix datasets are how you compare runs over time in the Phoenix UI.
# Two runs of the same dataset → side-by-side scores → see what changed.
#
# The Phoenix client API has changed across versions; we try the modern
# phoenix.client.Client().datasets.create_dataset() first, fall back to the
# older px.Client().upload_dataset(), and skip cleanly if neither is available.

import json
import os
from datetime import datetime
from src.config import PHOENIX_PORT


# truncation limits — keep markdown readable without losing debugging signal
CONTEXT_MAX_CHARS = 1500   # retrieved context can be huge; cap for readability
REPORT_MAX_CHARS = 4000    # reports are usually shorter, but cap as a safety net


def write_json(eval_run: dict, output_dir: str = "data/eval_results") -> str:
    os.makedirs(output_dir, exist_ok=True)
    run_id = eval_run["run_id"]
    path = os.path.join(output_dir, f"eval_{run_id}.json")
    with open(path, "w") as f:
        json.dump(eval_run, f, indent=2)
    print(f"\n[REPORTER] JSON written: {path}")
    return path


def _truncate(text: str, max_chars: int) -> str:
    # truncate with a clear marker so readers know content was cut
    if not text:
        return "(empty)"
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n_…truncated ({len(text) - max_chars} more chars in JSON file)_"


def write_markdown(eval_run: dict, output_dir: str = "data/eval_results") -> str:
    os.makedirs(output_dir, exist_ok=True)
    run_id = eval_run["run_id"]
    path = os.path.join(output_dir, f"eval_{run_id}.md")

    agg = eval_run["aggregate"]
    means = agg["mean_scores"]

    md = []
    md.append(f"# Eval Run — {run_id}")
    md.append("")
    md.append(f"**Started:** {eval_run['started_at']}  ")
    md.append(f"**Elapsed:** {eval_run['total_elapsed_seconds']:.1f}s  ")
    md.append(f"**Questions:** {agg['total_questions']} ({agg['valid_runs']} valid, {agg['agent_errors']} errors, {agg['blocked_by_guardrail']} blocked)")
    md.append("")

    md.append("## Aggregate Scores")
    md.append("")
    md.append("| Metric | Score |")
    md.append("|---|---|")
    md.append(f"| Relevance | {means['relevance']:.3f} |")
    md.append(f"| Groundedness | {means['groundedness']:.3f} |")
    md.append(f"| Completeness | {means['completeness']:.3f} |")
    md.append(f"| **Average** | **{means['average']:.3f}** |")
    md.append("")

    md.append("## Per-Category")
    md.append("")
    md.append("| Category | N | Mean Avg |")
    md.append("|---|---|---|")
    for cat, stats in agg["per_category"].items():
        md.append(f"| {cat} | {stats['n']} | {stats['mean_average']:.3f} |")
    md.append("")

    md.append("---")
    md.append("")
    md.append("## Per-Question Detail")
    md.append("")

    for r in eval_run["results"]:
        md.append(f"### [{r['id']}] {r['question']}")
        md.append("")

        # handle the agent-crashed case
        if r.get("error"):
            md.append(f"**ERROR:** {r['error']}")
            md.append("")
            md.append("---")
            md.append("")
            continue

        s = r["scores"]

        # metadata block
        md.append(f"**Category:** `{r['category']}` · **Blocked:** `{r['blocked_by_guardrail']}` · **Elapsed:** {r['elapsed_seconds']}s · **Average:** **{s['average']:.2f}**")
        md.append("")

        # if blocked, show why up front
        if r.get("blocked_by_guardrail") and r.get("block_reason"):
            md.append(f"> **Blocked by guardrail:** {r['block_reason']}")
            md.append("")

        # scores with reasoning
        md.append("#### Scores")
        md.append("")
        md.append(f"- **Relevance:** {s['relevance']['score']:.2f} — _{s['relevance']['reasoning']}_")
        md.append(f"- **Groundedness:** {s['groundedness']['score']:.2f} — _{s['groundedness']['reasoning']}_")
        md.append(f"- **Completeness:** {s['completeness']['score']:.2f} — _{s['completeness']['reasoning']}_")
        md.append("")

        # full agent report — this is what was missing before
        md.append("#### Agent Report")
        md.append("")
        report_text = _truncate(r.get("report", ""), REPORT_MAX_CHARS)
        # wrap in a quote block so headings inside the report don't break the markdown structure
        for line in report_text.split("\n"):
            md.append(f"> {line}")
        md.append("")

        # retrieved context — useful for understanding why groundedness scored what it did
        context_text = r.get("context", "") or ""
        if context_text:
            md.append("<details>")
            md.append("<summary><b>Retrieved Context</b> (click to expand)</summary>")
            md.append("")
            md.append("```")
            md.append(_truncate(context_text, CONTEXT_MAX_CHARS))
            md.append("```")
            md.append("")
            md.append("</details>")
            md.append("")

        md.append("---")
        md.append("")

    with open(path, "w") as f:
        f.write("\n".join(md))
    print(f"[REPORTER] Markdown written: {path}")
    return path


def _build_dataframe(eval_run: dict):
    # shared dataframe construction used by both upload paths
    import pandas as pd

    rows = []
    for r in eval_run["results"]:
        if not r.get("scores"):
            continue
        s = r["scores"]
        rows.append({
            "question_id": r["id"],
            "category": r["category"],
            "question": r["question"],
            "report": r.get("report", "")[:1000],  # cap to avoid massive cells
            "blocked": r.get("blocked_by_guardrail", False),
            "relevance": s["relevance"]["score"],
            "groundedness": s["groundedness"]["score"],
            "completeness": s["completeness"]["score"],
            "average": s["average"],
        })

    return pd.DataFrame(rows)


def push_to_phoenix(eval_run: dict) -> str | None:
    # uploads the run as a Phoenix dataset for visual comparison across runs
    # tries modern API first, falls back to legacy, skips gracefully if neither works

    dataset_name = f"research-agent-eval-{eval_run['run_id']}"

    # Attempt 1: modern phoenix.client API (Phoenix 5.x+)
    try:
        from phoenix.client import Client as PhoenixClient

        df = _build_dataframe(eval_run)
        client = PhoenixClient(base_url=f"http://localhost:{PHOENIX_PORT}")
        client.datasets.create_dataset(
            name=dataset_name,
            dataframe=df,
            input_keys=["question"],
            output_keys=["report"],
            metadata_keys=["category", "blocked", "relevance", "groundedness", "completeness", "average"],
        )
        print(f"[REPORTER] Phoenix dataset uploaded (modern API): {dataset_name}")
        print(f"[REPORTER] View at http://localhost:{PHOENIX_PORT}/datasets")
        return dataset_name
    except ImportError:
        pass  # phoenix.client not installed, try legacy
    except Exception as e:
        print(f"[REPORTER] Modern Phoenix API failed: {e}")

    # Attempt 2: legacy px.Client().upload_dataset() API
    try:
        import phoenix as px

        df = _build_dataframe(eval_run)
        client = px.Client()
        client.upload_dataset(
            dataframe=df,
            dataset_name=dataset_name,
            input_keys=["question"],
            output_keys=["report"],
            metadata_keys=["category", "blocked", "relevance", "groundedness", "completeness", "average"],
        )
        print(f"[REPORTER] Phoenix dataset uploaded (legacy API): {dataset_name}")
        print(f"[REPORTER] View at http://localhost:{PHOENIX_PORT}/datasets")
        return dataset_name
    except Exception as e:
        print(f"[REPORTER] Phoenix upload skipped: {e}")
        print(f"[REPORTER] JSON + markdown still written. Phoenix dataset is optional.")
        return None


def report(eval_run: dict, output_dir: str = "data/eval_results") -> dict:
    # writes all three sinks: JSON, markdown, Phoenix dataset
    json_path = write_json(eval_run, output_dir)
    md_path = write_markdown(eval_run, output_dir)
    phoenix_name = push_to_phoenix(eval_run)

    # console summary
    agg = eval_run["aggregate"]
    means = agg["mean_scores"]
    print("\n" + "=" * 60)
    print(f"  Eval Summary")
    print("=" * 60)
    print(f"  Questions: {agg['valid_runs']}/{agg['total_questions']} valid")
    print(f"  Relevance:    {means['relevance']:.3f}")
    print(f"  Groundedness: {means['groundedness']:.3f}")
    print(f"  Completeness: {means['completeness']:.3f}")
    print(f"  AVERAGE:      {means['average']:.3f}")
    print("=" * 60)

    return {
        "json_path": json_path,
        "markdown_path": md_path,
        "phoenix_dataset_name": phoenix_name,
    }