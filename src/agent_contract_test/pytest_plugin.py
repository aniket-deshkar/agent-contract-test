"""pytest fixture integration."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from .adapter import AgentAdapter
from .models import AgentContract, ContractReport
from .runner import assert_contract


@pytest.fixture
def contract_runner() -> Callable[[AgentContract, AgentAdapter], ContractReport]:
    """Return the assertion helper as an injectable pytest fixture."""
    return assert_contract
