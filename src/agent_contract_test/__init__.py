"""Framework-neutral behavioral contract testing for AI agents."""

from .adapter import AgentAdapter
from .evaluator import ContractEvaluator
from .fakes import FakeAgentAdapter, FakeTool, FakeToolRegistry
from .loading import load_contract, load_run
from .models import (
    AgentContract,
    AgentRun,
    ApprovalExpectation,
    CheckResult,
    ContractExpectations,
    ContractReport,
    ToolCall,
    ToolCallExpectation,
    UsageMetadata,
)
from .runner import (
    ContractViolationError,
    assert_contract,
    run_contract,
    run_contract_file,
)

__all__ = [
    "AgentAdapter",
    "AgentContract",
    "AgentRun",
    "ApprovalExpectation",
    "CheckResult",
    "ContractEvaluator",
    "ContractExpectations",
    "ContractReport",
    "ContractViolationError",
    "FakeAgentAdapter",
    "FakeTool",
    "FakeToolRegistry",
    "ToolCall",
    "ToolCallExpectation",
    "UsageMetadata",
    "assert_contract",
    "load_contract",
    "load_run",
    "run_contract",
    "run_contract_file",
]
