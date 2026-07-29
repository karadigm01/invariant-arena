from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import runpy
import sys
import warnings

import pytest
import inf_work
import inf_work.__main__ as unified_cli
import inf_work.kb_check as kb_check
from inf_work.rules import RuleFinding, RuleResult


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class FakeValidationResult:
    payload: dict[str, object]
    compliant: bool = True
    rule_results: list[RuleResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return dict(self.payload)


def _passing_rule(rule_id: str, domain: str = "workspace") -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        domain=domain,
        category="governance",
        severity="warning",
        description=f"{rule_id} description",
        passed=True,
        findings=[],
    )


def _failing_rule(rule_id: str, domain: str = "workspace") -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        domain=domain,
        category="governance",
        severity="error",
        description=f"{rule_id} description",
        passed=False,
        findings=[
            RuleFinding(
                message="failed",
                source_file="source.json",
                item_identifier="item",
                field_name="field",
            )
        ],
    )


def _parse_args(argv: list[str]) -> object:
    return unified_cli.build_parser().parse_args(argv)


def _run_main_json(monkeypatch, capsys, argv: list[str]) -> tuple[int, dict[str, object]]:
    monkeypatch.setattr(sys, "argv", argv)
    exit_code = unified_cli.main()
    return exit_code, json.loads(capsys.readouterr().out)


def _run_module_entrypoint(module_name: str, warning_pattern: str) -> int:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=warning_pattern, category=RuntimeWarning)
        with pytest.raises(SystemExit) as error:
            runpy.run_module(module_name, run_name="__main__")
    return int(error.value.code)


def test_package_public_api_exports_expected_symbols() -> None:
    expected_exports = {
        "CoreReferenceView",
        "ChangeProvenanceRecord",
        "KnowledgeBaseValidationResult",
        "PlanOperation",
        "RemediationExecutionResult",
        "ResolverCapabilitiesSnapshot",
        "ResolverTile",
        "ResolverTraversalResult",
        "ResolverTraversalStep",
        "RemediationPlan",
        "RemediationStrategy",
        "RollbackContract",
        "RuleFinding",
        "RuleResult",
        "SystemStatusSnapshot",
        "ValidationResult",
        "VerificationContract",
        "build_core_reference_view",
        "build_resolver_capabilities",
        "apply_package_public_api_export_remediation",
        "apply_remediation_plan",
        "build_system_status_snapshot",
        "build_test_coverage_snapshot",
        "apply_status_artifact_remediation",
        "compile_package_public_api_export_remediation_plan",
        "compile_remediation_plan",
        "compile_status_artifact_remediation_plan",
        "infer_route",
        "list_supported_remediation_strategies",
        "list_registered_tiles",
        "resolve_explicit_path",
        "resolve_tile",
        "validate_knowledge_base",
        "validate_system_status",
        "validate_workspace",
        "write_test_coverage_snapshot",
        "write_system_status_outputs",
    }

    assert expected_exports.issubset(set(inf_work.__all__))
    for export_name in expected_exports:
        assert getattr(inf_work, export_name) is not None


def test_kb_check_main_rewrites_argv_and_restores_it(monkeypatch) -> None:
    original_argv = ["kb-check", str(WORKSPACE_ROOT), "--pretty"]
    captured: dict[str, object] = {}

    def fake_unified_main() -> int:
        captured["argv"] = sys.argv[:]
        return 7

    monkeypatch.setattr(unified_cli, "main", fake_unified_main)
    monkeypatch.setattr(sys, "argv", original_argv[:])

    exit_code = kb_check.main()

    assert exit_code == 7
    assert captured["argv"] == ["kb-check", "kb", str(WORKSPACE_ROOT), "--pretty"]
    assert sys.argv == original_argv


def test_kb_check_module_main_raises_system_exit_with_unified_exit_code(monkeypatch) -> None:
    monkeypatch.setattr(unified_cli, "main", lambda: 9)
    monkeypatch.setattr(sys, "argv", ["kb-check", str(WORKSPACE_ROOT)])

    assert _run_module_entrypoint(
        "inf_work.kb_check",
        r"'inf_work\.kb_check' found in sys\.modules after import of package 'inf_work'",
    ) == 9

    assert sys.argv == ["kb-check", str(WORKSPACE_ROOT)]


def test_build_parser_parses_infer_route_arguments() -> None:
    parsed_args = _parse_args(
        [
            "infer-route",
            "workspace_governance",
            "knowledge_base_index",
            "--workspace-root",
            str(WORKSPACE_ROOT),
            "--pretty",
        ]
    )

    assert parsed_args.command == "infer-route"
    assert parsed_args.start_tile_id == "workspace_governance"
    assert parsed_args.target_tile_id == "knowledge_base_index"
    assert parsed_args.workspace_root == str(WORKSPACE_ROOT)
    assert parsed_args.pretty is True

def test_aggregate_validation_result_to_dict_returns_expected_payload() -> None:
    result = unified_cli.AggregateValidationResult(
        workspace_root=str(WORKSPACE_ROOT),
        compliant=True,
        workspace={"kind": "workspace"},
        knowledge_base={"kind": "knowledge_base"},
        status={"kind": "status"},
    )

    assert result.to_dict() == {
        "workspace_root": str(WORKSPACE_ROOT),
        "compliant": True,
        "workspace": {"kind": "workspace"},
        "knowledge_base": {"kind": "knowledge_base"},
        "status": {"kind": "status"},
    }


def test_artifact_refresh_result_to_dict_returns_expected_payload() -> None:
    result = unified_cli.ArtifactRefreshResult(
        workspace_root=str(WORKSPACE_ROOT),
        coverage_snapshot={"coverage_percentage": 100},
        status_snapshot={"generated_at": "2026-04-03T00:00:00Z"},
    )

    assert result.to_dict() == {
        "workspace_root": str(WORKSPACE_ROOT),
        "coverage_snapshot": {"coverage_percentage": 100},
        "status_snapshot": {"generated_at": "2026-04-03T00:00:00Z"},
    }


def test_build_parser_parses_summary_check_fix_flag() -> None:
    parsed_args = _parse_args(["summary-check", str(WORKSPACE_ROOT), "--pretty", "--fix"])

    assert parsed_args.command == "summary-check"
    assert parsed_args.workspace_root == str(WORKSPACE_ROOT)
    assert parsed_args.pretty is True
    assert parsed_args.fix is True


def test_build_parser_parses_coverage_snapshot_command() -> None:
    parsed_args = _parse_args(["coverage-snapshot", str(WORKSPACE_ROOT), "--pretty"])

    assert parsed_args.command == "coverage-snapshot"
    assert parsed_args.workspace_root == str(WORKSPACE_ROOT)
    assert parsed_args.pretty is True


def test_build_parser_parses_mutation_snapshot_command() -> None:
    parsed_args = _parse_args(["mutation-snapshot", str(WORKSPACE_ROOT), "--pretty"])

    assert parsed_args.command == "mutation-snapshot"
    assert parsed_args.workspace_root == str(WORKSPACE_ROOT)
    assert parsed_args.pretty is True


def test_build_parser_parses_refresh_artifacts_command() -> None:
    parsed_args = _parse_args(["refresh-artifacts", str(WORKSPACE_ROOT), "--pretty"])

    assert parsed_args.command == "refresh-artifacts"
    assert parsed_args.workspace_root == str(WORKSPACE_ROOT)
    assert parsed_args.pretty is True


def test_build_parser_parses_benchmark_command() -> None:
    parsed_args = _parse_args(["benchmark", str(WORKSPACE_ROOT), "--pretty"])

    assert parsed_args.command == "benchmark"
    assert parsed_args.workspace_root == str(WORKSPACE_ROOT)
    assert parsed_args.pretty is True


def test_build_parser_parses_remediation_plan_command() -> None:
    parsed_args = _parse_args(
        [
            "remediation-plan",
            str(WORKSPACE_ROOT),
            "--pretty",
            "--simulate",
            "--rule-id",
            "status.snapshot_matches_workspace",
        ]
    )

    assert parsed_args.command == "remediation-plan"
    assert parsed_args.workspace_root == str(WORKSPACE_ROOT)
    assert parsed_args.pretty is True
    assert parsed_args.simulate is True
    assert parsed_args.apply is False
    assert parsed_args.rule_id == ["status.snapshot_matches_workspace"]
    assert parsed_args.intent is None


def test_build_parser_parses_remediation_plan_intent_command() -> None:
    parsed_args = _parse_args(
        [
            "remediation-plan",
            str(WORKSPACE_ROOT),
            "--pretty",
            "--intent",
            "intent.status.refresh_artifacts",
        ]
    )

    assert parsed_args.command == "remediation-plan"
    assert parsed_args.intent == "intent.status.refresh_artifacts"


def test_build_parser_parses_remediation_plan_apply_command() -> None:
    parsed_args = _parse_args(
        [
            "remediation-plan",
            str(WORKSPACE_ROOT),
            "--pretty",
            "--apply",
            "--rule-id",
            "status.snapshot_matches_workspace",
        ]
    )

    assert parsed_args.command == "remediation-plan"
    assert parsed_args.workspace_root == str(WORKSPACE_ROOT)
    assert parsed_args.pretty is True
    assert parsed_args.apply is True
    assert parsed_args.simulate is False
    assert parsed_args.rule_id == ["status.snapshot_matches_workspace"]


def test_build_parser_parses_resolve_path_arguments() -> None:
    parsed_args = _parse_args(
        [
            "resolve-path",
            "workspace_governance",
            "component_index",
            "knowledge_base_index",
            "--workspace-root",
            str(WORKSPACE_ROOT),
            "--pretty",
        ]
    )

    assert parsed_args.command == "resolve-path"
    assert parsed_args.tile_ids == ["workspace_governance", "component_index", "knowledge_base_index"]
    assert parsed_args.workspace_root == str(WORKSPACE_ROOT)
    assert parsed_args.pretty is True


def test_unified_main_resolve_path_outputs_traversal_payload(monkeypatch, capsys) -> None:
    exit_code, payload = _run_main_json(
        monkeypatch,
        capsys,
        [
            "inf_work",
            "resolve-path",
            "workspace_governance",
            "component_index",
            "knowledge_base_index",
            "--workspace-root",
            str(WORKSPACE_ROOT),
            "--pretty",
        ],
    )
    assert exit_code == 0
    assert payload["traversal_mode"] == "explicit"
    assert payload["complete"] is True
    assert payload["requested_path"] == ["workspace_governance", "component_index", "knowledge_base_index"]
    assert payload["total_hops"] == 2


def test_unified_main_infer_route_outputs_traversal_payload(monkeypatch, capsys) -> None:
    exit_code, payload = _run_main_json(
        monkeypatch,
        capsys,
        [
            "inf_work",
            "infer-route",
            "workspace_governance",
            "knowledge_base_index",
            "--workspace-root",
            str(WORKSPACE_ROOT),
            "--pretty",
        ],
    )
    assert exit_code == 0
    assert payload["traversal_mode"] == "inferred"
    assert payload["complete"] is True
    assert payload["requested_path"] == ["workspace_governance", "knowledge_base_index"]
    assert payload["total_hops"] == 1


def test_unified_main_remediation_plan_outputs_compiled_plan(monkeypatch, capsys) -> None:
    plan_result = FakeValidationResult(
        payload={
            "plan_id": "remediation_plan_status_artifact_regeneration",
            "plan_available": True,
            "simulation_available": True,
            "triggering_rule_ids": ["status.snapshot_matches_workspace"],
        }
    )

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        unified_cli,
        "compile_remediation_plan",
        lambda workspace_root, selected_rule_ids, include_simulation=False, intent_id=None: captured.update(
            {
                "workspace_root": workspace_root,
                "selected_rule_ids": selected_rule_ids,
                "include_simulation": include_simulation,
                "intent_id": intent_id,
            }
        )
        or plan_result,
    )

    exit_code, payload = _run_main_json(
        monkeypatch,
        capsys,
        [
            "inf_work",
            "remediation-plan",
            str(WORKSPACE_ROOT),
            "--pretty",
            "--simulate",
        ],
    )

    assert exit_code == 0
    assert captured["workspace_root"] == WORKSPACE_ROOT
    assert captured["selected_rule_ids"] is None
    assert captured["include_simulation"] is True
    assert captured["intent_id"] is None
    assert payload == {
        "plan_available": True,
        "plan_id": "remediation_plan_status_artifact_regeneration",
        "simulation_available": True,
        "triggering_rule_ids": ["status.snapshot_matches_workspace"],
    }


def test_unified_main_remediation_plan_apply_outputs_execution_result(monkeypatch, capsys) -> None:
    execution_result = FakeValidationResult(
        payload={
            "plan_id": "remediation_plan_status_artifact_regeneration",
            "execution_attempted": True,
            "applied": True,
            "compliant": True,
        }
    )

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        unified_cli,
        "apply_remediation_plan",
        lambda workspace_root, selected_rule_ids, intent_id=None: captured.update(
            {
                "workspace_root": workspace_root,
                "selected_rule_ids": selected_rule_ids,
                "intent_id": intent_id,
            }
        )
        or execution_result,
    )

    exit_code, payload = _run_main_json(
        monkeypatch,
        capsys,
        [
            "inf_work",
            "remediation-plan",
            str(WORKSPACE_ROOT),
            "--pretty",
            "--apply",
        ],
    )

    assert exit_code == 0
    assert captured["workspace_root"] == WORKSPACE_ROOT
    assert captured["selected_rule_ids"] is None
    assert captured["intent_id"] is None
    assert payload == {
        "plan_id": "remediation_plan_status_artifact_regeneration",
        "execution_attempted": True,
        "applied": True,
        "compliant": True,
    }


def test_unified_main_remediation_plan_intent_outputs_compiled_plan(monkeypatch, capsys) -> None:
    plan_result = FakeValidationResult(
        payload={
            "plan_id": "remediation_plan_status_artifact_regeneration",
            "plan_available": True,
            "provenance": {"governed_intent_ids": ["intent.status.refresh_artifacts"]},
        }
    )

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        unified_cli,
        "compile_remediation_plan",
        lambda workspace_root, selected_rule_ids, include_simulation=False, intent_id=None: captured.update(
            {
                "workspace_root": workspace_root,
                "selected_rule_ids": selected_rule_ids,
                "include_simulation": include_simulation,
                "intent_id": intent_id,
            }
        )
        or plan_result,
    )

    exit_code, payload = _run_main_json(
        monkeypatch,
        capsys,
        [
            "inf_work",
            "remediation-plan",
            str(WORKSPACE_ROOT),
            "--pretty",
            "--intent",
            "intent.status.refresh_artifacts",
        ],
    )

    assert exit_code == 0
    assert captured["intent_id"] == "intent.status.refresh_artifacts"
    assert payload["provenance"] == {"governed_intent_ids": ["intent.status.refresh_artifacts"]}


def test_unified_main_resolve_path_returns_failure_for_unknown_tile(monkeypatch, capsys) -> None:
    exit_code, payload = _run_main_json(
        monkeypatch,
        capsys,
        [
            "inf_work",
            "resolve-path",
            "workspace_governance",
            "unknown_tile",
            "--workspace-root",
            str(WORKSPACE_ROOT),
            "--pretty",
        ],
    )
    assert exit_code == 1
    assert payload["complete"] is False
    assert payload["failure_reason"] == "unknown_tile:unknown_tile"


def test_unified_main_legacy_workspace_mode_outputs_workspace_payload(monkeypatch, capsys) -> None:
    exit_code, payload = _run_main_json(monkeypatch, capsys, ["inf_work", str(WORKSPACE_ROOT), "--pretty"])
    assert exit_code == 0
    assert payload["compliant"] is True
    assert payload["workspace_root"] == str(WORKSPACE_ROOT)
    assert payload["rule_summary"]["total_rules"] >= 1


def test_unified_main_status_outputs_latest_kb_highlights(monkeypatch, capsys) -> None:
    session_history = json.loads((WORKSPACE_ROOT / "knowledge_base" / "session_history.json").read_text(encoding="utf-8"))
    automation_patterns = json.loads(
        (WORKSPACE_ROOT / "knowledge_base" / "automation_patterns.json").read_text(encoding="utf-8")
    )
    latest_session = session_history["sessions"][-1]
    latest_automation_pattern = automation_patterns["automation_patterns"][-1]

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "inf_work",
            "status",
            str(WORKSPACE_ROOT),
            "--pretty",
        ],
    )

    exit_code = unified_cli.main()

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    recent_activity = payload["recent_session_activity"]
    assert exit_code == 0
    assert payload["workspace_root"] == str(WORKSPACE_ROOT)
    assert recent_activity["latest_session"]["session_id"] == latest_session["session_id"]
    assert recent_activity["latest_session"]["summary"] == latest_session["summary"]
    assert recent_activity["latest_automation_pattern"]["id"] == latest_automation_pattern["id"]
    assert recent_activity["latest_automation_pattern"]["pattern_name"] == latest_automation_pattern["pattern_name"]
    assert recent_activity["latest_summary"] == latest_session["summary"]


def test_unified_main_coverage_snapshot_outputs_payload(monkeypatch, capsys) -> None:
    expected_snapshot = {
        "workspace_root": str(WORKSPACE_ROOT),
        "totals": {"coverage_percentage": 91},
    }
    monkeypatch.setattr(unified_cli, "write_test_coverage_snapshot", lambda workspace_root: expected_snapshot)
    exit_code, payload = _run_main_json(monkeypatch, capsys, ["inf_work", "coverage-snapshot", str(WORKSPACE_ROOT), "--pretty"])
    assert exit_code == 0
    assert payload == expected_snapshot


def test_unified_main_mutation_snapshot_outputs_payload(monkeypatch, capsys) -> None:
    expected_snapshot = {
        "workspace_root": str(WORKSPACE_ROOT),
        "summary_text": "99 killed, 0 survived, 0 no-test",
        "status": "results_available",
    }
    monkeypatch.setattr(unified_cli, "write_mutation_test_snapshot", lambda workspace_root: expected_snapshot)

    exit_code, payload = _run_main_json(
        monkeypatch,
        capsys,
        ["inf_work", "mutation-snapshot", str(WORKSPACE_ROOT), "--pretty"],
    )

    assert exit_code == 0
    assert payload == expected_snapshot


def test_unified_main_benchmark_outputs_payload(monkeypatch, capsys) -> None:
    benchmark_result = FakeValidationResult(
        payload={
            "benchmark_id": "benchmark_governed_operator_workflows_v1",
            "compliant": True,
            "scenario_count": 7,
        }
    )

    monkeypatch.setattr(unified_cli, "run_benchmark", lambda workspace_root: benchmark_result)

    exit_code, payload = _run_main_json(monkeypatch, capsys, ["inf_work", "benchmark", str(WORKSPACE_ROOT), "--pretty"])

    assert exit_code == 0
    assert payload == {
        "benchmark_id": "benchmark_governed_operator_workflows_v1",
        "compliant": True,
        "scenario_count": 7,
    }


def test_unified_main_refresh_artifacts_outputs_combined_payload(monkeypatch, capsys) -> None:
    call_order: list[str] = []
    expected_coverage_snapshot = {
        "workspace_root": str(WORKSPACE_ROOT),
        "totals": {"coverage_percentage": 91},
    }

    class FakeStatusSnapshot:
        compliant = True

        def to_dict(self) -> dict[str, object]:
            return {
                "workspace_root": str(WORKSPACE_ROOT),
                "canonical_json_path": "ai_docs/system_status_snapshot.json",
            }

    def fake_write_test_coverage_snapshot(workspace_root):
        call_order.append("coverage")
        return expected_coverage_snapshot

    def fake_write_system_status_outputs(workspace_root):
        call_order.append("status")
        return FakeStatusSnapshot()

    monkeypatch.setattr(unified_cli, "write_test_coverage_snapshot", fake_write_test_coverage_snapshot)
    monkeypatch.setattr(unified_cli, "write_system_status_outputs", fake_write_system_status_outputs)
    monkeypatch.setattr(sys, "argv", ["inf_work", "refresh-artifacts", str(WORKSPACE_ROOT), "--pretty"])

    exit_code = unified_cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert call_order == ["coverage", "status"]
    assert payload["workspace_root"] == str(WORKSPACE_ROOT)
    assert payload["coverage_snapshot"] == expected_coverage_snapshot
    assert payload["status_snapshot"]["canonical_json_path"] == "ai_docs/system_status_snapshot.json"


def test_unified_main_kb_outputs_filtered_payload_and_failure_exit(monkeypatch, capsys) -> None:
    kb_result = FakeValidationResult(
        payload={"workspace_root": str(WORKSPACE_ROOT), "compliant": False},
        compliant=False,
        rule_results=[_failing_rule("knowledge_base.rule", domain="knowledge_base")],
    )
    monkeypatch.setattr(unified_cli, "validate_knowledge_base", lambda workspace_root, selected_rule_ids: kb_result)
    monkeypatch.setattr(unified_cli, "should_fail_rule_results", lambda rule_results, fail_on: True)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "inf_work",
            "kb",
            str(WORKSPACE_ROOT),
            "--pretty",
            "--only-failures",
            "--category",
            "governance",
            "--fail-on",
            "warning",
        ],
    )

    exit_code = unified_cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["workspace_root"] == str(WORKSPACE_ROOT)
    assert payload["rule_summary"]["failed_rules"] == 1
    assert payload["report_filters"]["only_failures"] is True
    assert payload["report_filters"]["categories"] == ["governance"]
    assert payload["report_filters"]["fail_on"] == "warning"


def test_unified_main_all_with_fix_status_outputs_aggregate_payload(monkeypatch, capsys) -> None:
    workspace_result = FakeValidationResult(
        payload={"workspace_root": str(WORKSPACE_ROOT), "kind": "workspace"},
        rule_results=[_passing_rule("workspace.rule", domain="workspace")],
    )
    kb_result = FakeValidationResult(
        payload={"workspace_root": str(WORKSPACE_ROOT), "kind": "kb"},
        rule_results=[_passing_rule("knowledge_base.rule", domain="knowledge_base")],
    )
    status_result = FakeValidationResult(
        payload={"workspace_root": str(WORKSPACE_ROOT), "kind": "status"},
        rule_results=[_passing_rule("status.rule", domain="status")],
    )
    monkeypatch.setattr(unified_cli, "validate_workspace", lambda workspace_root, selected_rule_ids: workspace_result)
    monkeypatch.setattr(unified_cli, "validate_knowledge_base", lambda workspace_root, selected_rule_ids: kb_result)
    monkeypatch.setattr(unified_cli, "repair_and_validate_system_status", lambda workspace_root, selected_rule_ids: status_result)
    monkeypatch.setattr(unified_cli, "should_fail_rule_results", lambda rule_results, fail_on: False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "inf_work",
            "all",
            str(WORKSPACE_ROOT),
            "--pretty",
            "--fix-status",
            "--domain-filter",
            "status",
            "--profile",
            "ci",
        ],
    )

    exit_code = unified_cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["workspace_root"] == str(WORKSPACE_ROOT)
    assert payload["aggregate_rule_summary"]["total_rules"] == 1
    assert payload["report_filters"]["fix_status"] is True
    assert payload["report_filters"]["domain_filter"] == "status"
    assert payload["report_filters"]["profiles"] == ["ci"]


def test_unified_main_workspace_outputs_failure_exit_when_threshold_trips(monkeypatch, capsys) -> None:
    workspace_result = FakeValidationResult(
        payload={"workspace_root": str(WORKSPACE_ROOT), "compliant": False},
        compliant=False,
        rule_results=[_failing_rule("workspace.rule", domain="workspace")],
    )
    monkeypatch.setattr(unified_cli, "validate_workspace", lambda workspace_root, selected_rule_ids: workspace_result)
    monkeypatch.setattr(unified_cli, "should_fail_rule_results", lambda rule_results, fail_on: True)
    monkeypatch.setattr(sys, "argv", ["inf_work", "workspace", str(WORKSPACE_ROOT), "--pretty"])

    exit_code = unified_cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["workspace_root"] == str(WORKSPACE_ROOT)
    assert payload["rule_summary"]["failed_rules"] == 1


def test_unified_main_status_check_fix_uses_repair_path(monkeypatch, capsys) -> None:
    status_result = FakeValidationResult(
        payload={"workspace_root": str(WORKSPACE_ROOT), "snapshot_path": "ai_docs/system_status_snapshot.json"},
        rule_results=[_passing_rule("status.rule", domain="status")],
    )
    monkeypatch.setattr(unified_cli, "repair_and_validate_system_status", lambda workspace_root, selected_rule_ids: status_result)
    monkeypatch.setattr(unified_cli, "should_fail_rule_results", lambda rule_results, fail_on: False)
    monkeypatch.setattr(sys, "argv", ["inf_work", "status-check", str(WORKSPACE_ROOT), "--pretty", "--fix"])

    exit_code = unified_cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["snapshot_path"] == "ai_docs/system_status_snapshot.json"
    assert payload["report_filters"]["fix"] is True


def test_unified_main_status_check_without_fix_uses_validation_path(monkeypatch, capsys) -> None:
    status_result = FakeValidationResult(
        payload={"workspace_root": str(WORKSPACE_ROOT), "snapshot_path": "ai_docs/system_status_snapshot.json"},
        rule_results=[_passing_rule("status.rule", domain="status")],
    )
    monkeypatch.setattr(unified_cli, "validate_system_status", lambda workspace_root, selected_rule_ids: status_result)
    monkeypatch.setattr(unified_cli, "should_fail_rule_results", lambda rule_results, fail_on: False)
    monkeypatch.setattr(sys, "argv", ["inf_work", "status-check", str(WORKSPACE_ROOT), "--pretty"])

    exit_code = unified_cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["snapshot_path"] == "ai_docs/system_status_snapshot.json"
    assert payload["report_filters"]["fix"] is False


def test_unified_main_summary_check_fix_uses_repair_path(monkeypatch, capsys) -> None:
    summary_result = FakeValidationResult(
        payload={"workspace_root": str(WORKSPACE_ROOT), "summary_path": "SYSTEM_SUMMARY.md"},
        rule_results=[_passing_rule("status.summary", domain="status")],
    )
    monkeypatch.setattr(unified_cli, "repair_and_validate_system_summary", lambda workspace_root: summary_result)
    monkeypatch.setattr(unified_cli, "should_fail_rule_results", lambda rule_results, fail_on: False)
    monkeypatch.setattr(sys, "argv", ["inf_work", "summary-check", str(WORKSPACE_ROOT), "--pretty", "--fix"])

    exit_code = unified_cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["summary_path"] == "SYSTEM_SUMMARY.md"
    assert payload["report_filters"]["fix"] is True


def test_unified_main_summary_check_without_fix_uses_validation_path(monkeypatch, capsys) -> None:
    summary_result = FakeValidationResult(
        payload={"workspace_root": str(WORKSPACE_ROOT), "summary_path": "SYSTEM_SUMMARY.md"},
        rule_results=[_passing_rule("status.summary", domain="status")],
    )
    monkeypatch.setattr(unified_cli, "validate_system_summary", lambda workspace_root: summary_result)
    monkeypatch.setattr(unified_cli, "should_fail_rule_results", lambda rule_results, fail_on: False)
    monkeypatch.setattr(sys, "argv", ["inf_work", "summary-check", str(WORKSPACE_ROOT), "--pretty"])

    exit_code = unified_cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["summary_path"] == "SYSTEM_SUMMARY.md"
    assert payload["report_filters"]["fix"] is False


def test_unified_main_all_without_fix_status_uses_status_validation(monkeypatch, capsys) -> None:
    workspace_result = FakeValidationResult(
        payload={"workspace_root": str(WORKSPACE_ROOT), "kind": "workspace"},
        rule_results=[_passing_rule("workspace.rule", domain="workspace")],
    )
    kb_result = FakeValidationResult(
        payload={"workspace_root": str(WORKSPACE_ROOT), "kind": "kb"},
        rule_results=[_passing_rule("knowledge_base.rule", domain="knowledge_base")],
    )
    status_result = FakeValidationResult(
        payload={"workspace_root": str(WORKSPACE_ROOT), "kind": "status"},
        rule_results=[_passing_rule("status.rule", domain="status")],
    )
    monkeypatch.setattr(unified_cli, "validate_workspace", lambda workspace_root, selected_rule_ids: workspace_result)
    monkeypatch.setattr(unified_cli, "validate_knowledge_base", lambda workspace_root, selected_rule_ids: kb_result)
    monkeypatch.setattr(unified_cli, "validate_system_status", lambda workspace_root, selected_rule_ids: status_result)
    monkeypatch.setattr(unified_cli, "should_fail_rule_results", lambda rule_results, fail_on: False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "inf_work",
            "all",
            str(WORKSPACE_ROOT),
            "--pretty",
            "--domain-filter",
            "status",
        ],
    )

    exit_code = unified_cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["aggregate_rule_summary"]["total_rules"] == 1
    assert payload["report_filters"]["fix_status"] is False


def test_unified_cli_module_main_raises_system_exit(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["inf_work", "workspace", str(WORKSPACE_ROOT), "--pretty"])

    assert _run_module_entrypoint(
        "inf_work.__main__",
        r"'inf_work\.__main__' found in sys\.modules after import of package 'inf_work'",
    ) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace_root"] == str(WORKSPACE_ROOT)


def test_unified_main_without_command_falls_back_to_workspace_root_dot(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}
    workspace_result = FakeValidationResult(
        payload={"workspace_root": str(WORKSPACE_ROOT), "compliant": True},
        rule_results=[_passing_rule("workspace.default", domain="workspace")],
    )

    def fake_validate_workspace(workspace_root, selected_rule_ids):
        captured["workspace_root"] = workspace_root
        captured["selected_rule_ids"] = selected_rule_ids
        return workspace_result

    monkeypatch.setattr(unified_cli, "validate_workspace", fake_validate_workspace)
    monkeypatch.setattr(sys, "argv", ["inf_work"])

    exit_code = unified_cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["workspace_root"] == Path(".")
    assert captured["selected_rule_ids"] is None
    assert payload["workspace_root"] == str(WORKSPACE_ROOT)
