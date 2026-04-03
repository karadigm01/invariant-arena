from __future__ import annotations

import ast
import difflib
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .kb_integrity import validate_knowledge_base
from .rules import RuleResult, summarize_rule_results
from .system_status import (
    build_system_status_snapshot,
    render_system_status_markdown,
    render_system_summary_markdown,
    validate_system_summary,
    validate_system_status,
    write_system_status_outputs,
)


_DEFAULT_STATUS_JSON_PATH = "ai_docs/system_status_snapshot.json"
_DEFAULT_STATUS_MARKDOWN_PATH = "SYSTEM_STATUS.md"
_DEFAULT_STATUS_SUMMARY_PATH = "SYSTEM_SUMMARY.md"
_PACKAGE_PUBLIC_API_DOC_PATH = "ai_docs/package_public_api_surface_20260331T000000Z.json"
_PACKAGE_PUBLIC_API_MODULE_PATH = "src/inf_work/__init__.py"
_STATUS_REFRESH_INTENT_ID = "intent.status.refresh_artifacts"

SUPPORTED_STATUS_ARTIFACT_TRIGGER_RULE_IDS = (
    "status.snapshot_matches_workspace",
    "status.markdown_matches_snapshot",
    "status.summary_matches_workspace",
)
SUPPORTED_SOURCE_LEVEL_TRIGGER_RULE_IDS = (
    "knowledge_base.component_doc_python_api_symbols_valid",
)
SUPPORTED_GOVERNED_INTENT_IDS = (
    _STATUS_REFRESH_INTENT_ID,
)


@dataclass(frozen=True)
class RemediationStrategy:
    strategy_id: str
    description: str
    supported_rule_ids: list[str]
    supported_intent_ids: list[str]
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
    governed_intent_ids: list[str]
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


@dataclass(frozen=True)
class OperationExecutionResult:
    operation_id: str
    operation_type: str
    target_paths: list[str]
    status: str
    mutation_performed: bool
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RemediationExecutionResult:
    workspace_root: str
    plan_id: str
    execution_phase: str
    execution_attempted: bool
    plan_available: bool
    applied: bool
    compliant: bool
    rollback_performed: bool
    rollback_summary: dict[str, Any]
    triggering_rule_ids: list[str]
    unsupported_failing_rule_ids: list[str]
    operation_results: list[OperationExecutionResult]
    status_validation: dict[str, Any] | None
    summary_validation: dict[str, Any] | None
    knowledge_base_validation: dict[str, Any] | None
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_root": self.workspace_root,
            "plan_id": self.plan_id,
            "execution_phase": self.execution_phase,
            "execution_attempted": self.execution_attempted,
            "plan_available": self.plan_available,
            "applied": self.applied,
            "compliant": self.compliant,
            "rollback_performed": self.rollback_performed,
            "rollback_summary": self.rollback_summary,
            "triggering_rule_ids": self.triggering_rule_ids,
            "unsupported_failing_rule_ids": self.unsupported_failing_rule_ids,
            "operation_results": [operation.to_dict() for operation in self.operation_results],
            "status_validation": self.status_validation,
            "summary_validation": self.summary_validation,
            "knowledge_base_validation": self.knowledge_base_validation,
            "notes": self.notes,
        }


def _build_status_artifact_strategy() -> RemediationStrategy:
    return RemediationStrategy(
        strategy_id="strategy_status_artifact_regeneration_plan",
        description="Compile a deterministic plan that regenerates canonical status artifacts and then re-validates the status surfaces.",
        supported_rule_ids=list(SUPPORTED_STATUS_ARTIFACT_TRIGGER_RULE_IDS),
        supported_intent_ids=[_STATUS_REFRESH_INTENT_ID],
        priority=1,
        allowed_operation_types=["regenerate_artifact", "run_validation_profile"],
        verification_profile="status_artifact_drift",
        rollback_profile="plan_only_noop",
    )


STATUS_ARTIFACT_REMEDIATION_STRATEGY = _build_status_artifact_strategy()


def _build_package_export_sync_strategy() -> RemediationStrategy:
    return RemediationStrategy(
        strategy_id="strategy_package_public_api_export_sync",
        description="Synchronize the governed `inf_work` package export surface in `src/inf_work/__init__.py` so documented package imports resolve to explicit re-exports.",
        supported_rule_ids=list(SUPPORTED_SOURCE_LEVEL_TRIGGER_RULE_IDS),
        supported_intent_ids=[],
        priority=2,
        allowed_operation_types=["rewrite_python_source", "run_validation_profile"],
        verification_profile="package_public_api_export_sync",
        rollback_profile="python_source_pre_state_restore",
    )


PACKAGE_EXPORT_SYNC_REMEDIATION_STRATEGY = _build_package_export_sync_strategy()


def list_supported_remediation_strategies() -> list[RemediationStrategy]:
    return [
        STATUS_ARTIFACT_REMEDIATION_STRATEGY,
        PACKAGE_EXPORT_SYNC_REMEDIATION_STRATEGY,
    ]


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


def _build_provenance_record(
    trigger_rule_ids: list[str],
    supporting_rule_ids: list[str],
    *,
    governed_intent_ids: list[str] | None = None,
) -> ChangeProvenanceRecord:
    return ChangeProvenanceRecord(
        record_id="provenance_status_artifact_regeneration_plan",
        trigger_kind="explicit_governed_intent" if governed_intent_ids else "status_rule_failure",
        trigger_rule_ids=trigger_rule_ids,
        governed_intent_ids=list(governed_intent_ids or []),
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


def _build_package_export_provenance_record(trigger_rule_ids: list[str], supporting_rule_ids: list[str]) -> ChangeProvenanceRecord:
    return ChangeProvenanceRecord(
        record_id="provenance_package_public_api_export_sync",
        trigger_kind="knowledge_base_rule_failure",
        trigger_rule_ids=trigger_rule_ids,
        governed_intent_ids=[],
        supporting_rule_ids=supporting_rule_ids,
        source_artifact_paths=[
            _PACKAGE_PUBLIC_API_DOC_PATH,
            _PACKAGE_PUBLIC_API_MODULE_PATH,
        ],
        derived_from_components=[
            "package_public_api_surface",
            "remediation_plan_compiler",
            "unified_cli_entry_point",
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


def _extract_module_export_surface(module_path: Path) -> tuple[set[str], set[str] | None]:
    module_ast = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    exported_names: set[str] = set()
    explicit_all: set[str] | None = None

    for node in module_ast.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            exported_names.add(node.name)
            continue

        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                exported_names.add(alias.asname or alias.name.split(".")[-1])
            continue

        if isinstance(node, ast.Assign):
            target_names = {
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            }
            exported_names.update(name for name in target_names if name != "__all__")
            if "__all__" in target_names:
                try:
                    literal_value = ast.literal_eval(node.value)
                except (ValueError, SyntaxError):
                    literal_value = None
                if isinstance(literal_value, (list, tuple)) and all(isinstance(value, str) for value in literal_value):
                    explicit_all = set(literal_value)

    return exported_names, explicit_all


def _extract_package_import_symbols(entry: str) -> set[str]:
    normalized_entry = entry.strip()
    prefix = "from inf_work import "
    if not normalized_entry.startswith(prefix):
        return set()
    return {
        part.strip()
        for part in normalized_entry[len(prefix):].split(",")
        if part.strip()
    }


def _group_missing_symbols_by_provider(root_path: Path, missing_symbols: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    provider_index: dict[str, set[str]] = {}
    package_root = root_path / "src" / "inf_work"
    for module_path in sorted(package_root.glob("*.py")):
        if module_path.name == "__init__.py":
            continue
        exported_names, _ = _extract_module_export_surface(module_path)
        module_name = module_path.stem
        for symbol in exported_names:
            provider_index.setdefault(symbol, set()).add(module_name)

    module_to_symbols: dict[str, list[str]] = {}
    unsupported_symbols: list[str] = []
    for symbol in sorted(missing_symbols):
        providers = sorted(provider_index.get(symbol, set()))
        if len(providers) != 1:
            unsupported_symbols.append(symbol)
            continue
        module_to_symbols.setdefault(providers[0], []).append(symbol)

    return module_to_symbols, unsupported_symbols


def _append_grouped_import_symbols(current_text: str, module_name: str, symbols: list[str]) -> str:
    lines = current_text.splitlines()
    header = f"from .{module_name} import ("
    for index, line in enumerate(lines):
        if line == header:
            end_index = index + 1
            existing_symbols: list[str] = []
            while end_index < len(lines) and lines[end_index].strip() != ")":
                stripped_line = lines[end_index].strip().rstrip(",")
                if stripped_line:
                    existing_symbols.append(stripped_line)
                end_index += 1
            updated_symbols = existing_symbols + [symbol for symbol in symbols if symbol not in existing_symbols]
            replacement_block = [header, *[f"\t{symbol}," for symbol in updated_symbols], ")"]
            return "\n".join([*lines[:index], *replacement_block, *lines[end_index + 1 :]])

    insert_index = next(index for index, line in enumerate(lines) if line.startswith("__all__ = ["))
    new_block = [header, *[f"\t{symbol}," for symbol in symbols], ")", ""]
    return "\n".join([*lines[:insert_index], *new_block, *lines[insert_index:]])


def _append_all_entries(current_text: str, symbols: list[str]) -> str:
    lines = current_text.splitlines()
    start_index = next(index for index, line in enumerate(lines) if line.startswith("__all__ = ["))
    end_index = start_index + 1
    existing_symbols: list[str] = []
    while end_index < len(lines) and lines[end_index].strip() != "]":
        stripped_line = lines[end_index].strip().rstrip(",")
        if stripped_line:
            existing_symbols.append(stripped_line.strip('"'))
        end_index += 1
    updated_symbols = existing_symbols + [symbol for symbol in symbols if symbol not in existing_symbols]
    replacement_block = ["__all__ = [", *[f'\t"{symbol}",' for symbol in updated_symbols], "]"]
    return "\n".join([*lines[:start_index], *replacement_block, *lines[end_index + 1 :]])


def _build_package_export_sync_state(root_path: Path) -> dict[str, Any]:
    documentation_payload = json.loads((root_path / _PACKAGE_PUBLIC_API_DOC_PATH).read_text(encoding="utf-8"))
    python_api_entries = documentation_payload.get("interfaces", {}).get("python_api", [])
    package_import_entry = next(
        (entry for entry in python_api_entries if isinstance(entry, str) and entry.strip().startswith("from inf_work import ")),
        None,
    )
    documented_symbols = sorted(_extract_package_import_symbols(package_import_entry or ""))

    module_path = root_path / _PACKAGE_PUBLIC_API_MODULE_PATH
    current_text = module_path.read_text(encoding="utf-8")
    exported_names, explicit_all = _extract_module_export_surface(module_path)
    current_expected_symbols = explicit_all if explicit_all is not None else exported_names
    missing_documented_symbols = sorted(symbol for symbol in documented_symbols if symbol not in current_expected_symbols)
    missing_import_symbols = sorted(symbol for symbol in documented_symbols if symbol not in exported_names)
    missing_all_symbols = sorted(
        symbol
        for symbol in documented_symbols
        if explicit_all is not None and symbol not in explicit_all
    )
    module_symbol_additions, unsupported_symbols = _group_missing_symbols_by_provider(root_path, missing_import_symbols)

    updated_text = current_text
    if not unsupported_symbols and (missing_import_symbols or missing_all_symbols):
        for module_name, symbols in sorted(module_symbol_additions.items()):
            updated_text = _append_grouped_import_symbols(updated_text, module_name, symbols)
        if missing_import_symbols or missing_all_symbols:
            updated_text = _append_all_entries(
                updated_text,
                sorted(set(missing_import_symbols) | set(missing_all_symbols)),
            )
        updated_text = f"{updated_text.rstrip()}\n"

    return {
        "documentation_path": _PACKAGE_PUBLIC_API_DOC_PATH,
        "module_path": _PACKAGE_PUBLIC_API_MODULE_PATH,
        "package_import_entry": package_import_entry,
        "documented_symbols": documented_symbols,
        "exported_names": sorted(exported_names),
        "explicit_all": sorted(explicit_all) if explicit_all is not None else None,
        "missing_documented_symbols": missing_documented_symbols,
        "missing_import_symbols": missing_import_symbols,
        "missing_all_symbols": missing_all_symbols,
        "module_symbol_additions": module_symbol_additions,
        "unsupported_symbols": unsupported_symbols,
        "updated_text": updated_text,
    }


def _build_package_export_plan_operations(workspace_root: str, trigger_rule_ids: list[str]) -> list[PlanOperation]:
    verify_arguments = [
        "-m",
        "inf_work",
        "kb",
        workspace_root,
        "--pretty",
        "--rule-id",
        "knowledge_base.component_doc_python_api_symbols_valid",
    ]
    return [
        PlanOperation(
            operation_id="sync_package_public_api_exports",
            operation_type="rewrite_python_source",
            target_paths=[_PACKAGE_PUBLIC_API_MODULE_PATH],
            description="Synchronize the governed `inf_work` package export surface so documented package imports resolve to explicit imports plus `__all__` entries.",
            command="python",
            command_arguments=[
                "-m",
                "inf_work",
                "remediation-plan",
                workspace_root,
                "--pretty",
                "--apply",
                "--rule-id",
                "knowledge_base.component_doc_python_api_symbols_valid",
            ],
            evidence_rule_ids=trigger_rule_ids,
            predicted_outcome="The governed package public API documentation matches the explicit `inf_work` re-export surface.",
        ),
        PlanOperation(
            operation_id="validate_package_public_api_exports",
            operation_type="run_validation_profile",
            target_paths=[_PACKAGE_PUBLIC_API_DOC_PATH, _PACKAGE_PUBLIC_API_MODULE_PATH],
            description="Validate the package-public-API symbol references against the governed module export surface after synchronization.",
            command="python",
            command_arguments=verify_arguments,
            evidence_rule_ids=trigger_rule_ids,
            predicted_outcome="The package-public-API doc references only symbols exported by `src/inf_work/__init__.py`.",
        ),
    ]


def _build_package_export_verification_contract(workspace_root: str, required_rule_ids: list[str]) -> VerificationContract:
    command = _operation_command_string(
        "python",
        [
            "-m",
            "inf_work",
            "kb",
            workspace_root,
            "--pretty",
            "--rule-id",
            "knowledge_base.component_doc_python_api_symbols_valid",
        ],
    )
    return VerificationContract(
        contract_id="verify_package_public_api_export_sync",
        required_rule_ids=required_rule_ids,
        commands=[command],
        success_criteria=[
            "`kb --rule-id knowledge_base.component_doc_python_api_symbols_valid` reports no missing `inf_work` package exports.",
        ],
    )


def _build_python_source_rollback_contract() -> RollbackContract:
    return RollbackContract(
        contract_id="rollback_python_source_pre_state_restore",
        strategy="restore_pre_state_file_contents",
        steps=[
            "Capture the full pre-remediation contents of the targeted Python source file before mutation.",
            "If verification fails, restore the exact pre-state file contents and rerun the targeted validator.",
        ],
    )


def _build_package_export_simulation(
    root_path: Path,
    rule_results: list[RuleResult],
    sync_state: dict[str, Any],
) -> dict[str, Any]:
    predicted_rule_results: list[RuleResult] = []
    predicted_rule_outcomes: list[dict[str, Any]] = []
    for rule_result in sorted(rule_results, key=lambda item: item.rule_id):
        predicted_passed = rule_result.passed
        rationale = "Dry-run simulation does not alter this rule surface, so the current result is preserved."
        if rule_result.rule_id == "knowledge_base.component_doc_python_api_symbols_valid" and not sync_state["unsupported_symbols"]:
            predicted_passed = True
            rationale = "Simulated package export synchronization adds the missing explicit re-exports required by the governed package API documentation."
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
        predicted_rule_outcomes.append(
            {
                "rule_id": rule_result.rule_id,
                "current_passed": rule_result.passed,
                "predicted_passed": predicted_passed,
                "predicted_effect": (
                    "would_pass"
                    if predicted_passed and not rule_result.passed
                    else "unchanged"
                    if predicted_passed == rule_result.passed
                    else "would_fail"
                ),
                "rationale": rationale,
            }
        )

    artifact_change = _build_artifact_change(
        root_path,
        sync_state["module_path"],
        sync_state["updated_text"],
    )
    changed_paths = [artifact_change["target_path"]] if artifact_change["content_changed"] else []
    unchanged_paths = [] if artifact_change["content_changed"] else [artifact_change["target_path"]]
    return {
        "simulation_id": "dry_run_package_public_api_export_sync",
        "simulation_phase": "dry_run_source_level_remediation",
        "workspace_mutation": False,
        "artifact_changes": [artifact_change],
        "changed_paths": changed_paths,
        "unchanged_paths": unchanged_paths,
        "predicted_rule_outcomes": predicted_rule_outcomes,
        "predicted_rule_summary": summarize_rule_results(predicted_rule_results),
        "notes": [
            "Dry-run simulation previews the deterministic `src/inf_work/__init__.py` re-export patch without mutating the workspace.",
            "The current source-level slice stays bounded to the package public API export surface and excludes arbitrary Python edits.",
        ],
    }


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


def _capture_artifact_pre_state(root_path: Path, target_paths: list[str]) -> dict[str, dict[str, Any]]:
    pre_state: dict[str, dict[str, Any]] = {}
    for target_path in target_paths:
        current_text = _read_optional_text(root_path / target_path)
        pre_state[target_path] = {
            "existed": current_text is not None,
            "text": current_text,
            "sha256": _sha256_text(current_text),
        }
    return pre_state


def _restore_artifact_pre_state(root_path: Path, pre_state: dict[str, dict[str, Any]]) -> dict[str, Any]:
    restored_paths: list[str] = []
    deleted_paths: list[str] = []
    for target_path, state in sorted(pre_state.items()):
        path = root_path / target_path
        if state["existed"]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(state["text"], encoding="utf-8")
            restored_paths.append(target_path)
        elif path.exists():
            path.unlink()
            deleted_paths.append(target_path)
    return {
        "restored_paths": restored_paths,
        "deleted_paths": deleted_paths,
    }


def _build_operation_execution_result(
    operation: PlanOperation,
    *,
    status: str,
    mutation_performed: bool,
    details: dict[str, Any],
) -> OperationExecutionResult:
    return OperationExecutionResult(
        operation_id=operation.operation_id,
        operation_type=operation.operation_type,
        target_paths=operation.target_paths,
        status=status,
        mutation_performed=mutation_performed,
        details=details,
    )


def _build_no_plan_execution_result(plan: RemediationPlan, *, notes: list[str]) -> RemediationExecutionResult:
    return RemediationExecutionResult(
        workspace_root=plan.workspace_root,
        plan_id=plan.plan_id,
        execution_phase="applied_structured_remediation",
        execution_attempted=False,
        plan_available=False,
        applied=False,
        compliant=plan.current_status_compliant,
        rollback_performed=False,
        rollback_summary={"restored_paths": [], "deleted_paths": []},
        triggering_rule_ids=plan.triggering_rule_ids,
        unsupported_failing_rule_ids=plan.unsupported_failing_rule_ids,
        operation_results=[],
        status_validation=None,
        summary_validation=None,
        knowledge_base_validation=None,
        notes=notes,
    )


def apply_status_artifact_remediation(
    workspace_root: str | Path,
    rule_ids: set[str] | None = None,
    *,
    intent_id: str | None = None,
) -> RemediationExecutionResult:
    root_path = Path(workspace_root).resolve()
    plan = compile_status_artifact_remediation_plan(
        root_path,
        rule_ids,
        include_simulation=False,
        intent_id=intent_id,
    )

    if not plan.plan_available:
        return _build_no_plan_execution_result(
            plan,
            notes=[
                "No supported applied remediation was executed because no bounded status-artifact remediation plan was available.",
                *plan.notes,
            ],
        )

    pre_state = _capture_artifact_pre_state(root_path, plan.affected_paths)
    operation_results: list[OperationExecutionResult] = []

    try:
        status_snapshot = write_system_status_outputs(
            root_path,
            canonical_json_path=_DEFAULT_STATUS_JSON_PATH,
            derived_markdown_path=_DEFAULT_STATUS_MARKDOWN_PATH,
            summary_path=_DEFAULT_STATUS_SUMMARY_PATH,
        )
        operation_results.append(
            _build_operation_execution_result(
                plan.operations[0],
                status="completed",
                mutation_performed=True,
                details={
                    "generated_at": status_snapshot.generated_at,
                    "canonical_json_path": status_snapshot.canonical_json_path,
                    "derived_markdown_path": status_snapshot.derived_markdown_path,
                },
            )
        )

        verification_rule_ids = set(plan.verification_contract.required_rule_ids) if plan.verification_contract else None
        status_validation = validate_system_status(root_path, verification_rule_ids)
        operation_results.append(
            _build_operation_execution_result(
                plan.operations[1],
                status="completed" if status_validation.compliant else "failed",
                mutation_performed=False,
                details={
                    "compliant": status_validation.compliant,
                    "issue_count": len(status_validation.issues),
                    "rule_summary": summarize_rule_results(status_validation.rule_results),
                },
            )
        )

        summary_validation = validate_system_summary(root_path)
        operation_results.append(
            _build_operation_execution_result(
                plan.operations[2],
                status="completed" if summary_validation.compliant else "failed",
                mutation_performed=False,
                details={
                    "compliant": summary_validation.compliant,
                    "issue_count": len(summary_validation.issues),
                    "rule_summary": summarize_rule_results(summary_validation.rule_results),
                },
            )
        )

        verification_passed = status_validation.compliant and summary_validation.compliant
        if verification_passed:
            return RemediationExecutionResult(
                workspace_root=str(root_path),
                plan_id=plan.plan_id,
                execution_phase="applied_structured_remediation",
                execution_attempted=True,
                plan_available=True,
                applied=True,
                compliant=True,
                rollback_performed=False,
                rollback_summary={"restored_paths": [], "deleted_paths": []},
                triggering_rule_ids=plan.triggering_rule_ids,
                unsupported_failing_rule_ids=plan.unsupported_failing_rule_ids,
                operation_results=operation_results,
                status_validation=status_validation.to_dict(),
                summary_validation=summary_validation.to_dict(),
                knowledge_base_validation=None,
                notes=[
                    "Applied remediation completed successfully for the bounded status-artifact slice.",
                    "Verification passed without requiring rollback.",
                ],
            )

        rollback_summary = _restore_artifact_pre_state(root_path, pre_state)
        return RemediationExecutionResult(
            workspace_root=str(root_path),
            plan_id=plan.plan_id,
            execution_phase="applied_structured_remediation",
            execution_attempted=True,
            plan_available=True,
            applied=False,
            compliant=False,
            rollback_performed=True,
            rollback_summary=rollback_summary,
            triggering_rule_ids=plan.triggering_rule_ids,
            unsupported_failing_rule_ids=plan.unsupported_failing_rule_ids,
            operation_results=operation_results,
            status_validation=status_validation.to_dict(),
            summary_validation=summary_validation.to_dict(),
            knowledge_base_validation=None,
            notes=[
                "Applied remediation failed verification and the bounded rollback contract restored the pre-remediation artifact state.",
            ],
        )
    except Exception as error:
        rollback_summary = _restore_artifact_pre_state(root_path, pre_state)
        return RemediationExecutionResult(
            workspace_root=str(root_path),
            plan_id=plan.plan_id,
            execution_phase="applied_structured_remediation",
            execution_attempted=True,
            plan_available=True,
            applied=False,
            compliant=False,
            rollback_performed=True,
            rollback_summary=rollback_summary,
            triggering_rule_ids=plan.triggering_rule_ids,
            unsupported_failing_rule_ids=plan.unsupported_failing_rule_ids,
            operation_results=operation_results,
            status_validation=None,
            summary_validation=None,
            knowledge_base_validation=None,
            notes=[
                "Applied remediation encountered an exception and the bounded rollback contract restored the pre-remediation artifact state.",
                f"Exception: {error}",
            ],
        )


def compile_package_public_api_export_remediation_plan(
    workspace_root: str | Path,
    rule_ids: set[str] | None = None,
    *,
    include_simulation: bool = False,
) -> RemediationPlan:
    root_path = Path(workspace_root).resolve()
    validation_result = validate_knowledge_base(root_path, rule_ids)
    failed_rule_ids = _sorted_failed_rule_ids(validation_result.rule_results)
    supported_rule_ids = [rule_id for rule_id in failed_rule_ids if rule_id in SUPPORTED_SOURCE_LEVEL_TRIGGER_RULE_IDS]
    unsupported_rule_ids = [rule_id for rule_id in failed_rule_ids if rule_id not in SUPPORTED_SOURCE_LEVEL_TRIGGER_RULE_IDS]
    selected_rule_ids = sorted(rule_ids) if rule_ids else []
    sync_state = _build_package_export_sync_state(root_path)
    plan_available = bool(supported_rule_ids) and bool(sync_state["missing_documented_symbols"]) and not sync_state["unsupported_symbols"]
    current_rule_summary = summarize_rule_results(validation_result.rule_results)
    triggering_evidence = [
        rule_result.to_dict()
        for rule_result in sorted(validation_result.rule_results, key=lambda item: item.rule_id)
        if not rule_result.passed and rule_result.rule_id in supported_rule_ids
    ]

    if plan_available:
        simulation = _build_package_export_simulation(root_path, validation_result.rule_results, sync_state) if include_simulation else None
        return RemediationPlan(
            workspace_root=str(root_path),
            plan_id="remediation_plan_package_public_api_export_sync",
            objective="Synchronize the governed `inf_work` package export surface so the package public API documentation references only explicit re-exports.",
            plan_phase="dry_run_source_level_remediation" if include_simulation else "bounded_source_level_remediation",
            plan_only=not include_simulation,
            current_status_compliant=validation_result.compliant,
            plan_available=True,
            selected_rule_ids=selected_rule_ids,
            triggering_rule_ids=supported_rule_ids,
            unsupported_failing_rule_ids=unsupported_rule_ids,
            selected_strategy=PACKAGE_EXPORT_SYNC_REMEDIATION_STRATEGY,
            triggering_evidence=triggering_evidence,
            current_rule_summary=current_rule_summary,
            affected_paths=[_PACKAGE_PUBLIC_API_MODULE_PATH],
            operations=_build_package_export_plan_operations(str(root_path), supported_rule_ids),
            verification_contract=_build_package_export_verification_contract(str(root_path), supported_rule_ids),
            rollback_contract=_build_python_source_rollback_contract(),
            provenance=_build_package_export_provenance_record(supported_rule_ids, unsupported_rule_ids),
            simulation_available=simulation is not None,
            simulation=simulation,
            notes=[
                "The current Phase 4 slice is bounded to deterministic re-export synchronization in `src/inf_work/__init__.py`.",
                "The strategy only compiles when every missing documented symbol resolves to exactly one governed provider module.",
                "The current slice intentionally excludes arbitrary Python edits, multi-file synthesis, and interface redesign.",
            ],
        )

    notes = [
        "No supported Phase 4 package-export drift failures are active, so no bounded source-level remediation plan is compiled.",
    ]
    if sync_state["unsupported_symbols"]:
        notes.append(
            "Some missing documented package exports could not be resolved to exactly one governed provider module, so source-level remediation remains blocked for those symbols."
        )
    elif supported_rule_ids:
        notes.append("The package public API documentation already matches the explicit `inf_work` package re-export surface.")
    else:
        notes.append(
            "Failing knowledge-base rules remain outside the supported Phase 4 package-export remediation slice and must be handled by validator-specific workflows."
        )

    return RemediationPlan(
        workspace_root=str(root_path),
        plan_id="remediation_plan_package_public_api_export_sync",
        objective="Determine whether the bounded package-export source-level remediation slice should compile a deterministic plan.",
        plan_phase="dry_run_source_level_remediation" if include_simulation else "bounded_source_level_remediation",
        plan_only=not include_simulation,
        current_status_compliant=validation_result.compliant,
        plan_available=False,
        selected_rule_ids=selected_rule_ids,
        triggering_rule_ids=[],
        unsupported_failing_rule_ids=unsupported_rule_ids,
        selected_strategy=None,
        triggering_evidence=[],
        current_rule_summary=current_rule_summary,
        affected_paths=[_PACKAGE_PUBLIC_API_MODULE_PATH],
        operations=[],
        verification_contract=None,
        rollback_contract=_build_python_source_rollback_contract(),
        provenance=_build_package_export_provenance_record([], unsupported_rule_ids),
        simulation_available=False,
        simulation=None,
        notes=notes,
    )


def apply_package_public_api_export_remediation(
    workspace_root: str | Path,
    rule_ids: set[str] | None = None,
) -> RemediationExecutionResult:
    root_path = Path(workspace_root).resolve()
    plan = compile_package_public_api_export_remediation_plan(root_path, rule_ids, include_simulation=False)
    if not plan.plan_available:
        return _build_no_plan_execution_result(
            plan,
            notes=[
                "No supported applied remediation was executed because no bounded package-export source-level remediation plan was available.",
                *plan.notes,
            ],
        )

    sync_state = _build_package_export_sync_state(root_path)
    pre_state = _capture_artifact_pre_state(root_path, plan.affected_paths)
    operation_results: list[OperationExecutionResult] = []

    try:
        target_path = root_path / _PACKAGE_PUBLIC_API_MODULE_PATH
        target_path.write_text(sync_state["updated_text"], encoding="utf-8")
        operation_results.append(
            _build_operation_execution_result(
                plan.operations[0],
                status="completed",
                mutation_performed=True,
                details={
                    "module_symbol_additions": sync_state["module_symbol_additions"],
                    "missing_all_symbols": sync_state["missing_all_symbols"],
                    "updated_path": _PACKAGE_PUBLIC_API_MODULE_PATH,
                },
            )
        )

        verification_rule_ids = set(plan.verification_contract.required_rule_ids) if plan.verification_contract else None
        kb_validation = validate_knowledge_base(root_path, verification_rule_ids)
        operation_results.append(
            _build_operation_execution_result(
                plan.operations[1],
                status="completed" if kb_validation.compliant else "failed",
                mutation_performed=False,
                details={
                    "compliant": kb_validation.compliant,
                    "issue_count": len(kb_validation.issues),
                    "rule_summary": summarize_rule_results(kb_validation.rule_results),
                },
            )
        )

        if kb_validation.compliant:
            return RemediationExecutionResult(
                workspace_root=str(root_path),
                plan_id=plan.plan_id,
                execution_phase="bounded_source_level_remediation",
                execution_attempted=True,
                plan_available=True,
                applied=True,
                compliant=True,
                rollback_performed=False,
                rollback_summary={"restored_paths": [], "deleted_paths": []},
                triggering_rule_ids=plan.triggering_rule_ids,
                unsupported_failing_rule_ids=plan.unsupported_failing_rule_ids,
                operation_results=operation_results,
                status_validation=None,
                summary_validation=None,
                knowledge_base_validation=kb_validation.to_dict(),
                notes=[
                    "Applied remediation completed successfully for the bounded package-export source-level slice.",
                    "Verification passed without requiring rollback.",
                ],
            )

        rollback_summary = _restore_artifact_pre_state(root_path, pre_state)
        return RemediationExecutionResult(
            workspace_root=str(root_path),
            plan_id=plan.plan_id,
            execution_phase="bounded_source_level_remediation",
            execution_attempted=True,
            plan_available=True,
            applied=False,
            compliant=False,
            rollback_performed=True,
            rollback_summary=rollback_summary,
            triggering_rule_ids=plan.triggering_rule_ids,
            unsupported_failing_rule_ids=plan.unsupported_failing_rule_ids,
            operation_results=operation_results,
            status_validation=None,
            summary_validation=None,
            knowledge_base_validation=kb_validation.to_dict(),
            notes=[
                "Applied remediation failed verification and the bounded rollback contract restored the pre-remediation Python source state.",
            ],
        )
    except Exception as error:
        rollback_summary = _restore_artifact_pre_state(root_path, pre_state)
        return RemediationExecutionResult(
            workspace_root=str(root_path),
            plan_id=plan.plan_id,
            execution_phase="bounded_source_level_remediation",
            execution_attempted=True,
            plan_available=True,
            applied=False,
            compliant=False,
            rollback_performed=True,
            rollback_summary=rollback_summary,
            triggering_rule_ids=plan.triggering_rule_ids,
            unsupported_failing_rule_ids=plan.unsupported_failing_rule_ids,
            operation_results=operation_results,
            status_validation=None,
            summary_validation=None,
            knowledge_base_validation=None,
            notes=[
                "Applied remediation encountered an exception and the bounded rollback contract restored the pre-remediation Python source state.",
                f"Exception: {error}",
            ],
        )


def compile_remediation_plan(
    workspace_root: str | Path,
    rule_ids: set[str] | None = None,
    *,
    include_simulation: bool = False,
    intent_id: str | None = None,
) -> RemediationPlan:
    root_path = Path(workspace_root).resolve()
    selected_rule_ids = sorted(rule_ids) if rule_ids else []
    status_plan = compile_status_artifact_remediation_plan(
        root_path,
        rule_ids,
        include_simulation=include_simulation,
        intent_id=intent_id,
    )
    package_plan = compile_package_public_api_export_remediation_plan(root_path, rule_ids, include_simulation=include_simulation)
    selected_domains = {rule_id.split(".", maxsplit=1)[0] for rule_id in selected_rule_ids}

    if intent_id == _STATUS_REFRESH_INTENT_ID:
        return status_plan

    if selected_domains == {"knowledge_base"}:
        return package_plan
    if selected_domains == {"status"}:
        return status_plan

    available_plans = [plan for plan in [status_plan, package_plan] if plan.plan_available and plan.selected_strategy is not None]
    if available_plans:
        return sorted(available_plans, key=lambda plan: plan.selected_strategy.priority)[0]
    if not status_plan.current_status_compliant:
        return status_plan
    if not package_plan.current_status_compliant:
        return package_plan
    return status_plan


def apply_remediation_plan(
    workspace_root: str | Path,
    rule_ids: set[str] | None = None,
    *,
    intent_id: str | None = None,
) -> RemediationExecutionResult:
    plan = compile_remediation_plan(workspace_root, rule_ids, include_simulation=False, intent_id=intent_id)
    if not plan.plan_available or plan.selected_strategy is None:
        return _build_no_plan_execution_result(
            plan,
            notes=[
                "No supported applied remediation was executed because no bounded remediation plan was available for the selected rule slice.",
                *plan.notes,
            ],
        )
    if plan.selected_strategy.strategy_id == STATUS_ARTIFACT_REMEDIATION_STRATEGY.strategy_id:
            return apply_status_artifact_remediation(workspace_root, rule_ids, intent_id=intent_id)
    if plan.selected_strategy.strategy_id == PACKAGE_EXPORT_SYNC_REMEDIATION_STRATEGY.strategy_id:
        return apply_package_public_api_export_remediation(workspace_root, rule_ids)
    return _build_no_plan_execution_result(
        plan,
        notes=[
            "No supported applied remediation was executed because the selected strategy does not yet have an execution binding.",
            *plan.notes,
        ],
    )


def _sorted_failed_rule_ids(rule_results: list[RuleResult]) -> list[str]:
    return sorted({rule_result.rule_id for rule_result in rule_results if not rule_result.passed})


def compile_status_artifact_remediation_plan(
    workspace_root: str | Path,
    rule_ids: set[str] | None = None,
    *,
    include_simulation: bool = False,
    intent_id: str | None = None,
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
    governed_intent_ids = [intent_id] if intent_id == _STATUS_REFRESH_INTENT_ID else []
    explicit_intent_selected = bool(governed_intent_ids)

    if supported_rule_ids or explicit_intent_selected:
        effective_rule_ids = supported_rule_ids or list(SUPPORTED_STATUS_ARTIFACT_TRIGGER_RULE_IDS)
        operations = _build_plan_operations(str(root_path), effective_rule_ids)
        verification_contract = _build_verification_contract(str(root_path), effective_rule_ids)
        rollback_contract = _build_plan_only_rollback_contract()
        simulation = _build_dry_run_simulation(root_path, validation_result.rule_results) if include_simulation else None
        return RemediationPlan(
            workspace_root=str(root_path),
            plan_id="remediation_plan_status_artifact_regeneration",
            objective=(
                "Refresh the governed status artifacts on explicit operator intent and verify that the canonical snapshot plus derived markdown outputs still match the current workspace state."
                if explicit_intent_selected
                else "Regenerate stale governed status artifacts and verify that the current workspace state is reflected across the canonical snapshot and derived markdown outputs."
            ),
            plan_phase="intent_driven_governed_change" if explicit_intent_selected else ("dry_run_structured_remediation" if include_simulation else "plan_only_structured_remediation"),
            plan_only=not include_simulation,
            current_status_compliant=validation_result.compliant,
            plan_available=True,
            selected_rule_ids=selected_rule_ids,
            triggering_rule_ids=effective_rule_ids if explicit_intent_selected else supported_rule_ids,
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
            provenance=_build_provenance_record(
                effective_rule_ids if explicit_intent_selected else supported_rule_ids,
                unsupported_rule_ids,
                governed_intent_ids=governed_intent_ids,
            ),
            simulation_available=simulation is not None,
            simulation=simulation,
            notes=[
                "The remediation compiler remains non-mutating and bounded to governed status artifacts.",
                "Enable dry-run simulation to preview deterministic post-state diffs before any manual operator action.",
                "Explicit governed intent currently supports deterministic status-artifact refresh without requiring an active failure.",
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