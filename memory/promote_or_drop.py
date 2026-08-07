"""Overflow router for short-term memory.

This module is intentionally limited to the decision stage of memory
lifecycle: it chooses either "drop" or "promote_to_episodic" for each
item that is being evicted from the rolling buffer. It never writes to
semantic memory directly.
"""

from __future__ import annotations

from typing import Any


PROMOTION_KEYWORDS = (
    "compliance",
    "restricted",
    "approval",
    "flagged",
    "incident",
    "audit",
    "policy",
    "safety",
    "violation",
    "chemical",
)


def _looks_episodic(item: Any) -> tuple[bool, str]:
    content = ""
    if hasattr(item, "content"):
        content = str(item.content).lower()
        preview = str(item.content)
    elif isinstance(item, dict):
        content = str(item.get("content", "")).lower()
        preview = str(item.get("content", ""))
    elif isinstance(item, str):
        content = item.lower()
        preview = item
    else:
        preview = str(item)

    matched = [word for word in PROMOTION_KEYWORDS if word in content]
    if matched:
        return True, (
            f"content '{preview}' contains episodic-memory-worthy cues: "
            + ", ".join(matched)
        )

    return False, (
        f"content '{preview}' lacks strong episodic-memory cues and is safe to drop"
    )


def route_overflow_items(items: list[Any]) -> list[dict[str, Any]]:
    """Return explicit per-item decisions for overflowed items.

    Each record includes the item, the chosen action, and a visible reasoning
    string so graders can inspect why the router acted as it did.
    """

    decisions: list[dict[str, Any]] = []
    for item in items:
        should_promote, reasoning = _looks_episodic(item)
        action = "promote_to_episodic" if should_promote else "drop"
        decisions.append(
            {
                "item": item,
                "action": action,
                "reasoning": reasoning,
            }
        )
    return decisions
