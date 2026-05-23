# test_dedup.py — verifies Phase 7 dedup works at both layers
# inserts same source twice, asserts no duplicates in either vector or graph
#
# Usage:
#   python tests/test_dedup.py

import psycopg2
from src.config import DATABASE_URL
from src.memory.memory_manager import store_source

FAKE_URL = "https://test.example.com/dedup-test-article"
FAKE_TITLE = "Dedup Test Article"
FAKE_CONTENT = (
    "Transformers are a deep learning architecture introduced in 2017. "
    "They use self-attention to model dependencies in sequences. "
    "BERT and GPT are both built on the transformer architecture. "
    "Transformers replaced RNNs for most NLP tasks because they parallelise better. "
) * 10  # repeat to force chunk_text into producing multiple chunks


def cleanup():
    # remove test data from both tables so the test is repeatable
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("DELETE FROM chunks WHERE source_url = %s", (FAKE_URL,))
    cur.execute("DELETE FROM sources WHERE source_url = %s", (FAKE_URL,))
    cur.close()
    conn.close()


def main():
    print("=" * 60)
    print("Cleaning up any previous test data...")
    cleanup()

    print("\n--- First ingestion ---")
    result1 = store_source(
        text=FAKE_CONTENT,
        source_url=FAKE_URL,
        source_title=FAKE_TITLE,
    )
    first_inserted = result1["vector"]["chunks_inserted"]
    first_triples = len(result1["triples"])
    print(f"  → {first_inserted} chunks inserted, {first_triples} triples extracted")

    assert first_inserted > 0, "FAIL: first ingestion should insert chunks"
    print("  PASS: first ingestion stored new chunks")

    print("\n--- Second ingestion (identical content) ---")
    result2 = store_source(
        text=FAKE_CONTENT,
        source_url=FAKE_URL,
        source_title=FAKE_TITLE,
    )
    second_inserted = result2["vector"]["chunks_inserted"]
    second_skipped = result2["vector"]["chunks_skipped"]
    second_triples = len(result2["triples"])
    print(f"  → {second_inserted} chunks inserted, {second_skipped} skipped, {second_triples} triples")

    assert second_inserted == 0, (
        f"FAIL: second ingestion should insert 0 chunks, got {second_inserted}"
    )
    print("  PASS: vector dedup skipped all chunks")

    assert second_triples == 0, (
        f"FAIL: second ingestion should extract 0 triples (graph skipped), got {second_triples}"
    )
    print("  PASS: graph dedup skipped extraction")

    print("\n" + "=" * 60)
    print("All dedup checks passed.")
    print("=" * 60)

    print("\nCleaning up test data...")
    cleanup()


if __name__ == "__main__":
    main()