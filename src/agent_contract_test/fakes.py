"""Deterministic model and tool doubles for normal contract tests."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from .models import AgentContract, AgentRun


class FakeAgentAdapter:
    """Return a scripted run or derive one deterministically from the contract."""

    def __init__(self, script: AgentRun | Callable[[AgentContract], AgentRun]) -> None:
        self._script = script
        self.contracts: list[AgentContract] = []

    def run(self, contract: AgentContract) -> AgentRun:
        """Record the contract and return an isolated run value."""
        self.contracts.append(contract.model_copy(deep=True))
        run = self._script(contract) if callable(self._script) else self._script
        return run.model_copy(deep=True)


@dataclass
class FakeTool:
    """Callable tool with a fixed result and recorded arguments."""

    name: str
    result: Any = None
    error: Exception | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, **arguments: Any) -> Any:
        self.calls.append(deepcopy(arguments))
        if self.error is not None:
            raise self.error
        return deepcopy(self.result)


class FakeToolRegistry:
    """Named collection of deterministic fake tools."""

    def __init__(self, *tools: FakeTool) -> None:
        self._tools = {tool.name: tool for tool in tools}
        if len(self._tools) != len(tools):
            raise ValueError("fake tool names must be unique")

    def invoke(self, name: str, arguments: dict[str, Any]) -> Any:
        """Invoke a registered tool or fail loudly for unknown names."""
        try:
            tool = self._tools[name]
        except KeyError as error:
            raise KeyError(f"unknown fake tool: {name}") from error
        return tool(**arguments)

    def tool(self, name: str) -> FakeTool:
        """Return a fake for call assertions."""
        return self._tools[name]
