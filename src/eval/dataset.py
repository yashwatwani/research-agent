# dataset.py — test set for the evaluation suite
# Mix of generic AI/ML and project-domain questions.
# Tagged by category so we can analyse performance per category later.
#
# Add or remove questions here. The runner picks up whatever EVAL_DATASET contains.

EVAL_DATASET = [
    # --- Generic concepts (testing memory + synthesis on textbook topics) ---
    {
        "id": "gen-001",
        "category": "concept",
        "question": "What is a transformer architecture in deep learning?",
    },
    {
        "id": "gen-002",
        "category": "concept",
        "question": "How does cosine similarity work in vector search?",
    },
    {
        "id": "gen-003",
        "category": "concept",
        "question": "What is the difference between RAG and fine-tuning?",
    },
    {
        "id": "gen-004",
        "category": "concept",
        "question": "Why are embeddings useful for semantic search?",
    },

    # --- Project domain (MCP, pgvector, agent frameworks) ---
    {
        "id": "dom-001",
        "category": "domain",
        "question": "What is the Model Context Protocol and why was it introduced?",
    },
    {
        "id": "dom-002",
        "category": "domain",
        "question": "What is pgvector and how does it integrate with PostgreSQL?",
    },
    {
        "id": "dom-003",
        "category": "domain",
        "question": "What is Arize Phoenix used for in LLM applications?",
    },
    {
        "id": "dom-004",
        "category": "domain",
        "question": "What does NetworkX do and when would you use it for graph storage?",
    },

    # --- Comparison questions (tests synthesis across multiple sources) ---
    {
        "id": "cmp-001",
        "category": "comparison",
        "question": "How does Graph RAG differ from standard vector RAG?",
    },
    {
        "id": "cmp-002",
        "category": "comparison",
        "question": "What are the tradeoffs between using gpt-4o and gpt-4o-mini for agent tasks?",
    },

    # --- Relationship / Graph-route questions ---
    {
        "id": "rel-001",
        "category": "relationship",
        "question": "Which companies have adopted the Model Context Protocol?",
    },
    {
        "id": "rel-002",
        "category": "relationship",
        "question": "What tools are commonly used in modern LLM observability stacks?",
    },

    # --- Recent / current info (tests web search path) ---
    {
        "id": "cur-001",
        "category": "current",
        "question": "What are the latest developments in retrieval-augmented generation in 2026?",
    },

    # --- Edge cases (tests guardrails + graceful failure) ---
    {
        "id": "edge-001",
        "category": "edge",
        "question": "What is the capital of France?",  # out-of-scope-ish; tests filter or fallback
    },
    {
        "id": "edge-002",
        "category": "edge",
        "question": "Explain how prompt engineering affects agent quality in research workflows.",
    },
]


def get_dataset() -> list[dict]:
    """Returns the full eval dataset."""
    return EVAL_DATASET


def get_by_category(category: str) -> list[dict]:
    """Filter dataset by category — useful for running subset evals."""
    return [q for q in EVAL_DATASET if q["category"] == category]