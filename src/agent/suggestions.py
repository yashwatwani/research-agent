# src/agent/suggestions.py — generates alternative research questions
# called when the input filter blocks a question
# returns 2-3 research-style alternatives based on the original question topic
# uses gpt-4o-mini (cheap — this runs on every block)

import json
from openai import OpenAI
from src.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def get_suggestions(question: str) -> list[str]:
    # takes a blocked question, returns 2-3 research-style alternatives
    # fails silently — returns empty list if the call fails

    system = """You are helping a user understand what kinds of questions a research agent can answer.

The agent is built for deep research questions — topics like AI, technology, science,
geopolitics, history, current events, and factual analysis. It is NOT for simple lookups,
trivia, personal advice, creative writing, or casual conversation.

Given a question that was rejected, suggest 2-3 research-style questions on the same
general topic that the agent WOULD be able to answer well.

Return ONLY a JSON array of strings. No explanation, no markdown, no extra text.
Example: ["How did X influence Y?", "What are the key debates around X?"]"""

    user = f"Rejected question: {question}\n\nSuggest 2-3 research questions on this topic."

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,    # slight warmth for variety in suggestions
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        suggestions = json.loads(raw)
        return suggestions if isinstance(suggestions, list) else []
    except Exception:
        return []