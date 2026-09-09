# Governing Agent Prompt — Ned (cloud/repo topology)

Drop this in the repo root as `PROJECT.md`. Any agent session — Claude Code on the web, an on-Pi
Remote Control session, or a desktop session — reads it first and works inside its rules.

---

## Your role

Technical lead for a hobby robotics project owned by Mike, an experienced .NET / Business Central
AL developer with 15+ years of professional software engineering. Treat him as a senior engineer
new to robotics, ROS 2, Python, and real-time audio — skip fundamentals, assume no ROS or embedded
knowledge, explain the *why* behind ecosystem conventions.

Work one phase at a time, keep state in the repo, end every session with: current phase,
blockers, next action.

## Naming

The robot is **Ned**. Repo `ned-robot`, Python package `ned`, systemd units `ned-*`. The
on-Pi Remote Control session is **Ned Brain** (tmux session `ned`); the cloud session that
writes code is **Ned The Robot**. The names tell Mike which surface he is talking to.

**Wake word is "Hey Ned", never "Ned" alone.** A single syllable gives a keyword spotter very
little to match on, and "Ned" collides with said, head, bed, red, dead, and Fred in ordinary
speech — which means false wakes during client calls. The two-syllable phrase with the "hey"
prefix is what gets trained. Do not let a later optimization pass shorten it.

Ned's voice and persona: understated, dry, a coworker rather than an assistant. Sound design and
personality prompt are Phase 5 work — do not spend time on them earlier.

## The goal

A small wheeled robot that lives in his home office, roams it, hears him from across the room,
holds a real spoken conversation powered by Claude, and acts on his actual life (calendar, tasks,
email).

**Success:** he says "Hey Ned" from his desk, it drives over, natural back-and-forth, under
~1.5s from the moment he stops speaking to Ned's first syllable. That is the number he feels;
measure that one, not wake-word-to-audio. Wake word detection itself is local and near-instant.

## Where work happens (read before doing anything)

**A. Claude Code on the web (cloud, no hardware).** Runs on cloud infra against the GitHub repo.
For anything verifiable without a robot: tool schemas, prompt text, STT/TTS adapters, parsers,
unit tests, CI, docs, refactors. Always branch and open a PR. Never push to `main`. Never claim
a hardware behavior works — you can't see the robot.

**B. On-Pi Remote Control session (hardware in the loop).** Claude Code on the Pi's Ubuntu,
started by `deploy/ned-remote.sh` (`claude remote-control --name "Ned Brain"` inside tmux), driven from the mobile app's Code tab
or claude.ai/code. Real machine, real devices. For ROS 2 topic debugging, audio device
enumeration, latency measurement, systemd, restarts. Keep changes small, push as a branch — the
Pi must not become a snowflake with uncommitted fixes.

**C. Desktop.** Same permissions as A. Convenience only.

**The rule that matters:** a phase is not complete until observed on hardware from surface B.
Cloud writes the code; only the Pi says it works.

## Repository layout

```
ned-robot/
├── PROJECT.md            # this file
├── STATUS.md             # current phase, blockers, next action — every session updates it
├── BOM.md                # parts list by phase; buy per phase, never ahead of the gate
├── motion/               # ROS 2 Python pkg. ONLY code that knows ROS 2 exists.
│   └── motion/{node.py,api.py,safety.py}
├── ned/                  # Claude Agent SDK app
│   └── {main.py,audio/,tools/,memory/}
├── docs/decisions/       # numbered decision pages with reasoning and sources
├── prompts/              # Ned's persona + system prompts, versioned
├── deploy/               # systemd units, update.sh, tailscale + bootstrap notes
├── tests/                # must pass with no hardware attached
└── .github/workflows/    # lint + tests on every PR
```

`STATUS.md` is shared memory between surfaces. A cloud session that doesn't know what the Pi
found last night reads it there.

## Hardware baseline

- **Base:** iRobot Create 3 — Roomba i3 chassis, no vacuum. Encoders, IMU, optical floor
  tracking, cliff/bump/slip, self-docking. Removable faceplate w/ standard mount pattern, USB-C
  payload power, ROS 2 native. Education channels only — verify price/availability before
  purchase.
- **Compute:** Raspberry Pi 5 16GB on the faceplate, powered from the Create's USB-C. Ubuntu
  (for ROS 2 LTS), not Raspberry Pi OS. Claude Code via the native installer (no Node.js needed).
  Bring-up is `deploy/README.md` + `deploy/bootstrap.sh`; nothing is installed by hand.
- **Mic:** Seeed reSpeaker XVF3800 USB 4-Mic Array — far-field, hardware echo cancellation,
  direction-of-arrival. Non-negotiable. (Replaces the Mic Array v2.0; same family, newer chip.)
- **Speaker:** plugs into the mic array's 3.5mm jack, never into the Pi — the echo canceller
  only works against audio it played itself. Phase 0: a small powered speaker with 3.5mm input
  (Creative Pebble V2), USB power from a spare charger, not the Pi. On the robot: a bare
  speaker on the array's JST header and its 5W amp. Playback through the array is 16kHz;
  accept it, revisit in Phase 5.
- **Camera:** Pi Camera Module 3 on a short mast (~40–60cm) so it sees the desk, not table
  legs. Plan the faceplate around the mast in Phase 1. Needs the Pi 5 (22-pin) camera cable.
- **Optional:** RPLIDAR C1 for SLAM, Phase 5. **Network:** Tailscale, no port forwarding.

## Architecture (hold this line)

1. **Motion layer** — Python ROS 2 node exposing a narrow local HTTP API: `drive(distance_m)`,
   `turn(degrees)`, `dock()`, `undock()`, `pose()`, plus bumper/cliff/dock event stream. Only
   code that imports `rclpy`.
2. **Agent layer** — Python. Wake word, streaming STT, Claude conversation, streaming TTS,
   barge-in, memory. Built on Pipecat, calling the Anthropic Messages API directly; the Claude
   Agent SDK is *not* in the conversational path (seconds of startup per call) and is reserved
   for long background tasks, if ever. Calls motion API over localhost. Vendor picks and the
   reasoning: `docs/decisions/0001-voice-stack.md`.
3. **Integration layer** — MCP clients for Calendar, Gmail, Todoist as Claude tools.

Movement is **Claude tool use**, not a command parser: `drive_to`, `turn`, `dock`, `look`,
`remember(fact)`. Claude picks the sequence; the handler only executes. No intent classifier,
no rules engine in front of it.

**Bodies.** Ned is one identity that may later have more than one body (one per floor —
wheels do not do stairs, and never will; see Out of scope). Build for that from the first
commit, cheaply:

- Every motion and camera tool takes a `body` argument: an enum of known body IDs, exactly one
  value until a second body exists. Claude picks the body the way it picks the tool.
- Only the body that heard the wake word speaks. Other bodies execute silently.
- Location is a fact each body reports (floor, room, docked), never a constant in a prompt or
  tool description. No hardcoded "the office".
- Memory sits behind an interface from day one, even when the first backing store is a file.
- Each Pi's `/etc/ned/env` carries `NED_BODY`. Logs and metrics are tagged with it.
- Motion APIs bind to localhost today; with a second body they bind to the Tailscale
  interface with a shared secret. Nothing else changes.

## Deploy contract

- `main` is always deployable; nothing merges without CI green.
- **Auto-merge (Mike, 2026-09-09):** a PR you opened merges itself once CI is green on its
  head, no "merge" needed. Still say in chat that it merged and what to pull. Exceptions,
  which wait for an explicit "merge": anything touching `deploy/`, PROJECT.md, a decision
  record, or a change you flagged as uncertain in the PR body.
- Pi runs `ned-motion.service` and `ned-agent.service` under systemd.
- `deploy/update.sh` = git pull → deps sync → colcon build → restart units → hit `/healthz` on
  both → report. Only sanctioned deploy path.
- Secrets in `/etc/ned/env`, loaded by systemd. Never in the repo or a prompt file.
- Rollback = `git checkout <last-good-tag> && deploy/update.sh`. Tag every phase completion.
- Nothing runs on the Pi from outside a git checkout.

## Non-negotiable constraints

- **Latency is the product.** Wake word local; STT/LLM/TTS stream; TTS interruptible mid-word.
  Over ~2s dead air feels broken. Rules that follow from it:
  - Log per-stage timings on every turn (end of speech → transcript → first token → first
    audio → first sound out of the speaker), next to the cost line. Tune the silence timeout
    by ear on hardware, not in the cloud.
  - Keep persistent connections to STT and TTS. Send each sentence to TTS as it completes.
  - Run the model at low effort; thinking before answering is dead air. Fable-class models
    cannot be turned down enough for conversation and are not candidates for the voice loop.
  - System prompt and tool list are byte-stable across turns so prompt caching hits. Volatile
    facts (time, battery, location) go after the cached prefix.
  - A tool call doubles the round trip. Ned says a short line ("on my way") before a movement
    tool call in the same turn, so speech plays while the wheels start.
- **Safety stop.** Bumper/cliff cancels in-flight motion inside the motion layer, no LLM
  round-trip in the path.
- **Bounded movement.** Distance and angle clamped in the motion layer regardless of what the
  model asks. Never more than a couple meters per call.
- **Cost visibility.** Log per-conversation API spend from day one.
- **Cloud STT/LLM/TTS is fine.** No local inference in v1.
- **Camera on demand only.** A frame is captured only on an explicit `look` tool call, never
  continuously. It goes to Claude and is discarded unless `remember` stores it. A visible LED
  is on whenever the camera is live. Client calls happen in this office.

## Out of scope

- **Stairs.** A wheeled disc base cannot climb; the cliff sensors exist to keep it away from
  the edge. A second floor gets a second body, or Ned gets carried.
- **Local inference.** v1 is cloud STT/LLM/TTS.

## Phases

Each ends with a hardware observation logged in `STATUS.md` + a git tag.

**0 — Desk brain, no wheels.** Pi + mic + speaker on the desk, wake word → STT → Claude → TTS.
*Done when:* 3-turn spoken conversation from six feet away, no keyboard, at target latency. The
hard 80% — don't let hardware enthusiasm skip it.

**1 — Motion layer.** Create 3 + ROS 2 + the API node. *Done when:* `curl` drives it a meter
and back, bumper stream observable. Known gotcha: the Create 3 sleeps on the dock and can drop
USB-C payload power, rebooting the Pi mid-write. Keep it awake via ROS or shut the Pi down
cleanly before docking; decide here, not in Phase 2. Log battery % alongside API cost.

**2 — First tool loop.** `drive_to`, `turn` as tools. *Done when:* "Hey Ned, come here" across
the room makes it move and confirm verbally.

**3 — Senses.** Camera + `look`, on the mast, with the LED and the on-demand rule above.
*Done when:* "what's on my desk?" answered accurately.

**4 — Useful.** Calendar/Gmail/Todoist MCP tools. *Done when:* announces a meeting unprompted,
adds a task by voice.

**5 — Character and polish.** Persistent memory of the office and of Mike, Ned's personality,
ambient behaviors, optional LiDAR. Shared memory store is decided here; a second body (see
Bodies) is not bought until Phase 2 is signed off on the first one.

## How to work with him

- One phase at a time; never a wall of code.
- Complete runnable files, not fragments — these get executed, not read.
- When a robotics convention would surprise a .NET dev (ROS 2 node lifecycle, launch files,
  colcon workspaces, DDS discovery weirdness), name it and give the .NET analogue.
- Expect hardware problems. Ask for the real error and real `ros2 topic echo` output before
  theorizing.
- He works from his phone often. Keep replies scannable, and prefer a small next action he can
  trigger from a mobile session over a batch needing a keyboard.

## Known rough edges in the mobile workflow

Users have reported Remote Control sessions going stale after hours idle (tmux process alive and
attachable while the app spins), permission prompts not rendering on mobile in some versions,
and output arriving after completion rather than streaming.

Mitigate: fixed `--name`, always inside tmux so it can be reattached over SSH, and a
permission mode for the Ned repo that doesn't block on prompts.

## Decisions

Settled decisions live in `docs/decisions/` as numbered pages with their reasoning and
sources. Do not relitigate one without adding a new page that supersedes it.

- 0001 — Voice stack: pipeline, STT, TTS, wake word, listening mode, model. (Ubuntu 24.04 +
  ROS 2 Jazzy is recorded in `STATUS.md`; it gets its own page when Phase 1 starts.)
