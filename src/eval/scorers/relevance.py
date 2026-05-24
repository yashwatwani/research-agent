# relevance.py — does the report actually answer the question asked?
# this catches the failure mode where the agent grounds claims well but rambles
# off-topic, or answers a related-but-different question.

from src.eval.scorers.base import call_judge


SYSTEM = """You are an evaluator scoring how relevant a generated report is to the question asked.

Return ONLY a JSON object with this exact shape:
{"score": <float 0.0-1.0>, "reasoning": "<one-sentence explanation>"}

Scoring guide:
- 1.0 = report directly and completely addresses what the question asked
- 0.7 = report addresses the question but with tangential material mixed in
- 0.5 = report is partially relevant, covers some adjacent topic
- 0.3 = report mostly addresses a different question
- 0.0 = report does not address the question at all

Judge the relevance of the answer to the question. Do NOT judge factual correctness here — only relevance.
No markdown. No extra text. Just the JSON object."""


def score(question: str, report: str) -> tuple[float, str]:
    user = f"""Question:
{question}

Generated Report:
{report}

Score the relevance of the report to the question."""

    return call_judge(SYSTEM, user)