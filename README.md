# ned-robot

Ned is a small office robot that listens, talks, and acts. Start with `PROJECT.md` (the rules),
then `STATUS.md` (where things stand), then `docs/decisions/` (why).

- `ned/` — the agent (Python, Pipecat). `uv sync --extra dev && uv run pytest`
- `deploy/` — Pi bring-up and the deploy path
- `prompts/` — system prompts, versioned
- `models/` — wake word model
