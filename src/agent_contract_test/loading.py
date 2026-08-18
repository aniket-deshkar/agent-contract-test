"""Safe YAML and JSON contract loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .models import AgentContract, AgentRun


def load_contract(path: str | Path) -> AgentContract:
    """Load and validate a contract based on its file extension."""
    source = Path(path)
    data = _load_mapping(source)
    return AgentContract.model_validate(data)


def load_run(path: str | Path) -> AgentRun:
    """Load a deterministic run fixture from YAML or JSON."""
    return AgentRun.model_validate(_load_mapping(Path(path)))


def _load_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"file does not exist: {path}")
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            value = json.loads(text)
        elif suffix in {".yaml", ".yml"}:
            value = yaml.safe_load(text)
        else:
            raise ValueError(f"expected a .json, .yaml, or .yml file: {path}")
    except (json.JSONDecodeError, yaml.YAMLError) as error:
        raise ValueError(f"invalid document {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"document root must be an object: {path}")
    return value
