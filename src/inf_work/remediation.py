from __future__ import annotations

import difflib
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .rules import RuleResult, summarize_rule_results
from .system_status import (
    build_system_status_snapshot,
    render_system_status_markdown,
    render_system_summary_markdown,
    validate_system_status,
)


_DEFAULT_STATUS_JSON_PATH = "ai_docs/system_status_snapshot.json"
_DEFAULT_STATUS_MARKDOWN_PATH = "SYSTEM_STATUS.md"
_DEFAULT_STATUS_SUMMARY_PATH = "SYSTEM_SUMMARY.md"

SUPPORTED_STATUS_ARTIFACT_TRIGGER_RULE_IDS = (
    "status.snapshot_matches_workspace",
    "status.markdown_matches_snapshot",
    "status.summary_matches_workspace",
)


@dataclass(frozen=True)
class RemediationStrategy:
    strategy_id: str
    description: str
    supported_rule_ids: list[str]
    priority: int
    allowed_operation_types: list[str]
    verification_profile: str
    rollback_profile: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlanOperation:
    operation_id: str
    operation_type: str
    target_paths: list[str]
    description: str
    command: str
    command_arguments: list[str]
    evidence_rule_ids: list[str]
    predicted_outcome: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerificationContract:
    contract_id: str
    required_rule_ids: list[str]
    commands: list[str]
    success_criteria: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RollbackContract:
    contract_id: str
    strategy: str
    steps: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChangeProvenanceRecord:
    record_id: str
    trigger_kind: str
    trigger_rule_ids: list[str]
    supporting_rule_ids: list[str]
    source_artifact_paths: list[str]
    derived_from_components: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RemediationPlan:
    workspace_root: str
    plan_id: str
    objective: str
    plan_phase: str
    plan_only: bool
    current_status_compliant: bool
    plan_available: bool
    selected_rule_ids: list[str]
    triggering_rule_ids: list[str]
    unsupported_failing_rule_ids: list[str]
    selected_strategy: RemediationStrategy | None
    triggering_evidence: list[dict[str, Any]]
    current_rule_summary: dict[str, Any]
    affected_paths: list[str]
    operations: list[PlanOperation]
    verification_contract: VerificationContract | None
    rollback_contract: RollbackContract | None
    provenance: ChangeProvenanceRecord
    simulation_available: bool
    simulation: dict[str, Any] | None
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_root": self.workspace_root,
            "plan_id": self.plan_id,
            "objective": self.objective,
            "plan_phase": self.plan_phase,
            "plan_only": self.plan_only,
            "current_status_compliant": self.current_status_compliant,
            "plan_available": self.plan_available,
            "selected_rule_ids": self.selected_rule_ids,
            "triggering_rule_ids": self.triggering_rule_ids,
            "unsupported_failing_rule_ids": self.unsupported_failing_rule_ids,
            "selected_strategy": self.selected_strategy.to_dict() if self.selected_strategy else None,
            "triggering_evidence": self.triggering_evidence,
            "current_rule_summary": self.current_rule_summary,
            "affected_paths": self.affected_paths,
            "operations": [operation.to_dict() for operation in self.operations],
            "verification_contract": self.verification_contract.to_dict() if self.verification_contract else None,
            "rollback_contract": self.rollback_contract.to_dict() if self.rollback_contract else None,
            "provenance": self.provenance.to_dict(),
            "simulation_available": self.simulation_available,
            "simulation": self.simulation,
            "notes": self.notes,
        }


def _build_status_artifact_strategy() -> RemediationStrategy:
    return RemediationStrategy(
        strategy_id="strategy_status_artifact_regeneration_plan",
        description="Compile a deterministic plan that regenerates canonical status artifacts and then re-validates the status surfaces.",
        supported_rule_ids=list(SUPPORTED_STATUS_ARTIFACT_TRIGGER_RULE_IDS),
        priority=1,
        allowed_operation_types=["regenerate_artifact", "run_validation_profile"],
        verification_profile="status_artifact_drift",
        rollback_profile="plan_only_noop",
    )


STATUS_ARTIFACT_REMEDIATION_STRATEGY = _build_status_artifact_strategy()


def list_supported_remediation_strategies() -> list[RemediationStrategy]:
    return [STATUS_ARTIFACT_REMEDIATION_STRATEGY]


def _operation_command_string(command: str, command_arguments: list[str]) -> str:
    return " ".join([command, *command_arguments])


def _build_plan_operations(workspace_root: str, evidence_rule_ids: list[str]) -> list[PlanOperation]:
    regenerate_arguments = [
        "-m",
        "inf_work",
        "status",
        workspace_root,
        "--json-output",
        _DEFAULT_STATUS_JSON_PATH,
        "--markdown-output",
        _DEFAULT_STATUS_MARKDOWN_PATH,
    ]
    status_check_arguments = ["-m", "inf_work", "status-check", workspace_root, "--pretty"]
    summary_check_arguments = ["-m", "inf_work", "summary-check", workspace_root, "--pretty"]
    return [
        PlanOperation(
            operation_id="regenerate_status_outputs",
            operation_type="regenerate_artifact",
            target_paths=[
                _DEFAULT_STATUS_JSON_PATH,
                _DEFAULT_STATUS_MARKDOWN_PATH,
                _DEFAULT_STATUS_SUMMARY_PATH,
            ],
            description="Regenerate the canonical status snapshot plus both derived markdown artifacts from the governed workspace state.",
            command="python",
            command_arguments=regenerate_arguments,
            evidence_rule_ids=evidence_rule_ids,
            predicted_outcome="All governed status artifacts are regenerated from current workspace inputs.",
        ),
        PlanOperation(
            operation_id="validate_status_artifacts",
            operation_type="run_validation_profile",
            target_paths=[_DEFAULT_STATUS_JSON_PATH, _DEFAULT_STATUS_MARKDOWN_PATH],
            description="Validate the canonical status snapshot and the derived status markdown after regeneration.",
            command="python",
            command_arguments=status_check_arguments,
            evidence_rule_ids=evidence_rule_ids,
            predicted_outcome="The supported status drift rules pass for the canonical snapshot and status markdown.",
        ),
        PlanOperation(
            operation_id="validate_system_summary",
            operation_type="run_validation_profile",
            target_paths=[_DEFAULT_STATUS_SUMMARY_PATH],
            description="Validate the derived summary artifact against the current governed workspace state.",
            command="python",
            command_arguments=summary_check_arguments,
            evidence_rule_ids=evidence_rule_ids,
            predicted_outcome="The derived summary artifact matches the current workspace state.",
        ),
    ]


def _build_verification_contract(workspace_root: str, required_rule_ids: list[str]) -> VerificationContract:
    status_check_command = _operation_command_string("python", ["-m", "inf_work", "status-check", workspace_root, "--pretty"])
    summary_check_command = _operation_command_string("python", ["-m", "inf_work", "summary-check", workspace_root, "--pretty"])
    return VerificationContract(
        contract_id="verify_status_artifact_regeneration_plan",
        required_rule_ids=required_rule_ids,
        commands=[status_check_command, summary_check_command],
        success_criteria=[
            "`status-check` reports no failing status-artifact drift rules.",
            "`summary-check` reports no failing summary-drift rules.",
        ],
    )


def _build_plan_only_rollback_contract() -> RollbackContract:
    return RollbackContract(
        contract_id="rollback_plan_only_noop",
        strategy="no_workspace_mutation",
        steps=[
            "No rollback action is required during phase-1 planning because the workflow compiles a plan without mutating workspace files.",
            "If an operator executes the plan manually, re-run the same governed regeneration command from version-controlled sources to restore deterministic artifacts.",
        ],
    )


def _build_provenance_record(trigger_rule_ids: list[str], supporting_rule_ids: list[str]) -> ChangeProvenanceRecord:
    return ChangeProvenanceRecord(
        record_id="provenance_status_artifact_regeneration_plan",
        trigger_kind="status_rule_failure",
        trigger_rule_ids=trigger_rule_ids,
        supporting_rule_ids=supporting_rule_ids,
        source_artifact_paths=[
            _DEFAULT_STATUS_JSON_PATH,
            _DEFAULT_STATUS_MARKDOWN_PATH,
            _DEFAULT_STATUS_SUMMARY_PATH,
        ],
        derived_from_components=[
            "system_status_generator",
            "unified_cli_entry_point",
            "remediation_plan_compiler",
        ],
    )


def _sha256_text(value: str | None) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_optional_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _line_preview(value: str | None, *, limit: int = 12) -> list[str]:
    if value is None:
        return []
    return value.splitlines()[:limit]


def _serialize_snapshot(snapshot: Any) -> str:
    return json.dumps(snapshot.to_dict(), indent=2)


def _build_artifact_change(root_path: Path, target_path: str, simulated_text: str) -> dict[str, Any]:
    current_text = _read_optional_text(root_path / target_path)
    current_exists = current_text is not None
    current_lines = [] if current_text is None else current_text.splitlines()
    simulated_lines = simulated_text.splitlines()
    diff_lines = list(
        difflib.unified_diff(
            current_lines,
            simulated_lines,
            fromfile=f"a/{target_path}",
            tofile=f"b/{target_path}",
            lineterm="",
        )
    )
    preview_limit = 120
    content_changed = current_text != simulated_text
    if not current_exists:
        change_type = "create"
    elif content_changed:
        change_type = "update"
    else:
        change_type = "noop"
    return {
        "target_path": target_path,
        "change_type": change_type,
        "current_exists": current_exists,
        "simulated_exists": True,
        "content_changed": content_changed,
        "current_sha256": _sha256_text(current_text),
        "simulated_sha256": _sha256_text(simulated_text),
        "current_line_count": len(current_lines),
        "simulated_line_count": len(simulated_lines),
        "current_excerpt": _line_preview(current_text),
        "simulated_excerpt": _line_preview(simulated_text),
        "diff_line_count": len(diff_lines),
        "diff_preview": diff_lines[:preview_limit],
        "diff_truncated": len(diff_lines) > preview_limit,
    }


def _build_predicted_rule_outcomes(rule_results: list[RuleResult]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    predicted_rule_results: list[RuleResult] = []
    predicted_rule_outcomes: list[dict[str, Any]] = []
    for rule_result in sorted(rule_results, key=lambda item: item.rule_id):
        if rule_result.rule_id in SUPPORTED_STATUS_ARTIFACT_TRIGGER_RULE_IDS or rule_result.rule_id == "status.artifacts_exist":
            predicted_passed = True
            rationale = "Simulated regeneration restores canonical artifact presence and content for this rule."
        else:
            predicted_passed = rule_result.passed
            rationale = "Dry-run simulation does not alter this rule surface, so the current result is preserved."
        predicted_rule_results.append(
            RuleResult(
                rule_id=rule_result.rule_id,
                domain=rule_result.domain,
                category=rule_result.category,
                severity=rule_result.severity,
                description=rule_result.description,
                passed=predicted_passed,
                findings=[] if predicted_passed else rule_result.findings,
            )
        )
        if predicted_passed and not rule_result.passed:
            predicted_effect = "would_pass"
        elif predicted_passed == rule_result.passed:
            predicted_effect = "unchanged"
        else:
            predicted_effect = "would_fail"
        predicted_rule_outcomes.append(
            {
                "rule_id": rule_result.rule_id,
                "current_passed": rule_result.passed,
                "predicted_passed": predicted_passed,
                "predicted_effect": predicted_effect,
                "rationale": rationale,
            }
        )
    return predicted_rule_outcomes, summarize_rule_results(predicted_rule_results)


def _build_dry_run_simulation(root_path: Path, rule_results: list[RuleResult]) -> dict[str, Any]:
    simulated_snapshot = build_system_status_snapshot(
        root_path,
        canonical_json_path=_DEFAULT_STATUS_JSON_PATH,
        derived_markdown_path=_DEFAULT_STATUS_MARKDOWN_PATH,
    )
    component_index = json.loads((root_path / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    kb_index = json.loads((root_path / "knowledge_base" / "kb_index.json").read_text(encoding="utf-8"))
    simulated_outputs = {
        _DEFAULT_STATUS_JSON_PATH: _serialize_snapshot(simulated_snapshot),
        _DEFAULT_STATUS_MARKDOWN_PATH: render_system_status_markdown(simulated_snapshot),
        _DEFAULT_STATUS_SUMMARY_PATH: render_system_summary_markdown(
            simulated_snapshot,
            component_index=component_index,
            kb_index=kb_index,
        ),
    }
    artifact_changes = [
        _build_artifact_change(root_path, target_path, simulated_text)
        for target_path, simulated_text in simulated_outputs.items()
    ]
    predicted_rule_outcomes, predicted_rule_summary = _build_predicted_rule_outcomes(rule_results)
    changed_paths = [entry["target_path"] for entry in artifact_changes if entry["content_changed"]]
    unchanged_paths = [entry["target_path"] for entry in artifact_changes if not entry["content_changed"]]
    return {
        "simulation_id": "dry_run_status_artifact_regeneration",
        "simulation_phase": "dry_run_structured_remediation",
        "workspace_mutation": False,
        "artifact_changes": artifact_changes,
        "changed_paths": changed_paths,
        "unchanged_paths": unchanged_paths,
        "predicted_rule_outcomes": predicted_rule_outcomes,
        "predicted_rule_summary": predicted_rule_summary,
        "notes": [
            "Dry-run simulation reuses the canonical status builders and renderers without writing files.",
            "Diff previews are deterministic excerpts from the simulated post-state for the governed status artifacts.",
        ],
    }


def _sorted_failed_rule_ids(rule_results: list[RuleResult]) -> list[str]:
    return sorted({rule_result.rule_id for rule_result in rule_results if not rule_result.passed})


def compile_status_artifact_remediation_plan(
    workspace_root: str | Path,
    rule_ids: set[str] | None = None,
    *,
    include_simulation: bool = False,
) -> RemediationPlan:
    root_path = Path(workspace_root).resolve()
    validation_result = validate_system_status(root_path, rule_ids)
    failed_rule_ids = _sorted_failed_rule_ids(validation_result.rule_results)
    supported_rule_ids = [rule_id for rule_id in failed_rule_ids if rule_id in SUPPORTED_STATUS_ARTIFACT_TRIGGER_RULE_IDS]
    unsupported_rule_ids = [rule_id for rule_id in failed_rule_ids if rule_id not in SUPPORTED_STATUS_ARTIFACT_TRIGGER_RULE_IDS]
    selected_rule_ids = sorted(rule_ids) if rule_ids else []
    triggering_evidence = [
        rule_result.to_dict()
        for rule_result in sorted(validation_result.rule_results, key=lambda item: item.rule_id)
        if not rule_result.passed and rule_result.rule_id in supported_rule_ids
    ]
    current_rule_summary = summarize_rule_results(validation_result.rule_results)

    if supported_rule_ids:
        operations = _build_plan_operations(str(root_path), supported_rule_ids)
        verification_contract = _build_verification_contract(str(root_path), supported_rule_ids)
        rollback_contract = _build_plan_only_rollback_contract()
        simulation = _build_dry_run_simulation(root_path, validation_result.rule_results) if include_simulation else None
        return RemediationPlan(
            workspace_root=str(root_path),
            plan_id="remediation_plan_status_artifact_regeneration",
            objective="Regenerate stale governed status artifacts and verify that the current workspace state is reflected across the canonical snapshot and derived markdown outputs.",
            plan_phase="dry_run_structured_remediation" if include_simulation else "plan_only_structured_remediation",
            plan_only=not include_simulation,
            current_status_compliant=validation_result.compliant,
            plan_available=True,
            selected_rule_ids=selected_rule_ids,
            triggering_rule_ids=supported_rule_ids,
            unsupported_failing_rule_ids=unsupported_rule_ids,
            selected_strategy=STATUS_ARTIFACT_REMEDIATION_STRATEGY,
            triggering_evidence=triggering_evidence,
            current_rule_summary=current_rule_summary,
            affected_paths=[
                _DEFAULT_STATUS_JSON_PATH,
                _DEFAULT_STATUS_MARKDOWN_PATH,
                _DEFAULT_STATUS_SUMMARY_PATH,
            ],
            operations=operations,
            verification_contract=verification_contract,
            rollback_contract=rollback_contract,
            provenance=_build_provenance_record(supported_rule_ids, unsupported_rule_ids),
            simulation_available=simulation is not None,
            simulation=simulation,
            notes=[
                "The remediation compiler remains non-mutating and bounded to governed status artifacts.",
                "Enable dry-run simulation to preview deterministic post-state diffs before any manual operator action.",
                "The current slice intentionally excludes arbitrary source edits and dependency changes.",
            ],
        )

    notes = [
        "No supported phase-1 status-artifact drift failures are active, so no remediation plan is compiled.",
    ]
    if unsupported_rule_ids:
        notes.append(
            "Failing rules remain outside the supported phase-1 remediation slice and must be handled by existing validator-specific workflows."
        )
    else:
        notes.append("The canonical status artifacts already match the current governed workspace state.")
    return RemediationPlan(
        workspace_root=str(root_path),
        plan_id="remediation_plan_status_artifact_regeneration",
        objective="Determine whether the bounded status-artifact remediation slice should compile a deterministic plan.",
        plan_phase="dry_run_structured_remediation" if include_simulation else "plan_only_structured_remediation",
        plan_only=not include_simulation,
        current_status_compliant=validation_result.compliant,
        plan_available=False,
        selected_rule_ids=selected_rule_ids,
        triggering_rule_ids=[],
        unsupported_failing_rule_ids=unsupported_rule_ids,
        selected_strategy=None,
        triggering_evidence=[],
        current_rule_summary=current_rule_summary,
        affected_paths=[
            _DEFAULT_STATUS_JSON_PATH,
            _DEFAULT_STATUS_MARKDOWN_PATH,
            _DEFAULT_STATUS_SUMMARY_PATH,
        ],
        operations=[],
        verification_contract=None,
        rollback_contract=_build_plan_only_rollback_contract(),
        provenance=_build_provenance_record([], unsupported_rule_ids),
        simulation_available=False,
        simulation=None,
        notes=notes,
    )