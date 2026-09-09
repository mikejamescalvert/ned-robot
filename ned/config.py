"""Configuration for the agent, read from the environment.

On the Pi, systemd loads /etc/ned/env before starting the service, so everything here is a
plain environment variable. In tests, construct Config directly. Secrets never have defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PROMPT = Path(__file__).resolve().parent.parent / "prompts" / "ned-v0.md"
DEFAULT_WAKE_MODEL = Path(__file__).resolve().parent.parent / "models" / "hey_ned.onnx"


class ConfigError(RuntimeError):
    """A required setting is missing or malformed."""


@dataclass(frozen=True)
class Config:
    # Identity
    body: str = "office"

    # Secrets (required at runtime, never defaulted)
    anthropic_api_key: str = ""
    deepgram_api_key: str = ""
    cartesia_api_key: str = ""

    # Audio. The reSpeaker shows up as ALSA card "Array"; match by name, never by index.
    audio_device_match: str = "Array"
    sample_rate_in: int = 16000
    sample_rate_out: int = 16000  # playback goes through the array's jack at 16 kHz

    # Wake word
    wake_model_path: Path = DEFAULT_WAKE_MODEL
    wake_threshold: float = 0.5
    wake_consecutive_frames: int = 2
    follow_up_secs: float = 8.0
    mute_file: Path = Path("/etc/ned/mute")

    # Model
    model: str = "claude-sonnet-5"  # docs/decisions/0002-chat-model.md
    effort: str = "low"
    thinking: str = "adaptive"  # "adaptive" or "disabled"; see decision 0002
    max_tokens: int = 400
    prompt_path: Path = DEFAULT_PROMPT

    # Speech
    tts_voice: str = ""  # Cartesia voice id; chosen on the Pi, see docs/decisions/0001
    tts_model: str = "sonic-3.6"

    # Telemetry
    log_dir: Path = Path.home() / "ned-logs"

    extra: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Config:
        e = dict(os.environ if env is None else env)

        def req(name: str) -> str:
            v = e.get(name, "").strip()
            if not v:
                raise ConfigError(f"{name} is not set (expected in /etc/ned/env)")
            return v

        def num(name: str, default: float, kind=float):
            raw = e.get(name)
            if raw is None or raw == "":
                return default
            try:
                return kind(raw)
            except ValueError as ex:
                raise ConfigError(f"{name}={raw!r} is not a number") from ex

        return cls(
            body=e.get("NED_BODY", "office"),
            anthropic_api_key=req("ANTHROPIC_API_KEY"),
            deepgram_api_key=req("DEEPGRAM_API_KEY"),
            cartesia_api_key=req("CARTESIA_API_KEY"),
            audio_device_match=e.get("NED_AUDIO_DEVICE", "Array"),
            sample_rate_in=num("NED_SAMPLE_RATE_IN", 16000, int),
            sample_rate_out=num("NED_SAMPLE_RATE_OUT", 16000, int),
            wake_model_path=Path(e.get("NED_WAKE_MODEL", str(DEFAULT_WAKE_MODEL))),
            wake_threshold=num("NED_WAKE_THRESHOLD", 0.5),
            wake_consecutive_frames=num("NED_WAKE_FRAMES", 2, int),
            follow_up_secs=num("NED_FOLLOW_UP_SECS", 8.0),
            mute_file=Path(e.get("NED_MUTE_FILE", "/etc/ned/mute")),
            model=e.get("NED_MODEL", "claude-sonnet-5"),
            effort=e.get("NED_EFFORT", "low"),
            thinking=e.get("NED_THINKING", "adaptive"),
            max_tokens=num("NED_MAX_TOKENS", 400, int),
            prompt_path=Path(e.get("NED_PROMPT", str(DEFAULT_PROMPT))),
            tts_voice=e.get("CARTESIA_VOICE_ID", ""),
            tts_model=e.get("NED_TTS_MODEL", "sonic-3.6"),
            log_dir=Path(e.get("NED_LOG_DIR", str(Path.home() / "ned-logs"))),
        )

    def system_prompt(self) -> str:
        """The byte-stable system prompt. Volatile facts are appended by the caller, after it."""
        text = self.prompt_path.read_text(encoding="utf-8").strip()
        return text.replace("{{body}}", self.body)
