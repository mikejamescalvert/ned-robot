# 0002 — Chat model: Sonnet 5 by default, tiered by activity later

Status: **accepted 2026-09-12.** Measured on the Pi over 24 turns: Claude first byte 900 ms
(was 1427 ms on Opus 5), first sound 1700 ms (was 1786 ms). Still over the 1.5 s target, but
the remaining gap is turn detection and TTS, not the model; see STATUS.md 2026-09-12.
Amends the LLM row of [0001](0001-voice-stack.md).

## Context

First hardware measurement, 18 turns at the desk, Opus 5 at `effort: low` with adaptive
thinking:

| stage | p50 |
|---|---|
| Deepgram Flux first byte | 75 ms |
| Anthropic first byte | **1427 ms** |
| Cartesia first byte | 139 ms |
| end of speech → first sound | 1786 ms |
| completion tokens per turn | 19 |

Target is 1.5 s to first sound; decision 0001 budgeted 500 ms for Claude. Opus 5 alone spent
nearly three times that, and the replies are 19 tokens, so no thinking is happening: it is
plain time-to-first-token for the largest model, from a Pi over home internet. Everything
else is inside budget. Mike raised the same point independently: a desk chat does not need
the top model, and model choice should follow what Ned is doing.

## Decision

1. **Sonnet 5 (`claude-sonnet-5`) is the default chat model.** Same `effort: low`, adaptive
   thinking. It is 2.5× cheaper per token and typically well under half the time to first
   token. `NED_MODEL` still overrides it per body.
2. **`NED_THINKING`** (`adaptive` default, `disabled` allowed) is the second lever, to be
   tried only if Sonnet adaptive is still over target. Not for Opus 5: with thinking off it
   can write tool calls as visible text.
3. **Tier by activity, later.** When Ned has tools that plan (navigation, multi-step
   errands), those turns can go to Opus 5 through a router that picks the model per turn;
   quick spoken replies stay on Sonnet. That is a Phase 2+ decision with its own number, not
   something to build before there is a tool to route.

## Consequences

- Cost per turn drops from about $0.002 to well under $0.001 before any other change.
- `ned-agent stats` reports `by_model` when the log spans both models, so the A/B is read
  from the same log without clearing it.
- The 0001 latency budget stands; this changes which model is expected to meet it.
