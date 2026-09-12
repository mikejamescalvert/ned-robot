"""Ned's agent: wake word -> Deepgram Flux STT -> Claude -> Cartesia TTS, on the desk.

Runs only on the Pi (real audio devices). Everything importable without hardware lives in the
sibling modules and is unit tested; this file is wiring. See docs/decisions/0001-voice-stack.md.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from loguru import logger

from ned import telemetry
from ned.audio import wake
from ned.audio.devices import list_pyaudio_devices, pick_device
from ned.config import Config, ConfigError
from ned.tools import clock


async def run(cfg: Config) -> None:
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.worker import PipelineParams, PipelineWorker, ProcessorUnusablePolicy
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.processors.aggregators.llm_response_universal import (
        LLMContextAggregatorPair,
        LLMUserAggregatorParams,
    )
    from pipecat.services.anthropic.llm import AnthropicLLMService, AnthropicThinkingConfig
    from pipecat.services.cartesia.tts import CartesiaTTSService
    from pipecat.services.deepgram.flux.stt import DeepgramFluxSTTService
    from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams
    from pipecat.workers.runner import WorkerRunner

    devices = list_pyaudio_devices()
    idx = pick_device(devices, cfg.audio_device_match)
    if idx is None:
        raise ConfigError(f"no audio device matching {cfg.audio_device_match!r}; saw {devices}")
    logger.info(f"audio device {idx}: {dict(devices)[idx]}")

    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_in_sample_rate=cfg.sample_rate_in,
            audio_out_sample_rate=cfg.sample_rate_out,
            input_device_index=idx,
            output_device_index=idx,
        )
    )

    detector = wake.OpenWakeWordDetector(
        cfg.wake_model_path,
        vad_threshold=cfg.wake_vad_threshold,
        verifier_path=cfg.wake_verifier_path,
        verifier_threshold=cfg.wake_verifier_threshold,
    )
    logger.info(
        f"wake: threshold {cfg.wake_threshold}, frames {cfg.wake_consecutive_frames}, "
        f"vad {cfg.wake_vad_threshold}, verifier {'on' if detector.verifier_active else 'off'}"
    )
    gate = wake.WakeGate(
        detector=detector,
        threshold=cfg.wake_threshold,
        consecutive_frames=cfg.wake_consecutive_frames,
        follow_up_secs=cfg.follow_up_secs,
        mute_file=cfg.mute_file,
    )

    stt = DeepgramFluxSTTService(api_key=cfg.deepgram_api_key, sample_rate=cfg.sample_rate_in)

    tts = CartesiaTTSService(
        api_key=cfg.cartesia_api_key,
        sample_rate=cfg.sample_rate_out,
        settings=CartesiaTTSService.Settings(voice=cfg.tts_voice, model=cfg.tts_model),
    )

    # Byte-stable system prompt first (cacheable); volatile facts go in a trailing block.
    llm = AnthropicLLMService(
        api_key=cfg.anthropic_api_key,
        settings=AnthropicLLMService.Settings(
            model=cfg.model,
            system_instruction=cfg.system_prompt(),
            max_tokens=cfg.max_tokens,
            enable_prompt_caching=True,
            thinking=AnthropicThinkingConfig(type=cfg.thinking),
            extra={"output_config": {"effort": cfg.effort}},
        ),
    )

    # Tools advertised here are registered on the LLM service automatically (handler on the
    # schema). Keep the list byte-stable across turns: it is part of the cached prefix.
    context = LLMContext(tools=[clock.function_schema()])
    user_agg, assistant_agg = LLMContextAggregatorPair(
        context,
        # Flux supplies end-of-turn; Silero VAD is here for barge-in only.
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    tracker = telemetry.TurnTracker(cfg.model, telemetry.jsonl_sink(cfg.log_dir))

    pipeline = Pipeline(
        [
            transport.input(),
            wake.build_processor(gate, cfg.sample_rate_out if cfg.wake_chime else 0),
            stt,
            user_agg,
            llm,
            tts,
            # After tts so it sees LLM/TTS timing and usage frames flowing down, and the
            # transport's bot-speaking frames flowing back up.
            telemetry.build_processor(tracker),
            transport.output(),
            assistant_agg,
        ]
    )

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=cfg.sample_rate_in,
            audio_out_sample_rate=cfg.sample_rate_out,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        processor_unusable_policy=ProcessorUnusablePolicy.END,
        # Pipecat cancels a pipeline that sees no frames for 5 min. The wake gate drops every
        # frame while Ned is asleep, so an idle Ned looks dead to it. Ned waits indefinitely.
        idle_timeout_secs=None,
    )
    runner = WorkerRunner()
    await runner.add_workers(worker)
    logger.info("Ned is listening for 'Hey Ned'")
    await runner.run()


def _mic_chunks(cfg: Config, seconds: float | None):
    """Yield 80 ms pcm16 chunks from the array mic. Pi only (PyAudio)."""
    import pyaudio

    devices = list_pyaudio_devices()
    idx = pick_device(devices, cfg.audio_device_match)
    if idx is None:
        raise ConfigError(f"no audio device matching {cfg.audio_device_match!r}; saw {devices}")
    pa = pyaudio.PyAudio()
    frames = wake.OpenWakeWordDetector.FRAME_SAMPLES
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=cfg.sample_rate_in,
        input=True,
        input_device_index=idx,
        frames_per_buffer=frames,
    )
    total = None if seconds is None else int(seconds * cfg.sample_rate_in / frames)
    try:
        n = 0
        while total is None or n < total:
            yield stream.read(frames, exception_on_overflow=False)
            n += 1
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()


def wakescore(cfg: Config) -> int:
    """Live wake-score meter. Say nothing, type, cough, then say "hey ned". Ctrl+C to stop."""
    detector = wake.OpenWakeWordDetector(
        cfg.wake_model_path,
        vad_threshold=cfg.wake_vad_threshold,
        verifier_path=cfg.wake_verifier_path,
        verifier_threshold=cfg.wake_verifier_threshold,
    )
    print(
        f"threshold {cfg.wake_threshold}  vad {cfg.wake_vad_threshold}  "
        f"verifier {'on' if detector.verifier_active else 'off'}   (Ctrl+C to stop)"
    )
    try:
        wake.score_meter(detector, _mic_chunks(cfg, None), cfg.wake_threshold)
    except KeyboardInterrupt:
        pass
    return 0


def record_clips(cfg: Config, kind: str, count: int, seconds: float = 2.0) -> int:
    """Record short WAV clips for the personal verifier into ~/ned-wake/<kind>/."""
    import time
    import wave

    out_dir = Path.home() / "ned-wake" / kind
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = (
        'say "hey ned", naturally, once'
        if kind == "positive"
        else "say anything that is NOT the wake word (a sentence, a name, a cough)"
    )
    for i in range(count):
        n = len(list(out_dir.glob("*.wav"))) + 1
        path = out_dir / f"{n:02d}.wav"
        print(f"[{i + 1}/{count}] in 1 second, {prompt}")
        time.sleep(1.0)
        print("   recording...")
        data = b"".join(_mic_chunks(cfg, seconds))
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(cfg.sample_rate_in)
            w.writeframes(data)
        print(f"   saved {path}")
        time.sleep(0.5)
    return 0


def train_verifier(cfg: Config) -> int:
    """Train the personal verifier from ~/ned-wake/{positive,negative}/*.wav."""
    from openwakeword.custom_verifier_model import train_custom_verifier
    from openwakeword.utils import download_models

    base = Path.home() / "ned-wake"
    pos = sorted(str(p) for p in (base / "positive").glob("*.wav"))
    neg = sorted(str(p) for p in (base / "negative").glob("*.wav"))
    if len(pos) < 5 or len(neg) < 5:
        logger.error(
            f"need at least 5 positive and 5 negative clips, have {len(pos)}/{len(neg)}; "
            "run `ned-agent record positive 10` and `ned-agent record negative 10`"
        )
        return 1
    download_models(model_names=["hey_jarvis_v0.1"])  # feature models only, see wake.py
    out = cfg.wake_verifier_path
    out.parent.mkdir(parents=True, exist_ok=True)
    train_custom_verifier(pos, neg, str(out), str(cfg.wake_model_path), inference_framework="onnx")
    logger.info(f"verifier written to {out}; it is picked up automatically on the next run")
    return 0


USAGE = (
    "usage: ned-agent [run | devices | stats [turns.jsonl] | wakescore | "
    "record positive|negative [count] | train-verifier]"
)


def cli(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    cmd = argv[0] if argv else "run"
    if cmd == "stats":
        path = Path(argv[1]) if len(argv) > 1 else Config().log_dir / "turns.jsonl"
        records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        print(json.dumps(telemetry.summarize(records), indent=2))
        return 0
    if cmd == "devices":
        for i, name in list_pyaudio_devices():
            print(f"{i:3d}  {name}")
        return 0
    if cmd not in ("run", "wakescore", "record", "train-verifier"):
        print(USAGE, file=sys.stderr)
        return 2
    try:
        cfg = Config.from_env()
        if cmd == "wakescore":
            return wakescore(cfg)
        if cmd == "record":
            kind = argv[1] if len(argv) > 1 else ""
            if kind not in ("positive", "negative"):
                print(USAGE, file=sys.stderr)
                return 2
            return record_clips(cfg, kind, int(argv[2]) if len(argv) > 2 else 10)
        if cmd == "train-verifier":
            return train_verifier(cfg)
    except ConfigError as e:
        logger.error(str(e))
        return 1
    asyncio.run(run(cfg))
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
