# logger.py — dual sink for guardrail events
# writes to data/logs/guardrails.jsonl AND emits OpenTelemetry span for Phoenix
#
# Every guardrail (input_filter, tool_allowlist, output_validator) calls
# log_event() so we have a single audit trail no matter which one fired.

import json
import os
from datetime import datetime
from opentelemetry import trace

LOG_PATH = "data/logs/guardrails.jsonl"

# get a tracer — Phoenix is already running via src/eval/tracer.py
# so spans emitted here will show up in the Phoenix UI under their own service name
_tracer = trace.get_tracer("research-agent.guardrails")


def log_event(
    guardrail: str,         # "input_filter" | "tool_allowlist" | "output_validator"
    event_type: str,        # "pass" | "block" | "violation" | "warn"
    reason: str = "",
    details: dict = None,
):
    # ensure log folder exists
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    record = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "guardrail": guardrail,
        "event_type": event_type,
        "reason": reason,
        "details": details or {},
    }

    # sink 1: JSONL file — one line per event, grep-friendly
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")

    # sink 2: Phoenix trace — emit a span so it shows up alongside agent traces
    with _tracer.start_as_current_span(f"guardrail.{guardrail}") as span:
        span.set_attribute("guardrail.name", guardrail)
        span.set_attribute("guardrail.event_type", event_type)
        span.set_attribute("guardrail.reason", reason)
        # details get flattened into span attributes for searchability in Phoenix
        for k, v in (details or {}).items():
            # span attributes only accept primitives — coerce to str if complex
            if isinstance(v, (str, bool, int, float)):
                span.set_attribute(f"guardrail.details.{k}", v)
            else:
                span.set_attribute(f"guardrail.details.{k}", str(v))

    # also print to console so you see it live during dev
    print(f"[GUARDRAIL/{guardrail}] {event_type}: {reason}")