import json
import psycopg2
import psycopg2.extras
from openai import OpenAI
from src.config import OPENAI_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMS, DATABASE_URL, CHUNK_SIZE, CHUNK_OVERLAP

client = OpenAI(api_key=OPENAI_API_KEY)


def get_connection():
    # opens a connection to Postgres
    return psycopg2.connect(DATABASE_URL)


def setup_table():
    # creates the chunks table if it doesn't exist
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS chunks (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            embedding vector({EMBEDDING_DIMS}),
            source_url TEXT,
            source_title TEXT,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Vector store table ready.")


def chunk_text(text: str) -> list[str]:
    # splits a long document into overlapping 300 word pieces
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + CHUNK_SIZE
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def embed_text(text: str) -> list[float]:
    # converts a piece of text into 1536 numbers(text-embedding-3-small) using OpenAI
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding


def store_document(text: str, source_url: str = "", source_title: str = "", metadata: dict = {}):
    # chunks a document, embeds each chunk, saves to pgvector
    chunks = chunk_text(text)
    conn = get_connection()
    cur = conn.cursor()

    stored = 0
    for chunk in chunks:
        embedding = embed_text(chunk)
        cur.execute("""
            INSERT INTO chunks (content, embedding, source_url, source_title, metadata)
            VALUES (%s, %s, %s, %s, %s)
        """, (chunk, embedding, source_url, source_title, json.dumps(metadata)))
        stored += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"Stored {stored} chunks from {source_title or source_url}")


def retrieve(query: str, top_k: int = 5) -> list[dict]:
    # embeds a query, finds closest chunks by cosine similarity, returns top K
    query_embedding = embed_text(query)
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT content, source_url, source_title, metadata,
               1 - (embedding <=> %s::vector) AS similarity
        FROM chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (query_embedding, query_embedding, top_k))

    results = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return results