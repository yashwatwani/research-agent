# groundedness.py — are the claims in the report supported by the retrieved context?
# same scoring criterion as src/guardrails/output_validator.py — kept separate here
# because the eval suite has different concerns (no threshold, no blocking, just a score)
#
# if you change the groundedness criterion later, change BOTH this and output_validator
# to keep online/offline scoring aligned.

from src.eval.scorers.base import call_judge


SYSTEM = """You are an evaluator scoring how well a generated report is grounded in the provided context.

Return ONLY a JSON object with this exact shape:
{"score": <float 0.0-1.0>, "reasoning": "<one-sentence explanation>"}

Scoring guide:
- 1.0 = every claim in the report is directly supported by the context
- 0.7 = most claims supported, minor inferences acceptable
- 0.5 = mix of supported and unsupported claims
- 0.3 = many claims not present in the context (likely hallucinated)
- 0.0 = report mostly invented / unrelated to context

Judge ONLY whether claims appear in the context. Do NOT judge whether the claims are factually true in the wider world.
No markdown. No extra text. Just the JSON object."""


def score(question: str, context: str, report: str) -> tuple[float, str]:
    if not context.strip():
        # no context to ground against — by definition score is 0
        return 0.0, "no retrieved context — report cannot be grounded"

    user = f"""Question:
{question}

Retrieved Context:
{context}

Generated Report:
{report}

Score the groundedness of the report against the context."""

    return call_judge(SYSTEM, user)