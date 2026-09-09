"""Per-turn latency and cost log. PROJECT.md: "Latency is the product" and "Cost visibility".

One JSON line per turn in ``<log_dir>/turns.jsonl``:
  end of speech -> first LLM token -> first TTS audio -> first sound out, plus tokens and an
  estimated dollar cost for the turn. ``TurnTracker`` is pure and unit-tested; ``build_processor``
  wraps it as a Pipecat processor.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

# USD per million tokens. Update when the price list changes; keep the model id exact.
PRICES: dict[str, dict[str, float]] = {
    "claude-opus-5": {"input": 5.0, "output": 25.0, "cache_read": 0.5, "cache_write": 6.25},
    "claude-sonnet-5": {"input": 2.0, "output": 10.0, "cache_read": 0.2, "cache_write": 2.5},
}


def llm_cost_usd(
    model: str, prompt: int, completion: int, cache_read: int = 0, cache_write: int = 0
) -> float:
    p = PRICES.get(model)
    if p is None:
        return 0.0
    uncached = max(prompt - cache_read - cache_write, 0)
    return (
        uncached * p["input"]
        + completion * p["output"]
        + cache_read * p["cache_read"]
        + cache_write * p["cache_write"]
    ) / 1_000_000


@dataclass
class Turn:
    started: float
    end_of_speech: float | None = None
    first_token: float | None = None
    llm_done: float | None = None
    first_tts_audio: float | None = None
    first_sound: float | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    tts_chars: int = 0
    cost_usd: float = 0.0
    ttfb: dict[str, float] = field(default_factory=dict)

    def latencies_ms(self) -> dict[str, int | None]:
        def d(a, b):
            return None if a is None or b is None else round((b - a) * 1000)

        return {
            "speech_to_first_token": d(self.end_of_speech, self.first_token),
            "speech_to_llm_done": d(self.end_of_speech, self.llm_done),
            "speech_to_first_tts_audio": d(self.end_of_speech, self.first_tts_audio),
            "speech_to_first_sound": d(self.end_of_speech, self.first_sound),
        }


class TurnTracker:
    def __init__(self, model: str, sink: Callable[[dict], None], clock=time.monotonic):
        self.model = model
        self.sink = sink
        self.clock = clock
        self.turn: Turn | None = None
        self.session_cost_usd = 0.0

    def user_stopped(self):
        self.turn = Turn(started=self.clock(), end_of_speech=self.clock())

    def first_token(self):
        if self.turn and self.turn.first_token is None:
            self.turn.first_token = self.clock()

    def llm_done(self):
        if self.turn and self.turn.llm_done is None:
            self.turn.llm_done = self.clock()

    def first_tts_audio(self):
        if self.turn and self.turn.first_tts_audio is None:
            self.turn.first_tts_audio = self.clock()

    def bot_started(self):
        if self.turn and self.turn.first_sound is None:
            self.turn.first_sound = self.clock()

    def ttfb(self, processor: str, seconds: float):
        if self.turn:
            self.turn.ttfb[processor] = round(seconds * 1000)

    def llm_usage(self, prompt: int, completion: int, cache_read: int = 0, cache_write: int = 0):
        if not self.turn:
            return
        t = self.turn
        t.prompt_tokens += prompt
        t.completion_tokens += completion
        t.cache_read_tokens += cache_read
        t.cache_write_tokens += cache_write
        t.cost_usd += llm_cost_usd(self.model, prompt, completion, cache_read, cache_write)

    def tts_usage(self, chars: int):
        if self.turn:
            self.turn.tts_chars += chars

    def bot_stopped(self):
        """End of Ned's reply: flush the turn."""
        if not self.turn:
            return
        t = self.turn
        self.session_cost_usd += t.cost_usd
        record = {
            "ts": time.time(),
            "model": self.model,
            **t.latencies_ms(),
            "ttfb_ms": t.ttfb,
            "tokens": {
                "prompt": t.prompt_tokens,
                "completion": t.completion_tokens,
                "cache_read": t.cache_read_tokens,
                "cache_write": t.cache_write_tokens,
            },
            "tts_chars": t.tts_chars,
            "cost_usd": round(t.cost_usd, 6),
            "session_cost_usd": round(self.session_cost_usd, 6),
        }
        self.sink(record)
        self.turn = None


def jsonl_sink(log_dir: Path) -> Callable[[dict], None]:
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "turns.jsonl"

    def write(record: dict) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    return write


def build_processor(tracker: TurnTracker):
    """Pipecat processor that feeds the tracker from pipeline frames. Passes everything through."""
    from loguru import logger
    from pipecat.frames.frames import (
        BotStartedSpeakingFrame,
        BotStoppedSpeakingFrame,
        Frame,
        LLMFullResponseEndFrame,
        LLMTextFrame,
        MetricsFrame,
        TTSStartedFrame,
        UserStoppedSpeakingFrame,
    )
    from pipecat.metrics.metrics import LLMUsageMetricsData, TTFBMetricsData, TTSUsageMetricsData
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

    class TurnMetrics(FrameProcessor):
        def __init__(self):
            super().__init__(name="TurnMetrics")

        async def process_frame(self, frame: Frame, direction: FrameDirection):
            await super().process_frame(frame, direction)
            if isinstance(frame, UserStoppedSpeakingFrame):
                tracker.user_stopped()
            elif isinstance(frame, LLMTextFrame):
                # Not LLMFullResponseStartFrame: that fires when the request is *sent*, which
                # read as a 1 ms "first token" on hardware. The first text frame is the first
                # token actually back from the model.
                tracker.first_token()
            elif isinstance(frame, LLMFullResponseEndFrame):
                tracker.llm_done()
            elif isinstance(frame, TTSStartedFrame):
                tracker.first_tts_audio()
            elif isinstance(frame, BotStartedSpeakingFrame):
                tracker.bot_started()
            elif isinstance(frame, BotStoppedSpeakingFrame):
                tracker.bot_stopped()
                if tracker.turn is None:
                    logger.info(f"turn logged; session cost ${tracker.session_cost_usd:.4f}")
            elif isinstance(frame, MetricsFrame):
                for m in frame.data:
                    if isinstance(m, TTFBMetricsData):
                        tracker.ttfb(m.processor, m.value)
                    elif isinstance(m, LLMUsageMetricsData):
                        u = m.value
                        tracker.llm_usage(
                            u.prompt_tokens,
                            u.completion_tokens,
                            u.cache_read_input_tokens or 0,
                            u.cache_creation_input_tokens or 0,
                        )
                    elif isinstance(m, TTSUsageMetricsData):
                        tracker.tts_usage(int(m.value))
            await self.push_frame(frame, direction)

    return TurnMetrics()


def summarize(records: list[dict]) -> dict:
    """Roll up turn records for `ned-agent stats`: medians per stage, per-service TTFB, cost.

    The stage medians answer "how far from the 1.5 s target". The TTFB medians say which
    vendor to blame: each is the time that service waited on its API for the first byte.
    """
    import statistics

    def p50(vals):
        return int(statistics.median(vals)) if vals else None

    out: dict = {
        "turns": len(records),
        "cost_usd": round(sum(r.get("cost_usd", 0) for r in records), 4),
        "cost_per_turn_usd": round(sum(r.get("cost_usd", 0) for r in records) / len(records), 4)
        if records
        else 0.0,
    }
    for key in (
        "speech_to_first_token",
        "speech_to_llm_done",
        "speech_to_first_tts_audio",
        "speech_to_first_sound",
    ):
        out[f"{key}_p50_ms"] = p50([r[key] for r in records if r.get(key) is not None])
    services = sorted({k for r in records for k in (r.get("ttfb_ms") or {})})
    out["ttfb_p50_ms"] = {
        svc: p50([r["ttfb_ms"][svc] for r in records if svc in (r.get("ttfb_ms") or {})])
        for svc in services
    }
    out["completion_tokens_p50"] = p50(
        [r["tokens"]["completion"] for r in records if r.get("tokens")]
    )
    return out
