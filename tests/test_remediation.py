from __future__ import annotations

from dataclasses import dataclass
import inspect
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


def test_remediation_compile_entry_points_expose_stable_default_flags() -> None:
    status_signature = inspect.signature(remediation_module.compile_status_artifact_remediation_plan)
    package_signature = inspect.signature(remediation_module.compile_package_public_api_export_remediation_plan)
    generic_signature = inspect.signature(remediation_module.compile_remediation_plan)

    assert status_signature.parameters["include_simulation"].default is None
    assert package_signature.parameters["include_simulation"].default is None
    assert generic_signature.parameters["include_simulation"].default is None
    assert remediation_module.compile_status_artifact_remediation_plan.__kwdefaults__ == {
        "include_simulation": None,
        "intent_id": None,
    }
    assert remediation_module.compile_package_public_api_export_remediation_plan.__kwdefaults__ == {
        "include_simulation": None,
    }
    assert remediation_module.compile_remediation_plan.__kwdefaults__ == {
        "include_simulation": None,
        "intent_id": None,
    }


def test_strategy_builders_expose_exact_supported_contracts() -> None:
    status_strategy = remediation_module._build_status_artifact_strategy()
    package_strategy = remediation_module._build_package_export_sync_strategy()

    assert status_strategy.to_dict() == {
        "strategy_id": "strategy_status_artifact_regeneration_plan",
        "description": "Compile a deterministic plan that regenerates canonical status artifacts and then re-validates the status surfaces.",
        "supported_rule_ids": list(remediation_module.SUPPORTED_STATUS_ARTIFACT_TRIGGER_RULE_IDS),
        "supported_intent_ids": list(remediation_module.SUPPORTED_GOVERNED_INTENT_IDS),
        "priority": 1,
        "allowed_operation_types": ["regenerate_artifact", "run_validation_profile"],
        "verification_profile": "status_artifact_drift",
        "rollback_profile": "plan_only_noop",
    }
    assert package_strategy.to_dict() == {
        "strategy_id": "strategy_package_public_api_export_sync",
        "description": "Synchronize the governed `inf_work` package export surface in `src/inf_work/__init__.py` so documented package imports resolve to explicit re-exports.",
        "supported_rule_ids": list(remediation_module.SUPPORTED_SOURCE_LEVEL_TRIGGER_RULE_IDS),
        "supported_intent_ids": [],
        "priority": 2,
        "allowed_operation_types": ["rewrite_python_source", "run_validation_profile"],
        "verification_profile": "package_public_api_export_sync",
        "rollback_profile": "python_source_pre_state_restore",
    }


def test_operation_command_and_plan_helpers_build_exact_payloads() -> None:
    workspace_root = "/tmp/workspace"
    evidence_rule_ids = ["status.snapshot_matches_workspace", "status.summary_matches_workspace"]

    assert remediation_module._operation_command_string("python", ["-m", "inf_work", "status-check"]) == (
        "python -m inf_work status-check"
    )

    operations = remediation_module._build_plan_operations(workspace_root, evidence_rule_ids)

    assert [operation.to_dict() for operation in operations] == [
        {
            "operation_id": "regenerate_status_outputs",
            "operation_type": "regenerate_artifact",
            "target_paths": [
                "ai_docs/system_status_snapshot.json",
                "SYSTEM_STATUS.md",
                "SYSTEM_SUMMARY.md",
            ],
            "description": "Regenerate the canonical status snapshot plus both derived markdown artifacts from the governed workspace state.",
            "command": "python",
            "command_arguments": [
                "-m",
                "inf_work",
                "status",
                workspace_root,
                "--json-output",
                "ai_docs/system_status_snapshot.json",
                "--markdown-output",
                "SYSTEM_STATUS.md",
            ],
            "evidence_rule_ids": evidence_rule_ids,
            "predicted_outcome": "All governed status artifacts are regenerated from current workspace inputs.",
        },
        {
            "operation_id": "validate_status_artifacts",
            "operation_type": "run_validation_profile",
            "target_paths": [
                "ai_docs/system_status_snapshot.json",
                "SYSTEM_STATUS.md",
            ],
            "description": "Validate the canonical status snapshot and the derived status markdown after regeneration.",
            "command": "python",
            "command_arguments": ["-m", "inf_work", "status-check", workspace_root, "--pretty"],
            "evidence_rule_ids": evidence_rule_ids,
            "predicted_outcome": "The supported status drift rules pass for the canonical snapshot and status markdown.",
        },
        {
            "operation_id": "validate_system_summary",
            "operation_type": "run_validation_profile",
            "target_paths": ["SYSTEM_SUMMARY.md"],
            "description": "Validate the derived summary artifact against the current governed workspace state.",
            "command": "python",
            "command_arguments": ["-m", "inf_work", "summary-check", workspace_root, "--pretty"],
            "evidence_rule_ids": evidence_rule_ids,
            "predicted_outcome": "The derived summary artifact matches the current workspace state.",
        },
    ]


def test_verification_rollback_and_provenance_helpers_build_exact_payloads() -> None:
    workspace_root = "/tmp/workspace"
    required_rule_ids = ["status.snapshot_matches_workspace", "status.summary_matches_workspace"]

    verification_contract = remediation_module._build_verification_contract(workspace_root, required_rule_ids)
    rollback_contract = remediation_module._build_plan_only_rollback_contract()
    provenance_record = remediation_module._build_provenance_record(
        ["status.snapshot_matches_workspace"],
        ["status.summary_matches_workspace"],
        governed_intent_ids=["intent.status.refresh_artifacts"],
    )
    package_provenance = remediation_module._build_package_export_provenance_record(
        ["knowledge_base.component_doc_python_api_symbols_valid"],
        ["knowledge_base.component_doc_cli_command_valid"],
    )

    assert verification_contract.to_dict() == {
        "contract_id": "verify_status_artifact_regeneration_plan",
        "required_rule_ids": required_rule_ids,
        "commands": [
            "python -m inf_work status-check /tmp/workspace --pretty",
            "python -m inf_work summary-check /tmp/workspace --pretty",
        ],
        "success_criteria": [
            "`status-check` reports no failing status-artifact drift rules.",
            "`summary-check` reports no failing summary-drift rules.",
        ],
    }
    assert rollback_contract.to_dict() == {
        "contract_id": "rollback_plan_only_noop",
        "strategy": "no_workspace_mutation",
        "steps": [
            "No rollback action is required during phase-1 planning because the workflow compiles a plan without mutating workspace files.",
            "If an operator executes the plan manually, re-run the same governed regeneration command from version-controlled sources to restore deterministic artifacts.",
        ],
    }
    assert provenance_record.to_dict() == {
        "record_id": "provenance_status_artifact_regeneration_plan",
        "trigger_kind": "explicit_governed_intent",
        "trigger_rule_ids": ["status.snapshot_matches_workspace"],
        "governed_intent_ids": ["intent.status.refresh_artifacts"],
        "supporting_rule_ids": ["status.summary_matches_workspace"],
        "source_artifact_paths": [
            "ai_docs/system_status_snapshot.json",
            "SYSTEM_STATUS.md",
            "SYSTEM_SUMMARY.md",
        ],
        "derived_from_components": [
            "system_status_generator",
            "unified_cli_entry_point",
            "remediation_plan_compiler",
        ],
    }
    assert package_provenance.to_dict() == {
        "record_id": "provenance_package_public_api_export_sync",
        "trigger_kind": "knowledge_base_rule_failure",
        "trigger_rule_ids": ["knowledge_base.component_doc_python_api_symbols_valid"],
        "governed_intent_ids": [],
        "supporting_rule_ids": ["knowledge_base.component_doc_cli_command_valid"],
        "source_artifact_paths": [
            "ai_docs/package_public_api_surface_20260331T000000Z.json",
            "src/inf_work/__init__.py",
        ],
        "derived_from_components": [
            "package_public_api_surface",
            "remediation_plan_compiler",
            "unified_cli_entry_point",
        ],
    }


def test_build_provenance_record_uses_status_rule_failure_without_governed_intent() -> None:
    provenance_record = remediation_module._build_provenance_record(
        ["status.snapshot_matches_workspace"],
        ["status.artifacts_exist"],
    )

    assert provenance_record.to_dict()["trigger_kind"] == "status_rule_failure"


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
    assert payload["workspace_root"] == str(WORKSPACE_ROOT.resolve())
    assert payload["objective"] == (
        "Regenerate stale governed status artifacts and verify that the current workspace state is reflected across the canonical snapshot and derived markdown outputs."
    )
    assert payload["plan_phase"] == "plan_only_structured_remediation"
    assert payload["plan_only"] is True
    assert payload["selected_rule_ids"] == ["status.snapshot_matches_workspace"]
    assert payload["selected_strategy"]["strategy_id"] == "strategy_status_artifact_regeneration_plan"
    assert payload["triggering_evidence"] == [
        _rule_result("status.snapshot_matches_workspace", passed=False).to_dict(),
        _rule_result("status.summary_matches_workspace", passed=False).to_dict(),
    ]
    assert payload["triggering_rule_ids"] == [
        "status.snapshot_matches_workspace",
        "status.summary_matches_workspace",
    ]
    assert payload["current_rule_summary"] == remediation_module.summarize_rule_results(
        [
            _rule_result("status.snapshot_matches_workspace", passed=False),
            _rule_result("status.summary_matches_workspace", passed=False),
            _rule_result("status.artifacts_exist", passed=False),
        ]
    )
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
    assert payload["verification_contract"]["commands"] == [
        f"python -m inf_work status-check {WORKSPACE_ROOT.resolve()} --pretty",
        f"python -m inf_work summary-check {WORKSPACE_ROOT.resolve()} --pretty",
    ]
    assert payload["rollback_contract"] == {
        "contract_id": "rollback_plan_only_noop",
        "strategy": "no_workspace_mutation",
        "steps": [
            "No rollback action is required during phase-1 planning because the workflow compiles a plan without mutating workspace files.",
            "If an operator executes the plan manually, re-run the same governed regeneration command from version-controlled sources to restore deterministic artifacts.",
        ],
    }
    assert payload["provenance"]["derived_from_components"] == [
        "system_status_generator",
        "unified_cli_entry_point",
        "remediation_plan_compiler",
    ]
    assert payload["provenance"]["trigger_rule_ids"] == [
        "status.snapshot_matches_workspace",
        "status.summary_matches_workspace",
    ]
    assert payload["provenance"]["supporting_rule_ids"] == ["status.artifacts_exist"]
    assert payload["notes"] == [
        "The remediation compiler remains non-mutating and bounded to governed status artifacts.",
        "Enable dry-run simulation to preview deterministic post-state diffs before any manual operator action.",
        "Explicit governed intent currently supports deterministic status-artifact refresh without requiring an active failure.",
        "The current slice intentionally excludes arbitrary source edits and dependency changes.",
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
    payload = plan.to_dict()

    assert plan.plan_available is False
    assert plan.current_status_compliant is True
    assert plan.selected_strategy is None
    assert plan.operations == []
    assert plan.triggering_rule_ids == []
    assert payload["workspace_root"] == str(WORKSPACE_ROOT.resolve())
    assert payload["plan_id"] == "remediation_plan_status_artifact_regeneration"
    assert payload["objective"] == "Determine whether the bounded status-artifact remediation slice should compile a deterministic plan."
    assert payload["plan_phase"] == "plan_only_structured_remediation"
    assert payload["plan_only"] is True
    assert payload["affected_paths"] == [
        "ai_docs/system_status_snapshot.json",
        "SYSTEM_STATUS.md",
        "SYSTEM_SUMMARY.md",
    ]
    assert payload["verification_contract"] is None
    assert payload["current_rule_summary"] == remediation_module.summarize_rule_results(
        [
            _rule_result("status.snapshot_matches_workspace", passed=True),
            _rule_result("status.markdown_matches_snapshot", passed=True),
            _rule_result("status.summary_matches_workspace", passed=True),
        ]
    )
    assert payload["rollback_contract"]["contract_id"] == "rollback_plan_only_noop"
    assert payload["provenance"]["trigger_rule_ids"] == []
    assert payload["provenance"]["supporting_rule_ids"] == []
    assert payload["notes"] == [
        "No supported phase-1 status-artifact drift failures are active, so no remediation plan is compiled.",
        "The canonical status artifacts already match the current governed workspace state.",
    ]
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

    payload = plan.to_dict()

    assert plan.plan_available is True
    assert plan.plan_phase == "intent_driven_governed_change"
    assert plan.provenance.governed_intent_ids == ["intent.status.refresh_artifacts"]
    assert plan.triggering_rule_ids == list(remediation_module.SUPPORTED_STATUS_ARTIFACT_TRIGGER_RULE_IDS)
    assert plan.selected_strategy is not None
    assert payload["objective"] == (
        "Refresh the governed status artifacts on explicit operator intent and verify that the canonical snapshot plus derived markdown outputs still match the current workspace state."
    )
    assert payload["triggering_evidence"] == []
    assert payload["provenance"]["trigger_kind"] == "explicit_governed_intent"
    assert payload["provenance"]["trigger_rule_ids"] == list(remediation_module.SUPPORTED_STATUS_ARTIFACT_TRIGGER_RULE_IDS)
    assert payload["provenance"]["supporting_rule_ids"] == []
    assert payload["provenance"]["governed_intent_ids"] == ["intent.status.refresh_artifacts"]


def test_compile_status_artifact_remediation_plan_handles_markdown_only_drift(monkeypatch) -> None:
    monkeypatch.setattr(
        remediation_module,
        "validate_system_status",
        lambda workspace_root, rule_ids: _status_validation_result(
            _rule_result("status.markdown_matches_snapshot", passed=False),
            compliant=False,
        ),
    )

    plan = compile_status_artifact_remediation_plan(WORKSPACE_ROOT)
    payload = plan.to_dict()

    assert plan.plan_available is True
    assert plan.current_status_compliant is False
    assert plan.triggering_rule_ids == ["status.markdown_matches_snapshot"]
    assert payload["triggering_evidence"] == [
        _rule_result("status.markdown_matches_snapshot", passed=False).to_dict()
    ]
    assert payload["unsupported_failing_rule_ids"] == []
    assert payload["verification_contract"]["required_rule_ids"] == ["status.markdown_matches_snapshot"]
    assert payload["current_rule_summary"] == remediation_module.summarize_rule_results(
        [_rule_result("status.markdown_matches_snapshot", passed=False)]
    )


def test_compile_status_artifact_remediation_plan_supports_explicit_status_refresh_intent_dry_run(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir()
    (workspace_root / "knowledge_base").mkdir()
    (workspace_root / "ai_docs" / "system_status_snapshot.json").write_text('{"current": true}', encoding="utf-8")
    (workspace_root / "SYSTEM_STATUS.md").write_text("# current\n", encoding="utf-8")
    (workspace_root / "SYSTEM_SUMMARY.md").write_text("# current summary\n", encoding="utf-8")
    (workspace_root / "ai_docs" / "component_index.json").write_text('{"components": [], "metadata": {}}', encoding="utf-8")
    (workspace_root / "knowledge_base" / "kb_index.json").write_text(
        '{"total_techniques": 10, "total_bug_fixes": 1, "total_innovations": 2, "total_automation_patterns": 60}',
        encoding="utf-8",
    )

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

    class FakeSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {
                "generated_at": "2026-04-07T00:00:00Z",
                "workspace_root": str(workspace_root.resolve()),
                "canonical_json_path": "ai_docs/system_status_snapshot.json",
                "derived_markdown_path": "SYSTEM_STATUS.md",
            }

    monkeypatch.setattr(remediation_module, "build_system_status_snapshot", lambda *args, **kwargs: FakeSnapshot())
    monkeypatch.setattr(remediation_module, "render_system_status_markdown", lambda snapshot: "# System Status\n\nrefreshed\n")
    monkeypatch.setattr(
        remediation_module,
        "render_system_summary_markdown",
        lambda snapshot, component_index, kb_index: "# System Summary\n\nrefreshed\n",
    )

    plan = compile_status_artifact_remediation_plan(
        workspace_root,
        include_simulation=True,
        intent_id="intent.status.refresh_artifacts",
    )
    payload = plan.to_dict()

    assert plan.plan_available is True
    assert payload["plan_phase"] == "intent_driven_governed_change"
    assert payload["plan_only"] is False
    assert payload["triggering_rule_ids"] == list(remediation_module.SUPPORTED_STATUS_ARTIFACT_TRIGGER_RULE_IDS)
    assert payload["provenance"]["governed_intent_ids"] == ["intent.status.refresh_artifacts"]
    assert payload["simulation_available"] is True
    assert payload["simulation"] is not None
    assert payload["simulation"]["simulation_phase"] == "dry_run_structured_remediation"
    assert payload["simulation"]["workspace_mutation"] is False



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
    payload = plan.to_dict()

    assert plan.plan_available is False
    assert plan.current_status_compliant is False
    assert payload["workspace_root"] == str(WORKSPACE_ROOT.resolve())
    assert payload["plan_id"] == "remediation_plan_status_artifact_regeneration"
    assert payload["objective"] == "Determine whether the bounded status-artifact remediation slice should compile a deterministic plan."
    assert payload["plan_phase"] == "plan_only_structured_remediation"
    assert payload["plan_only"] is True
    assert payload["selected_rule_ids"] == []
    assert payload["triggering_rule_ids"] == []
    assert payload["triggering_evidence"] == []
    assert payload["simulation_available"] is False
    assert payload["simulation"] is None
    assert plan.unsupported_failing_rule_ids == ["status.artifacts_exist"]
    assert payload["current_rule_summary"] == remediation_module.summarize_rule_results(
        [_rule_result("status.artifacts_exist", passed=False)]
    )
    assert plan.rollback_contract is not None
    assert payload["provenance"]["supporting_rule_ids"] == ["status.artifacts_exist"]
    assert payload["notes"] == [
        "No supported phase-1 status-artifact drift failures are active, so no remediation plan is compiled.",
        "Failing rules remain outside the supported phase-1 remediation slice and must be handled by existing validator-specific workflows.",
    ]
    assert "outside the supported phase-1 remediation slice" in plan.notes[-1]


def test_compile_status_artifact_remediation_plan_no_plan_honors_dry_run_phase(monkeypatch) -> None:
    unsupported_rule = _rule_result("status.artifacts_exist", passed=False)
    monkeypatch.setattr(
        remediation_module,
        "validate_system_status",
        lambda workspace_root, rule_ids: _status_validation_result(
            unsupported_rule,
            compliant=False,
        ),
    )

    plan = compile_status_artifact_remediation_plan(WORKSPACE_ROOT, include_simulation=True)
    payload = plan.to_dict()

    assert plan.plan_available is False
    assert payload["plan_phase"] == "dry_run_structured_remediation"
    assert payload["plan_only"] is False
    assert payload["current_rule_summary"] == remediation_module.summarize_rule_results([unsupported_rule])
    assert payload["provenance"]["trigger_rule_ids"] == []
    assert payload["provenance"]["supporting_rule_ids"] == ["status.artifacts_exist"]
    assert payload["simulation_available"] is False
    assert payload["simulation"] is None


def test_compile_status_artifact_remediation_plan_defaults_to_nonsimulated_plan(monkeypatch) -> None:
    failing_rules = [
        _rule_result("status.snapshot_matches_workspace", passed=False),
        _rule_result("status.summary_matches_workspace", passed=False),
    ]
    monkeypatch.setattr(
        remediation_module,
        "validate_system_status",
        lambda workspace_root, rule_ids: _status_validation_result(*failing_rules, compliant=False),
    )

    plan = compile_status_artifact_remediation_plan(WORKSPACE_ROOT)
    payload = plan.to_dict()

    assert payload["plan_phase"] == "plan_only_structured_remediation"
    assert payload["plan_only"] is True
    assert payload["simulation_available"] is False
    assert payload["simulation"] is None
    assert payload["current_rule_summary"] == remediation_module.summarize_rule_results(failing_rules)


def test_compile_status_artifact_remediation_plan_passes_workspace_root_to_operation_builder(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    captured: dict[str, object] = {}
    failing_rules = [
        _rule_result("status.snapshot_matches_workspace", passed=False),
        _rule_result("status.summary_matches_workspace", passed=False),
    ]

    monkeypatch.setattr(
        remediation_module,
        "validate_system_status",
        lambda workspace_root, rule_ids: _status_validation_result(*failing_rules, compliant=False),
    )
    monkeypatch.setattr(
        remediation_module,
        "_build_plan_operations",
        lambda workspace_root, evidence_rule_ids: captured.update(
            {
                "workspace_root": workspace_root,
                "evidence_rule_ids": evidence_rule_ids,
            }
        ) or [],
    )

    plan = compile_status_artifact_remediation_plan(workspace_root)

    assert plan.plan_available is True
    assert captured == {
        "workspace_root": str(workspace_root.resolve()),
        "evidence_rule_ids": [
            "status.snapshot_matches_workspace",
            "status.summary_matches_workspace",
        ],
    }


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
    payload = result.to_dict()

    assert result.execution_attempted is True
    assert result.applied is True
    assert result.compliant is True
    assert result.rollback_performed is False
    assert len(result.operation_results) == 3
    assert payload["plan_id"] == "remediation_plan_status_artifact_regeneration"
    assert payload["workspace_root"] == str(workspace_root.resolve())
    assert payload["execution_phase"] == "applied_structured_remediation"
    assert payload["plan_available"] is True
    assert payload["triggering_rule_ids"] == [
        "status.snapshot_matches_workspace",
        "status.summary_matches_workspace",
    ]
    assert payload["unsupported_failing_rule_ids"] == []
    assert payload["rollback_summary"] == {"restored_paths": [], "deleted_paths": []}
    assert payload["operation_results"] == [
        {
            "operation_id": "regenerate_status_outputs",
            "operation_type": "regenerate_artifact",
            "target_paths": [
                "ai_docs/system_status_snapshot.json",
                "SYSTEM_STATUS.md",
                "SYSTEM_SUMMARY.md",
            ],
            "status": "completed",
            "mutation_performed": True,
            "details": {
                "generated_at": "2026-04-03T21:00:00Z",
                "canonical_json_path": "ai_docs/system_status_snapshot.json",
                "derived_markdown_path": "SYSTEM_STATUS.md",
            },
        },
        {
            "operation_id": "validate_status_artifacts",
            "operation_type": "run_validation_profile",
            "target_paths": ["ai_docs/system_status_snapshot.json", "SYSTEM_STATUS.md"],
            "status": "completed",
            "mutation_performed": False,
            "details": {
                "compliant": True,
                "issue_count": 0,
                "rule_summary": remediation_module.summarize_rule_results(
                    [
                        _rule_result("status.snapshot_matches_workspace", passed=True),
                        _rule_result("status.summary_matches_workspace", passed=True),
                    ]
                ),
            },
        },
        {
            "operation_id": "validate_system_summary",
            "operation_type": "run_validation_profile",
            "target_paths": ["SYSTEM_SUMMARY.md"],
            "status": "completed",
            "mutation_performed": False,
            "details": {
                "compliant": True,
                "issue_count": 0,
                "rule_summary": remediation_module.summarize_rule_results(
                    [_rule_result("status.summary_matches_workspace", passed=True)]
                ),
            },
        },
    ]
    assert payload["status_validation"] == _status_validation_result(
        _rule_result("status.snapshot_matches_workspace", passed=True),
        _rule_result("status.summary_matches_workspace", passed=True),
        compliant=True,
    ).to_dict()
    assert payload["summary_validation"] == _status_validation_result(
        _rule_result("status.summary_matches_workspace", passed=True),
        compliant=True,
    ).to_dict()
    assert payload["knowledge_base_validation"] is None
    assert payload["notes"] == [
        "Applied remediation completed successfully for the bounded status-artifact slice.",
        "Verification passed without requiring rollback.",
    ]
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
    payload = result.to_dict()

    assert result.execution_attempted is True
    assert result.applied is False
    assert result.compliant is False
    assert result.rollback_performed is True
    assert payload["workspace_root"] == str(workspace_root.resolve())
    assert payload["plan_id"] == "remediation_plan_status_artifact_regeneration"
    assert payload["execution_phase"] == "applied_structured_remediation"
    assert payload["plan_available"] is True
    assert result.rollback_summary["restored_paths"] == [
        "SYSTEM_STATUS.md",
        "SYSTEM_SUMMARY.md",
        "ai_docs/system_status_snapshot.json",
    ]
    assert (workspace_root / "ai_docs" / "system_status_snapshot.json").read_text(encoding="utf-8") == original_snapshot
    assert (workspace_root / "SYSTEM_STATUS.md").read_text(encoding="utf-8") == original_status
    assert (workspace_root / "SYSTEM_SUMMARY.md").read_text(encoding="utf-8") == original_summary
    assert payload["operation_results"][0]["status"] == "completed"
    assert payload["operation_results"][1]["status"] == "failed"
    assert payload["operation_results"][1]["details"]["compliant"] is False
    assert payload["operation_results"][2]["status"] == "completed"
    assert payload["triggering_rule_ids"] == ["status.snapshot_matches_workspace"]
    assert payload["unsupported_failing_rule_ids"] == []
    assert payload["status_validation"] == _status_validation_result(
        _rule_result("status.snapshot_matches_workspace", passed=False),
        compliant=False,
    ).to_dict()
    assert payload["summary_validation"] == _status_validation_result(
        _rule_result("status.summary_matches_workspace", passed=True),
        compliant=True,
    ).to_dict()
    assert payload["notes"] == [
        "Applied remediation failed verification and the bounded rollback contract restored the pre-remediation artifact state.",
    ]


def test_apply_status_artifact_remediation_deletes_newly_created_artifacts_on_failed_verification(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir()

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

    monkeypatch.setattr(remediation_module, "validate_system_status", fake_validate_system_status)
    monkeypatch.setattr(
        remediation_module,
        "validate_system_summary",
        lambda workspace_root: _status_validation_result(
            _rule_result("status.summary_matches_workspace", passed=True),
            compliant=True,
        ),
    )

    class FakeSnapshot:
        generated_at = "2026-04-07T00:30:00Z"
        canonical_json_path = "ai_docs/system_status_snapshot.json"
        derived_markdown_path = "SYSTEM_STATUS.md"

    def fake_write_system_status_outputs(
        workspace_root: Path,
        canonical_json_path: str,
        derived_markdown_path: str,
        summary_path: str,
    ) -> FakeSnapshot:
        (workspace_root / canonical_json_path).write_text('{"created": true}', encoding="utf-8")
        (workspace_root / derived_markdown_path).write_text("# created status\n", encoding="utf-8")
        (workspace_root / summary_path).write_text("# created summary\n", encoding="utf-8")
        return FakeSnapshot()

    monkeypatch.setattr(remediation_module, "write_system_status_outputs", fake_write_system_status_outputs)

    result = apply_status_artifact_remediation(workspace_root)
    payload = result.to_dict()

    assert result.applied is False
    assert result.rollback_performed is True
    assert payload["rollback_summary"] == {
        "restored_paths": [],
        "deleted_paths": [
            "SYSTEM_STATUS.md",
            "SYSTEM_SUMMARY.md",
            "ai_docs/system_status_snapshot.json",
        ],
    }
    assert not (workspace_root / "ai_docs" / "system_status_snapshot.json").exists()
    assert not (workspace_root / "SYSTEM_STATUS.md").exists()
    assert not (workspace_root / "SYSTEM_SUMMARY.md").exists()
    assert payload["operation_results"][1]["status"] == "failed"
    assert payload["operation_results"][2]["status"] == "completed"


def test_apply_status_artifact_remediation_marks_summary_validation_failure_explicitly(monkeypatch, tmp_path: Path) -> None:
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
            _rule_result("status.snapshot_matches_workspace", passed=True),
            compliant=True,
        )

    def fake_validate_system_summary(workspace_root: Path) -> StatusValidationResult:
        return _status_validation_result(
            _rule_result("status.summary_matches_workspace", passed=False),
            compliant=False,
        )

    class FakeSnapshot:
        generated_at = "2026-04-03T21:40:00Z"
        canonical_json_path = "ai_docs/system_status_snapshot.json"
        derived_markdown_path = "SYSTEM_STATUS.md"

    def fake_write_system_status_outputs(
        workspace_root: Path,
        canonical_json_path: str,
        derived_markdown_path: str,
        summary_path: str,
    ) -> FakeSnapshot:
        (workspace_root / canonical_json_path).write_text('{"status": "broken-summary"}', encoding="utf-8")
        (workspace_root / derived_markdown_path).write_text("# broken status\n", encoding="utf-8")
        (workspace_root / summary_path).write_text("# broken summary\n", encoding="utf-8")
        return FakeSnapshot()

    monkeypatch.setattr(remediation_module, "validate_system_status", fake_validate_system_status)
    monkeypatch.setattr(remediation_module, "validate_system_summary", fake_validate_system_summary)
    monkeypatch.setattr(remediation_module, "write_system_status_outputs", fake_write_system_status_outputs)

    result = apply_status_artifact_remediation(workspace_root)
    payload = result.to_dict()

    assert result.applied is False
    assert result.rollback_performed is True
    assert payload["operation_results"][2]["status"] == "failed"
    assert payload["operation_results"][2]["mutation_performed"] is False
    assert payload["operation_results"][2]["details"] == {
        "compliant": False,
        "issue_count": 0,
        "rule_summary": remediation_module.summarize_rule_results(
            [_rule_result("status.summary_matches_workspace", passed=False)]
        ),
    }
    assert payload["summary_validation"] == _status_validation_result(
        _rule_result("status.summary_matches_workspace", passed=False),
        compliant=False,
    ).to_dict()
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


def test_line_preview_uses_exact_default_limit_of_twelve_lines() -> None:
    text = "\n".join(f"line-{index}" for index in range(15))

    preview = remediation_module._line_preview(text)

    assert preview == [f"line-{index}" for index in range(12)]


def test_package_export_plan_and_contract_helpers_build_exact_payloads() -> None:
    operations = remediation_module._build_package_export_plan_operations(
        "/tmp/workspace",
        ["knowledge_base.component_doc_python_api_symbols_valid"],
    )
    verification_contract = remediation_module._build_package_export_verification_contract(
        "/tmp/workspace",
        ["knowledge_base.component_doc_python_api_symbols_valid"],
    )
    rollback_contract = remediation_module._build_python_source_rollback_contract()

    assert [operation.to_dict() for operation in operations] == [
        {
            "operation_id": "sync_package_public_api_exports",
            "operation_type": "rewrite_python_source",
            "target_paths": ["src/inf_work/__init__.py"],
            "description": "Synchronize the governed `inf_work` package export surface so documented package imports resolve to explicit imports plus `__all__` entries.",
            "command": "python",
            "command_arguments": [
                "-m",
                "inf_work",
                "remediation-plan",
                "/tmp/workspace",
                "--pretty",
                "--apply",
                "--rule-id",
                "knowledge_base.component_doc_python_api_symbols_valid",
            ],
            "evidence_rule_ids": ["knowledge_base.component_doc_python_api_symbols_valid"],
            "predicted_outcome": "The governed package public API documentation matches the explicit `inf_work` re-export surface.",
        },
        {
            "operation_id": "validate_package_public_api_exports",
            "operation_type": "run_validation_profile",
            "target_paths": [
                "ai_docs/package_public_api_surface_20260331T000000Z.json",
                "src/inf_work/__init__.py",
            ],
            "description": "Validate the package-public-API symbol references against the governed module export surface after synchronization.",
            "command": "python",
            "command_arguments": [
                "-m",
                "inf_work",
                "kb",
                "/tmp/workspace",
                "--pretty",
                "--rule-id",
                "knowledge_base.component_doc_python_api_symbols_valid",
            ],
            "evidence_rule_ids": ["knowledge_base.component_doc_python_api_symbols_valid"],
            "predicted_outcome": "The package-public-API doc references only symbols exported by `src/inf_work/__init__.py`.",
        },
    ]
    assert verification_contract.to_dict() == {
        "contract_id": "verify_package_public_api_export_sync",
        "required_rule_ids": ["knowledge_base.component_doc_python_api_symbols_valid"],
        "commands": [
            "python -m inf_work kb /tmp/workspace --pretty --rule-id knowledge_base.component_doc_python_api_symbols_valid",
        ],
        "success_criteria": [
            "`kb --rule-id knowledge_base.component_doc_python_api_symbols_valid` reports no missing `inf_work` package exports.",
        ],
    }
    assert rollback_contract.to_dict() == {
        "contract_id": "rollback_python_source_pre_state_restore",
        "strategy": "restore_pre_state_file_contents",
        "steps": [
            "Capture the full pre-remediation contents of the targeted Python source file before mutation.",
            "If verification fails, restore the exact pre-state file contents and rerun the targeted validator.",
        ],
    }


def test_operation_and_no_plan_execution_result_helpers_build_exact_payloads() -> None:
    plan = remediation_module.RemediationPlan(
        workspace_root="/tmp/workspace",
        plan_id="plan-id",
        objective="objective",
        plan_phase="phase",
        plan_only=False,
        current_status_compliant=False,
        plan_available=False,
        selected_rule_ids=["status.snapshot_matches_workspace"],
        triggering_rule_ids=["status.snapshot_matches_workspace"],
        unsupported_failing_rule_ids=["status.artifacts_exist"],
        selected_strategy=None,
        triggering_evidence=[],
        current_rule_summary={"failed_rules": 1},
        affected_paths=["SYSTEM_STATUS.md"],
        operations=[],
        verification_contract=None,
        rollback_contract=None,
        provenance=remediation_module._build_provenance_record(["status.snapshot_matches_workspace"], []),
        simulation_available=False,
        simulation=None,
        notes=["original note"],
    )
    operation = remediation_module.PlanOperation(
        operation_id="op-id",
        operation_type="run_validation_profile",
        target_paths=["SYSTEM_STATUS.md"],
        description="desc",
        command="python",
        command_arguments=["-m", "inf_work", "status-check"],
        evidence_rule_ids=["status.snapshot_matches_workspace"],
        predicted_outcome="outcome",
    )

    operation_result = remediation_module._build_operation_execution_result(
        operation,
        status="completed",
        mutation_performed=False,
        details={"checked": True},
    )
    no_plan_result = remediation_module._build_no_plan_execution_result(plan, notes=["no plan note"])

    assert operation_result.to_dict() == {
        "operation_id": "op-id",
        "operation_type": "run_validation_profile",
        "target_paths": ["SYSTEM_STATUS.md"],
        "status": "completed",
        "mutation_performed": False,
        "details": {"checked": True},
    }
    assert no_plan_result.to_dict() == {
        "workspace_root": "/tmp/workspace",
        "plan_id": "plan-id",
        "execution_phase": "applied_structured_remediation",
        "execution_attempted": False,
        "plan_available": False,
        "applied": False,
        "compliant": False,
        "rollback_performed": False,
        "rollback_summary": {"restored_paths": [], "deleted_paths": []},
        "triggering_rule_ids": ["status.snapshot_matches_workspace"],
        "unsupported_failing_rule_ids": ["status.artifacts_exist"],
        "operation_results": [],
        "status_validation": None,
        "summary_validation": None,
        "knowledge_base_validation": None,
        "notes": ["no plan note"],
    }


def test_read_optional_text_reads_existing_files_with_utf8(monkeypatch, tmp_path: Path) -> None:
    target_path = tmp_path / "artifact.txt"
    target_path.write_text("hello\n", encoding="utf-8")
    original_read_text = Path.read_text
    captured: list[str | None] = []

    def capturing_read_text(self: Path, encoding: str | None = None, **kwargs):
        if self == target_path:
            captured.append(encoding)
        return original_read_text(self, encoding=encoding, **kwargs)

    monkeypatch.setattr(Path, "read_text", capturing_read_text)

    assert remediation_module._read_optional_text(target_path) == "hello\n"
    assert captured == ["utf-8"]


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


def test_extract_module_export_surface_ignores_invalid_all_and_continues_collecting_exports(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "VALUE = 1\n"
        "__all__ = UNKNOWN_SYMBOL\n"
        "def exported_function():\n"
        "    return VALUE\n",
        encoding="utf-8",
    )

    exported_names, explicit_all = remediation_module._extract_module_export_surface(module_path)

    assert exported_names == {"VALUE", "exported_function"}
    assert explicit_all is None


def test_extract_module_export_surface_rejects_mixed_type_all_literals(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "VALUE = 1\n"
        "__all__ = [\"valid_symbol\", 2]\n",
        encoding="utf-8",
    )

    exported_names, explicit_all = remediation_module._extract_module_export_surface(module_path)

    assert exported_names == {"VALUE"}
    assert explicit_all is None


def test_extract_module_export_surface_uses_module_filename_for_syntax_errors(tmp_path: Path) -> None:
    module_path = tmp_path / "broken_module.py"
    module_path.write_text("def broken(:\n    pass\n", encoding="utf-8")

    try:
        remediation_module._extract_module_export_surface(module_path)
    except SyntaxError as exc:
        assert exc.filename == str(module_path)
    else:
        raise AssertionError("Expected SyntaxError for malformed module source.")


def test_extract_module_export_surface_uses_last_segment_for_plain_imports(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "import pkg.submodule\n"
        "from pkg import nested\n",
        encoding="utf-8",
    )

    exported_names, explicit_all = remediation_module._extract_module_export_surface(module_path)

    assert exported_names == {"submodule", "nested"}
    assert explicit_all is None


def test_group_missing_symbols_by_provider_skips_package_init_exports(tmp_path: Path) -> None:
    package_root = tmp_path / "src" / "inf_work"
    package_root.mkdir(parents=True)
    (package_root / "__init__.py").write_text("def init_only_symbol():\n    return 1\n", encoding="utf-8")
    (package_root / "alpha.py").write_text("def alpha_symbol():\n    return 1\n", encoding="utf-8")

    module_to_symbols, unsupported_symbols = remediation_module._group_missing_symbols_by_provider(
        tmp_path,
        ["alpha_symbol", "init_only_symbol"],
    )

    assert module_to_symbols == {"alpha": ["alpha_symbol"]}
    assert unsupported_symbols == ["init_only_symbol"]


def test_serialize_snapshot_and_artifact_change_helpers_build_exact_payloads(tmp_path: Path) -> None:
    class FakeSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {"generated_at": "2026-04-04T00:00:00Z", "healthy": True}

    existing_path = tmp_path / "artifact.txt"
    existing_path.write_text("old\n", encoding="utf-8")

    assert remediation_module._serialize_snapshot(FakeSnapshot()) == json.dumps(
        {"generated_at": "2026-04-04T00:00:00Z", "healthy": True},
        indent=2,
    )
    assert remediation_module._build_artifact_change(tmp_path, "artifact.txt", "new\n") == {
        "target_path": "artifact.txt",
        "change_type": "update",
        "current_exists": True,
        "simulated_exists": True,
        "content_changed": True,
        "current_sha256": remediation_module._sha256_text("old\n"),
        "simulated_sha256": remediation_module._sha256_text("new\n"),
        "current_line_count": 1,
        "simulated_line_count": 1,
        "current_excerpt": ["old"],
        "simulated_excerpt": ["new"],
        "diff_line_count": 5,
        "diff_preview": [
            "--- a/artifact.txt",
            "+++ b/artifact.txt",
            "@@ -1 +1 @@",
            "-old",
            "+new",
        ],
        "diff_truncated": False,
    }


def test_predicted_rule_outcomes_helper_builds_exact_summary() -> None:
    predicted_rule_outcomes, predicted_rule_summary = remediation_module._build_predicted_rule_outcomes(
        [
            _rule_result("status.summary_matches_workspace", passed=False),
            _rule_result("status.resolver_explicit_route_integrity", passed=True),
        ]
    )

    assert predicted_rule_outcomes == [
        {
            "rule_id": "status.resolver_explicit_route_integrity",
            "current_passed": True,
            "predicted_passed": True,
            "predicted_effect": "unchanged",
            "rationale": "Dry-run simulation does not alter this rule surface, so the current result is preserved.",
        },
        {
            "rule_id": "status.summary_matches_workspace",
            "current_passed": False,
            "predicted_passed": True,
            "predicted_effect": "would_pass",
            "rationale": "Simulated regeneration restores canonical artifact presence and content for this rule.",
        },
    ]
    assert predicted_rule_summary == {
        "total_rules": 2,
        "passed_rules": 2,
        "failed_rules": 0,
        "total_findings": 0,
        "by_domain": {"status": {"rules": 2, "failed_rules": 0, "findings": 0}},
        "by_category": {"artifact_integrity": {"rules": 2, "failed_rules": 0, "findings": 0}},
        "by_severity": {"error": {"rules": 2, "failed_rules": 0, "findings": 0}},
    }


def test_predicted_rule_outcomes_helper_preserves_rule_ids_and_descriptions_for_all_supported_rules() -> None:
    predicted_rule_outcomes, predicted_rule_summary = remediation_module._build_predicted_rule_outcomes(
        [
            _rule_result("status.artifacts_exist", passed=False),
            _rule_result("status.summary_matches_workspace", passed=False),
        ]
    )

    assert predicted_rule_outcomes == [
        {
            "rule_id": "status.artifacts_exist",
            "current_passed": False,
            "predicted_passed": True,
            "predicted_effect": "would_pass",
            "rationale": "Simulated regeneration restores canonical artifact presence and content for this rule.",
        },
        {
            "rule_id": "status.summary_matches_workspace",
            "current_passed": False,
            "predicted_passed": True,
            "predicted_effect": "would_pass",
            "rationale": "Simulated regeneration restores canonical artifact presence and content for this rule.",
        },
    ]
    assert predicted_rule_summary["failed_rules"] == 0


def test_predicted_rule_outcomes_passes_rule_ids_and_descriptions_into_summary(monkeypatch) -> None:
    captured: dict[str, object] = {}
    rule = RuleResult(
        rule_id="status.artifacts_exist",
        domain="status",
        category="artifact_integrity",
        severity="error",
        description="artifact presence",
        passed=False,
        findings=[
            RuleFinding(
                message="missing",
                source_file="SYSTEM_STATUS.md",
                item_identifier="artifact",
                field_name="presence",
            )
        ],
    )

    def fake_summarize_rule_results(rule_results):
        captured["rule_results"] = [
            {
                "rule_id": item.rule_id,
                "description": item.description,
                "passed": item.passed,
            }
            for item in rule_results
        ]
        return {"captured": True}

    monkeypatch.setattr(remediation_module, "summarize_rule_results", fake_summarize_rule_results)

    predicted_rule_outcomes, predicted_rule_summary = remediation_module._build_predicted_rule_outcomes([rule])

    assert predicted_rule_outcomes[0]["rule_id"] == "status.artifacts_exist"
    assert predicted_rule_summary == {"captured": True}
    assert captured["rule_results"] == [
        {
            "rule_id": "status.artifacts_exist",
            "description": "artifact presence",
            "passed": True,
        }
    ]


def test_build_dry_run_simulation_builds_exact_payload_shape(monkeypatch, tmp_path: Path) -> None:
    root_path = tmp_path
    (root_path / "ai_docs").mkdir()
    (root_path / "knowledge_base").mkdir()
    (root_path / "ai_docs" / "component_index.json").write_text('{"components": [], "metadata": {}}', encoding="utf-8")
    (root_path / "knowledge_base" / "kb_index.json").write_text('{"total_techniques": 10}', encoding="utf-8")
    (root_path / "ai_docs" / "system_status_snapshot.json").write_text('{"generated_at": "old"}\n', encoding="utf-8")
    (root_path / "SYSTEM_STATUS.md").write_text("old status\n", encoding="utf-8")
    (root_path / "SYSTEM_SUMMARY.md").write_text("old summary\n", encoding="utf-8")

    class FakeSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {"generated_at": "2026-04-04T00:00:00Z", "workspace_root": str(root_path)}

    monkeypatch.setattr(remediation_module, "build_system_status_snapshot", lambda *args, **kwargs: FakeSnapshot())
    monkeypatch.setattr(remediation_module, "render_system_status_markdown", lambda snapshot: "new status\n")
    monkeypatch.setattr(remediation_module, "render_system_summary_markdown", lambda snapshot, component_index, kb_index: "new summary\n")

    simulation = remediation_module._build_dry_run_simulation(
        root_path,
        [_rule_result("status.summary_matches_workspace", passed=False)],
    )

    assert simulation["simulation_id"] == "dry_run_status_artifact_regeneration"
    assert simulation["simulation_phase"] == "dry_run_structured_remediation"
    assert simulation["workspace_mutation"] is False
    assert simulation["changed_paths"] == [
        "ai_docs/system_status_snapshot.json",
        "SYSTEM_STATUS.md",
        "SYSTEM_SUMMARY.md",
    ]
    assert simulation["unchanged_paths"] == []
    assert simulation["artifact_changes"][0] == {
        "target_path": "ai_docs/system_status_snapshot.json",
        "change_type": "update",
        "current_exists": True,
        "simulated_exists": True,
        "content_changed": True,
        "current_sha256": remediation_module._sha256_text('{"generated_at": "old"}\n'),
        "simulated_sha256": remediation_module._sha256_text(
            json.dumps({"generated_at": "2026-04-04T00:00:00Z", "workspace_root": str(root_path)}, indent=2)
        ),
        "current_line_count": 1,
        "simulated_line_count": 4,
        "current_excerpt": ['{"generated_at": "old"}'],
        "simulated_excerpt": [
            "{",
            '  "generated_at": "2026-04-04T00:00:00Z",',
            f'  "workspace_root": "{root_path}"',
            "}",
        ],
        "diff_line_count": 8,
        "diff_preview": [
            "--- a/ai_docs/system_status_snapshot.json",
            "+++ b/ai_docs/system_status_snapshot.json",
            "@@ -1 +1,4 @@",
            '-{"generated_at": "old"}',
            "+{",
            '+  "generated_at": "2026-04-04T00:00:00Z",',
            f'+  "workspace_root": "{root_path}"',
            "+}",
        ],
        "diff_truncated": False,
    }
    assert simulation["predicted_rule_outcomes"][0]["predicted_effect"] == "would_pass"
    assert simulation["predicted_rule_summary"]["failed_rules"] == 0
    assert simulation["notes"] == [
        "Dry-run simulation reuses the canonical status builders and renderers without writing files.",
        "Diff previews are deterministic excerpts from the simulated post-state for the governed status artifacts.",
    ]


def test_build_package_export_simulation_builds_exact_payload_shape(tmp_path: Path) -> None:
    root_path = tmp_path
    (root_path / "src" / "inf_work").mkdir(parents=True)
    (root_path / "src" / "inf_work" / "__init__.py").write_text("__all__ = []\n", encoding="utf-8")
    sync_state = {
        "module_path": "src/inf_work/__init__.py",
        "updated_text": '__all__ = [\n\t"symbol",\n]\n',
        "unsupported_symbols": [],
    }

    simulation = remediation_module._build_package_export_simulation(
        root_path,
        [_rule_result("knowledge_base.component_doc_python_api_symbols_valid", passed=False, domain="knowledge_base")],
        sync_state,
    )

    assert simulation["simulation_id"] == "dry_run_package_public_api_export_sync"
    assert simulation["simulation_phase"] == "dry_run_source_level_remediation"
    assert simulation["workspace_mutation"] is False
    assert simulation["artifact_changes"] == [
        {
            "target_path": "src/inf_work/__init__.py",
            "change_type": "update",
            "current_exists": True,
            "simulated_exists": True,
            "content_changed": True,
            "current_sha256": remediation_module._sha256_text("__all__ = []\n"),
            "simulated_sha256": remediation_module._sha256_text('__all__ = [\n\t"symbol",\n]\n'),
            "current_line_count": 1,
            "simulated_line_count": 3,
            "current_excerpt": ["__all__ = []"],
            "simulated_excerpt": ["__all__ = [", '\t"symbol",', "]"],
            "diff_line_count": 7,
            "diff_preview": [
                "--- a/src/inf_work/__init__.py",
                "+++ b/src/inf_work/__init__.py",
                "@@ -1 +1,3 @@",
                "-__all__ = []",
                "+__all__ = [",
                '+\t"symbol",',
                "+]",
            ],
            "diff_truncated": False,
        }
    ]
    assert simulation["changed_paths"] == ["src/inf_work/__init__.py"]
    assert simulation["unchanged_paths"] == []
    assert simulation["predicted_rule_outcomes"][0] == {
        "rule_id": "knowledge_base.component_doc_python_api_symbols_valid",
        "current_passed": False,
        "predicted_passed": True,
        "predicted_effect": "would_pass",
        "rationale": "Simulated package export synchronization adds the missing explicit re-exports required by the governed package API documentation.",
    }
    assert simulation["predicted_rule_summary"]["failed_rules"] == 0
    assert simulation["notes"] == [
        "Dry-run simulation previews the deterministic `src/inf_work/__init__.py` re-export patch without mutating the workspace.",
        "The current source-level slice stays bounded to the package public API export surface and excludes arbitrary Python edits.",
    ]


def test_build_package_export_simulation_sorts_rules_and_preserves_unaffected_rule_metadata(tmp_path: Path) -> None:
    root_path = tmp_path
    (root_path / "src" / "inf_work").mkdir(parents=True)
    (root_path / "src" / "inf_work" / "__init__.py").write_text("__all__ = []\n", encoding="utf-8")
    supported_rule = _rule_result(
        "knowledge_base.component_doc_python_api_symbols_valid",
        passed=False,
        domain="knowledge_base",
        category="api_surface",
    )
    unaffected_rule = _rule_result(
        "status.summary_matches_workspace",
        passed=False,
        domain="status",
        category="artifact_integrity",
    )

    simulation = remediation_module._build_package_export_simulation(
        root_path,
        [unaffected_rule, supported_rule],
        {
            "module_path": "src/inf_work/__init__.py",
            "updated_text": '__all__ = [\n\t"symbol",\n]\n',
            "unsupported_symbols": [],
        },
    )

    assert simulation["predicted_rule_outcomes"] == [
        {
            "rule_id": "knowledge_base.component_doc_python_api_symbols_valid",
            "current_passed": False,
            "predicted_passed": True,
            "predicted_effect": "would_pass",
            "rationale": "Simulated package export synchronization adds the missing explicit re-exports required by the governed package API documentation.",
        },
        {
            "rule_id": "status.summary_matches_workspace",
            "current_passed": False,
            "predicted_passed": False,
            "predicted_effect": "unchanged",
            "rationale": "Dry-run simulation does not alter this rule surface, so the current result is preserved.",
        },
    ]
    assert simulation["predicted_rule_summary"] == {
        "total_rules": 2,
        "passed_rules": 1,
        "failed_rules": 1,
        "total_findings": 1,
        "by_domain": {
            "knowledge_base": {"rules": 1, "failed_rules": 0, "findings": 0},
            "status": {"rules": 1, "failed_rules": 1, "findings": 1},
        },
        "by_category": {
            "api_surface": {"rules": 1, "failed_rules": 0, "findings": 0},
            "artifact_integrity": {"rules": 1, "failed_rules": 1, "findings": 1},
        },
        "by_severity": {"error": {"rules": 2, "failed_rules": 1, "findings": 1}},
    }


def test_build_package_export_simulation_passes_rule_ids_and_descriptions_into_summary(monkeypatch, tmp_path: Path) -> None:
    root_path = tmp_path
    (root_path / "src" / "inf_work").mkdir(parents=True)
    (root_path / "src" / "inf_work" / "__init__.py").write_text("__all__ = []\n", encoding="utf-8")
    captured: dict[str, object] = {}
    rule = RuleResult(
        rule_id="knowledge_base.component_doc_python_api_symbols_valid",
        domain="knowledge_base",
        category="api_surface",
        severity="error",
        description="missing export",
        passed=False,
        findings=[
            RuleFinding(
                message="missing",
                source_file="ai_docs/package_public_api_surface_20260331T000000Z.json",
                item_identifier="symbol",
                field_name="python_api",
            )
        ],
    )

    def fake_summarize_rule_results(rule_results):
        captured["rule_results"] = [
            {
                "rule_id": item.rule_id,
                "description": item.description,
                "passed": item.passed,
            }
            for item in rule_results
        ]
        return {"captured": True}

    monkeypatch.setattr(remediation_module, "summarize_rule_results", fake_summarize_rule_results)

    simulation = remediation_module._build_package_export_simulation(
        root_path,
        [rule],
        {
            "module_path": "src/inf_work/__init__.py",
            "updated_text": '__all__ = [\n\t"symbol",\n]\n',
            "unsupported_symbols": [],
        },
    )

    assert simulation["predicted_rule_summary"] == {"captured": True}
    assert captured["rule_results"] == [
        {
            "rule_id": "knowledge_base.component_doc_python_api_symbols_valid",
            "description": "missing export",
            "passed": True,
        }
    ]


def test_build_artifact_change_marks_truncation_when_diff_exceeds_preview_limit(monkeypatch, tmp_path: Path) -> None:
    target_path = tmp_path / "artifact.txt"
    target_path.write_text("old\n", encoding="utf-8")
    diff_lines = [f"line-{index}" for index in range(121)]

    monkeypatch.setattr(remediation_module.difflib, "unified_diff", lambda *args, **kwargs: iter(diff_lines))

    change = remediation_module._build_artifact_change(tmp_path, "artifact.txt", "new\n")

    assert change["diff_line_count"] == 121
    assert len(change["diff_preview"]) == 120
    assert change["diff_preview"][-1] == "line-119"
    assert change["diff_truncated"] is True


def test_build_artifact_change_does_not_truncate_when_diff_matches_preview_limit(monkeypatch, tmp_path: Path) -> None:
    target_path = tmp_path / "artifact.txt"
    target_path.write_text("old\n", encoding="utf-8")
    diff_lines = [f"line-{index}" for index in range(120)]

    monkeypatch.setattr(remediation_module.difflib, "unified_diff", lambda *args, **kwargs: iter(diff_lines))

    change = remediation_module._build_artifact_change(tmp_path, "artifact.txt", "new\n")

    assert change["diff_line_count"] == 120
    assert len(change["diff_preview"]) == 120
    assert change["diff_preview"][-1] == "line-119"
    assert change["diff_truncated"] is False


def test_build_package_export_simulation_reports_noop_when_updated_text_is_unchanged(tmp_path: Path) -> None:
    root_path = tmp_path
    (root_path / "src" / "inf_work").mkdir(parents=True)
    current_text = '__all__ = []\n'
    (root_path / "src" / "inf_work" / "__init__.py").write_text(current_text, encoding="utf-8")

    simulation = remediation_module._build_package_export_simulation(
        root_path,
        [_rule_result("knowledge_base.component_doc_python_api_symbols_valid", passed=True, domain="knowledge_base")],
        {
            "module_path": "src/inf_work/__init__.py",
            "updated_text": current_text,
            "unsupported_symbols": [],
        },
    )

    assert simulation["changed_paths"] == []
    assert simulation["unchanged_paths"] == ["src/inf_work/__init__.py"]
    assert simulation["artifact_changes"][0]["change_type"] == "noop"
    assert simulation["artifact_changes"][0]["diff_line_count"] == 0


def test_build_dry_run_simulation_reports_unchanged_paths_when_outputs_already_match(monkeypatch, tmp_path: Path) -> None:
    root_path = tmp_path
    (root_path / "ai_docs").mkdir()
    (root_path / "knowledge_base").mkdir()
    (root_path / "ai_docs" / "component_index.json").write_text('{"components": [], "metadata": {}}', encoding="utf-8")
    (root_path / "knowledge_base" / "kb_index.json").write_text('{"total_techniques": 10}', encoding="utf-8")
    snapshot_text = json.dumps({"generated_at": "2026-04-04T00:00:00Z", "workspace_root": str(root_path)}, indent=2)
    (root_path / "ai_docs" / "system_status_snapshot.json").write_text(snapshot_text, encoding="utf-8")
    (root_path / "SYSTEM_STATUS.md").write_text("new status\n", encoding="utf-8")
    (root_path / "SYSTEM_SUMMARY.md").write_text("new summary\n", encoding="utf-8")

    class FakeSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {"generated_at": "2026-04-04T00:00:00Z", "workspace_root": str(root_path)}

    monkeypatch.setattr(remediation_module, "build_system_status_snapshot", lambda *args, **kwargs: FakeSnapshot())
    monkeypatch.setattr(remediation_module, "render_system_status_markdown", lambda snapshot: "new status\n")
    monkeypatch.setattr(remediation_module, "render_system_summary_markdown", lambda snapshot, component_index, kb_index: "new summary\n")

    simulation = remediation_module._build_dry_run_simulation(root_path, [])

    assert simulation["changed_paths"] == []
    assert simulation["unchanged_paths"] == [
        "ai_docs/system_status_snapshot.json",
        "SYSTEM_STATUS.md",
        "SYSTEM_SUMMARY.md",
    ]
    assert all(change["change_type"] == "noop" for change in simulation["artifact_changes"])


def test_build_dry_run_simulation_passes_governed_builder_and_summary_inputs(monkeypatch, tmp_path: Path) -> None:
    root_path = tmp_path
    (root_path / "ai_docs").mkdir()
    (root_path / "knowledge_base").mkdir()
    component_index_payload = {"components": [], "metadata": {"schema_version": "1.0.0"}}
    kb_index_payload = {"total_techniques": 10, "last_updated": "2026-04-04T00:00:00Z"}
    (root_path / "ai_docs" / "component_index.json").write_text(json.dumps(component_index_payload), encoding="utf-8")
    (root_path / "knowledge_base" / "kb_index.json").write_text(json.dumps(kb_index_payload), encoding="utf-8")
    (root_path / "ai_docs" / "system_status_snapshot.json").write_text('{}\n', encoding="utf-8")
    (root_path / "SYSTEM_STATUS.md").write_text("status\n", encoding="utf-8")
    (root_path / "SYSTEM_SUMMARY.md").write_text("summary\n", encoding="utf-8")
    captured: dict[str, object] = {}

    class FakeSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {"generated_at": "2026-04-04T00:00:00Z", "workspace_root": str(root_path)}

    snapshot = FakeSnapshot()

    def fake_build_system_status_snapshot(workspace_root, *, canonical_json_path, derived_markdown_path):
        captured["workspace_root"] = workspace_root
        captured["canonical_json_path"] = canonical_json_path
        captured["derived_markdown_path"] = derived_markdown_path
        return snapshot

    def fake_render_system_status_markdown(input_snapshot):
        captured["status_snapshot"] = input_snapshot
        return "status\n"

    def fake_render_system_summary_markdown(input_snapshot, *, component_index, kb_index):
        captured["summary_snapshot"] = input_snapshot
        captured["component_index"] = component_index
        captured["kb_index"] = kb_index
        return "summary\n"

    monkeypatch.setattr(remediation_module, "build_system_status_snapshot", fake_build_system_status_snapshot)
    monkeypatch.setattr(remediation_module, "render_system_status_markdown", fake_render_system_status_markdown)
    monkeypatch.setattr(remediation_module, "render_system_summary_markdown", fake_render_system_summary_markdown)

    simulation = remediation_module._build_dry_run_simulation(
        root_path,
        [_rule_result("status.summary_matches_workspace", passed=False)],
    )

    assert simulation["simulation_id"] == "dry_run_status_artifact_regeneration"
    assert captured == {
        "workspace_root": root_path,
        "canonical_json_path": "ai_docs/system_status_snapshot.json",
        "derived_markdown_path": "SYSTEM_STATUS.md",
        "status_snapshot": snapshot,
        "summary_snapshot": snapshot,
        "component_index": component_index_payload,
        "kb_index": kb_index_payload,
    }


def test_build_dry_run_simulation_reads_indexes_with_utf8(monkeypatch, tmp_path: Path) -> None:
    root_path = tmp_path
    (root_path / "ai_docs").mkdir()
    (root_path / "knowledge_base").mkdir()
    component_index_path = root_path / "ai_docs" / "component_index.json"
    kb_index_path = root_path / "knowledge_base" / "kb_index.json"
    component_index_path.write_text('{"components": []}', encoding="utf-8")
    kb_index_path.write_text('{"total_techniques": 10}', encoding="utf-8")
    (root_path / "ai_docs" / "system_status_snapshot.json").write_text('{}\n', encoding="utf-8")
    (root_path / "SYSTEM_STATUS.md").write_text("status\n", encoding="utf-8")
    (root_path / "SYSTEM_SUMMARY.md").write_text("summary\n", encoding="utf-8")
    captured: list[tuple[Path, str | None]] = []
    original_read_text = Path.read_text

    class FakeSnapshot:
        def to_dict(self) -> dict[str, object]:
            return {"generated_at": "2026-04-04T00:00:00Z", "workspace_root": str(root_path)}

    def capturing_read_text(self: Path, encoding: str | None = None, **kwargs):
        if self in {component_index_path, kb_index_path}:
            captured.append((self, encoding))
        return original_read_text(self, encoding=encoding, **kwargs)

    monkeypatch.setattr(Path, "read_text", capturing_read_text)
    monkeypatch.setattr(remediation_module, "build_system_status_snapshot", lambda *args, **kwargs: FakeSnapshot())
    monkeypatch.setattr(remediation_module, "render_system_status_markdown", lambda snapshot: "status\n")
    monkeypatch.setattr(
        remediation_module,
        "render_system_summary_markdown",
        lambda snapshot, component_index, kb_index: "summary\n",
    )

    simulation = remediation_module._build_dry_run_simulation(root_path, [])

    assert simulation["simulation_id"] == "dry_run_status_artifact_regeneration"
    assert captured == [
        (component_index_path, "utf-8"),
        (kb_index_path, "utf-8"),
    ]


def test_extract_module_export_surface_reports_explicit_all_exactly(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from .alpha import exported_alias as alias\n\n"
        "class ExportedClass:\n"
        "    pass\n\n"
        "def exported_function():\n"
        "    return 1\n\n"
        "VALUE = 1\n"
        "__all__ = [\"alias\", \"exported_function\"]\n",
        encoding="utf-8",
    )

    exported_names, explicit_all = remediation_module._extract_module_export_surface(module_path)

    assert exported_names == {"alias", "ExportedClass", "exported_function", "VALUE"}
    assert explicit_all == {"alias", "exported_function"}


def test_append_helpers_preserve_existing_entries_and_order_exactly() -> None:
    current_text = (
        "from .beta import (\n"
        "\texisting_symbol,\n"
        ")\n\n"
        "__all__ = [\n"
        '\t"existing_symbol",\n'
        "]"
    )
    updated_imports = remediation_module._append_grouped_import_symbols(
        current_text,
        "beta",
        ["existing_symbol", "new_symbol"],
    )
    updated_all = remediation_module._append_all_entries(
        updated_imports,
        ["existing_symbol", "new_symbol"],
    )

    assert updated_imports == (
        "from .beta import (\n"
        "\texisting_symbol,\n"
        "\tnew_symbol,\n"
        ")\n\n"
        "__all__ = [\n"
        '\t"existing_symbol",\n'
        "]"
    )
    assert updated_all == (
        "from .beta import (\n"
        "\texisting_symbol,\n"
        "\tnew_symbol,\n"
        ")\n\n"
        "__all__ = [\n"
        '\t"existing_symbol",\n'
        '\t"new_symbol",\n'
        "]"
    )


def test_capture_artifact_pre_state_records_exact_file_state(tmp_path: Path) -> None:
    (tmp_path / "ai_docs").mkdir()
    (tmp_path / "ai_docs" / "system_status_snapshot.json").write_text('{"ok": true}\n', encoding="utf-8")

    pre_state = remediation_module._capture_artifact_pre_state(
        tmp_path,
        ["ai_docs/system_status_snapshot.json", "SYSTEM_STATUS.md"],
    )

    assert pre_state == {
        "ai_docs/system_status_snapshot.json": {
            "existed": True,
            "text": '{"ok": true}\n',
            "sha256": remediation_module._sha256_text('{"ok": true}\n'),
        },
        "SYSTEM_STATUS.md": {
            "existed": False,
            "text": None,
            "sha256": None,
        },
    }


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


def test_build_package_export_sync_state_builds_exact_payload(tmp_path: Path) -> None:
    package_root = tmp_path / "src" / "inf_work"
    package_root.mkdir(parents=True)
    (tmp_path / "ai_docs").mkdir()
    (tmp_path / "ai_docs" / "package_public_api_surface_20260331T000000Z.json").write_text(
        json.dumps(
            {
                "interfaces": {
                    "python_api": [
                        "from inf_work import existing_symbol, missing_symbol",
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    (package_root / "alpha.py").write_text("def missing_symbol():\n    return 'alpha'\n", encoding="utf-8")
    (package_root / "__init__.py").write_text(
        "from .beta import (\n\texisting_symbol,\n)\n\n__all__ = [\n\t\"existing_symbol\",\n]\n",
        encoding="utf-8",
    )

    sync_state = remediation_module._build_package_export_sync_state(tmp_path)

    assert sync_state == {
        "documentation_path": "ai_docs/package_public_api_surface_20260331T000000Z.json",
        "module_path": "src/inf_work/__init__.py",
        "package_import_entry": "from inf_work import existing_symbol, missing_symbol",
        "documented_symbols": ["existing_symbol", "missing_symbol"],
        "exported_names": ["existing_symbol"],
        "explicit_all": ["existing_symbol"],
        "missing_documented_symbols": ["missing_symbol"],
        "missing_import_symbols": ["missing_symbol"],
        "missing_all_symbols": ["missing_symbol"],
        "module_symbol_additions": {"alpha": ["missing_symbol"]},
        "unsupported_symbols": [],
        "updated_text": (
            "from .beta import (\n"
            "\texisting_symbol,\n"
            ")\n\n"
            "from .alpha import (\n"
            "\tmissing_symbol,\n"
            ")\n\n"
            "__all__ = [\n"
            "\t\"existing_symbol\",\n"
            "\t\"missing_symbol\",\n"
            "]\n"
        ),
    }


def test_build_package_export_sync_state_preserves_text_when_symbols_are_unsupported(tmp_path: Path) -> None:
    package_root = tmp_path / "src" / "inf_work"
    package_root.mkdir(parents=True)
    (tmp_path / "ai_docs").mkdir()
    (tmp_path / "ai_docs" / "package_public_api_surface_20260331T000000Z.json").write_text(
        json.dumps({"interfaces": {"python_api": ["from inf_work import missing_symbol"]}}),
        encoding="utf-8",
    )
    original_text = "__all__ = []\n"
    (package_root / "__init__.py").write_text(original_text, encoding="utf-8")

    sync_state = remediation_module._build_package_export_sync_state(tmp_path)

    assert sync_state["missing_documented_symbols"] == ["missing_symbol"]
    assert sync_state["unsupported_symbols"] == ["missing_symbol"]
    assert sync_state["module_symbol_additions"] == {}
    assert sync_state["updated_text"] == original_text


def test_build_package_export_sync_state_handles_missing_or_mixed_python_api_entries(tmp_path: Path) -> None:
    package_root = tmp_path / "src" / "inf_work"
    package_root.mkdir(parents=True)
    (tmp_path / "ai_docs").mkdir()
    (package_root / "__init__.py").write_text('__all__ = []\n', encoding="utf-8")
    (package_root / "remediation.py").write_text('def exported_symbol():\n    return 1\n', encoding="utf-8")

    missing_python_api_path = tmp_path / "ai_docs" / "package_public_api_surface_20260331T000000Z.json"
    missing_python_api_path.write_text(json.dumps({}), encoding="utf-8")

    missing_interfaces_state = remediation_module._build_package_export_sync_state(tmp_path)

    assert missing_interfaces_state["package_import_entry"] is None
    assert missing_interfaces_state["documented_symbols"] == []
    assert missing_interfaces_state["missing_documented_symbols"] == []
    assert missing_interfaces_state["updated_text"] == '__all__ = []\n'

    missing_python_api_path.write_text(json.dumps({"interfaces": {}}), encoding="utf-8")

    missing_state = remediation_module._build_package_export_sync_state(tmp_path)

    assert missing_state["package_import_entry"] is None
    assert missing_state["documented_symbols"] == []
    assert missing_state["missing_documented_symbols"] == []
    assert missing_state["updated_text"] == '__all__ = []\n'

    missing_python_api_path.write_text(
        json.dumps({"interfaces": {"python_api": [{"not": "a string"}, "from inf_work import exported_symbol"]}}),
        encoding="utf-8",
    )

    mixed_state = remediation_module._build_package_export_sync_state(tmp_path)

    assert mixed_state["package_import_entry"] == "from inf_work import exported_symbol"
    assert mixed_state["documented_symbols"] == ["exported_symbol"]


def test_build_package_export_sync_state_reads_governed_files_with_utf8(monkeypatch, tmp_path: Path) -> None:
    package_root = tmp_path / "src" / "inf_work"
    package_root.mkdir(parents=True)
    (tmp_path / "ai_docs").mkdir()
    doc_path = tmp_path / "ai_docs" / "package_public_api_surface_20260331T000000Z.json"
    init_path = package_root / "__init__.py"
    module_path = package_root / "remediation.py"
    doc_path.write_text(
        json.dumps({"interfaces": {"python_api": ["from inf_work import exported_symbol"]}}),
        encoding="utf-8",
    )
    init_path.write_text('__all__ = []\n', encoding="utf-8")
    module_path.write_text('def exported_symbol():\n    return 1\n', encoding="utf-8")
    original_read_text = Path.read_text
    captured: list[tuple[Path, str | None]] = []

    def capturing_read_text(self: Path, encoding: str | None = None, **kwargs):
        if self in {doc_path, init_path, module_path}:
            captured.append((self, encoding))
        return original_read_text(self, encoding=encoding, **kwargs)

    monkeypatch.setattr(Path, "read_text", capturing_read_text)

    sync_state = remediation_module._build_package_export_sync_state(tmp_path)

    assert sync_state["documented_symbols"] == ["exported_symbol"]
    assert (doc_path, "utf-8") in captured
    assert (init_path, "utf-8") in captured
    assert (module_path, "utf-8") in captured
    assert not any(path in {doc_path, init_path, module_path} and encoding is None for path, encoding in captured)
    assert not any(path in {doc_path, init_path, module_path} and encoding == "UTF-8" for path, encoding in captured)


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


def test_append_grouped_import_symbols_preserves_existing_entries_exactly() -> None:
    current_text = (
        "from .beta import (\n"
        "\tfirst_symbol,\n"
        "\tsecond_symbol,\n"
        ")\n\n"
        "__all__ = [\n"
        '\t"first_symbol",\n'
        '\t"second_symbol",\n'
        "]\n"
    )

    updated_text = remediation_module._append_grouped_import_symbols(current_text, "beta", ["third_symbol"])

    assert updated_text == (
        "from .beta import (\n"
        "\tfirst_symbol,\n"
        "\tsecond_symbol,\n"
        "\tthird_symbol,\n"
        ")\n\n"
        "__all__ = [\n"
        '\t"first_symbol",\n'
        '\t"second_symbol",\n'
        "]"
    )


def test_append_grouped_import_symbols_preserves_existing_symbols_ending_with_x() -> None:
    current_text = (
        "from .beta import (\n"
        "\ttrailingX,\n"
        ")\n\n"
        "__all__ = [\n"
        '\t"trailingX",\n'
        "]\n"
    )

    updated_text = remediation_module._append_grouped_import_symbols(current_text, "beta", ["second_symbol"])

    assert updated_text == (
        "from .beta import (\n"
        "\ttrailingX,\n"
        "\tsecond_symbol,\n"
        ")\n\n"
        "__all__ = [\n"
        '\t"trailingX",\n'
        "]"
    )


def test_append_grouped_import_symbols_drops_unclosed_original_block_tail() -> None:
    current_text = (
        "from .beta import (\n"
        "\texisting_symbol,\n"
        "__all__ = [\n"
        '\t"existing_symbol",\n'
        "]"
    )

    updated_text = remediation_module._append_grouped_import_symbols(current_text, "beta", ["second_symbol"])

    assert updated_text == (
        "from .beta import (\n"
        "\texisting_symbol,\n"
        "\t__all__ = [,\n"
        '\t"existing_symbol",\n'
        "\t],\n"
        "\tsecond_symbol,\n"
        ")"
    )


def test_append_all_entries_skips_blank_lines_in_existing_all_block() -> None:
    current_text = '__all__ = [\n\n\t"existing_symbol",\n]\n'

    updated_text = remediation_module._append_all_entries(current_text, ["second_symbol"])

    assert '\t"existing_symbol",' in updated_text
    assert '\t"second_symbol",' in updated_text
    assert "\n\n\t\"existing_symbol\"" not in updated_text


def test_append_all_entries_preserves_existing_entries_and_following_content_exactly() -> None:
    current_text = (
        '__all__ = [\n'
        '\t"first_symbol",\n'
        '\t"second_symbol",\n'
        ']\n\n'
        'AFTER_BLOCK = True\n'
    )

    updated_text = remediation_module._append_all_entries(current_text, ["third_symbol"])

    assert updated_text == (
        '__all__ = [\n'
        '\t"first_symbol",\n'
        '\t"second_symbol",\n'
        '\t"third_symbol",\n'
        ']\n\n'
        'AFTER_BLOCK = True'
    )


def test_append_all_entries_preserves_existing_symbols_ending_with_x() -> None:
    current_text = (
        '__all__ = [\n'
        '\t"trailingX",\n'
        ']\n'
    )

    updated_text = remediation_module._append_all_entries(current_text, ["second_symbol"])

    assert updated_text == (
        '__all__ = [\n'
        '\t"trailingX",\n'
        '\t"second_symbol",\n'
        ']'
    )


def test_append_all_entries_preserves_one_sided_quoted_symbols() -> None:
    current_text = (
        '__all__ = [\n'
        '\t"leading_only,\n'
        '\ttrailing_only",\n'
        ']\n'
    )

    updated_text = remediation_module._append_all_entries(current_text, ["second_symbol"])

    assert updated_text == (
        '__all__ = [\n'
        '\t""leading_only",\n'
        '\t"trailing_only\"",\n'
        '\t"second_symbol",\n'
        ']'
    )


def test_append_all_entries_drops_unclosed_original_block_tail() -> None:
    current_text = (
        '__all__ = [\n'
        '\t"existing_symbol",\n'
        'AFTER_BLOCK = True\n'
    )

    updated_text = remediation_module._append_all_entries(current_text, ["second_symbol"])

    assert updated_text == (
        '__all__ = [\n'
        '\t"existing_symbol",\n'
        '\t"AFTER_BLOCK = True",\n'
        '\t"second_symbol",\n'
        ']'
    )


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


def test_restore_artifact_pre_state_deletes_created_files_and_build_no_plan_result(tmp_path: Path) -> None:
    workspace_root = tmp_path
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


def test_restore_artifact_pre_state_restores_nested_files_with_parent_creation_and_utf8(monkeypatch, tmp_path: Path) -> None:
    target_path = tmp_path / "nested" / "deep" / "artifact.txt"
    mkdir_calls: list[tuple[Path, bool | None, bool | None]] = []
    write_calls: list[tuple[Path, str | None, str]] = []
    original_mkdir = Path.mkdir
    original_write_text = Path.write_text

    def capturing_mkdir(self: Path, mode=0o777, parents=False, exist_ok=False):
        if self == target_path.parent:
            mkdir_calls.append((self, parents, exist_ok))
        return original_mkdir(self, mode=mode, parents=parents, exist_ok=exist_ok)

    def capturing_write_text(self: Path, text: str, encoding: str | None = None, **kwargs):
        if self == target_path:
            write_calls.append((self, encoding, text))
        return original_write_text(self, text, encoding=encoding, **kwargs)

    monkeypatch.setattr(Path, "mkdir", capturing_mkdir)
    monkeypatch.setattr(Path, "write_text", capturing_write_text)

    rollback_summary = remediation_module._restore_artifact_pre_state(
        tmp_path,
        {
            "nested/deep/artifact.txt": {
                "existed": True,
                "text": "restored\n",
                "sha256": remediation_module._sha256_text("restored\n"),
            }
        },
    )

    assert rollback_summary == {"restored_paths": ["nested/deep/artifact.txt"], "deleted_paths": []}
    assert (target_path.parent, True, True) in mkdir_calls
    assert write_calls == [(target_path, "utf-8", "restored\n")]
    assert target_path.read_text(encoding="utf-8") == "restored\n"


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
    payload = result.to_dict()

    assert result.execution_attempted is False
    assert "No supported applied remediation was executed" in result.notes[0]
    assert payload["plan_id"] == "no-plan"
    assert payload["execution_phase"] == "applied_structured_remediation"
    assert payload["plan_available"] is False
    assert payload["rollback_summary"] == {"restored_paths": [], "deleted_paths": []}
    assert payload["notes"] == [
        "No supported applied remediation was executed because no bounded status-artifact remediation plan was available.",
        "already clean",
    ]


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
    payload = result.to_dict()

    assert result.applied is False
    assert result.execution_attempted is True
    assert result.compliant is False
    assert result.rollback_performed is True
    assert payload["workspace_root"] == str(workspace_root.resolve())
    assert payload["plan_id"] == "remediation_plan_status_artifact_regeneration"
    assert payload["execution_phase"] == "applied_structured_remediation"
    assert payload["plan_available"] is True
    assert payload["rollback_summary"] == {
        "restored_paths": [
            "SYSTEM_STATUS.md",
            "SYSTEM_SUMMARY.md",
            "ai_docs/system_status_snapshot.json",
        ],
        "deleted_paths": [],
    }
    assert payload["triggering_rule_ids"] == ["status.snapshot_matches_workspace"]
    assert payload["unsupported_failing_rule_ids"] == []
    assert any(note.endswith("forced failure") for note in result.notes)
    assert payload["status_validation"] is None
    assert payload["summary_validation"] is None
    assert payload["knowledge_base_validation"] is None
    assert payload["operation_results"] == []
    assert payload["notes"] == [
        "Applied remediation encountered an exception and the bounded rollback contract restored the pre-remediation artifact state.",
        "Exception: forced failure",
    ]


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

    payload = plan.to_dict()

    assert plan.plan_available is True
    assert payload["workspace_root"] == str(workspace_root.resolve())
    assert payload["current_status_compliant"] is False
    assert plan.selected_strategy is not None
    assert plan.selected_strategy.strategy_id == "strategy_package_public_api_export_sync"
    assert payload["objective"] == (
        "Synchronize the governed `inf_work` package export surface so the package public API documentation references only explicit re-exports."
    )
    assert payload["plan_phase"] == "dry_run_source_level_remediation"
    assert payload["plan_only"] is False
    assert payload["selected_rule_ids"] == ["knowledge_base.component_doc_python_api_symbols_valid"]
    assert payload["triggering_rule_ids"] == ["knowledge_base.component_doc_python_api_symbols_valid"]
    assert payload["unsupported_failing_rule_ids"] == []
    assert payload["triggering_evidence"] == [
        _rule_result(
            "knowledge_base.component_doc_python_api_symbols_valid",
            passed=False,
            domain="knowledge_base",
            category="api_surface",
        ).to_dict()
    ]
    assert payload["operations"] == [
        operation.to_dict() for operation in remediation_module._build_package_export_plan_operations(
            str(workspace_root.resolve()),
            ["knowledge_base.component_doc_python_api_symbols_valid"],
        )
    ]
    assert plan.operations[0].operation_type == "rewrite_python_source"
    assert plan.affected_paths == ["src/inf_work/__init__.py"]
    assert plan.simulation_available is True
    assert plan.simulation is not None
    assert plan.simulation["changed_paths"] == ["src/inf_work/__init__.py"]
    assert payload["verification_contract"]["required_rule_ids"] == [
        "knowledge_base.component_doc_python_api_symbols_valid"
    ]
    assert payload["verification_contract"]["commands"] == [
        f"python -m inf_work kb {workspace_root.resolve()} --pretty --rule-id knowledge_base.component_doc_python_api_symbols_valid"
    ]
    assert payload["rollback_contract"]["contract_id"] == "rollback_python_source_pre_state_restore"
    assert payload["provenance"] == {
        "record_id": "provenance_package_public_api_export_sync",
        "trigger_kind": "knowledge_base_rule_failure",
        "trigger_rule_ids": ["knowledge_base.component_doc_python_api_symbols_valid"],
        "governed_intent_ids": [],
        "supporting_rule_ids": [],
        "source_artifact_paths": [
            "ai_docs/package_public_api_surface_20260331T000000Z.json",
            "src/inf_work/__init__.py",
        ],
        "derived_from_components": [
            "package_public_api_surface",
            "remediation_plan_compiler",
            "unified_cli_entry_point",
        ],
    }
    assert payload["notes"] == [
        "The current Phase 4 slice is bounded to deterministic re-export synchronization in `src/inf_work/__init__.py`.",
        "The strategy only compiles when every missing documented symbol resolves to exactly one governed provider module.",
        "The current slice intentionally excludes arbitrary Python edits, multi-file synthesis, and interface redesign.",
    ]


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
    payload = plan.to_dict()

    assert plan.plan_available is False
    assert payload["workspace_root"] == str(workspace_root.resolve())
    assert payload["plan_id"] == "remediation_plan_package_public_api_export_sync"
    assert payload["objective"] == "Determine whether the bounded package-export source-level remediation slice should compile a deterministic plan."
    assert payload["plan_phase"] == "bounded_source_level_remediation"
    assert payload["plan_only"] is True
    assert payload["current_status_compliant"] is False
    assert payload["selected_rule_ids"] == []
    assert payload["triggering_rule_ids"] == []
    assert payload["unsupported_failing_rule_ids"] == []
    assert payload["triggering_evidence"] == []
    assert payload["simulation_available"] is False
    assert payload["simulation"] is None
    assert payload["current_rule_summary"] == remediation_module.summarize_rule_results(
        [
            _rule_result(
                "knowledge_base.component_doc_python_api_symbols_valid",
                passed=False,
                domain="knowledge_base",
                category="api_surface",
            )
        ]
    )
    assert payload["affected_paths"] == ["src/inf_work/__init__.py"]
    assert payload["rollback_contract"] == {
        "contract_id": "rollback_python_source_pre_state_restore",
        "strategy": "restore_pre_state_file_contents",
        "steps": [
            "Capture the full pre-remediation contents of the targeted Python source file before mutation.",
            "If verification fails, restore the exact pre-state file contents and rerun the targeted validator.",
        ],
    }
    assert payload["provenance"] == {
        "record_id": "provenance_package_public_api_export_sync",
        "trigger_kind": "knowledge_base_rule_failure",
        "trigger_rule_ids": [],
        "governed_intent_ids": [],
        "supporting_rule_ids": [],
        "source_artifact_paths": [
            "ai_docs/package_public_api_surface_20260331T000000Z.json",
            "src/inf_work/__init__.py",
        ],
        "derived_from_components": [
            "package_public_api_surface",
            "remediation_plan_compiler",
            "unified_cli_entry_point",
        ],
    }
    assert payload["provenance"]["supporting_rule_ids"] == []
    assert payload["notes"] == [
        "No supported Phase 4 package-export drift failures are active, so no bounded source-level remediation plan is compiled.",
        "Some missing documented package exports could not be resolved to exactly one governed provider module, so source-level remediation remains blocked for those symbols.",
    ]
    assert "could not be resolved to exactly one governed provider module" in plan.notes[-1]


def test_compile_package_public_api_export_remediation_plan_no_plan_honors_dry_run_phase(monkeypatch, tmp_path: Path) -> None:
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

    failing_rule = _rule_result(
        "knowledge_base.component_doc_python_api_symbols_valid",
        passed=False,
        domain="knowledge_base",
        category="api_surface",
    )
    monkeypatch.setattr(
        remediation_module,
        "validate_knowledge_base",
        lambda workspace_root, rule_ids: _kb_validation_result(
            failing_rule,
            compliant=False,
            workspace_root=Path(workspace_root),
        ),
    )

    plan = compile_package_public_api_export_remediation_plan(workspace_root, include_simulation=True)
    payload = plan.to_dict()

    assert plan.plan_available is False
    assert payload["plan_phase"] == "dry_run_source_level_remediation"
    assert payload["plan_only"] is False
    assert payload["current_rule_summary"] == remediation_module.summarize_rule_results([failing_rule])
    assert payload["affected_paths"] == ["src/inf_work/__init__.py"]
    assert payload["rollback_contract"]["contract_id"] == "rollback_python_source_pre_state_restore"
    assert payload["provenance"]["trigger_rule_ids"] == []
    assert payload["provenance"]["supporting_rule_ids"] == []
    assert payload["simulation_available"] is False
    assert payload["simulation"] is None


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
    payload = plan.to_dict()

    assert plan.plan_available is False
    assert payload["plan_phase"] == "bounded_source_level_remediation"
    assert payload["plan_only"] is True
    assert payload["current_status_compliant"] is False
    assert payload["triggering_rule_ids"] == []
    assert payload["unsupported_failing_rule_ids"] == []
    assert payload["selected_strategy"] is None
    assert payload["triggering_evidence"] == []
    assert payload["simulation_available"] is False
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

    assert sync_state["missing_documented_symbols"] == ["synced_symbol"]
    assert sync_state["missing_import_symbols"] == []
    assert sync_state["missing_all_symbols"] == ["synced_symbol"]
    assert sync_state["explicit_all"] == []
    assert '"synced_symbol"' in sync_state["updated_text"]


def test_build_package_export_sync_state_preserves_leading_whitespace_when_normalizing_updated_text(tmp_path: Path) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir()
    (workspace_root / "src" / "inf_work").mkdir(parents=True)
    (workspace_root / "ai_docs" / "package_public_api_surface_20260331T000000Z.json").write_text(
        json.dumps({"interfaces": {"python_api": ["from inf_work import synced_symbol"]}}),
        encoding="utf-8",
    )
    (workspace_root / "src" / "inf_work" / "__init__.py").write_text(
        '\n\nfrom .remediation import (\n\tsynced_symbol,\n)\n\n__all__ = [\n]\n',
        encoding="utf-8",
    )
    (workspace_root / "src" / "inf_work" / "remediation.py").write_text(
        'def synced_symbol():\n    return 1\n',
        encoding="utf-8",
    )

    sync_state = remediation_module._build_package_export_sync_state(workspace_root)

    assert sync_state["updated_text"].startswith('\n\nfrom .remediation import (')


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
    payload = plan.to_dict()

    assert plan.plan_available is False
    assert payload["workspace_root"] == str(tmp_path.resolve())
    assert payload["plan_id"] == "remediation_plan_package_public_api_export_sync"
    assert payload["objective"] == "Determine whether the bounded package-export source-level remediation slice should compile a deterministic plan."
    assert payload["unsupported_failing_rule_ids"] == ["knowledge_base.unrelated_rule"]
    assert payload["provenance"]["supporting_rule_ids"] == ["knowledge_base.unrelated_rule"]
    assert payload["notes"] == [
        "No supported Phase 4 package-export drift failures are active, so no bounded source-level remediation plan is compiled.",
        "Failing knowledge-base rules remain outside the supported Phase 4 package-export remediation slice and must be handled by validator-specific workflows.",
    ]
    assert "outside the supported Phase 4 package-export remediation slice" in plan.notes[-1]


def test_compile_package_public_api_export_remediation_plan_preserves_mixed_supported_and_unsupported_failures(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir()
    (workspace_root / "src" / "inf_work").mkdir(parents=True)
    (workspace_root / "ai_docs" / "package_public_api_surface_20260331T000000Z.json").write_text(
        json.dumps({"interfaces": {"python_api": ["from inf_work import exported_symbol, missing_symbol"]}}),
        encoding="utf-8",
    )
    (workspace_root / "src" / "inf_work" / "__init__.py").write_text(
        'from .remediation import (\n\texported_symbol,\n)\n\n__all__ = [\n\t"exported_symbol",\n]\n',
        encoding="utf-8",
    )
    (workspace_root / "src" / "inf_work" / "remediation.py").write_text(
        'def exported_symbol():\n    return 1\n\n'
        'def missing_symbol():\n    return 2\n',
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

    plan = compile_package_public_api_export_remediation_plan(workspace_root)
    payload = plan.to_dict()

    assert payload["plan_available"] is True
    assert payload["triggering_rule_ids"] == ["knowledge_base.component_doc_python_api_symbols_valid"]
    assert payload["unsupported_failing_rule_ids"] == ["knowledge_base.unrelated_rule"]
    assert payload["triggering_evidence"] == [
        _rule_result(
            "knowledge_base.component_doc_python_api_symbols_valid",
            passed=False,
            domain="knowledge_base",
            category="api_surface",
        ).to_dict()
    ]
    assert payload["provenance"]["supporting_rule_ids"] == ["knowledge_base.unrelated_rule"]
    assert payload["simulation"] is None


def test_apply_status_artifact_remediation_preserves_unsupported_failures_in_success_result(monkeypatch, tmp_path: Path) -> None:
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
                _rule_result("status.artifacts_exist", passed=False),
                compliant=False,
            )
        return _status_validation_result(
            _rule_result("status.snapshot_matches_workspace", passed=True),
            compliant=True,
        )

    monkeypatch.setattr(remediation_module, "validate_system_status", fake_validate_system_status)
    monkeypatch.setattr(
        remediation_module,
        "validate_system_summary",
        lambda workspace_root: _status_validation_result(
            _rule_result("status.summary_matches_workspace", passed=True),
            compliant=True,
        ),
    )

    class FakeSnapshot:
        generated_at = "2026-04-04T02:00:00Z"
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

    result = apply_status_artifact_remediation(workspace_root)

    assert result.applied is True
    assert result.unsupported_failing_rule_ids == ["status.artifacts_exist"]
    assert result.to_dict()["unsupported_failing_rule_ids"] == ["status.artifacts_exist"]


def test_apply_package_public_api_export_remediation_preserves_unsupported_failures_in_success_result(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir()
    (workspace_root / "src" / "inf_work").mkdir(parents=True)
    (workspace_root / "ai_docs" / "package_public_api_surface_20260331T000000Z.json").write_text(
        json.dumps({"interfaces": {"python_api": ["from inf_work import missing_symbol"]}}),
        encoding="utf-8",
    )
    (workspace_root / "src" / "inf_work" / "__init__.py").write_text('__all__ = []\n', encoding="utf-8")
    (workspace_root / "src" / "inf_work" / "remediation.py").write_text(
        'def missing_symbol():\n    return None\n',
        encoding="utf-8",
    )

    validation_calls = {"count": 0}

    def fake_validate_knowledge_base(workspace_root: Path, rule_ids: set[str] | None):
        validation_calls["count"] += 1
        if validation_calls["count"] == 1:
            return _kb_validation_result(
                _rule_result(
                    "knowledge_base.component_doc_python_api_symbols_valid",
                    passed=False,
                    domain="knowledge_base",
                    category="api_surface",
                ),
                _rule_result(
                    "knowledge_base.unrelated_rule",
                    passed=False,
                    domain="knowledge_base",
                    category="api_surface",
                ),
                compliant=False,
                workspace_root=Path(workspace_root),
            )
        return _kb_validation_result(
            _rule_result(
                "knowledge_base.component_doc_python_api_symbols_valid",
                passed=True,
                domain="knowledge_base",
                category="api_surface",
            ),
            compliant=True,
            workspace_root=Path(workspace_root),
        )

    monkeypatch.setattr(remediation_module, "validate_knowledge_base", fake_validate_knowledge_base)

    result = apply_package_public_api_export_remediation(workspace_root)

    assert result.applied is True
    assert result.unsupported_failing_rule_ids == ["knowledge_base.unrelated_rule"]
    assert result.to_dict()["unsupported_failing_rule_ids"] == ["knowledge_base.unrelated_rule"]


def test_build_no_plan_execution_result_preserves_noncompliant_plan_state() -> None:
    plan = remediation_module.RemediationPlan(
        workspace_root="/tmp/workspace",
        plan_id="noncompliant-no-plan",
        objective="noop",
        plan_phase="phase",
        plan_only=True,
        current_status_compliant=False,
        plan_available=False,
        selected_rule_ids=[],
        triggering_rule_ids=[],
        unsupported_failing_rule_ids=["status.artifacts_exist"],
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
        notes=["existing note"],
    )

    result = remediation_module._build_no_plan_execution_result(plan, notes=["no plan note"])

    assert result.compliant is False
    assert result.plan_available is False
    assert result.unsupported_failing_rule_ids == ["status.artifacts_exist"]
    assert result.to_dict()["notes"] == ["no plan note"]


def test_compile_remediation_plan_prefers_package_export_slice_for_kb_rule(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        remediation_module,
        "compile_status_artifact_remediation_plan",
        lambda workspace_root, rule_ids, include_simulation=False, intent_id=None: captured.update(
            {
                "status_workspace_root": Path(workspace_root).resolve(),
                "status_rule_ids": rule_ids,
                "status_include_simulation": include_simulation,
                "status_intent_id": intent_id,
            }
        )
        or remediation_module.RemediationPlan(
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
        lambda workspace_root, rule_ids, include_simulation=False: captured.update(
            {
                "package_workspace_root": Path(workspace_root).resolve(),
                "package_rule_ids": rule_ids,
                "package_include_simulation": include_simulation,
            }
        )
        or remediation_module.RemediationPlan(
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
    assert captured == {
        "status_workspace_root": workspace_root.resolve(),
        "status_rule_ids": {"knowledge_base.component_doc_python_api_symbols_valid"},
        "status_include_simulation": False,
        "status_intent_id": None,
        "package_workspace_root": workspace_root.resolve(),
        "package_rule_ids": {"knowledge_base.component_doc_python_api_symbols_valid"},
        "package_include_simulation": False,
    }


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
    payload = result.to_dict()

    assert result.applied is True
    assert result.compliant is True
    assert result.rollback_performed is False
    updated_text = init_path.read_text(encoding="utf-8")
    assert "apply_status_artifact_remediation" in updated_text
    assert '"apply_status_artifact_remediation"' in updated_text
    assert result.knowledge_base_validation is not None
    assert payload["plan_id"] == "remediation_plan_package_public_api_export_sync"
    assert payload["workspace_root"] == str(workspace_root.resolve())
    assert payload["execution_phase"] == "bounded_source_level_remediation"
    assert payload["triggering_rule_ids"] == ["knowledge_base.component_doc_python_api_symbols_valid"]
    assert payload["unsupported_failing_rule_ids"] == []
    assert payload["rollback_summary"] == {"restored_paths": [], "deleted_paths": []}
    assert payload["operation_results"][0] == {
        "operation_id": "sync_package_public_api_exports",
        "operation_type": "rewrite_python_source",
        "target_paths": ["src/inf_work/__init__.py"],
        "status": "completed",
        "mutation_performed": True,
        "details": {
            "module_symbol_additions": {"remediation": ["apply_status_artifact_remediation"]},
            "missing_all_symbols": ["apply_status_artifact_remediation"],
            "updated_path": "src/inf_work/__init__.py",
        },
    }
    assert payload["operation_results"][1]["operation_id"] == "validate_package_public_api_exports"
    assert payload["operation_results"][1]["status"] == "completed"
    assert payload["operation_results"][1]["mutation_performed"] is False
    assert payload["operation_results"][1]["details"] == {
        "compliant": True,
        "issue_count": 0,
        "rule_summary": remediation_module.summarize_rule_results(
            [
                _rule_result(
                    "knowledge_base.component_doc_python_api_symbols_valid",
                    passed=True,
                    domain="knowledge_base",
                    category="api_surface",
                )
            ]
        ),
    }
    assert payload["execution_attempted"] is True
    assert payload["plan_available"] is True
    assert payload["knowledge_base_validation"] == _kb_validation_result(
        _rule_result(
            "knowledge_base.component_doc_python_api_symbols_valid",
            passed=True,
            domain="knowledge_base",
            category="api_surface",
        ),
        compliant=True,
        workspace_root=workspace_root,
    ).to_dict()
    assert payload["notes"] == [
        "Applied remediation completed successfully for the bounded package-export source-level slice.",
        "Verification passed without requiring rollback.",
    ]


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
    payload = result.to_dict()

    assert result.execution_attempted is False
    assert "No supported applied remediation was executed" in result.notes[0]
    assert payload["plan_id"] == "no-package-plan"
    assert payload["execution_phase"] == "applied_structured_remediation"
    assert payload["notes"] == [
        "No supported applied remediation was executed because no bounded package-export source-level remediation plan was available.",
        "already synced",
    ]


def test_apply_package_public_api_export_remediation_forwards_rule_ids_and_disable_simulation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path
    captured: dict[str, object] = {}
    plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="no-package-plan",
        objective="noop",
        plan_phase="phase",
        plan_only=True,
        current_status_compliant=True,
        plan_available=False,
        selected_rule_ids=["knowledge_base.component_doc_python_api_symbols_valid"],
        triggering_rule_ids=[],
        unsupported_failing_rule_ids=[],
        selected_strategy=None,
        triggering_evidence=[],
        current_rule_summary={"failed_rules": 0},
        affected_paths=[],
        operations=[],
        verification_contract=None,
        rollback_contract=None,
        provenance=remediation_module.ChangeProvenanceRecord("id", "kind", [], [], [], [], []),
        simulation_available=False,
        simulation=None,
        notes=["already synced"],
    )

    def fake_compile_package_public_api_export_remediation_plan(workspace_root, rule_ids, **kwargs):
        captured["workspace_root"] = Path(workspace_root).resolve()
        captured["rule_ids"] = rule_ids
        captured["kwargs"] = kwargs
        return plan

    monkeypatch.setattr(
        remediation_module,
        "compile_package_public_api_export_remediation_plan",
        fake_compile_package_public_api_export_remediation_plan,
    )

    result = apply_package_public_api_export_remediation(
        workspace_root,
        {"knowledge_base.component_doc_python_api_symbols_valid"},
    )

    assert captured == {
        "workspace_root": workspace_root.resolve(),
        "rule_ids": {"knowledge_base.component_doc_python_api_symbols_valid"},
        "kwargs": {"include_simulation": False},
    }
    assert result.execution_attempted is False
    assert result.plan_available is False


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
    payload = result.to_dict()

    assert result.applied is False
    assert result.execution_attempted is True
    assert result.compliant is False
    assert result.rollback_performed is True
    assert payload["workspace_root"] == str(workspace_root.resolve())
    assert payload["plan_id"] == "remediation_plan_package_public_api_export_sync"
    assert payload["execution_phase"] == "bounded_source_level_remediation"
    assert payload["plan_available"] is True
    assert payload["rollback_summary"] == {"restored_paths": ["src/inf_work/__init__.py"], "deleted_paths": []}
    assert payload["triggering_rule_ids"] == ["knowledge_base.component_doc_python_api_symbols_valid"]
    assert payload["unsupported_failing_rule_ids"] == []
    assert init_path.read_text(encoding="utf-8") == original_text
    assert result.knowledge_base_validation is not None
    assert payload["operation_results"][0]["status"] == "completed"
    assert payload["operation_results"][1]["status"] == "failed"
    assert payload["operation_results"][1]["mutation_performed"] is False
    assert payload["operation_results"][1]["details"] == {
        "compliant": False,
        "issue_count": 0,
        "rule_summary": remediation_module.summarize_rule_results(
            [
                _rule_result(
                    "knowledge_base.component_doc_python_api_symbols_valid",
                    passed=False,
                    domain="knowledge_base",
                    category="api_surface",
                )
            ]
        ),
    }
    assert payload["operation_results"][1]["details"]["compliant"] is False
    assert payload["notes"] == [
        "Applied remediation failed verification and the bounded rollback contract restored the pre-remediation Python source state.",
    ]


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
    payload = result.to_dict()

    assert result.applied is False
    assert result.execution_attempted is True
    assert result.compliant is False
    assert result.rollback_performed is True
    assert payload["workspace_root"] == str(workspace_root.resolve())
    assert payload["plan_id"] == "remediation_plan_package_public_api_export_sync"
    assert payload["execution_phase"] == "bounded_source_level_remediation"
    assert payload["plan_available"] is True
    assert payload["rollback_summary"] == {
        "restored_paths": ["src/inf_work/__init__.py"],
        "deleted_paths": [],
    }
    assert payload["triggering_rule_ids"] == ["knowledge_base.component_doc_python_api_symbols_valid"]
    assert payload["unsupported_failing_rule_ids"] == []
    assert init_path.read_text(encoding="utf-8") == original_text
    assert any(note.endswith("write failed") for note in result.notes)
    assert payload["knowledge_base_validation"] is None
    assert payload["operation_results"] == []
    assert payload["notes"] == [
        "Applied remediation encountered an exception and the bounded rollback contract restored the pre-remediation Python source state.",
        "Exception: write failed",
    ]


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


def test_compile_remediation_plan_routes_selected_domain_over_priority(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path

    def make_plan(plan_id: str, strategy):
        return remediation_module.RemediationPlan(
            workspace_root=str(workspace_root.resolve()),
            plan_id=plan_id,
            objective=plan_id,
            plan_phase="phase",
            plan_only=True,
            current_status_compliant=False,
            plan_available=True,
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

    status_available = make_plan("status-available", remediation_module.STATUS_ARTIFACT_REMEDIATION_STRATEGY)
    package_available = make_plan("package-available", remediation_module.PACKAGE_EXPORT_SYNC_REMEDIATION_STRATEGY)

    monkeypatch.setattr(remediation_module, "compile_status_artifact_remediation_plan", lambda *args, **kwargs: status_available)
    monkeypatch.setattr(remediation_module, "compile_package_public_api_export_remediation_plan", lambda *args, **kwargs: package_available)

    package_plan = compile_remediation_plan(
        workspace_root,
        {"knowledge_base.component_doc_python_api_symbols_valid"},
    )
    status_plan = compile_remediation_plan(
        workspace_root,
        {"status.snapshot_matches_workspace"},
    )

    assert package_plan.plan_id == "package-available"
    assert status_plan.plan_id == "status-available"


def test_compile_remediation_plan_routes_multi_dot_rule_ids_by_first_domain_segment(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path

    def make_plan(plan_id: str, strategy):
        return remediation_module.RemediationPlan(
            workspace_root=str(workspace_root.resolve()),
            plan_id=plan_id,
            objective=plan_id,
            plan_phase="phase",
            plan_only=True,
            current_status_compliant=False,
            plan_available=True,
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

    status_available = make_plan("status-available", remediation_module.STATUS_ARTIFACT_REMEDIATION_STRATEGY)
    package_available = make_plan("package-available", remediation_module.PACKAGE_EXPORT_SYNC_REMEDIATION_STRATEGY)

    monkeypatch.setattr(remediation_module, "compile_status_artifact_remediation_plan", lambda *args, **kwargs: status_available)
    monkeypatch.setattr(remediation_module, "compile_package_public_api_export_remediation_plan", lambda *args, **kwargs: package_available)

    package_plan = compile_remediation_plan(workspace_root, {"knowledge_base.extra.rule"})
    status_plan = compile_remediation_plan(workspace_root, {"status.extra.rule"})

    assert package_plan.plan_id == "package-available"
    assert status_plan.plan_id == "status-available"


def test_compile_remediation_plan_respects_selected_status_domain_before_available_plan_selection(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path

    status_plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="status-unavailable",
        objective="status",
        plan_phase="phase",
        plan_only=True,
        current_status_compliant=True,
        plan_available=False,
        selected_rule_ids=["status.snapshot_matches_workspace"],
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
    )
    package_plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="package-available",
        objective="package",
        plan_phase="phase",
        plan_only=True,
        current_status_compliant=False,
        plan_available=True,
        selected_rule_ids=[],
        triggering_rule_ids=[],
        unsupported_failing_rule_ids=[],
        selected_strategy=remediation_module.PACKAGE_EXPORT_SYNC_REMEDIATION_STRATEGY,
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

    monkeypatch.setattr(remediation_module, "compile_status_artifact_remediation_plan", lambda *args, **kwargs: status_plan)
    monkeypatch.setattr(remediation_module, "compile_package_public_api_export_remediation_plan", lambda *args, **kwargs: package_plan)

    plan = compile_remediation_plan(workspace_root, {"status.snapshot_matches_workspace"})

    assert plan.plan_id == "status-unavailable"


def test_compile_remediation_plan_ignores_available_plans_without_strategy_binding(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    status_plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="status-clean",
        objective="status",
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
        notes=[],
    )
    package_plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="package-unbound",
        objective="package",
        plan_phase="phase",
        plan_only=True,
        current_status_compliant=True,
        plan_available=True,
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
    )

    monkeypatch.setattr(remediation_module, "compile_status_artifact_remediation_plan", lambda *args, **kwargs: status_plan)
    monkeypatch.setattr(remediation_module, "compile_package_public_api_export_remediation_plan", lambda *args, **kwargs: package_plan)

    plan = compile_remediation_plan(workspace_root)

    assert plan.plan_id == "status-clean"


def test_compile_remediation_plan_returns_available_package_plan_before_clean_status_fallback(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    status_plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="status-clean",
        objective="status",
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
        notes=[],
    )
    package_plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="package-available",
        objective="package",
        plan_phase="phase",
        plan_only=True,
        current_status_compliant=True,
        plan_available=True,
        selected_rule_ids=[],
        triggering_rule_ids=[],
        unsupported_failing_rule_ids=[],
        selected_strategy=remediation_module.PACKAGE_EXPORT_SYNC_REMEDIATION_STRATEGY,
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

    monkeypatch.setattr(remediation_module, "compile_status_artifact_remediation_plan", lambda *args, **kwargs: status_plan)
    monkeypatch.setattr(remediation_module, "compile_package_public_api_export_remediation_plan", lambda *args, **kwargs: package_plan)

    plan = compile_remediation_plan(workspace_root)

    assert plan.plan_id == "package-available"


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
    compile_calls: dict[str, object] = {}
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        remediation_module,
        "compile_remediation_plan",
        lambda workspace_root, rule_ids, include_simulation=False, intent_id=None: compile_calls.update(
            {
                "workspace_root": workspace_root,
                "rule_ids": rule_ids,
                "include_simulation": include_simulation,
                "intent_id": intent_id,
            }
        )
        or plan,
    )
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
    assert compile_calls == {
        "workspace_root": workspace_root,
        "rule_ids": {"knowledge_base.component_doc_python_api_symbols_valid"},
        "include_simulation": False,
        "intent_id": None,
    }
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
    compile_calls: dict[str, object] = {}
    monkeypatch.setattr(
        remediation_module,
        "compile_remediation_plan",
        lambda workspace_root, rule_ids, **kwargs: compile_calls.update(
            {
                "workspace_root": workspace_root,
                "rule_ids": rule_ids,
                "kwargs": kwargs,
            }
        ) or base_plan,
    )

    no_plan_result = apply_remediation_plan(workspace_root)

    assert no_plan_result.execution_attempted is False
    assert "No supported applied remediation was executed" in no_plan_result.notes[0]
    assert no_plan_result.to_dict()["notes"] == [
        "No supported applied remediation was executed because no bounded remediation plan was available for the selected rule slice.",
        "base",
    ]
    assert compile_calls == {
        "workspace_root": workspace_root,
        "rule_ids": None,
        "kwargs": {"include_simulation": False, "intent_id": None},
    }

    status_plan = remediation_module.RemediationPlan(
        **{**base_plan.__dict__, "plan_available": True, "selected_strategy": remediation_module.STATUS_ARTIFACT_REMEDIATION_STRATEGY, "plan_id": "status"}
    )
    captured: dict[str, object] = {}
    status_compile_calls: dict[str, object] = {}
    monkeypatch.setattr(
        remediation_module,
        "compile_remediation_plan",
        lambda workspace_root, rule_ids, **kwargs: status_compile_calls.update(
            {
                "workspace_root": workspace_root,
                "rule_ids": rule_ids,
                "kwargs": kwargs,
            }
        ) or status_plan,
    )
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
    assert status_compile_calls == {
        "workspace_root": workspace_root,
        "rule_ids": {"status.snapshot_matches_workspace"},
        "kwargs": {"include_simulation": False, "intent_id": "intent.status.refresh_artifacts"},
    }
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
    unknown_compile_calls: dict[str, object] = {}
    monkeypatch.setattr(
        remediation_module,
        "compile_remediation_plan",
        lambda workspace_root, rule_ids, **kwargs: unknown_compile_calls.update(
            {
                "workspace_root": workspace_root,
                "rule_ids": rule_ids,
                "kwargs": kwargs,
            }
        ) or unknown_plan,
    )

    unknown_result = apply_remediation_plan(workspace_root)

    assert unknown_result.execution_attempted is False
    assert unknown_compile_calls == {
        "workspace_root": workspace_root,
        "rule_ids": None,
        "kwargs": {"include_simulation": False, "intent_id": None},
    }
    assert "does not yet have an execution binding" in unknown_result.notes[0]
    assert unknown_result.to_dict()["notes"] == [
        "No supported applied remediation was executed because the selected strategy does not yet have an execution binding.",
        "base",
    ]


def test_apply_remediation_plan_returns_noop_when_plan_is_unavailable_even_with_strategy(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="unavailable-with-strategy",
        objective="base",
        plan_phase="phase",
        plan_only=True,
        current_status_compliant=True,
        plan_available=False,
        selected_rule_ids=[],
        triggering_rule_ids=[],
        unsupported_failing_rule_ids=[],
        selected_strategy=remediation_module.STATUS_ARTIFACT_REMEDIATION_STRATEGY,
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

    monkeypatch.setattr(remediation_module, "compile_remediation_plan", lambda *args, **kwargs: plan)

    result = apply_remediation_plan(workspace_root)

    assert result.execution_attempted is False
    assert result.plan_available is False
    assert result.to_dict()["notes"] == [
        "No supported applied remediation was executed because no bounded remediation plan was available for the selected rule slice.",
        "base",
    ]


def test_compile_remediation_plan_routes_explicit_status_intent(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        remediation_module,
        "compile_status_artifact_remediation_plan",
        lambda workspace_root, rule_ids, **kwargs: captured.update(
            {
                "status_workspace_root": Path(workspace_root).resolve(),
                "status_rule_ids": rule_ids,
                "status_kwargs": kwargs,
            }
        )
        or remediation_module.RemediationPlan(
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
            provenance=remediation_module.ChangeProvenanceRecord("id", "kind", [], [kwargs.get("intent_id")] if kwargs.get("intent_id") else [], [], [], []),
            simulation_available=False,
            simulation=None,
            notes=[],
        ),
    )
    monkeypatch.setattr(
        remediation_module,
        "compile_package_public_api_export_remediation_plan",
        lambda workspace_root, rule_ids, **kwargs: captured.update(
            {
                "package_workspace_root": Path(workspace_root).resolve(),
                "package_rule_ids": rule_ids,
                "package_kwargs": kwargs,
            }
        )
        or remediation_module.RemediationPlan(
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
    assert captured == {
        "status_workspace_root": workspace_root.resolve(),
        "status_rule_ids": None,
        "status_kwargs": {"include_simulation": False, "intent_id": "intent.status.refresh_artifacts"},
        "package_workspace_root": workspace_root.resolve(),
        "package_rule_ids": None,
        "package_kwargs": {"include_simulation": False},
    }


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


def test_apply_status_artifact_remediation_forwards_rule_ids_and_disable_simulation(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    captured: dict[str, object] = {}
    plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="no-plan",
        objective="noop",
        plan_phase="phase",
        plan_only=True,
        current_status_compliant=True,
        plan_available=False,
        selected_rule_ids=["status.snapshot_matches_workspace"],
        triggering_rule_ids=[],
        unsupported_failing_rule_ids=[],
        selected_strategy=None,
        triggering_evidence=[],
        current_rule_summary={"failed_rules": 0},
        affected_paths=[],
        operations=[],
        verification_contract=None,
        rollback_contract=None,
        provenance=remediation_module.ChangeProvenanceRecord("id", "kind", [], [], [], [], []),
        simulation_available=False,
        simulation=None,
        notes=["already clean"],
    )

    def fake_compile_status_artifact_remediation_plan(workspace_root, rule_ids, **kwargs):
        captured["workspace_root"] = Path(workspace_root).resolve()
        captured["rule_ids"] = rule_ids
        captured["kwargs"] = kwargs
        return plan

    monkeypatch.setattr(
        remediation_module,
        "compile_status_artifact_remediation_plan",
        fake_compile_status_artifact_remediation_plan,
    )

    result = apply_status_artifact_remediation(
        workspace_root,
        {"status.snapshot_matches_workspace"},
        intent_id="intent.status.refresh_artifacts",
    )

    assert captured == {
        "workspace_root": workspace_root.resolve(),
        "rule_ids": {"status.snapshot_matches_workspace"},
        "kwargs": {
            "include_simulation": False,
            "intent_id": "intent.status.refresh_artifacts",
        },
    }
    assert result.execution_attempted is False
    assert result.plan_available is False


def test_compile_package_public_api_export_remediation_plan_defaults_to_nonsimulated_plan(monkeypatch, tmp_path: Path) -> None:
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

    failing_rule = _rule_result(
        "knowledge_base.component_doc_python_api_symbols_valid",
        passed=False,
        domain="knowledge_base",
        category="api_surface",
    )
    monkeypatch.setattr(
        remediation_module,
        "validate_knowledge_base",
        lambda workspace_root, rule_ids: _kb_validation_result(
            failing_rule,
            compliant=False,
            workspace_root=Path(workspace_root),
        ),
    )

    plan = compile_package_public_api_export_remediation_plan(workspace_root)
    payload = plan.to_dict()

    assert payload["plan_phase"] == "bounded_source_level_remediation"
    assert payload["plan_only"] is True
    assert payload["simulation_available"] is False
    assert payload["simulation"] is None
    assert payload["current_rule_summary"] == remediation_module.summarize_rule_results([failing_rule])


def test_compile_package_public_api_export_remediation_plan_forwards_rule_ids_to_validation(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    captured: dict[str, object] = {}
    (workspace_root / "ai_docs").mkdir()
    (workspace_root / "src" / "inf_work").mkdir(parents=True)
    (workspace_root / "ai_docs" / "package_public_api_surface_20260331T000000Z.json").write_text(
        json.dumps({"interfaces": {"python_api": ["from inf_work import missing_symbol"]}}),
        encoding="utf-8",
    )
    (workspace_root / "src" / "inf_work" / "__init__.py").write_text('__all__ = []\n', encoding="utf-8")
    (workspace_root / "src" / "inf_work" / "remediation.py").write_text(
        'def missing_symbol():\n    return None\n',
        encoding="utf-8",
    )
    failing_rule = _rule_result(
        "knowledge_base.component_doc_python_api_symbols_valid",
        passed=False,
        domain="knowledge_base",
        category="api_surface",
    )

    def fake_validate_knowledge_base(workspace_root, rule_ids):
        captured["workspace_root"] = Path(workspace_root).resolve()
        captured["rule_ids"] = rule_ids
        return _kb_validation_result(failing_rule, compliant=False, workspace_root=Path(workspace_root))

    monkeypatch.setattr(remediation_module, "validate_knowledge_base", fake_validate_knowledge_base)

    plan = compile_package_public_api_export_remediation_plan(
        workspace_root,
        {"knowledge_base.component_doc_python_api_symbols_valid"},
    )

    assert plan.plan_available is True
    assert captured == {
        "workspace_root": workspace_root.resolve(),
        "rule_ids": {"knowledge_base.component_doc_python_api_symbols_valid"},
    }


def test_apply_status_artifact_remediation_validates_with_contract_rule_ids(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    captured: dict[str, object] = {"calls": 0}
    plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="status-plan",
        objective="status",
        plan_phase="phase",
        plan_only=False,
        current_status_compliant=False,
        plan_available=True,
        selected_rule_ids=["status.snapshot_matches_workspace"],
        triggering_rule_ids=["status.snapshot_matches_workspace"],
        unsupported_failing_rule_ids=[],
        selected_strategy=remediation_module.STATUS_ARTIFACT_REMEDIATION_STRATEGY,
        triggering_evidence=[],
        current_rule_summary={},
        affected_paths=[
            "ai_docs/system_status_snapshot.json",
            "SYSTEM_STATUS.md",
            "SYSTEM_SUMMARY.md",
        ],
        operations=remediation_module._build_plan_operations(str(workspace_root.resolve()), ["status.snapshot_matches_workspace"]),
        verification_contract=remediation_module.VerificationContract(
            contract_id="verify",
            required_rule_ids=["status.snapshot_matches_workspace"],
            commands=[],
            success_criteria=[],
        ),
        rollback_contract=remediation_module._build_plan_only_rollback_contract(),
        provenance=remediation_module.ChangeProvenanceRecord("id", "kind", [], [], [], [], []),
        simulation_available=False,
        simulation=None,
        notes=[],
    )

    monkeypatch.setattr(remediation_module, "compile_status_artifact_remediation_plan", lambda *args, **kwargs: plan)
    monkeypatch.setattr(
        remediation_module,
        "write_system_status_outputs",
        lambda workspace_root, canonical_json_path, derived_markdown_path, summary_path: type(
            "Snapshot",
            (),
            {
                "generated_at": "2026-04-04T03:00:00Z",
                "canonical_json_path": canonical_json_path,
                "derived_markdown_path": derived_markdown_path,
            },
        )(),
    )

    def fake_validate_system_status(workspace_root, rule_ids):
        captured["calls"] += 1
        captured["workspace_root"] = Path(workspace_root).resolve()
        captured["rule_ids"] = rule_ids
        return _status_validation_result(_rule_result("status.snapshot_matches_workspace", passed=True), compliant=True)

    monkeypatch.setattr(remediation_module, "validate_system_status", fake_validate_system_status)
    monkeypatch.setattr(
        remediation_module,
        "validate_system_summary",
        lambda workspace_root: _status_validation_result(_rule_result("status.summary_matches_workspace", passed=True), compliant=True),
    )

    result = apply_status_artifact_remediation(workspace_root, {"status.snapshot_matches_workspace"})

    assert result.applied is True
    assert captured == {
        "calls": 1,
        "workspace_root": workspace_root.resolve(),
        "rule_ids": {"status.snapshot_matches_workspace"},
    }


def test_apply_status_artifact_remediation_validates_summary_against_workspace_root(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    captured: dict[str, object] = {}
    plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="status-plan",
        objective="status",
        plan_phase="phase",
        plan_only=False,
        current_status_compliant=False,
        plan_available=True,
        selected_rule_ids=["status.snapshot_matches_workspace"],
        triggering_rule_ids=["status.snapshot_matches_workspace"],
        unsupported_failing_rule_ids=[],
        selected_strategy=remediation_module.STATUS_ARTIFACT_REMEDIATION_STRATEGY,
        triggering_evidence=[],
        current_rule_summary={},
        affected_paths=[
            "ai_docs/system_status_snapshot.json",
            "SYSTEM_STATUS.md",
            "SYSTEM_SUMMARY.md",
        ],
        operations=remediation_module._build_plan_operations(str(workspace_root.resolve()), ["status.snapshot_matches_workspace"]),
        verification_contract=remediation_module.VerificationContract(
            contract_id="verify",
            required_rule_ids=["status.snapshot_matches_workspace"],
            commands=[],
            success_criteria=[],
        ),
        rollback_contract=remediation_module._build_plan_only_rollback_contract(),
        provenance=remediation_module.ChangeProvenanceRecord("id", "kind", [], [], [], [], []),
        simulation_available=False,
        simulation=None,
        notes=[],
    )

    monkeypatch.setattr(remediation_module, "compile_status_artifact_remediation_plan", lambda *args, **kwargs: plan)
    monkeypatch.setattr(
        remediation_module,
        "write_system_status_outputs",
        lambda workspace_root, canonical_json_path, derived_markdown_path, summary_path: type(
            "Snapshot",
            (),
            {
                "generated_at": "2026-04-04T03:15:00Z",
                "canonical_json_path": canonical_json_path,
                "derived_markdown_path": derived_markdown_path,
            },
        )(),
    )
    monkeypatch.setattr(
        remediation_module,
        "validate_system_status",
        lambda workspace_root, rule_ids: _status_validation_result(_rule_result("status.snapshot_matches_workspace", passed=True), compliant=True),
    )

    def fake_validate_system_summary(workspace_root):
        captured["workspace_root"] = Path(workspace_root).resolve()
        return _status_validation_result(_rule_result("status.summary_matches_workspace", passed=True), compliant=True)

    monkeypatch.setattr(remediation_module, "validate_system_summary", fake_validate_system_summary)

    result = apply_status_artifact_remediation(workspace_root, {"status.snapshot_matches_workspace"})
    payload = result.to_dict()

    assert result.applied is True
    assert captured == {"workspace_root": workspace_root.resolve()}
    assert payload["operation_results"][2]["status"] == "completed"


def test_compile_remediation_plan_defaults_include_simulation_to_false(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    captured: dict[str, object] = {}
    status_plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="status-default",
        objective="status",
        plan_phase="plan_only_structured_remediation",
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
    )
    package_plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="package-default",
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
    )

    monkeypatch.setattr(
        remediation_module,
        "compile_status_artifact_remediation_plan",
        lambda workspace_root, rule_ids, **kwargs: captured.update(
            {
                "status_workspace_root": Path(workspace_root).resolve(),
                "status_rule_ids": rule_ids,
                "status_kwargs": kwargs,
            }
        ) or status_plan,
    )
    monkeypatch.setattr(
        remediation_module,
        "compile_package_public_api_export_remediation_plan",
        lambda workspace_root, rule_ids, **kwargs: captured.update(
            {
                "package_workspace_root": Path(workspace_root).resolve(),
                "package_rule_ids": rule_ids,
                "package_kwargs": kwargs,
            }
        ) or package_plan,
    )

    plan = compile_remediation_plan(workspace_root)

    assert plan.plan_id == "status-default"
    assert captured == {
        "status_workspace_root": workspace_root.resolve(),
        "status_rule_ids": None,
        "status_kwargs": {"include_simulation": False, "intent_id": None},
        "package_workspace_root": workspace_root.resolve(),
        "package_rule_ids": None,
        "package_kwargs": {"include_simulation": False},
    }


def test_compile_remediation_plan_treats_truthy_include_simulation_as_requested(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    captured: dict[str, object] = {}
    status_plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="status-default",
        objective="status",
        plan_phase="plan_only_structured_remediation",
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
    )
    package_plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="package-default",
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
    )

    monkeypatch.setattr(
        remediation_module,
        "compile_status_artifact_remediation_plan",
        lambda workspace_root, rule_ids, **kwargs: captured.update(
            {
                "status_workspace_root": Path(workspace_root).resolve(),
                "status_rule_ids": rule_ids,
                "status_kwargs": kwargs,
            }
        ) or status_plan,
    )
    monkeypatch.setattr(
        remediation_module,
        "compile_package_public_api_export_remediation_plan",
        lambda workspace_root, rule_ids, **kwargs: captured.update(
            {
                "package_workspace_root": Path(workspace_root).resolve(),
                "package_rule_ids": rule_ids,
                "package_kwargs": kwargs,
            }
        ) or package_plan,
    )

    plan = compile_remediation_plan(workspace_root, include_simulation=1)

    assert plan.plan_id == "status-default"
    assert captured == {
        "status_workspace_root": workspace_root.resolve(),
        "status_rule_ids": None,
        "status_kwargs": {"include_simulation": True, "intent_id": None},
        "package_workspace_root": workspace_root.resolve(),
        "package_rule_ids": None,
        "package_kwargs": {"include_simulation": True},
    }


def test_apply_package_public_api_export_remediation_writes_updated_text_with_utf8(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    (workspace_root / "src" / "inf_work").mkdir(parents=True)
    target_path = workspace_root / "src" / "inf_work" / "__init__.py"
    target_path.write_text('__all__ = []\n', encoding="utf-8")
    captured: dict[str, object] = {}
    original_write_text = Path.write_text
    plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="package-plan",
        objective="package",
        plan_phase="bounded_source_level_remediation",
        plan_only=False,
        current_status_compliant=False,
        plan_available=True,
        selected_rule_ids=["knowledge_base.component_doc_python_api_symbols_valid"],
        triggering_rule_ids=["knowledge_base.component_doc_python_api_symbols_valid"],
        unsupported_failing_rule_ids=[],
        selected_strategy=remediation_module.PACKAGE_EXPORT_SYNC_REMEDIATION_STRATEGY,
        triggering_evidence=[],
        current_rule_summary={},
        affected_paths=["src/inf_work/__init__.py"],
        operations=remediation_module._build_package_export_plan_operations(
            str(workspace_root.resolve()),
            ["knowledge_base.component_doc_python_api_symbols_valid"],
        ),
        verification_contract=remediation_module._build_package_export_verification_contract(
            str(workspace_root.resolve()),
            ["knowledge_base.component_doc_python_api_symbols_valid"],
        ),
        rollback_contract=remediation_module._build_python_source_rollback_contract(),
        provenance=remediation_module.ChangeProvenanceRecord("id", "kind", [], [], [], [], []),
        simulation_available=False,
        simulation=None,
        notes=[],
    )

    monkeypatch.setattr(remediation_module, "compile_package_public_api_export_remediation_plan", lambda *args, **kwargs: plan)
    monkeypatch.setattr(
        remediation_module,
        "_build_package_export_sync_state",
        lambda root_path: {
            "updated_text": '__all__ = [\n\t"symbol",\n]\n',
            "module_symbol_additions": {"remediation": ["symbol"]},
            "missing_all_symbols": ["symbol"],
        },
    )
    monkeypatch.setattr(
        remediation_module,
        "validate_knowledge_base",
        lambda workspace_root, rule_ids: _kb_validation_result(
            _rule_result(
                "knowledge_base.component_doc_python_api_symbols_valid",
                passed=True,
                domain="knowledge_base",
                category="api_surface",
            ),
            compliant=True,
            workspace_root=Path(workspace_root),
        ),
    )

    def capturing_write_text(self: Path, text: str, encoding: str | None = None, **kwargs):
        if self == target_path:
            captured["path"] = self
            captured["text"] = text
            captured["encoding"] = encoding
        return original_write_text(self, text, encoding=encoding, **kwargs)

    monkeypatch.setattr(Path, "write_text", capturing_write_text)

    result = apply_package_public_api_export_remediation(
        workspace_root,
        {"knowledge_base.component_doc_python_api_symbols_valid"},
    )

    assert result.applied is True
    assert captured == {
        "path": target_path,
        "text": '__all__ = [\n\t"symbol",\n]\n',
        "encoding": "utf-8",
    }


def test_apply_package_public_api_export_remediation_validates_with_contract_rule_ids(monkeypatch, tmp_path: Path) -> None:
    workspace_root = tmp_path
    (workspace_root / "src" / "inf_work").mkdir(parents=True)
    (workspace_root / "src" / "inf_work" / "__init__.py").write_text('__all__ = []\n', encoding="utf-8")
    captured: dict[str, object] = {}
    plan = remediation_module.RemediationPlan(
        workspace_root=str(workspace_root.resolve()),
        plan_id="package-plan",
        objective="package",
        plan_phase="bounded_source_level_remediation",
        plan_only=False,
        current_status_compliant=False,
        plan_available=True,
        selected_rule_ids=["knowledge_base.component_doc_python_api_symbols_valid"],
        triggering_rule_ids=["knowledge_base.component_doc_python_api_symbols_valid"],
        unsupported_failing_rule_ids=[],
        selected_strategy=remediation_module.PACKAGE_EXPORT_SYNC_REMEDIATION_STRATEGY,
        triggering_evidence=[],
        current_rule_summary={},
        affected_paths=["src/inf_work/__init__.py"],
        operations=remediation_module._build_package_export_plan_operations(
            str(workspace_root.resolve()),
            ["knowledge_base.component_doc_python_api_symbols_valid"],
        ),
        verification_contract=remediation_module.VerificationContract(
            contract_id="verify",
            required_rule_ids=["knowledge_base.component_doc_python_api_symbols_valid"],
            commands=[],
            success_criteria=[],
        ),
        rollback_contract=remediation_module._build_python_source_rollback_contract(),
        provenance=remediation_module.ChangeProvenanceRecord("id", "kind", [], [], [], [], []),
        simulation_available=False,
        simulation=None,
        notes=[],
    )

    monkeypatch.setattr(remediation_module, "compile_package_public_api_export_remediation_plan", lambda *args, **kwargs: plan)
    monkeypatch.setattr(
        remediation_module,
        "_build_package_export_sync_state",
        lambda root_path: {
            "updated_text": '__all__ = [\n\t"symbol",\n]\n',
            "module_symbol_additions": {"remediation": ["symbol"]},
            "missing_all_symbols": ["symbol"],
        },
    )

    def fake_validate_knowledge_base(workspace_root, rule_ids):
        captured["workspace_root"] = Path(workspace_root).resolve()
        captured["rule_ids"] = rule_ids
        return _kb_validation_result(
            _rule_result(
                "knowledge_base.component_doc_python_api_symbols_valid",
                passed=True,
                domain="knowledge_base",
                category="api_surface",
            ),
            compliant=True,
            workspace_root=Path(workspace_root),
        )

    monkeypatch.setattr(remediation_module, "validate_knowledge_base", fake_validate_knowledge_base)

    result = apply_package_public_api_export_remediation(
        workspace_root,
        {"knowledge_base.component_doc_python_api_symbols_valid"},
    )

    assert result.applied is True
    assert captured == {
        "workspace_root": workspace_root.resolve(),
        "rule_ids": {"knowledge_base.component_doc_python_api_symbols_valid"},
    }