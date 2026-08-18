"""Validated contract, execution, and report models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Base model that rejects misspelled contract fields."""

    model_config = ConfigDict(extra="forbid")


class ToolCallExpectation(StrictModel):
    """Expected tool name and optional deep-subset argument constraints."""

    name: str = Field(min_length=1)
    arguments: dict[str, Any] | None = None


class ApprovalExpectation(StrictModel):
    """Approval contract for every call to a named tool."""

    tool: str = Field(min_length=1)
    required: bool = True
    granted: bool | None = None


class ContractExpectations(StrictModel):
    """Behavioral invariants evaluated against an agent run."""

    required_tool_calls: list[ToolCallExpectation] = Field(default_factory=list)
    forbidden_tool_calls: list[str] = Field(default_factory=list)
    tool_order: list[str] = Field(default_factory=list)
    max_agent_steps: int | None = Field(default=None, ge=0)
    max_model_calls: int | None = Field(default=None, ge=0)
    max_tokens: int | None = Field(default=None, ge=0)
    max_cost: float | None = Field(default=None, ge=0)
    response_schema: dict[str, Any] | None = None
    approvals: list[ApprovalExpectation] = Field(default_factory=list)


class AgentContract(StrictModel):
    """Versioned, portable contract loaded from YAML or JSON."""

    version: Literal["1"] = "1"
    name: str = Field(min_length=1)
    description: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    expect: ContractExpectations

    @model_validator(mode="after")
    def validate_tool_sets(self) -> AgentContract:
        required = {item.name for item in self.expect.required_tool_calls}
        forbidden = set(self.expect.forbidden_tool_calls)
        overlap = required & forbidden
        if overlap:
            names = ", ".join(sorted(overlap))
            raise ValueError(f"tools cannot be both required and forbidden: {names}")
        return self


class ToolCall(StrictModel):
    """One observed agent tool call."""

    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    approval_requested: bool = False
    approval_granted: bool | None = None
    result: Any = None


class UsageMetadata(StrictModel):
    """Optional provider usage metadata."""

    tokens: int | None = Field(default=None, ge=0)
    cost: float | None = Field(default=None, ge=0)


class AgentRun(StrictModel):
    """Framework-neutral execution transcript returned by an adapter."""

    response: Any
    tool_calls: list[ToolCall] = Field(default_factory=list)
    agent_steps: int = Field(ge=0)
    model_calls: int = Field(ge=0)
    usage: UsageMetadata | None = None


class CheckResult(StrictModel):
    """One stable machine-readable assertion outcome."""

    code: str
    passed: bool
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ContractReport(StrictModel):
    """Complete result for one contract execution."""

    schema_version: Literal["1"] = "1"
    contract: str
    passed: bool
    checks: list[CheckResult]
    run: AgentRun
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
