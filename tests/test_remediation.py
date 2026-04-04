from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import inf_work.remediation as remediation_module
from inf_work.remediation import (
    apply_package_public_api_export_remediation,
    apply_remediation_plan,
    apply_status_artifact_remediation,
    compile_package_public_api_export_remediation_plan,
    compile_remediation_plan,
    compile_status_artifact_remediation_plan,
    list_supported_remediation_strategies,
)
from inf_work.rules import RuleFinding, RuleResult
from inf_work.system_status import StatusValidationResult


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class FakeKnowledgeBaseValidationResult:
    workspace_root: str
    compliant: bool
    issues: list[object]
    rule_results: list[RuleResult]

    def to_dict(self) -> dict[str, object]:
        return {
            "workspace_root": self.workspace_root,
            "compliant": self.compliant,
            "issues": list(self.issues),
            "rule_results": [rule_result.to_dict() for rule_result in self.rule_results],
        }


def _rule_result(
    rule_id: str,
    *,
    passed: bool,
    domain: str = "status",
    category: str = "artifact_integrity",
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        domain=domain,
        category=category,
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


def _kb_validation_result(*rule_results: RuleResult, compliant: bool, workspace_root: Path) -> FakeKnowledgeBaseValidationResult:
    return FakeKnowledgeBaseValidationResult(
        workspace_root=str(workspace_root.resolve()),
        compliant=compliant,
        issues=[],
        rule_results=list(rule_results),
    )


def test_list_supported_remediation_strategies_returns_phase_one_strategy() -> None:
    strategies = list_supported_remediation_strategies()

    assert len(strategies) == 2
    assert strategies[0].strategy_id == "strategy_status_artifact_regeneration_plan"
    assert strategies[0].supported_rule_ids == list(remediation_module.SUPPORTED_STATUS_ARTIFACT_TRIGGER_RULE_IDS)
    assert strategies[0].supported_intent_ids == list(remediation_module.SUPPORTED_GOVERNED_INTENT_IDS)
    assert strategies[1].strategy_id == "strategy_package_public_api_export_sync"
    assert strategies[1].supported_rule_ids == list(remediation_module.SUPPORTED_SOURCE_LEVEL_TRIGGER_RULE_IDS)
    assert strategies[1].supported_intent_ids == []


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


def test_compile_status_artifact_remediation_plan_supports_explicit_status_refresh_intent(monkeypatch) -> None:
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

    plan = compile_status_artifact_remediation_plan(
        WORKSPACE_ROOT,
        intent_id="intent.status.refresh_artifacts",
    )

    assert plan.plan_available is True
    assert plan.plan_phase == "intent_driven_governed_change"
    assert plan.provenance.governed_intent_ids == ["intent.status.refresh_artifacts"]
    assert plan.triggering_rule_ids == list(remediation_module.SUPPORTED_STATUS_ARTIFACT_TRIGGER_RULE_IDS)
    assert plan.selected_strategy is not None


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


def test_remediation_serializers_and_optional_helpers_cover_none_paths() -> None:
    operation_result = remediation_module.OperationExecutionResult(
        operation_id="operation-id",
        operation_type="run_validation_profile",
        target_paths=["SYSTEM_STATUS.md"],
        status="completed",
        mutation_performed=False,
        details={"ok": True},
    )
    execution_result = remediation_module.RemediationExecutionResult(
        workspace_root=str(WORKSPACE_ROOT),
        plan_id="plan-id",
        execution_phase="phase",
        execution_attempted=False,
        plan_available=False,
        applied=False,
        compliant=True,
        rollback_performed=False,
        rollback_summary={"restored_paths": [], "deleted_paths": []},
        triggering_rule_ids=[],
        unsupported_failing_rule_ids=[],
        operation_results=[operation_result],
        status_validation=None,
        summary_validation=None,
        knowledge_base_validation=None,
        notes=["note"],
    )

    assert operation_result.to_dict()["details"] == {"ok": True}
    assert execution_result.to_dict()["operation_results"][0]["operation_id"] == "operation-id"
    assert remediation_module._sha256_text(None) is None
    assert remediation_module._read_optional_text(WORKSPACE_ROOT / "does-not-exist.txt") is None
    assert remediation_module._line_preview(None) == []


def test_extract_module_export_surface_and_provider_grouping_cover_fallback_paths(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "import json\n\n"
        "def exported_function():\n"
        "    return 1\n\n"
        "__all__ = UNKNOWN_SYMBOL\n",
        encoding="utf-8",
    )

    exported_names, explicit_all = remediation_module._extract_module_export_surface(module_path)

    assert "json" in exported_names
    assert "exported_function" in exported_names
    assert explicit_all is None
    assert remediation_module._extract_package_import_symbols("import inf_work") == set()

    package_root = tmp_path / "src" / "inf_work"
    package_root.mkdir(parents=True)
    (package_root / "alpha.py").write_text("def shared_symbol():\n    return 'alpha'\n", encoding="utf-8")
    (package_root / "beta.py").write_text(
        "def shared_symbol():\n    return 'beta'\n\n"
        "def unique_symbol():\n    return 'unique'\n",
        encoding="utf-8",
    )
    (package_root / "__init__.py").write_text("__all__ = []\n", encoding="utf-8")

    module_to_symbols, unsupported_symbols = remediation_module._group_missing_symbols_by_provider(
        tmp_path,
        ["missing_symbol", "shared_symbol", "unique_symbol"],
    )

    assert module_to_symbols == {"beta": ["unique_symbol"]}
    assert unsupported_symbols == ["missing_symbol", "shared_symbol"]


def test_extract_module_export_surface_ignores_non_assign_nodes_and_non_all_assignments(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        '"module doc"\n\n'
        "VALUE = 1\n\n"
        "class ExportedClass:\n"
        "    pass\n",
        encoding="utf-8",
    )

    exported_names, explicit_all = remediation_module._extract_module_export_surface(module_path)

    assert "VALUE" in exported_names
    assert "ExportedClass" in exported_names
    assert explicit_all is None


def test_append_grouped_import_symbols_and_artifact_change_cover_insert_create_and_noop(tmp_path: Path) -> None:
    current_text = '__all__ = [\n\t"existing_symbol",\n]\n'

    updated_text = remediation_module._append_grouped_import_symbols(current_text, "beta", ["unique_symbol"])

    assert updated_text.startswith("from .beta import (\n\tunique_symbol,\n)\n\n__all__ = [")

    created_change = remediation_module._build_artifact_change(tmp_path, "new-file.txt", "created\n")
    assert created_change["change_type"] == "create"
    assert created_change["current_exists"] is False

    existing_path = tmp_path / "existing.txt"
    existing_path.write_text("same\n", encoding="utf-8")
    noop_change = remediation_module._build_artifact_change(tmp_path, "existing.txt", "same\n")
    assert noop_change["change_type"] == "noop"
    assert noop_change["content_changed"] is False


def test_append_grouped_import_symbols_skips_blank_lines_in_existing_block() -> None:
    current_text = (
        "from .beta import (\n"
        "\n"
        "\tunique_symbol,\n"
        ")\n\n"
        "__all__ = [\n"
        '\t"unique_symbol",\n'
        "]\n"
    )

    updated_text = remediation_module._append_grouped_import_symbols(current_text, "beta", ["second_symbol"])

    assert "\n\n\t" not in updated_text.split("from .beta import (", maxsplit=1)[1]
    assert "\tsecond_symbol," in updated_text


def test_append_all_entries_skips_blank_lines_in_existing_all_block() -> None:
    current_text = '__all__ = [\n\n\t"existing_symbol",\n]\n'

    updated_text = remediation_module._append_all_entries(current_text, ["second_symbol"])

    assert '\t"existing_symbol",' in updated_text
    assert '\t"second_symbol",' in updated_text
    assert "\n\n\t\"existing_symbol\"" not in updated_text


def test_build_predicted_rule_outcomes_can_mark_would_fail_for_non_boolean_pass_value() -> None:
    non_boolean_rule = RuleResult(
        rule_id="status.snapshot_matches_workspace",
        domain="status",
        category="artifact_integrity",
        severity="error",
        description="non boolean",
        passed="truthy-string",
        findings=[],
    )

    predicted_outcomes, predicted_summary = remediation_module._build_predicted_rule_outcomes([non_boolean_rule])

    assert predicted_outcomes[0]["predicted_effect"] == "would_fail"
    assert predicted_summary["failed_rules"] == 0


def test_build_package_export_simulation_preserves_target_rule_when_symbols_are_unsupported(tmp_path: Path) -> None:
    module_path = tmp_path / "src" / "inf_work" / "__init__.py"
    module_path.parent.mkdir(parents=True)
    module_path.write_text('__all__ = []\n', encoding="utf-8")

    rule_result = _rule_result(
        "knowledge_base.component_doc_python_api_symbols_valid",
        passed=False,
        domain="knowledge_base",
        category="api_surface",
    )

    simulation = remediation_module._build_package_export_simulation(
        tmp_path,
        [rule_result],
        {
            "unsupported_symbols": ["shared_symbol"],
            "module_path": "src/inf_work/__init__.py",
            "updated_text": '__all__ = []\n',
        },
    )

    assert simulation["predicted_rule_outcomes"][0]["predicted_passed"] is False
    assert simulation["predicted_rule_outcomes"][0]["predicted_effect"] == "unchanged"


def test_restore_artifact_pre_state_deletes_created_files_and_build_no_plan_result() -> None:
    workspace_root = WORKSPACE_ROOT / ".pytest-remediation-temp-do-not-keep"
    if workspace_root.exists():
        raise AssertionError("Unexpected leftover remediation temp path.")

    workspace_root.mkdir()
    try:
        created_path = workspace_root / "created.txt"
        created_path.write_text("temporary\n", encoding="utf-8")
        rollback_summary = remediation_module._restore_artifact_pre_state(
            workspace_root,
            {"created.txt": {"existed": False, "text": None, "sha256": None}},
        )

        assert rollback_summary == {"restored_paths": [], "deleted_paths": ["created.txt"]}
        assert not created_path.exists()

        plan = remediation_module.RemediationPlan(
            workspace_root=str(workspace_root),
            plan_id="no-plan",
            objective="noop",
            plan_phase="phase",
            plan_only=True,
            current_status_compliant=True,
            plan_available=False,
            selected_rule_ids=[],
            triggering_rule_ids=[],
            unsupported_failing_rule_ids=[],
            selected_strategy=None,
            triggering_evidence=[],
            current_rule_summary={},
            affected_paths=[],
            operations=[],
            verification_contract=None,
            rollback_contract=None,
            provenance=remediation_module.ChangeProvenanceRecord("id", "kind", [], [], [], [], []),
            simulation_available=False,
            simulation=None,
            notes=["existing"],
        )

        result = remediation_module._build_no_plan_execution_result(plan, notes=["note"])

        assert result.to_dict()["execution_attempted"] is False
        assert result.to_dict()["notes"] == ["note"]
    finally:
        workspace_root.rmdir()


def test_restore_artifact_pre_state_ignores_missing_paths_that_never_existed(tmp_path: Path) -> None:
    rollback_summary = remediation_module._restore_artifact_pre_state(
        tmp_path,
        {"missing.txt": {"existed": False, "text": None, "sha256": None}},
    )

    assert rollback_summary == {"restored_paths": [], "deleted_paths": []}


def test_apply_status_artifact_remediation_returns_noop_when_no_plan_is_available(monkeypatch, tmp_path: Path) -> None:
    plan = remediation_module.RemediationPlan(
        workspace_root=str(tmp_path.resolve()),
        plan_id="no-plan",
        objective="noop",
        plan_phase="phase",
        plan_only=True,
        current_status_compliant=True,
        plan_available=False,
        selected_rule_ids=[],
        triggering_rule_ids=[],
        unsupported_failing_rule_ids=[],
        selected_strategy=None,
        triggering_evidence=[],
        current_rule_summary={},
        affected_paths=[],
        operations=[],
        verification_contract=None,
        rollback_contract=None,
        provenance=remediation_module.ChangeProvenanceRecord("id", "kind", [], [], [], [], []),
        simulation_available=False,
        simulation=None,
        notes=["already clean"],
    )
    monkeypatch.setattr(remediation_module, "compile_status_artifact_remediation_plan", lambda *args, **kwargs: plan)

    result = remediation_module.apply_status_artifact_remediation(tmp_path)

    assert result.execution_attempted is False
    assert "No supported applied remediation was executed" in result.notes[0]


def test_apply_status_artifact_remediation_rolls_back_on_exception(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir()
    (workspace_root / "ai_docs" / "system_status_snapshot.json").write_text('{"stale": true}', encoding="utf-8")
    (workspace_root / "SYSTEM_STATUS.md").write_text("# stale\n", encoding="utf-8")
    (workspace_root / "SYSTEM_SUMMARY.md").write_text("# stale summary\n", encoding="utf-8")

    validation_calls = {"count": 0}

    def fake_validate_system_status(workspace_root: Path, rule_ids: set[str] | None) -> StatusValidationResult:
        validation_calls["count"] += 1
        if validation_calls["count"] == 1:
            return _status_validation_result(_rule_result("status.snapshot_matches_workspace", passed=False), compliant=False)
        return _status_validation_result(_rule_result("status.snapshot_matches_workspace", passed=True), compliant=True)

    monkeypatch.setattr(remediation_module, "validate_system_status", fake_validate_system_status)
    monkeypatch.setattr(
        remediation_module,
        "write_system_status_outputs",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("forced failure")),
    )

    result = remediation_module.apply_status_artifact_remediation(workspace_root)

    assert result.applied is False
    assert result.rollback_performed is True
    assert any(note.endswith("forced failure") for note in result.notes)


def test_compile_package_public_api_export_remediation_plan_builds_source_level_plan(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir()
    (workspace_root / "src" / "inf_work").mkdir(parents=True)
    (workspace_root / "ai_docs" / "package_public_api_surface_20260331T000000Z.json").write_text(
        json.dumps(
            {
                "interfaces": {
                    "python_api": [
                        "from inf_work import apply_status_artifact_remediation, compile_status_artifact_remediation_plan"
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    (workspace_root / "src" / "inf_work" / "__init__.py").write_text(
        'from .remediation import (\n\tcompile_status_artifact_remediation_plan,\n)\n\n__all__ = [\n\t"compile_status_artifact_remediation_plan",\n]\n',
        encoding="utf-8",
    )
    (workspace_root / "src" / "inf_work" / "remediation.py").write_text(
        'def apply_status_artifact_remediation():\n    return None\n\n'
        'def compile_status_artifact_remediation_plan():\n    return None\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        remediation_module,
        "validate_knowledge_base",
        lambda workspace_root, rule_ids: _kb_validation_result(
            _rule_result(
                "knowledge_base.component_doc_python_api_symbols_valid",
                passed=False,
                domain="knowledge_base",
                category="api_surface",
            ),
            compliant=False,
            workspace_root=Path(workspace_root),
        ),
    )

    plan = compile_package_public_api_export_remediation_plan(
        workspace_root,
        {"knowledge_base.component_doc_python_api_symbols_valid"},
        include_simulation=True,
    )

    assert plan.plan_available is True
    assert plan.selected_strategy is not None
    assert plan.selected_strategy.strategy_id == "strategy_package_public_api_export_sync"
    assert plan.operations[0].operation_type == "rewrite_python_source"
    assert plan.affected_paths == ["src/inf_work/__init__.py"]
    assert plan.simulation_available is True
    assert plan.simulation is not None
    assert plan.simulation["changed_paths"] == ["src/inf_work/__init__.py"]


def test_compile_package_public_api_export_remediation_plan_reports_unsupported_symbols(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir()
    (workspace_root / "src" / "inf_work").mkdir(parents=True)
    (workspace_root / "ai_docs" / "package_public_api_surface_20260331T000000Z.json").write_text(
        json.dumps({"interfaces": {"python_api": ["from inf_work import shared_symbol"]}}),
        encoding="utf-8",
    )
    (workspace_root / "src" / "inf_work" / "__init__.py").write_text("__all__ = []\n", encoding="utf-8")
    (workspace_root / "src" / "inf_work" / "alpha.py").write_text("def shared_symbol():\n    return 'a'\n", encoding="utf-8")
    (workspace_root / "src" / "inf_work" / "beta.py").write_text("def shared_symbol():\n    return 'b'\n", encoding="utf-8")

    monkeypatch.setattr(
        remediation_module,
        "validate_knowledge_base",
        lambda workspace_root, rule_ids: _kb_validation_result(
            _rule_result(
                "knowledge_base.component_doc_python_api_symbols_valid",
                passed=False,
                domain="knowledge_base",
                category="api_surface",
            ),
            compliant=False,
            workspace_root=Path(workspace_root),
        ),
    )

    plan = compile_package_public_api_export_remediation_plan(workspace_root)

    assert plan.plan_available is False
    assert "could not be resolved to exactly one governed provider module" in plan.notes[-1]


def test_compile_package_public_api_export_remediation_plan_reports_already_synced_surface(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir()
    (workspace_root / "src" / "inf_work").mkdir(parents=True)
    (workspace_root / "ai_docs" / "package_public_api_surface_20260331T000000Z.json").write_text(
        json.dumps({"interfaces": {"python_api": ["from inf_work import synced_symbol"]}}),
        encoding="utf-8",
    )
    (workspace_root / "src" / "inf_work" / "__init__.py").write_text(
        'from .remediation import (\n\tsynced_symbol,\n)\n\n__all__ = [\n\t"synced_symbol",\n]\n',
        encoding="utf-8",
    )
    (workspace_root / "src" / "inf_work" / "remediation.py").write_text("def synced_symbol():\n    return 1\n", encoding="utf-8")

    monkeypatch.setattr(
        remediation_module,
        "validate_knowledge_base",
        lambda workspace_root, rule_ids: _kb_validation_result(
            _rule_result(
                "knowledge_base.component_doc_python_api_symbols_valid",
                passed=False,
                domain="knowledge_base",
                category="api_surface",
            ),
            compliant=False,
            workspace_root=Path(workspace_root),
        ),
    )

    plan = compile_package_public_api_export_remediation_plan(workspace_root)

    assert plan.plan_available is False
    assert plan.notes[-1] == "The package public API documentation already matches the explicit `inf_work` package re-export surface."


def test_build_package_export_sync_state_updates_all_when_imports_exist_but_all_is_missing_symbol(tmp_path: Path) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir()
    (workspace_root / "src" / "inf_work").mkdir(parents=True)
    (workspace_root / "ai_docs" / "package_public_api_surface_20260331T000000Z.json").write_text(
        json.dumps({"interfaces": {"python_api": ["from inf_work import synced_symbol"]}}),
        encoding="utf-8",
    )
    (workspace_root / "src" / "inf_work" / "__init__.py").write_text(
        'from .remediation import (\n\tsynced_symbol,\n)\n\n__all__ = [\n]\n',
        encoding="utf-8",
    )
    (workspace_root / "src" / "inf_work" / "remediation.py").write_text("def synced_symbol():\n    return 1\n", encoding="utf-8")

    sync_state = remediation_module._build_package_export_sync_state(workspace_root)

    assert sync_state["missing_import_symbols"] == []
    assert sync_state["missing_all_symbols"] == ["synced_symbol"]
    assert '"synced_symbol"' in sync_state["updated_text"]


def test_compile_package_public_api_export_remediation_plan_reports_unsupported_rule_slice(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "ai_docs").mkdir()
    (tmp_path / "src" / "inf_work").mkdir(parents=True)
    (tmp_path / "ai_docs" / "package_public_api_surface_20260331T000000Z.json").write_text(
        json.dumps({"interfaces": {"python_api": []}}),
        encoding="utf-8",
    )
    (tmp_path / "src" / "inf_work" / "__init__.py").write_text('__all__ = []\n', encoding="utf-8")

    monkeypatch.setattr(
        remediation_module,
        "validate_knowledge_base",
        lambda workspace_root, rule_ids: _kb_validation_result(
            _rule_result(
                "knowledge_base.unrelated_rule",
                passed=False,
                domain="knowledge_base",
                category="api_surface",
            ),
            compliant=False,
            workspace_root=Path(workspace_root),
        ),
    )

    plan = compile_package_public_api_export_remediation_plan(tmp_path)

    assert plan.plan_available is False
    assert "outside the supported Phase 4 package-export remediation slice" in plan.notes[-1]


def test_compile_remediation_plan_prefers_package_export_slice_for_kb_rule(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    monkeypatch.setattr(
        remediation_module,
        "compile_status_artifact_remediation_plan",
        lambda workspace_root, rule_ids, include_simulation=False, intent_id=None: remediation_module.RemediationPlan(
            workspace_root=str(Path(workspace_root).resolve()),
            plan_id="status",
            objective="status",
            plan_phase="plan_only_structured_remediation",
            plan_only=True,
            current_status_compliant=True,
            plan_available=False,
            selected_rule_ids=sorted(rule_ids) if rule_ids else [],
            triggering_rule_ids=[],
            unsupported_failing_rule_ids=[],
            selected_strategy=None,
            triggering_evidence=[],
            current_rule_summary={},
            affected_paths=[],
            operations=[],
            verification_contract=None,
            rollback_contract=None,
            provenance=remediation_module.ChangeProvenanceRecord("id", "kind", [], [], [], [], []),
            simulation_available=False,
            simulation=None,
            notes=[],
        ),
    )
    monkeypatch.setattr(
        remediation_module,
        "compile_package_public_api_export_remediation_plan",
        lambda workspace_root, rule_ids, include_simulation=False: remediation_module.RemediationPlan(
            workspace_root=str(Path(workspace_root).resolve()),
            plan_id="package",
            objective="package",
            plan_phase="bounded_source_level_remediation",
            plan_only=True,
            current_status_compliant=False,
            plan_available=True,
            selected_rule_ids=sorted(rule_ids) if rule_ids else [],
            triggering_rule_ids=["knowledge_base.component_doc_python_api_symbols_valid"],
            unsupported_failing_rule_ids=[],
            selected_strategy=remediation_module.PACKAGE_EXPORT_SYNC_REMEDIATION_STRATEGY,
            triggering_evidence=[],
            current_rule_summary={},
            affected_paths=["src/inf_work/__init__.py"],
            operations=[],
            verification_contract=None,
            rollback_contract=None,
            provenance=remediation_module.ChangeProvenanceRecord("id", "kind", [], [], [], [], []),
            simulation_available=False,
            simulation=None,
            notes=[],
        ),
    )

    plan = compile_remediation_plan(workspace_root, {"knowledge_base.component_doc_python_api_symbols_valid"})

    assert plan.plan_id == "package"


def test_apply_package_public_api_export_remediation_updates_init_and_verifies(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir()
    (workspace_root / "src" / "inf_work").mkdir(parents=True)
    doc_path = workspace_root / "ai_docs" / "package_public_api_surface_20260331T000000Z.json"
    init_path = workspace_root / "src" / "inf_work" / "__init__.py"
    remediation_path = workspace_root / "src" / "inf_work" / "remediation.py"
    doc_path.write_text(
        json.dumps(
            {
                "interfaces": {
                    "python_api": [
                        "from inf_work import apply_status_artifact_remediation, compile_status_artifact_remediation_plan"
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    init_path.write_text(
        'from .remediation import (\n\tcompile_status_artifact_remediation_plan,\n)\n\n__all__ = [\n\t"compile_status_artifact_remediation_plan",\n]\n',
        encoding="utf-8",
    )
    remediation_path.write_text(
        'def apply_status_artifact_remediation():\n    return None\n\n'
        'def compile_status_artifact_remediation_plan():\n    return None\n',
        encoding="utf-8",
    )

    validation_calls = {"count": 0}

    def fake_validate_knowledge_base(workspace_root: Path, rule_ids: set[str] | None):
        validation_calls["count"] += 1
        passed = validation_calls["count"] > 1
        return _kb_validation_result(
            _rule_result(
                "knowledge_base.component_doc_python_api_symbols_valid",
                passed=passed,
                domain="knowledge_base",
                category="api_surface",
            ),
            compliant=passed,
            workspace_root=Path(workspace_root),
        )

    monkeypatch.setattr(remediation_module, "validate_knowledge_base", fake_validate_knowledge_base)

    result = apply_package_public_api_export_remediation(
        workspace_root,
        {"knowledge_base.component_doc_python_api_symbols_valid"},
    )

    assert result.applied is True
    assert result.compliant is True
    assert result.rollback_performed is False
    updated_text = init_path.read_text(encoding="utf-8")
    assert "apply_status_artifact_remediation" in updated_text
    assert '"apply_status_artifact_remediation"' in updated_text
    assert result.knowledge_base_validation is not None


def test_apply_package_public_api_export_remediation_returns_noop_when_no_plan_is_available(monkeypatch, tmp_path: Path) -> None:
    plan = remediation_module.RemediationPlan(
        workspace_root=str(tmp_path.resolve()),
        plan_id="no-package-plan",
        objective="noop",
        plan_phase="phase",
        plan_only=True,
        current_status_compliant=True,
        plan_available=False,
        selected_rule_ids=[],
        triggering_rule_ids=[],
        unsupported_failing_rule_ids=[],
        selected_strategy=None,
        triggering_evidence=[],
        current_rule_summary={},
        affected_paths=[],
        operations=[],
        verification_contract=None,
        rollback_contract=None,
        provenance=remediation_module.ChangeProvenanceRecord("id", "kind", [], [], [], [], []),
        simulation_available=False,
        simulation=None,
        notes=["already synced"],
    )
    monkeypatch.setattr(remediation_module, "compile_package_public_api_export_remediation_plan", lambda *args, **kwargs: plan)

    result = remediation_module.apply_package_public_api_export_remediation(tmp_path)

    assert result.execution_attempted is False
    assert "No supported applied remediation was executed" in result.notes[0]


def test_apply_package_public_api_export_remediation_rolls_back_on_failed_verification(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir()
    (workspace_root / "src" / "inf_work").mkdir(parents=True)
    doc_path = workspace_root / "ai_docs" / "package_public_api_surface_20260331T000000Z.json"
    init_path = workspace_root / "src" / "inf_work" / "__init__.py"
    remediation_path = workspace_root / "src" / "inf_work" / "remediation.py"
    doc_path.write_text(
        json.dumps({"interfaces": {"python_api": ["from inf_work import apply_status_artifact_remediation"]}}),
        encoding="utf-8",
    )
    original_text = '__all__ = []\n'
    init_path.write_text(original_text, encoding="utf-8")
    remediation_path.write_text("def apply_status_artifact_remediation():\n    return None\n", encoding="utf-8")

    validation_calls = {"count": 0}

    def fake_validate_knowledge_base(workspace_root: Path, rule_ids: set[str] | None):
        validation_calls["count"] += 1
        return _kb_validation_result(
            _rule_result(
                "knowledge_base.component_doc_python_api_symbols_valid",
                passed=validation_calls["count"] > 1 and False,
                domain="knowledge_base",
                category="api_surface",
            ),
            compliant=False,
            workspace_root=Path(workspace_root),
        )

    monkeypatch.setattr(remediation_module, "validate_knowledge_base", fake_validate_knowledge_base)

    result = remediation_module.apply_package_public_api_export_remediation(
        workspace_root,
        {"knowledge_base.component_doc_python_api_symbols_valid"},
    )

    assert result.applied is False
    assert result.rollback_performed is True
    assert init_path.read_text(encoding="utf-8") == original_text
    assert result.knowledge_base_validation is not None


def test_apply_package_public_api_export_remediation_rolls_back_on_exception(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir()
    (workspace_root / "src" / "inf_work").mkdir(parents=True)
    (workspace_root / "ai_docs" / "package_public_api_surface_20260331T000000Z.json").write_text(
        json.dumps({"interfaces": {"python_api": ["from inf_work import apply_status_artifact_remediation"]}}),
        encoding="utf-8",
    )
    init_path = workspace_root / "src" / "inf_work" / "__init__.py"
    original_text = '__all__ = []\n'
    init_path.write_text(original_text, encoding="utf-8")
    (workspace_root / "src" / "inf_work" / "remediation.py").write_text(
        "def apply_status_artifact_remediation():\n    return None\n",
        encoding="utf-8",
    )

    validation_calls = {"count": 0}

    def fake_validate_knowledge_base(workspace_root: Path, rule_ids: set[str] | None):
        validation_calls["count"] += 1
        return _kb_validation_result(
            _rule_result(
                "knowledge_base.component_doc_python_api_symbols_valid",
                passed=False,
                domain="knowledge_base",
                category="api_surface",
            ),
            compliant=False,
            workspace_root=Path(workspace_root),
        )

    original_write_text = Path.write_text
    write_calls = {"count": 0}

    def failing_write_text(self: Path, text: str, encoding: str | None = None, **kwargs):
        if self == init_path and write_calls["count"] == 0:
            write_calls["count"] += 1
            raise RuntimeError("write failed")
        return original_write_text(self, text, encoding=encoding, **kwargs)

    monkeypatch.setattr(remediation_module, "validate_knowledge_base", fake_validate_knowledge_base)
    monkeypatch.setattr(Path, "write_text", failing_write_text)

    result = remediation_module.apply_package_public_api_export_remediation(
        workspace_root,
        {"knowledge_base.component_doc_python_api_symbols_valid"},
    )

    assert result.applied is False
    assert result.rollback_performed is True
    assert init_path.read_text(encoding="utf-8") == original_text
    assert any(note.endswith("write failed") for note in result.notes)


def test_compile_remediation_plan_covers_status_and_fallback_selection(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path

    def make_plan(plan_id: str, *, available: bool, compliant: bool, strategy):
        return remediation_module.RemediationPlan(
            workspace_root=str(workspace_root.resolve()),
            plan_id=plan_id,
            objective=plan_id,
            plan_phase="phase",
            plan_only=True,
            current_status_compliant=compliant,
            plan_available=available,
            selected_rule_ids=[],
            triggering_rule_ids=[],
            unsupported_failing_rule_ids=[],
            selected_strategy=strategy,
            triggering_evidence=[],
            current_rule_summary={},
            affected_paths=[],
            operations=[],
            verification_contract=None,
            rollback_contract=None,
            provenance=remediation_module.ChangeProvenanceRecord("id", "kind", [], [], [], [], []),
            simulation_available=False,
            simulation=None,
            notes=[],
        )

    status_plan = make_plan("status", available=False, compliant=True, strategy=None)
    package_plan = make_plan("package", available=False, compliant=True, strategy=None)
    monkeypatch.setattr(remediation_module, "compile_status_artifact_remediation_plan", lambda *args, **kwargs: status_plan)
    monkeypatch.setattr(remediation_module, "compile_package_public_api_export_remediation_plan", lambda *args, **kwargs: package_plan)
    assert compile_remediation_plan(workspace_root, {"status.snapshot_matches_workspace"}).plan_id == "status"

    status_available = make_plan("status-available", available=True, compliant=False, strategy=remediation_module.STATUS_ARTIFACT_REMEDIATION_STRATEGY)
    package_available = make_plan("package-available", available=True, compliant=False, strategy=remediation_module.PACKAGE_EXPORT_SYNC_REMEDIATION_STRATEGY)
    monkeypatch.setattr(remediation_module, "compile_status_artifact_remediation_plan", lambda *args, **kwargs: status_available)
    monkeypatch.setattr(remediation_module, "compile_package_public_api_export_remediation_plan", lambda *args, **kwargs: package_available)
    assert compile_remediation_plan(workspace_root).plan_id == "status-available"

    status_noncompliant = make_plan("status-noncompliant", available=False, compliant=False, strategy=None)
    package_clean = make_plan("package-clean", available=False, compliant=True, strategy=None)
    monkeypatch.setattr(remediation_module, "compile_status_artifact_remediation_plan", lambda *args, **kwargs: status_noncompliant)
    monkeypatch.setattr(remediation_module, "compile_package_public_api_export_remediation_plan", lambda *args, **kwargs: package_clean)
    assert compile_remediation_plan(workspace_root).plan_id == "status-noncompliant"

    status_clean = make_plan("status-clean", available=False, compliant=True, strategy=None)
    package_noncompliant = make_plan("package-noncompliant", available=False, compliant=False, strategy=None)
    monkeypatch.setattr(remediation_module, "compile_status_artifact_remediation_plan", lambda *args, **kwargs: status_clean)
    monkeypatch.setattr(remediation_module, "compile_package_public_api_export_remediation_plan", lambda *args, **kwargs: package_noncompliant)
    assert compile_remediation_plan(workspace_root).plan_id == "package-noncompliant"

    monkeypatch.setattr(remediation_module, "compile_status_artifact_remediation_plan", lambda *args, **kwargs: status_clean)
    monkeypatch.setattr(remediation_module, "compile_package_public_api_export_remediation_plan", lambda *args, **kwargs: package_clean)
    assert compile_remediation_plan(workspace_root).plan_id == "status-clean"


def test_apply_remediation_plan_routes_to_package_export_strategy(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="package",
        objective="package",
        plan_phase="bounded_source_level_remediation",
        plan_only=True,
        current_status_compliant=False,
        plan_available=True,
        selected_rule_ids=["knowledge_base.component_doc_python_api_symbols_valid"],
        triggering_rule_ids=["knowledge_base.component_doc_python_api_symbols_valid"],
        unsupported_failing_rule_ids=[],
        selected_strategy=remediation_module.PACKAGE_EXPORT_SYNC_REMEDIATION_STRATEGY,
        triggering_evidence=[],
        current_rule_summary={},
        affected_paths=["src/inf_work/__init__.py"],
        operations=[],
        verification_contract=None,
        rollback_contract=None,
        provenance=remediation_module.ChangeProvenanceRecord("id", "kind", [], [], [], [], []),
        simulation_available=False,
        simulation=None,
        notes=[],
    )
    captured: dict[str, object] = {}
    monkeypatch.setattr(remediation_module, "compile_remediation_plan", lambda *args, **kwargs: plan)
    monkeypatch.setattr(
        remediation_module,
        "apply_package_public_api_export_remediation",
        lambda workspace_root, rule_ids: captured.update({"workspace_root": workspace_root, "rule_ids": rule_ids})
        or remediation_module.RemediationExecutionResult(
            workspace_root=str(Path(workspace_root).resolve()),
            plan_id="package",
            execution_phase="bounded_source_level_remediation",
            execution_attempted=True,
            plan_available=True,
            applied=True,
            compliant=True,
            rollback_performed=False,
            rollback_summary={"restored_paths": [], "deleted_paths": []},
            triggering_rule_ids=["knowledge_base.component_doc_python_api_symbols_valid"],
            unsupported_failing_rule_ids=[],
            operation_results=[],
            status_validation=None,
            summary_validation=None,
            knowledge_base_validation=None,
            notes=[],
        ),
    )

    result = apply_remediation_plan(workspace_root, {"knowledge_base.component_doc_python_api_symbols_valid"})

    assert result.compliant is True
    assert captured["workspace_root"] == workspace_root
    assert captured["rule_ids"] == {"knowledge_base.component_doc_python_api_symbols_valid"}


def test_apply_remediation_plan_covers_no_plan_status_route_and_unknown_strategy(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    base_plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="base",
        objective="base",
        plan_phase="phase",
        plan_only=True,
        current_status_compliant=True,
        plan_available=False,
        selected_rule_ids=[],
        triggering_rule_ids=[],
        unsupported_failing_rule_ids=[],
        selected_strategy=None,
        triggering_evidence=[],
        current_rule_summary={},
        affected_paths=[],
        operations=[],
        verification_contract=None,
        rollback_contract=None,
        provenance=remediation_module.ChangeProvenanceRecord("id", "kind", [], [], [], [], []),
        simulation_available=False,
        simulation=None,
        notes=["base"],
    )
    monkeypatch.setattr(remediation_module, "compile_remediation_plan", lambda *args, **kwargs: base_plan)

    no_plan_result = apply_remediation_plan(workspace_root)

    assert no_plan_result.execution_attempted is False
    assert "No supported applied remediation was executed" in no_plan_result.notes[0]

    status_plan = remediation_module.RemediationPlan(
        **{**base_plan.__dict__, "plan_available": True, "selected_strategy": remediation_module.STATUS_ARTIFACT_REMEDIATION_STRATEGY, "plan_id": "status"}
    )
    captured: dict[str, object] = {}
    monkeypatch.setattr(remediation_module, "compile_remediation_plan", lambda *args, **kwargs: status_plan)
    monkeypatch.setattr(
        remediation_module,
        "apply_status_artifact_remediation",
        lambda workspace_root, rule_ids, intent_id=None: captured.update(
            {"workspace_root": workspace_root, "rule_ids": rule_ids, "intent_id": intent_id}
        )
        or remediation_module.RemediationExecutionResult(
            workspace_root=str(Path(workspace_root).resolve()),
            plan_id="status",
            execution_phase="applied_structured_remediation",
            execution_attempted=True,
            plan_available=True,
            applied=True,
            compliant=True,
            rollback_performed=False,
            rollback_summary={"restored_paths": [], "deleted_paths": []},
            triggering_rule_ids=[],
            unsupported_failing_rule_ids=[],
            operation_results=[],
            status_validation=None,
            summary_validation=None,
            knowledge_base_validation=None,
            notes=[],
        ),
    )

    status_result = apply_remediation_plan(workspace_root, {"status.snapshot_matches_workspace"}, intent_id="intent.status.refresh_artifacts")

    assert status_result.compliant is True
    assert captured == {
        "workspace_root": workspace_root,
        "rule_ids": {"status.snapshot_matches_workspace"},
        "intent_id": "intent.status.refresh_artifacts",
    }

    unknown_strategy = remediation_module.RemediationStrategy(
        strategy_id="strategy.unknown",
        description="unknown",
        supported_rule_ids=[],
        supported_intent_ids=[],
        priority=99,
        allowed_operation_types=[],
        verification_profile="none",
        rollback_profile="none",
    )
    unknown_plan = remediation_module.RemediationPlan(
        **{**base_plan.__dict__, "plan_available": True, "selected_strategy": unknown_strategy, "plan_id": "unknown"}
    )
    monkeypatch.setattr(remediation_module, "compile_remediation_plan", lambda *args, **kwargs: unknown_plan)

    unknown_result = apply_remediation_plan(workspace_root)

    assert unknown_result.execution_attempted is False
    assert "does not yet have an execution binding" in unknown_result.notes[0]


def test_compile_remediation_plan_routes_explicit_status_intent(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    monkeypatch.setattr(
        remediation_module,
        "compile_status_artifact_remediation_plan",
        lambda workspace_root, rule_ids, include_simulation=False, intent_id=None: remediation_module.RemediationPlan(
            workspace_root=str(Path(workspace_root).resolve()),
            plan_id="status-intent",
            objective="intent",
            plan_phase="intent_driven_governed_change",
            plan_only=True,
            current_status_compliant=True,
            plan_available=True,
            selected_rule_ids=[],
            triggering_rule_ids=list(remediation_module.SUPPORTED_STATUS_ARTIFACT_TRIGGER_RULE_IDS),
            unsupported_failing_rule_ids=[],
            selected_strategy=remediation_module.STATUS_ARTIFACT_REMEDIATION_STRATEGY,
            triggering_evidence=[],
            current_rule_summary={},
            affected_paths=[],
            operations=[],
            verification_contract=None,
            rollback_contract=None,
            provenance=remediation_module.ChangeProvenanceRecord("id", "kind", [], [intent_id] if intent_id else [], [], [], []),
            simulation_available=False,
            simulation=None,
            notes=[],
        ),
    )
    monkeypatch.setattr(
        remediation_module,
        "compile_package_public_api_export_remediation_plan",
        lambda workspace_root, rule_ids, include_simulation=False: remediation_module.RemediationPlan(
            workspace_root=str(Path(workspace_root).resolve()),
            plan_id="package",
            objective="package",
            plan_phase="bounded_source_level_remediation",
            plan_only=True,
            current_status_compliant=True,
            plan_available=False,
            selected_rule_ids=[],
            triggering_rule_ids=[],
            unsupported_failing_rule_ids=[],
            selected_strategy=None,
            triggering_evidence=[],
            current_rule_summary={},
            affected_paths=[],
            operations=[],
            verification_contract=None,
            rollback_contract=None,
            provenance=remediation_module.ChangeProvenanceRecord("id", "kind", [], [], [], [], []),
            simulation_available=False,
            simulation=None,
            notes=[],
        ),
    )

    plan = compile_remediation_plan(workspace_root, intent_id="intent.status.refresh_artifacts")

    assert plan.plan_id == "status-intent"


def test_apply_status_artifact_remediation_supports_explicit_status_refresh_intent(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir()
    (workspace_root / "ai_docs" / "system_status_snapshot.json").write_text('{"stale": false}', encoding="utf-8")
    (workspace_root / "SYSTEM_STATUS.md").write_text("# current\n", encoding="utf-8")
    (workspace_root / "SYSTEM_SUMMARY.md").write_text("# current summary\n", encoding="utf-8")

    monkeypatch.setattr(
        remediation_module,
        "validate_system_status",
        lambda workspace_root, rule_ids: _status_validation_result(
            _rule_result("status.snapshot_matches_workspace", passed=True),
            _rule_result("status.summary_matches_workspace", passed=True),
            compliant=True,
        ),
    )
    monkeypatch.setattr(
        remediation_module,
        "validate_system_summary",
        lambda workspace_root: _status_validation_result(
            _rule_result("status.summary_matches_workspace", passed=True),
            compliant=True,
        ),
    )

    class FakeSnapshot:
        generated_at = "2026-04-03T22:00:00Z"
        canonical_json_path = "ai_docs/system_status_snapshot.json"
        derived_markdown_path = "SYSTEM_STATUS.md"

    monkeypatch.setattr(
        remediation_module,
        "write_system_status_outputs",
        lambda workspace_root, canonical_json_path, derived_markdown_path, summary_path: (
            (workspace_root / canonical_json_path).write_text('{"refreshed": true}', encoding="utf-8"),
            (workspace_root / derived_markdown_path).write_text("# refreshed\n", encoding="utf-8"),
            (workspace_root / summary_path).write_text("# refreshed summary\n", encoding="utf-8"),
            FakeSnapshot(),
        )[-1],
    )

    result = apply_status_artifact_remediation(workspace_root, intent_id="intent.status.refresh_artifacts")

    assert result.applied is True
    assert result.compliant is True
    assert result.rollback_performed is False