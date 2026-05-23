# tool_allowlist.py — soft allow-list for agent tool calls
# Phase 7: log violations only, do not block hard
#
# When the agent picks a tool name not in ALLOWED_TOOLS, we log it as a violation
# and return a friendly error message. We do NOT raise an exception — that would
# crash the agent loop. The agent can recover by trying a different approach.

from src.guardrails.logger import log_event

# extend this set whenever you add a new MCP tool
ALLOWED_TOOLS = {
    "search_web",
}


def check_tool(tool_name: str) -> tuple[bool, str]:
    # returns (is_allowed, reason)
    if tool_name in ALLOWED_TOOLS:
        log_event(
            "tool_allowlist",
            "pass",
            reason=f"tool '{tool_name}' is allowed",
            details={"tool_name": tool_name},
        )
        return True, ""

    log_event(
        "tool_allowlist",
        "violation",
        reason=f"unknown tool '{tool_name}' called",
        details={"tool_name": tool_name, "allowed": list(ALLOWED_TOOLS)},
    )
    return False, f"tool '{tool_name}' is not in the allow-list"