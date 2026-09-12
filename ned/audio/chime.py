"""Wake and sleep chimes: the audible "I am listening" cue.

Two short sine tones, generated here rather than shipped as a WAV so there is no asset to
keep in sync with the output sample rate. Kept deliberately quiet and brief: this plays
before every conversation, so it has to be unobtrusive on the tenth time, not the first.
"""

from __future__ import annotations

import math
import struct

WAKE_TONES = ((880.0, 0.07), (1174.7, 0.09))  # A5 then D6: rising, "yes?"
SLEEP_TONES = ((587.3, 0.07), (440.0, 0.09))  # D5 then A4: falling, "gone"


def tone(freq_hz: float, secs: float, sample_rate: int, amplitude: float = 0.18) -> bytes:
    """One sine tone as pcm16, with a short fade in and out so it does not click."""
    n = int(sample_rate * secs)
    fade = max(1, int(sample_rate * 0.005))
    out = bytearray()
    for i in range(n):
        env = min(1.0, i / fade, (n - i) / fade)
        v = amplitude * env * math.sin(2 * math.pi * freq_hz * i / sample_rate)
        out += struct.pack("<h", int(v * 32767))
    return bytes(out)


def chime(tones=WAKE_TONES, sample_rate: int = 16000) -> bytes:
    """Concatenate ``tones`` (pairs of frequency and duration) into one pcm16 buffer."""
    return b"".join(tone(f, s, sample_rate) for f, s in tones)
