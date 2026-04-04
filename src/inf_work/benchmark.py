from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


_GOVERNED_TOP_LEVEL_FILES = (
    "core_reference.json",
    "behavioral_directives.json",
    "README.md",
    "pyproject.toml",
    "SYSTEM_STATUS.md",
    "SYSTEM_SUMMARY.md",
)
_GOVERNED_TOP_LEVEL_DIRECTORIES = (
    "ai_docs",
    "build",
    "config",
    "knowledge_base",
    "src",
    "tests",
)


@dataclass(frozen=True)
class BenchmarkScenarioResult:
    scenario_id: str
    category: str
    description: str
    command: list[str]
    expected_exit_code: int
    actual_exit_code: int
    passed: bool
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkReport:
    workspace_root: str
    benchmark_id: str
    compliant: bool
    scenario_count: int
    passed_scenarios: int
    failed_scenarios: int
    scorecard: dict[str, Any]
    scenarios: list[BenchmarkScenarioResult]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_root": self.workspace_root,
            "benchmark_id": self.benchmark_id,
            "compliant": self.compliant,
            "scenario_count": self.scenario_count,
            "passed_scenarios": self.passed_scenarios,
            "failed_scenarios": self.failed_scenarios,
            "scorecard": self.scorecard,
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "notes": list(self.notes),
        }


def _copy_governed_workspace(source_root: Path, destination_root: Path) -> Path:
    workspace_root = destination_root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    for file_name in _GOVERNED_TOP_LEVEL_FILES:
        shutil.copy2(source_root / file_name, workspace_root / file_name)

    for directory_name in _GOVERNED_TOP_LEVEL_DIRECTORIES:
        shutil.copytree(
            source_root / directory_name,
            workspace_root / directory_name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )

    backups_path = workspace_root / "ai_docs" / "backups"
    if backups_path.exists():
        shutil.rmtree(backups_path)

    return workspace_root


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_benchmark_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        normalized: dict[str, Any] = {}
        for key, value in payload.items():
            if key == "workspace_root":
                normalized[key] = "<workspace_root>"
            elif key == "generated_at":
                normalized[key] = "<generated_at>"
            else:
                normalized[key] = _normalize_benchmark_payload(value)
        return normalized
    if isinstance(payload, list):
        return [_normalize_benchmark_payload(item) for item in payload]
    return payload


def _write_stale_status_artifacts(workspace_root: Path) -> None:
    snapshot_path = workspace_root / "ai_docs" / "system_status_snapshot.json"
    snapshot_payload = _read_json(snapshot_path)
    snapshot_payload["generated_at"] = "2026-03-01T00:00:00Z"
    snapshot_payload["workspace_root"] = "/tmp/stale-workspace"
    snapshot_path.write_text(json.dumps(snapshot_payload, indent=2), encoding="utf-8")
    (workspace_root / "SYSTEM_STATUS.md").write_text("# stale status\n", encoding="utf-8")
    (workspace_root / "SYSTEM_SUMMARY.md").write_text("# stale summary\n", encoding="utf-8")


def _build_pythonpath(workspace_root: Path, *extra_entries: Path) -> str:
    entries = [str(path) for path in extra_entries if path is not None]
    entries.append(str(workspace_root / "src"))
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
        "PYTHONPATH": _build_pythonpath(workspace_root, *(extra_pythonpath_entries or [])),
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


def _run_json_command(
    workspace_root: Path,
    *args: str,
    expected_exit_code: int,
    extra_env: dict[str, str] | None = None,
    extra_pythonpath_entries: list[Path] | None = None,
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    completed = _run_inf_work(
        workspace_root,
        *args,
        extra_env=extra_env,
        extra_pythonpath_entries=extra_pythonpath_entries,
    )
    payload = json.loads(completed.stdout)
    if completed.returncode != expected_exit_code:
        raise AssertionError(
            f"Expected exit code {expected_exit_code} for {' '.join(args)}, got {completed.returncode}: {completed.stdout or completed.stderr}"
        )
    return completed, payload


def _create_summary_failure_hook(hook_root: Path, workspace_root: Path) -> Path:
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
                "                    message='Forced summary validation failure for benchmark rollback coverage.',",
                "                )",
                "            ],",
                "            rule_results=[",
                "                RuleResult(",
                "                    rule_id='status.summary_matches_workspace',",
                "                    domain='status',",
                "                    category='artifact_integrity',",
                "                    severity='error',",
                "                    description='Forced summary mismatch for benchmark rollback coverage.',",
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


def _scenario_aggregate_healthy(source_root: Path) -> BenchmarkScenarioResult:
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_root = _copy_governed_workspace(source_root, Path(temp_dir))
        _run_json_command(workspace_root, "status", str(workspace_root), "--pretty", expected_exit_code=0)
        _, payload = _run_json_command(workspace_root, "all", str(workspace_root), "--pretty", expected_exit_code=0)
        passed = payload["compliant"] is True and payload["aggregate_rule_summary"]["failed_rules"] == 0
        return BenchmarkScenarioResult(
            scenario_id="aggregate_healthy_workspace",
            category="operator_e2e",
            description="Run the aggregate governance report on a healthy governed workspace copy.",
            command=["python", "-m", "inf_work", "all", str(workspace_root), "--pretty"],
            expected_exit_code=0,
            actual_exit_code=0,
            passed=passed,
            evidence={
                "compliant": payload["compliant"],
                "failed_rules": payload["aggregate_rule_summary"]["failed_rules"],
            },
        )


def _scenario_status_drift_detection(source_root: Path) -> BenchmarkScenarioResult:
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_root = _copy_governed_workspace(source_root, Path(temp_dir))
        _write_stale_status_artifacts(workspace_root)
        _, payload = _run_json_command(workspace_root, "status-check", str(workspace_root), "--pretty", expected_exit_code=1)
        passed = payload["compliant"] is False and payload["rule_summary"]["failed_rules"] >= 1
        return BenchmarkScenarioResult(
            scenario_id="status_drift_detection",
            category="remediation",
            description="Confirm stale governed status artifacts are detected before remediation.",
            command=["python", "-m", "inf_work", "status-check", str(workspace_root), "--pretty"],
            expected_exit_code=1,
            actual_exit_code=1,
            passed=passed,
            evidence={
                "compliant": payload["compliant"],
                "failed_rules": payload["rule_summary"]["failed_rules"],
            },
        )


def _scenario_remediation_plan_simulation(source_root: Path) -> BenchmarkScenarioResult:
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_root = _copy_governed_workspace(source_root, Path(temp_dir))
        _write_stale_status_artifacts(workspace_root)
        _, payload = _run_json_command(
            workspace_root,
            "remediation-plan",
            str(workspace_root),
            "--pretty",
            "--simulate",
            expected_exit_code=0,
        )
        simulation = payload["simulation"]
        expected_paths = ["ai_docs/system_status_snapshot.json", "SYSTEM_STATUS.md", "SYSTEM_SUMMARY.md"]
        passed = (
            payload["simulation_available"] is True
            and payload["plan_available"] is True
            and simulation["workspace_mutation"] is False
            and simulation["changed_paths"] == expected_paths
            and simulation["predicted_rule_summary"]["failed_rules"] == 0
        )
        return BenchmarkScenarioResult(
            scenario_id="remediation_plan_simulation",
            category="remediation",
            description="Compile the bounded remediation plan with dry-run simulation for stale status artifacts.",
            command=["python", "-m", "inf_work", "remediation-plan", str(workspace_root), "--pretty", "--simulate"],
            expected_exit_code=0,
            actual_exit_code=0,
            passed=passed,
            evidence={
                "simulation_available": payload["simulation_available"],
                "changed_paths": simulation["changed_paths"],
                "predicted_failed_rules": simulation["predicted_rule_summary"]["failed_rules"],
            },
        )


def _scenario_remediation_apply_success(source_root: Path) -> BenchmarkScenarioResult:
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_root = _copy_governed_workspace(source_root, Path(temp_dir))
        _write_stale_status_artifacts(workspace_root)
        _, apply_payload = _run_json_command(
            workspace_root,
            "remediation-plan",
            str(workspace_root),
            "--pretty",
            "--apply",
            expected_exit_code=0,
        )
        _, status_payload = _run_json_command(workspace_root, "status-check", str(workspace_root), "--pretty", expected_exit_code=0)
        _, summary_payload = _run_json_command(workspace_root, "summary-check", str(workspace_root), "--pretty", expected_exit_code=0)
        passed = (
            apply_payload["applied"] is True
            and apply_payload["compliant"] is True
            and apply_payload["rollback_performed"] is False
            and status_payload["compliant"] is True
            and summary_payload["compliant"] is True
        )
        return BenchmarkScenarioResult(
            scenario_id="remediation_apply_success",
            category="remediation",
            description="Apply the bounded remediation slice and verify the repaired workspace passes post-apply validation.",
            command=["python", "-m", "inf_work", "remediation-plan", str(workspace_root), "--pretty", "--apply"],
            expected_exit_code=0,
            actual_exit_code=0,
            passed=passed,
            evidence={
                "applied": apply_payload["applied"],
                "rollback_performed": apply_payload["rollback_performed"],
                "status_check_compliant": status_payload["compliant"],
                "summary_check_compliant": summary_payload["compliant"],
            },
        )


def _scenario_remediation_apply_rollback(source_root: Path) -> BenchmarkScenarioResult:
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_root = _copy_governed_workspace(source_root, Path(temp_dir))
        _write_stale_status_artifacts(workspace_root)
        pre_snapshot = (workspace_root / "ai_docs" / "system_status_snapshot.json").read_text(encoding="utf-8")
        pre_status = (workspace_root / "SYSTEM_STATUS.md").read_text(encoding="utf-8")
        pre_summary = (workspace_root / "SYSTEM_SUMMARY.md").read_text(encoding="utf-8")
        hook_root = _create_summary_failure_hook(Path(temp_dir) / "hook", workspace_root)
        _, payload = _run_json_command(
            workspace_root,
            "remediation-plan",
            str(workspace_root),
            "--pretty",
            "--apply",
            expected_exit_code=1,
            extra_env={
                "INF_WORK_FORCE_SUMMARY_VALIDATION_FAILURE": "1",
                "INF_WORK_FAIL_WORKSPACE_ROOT": str(workspace_root),
            },
            extra_pythonpath_entries=[hook_root],
        )
        restored = payload["rollback_summary"]["restored_paths"]
        passed = (
            payload["applied"] is False
            and payload["rollback_performed"] is True
            and restored == ["SYSTEM_STATUS.md", "SYSTEM_SUMMARY.md", "ai_docs/system_status_snapshot.json"]
            and (workspace_root / "ai_docs" / "system_status_snapshot.json").read_text(encoding="utf-8") == pre_snapshot
            and (workspace_root / "SYSTEM_STATUS.md").read_text(encoding="utf-8") == pre_status
            and (workspace_root / "SYSTEM_SUMMARY.md").read_text(encoding="utf-8") == pre_summary
        )
        return BenchmarkScenarioResult(
            scenario_id="remediation_apply_rollback",
            category="recovery",
            description="Force post-apply summary validation failure and verify rollback restores the pre-apply governed artifacts.",
            command=["python", "-m", "inf_work", "remediation-plan", str(workspace_root), "--pretty", "--apply"],
            expected_exit_code=1,
            actual_exit_code=1,
            passed=passed,
            evidence={
                "applied": payload["applied"],
                "rollback_performed": payload["rollback_performed"],
                "restored_paths": restored,
            },
        )


def _scenario_aggregate_fix_status(source_root: Path) -> BenchmarkScenarioResult:
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_root = _copy_governed_workspace(source_root, Path(temp_dir))
        _write_stale_status_artifacts(workspace_root)
        _, payload = _run_json_command(
            workspace_root,
            "all",
            str(workspace_root),
            "--pretty",
            "--fix-status",
            expected_exit_code=0,
        )
        passed = (
            payload["compliant"] is True
            and payload["workspace"]["compliant"] is True
            and payload["knowledge_base"]["compliant"] is True
            and payload["status"]["compliant"] is True
        )
        return BenchmarkScenarioResult(
            scenario_id="aggregate_fix_status_recovery",
            category="operator_e2e",
            description="Run the aggregate report with status repair enabled against a workspace with stale status artifacts.",
            command=["python", "-m", "inf_work", "all", str(workspace_root), "--pretty", "--fix-status"],
            expected_exit_code=0,
            actual_exit_code=0,
            passed=passed,
            evidence={
                "compliant": payload["compliant"],
                "status_compliant": payload["status"]["compliant"],
                "knowledge_base_compliant": payload["knowledge_base"]["compliant"],
            },
        )


def _scenario_simulation_determinism(source_root: Path) -> BenchmarkScenarioResult:
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_root = _copy_governed_workspace(source_root, Path(temp_dir))
        _write_stale_status_artifacts(workspace_root)
        _, first_payload = _run_json_command(
            workspace_root,
            "remediation-plan",
            str(workspace_root),
            "--pretty",
            "--simulate",
            expected_exit_code=0,
        )
        _, second_payload = _run_json_command(
            workspace_root,
            "remediation-plan",
            str(workspace_root),
            "--pretty",
            "--simulate",
            expected_exit_code=0,
        )
        normalized_first = _normalize_benchmark_payload(first_payload)
        normalized_second = _normalize_benchmark_payload(second_payload)
        passed = normalized_first == normalized_second
        return BenchmarkScenarioResult(
            scenario_id="simulation_determinism",
            category="determinism",
            description="Run the same dry-run remediation simulation twice and require normalized payload stability.",
            command=["python", "-m", "inf_work", "remediation-plan", str(workspace_root), "--pretty", "--simulate"],
            expected_exit_code=0,
            actual_exit_code=0,
            passed=passed,
            evidence={
                "payloads_identical": passed,
                "triggering_rule_ids": first_payload["triggering_rule_ids"],
            },
        )


def _build_scorecard(scenarios: list[BenchmarkScenarioResult]) -> dict[str, Any]:
    dimension_map = {
        "operator_e2e": ["aggregate_healthy_workspace", "aggregate_fix_status_recovery"],
        "remediation": ["status_drift_detection", "remediation_plan_simulation", "remediation_apply_success"],
        "recovery": ["remediation_apply_rollback"],
        "determinism": ["simulation_determinism"],
    }
    scenario_lookup = {scenario.scenario_id: scenario for scenario in scenarios}
    by_dimension: dict[str, Any] = {}
    for dimension, scenario_ids in dimension_map.items():
        passed = sum(1 for scenario_id in scenario_ids if scenario_lookup[scenario_id].passed)
        total = len(scenario_ids)
        by_dimension[dimension] = {
            "scenario_ids": scenario_ids,
            "passed": passed,
            "total": total,
            "score_percentage": int((passed / total) * 100) if total else 100,
        }

    total_passed = sum(1 for scenario in scenarios if scenario.passed)
    total = len(scenarios)
    return {
        "overall_score_percentage": int((total_passed / total) * 100) if total else 100,
        "by_dimension": by_dimension,
    }


def run_benchmark(workspace_root: str | Path) -> BenchmarkReport:
    source_root = Path(workspace_root).resolve()
    scenarios = [
        _scenario_aggregate_healthy(source_root),
        _scenario_status_drift_detection(source_root),
        _scenario_remediation_plan_simulation(source_root),
        _scenario_remediation_apply_success(source_root),
        _scenario_remediation_apply_rollback(source_root),
        _scenario_aggregate_fix_status(source_root),
        _scenario_simulation_determinism(source_root),
    ]
    passed_scenarios = sum(1 for scenario in scenarios if scenario.passed)
    failed_scenarios = len(scenarios) - passed_scenarios
    scorecard = _build_scorecard(scenarios)
    return BenchmarkReport(
        workspace_root=str(source_root),
        benchmark_id="benchmark_governed_operator_workflows_v1",
        compliant=failed_scenarios == 0,
        scenario_count=len(scenarios),
        passed_scenarios=passed_scenarios,
        failed_scenarios=failed_scenarios,
        scorecard=scorecard,
        scenarios=scenarios,
        notes=[
            "This benchmark is intentionally deterministic and scores operator workflow correctness, remediation behavior, recovery, and simulation stability.",
            "Raw wall-clock latency is not included in the machine-readable report so repeated benchmark runs preserve deterministic outputs under the governed architectural constraints.",
        ],
    )
