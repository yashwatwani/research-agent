# output_validator.py — LLM-as-judge groundedness check
# Runs after synthesise_node writes the report.
# Scores 0.0-1.0 on how well the report's claims are supported by retrieved context.
# Blocks the response if score < THRESHOLD.
#
# Threshold starts at 0.5 (balanced). Tune later based on JSONL logs:
#   cat data/logs/guardrails.jsonl | jq 'select(.guardrail=="output_validator")'

import json
from openai import OpenAI
from src.config import OPENAI_API_KEY, CHAT_MODEL
from src.guardrails.logger import log_event

client = OpenAI(api_key=OPENAI_API_KEY)

THRESHOLD = 0.5


def check_output(question: str, context: str, report: str) -> tuple[bool, float, str]:
    # returns (is_grounded, score, reasoning)
    # is_grounded = score >= THRESHOLD

    # if there's no context at all, the report is ungrounded by definition
    if not context.strip():
        log_event(
            "output_validator",
            "block",
            reason="no context provided — report cannot be grounded",
            details={"score": 0.0, "threshold": THRESHOLD},
        )
        return False, 0.0, "no context provided"

    system = """You are a groundedness evaluator. Given a question, the retrieved context, and a generated report, score how well the report is grounded in the context.

Return ONLY a JSON object with this exact shape:
{"groundedness": <float 0.0-1.0>, "reasoning": "<one-sentence explanation>"}

Scoring guide:
- 1.0 = every claim in the report is directly supported by the context
- 0.7 = most claims supported, minor inferences acceptable
- 0.5 = mix of supported and unsupported claims
- 0.3 = many claims not in the context
- 0.0 = report mostly hallucinated / unrelated to context

No markdown. No extra text. Just the JSON object."""

    user = f"""Question:
{question}

Retrieved Context:
{context}

Generated Report:
{report}

Score the report's groundedness."""

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(raw)
        score = float(parsed.get("groundedness", 0.0))
        reasoning = parsed.get("reasoning", "")
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        # if judge returns garbage, fail open — log a warn, allow report through
        log_event(
            "output_validator",
            "warn",
            reason=f"judge returned non-parseable output: {raw[:150]}",
            details={"parse_error": str(e)},
        )
        return True, 0.5, "judge output unparseable — defaulted to pass"

    # clamp into [0, 1] in case the judge returns something silly
    score = max(0.0, min(1.0, score))

    is_grounded = score >= THRESHOLD
    event_type = "pass" if is_grounded else "block"

    log_event(
        "output_validator",
        event_type,
        reason=reasoning,
        details={
            "score": score,
            "threshold": THRESHOLD,
            "question_preview": question[:100],
        },
    )

    return is_grounded, score, reasoning