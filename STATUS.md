# STATUS

Shared memory between surfaces. Every session updates this file before it ends.
See `PROJECT.md` for the rules.

## Current phase

**Phase 0 — Desk brain, no wheels.** Hardware arrived 2026-09-08. Bring-up scripts are in
`deploy/`; the Pi has not been flashed yet. No agent code in the repo yet.

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

2026-09-08 — Pi 5 flashed with Ubuntu 24.04, bootstrapped, on Tailscale. `claude
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
- [ ] STT vendor, chosen on streaming latency.
- [ ] TTS vendor, chosen on streaming latency and mid-word interruptibility.
- [ ] Continuous listening vs wake-word-only (client calls happen in the office).

## Next action

Hardware bring-up is done. The Pi needs nothing more until there is agent code to run.

Cloud, next: settle STT and TTS vendors (shortlist with streaming latency numbers), then
scaffold the repo (`ned/` package, `tests/`, CI) and the first runnable loop: wake word →
STT → Claude → TTS on the desk. Continuous-vs-wake-word decision comes with the vendor pick.

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
