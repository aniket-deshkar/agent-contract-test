from __future__ import annotations

import pytest

from agent_contract_test import (
    AgentContract,
    AgentRun,
    ContractExpectations,
    ContractViolationError,
    FakeAgentAdapter,
    FakeTool,
    FakeToolRegistry,
    assert_contract,
)


def test_fake_agent_records_contract_and_returns_deep_copies() -> None:
    scripted = AgentRun(response={"items": []}, agent_steps=1, model_calls=1)
    adapter = FakeAgentAdapter(scripted)
    contract = AgentContract(name="copy", expect=ContractExpectations())

    first = adapter.run(contract)
    first.response["items"].append("mutated")
    second = adapter.run(contract)

    assert second.response == {"items": []}
    assert len(adapter.contracts) == 2


def test_fake_tools_record_calls_return_copies_and_raise_scripted_errors() -> None:
    search = FakeTool("search", result={"hits": [1]})
    broken = FakeTool("broken", error=RuntimeError("offline"))
    registry = FakeToolRegistry(search, broken)

    result = registry.invoke("search", {"query": "agent"})
    result["hits"].append(2)

    assert registry.invoke("search", {"query": "again"}) == {"hits": [1]}
    assert search.calls == [{"query": "agent"}, {"query": "again"}]
    with pytest.raises(RuntimeError, match="offline"):
        registry.invoke("broken", {})
    with pytest.raises(KeyError, match="unknown fake tool"):
        registry.invoke("unknown", {})


def test_assert_contract_reports_all_failures() -> None:
    contract = AgentContract(
        name="failures",
        expect=ContractExpectations(required_tool_calls=[{"name": "search"}], max_agent_steps=0),
    )
    adapter = FakeAgentAdapter(AgentRun(response="none", agent_steps=1, model_calls=0))

    with pytest.raises(ContractViolationError) as captured:
        assert_contract(contract, adapter)

    assert "tool.required" in str(captured.value)
    assert "budget.agent_steps" in str(captured.value)


def test_pytest_fixture_executes_contract(contract_runner) -> None:
    contract = AgentContract(name="fixture", expect=ContractExpectations())
    adapter = FakeAgentAdapter(AgentRun(response="ok", agent_steps=0, model_calls=0))

    assert contract_runner(contract, adapter).passed
