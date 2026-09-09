"""Wake word gate.

Sits between the microphone and speech-to-text. While ASLEEP it drops audio on the floor and
only feeds the local wake word detector, so nothing is streamed to a cloud STT vendor and
nothing is billed. On "Hey Ned" it opens, stays open while a conversation is happening, and
closes again after ``follow_up_secs`` of quiet. A mute file (touch /etc/ned/mute) keeps it
closed no matter what, for client calls.

The gate is a plain state machine (``WakeGate``) with an injectable detector so it can be unit
tested without audio hardware or openWakeWord. ``WakeGateProcessor`` is the Pipecat wrapper.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np


class Detector(Protocol):
    """Anything that scores a chunk of 16 kHz int16 audio for the wake word."""

    def score(self, pcm16: bytes) -> float: ...

    def reset(self) -> None:
        """Forget buffered audio and scores. Called on every wake and sleep transition."""
        ...


@dataclass
class WakeGate:
    detector: Detector
    threshold: float = 0.5
    consecutive_frames: int = 2
    follow_up_secs: float = 8.0
    refractory_secs: float = 1.0  # after sleeping, ignore detections this long
    mute_file: Path | None = None
    clock: Callable[[], float] = time.monotonic

    awake: bool = False
    _hits: int = 0
    _last_activity: float = 0.0
    _slept_at: float = -1e9
    _busy: bool = False  # user or bot currently speaking
    on_wake: list[Callable[[], None]] = field(default_factory=list)
    on_sleep: list[Callable[[], None]] = field(default_factory=list)

    def muted(self) -> bool:
        return bool(self.mute_file and self.mute_file.exists())

    def feed(self, pcm16: bytes) -> bool:
        """Feed one audio chunk. Returns True if the chunk should pass downstream."""
        if self.muted():
            if self.awake:
                self._sleep()
            return False
        if self.awake:
            if not self._busy and self.clock() - self._last_activity > self.follow_up_secs:
                self._sleep()
                return False
            return True
        score = self.detector.score(pcm16)
        if self.clock() - self._slept_at < self.refractory_secs:
            self._hits = 0  # detector still warming up on fresh audio; ignore
            return False
        if score >= self.threshold:
            self._hits += 1
            if self._hits >= self.consecutive_frames:
                self._wake()
                return True
        else:
            self._hits = 0
        return False

    def activity(self, busy: bool) -> None:
        """Call with True when the user or Ned starts speaking, False when they stop."""
        self._busy = busy
        self._last_activity = self.clock()

    def _wake(self) -> None:
        self.awake = True
        self._hits = 0
        self._last_activity = self.clock()
        self._reset_detector()
        for cb in self.on_wake:
            cb()

    def _sleep(self) -> None:
        self.awake = False
        self._hits = 0
        self._busy = False
        self._slept_at = self.clock()
        self._reset_detector()  # or the phrase that woke us is still in its buffer
        for cb in self.on_sleep:
            cb()

    def _reset_detector(self) -> None:
        reset = getattr(self.detector, "reset", None)
        if callable(reset):
            reset()


class OpenWakeWordDetector:
    """openWakeWord wrapper. Buffers to 80 ms frames (1280 samples at 16 kHz) as the model wants.

    Only imported on the Pi; openWakeWord is in the ``pi`` extra. Use the ONNX backend, the
    tflite path has dependency problems on Python 3.12.
    """

    FRAME_SAMPLES = 1280

    def __init__(self, model_path: Path, keyword: str | None = None):
        from openwakeword.model import Model  # local import: pi extra only
        from openwakeword.utils import download_models

        if not Path(model_path).exists():
            raise FileNotFoundError(
                f"wake word model not found at {model_path}; see docs/wakeword.md"
            )
        # The package does not ship the shared melspectrogram/embedding models; this fetches
        # them once into the package directory and is a no-op afterwards. Empty list means
        # "feature models only", not the stock wake words.
        download_models(model_names=[])
        self._model = Model(wakeword_models=[str(model_path)], inference_framework="onnx")
        self._keyword = keyword or Path(model_path).stem
        self._buf = np.zeros(0, dtype=np.int16)
        self._last = 0.0

    def reset(self) -> None:
        self._model.reset()
        self._buf = np.zeros(0, dtype=np.int16)
        self._last = 0.0

    def score(self, pcm16: bytes) -> float:
        self._buf = np.concatenate([self._buf, np.frombuffer(pcm16, dtype=np.int16)])
        while len(self._buf) >= self.FRAME_SAMPLES:
            frame, self._buf = self._buf[: self.FRAME_SAMPLES], self._buf[self.FRAME_SAMPLES :]
            scores = self._model.predict(frame)
            self._last = float(scores.get(self._keyword, max(scores.values(), default=0.0)))
        return self._last


def build_processor(gate: WakeGate):
    """Return a Pipecat FrameProcessor that applies ``gate`` to input audio.

    Built lazily so the pure state machine above stays importable without Pipecat.
    """
    from loguru import logger
    from pipecat.frames.frames import (
        BotStartedSpeakingFrame,
        BotStoppedSpeakingFrame,
        Frame,
        InputAudioRawFrame,
        UserStartedSpeakingFrame,
        UserStoppedSpeakingFrame,
    )
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

    class WakeGateProcessor(FrameProcessor):
        def __init__(self):
            super().__init__(name="WakeGate")
            gate.on_wake.append(lambda: logger.info("wake: Hey Ned"))
            gate.on_sleep.append(lambda: logger.info("wake: back to sleep"))

        async def process_frame(self, frame: Frame, direction: FrameDirection):
            await super().process_frame(frame, direction)
            if isinstance(frame, InputAudioRawFrame):
                if gate.feed(frame.audio):
                    await self.push_frame(frame, direction)
                return
            if isinstance(frame, (UserStartedSpeakingFrame, BotStartedSpeakingFrame)):
                gate.activity(True)
            elif isinstance(frame, (UserStoppedSpeakingFrame, BotStoppedSpeakingFrame)):
                gate.activity(False)
            await self.push_frame(frame, direction)

    return WakeGateProcessor()
