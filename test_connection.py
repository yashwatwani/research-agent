from openai import OpenAI
from src.config import OPENAI_API_KEY, CHAT_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

def test_connection():
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": "You are a research assistant."},
            {"role": "user", "content": "In one sentence, what is RAG in AI?"}
        ]
    )
    print(response.choices[0].message.content)

if __name__ == "__main__":
    test_connection()