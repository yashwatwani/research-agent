Phase 7: dedup + guardrails

Dedup:
- SHA-256 content hashing at chunk and source level
- Pre-check before embedding to avoid wasted OpenAI calls
- UNIQUE index on content_hash as atomic safety net
- New sources table for source-level dedup tracking
- One-time migration script in scripts/

Guardrails (soft enforcement, log-only on violations):
- Two-stage input filter (regex + gpt-4o-mini classifier)
- Soft tool allow-list with violation logging
- LLM-as-judge output validator (groundedness, threshold 0.5)
- Dual logging: JSONL audit trail + Phoenix OTel spans

Wiring:
- input_filter_node added as first gate in run_agent
- output_validator_node added as last gate after synthesise
- AgentState extended with blocked, block_reason, groundedness_score, context_text

Tests:
- test_dedup.py covers both source-level and chunk-level dedup
- test_guardrails.py covers all three guardrails + end-to-end agent flow