from pathlib import Path

from ned.audio.wake import WakeGate


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
