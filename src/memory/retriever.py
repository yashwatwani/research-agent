from openai import OpenAI
from src.config import OPENAI_API_KEY, CHAT_MODEL
from src.memory.vector_store import retrieve as vector_retrieve
from src.memory.graph_store import query_graph

client = OpenAI(api_key=OPENAI_API_KEY)


def classify_query(question: str) -> str:
    # sends question to gpt-4o, returns "graph" or "vector"
    
    prompt = f"""Classify this question as either 'graph' or 'vector'.

'graph' — relationship questions: who did what, which companies,
how are X and Y related, what does X make.

'vector' — concept questions: what is X, explain Y,
how does Z work, compare A and B.

Return ONLY the word 'graph' or 'vector', nothing else.

Question: {question}
Type:"""

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    result = response.choices[0].message.content.strip().lower()
    return "graph" if "graph" in result else "vector"


def retrieve(question: str, top_k: int = 5) -> dict:
    #classifies the question, calls the right retrieval path, returns results

    query_type = classify_query(question)
    print(f"Query router: {query_type}")

    if query_type == "graph":
        results = query_graph(question)
        return {"type": "graph", "results": results}
    else:
        results = vector_retrieve(question, top_k=top_k)
        return {"type": "vector", "results": results}