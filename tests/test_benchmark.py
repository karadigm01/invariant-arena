from __future__ import annotations

import json
from pathlib import Path
import subprocess

import inf_work.benchmark as benchmark_module
from inf_work.benchmark import BenchmarkScenarioResult, run_benchmark
from inf_work.system_status import write_system_status_outputs


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


def _prepare_benchmark_source_workspace(tmp_path: Path) -> Path:
    source_root = benchmark_module._copy_governed_workspace(WORKSPACE_ROOT, tmp_path)
    coverage_path = source_root / "ai_docs" / "test_coverage_snapshot.json"
    coverage_payload = json.loads(coverage_path.read_text(encoding="utf-8"))
    coverage_payload["module_coverage"].append(
        {
            "module_path": "src/inf_work/benchmark.py",
            "coverage_percentage": 100,
            "num_statements": 1,
            "covered_lines": 1,
            "missing_lines": 0,
        }
    )
    coverage_payload["metadata"]["total_modules"] = len(coverage_payload["module_coverage"])
    coverage_path.write_text(json.dumps(coverage_payload, indent=2), encoding="utf-8")
    write_system_status_outputs(source_root)
    return source_root


def test_normalize_benchmark_payload_replaces_workspace_and_generated_at_fields() -> None:
    payload = {
        "workspace_root": "/tmp/example",
        "generated_at": "2026-04-03T00:00:00Z",
        "nested": [{"workspace_root": "/tmp/example", "value": 1}],
    }

    normalized = benchmark_module._normalize_benchmark_payload(payload)

    assert normalized == {
        "workspace_root": "<workspace_root>",
        "generated_at": "<generated_at>",
        "nested": [{"workspace_root": "<workspace_root>", "value": 1}],
    }


def test_build_scorecard_handles_pass_and_fail_mix() -> None:
    scorecard = benchmark_module._build_scorecard(
        [
            BenchmarkScenarioResult("aggregate_healthy_workspace", "operator_e2e", "a", [], 0, 0, True, {}),
            BenchmarkScenarioResult("aggregate_fix_status_recovery", "operator_e2e", "b", [], 0, 0, False, {}),
            BenchmarkScenarioResult("status_drift_detection", "remediation", "c", [], 1, 1, True, {}),
            BenchmarkScenarioResult("remediation_plan_simulation", "remediation", "d", [], 0, 0, True, {}),
            BenchmarkScenarioResult("remediation_apply_success", "remediation", "e", [], 0, 0, False, {}),
            BenchmarkScenarioResult("remediation_apply_rollback", "recovery", "f", [], 1, 1, True, {}),
            BenchmarkScenarioResult("simulation_determinism", "determinism", "g", [], 0, 0, True, {}),
        ]
    )

    assert scorecard["overall_score_percentage"] == 71
    assert scorecard["by_dimension"]["operator_e2e"]["score_percentage"] == 50
    assert scorecard["by_dimension"]["remediation"]["score_percentage"] == 66
    assert scorecard["by_dimension"]["recovery"]["score_percentage"] == 100
    assert scorecard["by_dimension"]["determinism"]["score_percentage"] == 100


def test_copy_governed_workspace_removes_backups_directory(tmp_path: Path) -> None:
    copied_root = benchmark_module._copy_governed_workspace(WORKSPACE_ROOT, tmp_path)

    assert copied_root.exists()
    assert (copied_root / "src" / "inf_work" / "benchmark.py").is_file()
    assert not (copied_root / "ai_docs" / "backups").exists()


def test_build_pythonpath_appends_existing_pythonpath(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    monkeypatch.setenv("PYTHONPATH", "/tmp/existing-pythonpath")

    pythonpath = benchmark_module._build_pythonpath(workspace_root, tmp_path / "extra")

    assert pythonpath.split(benchmark_module.os.pathsep) == [
        str(tmp_path / "extra"),
        str(workspace_root / "src"),
        "/tmp/existing-pythonpath",
    ]


def test_run_json_command_raises_for_unexpected_exit_code(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    monkeypatch.setattr(
        benchmark_module,
        "_run_inf_work",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=["python", "-m", "inf_work", "status"],
            returncode=1,
            stdout='{"compliant": false}',
            stderr="boom",
        ),
    )

    try:
        benchmark_module._run_json_command(workspace_root, "status", str(workspace_root), expected_exit_code=0)
    except AssertionError as error:
        message = str(error)
    else:
        raise AssertionError("Expected _run_json_command to raise on an unexpected exit code.")

    assert "Expected exit code 0" in message
    assert "status" in message


def test_run_benchmark_reports_all_governed_operator_scenarios(tmp_path: Path) -> None:
    source_root = _prepare_benchmark_source_workspace(tmp_path)

    report = run_benchmark(source_root)
    payload = report.to_dict()

    assert report.compliant is True
    assert payload["benchmark_id"] == "benchmark_governed_operator_workflows_v1"
    assert payload["scenario_count"] == 7
    assert payload["passed_scenarios"] == 7
    assert payload["failed_scenarios"] == 0
    assert payload["scorecard"]["overall_score_percentage"] == 100
    assert [scenario["scenario_id"] for scenario in payload["scenarios"]] == [
        "aggregate_healthy_workspace",
        "status_drift_detection",
        "remediation_plan_simulation",
        "remediation_apply_success",
        "remediation_apply_rollback",
        "aggregate_fix_status_recovery",
        "simulation_determinism",
    ]
    assert all(scenario["passed"] is True for scenario in payload["scenarios"])
    assert json.loads(json.dumps(payload))["compliant"] is True
