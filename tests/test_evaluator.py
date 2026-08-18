from __future__ import annotations

import pytest

from agent_contract_test import (
    AgentContract,
    AgentRun,
    ContractEvaluator,
    ContractExpectations,
    ToolCall,
    ToolCallExpectation,
    UsageMetadata,
)
from agent_contract_test.models import ApprovalExpectation


def contract(**expectations: object) -> AgentContract:
    return AgentContract(
        name="test-contract",
        input={"request": "hello"},
        expect=ContractExpectations(**expectations),
    )


def run(**overrides: object) -> AgentRun:
    values = {"response": {"status": "ok"}, "agent_steps": 2, "model_calls": 1}
    values.update(overrides)
    return AgentRun(**values)


def check(report, code: str, occurrence: int = 0):
    return [item for item in report.checks if item.code == code][occurrence]


def test_passing_contract_covers_tools_order_budgets_schema_and_approval() -> None:
    specification = contract(
        required_tool_calls=[
            ToolCallExpectation(name="search", arguments={"query": "spring"}),
            ToolCallExpectation(name="save", arguments={"record": {"id": 7}}),
        ],
        forbidden_tool_calls=["delete"],
        tool_order=["search", "save"],
        max_agent_steps=3,
        max_model_calls=2,
        max_tokens=100,
        max_cost=0.1,
        response_schema={
            "type": "object",
            "required": ["status"],
            "properties": {"status": {"const": "ok"}},
        },
        approvals=[ApprovalExpectation(tool="save", granted=True)],
    )
    execution = run(
        tool_calls=[
            ToolCall(name="search", arguments={"query": "spring", "limit": 5}),
            ToolCall(
                name="save",
                arguments={"record": {"id": 7, "label": "kept"}},
                approval_requested=True,
                approval_granted=True,
            ),
        ],
        usage=UsageMetadata(tokens=80, cost=0.05),
    )

    report = ContractEvaluator().evaluate(specification, execution)

    assert report.passed
    assert all(item.passed for item in report.checks)


@pytest.mark.parametrize(
    ("expectations", "execution", "code"),
    [
        (
            {"required_tool_calls": [{"name": "missing"}]},
            run(),
            "tool.required",
        ),
        (
            {"forbidden_tool_calls": ["delete"]},
            run(tool_calls=[ToolCall(name="delete")]),
            "tool.forbidden",
        ),
        (
            {"tool_order": ["search", "save"]},
            run(tool_calls=[ToolCall(name="save"), ToolCall(name="search")]),
            "tool.order",
        ),
        ({"max_agent_steps": 1}, run(agent_steps=2), "budget.agent_steps"),
        ({"max_model_calls": 0}, run(model_calls=1), "budget.model_calls"),
        (
            {"max_tokens": 10},
            run(usage=UsageMetadata(tokens=11)),
            "budget.tokens",
        ),
        (
            {"max_cost": 0.01},
            run(usage=UsageMetadata(cost=0.02)),
            "budget.cost",
        ),
        (
            {"response_schema": {"type": "object", "required": ["id"]}},
            run(response={}),
            "response.schema",
        ),
        (
            {"approvals": [{"tool": "write", "required": True}]},
            run(tool_calls=[ToolCall(name="write", approval_requested=False)]),
            "approval.requirement",
        ),
    ],
)
def test_contract_failures_are_machine_readable(
    expectations: dict[str, object], execution: AgentRun, code: str
) -> None:
    report = ContractEvaluator().evaluate(contract(**expectations), execution)

    assert not report.passed
    assert not check(report, code).passed
    assert report.model_dump(mode="json")["schema_version"] == "1"


def test_missing_optional_usage_metadata_does_not_fail_budget() -> None:
    report = ContractEvaluator().evaluate(contract(max_tokens=10, max_cost=0.01), run())

    assert report.passed
    assert check(report, "budget.tokens").details == {"maximum": 10, "available": False}


def test_repeated_required_tool_expectations_need_distinct_calls() -> None:
    specification = contract(required_tool_calls=[{"name": "search"}, {"name": "search"}])

    report = ContractEvaluator().evaluate(specification, run(tool_calls=[ToolCall(name="search")]))

    assert not report.passed
    assert check(report, "tool.required", 0).passed
    assert not check(report, "tool.required", 1).passed


def test_invalid_json_schema_is_a_contract_failure() -> None:
    report = ContractEvaluator().evaluate(
        contract(response_schema={"type": "not-a-json-schema-type"}), run()
    )

    assert not report.passed
    assert "invalid response schema" in check(report, "response.schema").message
