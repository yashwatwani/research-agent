# runner.py — runs the agent over the eval dataset and scores each output
# entry point: run_eval()
#
# for each question:
#   1. run the agent end-to-end (this includes guardrails — blocked responses get scored too)
#   2. run all three scorers against the result
#   3. collect into a structured dict
# returns: dict with per-question results + aggregate stats

import asyncio
import time
from datetime import datetime
from src.agent.researcher import run_agent
from src.eval.dataset import get_dataset
from src.eval.scorers import relevance, groundedness, completeness


async def _eval_one(question_dict: dict) -> dict:
    # runs agent on one question, then scores all three dimensions
    q_id = question_dict["id"]
    q_text = question_dict["question"]
    category = question_dict["category"]

    print(f"\n{'─' * 60}")
    print(f"[{q_id}] ({category}) {q_text}")
    print(f"{'─' * 60}")

    # 1. run the agent
    start = time.time()
    try:
        agent_state = await run_agent(q_text)
        agent_error = None
    except Exception as e:
        # agent crashed — record the failure but keep the eval moving
        agent_state = None
        agent_error = str(e)
        print(f"[EVAL] agent crashed: {e}")

    elapsed = time.time() - start

    if agent_state is None or agent_error is not None:
        return {
            "id": q_id,
            "category": category,
            "question": q_text,
            "error": agent_error,
            "elapsed_seconds": elapsed,
            "scores": None,
        }

    report = agent_state.report or ""
    context = getattr(agent_state, "context_text", "") or ""
    was_blocked = getattr(agent_state, "blocked", False)
    block_reason = getattr(agent_state, "block_reason", None)

    # 2. score all three dimensions
    print(f"[EVAL] scoring relevance...")
    rel_score, rel_reason = relevance.score(q_text, report)
    print(f"[EVAL] scoring groundedness...")
    gnd_score, gnd_reason = groundedness.score(q_text, context, report)
    print(f"[EVAL] scoring completeness...")
    cmp_score, cmp_reason = completeness.score(q_text, report)

    avg = round((rel_score + gnd_score + cmp_score) / 3, 3)

    result = {
        "id": q_id,
        "category": category,
        "question": q_text,
        "report": report,
        "context": context,                              # NEW: include retrieved context
        "blocked_by_guardrail": was_blocked,
        "block_reason": block_reason,
        "elapsed_seconds": round(elapsed, 2),
        "scores": {
            "relevance": {"score": rel_score, "reasoning": rel_reason},
            "groundedness": {"score": gnd_score, "reasoning": gnd_reason},
            "completeness": {"score": cmp_score, "reasoning": cmp_reason},
            "average": avg,
        },
    }

    print(f"[EVAL] rel={rel_score:.2f} gnd={gnd_score:.2f} cmp={cmp_score:.2f} avg={avg:.2f}")
    return result


def _aggregate(results: list[dict]) -> dict:
    # compute mean scores across all questions, and per-category breakdown
    valid = [r for r in results if r.get("scores")]

    if not valid:
        return {"total_questions": len(results), "valid_runs": 0}

    rel_mean = sum(r["scores"]["relevance"]["score"] for r in valid) / len(valid)
    gnd_mean = sum(r["scores"]["groundedness"]["score"] for r in valid) / len(valid)
    cmp_mean = sum(r["scores"]["completeness"]["score"] for r in valid) / len(valid)
    avg_mean = sum(r["scores"]["average"] for r in valid) / len(valid)

    # per-category
    categories = {}
    for r in valid:
        cat = r["category"]
        categories.setdefault(cat, []).append(r["scores"]["average"])
    per_cat = {
        cat: {"n": len(scores), "mean_average": round(sum(scores) / len(scores), 3)}
        for cat, scores in categories.items()
    }

    blocked_count = sum(1 for r in valid if r.get("blocked_by_guardrail"))

    return {
        "total_questions": len(results),
        "valid_runs": len(valid),
        "agent_errors": len(results) - len(valid),
        "blocked_by_guardrail": blocked_count,
        "mean_scores": {
            "relevance": round(rel_mean, 3),
            "groundedness": round(gnd_mean, 3),
            "completeness": round(cmp_mean, 3),
            "average": round(avg_mean, 3),
        },
        "per_category": per_cat,
    }


async def run_eval(subset: list[dict] | None = None) -> dict:
    # main entry point. pass subset=... to run on a partial dataset.
    dataset = subset or get_dataset()

    print(f"\n{'=' * 60}")
    print(f"  Eval run starting — {len(dataset)} questions")
    print(f"  Started at {datetime.utcnow().isoformat()}Z")
    print(f"{'=' * 60}")

    start = time.time()
    results = []
    for q in dataset:
        result = await _eval_one(q)
        results.append(result)

    elapsed = time.time() - start
    aggregate = _aggregate(results)

    return {
        "run_id": datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
        "started_at": datetime.utcnow().isoformat() + "Z",
        "total_elapsed_seconds": round(elapsed, 1),
        "aggregate": aggregate,
        "results": results,
    }