"""Dependency-light command-line interface."""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .adapter import AgentAdapter
from .fakes import FakeAgentAdapter
from .loading import load_contract, load_run
from .runner import run_contract


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for direct testing and shell completion tools."""
    parser = argparse.ArgumentParser(prog="agent-contract-test")
    subcommands = parser.add_subparsers(dest="command", required=True)
    run = subcommands.add_parser("run", help="execute one YAML or JSON contract")
    run.add_argument("contract", type=Path)
    source = run.add_mutually_exclusive_group(required=True)
    source.add_argument("--adapter", help="adapter factory as module:attribute")
    source.add_argument("--run-fixture", type=Path, help="deterministic AgentRun YAML or JSON")
    run.add_argument("--report", type=Path, help="also write the JSON report to this path")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a stable process exit code."""
    arguments = build_parser().parse_args(argv)
    try:
        contract = load_contract(arguments.contract)
        adapter = (
            _load_adapter(arguments.adapter)
            if arguments.adapter
            else FakeAgentAdapter(load_run(arguments.run_fixture))
        )
        report = run_contract(contract, adapter)
        rendered = report.model_dump_json(indent=2)
        print(rendered)
        if arguments.report:
            arguments.report.parent.mkdir(parents=True, exist_ok=True)
            arguments.report.write_text(rendered + "\n", encoding="utf-8")
        return 0 if report.passed else 1
    except (
        FileNotFoundError,
        ValueError,
        ImportError,
        AttributeError,
        TypeError,
        ValidationError,
    ) as error:
        print(f"agent-contract-test: {error}", file=sys.stderr)
        return 2


def _load_adapter(reference: str) -> AgentAdapter:
    module_name, separator, attribute_name = reference.partition(":")
    if not separator or not module_name or not attribute_name:
        raise ValueError("adapter must use module:attribute syntax")
    working_directory = str(Path.cwd())
    if working_directory not in sys.path:
        sys.path.insert(0, working_directory)
    value: Any = getattr(importlib.import_module(module_name), attribute_name)
    adapter = (
        value()
        if isinstance(value, type) or (callable(value) and not hasattr(value, "run"))
        else value
    )
    if not isinstance(adapter, AgentAdapter):
        raise TypeError(f"adapter does not implement run(contract): {reference}")
    return adapter
