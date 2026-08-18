"""Framework-neutral adapter service-provider interface."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import AgentContract, AgentRun


@runtime_checkable
class AgentAdapter(Protocol):
    """Maps a framework-specific agent execution into :class:`AgentRun`."""

    def run(self, contract: AgentContract) -> AgentRun:
        """Execute the contract input and return a normalized transcript."""
        ...
