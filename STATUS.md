# STATUS

Shared memory between surfaces. Every session updates this file before it ends.
See `PROJECT.md` for the rules.

## Current phase

**Phase 0 — Desk brain, no wheels.** Not started. No code in the repo yet.

## Last hardware observation (surface B)

None. Nothing has run on the Pi.

## Blockers

Open decisions that gate Phase 0 setup — settle before installing anything on the Pi:

- [ ] Ubuntu version / ROS 2 distro pinning on the Pi 5.
- [ ] STT vendor, chosen on streaming latency.
- [ ] TTS vendor, chosen on streaming latency and mid-word interruptibility.
- [ ] Continuous listening vs wake-word-only (client calls happen in the office).

## Next action

Settle the four open decisions above in a cloud session, then flash the Pi and bring up
`claude remote-control --name ned` inside tmux for the first surface B session.

## Session log

- 2026-09-03 — Governing prompt landed in `PROJECT.md`. `STATUS.md` created.
