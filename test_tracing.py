from src.eval.tracer import init_tracing
from openai import OpenAI
from src.config import OPENAI_API_KEY, CHAT_MODEL

init_tracing()

client = OpenAI(api_key=OPENAI_API_KEY)

response = client.chat.completions.create(
    model=CHAT_MODEL,
    messages=[
        {"role": "system", "content": "You are a research assistant."},
        {"role": "user", "content": "What is RAG in AI? One sentence."}
    ]
)

print(response.choices[0].message.content)
print("\nNow open your browser and check the Phoenix UI to see the trace.")