# STATUS

Shared memory between surfaces. Every session updates this file before it ends.
See `PROJECT.md` for the rules.

## Current phase

**Phase 0 — Desk brain, no wheels.** The loop runs on hardware as of 2026-09-09 (see below).
Latest measurement 2026-09-12 (below): 1.70 s to first sound on Sonnet 5, target 1.5 s.
Remaining for the phase gate: the 3-turn conversation from six feet and the barge-in check.

## Hardware on order (Phase 0)

- Raspberry Pi 5, 16GB
- Seeed reSpeaker XVF3800 USB 4-Mic Array, with case. **Swapped in for the Mic Array v2.0**,
  which was back-ordered. Same family, newer XMOS chip, keeps the 3.5mm headphone jack the
  echo canceller needs, and adds a JST speaker header with a 5W amp (lets the Pebble come off
  the robot in Phase 1).
- Creative Pebble V2 speaker (3.5mm aux from the mic array; USB-C power from a spare charger,
  not from the Pi)
- Official Raspberry Pi 27W USB-C power supply
- SanDisk Extreme 64GB microSD (A2)
- Official Raspberry Pi Active Cooler

Wiring: Pi USB → mic array. Mic array 3.5mm → Pebble aux in. Playback must go through the
array's jack or its AEC has nothing to cancel against.

## Last hardware observation (surface B)

**2026-09-12 — Sonnet 5 A/B, 24 turns.** Claude's first byte fell from 1427 ms to 900 ms,
but first sound only moved from 1786 ms to 1700 ms. The half second Claude gave back mostly
did not reach the speaker, so the rest of the turn is now the problem:

| stage (p50, Sonnet) | ms |
|---|---|
| end of speech → LLM request sent | ~400 (turn detection; measured directly from now on) |
| LLM first byte | 900 |
| first sentence → TTS first byte | 135 |
| TTS audio → speaker | ~160 |
| **end of speech → first sound** | **1700** (target 1500) |

Note "end of speech" is the VAD stop, which fires 200 ms after the last word, so the number
a person feels is about 1.9 s. Decision 0002 accepted anyway: Sonnet is better on every
axis and Opus was buying nothing for 19-token replies. Cost per turn rose to $0.0029
because the session was longer (context grows every turn) and included tool calls, not
because of the model. Next levers, in order: `NED_THINKING=disabled` (env only),
`NED_EOT_THRESHOLD` lower than 0.7, then eager end-of-turn. First-token telemetry had to
move upstream of TTS, which eats text frames; fixed the same day.

**2026-09-09 — First latency numbers.** `ned-agent stats` over 18 turns, one desk session:

| metric | p50 |
|---|---|
| end of speech → first TTS audio | 1619 ms |
| end of speech → first sound from speaker | 1786 ms |
| cost per turn | $0.0021 |

Against the 1.5 s target we are 0.3 s over on the first try, before any tuning. The
"first token 1 ms" the same run printed was a telemetry bug (it timed the LLM request being
sent, not the first token back); fixed the same day. The per-service breakdown from the same
log: Deepgram first byte 75 ms, **Anthropic 1427 ms**, Cartesia 139 ms. Claude owns the whole
gap, and replies are 19 tokens so it is not thinking time. Decision 0002 moves the default
chat model to Sonnet 5; the next run measures that. `NED_THINKING=disabled` is the lever
after it if needed.

**2026-09-09 — First spoken exchange with Ned.** On the Pi, `uv run --extra pi ned-agent run`
with the trained `hey_ned.onnx` (threshold 0.35, 1 frame). Mike said "Hey Ned" then "what time
is it today" from the desk; Ned answered through the array's speaker: "I don't have a clock I
can check right now so I can't tell you." Wake word → Deepgram Flux → Claude Opus 5 → Cartesia
→ speaker, end to end, first attempt. Latency numbers read later the same day (above).

Earlier: 2026-09-08 — Pi 5 flashed with Ubuntu 24.04, bootstrapped, on Tailscale. `claude
remote-control --name ned` running in tmux and visible in the Claude app.

`deploy/check-audio.sh` passed. Mike heard himself on playback. Distance not measured; the
six-foot test is part of the Phase 0 done criterion, not this check.

```
Bus 002 Device 002: ID 2886:001a Seeed Technology Co., Ltd. reSpeaker XVF3800 4-Mic Array
reSpeaker is ALSA card 0
card 0: Array [reSpeaker XVF3800 4-Mic Array], device 0: USB Audio [USB Audio]   # capture
card 0: Array [reSpeaker XVF3800 4-Mic Array], device 0: USB Audio [USB Audio]   # playback
```

Facts for the agent config: USB id `2886:001a`, ALSA card name `Array`, capture and playback
both on `plughw:CARD=Array,DEV=0`. Use the card *name*, not the number; the number can change
across reboots.

## Blockers

Open decisions that gate Phase 0 setup — settle before installing anything on the Pi:

- [x] **Ubuntu / ROS 2 pin: Ubuntu 24.04 LTS + ROS 2 Jazzy Jalisco** (LTS to May 2029).
  Pinned 2026-09-08 on hardware day; Mike read the reasoning and did not object. Lyrical Luth
  (Ubuntu 26.04) was rejected because the Create 3 ecosystem is on Jazzy and its firmware is
  the one piece we cannot patch. Change this only with a written reason here.
- [x] **Voice stack** — accepted 2026-09-08, `docs/decisions/0001-voice-stack.md`: Pipecat,
  Deepgram Flux STT, Cartesia Sonic TTS, openWakeWord "Hey Ned", wake-word-only with a
  follow-up window, Claude Opus 5 at low effort.
- [ ] **API keys on the Pi** — Deepgram, Cartesia, Anthropic, in `/etc/ned/env`. Mike.

## Next action

Hardware bring-up is done. The Pi needs nothing more until there is agent code to run.

Mike, three small things, any order:
1. Keys in `/etc/ned/env` (Deepgram, Cartesia, Anthropic) plus `CARTESIA_VOICE_ID` from the
   Cartesia playground.
2. Train `hey_ned.onnx` per `docs/wakeword.md` (Colab, under an hour), commit it to `models/`.
3. On the Pi: `git pull`, `uv sync --extra pi`, then `uv run --extra pi ned-agent devices` to
   confirm the array is listed, then `uv run --extra pi ned-agent run` in tmux and say
   "Hey Ned". Paste whatever it prints, good or bad, into Ned Brain.

Cloud: nothing blocking. Next code is whatever the first run on hardware reveals.

## Decisions logged this week (now in PROJECT.md)

- Latency target restated as end-of-speech → first syllable; per-stage timing logged per turn.
- Voice loop runs the model at low effort; Ned speaks a short line before a movement tool call.
- One Ned, possibly many bodies: `body` enum on motion/camera tools, `NED_BODY` in env, memory
  behind an interface, no hardcoded location. Second body not before Phase 2 sign-off.
- Camera on demand only, LED when live, frames discarded unless remembered. Mast at desk height.
- Stairs out of scope. Create 3 dock-sleep power gotcha assigned to Phase 1.
- `BOM.md` is now a real parts list by phase (it was a stray copy of the old PROJECT.md).

## Session log

- 2026-09-03 — Governing prompt landed in `PROJECT.md`. `STATUS.md` created.
- 2026-09-03 — Phase 0 parts ordered (list above), ETA 2026-09-08. Mic swapped to XVF3800.
  Distro pin proposed: 24.04 + Jazzy.
- 2026-09-03 — Design decisions from the planning conversation folded into `PROJECT.md`;
  `BOM.md` rewritten as a parts list.
- 2026-09-08 — Hardware arrived. `deploy/` bring-up added (README, bootstrap, audio check,
  Remote Control wrapper, env template). Distro pinned 24.04 + Jazzy.
- 2026-09-08 — First surface B session up. Two bring-up snags fixed in `deploy/`: workspace
  trust dialog must be accepted once interactively; wrapper now passes `--spawn=same-dir`.
- 2026-09-08 — Audio check passed on hardware (card `Array`, USB `2886:001a`). Phase 0
  hardware bring-up complete; Phase 0 itself stays open until the 3-turn conversation test.
- 2026-09-08 — Voice stack researched (three parallel tracks) and proposed as decision 0001.
  PROJECT.md architecture corrected: Messages API via Pipecat, not the Agent SDK, in the
  voice path. Remote Control session named "Ned Brain".
- 2026-09-12 — Sonnet 5 measured: 1.70 s p50 to first sound, Claude 900 ms. Decision 0002
  accepted. Telemetry now stamps LLM request start upstream of TTS; Flux EOT knobs added.
- 2026-09-10 — First tool: `get_time`. Ned no longer says "I don't have a clock". Exercises the
  Pipecat function-calling path that `drive_to` will use.
- 2026-09-09 — Design: Telegram bot as a second transport in Phase 4 (caller, not a body).
- 2026-09-09 — Design: doors and locks go through Home Assistant tools, not robot hardware.
  Create 3 stays the base; taller mast + earlier lidar proposed, not yet written in.
- 2026-09-09 — Breakdown read: Anthropic TTFB 1427 ms is the gap. Decision 0002 proposed: Sonnet 5
  default chat model, `NED_THINKING` knob, tier by activity later.
- 2026-09-09 — First latency measurement: 1.79 s p50 to first sound over 18 turns, $0.002/turn.
  Telemetry first-token bug fixed; `stats` gained per-service TTFB breakdown.
- 2026-09-08 — Agent scaffold landed: `ned/` package, wake gate, per-turn latency/cost log,
  tests, CI, `ned-agent.service`, `update.sh`. Verified in the cloud only.
- 2026-09-09 — Wake word model trained (Colab Pro, L4, runtime 2026.04, four notebook patches;
  copied to the Pi). First `uv sync --extra pi` on the Pi failed: openwakeword 0.6.0 pins
  tflite-runtime (no Python 3.12 wheels). Fixed with uv dependency overrides; the ONNX path
  verified in the cloud. Next: first run on the Pi.
- 2026-09-09 — First spoken exchange on the Pi. Phase 0 loop works end to end.
