"""Deterministic behavioral contract evaluation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from .models import AgentContract, AgentRun, CheckResult, ContractReport, ToolCallExpectation


class ContractEvaluator:
    """Evaluate a normalized agent run without invoking a model."""

    def evaluate(self, contract: AgentContract, run: AgentRun) -> ContractReport:
        """Return every check instead of stopping at the first failure."""
        checks: list[CheckResult] = []
        checks.extend(self._required_tools(contract, run))
        checks.extend(self._forbidden_tools(contract, run))
        checks.append(self._tool_order(contract, run))
        checks.extend(self._budgets(contract, run))
        checks.append(self._response_schema(contract, run))
        checks.extend(self._approvals(contract, run))
        return ContractReport(
            contract=contract.name,
            passed=all(check.passed for check in checks),
            checks=checks,
            run=run,
        )

    def _required_tools(self, contract: AgentContract, run: AgentRun) -> list[CheckResult]:
        available = set(range(len(run.tool_calls)))
        results: list[CheckResult] = []
        for expected in contract.expect.required_tool_calls:
            match = next(
                (
                    index
                    for index in sorted(available)
                    if self._matches(
                        expected, run.tool_calls[index].name, run.tool_calls[index].arguments
                    )
                ),
                None,
            )
            passed = match is not None
            if match is not None:
                available.remove(match)
            results.append(
                CheckResult(
                    code="tool.required",
                    passed=passed,
                    message=(
                        f"required tool call observed: {expected.name}"
                        if passed
                        else f"required tool call missing: {expected.name}"
                    ),
                    details={"tool": expected.name, "arguments": expected.arguments},
                )
            )
        return results

    def _forbidden_tools(self, contract: AgentContract, run: AgentRun) -> list[CheckResult]:
        observed = [call.name for call in run.tool_calls]
        return [
            CheckResult(
                code="tool.forbidden",
                passed=tool not in observed,
                message=(
                    f"forbidden tool was not called: {tool}"
                    if tool not in observed
                    else f"forbidden tool was called: {tool}"
                ),
                details={"tool": tool},
            )
            for tool in contract.expect.forbidden_tool_calls
        ]

    def _tool_order(self, contract: AgentContract, run: AgentRun) -> CheckResult:
        expected = contract.expect.tool_order
        observed = [call.name for call in run.tool_calls]
        cursor = 0
        for name in observed:
            if cursor < len(expected) and name == expected[cursor]:
                cursor += 1
        passed = cursor == len(expected)
        return CheckResult(
            code="tool.order",
            passed=passed,
            message="required tool order satisfied"
            if passed
            else "required tool order not satisfied",
            details={"expected": expected, "observed": observed},
        )

    def _budgets(self, contract: AgentContract, run: AgentRun) -> list[CheckResult]:
        expected = contract.expect
        checks = [
            self._maximum("budget.agent_steps", expected.max_agent_steps, run.agent_steps),
            self._maximum("budget.model_calls", expected.max_model_calls, run.model_calls),
        ]
        checks.append(
            self._maximum(
                "budget.tokens",
                expected.max_tokens,
                run.usage.tokens if run.usage is not None else None,
                optional_metadata=True,
            )
        )
        checks.append(
            self._maximum(
                "budget.cost",
                expected.max_cost,
                run.usage.cost if run.usage is not None else None,
                optional_metadata=True,
            )
        )
        return checks

    def _maximum(
        self,
        code: str,
        maximum: int | float | None,
        actual: int | float | None,
        *,
        optional_metadata: bool = False,
    ) -> CheckResult:
        if maximum is None:
            return CheckResult(code=code, passed=True, message="budget not configured")
        if actual is None and optional_metadata:
            return CheckResult(
                code=code,
                passed=True,
                message="usage metadata unavailable; budget not evaluated",
                details={"maximum": maximum, "available": False},
            )
        passed = actual is not None and actual <= maximum
        return CheckResult(
            code=code,
            passed=passed,
            message=(
                f"observed {actual} within maximum {maximum}"
                if passed
                else f"observed {actual} exceeds maximum {maximum}"
            ),
            details={"maximum": maximum, "actual": actual},
        )

    def _response_schema(self, contract: AgentContract, run: AgentRun) -> CheckResult:
        schema = contract.expect.response_schema
        if schema is None:
            return CheckResult(
                code="response.schema", passed=True, message="response schema not configured"
            )
        try:
            Draft202012Validator.check_schema(schema)
            errors = sorted(
                Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(
                    run.response
                ),
                key=lambda error: list(error.absolute_path),
            )
        except SchemaError as error:
            return CheckResult(
                code="response.schema",
                passed=False,
                message=f"contract contains an invalid response schema: {error.message}",
            )
        messages = [
            f"{'/'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
            for error in errors
        ]
        return CheckResult(
            code="response.schema",
            passed=not errors,
            message="response matches JSON Schema"
            if not errors
            else "response violates JSON Schema",
            details={"errors": messages},
        )

    def _approvals(self, contract: AgentContract, run: AgentRun) -> list[CheckResult]:
        checks: list[CheckResult] = []
        for expected in contract.expect.approvals:
            calls = [call for call in run.tool_calls if call.name == expected.tool]
            passed = bool(calls)
            if expected.required:
                passed = passed and all(call.approval_requested for call in calls)
            else:
                passed = passed and all(not call.approval_requested for call in calls)
            if expected.granted is not None:
                passed = passed and all(call.approval_granted is expected.granted for call in calls)
            checks.append(
                CheckResult(
                    code="approval.requirement",
                    passed=passed,
                    message=(
                        f"approval contract satisfied for {expected.tool}"
                        if passed
                        else f"approval contract violated for {expected.tool}"
                    ),
                    details=expected.model_dump(),
                )
            )
        return checks

    def _matches(self, expected: ToolCallExpectation, name: str, arguments: dict[str, Any]) -> bool:
        return expected.name == name and (
            expected.arguments is None or _is_deep_subset(expected.arguments, arguments)
        )


def _is_deep_subset(expected: Any, actual: Any) -> bool:
    if isinstance(expected, Mapping):
        return isinstance(actual, Mapping) and all(
            key in actual and _is_deep_subset(value, actual[key]) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(expected) == len(actual)
            and all(
                _is_deep_subset(left, right) for left, right in zip(expected, actual, strict=True)
            )
        )
    return expected == actual
