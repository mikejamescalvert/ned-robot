from ned.telemetry import TurnTracker, llm_cost_usd, summarize


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def test_cost_math_uses_cached_rates():
    # 1000 prompt tokens of which 800 cache-read, 100 completion, on Opus 5
    usd = llm_cost_usd("claude-opus-5", 1000, 100, cache_read=800)
    expected = (200 * 5.0 + 100 * 25.0 + 800 * 0.5) / 1e6
    assert abs(usd - expected) < 1e-12


def test_unknown_model_costs_zero():
    assert llm_cost_usd("mystery", 10, 10) == 0.0


def test_turn_record_latencies_and_cost():
    clock = Clock()
    out = []
    t = TurnTracker("claude-opus-5", out.append, clock=clock)
    t.user_stopped()
    clock.t += 0.4
    t.first_token()
    clock.t += 0.1
    t.llm_done()
    clock.t += 0.1
    t.first_tts_audio()
    clock.t += 0.1
    t.bot_started()
    t.llm_usage(prompt=1200, completion=60, cache_read=1000)
    t.tts_usage(80)
    t.ttfb("AnthropicLLMService", 0.41)
    t.bot_stopped()
    assert len(out) == 1
    r = out[0]
    assert r["speech_to_first_token"] == 400
    assert r["speech_to_llm_done"] == 500
    assert r["speech_to_first_tts_audio"] == 600
    assert r["speech_to_first_sound"] == 700
    assert r["tokens"]["cache_read"] == 1000
    assert r["tts_chars"] == 80
    assert r["ttfb_ms"]["AnthropicLLMService"] == 410
    assert r["cost_usd"] > 0
    assert r["session_cost_usd"] == r["cost_usd"]
    assert t.turn is None


def test_events_without_a_turn_are_ignored():
    t = TurnTracker("claude-opus-5", lambda r: (_ for _ in ()).throw(AssertionError("no")))
    t.first_token()
    t.bot_stopped()  # nothing to flush, sink must not be called


def test_summarize_medians():
    recs = [
        {"speech_to_first_sound": 900, "cost_usd": 0.01, "ttfb_ms": {"Anthropic": 500}},
        {"speech_to_first_sound": 1100, "cost_usd": 0.02, "ttfb_ms": {"Anthropic": 700}},
        {"speech_to_first_sound": None, "cost_usd": 0.0},  # abandoned turn, no ttfb dict
    ]
    s = summarize(recs)
    assert s["turns"] == 3
    assert s["speech_to_first_sound_p50_ms"] == 1000
    assert s["cost_usd"] == 0.03
    assert s["cost_per_turn_usd"] == 0.01
    assert s["ttfb_p50_ms"] == {"Anthropic": 600}
    assert s["completion_tokens_p50"] is None


def test_summarize_empty():
    assert summarize([])["turns"] == 0
