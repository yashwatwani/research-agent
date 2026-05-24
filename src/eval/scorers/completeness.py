# completeness.py — does the report cover what the question asked for?
# this catches the failure mode where the agent is relevant + grounded but
# only covers half of what the question actually asked.
#
# example: question = "What is X and why is it useful?"
# report = "X is Y." → relevant + grounded but only half the question = low completeness

from src.eval.scorers.base import call_judge


SYSTEM = """You are an evaluator scoring how completely a generated report addresses the question.

Return ONLY a JSON object with this exact shape:
{"score": <float 0.0-1.0>, "reasoning": "<one-sentence explanation>"}

Identify the key aspects implied by the question. A multi-part question ("what is X and why is it useful")
has multiple aspects. A simple question ("what is X") has one aspect.

Scoring guide:
- 1.0 = report covers all key aspects of the question thoroughly
- 0.7 = report covers most key aspects, minor gaps
- 0.5 = report covers about half of the key aspects
- 0.3 = report covers only one minor aspect
- 0.0 = report misses every key aspect of the question

Judge ONLY coverage breadth. Do NOT judge depth, correctness, or relevance separately.
No markdown. No extra text. Just the JSON object."""


def score(question: str, report: str) -> tuple[float, str]:
    user = f"""Question:
{question}

Generated Report:
{report}

Score the completeness of coverage."""

    return call_judge(SYSTEM, user)