from __future__ import annotations

import json
from pathlib import Path

from agent_contract_test.cli import main


def write_contract(path) -> None:
    path.write_text(
        """
version: "1"
name: cli-contract
input: {}
expect:
  required_tool_calls:
    - name: search
  max_model_calls: 1
""".lstrip(),
        encoding="utf-8",
    )


def test_cli_writes_passing_machine_report(tmp_path, capsys) -> None:
    contract = tmp_path / "contract.yaml"
    fixture = tmp_path / "run.json"
    report = tmp_path / "artifacts" / "report.json"
    write_contract(contract)
    fixture.write_text(
        json.dumps(
            {
                "response": "found",
                "tool_calls": [{"name": "search", "arguments": {}}],
                "agent_steps": 1,
                "model_calls": 1,
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(["run", str(contract), "--run-fixture", str(fixture), "--report", str(report)])

    stdout = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert stdout["passed"] is True
    assert json.loads(report.read_text(encoding="utf-8"))["contract"] == "cli-contract"


def test_cli_returns_one_for_contract_failure(tmp_path, capsys) -> None:
    contract = tmp_path / "contract.yaml"
    fixture = tmp_path / "run.json"
    write_contract(contract)
    fixture.write_text(
        json.dumps({"response": "none", "agent_steps": 1, "model_calls": 2}),
        encoding="utf-8",
    )

    exit_code = main(["run", str(contract), "--run-fixture", str(fixture)])

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert report["passed"] is False
    assert {check["code"] for check in report["checks"] if not check["passed"]} == {
        "tool.required",
        "budget.model_calls",
    }


def test_cli_returns_two_for_invalid_input(tmp_path, capsys) -> None:
    missing = tmp_path / "missing.yaml"

    assert main(["run", str(missing), "--run-fixture", str(missing)]) == 2
    assert "file does not exist" in capsys.readouterr().err


def test_cli_loads_adapter_factory_from_working_directory(capsys) -> None:
    contract = Path("examples/order-contract.yaml")

    exit_code = main(["run", str(contract), "--adapter", "examples.fake_adapter:create_adapter"])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["passed"] is True
