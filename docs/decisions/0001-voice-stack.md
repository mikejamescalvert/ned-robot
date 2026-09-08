# 0001 — Voice stack for Phase 0

Status: **proposed 2026-09-08, awaiting Mike's ack.** Researched in a cloud session; nothing
here has run on the Pi yet. Numbers are vendor-published or third-party (Coval, Hamming,
Gradium) as of September 2026 and should be re-measured on hardware.

## Decisions

| Concern | Pick | Backup | Why |
|---|---|---|---|
| Pipeline | **Pipecat** (BSD-2) with `LocalAudioTransport`, Silero VAD, `AnthropicLLMService` | hand-rolled asyncio | Only maintained framework that runs local mic/speaker on a Pi 5 with no server, has first-class Claude tool calling, and ships barge-in + turn handling. Proven on a Pi 5 with a reSpeaker array. |
| STT | **Deepgram Flux** (`flux-general-en`) | AssemblyAI Universal-3.5 Pro Realtime | Independently measured sub-300 ms semantic end-of-turn; tunable `eot_threshold`; eager end-of-turn lets us pre-warm Claude; native 16 kHz linear16; asyncio SDK. $0.39/hr streamed. |
| TTS | **Cartesia Sonic 3.6** | ElevenLabs Flash v2.5 | ~190 ms first audio (Coval P50); explicit `cancel` on a context; raw `pcm_s16le` at 16 kHz so no decode on the Pi; top-ranked voice quality; cheapest at hobby volume. |
| Wake word | **openWakeWord**, self-trained "Hey Ned" ONNX model | none viable | Picovoice ended its free tier 2026-06-30 (lowest paid tier ~$899/mo). openWakeWord trains from synthetic TTS in a free Colab in under an hour, runs at a few % of one Pi core. |
| Listening mode | **Wake-word-only, with a follow-up window** | continuous | STT is billed per streamed hour. Continuous ≈ $9/day. Wake-word-only streams only during a conversation, then keeps a short follow-up window (~8 s) so "Hey Ned" is not needed for every turn. Also the privacy answer for an office with client calls. |
| LLM | **Claude Opus 5** (`claude-opus-5`) at `effort: low`, adaptive thinking | Sonnet 5 for A/B on latency | Per PROJECT.md: low effort, byte-stable system prompt for caching, short spoken line before movement tool calls. |

## Architecture correction

PROJECT.md said the agent layer is "Python (Claude Agent SDK)". The Agent SDK spawns the
Claude Code process and carries seconds of startup per call; it is not a conversational
path. The voice loop calls the **Messages API directly** through Pipecat's Anthropic service.
The Agent SDK remains an option later for long background tasks Ned hands off ("go through my
inbox"), never in the wake-to-first-syllable path.

## Latency budget this stack targets

| Stage | Budget | Source of the number |
|---|---|---|
| End of speech → transcript final | ≤ 300 ms | Flux EOT (Coval) |
| Transcript → Claude first token | ≤ 500 ms | Opus 5 low effort, cached prefix; measure |
| First sentence → first audio | ≤ 200 ms | Cartesia (Coval P50 188 ms) |
| Audio → speaker | ≤ 100 ms | ALSA buffer on the Pi; measure |
| **Total, end of speech → first syllable** | **≈ 1.1 s** | leaves ~0.4 s of the 1.5 s target as slack |

Every stage is logged per turn from the first commit (PROJECT.md, "Latency is the product").

## Things the research flagged

- **openWakeWord on Python 3.12**: install with the ONNX backend only; the tflite path has
  dependency problems. Last release Feb 2024 but the runtime is small and stable.
- **Cartesia cancel**: halts queued text; a request already generating runs to completion and
  is billed. Mitigation: push one sentence at a time and stop *local* playback the instant
  VAD fires, without waiting for the server.
- **Deepgram Flux accuracy** is "on par with Nova-3", which independent tests place behind
  AssemblyAI on hard audio. Fine for one speaker in a quiet office; the backup exists if not.
- **XVF3800 has no keyword spotting** in its USB firmware; the wake word runs on the Pi.
- **Flux vs. Pipecat smart-turn**: both do end-of-turn. Start with Flux's and leave Pipecat's
  `LocalSmartTurnAnalyzerV3` off; add it only if Flux's EOT misfires.

## What Mike does

1. Ack this page (or name a swap).
2. Create three accounts and put the keys in `/etc/ned/env` on the Pi, never in the repo:
   - Deepgram ($200 free credit on signup)
   - Cartesia (free tier, then Pro at $4/mo)
   - Anthropic API key (Console)
3. Nothing else. The scaffold and the first loop arrive as a PR.

## Sources

- Deepgram Flux: https://deepgram.com/learn/introducing-flux-conversational-speech-recognition ;
  Coval validation: https://deepgram.com/learn/coval-validates-flux-no-tradeoff-between-latency-and-interruption ;
  config: https://developers.deepgram.com/docs/flux/configuration
- AssemblyAI benchmarks: https://www.assemblyai.com/blog/universal-3-5-pro-independent-stt-benchmarks
- TTS latency (Coval via Gradium): https://gradium.ai/content/tts-latency-benchmark-2026
- Cartesia contexts/cancel: https://docs.cartesia.ai/use-the-api/tts-websocket/contexts
- ElevenLabs multi-context WS: https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/multi-context-web-socket
- openWakeWord: https://github.com/dscripka/openWakeWord ; training pipeline:
  https://github.com/CoreWorxLab/openwakeword-training
- Picovoice free tier end: https://community.home-assistant.io/t/fyi-picovoice-confirmed-free-tier-accesskeys-will-stop-working-after-june-30-2026/1012744
- Pipecat: https://github.com/pipecat-ai/pipecat ; Anthropic service:
  https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/services/anthropic/llm.py ;
  Pi 5 + reSpeaker example: https://github.com/podstawek/frustratedbox
- Claude Agent SDK startup cost: https://github.com/anthropics/claude-agent-sdk-typescript/issues/34
