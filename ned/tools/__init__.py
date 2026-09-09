"""Claude tools. Phase 0 has none that move anything; this module carries the conventions.

PROJECT.md, "Bodies": every motion and camera tool takes a ``body`` argument, an enum of known
body IDs with exactly one value until a second body exists. ``body_property`` builds that
schema fragment so no tool hand-writes it.
"""

from __future__ import annotations

from typing import Any


def body_property(bodies: list[str]) -> dict[str, Any]:
    if not bodies:
        raise ValueError("at least one body id is required")
    return {
        "type": "string",
        "enum": list(bodies),
        "description": "Which body performs this. Use the body you are talking through unless "
        "the request is about somewhere only another body can reach.",
    }


def tool_schema(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str],
    bodies: list[str] | None = None,
) -> dict[str, Any]:
    """Plain JSON-schema tool definition; convert with Pipecat's FunctionSchema at wiring time."""
    props = dict(properties)
    req = list(required)
    if bodies is not None:
        props["body"] = body_property(bodies)
        req.append("body")
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": props,
            "required": req,
            "additionalProperties": False,
        },
    }
