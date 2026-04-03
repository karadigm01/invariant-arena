from __future__ import annotations

from pathlib import Path

import inf_work.remediation as remediation_module
from inf_work.remediation import compile_status_artifact_remediation_plan, list_supported_remediation_strategies
from inf_work.rules import RuleFinding, RuleResult
from inf_work.system_status import StatusValidationResult


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


def _rule_result(rule_id: str, *, passed: bool) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        domain="status",
        category="artifact_integrity",
        severity="error",
        description=f"{rule_id} description",
        passed=passed,
        findings=[]
        if passed
        else [
            RuleFinding(
                message="failed",
                source_file="SYSTEM_STATUS.md",
                item_identifier="artifact",
                field_name="consistency",
            )
        ],
    )


def _status_validation_result(*rule_results: RuleResult, compliant: bool) -> StatusValidationResult:
    return StatusValidationResult(
        workspace_root=str(WORKSPACE_ROOT),
        snapshot_path="ai_docs/system_status_snapshot.json",
        markdown_path="SYSTEM_STATUS.md",
        summary_path="SYSTEM_SUMMARY.md",
        compliant=compliant,
        issues=[],
        rule_results=list(rule_results),
    )


def test_list_supported_remediation_strategies_returns_phase_one_strategy() -> None:
    strategies = list_supported_remediation_strategies()

    assert len(strategies) == 1
    assert strategies[0].strategy_id == "strategy_status_artifact_regeneration_plan"
    assert strategies[0].supported_rule_ids == list(remediation_module.SUPPORTED_STATUS_ARTIFACT_TRIGGER_RULE_IDS)


def test_compile_status_artifact_remediation_plan_builds_supported_plan(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_validate_system_status(workspace_root: Path, rule_ids: set[str] | None) -> StatusValidationResult:
        captured["workspace_root"] = workspace_root
        captured["rule_ids"] = rule_ids
        return _status_validation_result(
            _rule_result("status.snapshot_matches_workspace", passed=False),
            _rule_result("status.summary_matches_workspace", passed=False),
            _rule_result("status.artifacts_exist", passed=False),
            compliant=False,
        )

    monkeypatch.setattr(remediation_module, "validate_system_status", fake_validate_system_status)

    plan = compile_status_artifact_remediation_plan(WORKSPACE_ROOT, {"status.snapshot_matches_workspace"})
    payload = plan.to_dict()

    assert captured == {
        "workspace_root": WORKSPACE_ROOT.resolve(),
        "rule_ids": {"status.snapshot_matches_workspace"},
    }
    assert plan.plan_available is True
    assert plan.current_status_compliant is False
    assert payload["selected_strategy"]["strategy_id"] == "strategy_status_artifact_regeneration_plan"
    assert payload["triggering_rule_ids"] == [
        "status.snapshot_matches_workspace",
        "status.summary_matches_workspace",
    ]
    assert payload["unsupported_failing_rule_ids"] == ["status.artifacts_exist"]
    assert [operation["operation_type"] for operation in payload["operations"]] == [
        "regenerate_artifact",
        "run_validation_profile",
        "run_validation_profile",
    ]
    assert payload["operations"][0]["target_paths"] == [
        "ai_docs/system_status_snapshot.json",
        "SYSTEM_STATUS.md",
        "SYSTEM_SUMMARY.md",
    ]
    assert payload["verification_contract"]["required_rule_ids"] == [
        "status.snapshot_matches_workspace",
        "status.summary_matches_workspace",
    ]
    assert payload["provenance"]["derived_from_components"] == [
        "system_status_generator",
        "unified_cli_entry_point",
        "remediation_plan_compiler",
    ]


def test_compile_status_artifact_remediation_plan_returns_noop_when_status_is_compliant(monkeypatch) -> None:
    monkeypatch.setattr(
        remediation_module,
        "validate_system_status",
        lambda workspace_root, rule_ids: _status_validation_result(
            _rule_result("status.snapshot_matches_workspace", passed=True),
            _rule_result("status.markdown_matches_snapshot", passed=True),
            _rule_result("status.summary_matches_workspace", passed=True),
            compliant=True,
        ),
    )

    plan = compile_status_artifact_remediation_plan(WORKSPACE_ROOT)

    assert plan.plan_available is False
    assert plan.current_status_compliant is True
    assert plan.selected_strategy is None
    assert plan.operations == []
    assert plan.triggering_rule_ids == []
    assert "already match the current governed workspace state" in plan.notes[-1]


def test_compile_status_artifact_remediation_plan_reports_unsupported_failures(monkeypatch) -> None:
    monkeypatch.setattr(
        remediation_module,
        "validate_system_status",
        lambda workspace_root, rule_ids: _status_validation_result(
            _rule_result("status.artifacts_exist", passed=False),
            compliant=False,
        ),
    )

    plan = compile_status_artifact_remediation_plan(WORKSPACE_ROOT)

    assert plan.plan_available is False
    assert plan.current_status_compliant is False
    assert plan.unsupported_failing_rule_ids == ["status.artifacts_exist"]
    assert plan.rollback_contract is not None
    assert "outside the supported phase-1 remediation slice" in plan.notes[-1]