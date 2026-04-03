from __future__ import annotations

import json
from pathlib import Path

import inf_work.remediation as remediation_module
from inf_work.remediation import apply_status_artifact_remediation, compile_status_artifact_remediation_plan, list_supported_remediation_strategies
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
    assert payload["simulation_available"] is False
    assert payload["simulation"] is None


def test_compile_status_artifact_remediation_plan_builds_dry_run_simulation(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir()
    (workspace_root / "knowledge_base").mkdir()
    (workspace_root / "ai_docs" / "system_status_snapshot.json").write_text('{"stale": true}', encoding="utf-8")
    (workspace_root / "SYSTEM_STATUS.md").write_text("# stale\n", encoding="utf-8")
    (workspace_root / "SYSTEM_SUMMARY.md").write_text("# old summary\n", encoding="utf-8")
    (workspace_root / "ai_docs" / "component_index.json").write_text('{"components": [], "metadata": {}}', encoding="utf-8")
    (workspace_root / "knowledge_base" / "kb_index.json").write_text(
        '{"total_techniques": 9, "total_bug_fixes": 1, "total_innovations": 2, "total_automation_patterns": 59}',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        remediation_module,
        "validate_system_status",
        lambda workspace_root, rule_ids: _status_validation_result(
            _rule_result("status.artifacts_exist", passed=False),
            _rule_result("status.snapshot_matches_workspace", passed=False),
            _rule_result("status.markdown_matches_snapshot", passed=False),
            _rule_result("status.summary_matches_workspace", passed=False),
            _rule_result("status.resolver_explicit_route_integrity", passed=True),
            compliant=False,
        ),
    )

    class FakeSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {
                "generated_at": "2026-04-03T20:00:00Z",
                "workspace_root": str(workspace_root.resolve()),
                "canonical_json_path": "ai_docs/system_status_snapshot.json",
                "derived_markdown_path": "SYSTEM_STATUS.md",
            }

    monkeypatch.setattr(remediation_module, "build_system_status_snapshot", lambda *args, **kwargs: FakeSnapshot())
    monkeypatch.setattr(remediation_module, "render_system_status_markdown", lambda snapshot: "# System Status\n\nupdated\n")
    monkeypatch.setattr(
        remediation_module,
        "render_system_summary_markdown",
        lambda snapshot, component_index, kb_index: "# System Summary\n\nupdated\n",
    )

    plan = compile_status_artifact_remediation_plan(workspace_root, include_simulation=True)
    payload = plan.to_dict()

    assert payload["plan_phase"] == "dry_run_structured_remediation"
    assert payload["plan_only"] is False
    assert payload["simulation_available"] is True
    assert payload["simulation"]["workspace_mutation"] is False
    assert payload["simulation"]["changed_paths"] == [
        "ai_docs/system_status_snapshot.json",
        "SYSTEM_STATUS.md",
        "SYSTEM_SUMMARY.md",
    ]
    assert payload["simulation"]["predicted_rule_summary"]["failed_rules"] == 0
    assert payload["simulation"]["predicted_rule_outcomes"][0]["rule_id"] == "status.artifacts_exist"
    assert payload["simulation"]["predicted_rule_outcomes"][0]["predicted_passed"] is True
    assert payload["simulation"]["artifact_changes"][0]["change_type"] == "update"
    assert payload["simulation"]["artifact_changes"][0]["diff_preview"][0].startswith("--- a/ai_docs/system_status_snapshot.json")


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


def test_apply_status_artifact_remediation_updates_governed_artifacts(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir()
    (workspace_root / "ai_docs" / "system_status_snapshot.json").write_text('{"stale": true}', encoding="utf-8")
    (workspace_root / "SYSTEM_STATUS.md").write_text("# stale\n", encoding="utf-8")
    (workspace_root / "SYSTEM_SUMMARY.md").write_text("# stale summary\n", encoding="utf-8")

    validation_calls = {"count": 0}

    def fake_validate_system_status(workspace_root: Path, rule_ids: set[str] | None) -> StatusValidationResult:
        validation_calls["count"] += 1
        if validation_calls["count"] == 1:
            return _status_validation_result(
                _rule_result("status.snapshot_matches_workspace", passed=False),
                _rule_result("status.summary_matches_workspace", passed=False),
                compliant=False,
            )
        return _status_validation_result(
            _rule_result("status.snapshot_matches_workspace", passed=True),
            _rule_result("status.summary_matches_workspace", passed=True),
            compliant=True,
        )

    def fake_validate_system_summary(workspace_root: Path) -> StatusValidationResult:
        return _status_validation_result(
            _rule_result("status.summary_matches_workspace", passed=True),
            compliant=True,
        )

    class FakeSnapshot:
        generated_at = "2026-04-03T21:00:00Z"
        canonical_json_path = "ai_docs/system_status_snapshot.json"
        derived_markdown_path = "SYSTEM_STATUS.md"

    def fake_write_system_status_outputs(
        workspace_root: Path,
        canonical_json_path: str,
        derived_markdown_path: str,
        summary_path: str,
    ) -> FakeSnapshot:
        (workspace_root / canonical_json_path).write_text(
            json.dumps({"generated_at": "2026-04-03T21:00:00Z", "status": "ok"}, indent=2),
            encoding="utf-8",
        )
        (workspace_root / derived_markdown_path).write_text("# System Status\n\nok\n", encoding="utf-8")
        (workspace_root / summary_path).write_text("# System Summary\n\nok\n", encoding="utf-8")
        return FakeSnapshot()

    monkeypatch.setattr(remediation_module, "validate_system_status", fake_validate_system_status)
    monkeypatch.setattr(remediation_module, "validate_system_summary", fake_validate_system_summary)
    monkeypatch.setattr(remediation_module, "write_system_status_outputs", fake_write_system_status_outputs)

    result = apply_status_artifact_remediation(workspace_root)

    assert result.execution_attempted is True
    assert result.applied is True
    assert result.compliant is True
    assert result.rollback_performed is False
    assert len(result.operation_results) == 3
    assert json.loads((workspace_root / "ai_docs" / "system_status_snapshot.json").read_text(encoding="utf-8"))["status"] == "ok"
    assert (workspace_root / "SYSTEM_STATUS.md").read_text(encoding="utf-8") == "# System Status\n\nok\n"
    assert (workspace_root / "SYSTEM_SUMMARY.md").read_text(encoding="utf-8") == "# System Summary\n\nok\n"


def test_apply_status_artifact_remediation_rolls_back_on_failed_verification(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir()
    original_snapshot = '{"stale": true}'
    original_status = "# stale\n"
    original_summary = "# stale summary\n"
    (workspace_root / "ai_docs" / "system_status_snapshot.json").write_text(original_snapshot, encoding="utf-8")
    (workspace_root / "SYSTEM_STATUS.md").write_text(original_status, encoding="utf-8")
    (workspace_root / "SYSTEM_SUMMARY.md").write_text(original_summary, encoding="utf-8")

    validation_calls = {"count": 0}

    def fake_validate_system_status(workspace_root: Path, rule_ids: set[str] | None) -> StatusValidationResult:
        validation_calls["count"] += 1
        if validation_calls["count"] == 1:
            return _status_validation_result(
                _rule_result("status.snapshot_matches_workspace", passed=False),
                compliant=False,
            )
        return _status_validation_result(
            _rule_result("status.snapshot_matches_workspace", passed=False),
            compliant=False,
        )

    def fake_validate_system_summary(workspace_root: Path) -> StatusValidationResult:
        return _status_validation_result(
            _rule_result("status.summary_matches_workspace", passed=True),
            compliant=True,
        )

    class FakeSnapshot:
        generated_at = "2026-04-03T21:30:00Z"
        canonical_json_path = "ai_docs/system_status_snapshot.json"
        derived_markdown_path = "SYSTEM_STATUS.md"

    def fake_write_system_status_outputs(
        workspace_root: Path,
        canonical_json_path: str,
        derived_markdown_path: str,
        summary_path: str,
    ) -> FakeSnapshot:
        (workspace_root / canonical_json_path).write_text('{"status": "broken"}', encoding="utf-8")
        (workspace_root / derived_markdown_path).write_text("# broken\n", encoding="utf-8")
        (workspace_root / summary_path).write_text("# broken summary\n", encoding="utf-8")
        return FakeSnapshot()

    monkeypatch.setattr(remediation_module, "validate_system_status", fake_validate_system_status)
    monkeypatch.setattr(remediation_module, "validate_system_summary", fake_validate_system_summary)
    monkeypatch.setattr(remediation_module, "write_system_status_outputs", fake_write_system_status_outputs)

    result = apply_status_artifact_remediation(workspace_root)

    assert result.execution_attempted is True
    assert result.applied is False
    assert result.compliant is False
    assert result.rollback_performed is True
    assert result.rollback_summary["restored_paths"] == [
        "SYSTEM_STATUS.md",
        "SYSTEM_SUMMARY.md",
        "ai_docs/system_status_snapshot.json",
    ]
    assert (workspace_root / "ai_docs" / "system_status_snapshot.json").read_text(encoding="utf-8") == original_snapshot
    assert (workspace_root / "SYSTEM_STATUS.md").read_text(encoding="utf-8") == original_status
    assert (workspace_root / "SYSTEM_SUMMARY.md").read_text(encoding="utf-8") == original_summary