from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
GOVERNED_TOP_LEVEL_FILES = [
    "core_reference.json",
    "behavioral_directives.json",
    "README.md",
    "pyproject.toml",
    "SYSTEM_STATUS.md",
    "SYSTEM_SUMMARY.md",
]
GOVERNED_TOP_LEVEL_DIRECTORIES = [
    "ai_docs",
    "build",
    "config",
    "knowledge_base",
    "src",
    "tests",
]


def _copy_governed_workspace(tmp_path: Path) -> Path:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    for file_name in GOVERNED_TOP_LEVEL_FILES:
        shutil.copy2(REPO_ROOT / file_name, workspace_root / file_name)

    for directory_name in GOVERNED_TOP_LEVEL_DIRECTORIES:
        shutil.copytree(
            REPO_ROOT / directory_name,
            workspace_root / directory_name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )

    backups_path = workspace_root / "ai_docs" / "backups"
    if backups_path.exists():
        shutil.rmtree(backups_path)

    return workspace_root


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_stale_status_artifacts(workspace_root: Path) -> None:
    snapshot_path = workspace_root / "ai_docs" / "system_status_snapshot.json"
    snapshot_payload = _read_json(snapshot_path)
    snapshot_payload["generated_at"] = "2026-03-01T00:00:00Z"
    snapshot_payload["workspace_root"] = "/tmp/stale-workspace"
    snapshot_path.write_text(json.dumps(snapshot_payload, indent=2), encoding="utf-8")
    (workspace_root / "SYSTEM_STATUS.md").write_text("# stale status\n", encoding="utf-8")
    (workspace_root / "SYSTEM_SUMMARY.md").write_text("# stale summary\n", encoding="utf-8")


def _build_pythonpath(*extra_entries: Path) -> str:
    entries = [str(path) for path in extra_entries if path is not None]
    entries.append(str(REPO_ROOT / "src"))
    existing_pythonpath = os.environ.get("PYTHONPATH")
    if existing_pythonpath:
        entries.append(existing_pythonpath)
    return os.pathsep.join(entries)


def _run_inf_work(
    workspace_root: Path,
    *args: str,
    extra_env: dict[str, str] | None = None,
    extra_pythonpath_entries: list[Path] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = {
        **os.environ,
        "PYTHONPATH": _build_pythonpath(*(extra_pythonpath_entries or [])),
    }
    if extra_env:
        environment.update(extra_env)

    return subprocess.run(
        [sys.executable, "-m", "inf_work", *args],
        check=False,
        capture_output=True,
        text=True,
        cwd=workspace_root,
        env=environment,
    )


def _create_summary_failure_hook(tmp_path: Path, workspace_root: Path) -> Path:
    hook_root = tmp_path / "hook"
    hook_root.mkdir(parents=True, exist_ok=True)
    (hook_root / "sitecustomize.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import os",
                "from pathlib import Path",
                "",
                "import inf_work.remediation as remediation_module",
                "from inf_work.rules import RuleFinding, RuleResult",
                "from inf_work.system_status import StatusValidationIssue, StatusValidationResult",
                "",
                "_ORIGINAL_VALIDATE_SYSTEM_SUMMARY = remediation_module.validate_system_summary",
                "_TARGET_ROOT = Path(os.environ['INF_WORK_FAIL_WORKSPACE_ROOT']).resolve()",
                "",
                "def _forced_summary_failure(workspace_root, *args, **kwargs):",
                "    resolved_root = Path(workspace_root).resolve()",
                "    if os.environ.get('INF_WORK_FORCE_SUMMARY_VALIDATION_FAILURE') == '1' and resolved_root == _TARGET_ROOT:",
                "        return StatusValidationResult(",
                "            workspace_root=str(resolved_root),",
                "            snapshot_path='ai_docs/system_status_snapshot.json',",
                "            markdown_path='SYSTEM_STATUS.md',",
                "            summary_path='SYSTEM_SUMMARY.md',",
                "            compliant=False,",
                "            issues=[",
                "                StatusValidationIssue(",
                "                    source_file='SYSTEM_SUMMARY.md',",
                "                    item_identifier='summary',",
                "                    field_name='content',",
                "                    message='Forced summary validation failure for subprocess rollback coverage.',",
                "                )",
                "            ],",
                "            rule_results=[",
                "                RuleResult(",
                "                    rule_id='status.summary_matches_workspace',",
                "                    domain='status',",
                "                    category='artifact_integrity',",
                "                    severity='error',",
                "                    description='Forced summary mismatch for rollback coverage.',",
                "                    passed=False,",
                "                    findings=[",
                "                        RuleFinding(",
                "                            message='forced failure',",
                "                            source_file='SYSTEM_SUMMARY.md',",
                "                            item_identifier='summary',",
                "                            field_name='content',",
                "                        )",
                "                    ],",
                "                )",
                "            ],",
                "        )",
                "    return _ORIGINAL_VALIDATE_SYSTEM_SUMMARY(workspace_root, *args, **kwargs)",
                "",
                "remediation_module.validate_system_summary = _forced_summary_failure",
            ]
        ),
        encoding="utf-8",
    )
    return hook_root


def test_remediation_plan_cli_compiles_status_plan_for_stale_workspace(tmp_path: Path) -> None:
    workspace_root = _copy_governed_workspace(tmp_path)
    _write_stale_status_artifacts(workspace_root)

    completed = _run_inf_work(workspace_root, "remediation-plan", str(workspace_root), "--pretty")

    assert completed.returncode == 0, completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["plan_available"] is True
    assert payload["selected_strategy"]["strategy_id"] == "strategy_status_artifact_regeneration_plan"
    assert payload["plan_phase"] == "plan_only_structured_remediation"
    assert "status.snapshot_matches_workspace" in payload["triggering_rule_ids"]
    assert payload["simulation_available"] is False


def test_remediation_plan_cli_simulates_status_repair_against_temp_workspace(tmp_path: Path) -> None:
    workspace_root = _copy_governed_workspace(tmp_path)
    _write_stale_status_artifacts(workspace_root)

    completed = _run_inf_work(workspace_root, "remediation-plan", str(workspace_root), "--pretty", "--simulate")

    assert completed.returncode == 0, completed.stdout
    payload = json.loads(completed.stdout)
    simulation = payload["simulation"]
    assert payload["simulation_available"] is True
    assert payload["plan_phase"] == "dry_run_structured_remediation"
    assert simulation["workspace_mutation"] is False
    assert simulation["predicted_rule_summary"]["failed_rules"] == 0
    assert simulation["changed_paths"] == [
        "ai_docs/system_status_snapshot.json",
        "SYSTEM_STATUS.md",
        "SYSTEM_SUMMARY.md",
    ]
    assert simulation["artifact_changes"][0]["diff_preview"][0].startswith("--- a/")


def test_remediation_plan_cli_applies_status_repair_and_post_validation_passes(tmp_path: Path) -> None:
    workspace_root = _copy_governed_workspace(tmp_path)
    _write_stale_status_artifacts(workspace_root)
    pre_snapshot_text = (workspace_root / "ai_docs" / "system_status_snapshot.json").read_text(encoding="utf-8")
    pre_status_text = (workspace_root / "SYSTEM_STATUS.md").read_text(encoding="utf-8")
    pre_summary_text = (workspace_root / "SYSTEM_SUMMARY.md").read_text(encoding="utf-8")

    completed = _run_inf_work(workspace_root, "remediation-plan", str(workspace_root), "--pretty", "--apply")

    assert completed.returncode == 0, completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["applied"] is True
    assert payload["compliant"] is True
    assert payload["rollback_performed"] is False
    assert [operation["status"] for operation in payload["operation_results"]] == ["completed", "completed", "completed"]
    assert (workspace_root / "ai_docs" / "system_status_snapshot.json").read_text(encoding="utf-8") != pre_snapshot_text
    assert (workspace_root / "SYSTEM_STATUS.md").read_text(encoding="utf-8") != pre_status_text
    assert (workspace_root / "SYSTEM_SUMMARY.md").read_text(encoding="utf-8") != pre_summary_text

    status_check = _run_inf_work(workspace_root, "status-check", str(workspace_root), "--pretty")
    assert status_check.returncode == 0, status_check.stdout
    assert json.loads(status_check.stdout)["compliant"] is True

    summary_check = _run_inf_work(workspace_root, "summary-check", str(workspace_root), "--pretty")
    assert summary_check.returncode == 0, summary_check.stdout
    assert json.loads(summary_check.stdout)["compliant"] is True


def test_remediation_plan_cli_rolls_back_when_post_apply_summary_validation_fails(tmp_path: Path) -> None:
    workspace_root = _copy_governed_workspace(tmp_path)
    _write_stale_status_artifacts(workspace_root)
    pre_snapshot_text = (workspace_root / "ai_docs" / "system_status_snapshot.json").read_text(encoding="utf-8")
    pre_status_text = (workspace_root / "SYSTEM_STATUS.md").read_text(encoding="utf-8")
    pre_summary_text = (workspace_root / "SYSTEM_SUMMARY.md").read_text(encoding="utf-8")
    hook_root = _create_summary_failure_hook(tmp_path, workspace_root)

    completed = _run_inf_work(
        workspace_root,
        "remediation-plan",
        str(workspace_root),
        "--pretty",
        "--apply",
        extra_env={
            "INF_WORK_FORCE_SUMMARY_VALIDATION_FAILURE": "1",
            "INF_WORK_FAIL_WORKSPACE_ROOT": str(workspace_root),
        },
        extra_pythonpath_entries=[hook_root],
    )

    assert completed.returncode == 1, completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["applied"] is False
    assert payload["compliant"] is False
    assert payload["rollback_performed"] is True
    assert payload["rollback_summary"]["restored_paths"] == [
        "SYSTEM_STATUS.md",
        "SYSTEM_SUMMARY.md",
        "ai_docs/system_status_snapshot.json",
    ]
    assert (workspace_root / "ai_docs" / "system_status_snapshot.json").read_text(encoding="utf-8") == pre_snapshot_text
    assert (workspace_root / "SYSTEM_STATUS.md").read_text(encoding="utf-8") == pre_status_text
    assert (workspace_root / "SYSTEM_SUMMARY.md").read_text(encoding="utf-8") == pre_summary_text


def test_all_fix_status_cli_succeeds_for_governed_temp_workspace(tmp_path: Path) -> None:
    workspace_root = _copy_governed_workspace(tmp_path)

    completed = _run_inf_work(workspace_root, "all", str(workspace_root), "--pretty", "--fix-status")

    assert completed.returncode == 0, completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["compliant"] is True
    assert payload["workspace"]["compliant"] is True
    assert payload["knowledge_base"]["compliant"] is True
    assert payload["status"]["compliant"] is True
    assert payload["aggregate_rule_summary"]["failed_rules"] == 0