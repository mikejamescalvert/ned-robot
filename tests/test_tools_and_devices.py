import pytest

from ned.audio.devices import pick_device
from ned.memory import InMemory
from ned.tools import body_property, tool_schema
from ned.tools.clock import SCHEMA, now_facts


def test_pick_device_by_name_case_insensitive():
    devs = [(0, "bcm2835 Headphones"), (1, "reSpeaker XVF3800 4-Mic Array: USB Audio")]
    assert pick_device(devs, "array") == 1
    assert pick_device(devs, "Array") == 1
    assert pick_device(devs, "nope") is None


def test_tool_schema_adds_body_enum():
    s = tool_schema(
        "drive_to", "Drive somewhere.", {"place": {"type": "string"}}, ["place"], bodies=["office"]
    )
    props = s["input_schema"]["properties"]
    assert props["body"]["enum"] == ["office"]
    assert s["input_schema"]["required"] == ["place", "body"]
    assert s["input_schema"]["additionalProperties"] is False


def test_tool_schema_without_body_is_plain():
    s = tool_schema("get_time", "Tell the time.", {}, [])
    assert "body" not in s["input_schema"]["properties"]


def test_body_property_requires_a_body():
    with pytest.raises(ValueError):
        body_property([])


def test_memory_dedupes_and_recalls_latest():
    m = InMemory()
    m.remember("desk is by the window")
    m.remember("desk is by the window")
    m.remember("  coffee at 9 ")
    assert m.recall() == ["desk is by the window", "coffee at 9"]
    assert m.recall(limit=1) == ["coffee at 9"]


def test_clock_facts_are_spoken_friendly():
    from datetime import datetime, timedelta, timezone

    tz = timezone(timedelta(hours=-4), "EDT")
    f = now_facts(datetime(2026, 9, 10, 0, 5, tzinfo=tz))
    assert f["time"] == "12:05 AM"
    assert f["weekday"] == "Thursday"
    assert f["date"] == "September 10, 2026"
    assert f["timezone"] == "EDT"
    f = now_facts(datetime(2026, 9, 10, 13, 30, tzinfo=tz))
    assert f["time"] == "1:30 PM"


def test_clock_schema_takes_no_arguments():
    assert SCHEMA["name"] == "get_time"
    assert SCHEMA["input_schema"]["properties"] == {}
    assert SCHEMA["input_schema"]["required"] == []
