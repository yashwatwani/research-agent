# base.py — shared judge call used by all three scorers
# every scorer (relevance, groundedness, completeness) sends a prompt to gpt-4o,
# expects back a JSON {"score": float, "reasoning": str}, and clamps to [0, 1]
#
# centralised here so we change the model, retry logic, or temperature once

import json
from openai import OpenAI
from src.config import OPENAI_API_KEY, CHAT_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)


def call_judge(system_prompt: str, user_prompt: str) -> tuple[float, str]:
    # sends prompts to gpt-4o, parses JSON response, returns (score, reasoning)
    # fails open on parse errors — returns (0.0, error_message) so the eval keeps running

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(raw)
        score = float(parsed.get("score", 0.0))
        reasoning = parsed.get("reasoning", "")
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        # don't crash the whole eval run on one bad parse — log and return 0
        return 0.0, f"judge output unparseable: {raw[:150]}"

    # clamp to [0, 1] in case the judge returns 1.5 or -0.3
    score = max(0.0, min(1.0, score))
    return score, reasoning