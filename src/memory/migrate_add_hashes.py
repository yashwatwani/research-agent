"""
One-time migration: add hash columns and sources table for dedup.

Run this once before deploying the dedup changes in Phase 7.

Usage:
    python scripts/migrate_add_hashes.py
"""

import hashlib
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def main():
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        with conn.cursor() as cur:
            print("Step 1/4: Adding content_hash column to chunks table...")
            cur.execute("""
                ALTER TABLE chunks
                ADD COLUMN IF NOT EXISTS content_hash TEXT;
            """)

            print("Step 2/4: Backfilling content_hash for existing rows...")
            cur.execute("SELECT id, content FROM chunks WHERE content_hash IS NULL;")
            rows = cur.fetchall()
            print(f"  Found {len(rows)} rows to backfill.")
            for row_id, content in rows:
                h = hashlib.sha256(content.encode("utf-8")).hexdigest()
                cur.execute(
                    "UPDATE chunks SET content_hash = %s WHERE id = %s;",
                    (h, row_id),
                )
            print(f"  Backfilled {len(rows)} rows.")

            print("Step 3/4: Adding UNIQUE index on content_hash...")
            # Use a unique index (not constraint) so we can use ON CONFLICT cleanly.
            # If duplicates already exist in the old data, this will fail —
            # we deduplicate them first.
            cur.execute("""
                DELETE FROM chunks a
                USING chunks b
                WHERE a.id > b.id
                  AND a.content_hash = b.content_hash;
            """)
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS chunks_content_hash_idx
                ON chunks (content_hash);
            """)

            print("Step 4/4: Creating sources table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sources (
                    id SERIAL PRIMARY KEY,
                    source_hash TEXT UNIQUE NOT NULL,
                    source_url TEXT,
                    source_title TEXT,
                    ingested_at TIMESTAMP DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS sources_url_idx ON sources (source_url);
            """)

            print("\nMigration complete.")


if __name__ == "__main__":
    main()