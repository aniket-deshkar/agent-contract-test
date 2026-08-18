"""Public orchestration and assertion API."""

from __future__ import annotations

from pathlib import Path

from .adapter import AgentAdapter
from .evaluator import ContractEvaluator
from .loading import load_contract
from .models import AgentContract, ContractReport


class ContractViolationError(AssertionError):
    """Raised by assertion helpers with all failed checks."""


def run_contract(contract: AgentContract, adapter: AgentAdapter) -> ContractReport:
    """Execute an adapter and evaluate its normalized run."""
    return ContractEvaluator().evaluate(contract, adapter.run(contract))


def run_contract_file(path: str | Path, adapter: AgentAdapter) -> ContractReport:
    """Load, execute, and evaluate a contract file."""
    return run_contract(load_contract(path), adapter)


def assert_contract(contract: AgentContract, adapter: AgentAdapter) -> ContractReport:
    """Return a passing report or raise an assertion suitable for pytest."""
    report = run_contract(contract, adapter)
    if not report.passed:
        failures = "\n".join(
            f"- [{check.code}] {check.message}" for check in report.checks if not check.passed
        )
        raise ContractViolationError(f"Contract '{contract.name}' failed:\n{failures}")
    return report
