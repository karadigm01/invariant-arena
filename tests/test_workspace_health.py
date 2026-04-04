from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import inf_work.workspace_health as workspace_health_module
from inf_work.workspace_health import validate_workspace


def write_core_reference(workspace_root: Path) -> None:
    payload = {
        "workspace_governance": {
            "directory_structure": {
                "ai_docs/": "AI docs",
                "knowledge_base/": "Knowledge base",
                "src/": "Source code",
                "tests/": "Tests",
                "config/": "Configuration",
                "build/": "Build artifacts",
            }
        }
    }
    (workspace_root / "core_reference.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_validate_workspace_reports_missing_directories(tmp_path: Path) -> None:
    write_core_reference(tmp_path)
    (tmp_path / "ai_docs").mkdir()
    (tmp_path / "knowledge_base").mkdir()
    (tmp_path / "src").mkdir()

    result = validate_workspace(tmp_path)

    assert result.compliant is False
    assert result.workspace_root == str(tmp_path.resolve())
    assert result.missing_directories == ["build", "config", "tests"]
    assert result.present_directories == ["ai_docs", "knowledge_base", "src"]
    assert [rule_result.rule_id for rule_result in result.rule_results] == ["workspace.required_directories_present"]


def test_validate_workspace_reports_compliance(tmp_path: Path) -> None:
    write_core_reference(tmp_path)
    for directory_name in ["ai_docs", "knowledge_base", "src", "tests", "config", "build"]:
        (tmp_path / directory_name).mkdir()

    result = validate_workspace(tmp_path)

    assert result.compliant is True
    assert result.workspace_root == str(tmp_path.resolve())
    assert result.missing_directories == []
    assert result.required_directories == ["ai_docs", "build", "config", "knowledge_base", "src", "tests"]
    assert [rule_result.rule_id for rule_result in result.rule_results] == ["workspace.required_directories_present"]


def test_build_workspace_context_reports_exact_payload(tmp_path: Path) -> None:
    write_core_reference(tmp_path)
    (tmp_path / "ai_docs").mkdir()
    (tmp_path / "src").mkdir()

    context = workspace_health_module._build_workspace_context(tmp_path)

    assert set(context) == {
        "workspace_root",
        "required_directories",
        "present_directories",
        "missing_directories",
    }
    assert context["workspace_root"] == str(tmp_path.resolve())
    assert context["required_directories"] == ["ai_docs", "build", "config", "knowledge_base", "src", "tests"]
    assert context["present_directories"] == ["ai_docs", "src"]
    assert context["missing_directories"] == ["build", "config", "knowledge_base", "tests"]


def test_evaluate_required_directories_present_reports_rule_findings() -> None:
    findings = workspace_health_module._evaluate_required_directories_present(
        {
            "missing_directories": ["build", "tests"],
        }
    )

    assert [finding.item_identifier for finding in findings] == ["build", "tests"]
    assert [finding.message for finding in findings] == [
        "Missing required directory: build",
        "Missing required directory: tests",
    ]
    assert all(finding.source_file == "core_reference.json" for finding in findings)
    assert all(finding.field_name == "workspace_governance.directory_structure" for finding in findings)


def test_validate_workspace_forwards_rule_selection_to_rule_runner(monkeypatch, tmp_path: Path) -> None:
    write_core_reference(tmp_path)

    expected_rule_ids = {"workspace.required_directories_present"}

    def fake_run_registered_rules(domain, context, rule_ids):
        assert domain == "workspace"
        assert context["workspace_root"] == str(tmp_path.resolve())
        assert rule_ids == expected_rule_ids
        return []

    monkeypatch.setattr(workspace_health_module, "run_registered_rules", fake_run_registered_rules)

    result = workspace_health_module.validate_workspace(tmp_path, expected_rule_ids)

    assert result.compliant is True
    assert result.rule_results == []


def test_cli_outputs_json_for_current_workspace() -> None:
    workspace_root = Path(__file__).resolve().parents[1]
    environment = {
        **os.environ,
        "PYTHONPATH": str(workspace_root / "src"),
    }
    completed = subprocess.run(
        [sys.executable, "-m", "inf_work", str(workspace_root), "--pretty"],
        check=False,
        capture_output=True,
        text=True,
        cwd=workspace_root,
        env=environment,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["compliant"] is True
    assert "src" in payload["present_directories"]


def test_unified_workspace_subcommand_outputs_json_for_current_workspace() -> None:
    workspace_root = Path(__file__).resolve().parents[1]
    environment = {
        **os.environ,
        "PYTHONPATH": str(workspace_root / "src"),
    }
    completed = subprocess.run(
        [sys.executable, "-m", "inf_work", "workspace", str(workspace_root), "--pretty"],
        check=False,
        capture_output=True,
        text=True,
        cwd=workspace_root,
        env=environment,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["compliant"] is True
    assert "src" in payload["present_directories"]


def test_unified_all_subcommand_outputs_workspace_results_for_current_workspace() -> None:
    workspace_root = Path(__file__).resolve().parents[1]
    environment = {
        **os.environ,
        "PYTHONPATH": str(workspace_root / "src"),
    }
    completed = subprocess.run(
        [sys.executable, "-m", "inf_work", "all", str(workspace_root), "--pretty"],
        check=False,
        capture_output=True,
        text=True,
        cwd=workspace_root,
        env=environment,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["compliant"] is True
    assert payload["workspace"]["compliant"] is True
    assert payload["knowledge_base"]["compliant"] is True
    assert "src" in payload["workspace"]["present_directories"]
