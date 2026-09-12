import struct
from pathlib import Path

from ned.audio.chime import SLEEP_TONES, WAKE_TONES, chime, tone
from ned.audio.wake import WakeGate, score_meter


class FakeDetector:
    def __init__(self, scores):
        self.scores = list(scores)
        self.resets = 0

    def score(self, pcm16: bytes) -> float:
        return self.scores.pop(0) if self.scores else 0.0

    def reset(self) -> None:
        self.resets += 1


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def make(scores, **kw):
    clock = Clock()
    gate = WakeGate(detector=FakeDetector(scores), clock=clock, **kw)
    return gate, clock


def test_asleep_drops_audio_and_needs_consecutive_hits():
    gate, _ = make([0.9, 0.1, 0.9, 0.9], threshold=0.5, consecutive_frames=2)
    assert gate.feed(b"x") is False  # one hit, not enough
    assert gate.feed(b"x") is False  # miss resets
    assert gate.feed(b"x") is False  # hit 1
    assert gate.feed(b"x") is True  # hit 2: awake, this chunk passes
    assert gate.awake


def test_follow_up_window_then_sleep():
    gate, clock = make([0.9, 0.9], consecutive_frames=2, follow_up_secs=8)
    gate.feed(b"x")
    gate.feed(b"x")
    assert gate.awake
    clock.t = 5
    assert gate.feed(b"x") is True
    clock.t = 9
    assert gate.feed(b"x") is False
    assert not gate.awake


def test_activity_keeps_it_awake():
    gate, clock = make([0.9, 0.9], consecutive_frames=2, follow_up_secs=8)
    gate.feed(b"x")
    gate.feed(b"x")
    gate.activity(True)  # user talking
    clock.t = 60
    assert gate.feed(b"x") is True  # busy: never times out mid-speech
    gate.activity(False)
    clock.t = 65
    assert gate.feed(b"x") is True  # inside follow-up window measured from activity
    clock.t = 70
    assert gate.feed(b"x") is False


def test_mute_file_forces_sleep(tmp_path: Path):
    mute = tmp_path / "mute"
    gate, _ = make([0.9, 0.9, 0.9, 0.9], consecutive_frames=2, mute_file=mute)
    gate.feed(b"x")
    gate.feed(b"x")
    assert gate.awake
    mute.touch()
    assert gate.feed(b"x") is False
    assert not gate.awake
    assert gate.feed(b"x") is False  # still muted: detector is not even consulted
    assert len(gate.detector.scores) == 2


def test_callbacks_fire():
    gate, clock = make([0.9], consecutive_frames=1, follow_up_secs=1)
    events = []
    gate.on_wake.append(lambda: events.append("wake"))
    gate.on_sleep.append(lambda: events.append("sleep"))
    gate.feed(b"x")
    clock.t = 5
    gate.feed(b"x")
    assert events == ["wake", "sleep"]


def test_sleep_resets_detector_and_refractory_blocks_immediate_rewake():
    # The bug seen on the Pi: after sleeping, the phrase still in the detector's buffer
    # scored high on the next frame and woke it again, every follow-up window.
    gate, clock = make(
        [0.9, 0.9, 0.9, 0.9, 0.9], consecutive_frames=1, follow_up_secs=8, refractory_secs=1.0
    )
    assert gate.feed(b"x") is True
    assert gate.detector.resets == 1  # reset on wake
    clock.t = 9
    assert gate.feed(b"x") is False  # follow-up expired: sleep
    assert gate.detector.resets == 2  # reset on sleep
    assert gate.feed(b"x") is False  # still inside refractory: high score ignored
    clock.t = 10.5
    assert gate.feed(b"x") is True  # refractory over: a real detection wakes it again


def test_last_score_is_exposed_for_logging():
    gate, _ = make([0.2, 0.7], threshold=0.5, consecutive_frames=1)
    gate.feed(b"x")
    assert gate.last_score == 0.2
    gate.feed(b"x")
    assert gate.last_score == 0.7
    assert gate.awake


def test_score_meter_prints_peak_per_line_and_flags_wakes():
    lines = []
    det = FakeDetector([0.1, 0.3, 0.05, 0.9, 0.2, 0.0])
    score_meter(det, [b"x"] * 6, threshold=0.5, frames_per_line=3, out=lines.append)
    assert len(lines) == 2
    assert lines[0].startswith(" 0.30 |") and "WAKE" not in lines[0]
    assert lines[1].startswith(" 0.90 |") and lines[1].endswith("WAKE")


def test_tone_is_pcm16_of_the_right_length_and_starts_quiet():
    pcm = tone(440.0, 0.05, 16000)
    assert len(pcm) == int(16000 * 0.05) * 2  # 16-bit mono
    first, last = struct.unpack("<h", pcm[:2])[0], struct.unpack("<h", pcm[-2:])[0]
    assert abs(first) < 100 and abs(last) < 100  # faded in and out: no click
    assert max(abs(v) for v in struct.unpack(f"<{len(pcm) // 2}h", pcm)) > 1000


def test_wake_and_sleep_chimes_differ_and_are_short():
    w, s = chime(WAKE_TONES, 16000), chime(SLEEP_TONES, 16000)
    assert w != s
    assert len(w) / 2 / 16000 < 0.25  # under a quarter second
