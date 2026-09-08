"""Memory behind an interface from day one (PROJECT.md, "Bodies"). Phase 0 ships the
interface and an in-memory implementation; a shared store replaces it in Phase 5 without
touching callers.
"""

from __future__ import annotations

from typing import Protocol


class Memory(Protocol):
    def remember(self, fact: str) -> None: ...
    def recall(self, limit: int = 20) -> list[str]: ...


class InMemory:
    def __init__(self) -> None:
        self._facts: list[str] = []

    def remember(self, fact: str) -> None:
        fact = fact.strip()
        if fact and fact not in self._facts:
            self._facts.append(fact)

    def recall(self, limit: int = 20) -> list[str]:
        return self._facts[-limit:]
