# STATUS

Shared memory between surfaces. Every session updates this file before it ends.
See `PROJECT.md` for the rules.

## Current phase

**Phase 0 — Desk brain, no wheels.** Hardware ordered, arriving Tue 2026-09-08. No code in
the repo yet. Cloud-only prep week until the parts land.

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

None. Nothing has run on the Pi.

## Blockers

Open decisions that gate Phase 0 setup — settle before installing anything on the Pi:

- [ ] **Ubuntu / ROS 2 pin.** Proposed: **Ubuntu 24.04 LTS + ROS 2 Jazzy Jalisco** (LTS to
  May 2029). Lyrical Luth (May 2026, Ubuntu 26.04) is LTS but three months old; iRobot's
  Create 3 packages and the community Pi 5 + Create 3 write-ups are on Jazzy, and the Create 3
  firmware is the one piece of this stack we cannot patch. Awaiting Mike's ack.
- [ ] STT vendor, chosen on streaming latency.
- [ ] TTS vendor, chosen on streaming latency and mid-word interruptibility.
- [ ] Continuous listening vs wake-word-only (client calls happen in the office).

## Next action

Before Tuesday, in cloud sessions: ack the distro pin, pick STT/TTS vendors, and scaffold the
repo (`ned/` package, `tests/`, CI) so hardware day is flash-and-run, not decide-and-install.

On Tuesday, surface B: flash Ubuntu 24.04 Server (64-bit) with Raspberry Pi Imager (Wi-Fi +
SSH key preconfigured, headless), install Tailscale and Node.js, start
`claude remote-control --name ned` inside tmux, and confirm `arecord -l` shows the XVF3800.

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
