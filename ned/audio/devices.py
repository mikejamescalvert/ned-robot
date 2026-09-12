"""Find the reSpeaker by name.

PyAudio (what Pipecat's local transport uses) numbers devices at startup and the numbers move
around across reboots and USB replugs. Match on the name instead. This module has no hard
dependency on PyAudio so it can be unit tested; pass in any list of (index, name) pairs.
"""

from __future__ import annotations

import contextlib
import os
import sys
from collections.abc import Iterable, Iterator


def pick_device(devices: Iterable[tuple[int, str]], match: str) -> int | None:
    """Return the index of the first device whose name contains ``match`` (case-insensitive)."""
    needle = match.lower()
    for index, name in devices:
        if needle in name.lower():
            return index
    return None


@contextlib.contextmanager
def quiet_stderr() -> Iterator[None]:
    """Silence writes to stderr, including ones from C libraries.

    Initialising PortAudio makes ALSA and JACK print ~25 lines about sound cards this Pi does
    not have (hdmi, rear, modem, a JACK server nobody is running). They are harmless and there
    is no ALSA setting that turns them off from here, but they bury the prompts in interactive
    commands. They come from C, so redirecting ``sys.stderr`` is not enough: the underlying
    file descriptor has to move.

    Everything written to fd 2 inside the block is discarded, Python's own stderr included, so
    keep blocks short and around library calls rather than around our own logic. An exception
    raised inside still propagates and prints normally, because that happens after the block.
    """
    sys.stderr.flush()
    saved = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 2)
        yield
    finally:
        sys.stderr.flush()
        os.dup2(saved, 2)
        os.close(devnull)
        os.close(saved)


def open_pyaudio():
    """Construct a PyAudio instance without the ALSA/JACK noise. Caller must ``terminate()``."""
    import pyaudio  # local import: not installed in CI

    with quiet_stderr():
        return pyaudio.PyAudio()


def list_pyaudio_devices(pa=None) -> list[tuple[int, str]]:
    """Enumerate devices through PyAudio. Only works where PortAudio is installed (the Pi).

    Pass an existing instance to avoid paying the (noisy, ~1 s) PortAudio start-up again.
    """
    own = pa is None
    pa = pa or open_pyaudio()
    try:
        with quiet_stderr():
            return [
                (i, pa.get_device_info_by_index(i)["name"]) for i in range(pa.get_device_count())
            ]
    finally:
        if own:
            pa.terminate()
