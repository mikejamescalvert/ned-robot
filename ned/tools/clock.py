"""``get_time``: the first tool. Exists to exercise the tool-calling path end to end.

Time is a volatile fact, so it does not live in the cached system prompt (PROJECT.md, "Latency
is the product"). Ned calls this when asked, the same way it will call ``drive_to`` later.
No ``body`` argument: the clock is not a motion or camera tool, and both bodies share a house.
"""

from __future__ import annotations

from datetime import datetime

from ned.tools import tool_schema

NAME = "get_time"
DESCRIPTION = (
    "Current local date and time where Ned is. Call this whenever the person asks the time, "
    "the date, or the day of the week; do not guess."
)


def now_facts(now: datetime | None = None) -> dict[str, str]:
    """Spoken-friendly clock facts. Pure, so it is unit tested without Pipecat."""
    dt = now or datetime.now()
    if dt.tzinfo is None:
        dt = dt.astimezone()  # attach the Pi's local zone
    hour12 = dt.hour % 12 or 12
    return {
        "time": f"{hour12}:{dt.minute:02d} {'AM' if dt.hour < 12 else 'PM'}",
        "weekday": dt.strftime("%A"),
        "date": f"{dt.strftime('%B')} {dt.day}, {dt.year}",
        "timezone": dt.tzname() or "local",
        "iso": dt.isoformat(timespec="minutes"),
    }


SCHEMA = tool_schema(NAME, DESCRIPTION, properties={}, required=[])


def function_schema():
    """Pipecat FunctionSchema with the handler attached; the LLM service registers it."""
    from pipecat.adapters.schemas.function_schema import FunctionSchema
    from pipecat.services.llm_service import FunctionCallParams

    async def handler(params: FunctionCallParams) -> None:
        await params.result_callback(now_facts())

    return FunctionSchema(
        name=NAME,
        description=DESCRIPTION,
        properties=SCHEMA["input_schema"]["properties"],
        required=SCHEMA["input_schema"]["required"],
        handler=handler,
    )
