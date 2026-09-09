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

    gate = wake.WakeGate(
        detector=wake.OpenWakeWordDetector(cfg.wake_model_path),
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
            thinking=AnthropicThinkingConfig(type="adaptive"),
            extra={"output_config": {"effort": cfg.effort}},
        ),
    )

    context = LLMContext()
    user_agg, assistant_agg = LLMContextAggregatorPair(
        context,
        # Flux supplies end-of-turn; Silero VAD is here for barge-in only.
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    tracker = telemetry.TurnTracker(cfg.model, telemetry.jsonl_sink(cfg.log_dir))

    pipeline = Pipeline(
        [
            transport.input(),
            wake.build_processor(gate),
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
    )
    runner = WorkerRunner()
    await runner.add_workers(worker)
    logger.info("Ned is listening for 'Hey Ned'")
    await runner.run()


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
    if cmd != "run":
        print("usage: ned-agent [run|devices|stats [turns.jsonl]]", file=sys.stderr)
        return 2
    try:
        cfg = Config.from_env()
    except ConfigError as e:
        logger.error(str(e))
        return 1
    asyncio.run(run(cfg))
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
