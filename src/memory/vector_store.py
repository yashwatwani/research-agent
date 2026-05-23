import json
import hashlib
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
    # Phase 7: content_hash column added via scripts/migrate_add_hashes.py
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS chunks (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            content_hash TEXT,
            embedding vector({EMBEDDING_DIMS}),
            source_url TEXT,
            source_title TEXT,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS chunks_content_hash_idx
        ON chunks (content_hash)
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Vector store table ready.")


def _hash(text: str) -> str:
    # Phase 7: SHA-256 hex of UTF-8 text, used for chunk-level dedup
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
    # Phase 7: chunk-level dedup via SHA-256 content_hash
    # for each chunk: hash first, check if exists, skip embedding+insert if so
    # returns dict with attempted/inserted/skipped counts so the caller can log
    chunks = chunk_text(text)
    conn = get_connection()
    cur = conn.cursor()

    attempted = len(chunks)
    inserted = 0

    for chunk in chunks:
        content_hash = _hash(chunk)

        # pre-check: skip embedding entirely if we've seen this chunk before
        # this is the cost-saver — embedding API costs money per call
        cur.execute(
            "SELECT 1 FROM chunks WHERE content_hash = %s LIMIT 1",
            (content_hash,)
        )
        if cur.fetchone() is not None:
            continue

        embedding = embed_text(chunk)
        # ON CONFLICT is the atomic safety net — handles race conditions
        # where two processes might insert the same hash simultaneously
        cur.execute("""
            INSERT INTO chunks (content, content_hash, embedding, source_url, source_title, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (content_hash) DO NOTHING
        """, (chunk, content_hash, embedding, source_url, source_title, json.dumps(metadata)))

        if cur.rowcount > 0:
            inserted += 1

    conn.commit()
    cur.close()
    conn.close()

    skipped = attempted - inserted
    print(f"Stored {inserted} new chunks, skipped {skipped} duplicates from {source_title or source_url}")

    return {
        "chunks_attempted": attempted,
        "chunks_inserted": inserted,
        "chunks_skipped": skipped,
    }


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