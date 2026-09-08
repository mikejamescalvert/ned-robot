"""Find the reSpeaker by name.

PyAudio (what Pipecat's local transport uses) numbers devices at startup and the numbers move
around across reboots and USB replugs. Match on the name instead. This module has no hard
dependency on PyAudio so it can be unit tested; pass in any list of (index, name) pairs.
"""

from __future__ import annotations

from collections.abc import Iterable


def pick_device(devices: Iterable[tuple[int, str]], match: str) -> int | None:
    """Return the index of the first device whose name contains ``match`` (case-insensitive)."""
    needle = match.lower()
    for index, name in devices:
        if needle in name.lower():
            return index
    return None


def list_pyaudio_devices() -> list[tuple[int, str]]:
    """Enumerate devices through PyAudio. Only works where PortAudio is installed (the Pi)."""
    import pyaudio  # local import: not installed in CI

    pa = pyaudio.PyAudio()
    try:
        return [(i, pa.get_device_info_by_index(i)["name"]) for i in range(pa.get_device_count())]
    finally:
        pa.terminate()
