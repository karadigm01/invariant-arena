from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .core_reference import build_core_reference_view
from .rules import RuleFinding, RuleResult, ValidationRule, register_rules, run_registered_rules


@dataclass(frozen=True)
class ValidationResult:
    workspace_root: str
    required_directories: list[str]
    present_directories: list[str]
    missing_directories: list[str]
    compliant: bool
    rule_results: list[RuleResult]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["rule_results"] = [rule_result.to_dict() for rule_result in self.rule_results]
        return payload


def _build_workspace_context(root_path: Path) -> dict[str, Any]:
    reference_view = build_core_reference_view(root_path)
    required_directories = reference_view.required_directories
    present_directories = [
        directory_name
        for directory_name in required_directories
        if (root_path / directory_name).is_dir()
    ]
    missing_directories = [
        directory_name
        for directory_name in required_directories
        if directory_name not in present_directories
    ]
    return {
        "workspace_root": str(root_path),
        "required_directories": required_directories,
        "present_directories": present_directories,
        "missing_directories": missing_directories,
    }


def _evaluate_required_directories_present(context: dict[str, Any]) -> list[RuleFinding]:
    return [
        RuleFinding(
            message=f"Missing required directory: {directory_name}",
            source_file="core_reference.json",
            item_identifier=directory_name,
            field_name="workspace_governance.directory_structure",
        )
        for directory_name in context["missing_directories"]
    ]


WORKSPACE_RULES = [
    ValidationRule(
        rule_id="workspace.required_directories_present",
        domain="workspace",
        category="coherence",
        severity="error",
        description="All governed directories from core_reference.json must exist in the workspace.",
        evaluator=_evaluate_required_directories_present,
    )
]

register_rules(WORKSPACE_RULES)


def run_workspace_rules(workspace_root: str | Path, rule_ids: set[str] | None = None) -> list[RuleResult]:
    root_path = Path(workspace_root).resolve()
    context = _build_workspace_context(root_path)
    return run_registered_rules("workspace", context, rule_ids)


def validate_workspace(workspace_root: str | Path, rule_ids: set[str] | None = None) -> ValidationResult:
    root_path = Path(workspace_root).resolve()
    context = _build_workspace_context(root_path)
    rule_results = run_registered_rules("workspace", context, rule_ids)

    return ValidationResult(
        workspace_root=str(root_path),
        required_directories=context["required_directories"],
        present_directories=context["present_directories"],
        missing_directories=context["missing_directories"],
        compliant=all(rule_result.passed for rule_result in rule_results),
        rule_results=rule_results,
    )
