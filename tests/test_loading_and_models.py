from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from agent_contract_test import load_contract, load_run


def test_loads_equivalent_yaml_and_json_contracts(tmp_path) -> None:
    yaml_path = tmp_path / "contract.yaml"
    yaml_path.write_text(
        'version: "1"\nname: portable\ninput: {}\nexpect:\n  max_agent_steps: 2\n',
        encoding="utf-8",
    )
    json_path = tmp_path / "contract.json"
    json_path.write_text(
        json.dumps(
            {"version": "1", "name": "portable", "input": {}, "expect": {"max_agent_steps": 2}}
        ),
        encoding="utf-8",
    )

    assert load_contract(yaml_path) == load_contract(json_path)


def test_safe_yaml_loader_rejects_python_object_tags(tmp_path) -> None:
    path = tmp_path / "unsafe.yaml"
    path.write_text("!!python/object/apply:os.system ['echo unsafe']", encoding="utf-8")

    with pytest.raises(ValueError, match="could not determine a constructor"):
        load_contract(path)


def test_unknown_fields_and_conflicting_tools_are_rejected(tmp_path) -> None:
    unknown = tmp_path / "unknown.json"
    unknown.write_text(json.dumps({"name": "bad", "expect": {}, "typo": True}), encoding="utf-8")
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        load_contract(unknown)

    conflict = tmp_path / "conflict.json"
    conflict.write_text(
        json.dumps(
            {
                "name": "bad",
                "expect": {
                    "required_tool_calls": [{"name": "write"}],
                    "forbidden_tool_calls": ["write"],
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="both required and forbidden"):
        load_contract(conflict)


def test_load_run_validates_non_negative_counters(tmp_path) -> None:
    path = tmp_path / "run.json"
    path.write_text(
        json.dumps({"response": "ok", "agent_steps": -1, "model_calls": 0}),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_run(path)
