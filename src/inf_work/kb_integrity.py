from __future__ import annotations

import ast
from datetime import datetime
import json
from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Any

from .rules import RuleFinding, RuleResult, ValidationRule, register_rules, run_registered_rules


VALID_CONSTRAINTS = {"I1", "I2", "I3", "I4"}
SUPPORTED_INF_WORK_SUBCOMMANDS = {
    "all",
    "workspace",
    "kb",
    "benchmark",
    "status",
    "status-check",
    "summary-check",
    "coverage-snapshot",
    "mutation-snapshot",
    "refresh-artifacts",
    "remediation-plan",
    "resolve-path",
    "infer-route",
}
_SUPPORTED_COMPONENT_INDEX_TYPES = {"governance_artifact", "python_module"}
_PYTHON_API_SYMBOL_PATTERN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_PACKAGE_IMPORT_PATTERN = re.compile(r"^\s*from\s+inf_work\s+import\s+(.+)$")


@dataclass(frozen=True)
class ReferenceIssue:
    source_file: str
    item_identifier: str
    field_name: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class KnowledgeBaseValidationResult:
    workspace_root: str
    compliant: bool
    issues: list[ReferenceIssue]
    rule_results: list[RuleResult]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["issues"] = [issue.to_dict() for issue in self.issues]
        payload["rule_results"] = [rule_result.to_dict() for rule_result in self.rule_results]
        return payload


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _item_label(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("component_id") or item.get("pattern_name") or item.get("component_name") or "unknown")


def _build_knowledge_base_context(root_path: Path) -> dict[str, Any]:
    core_reference_path = root_path / "core_reference.json"
    core_reference_payload = _load_json(core_reference_path) if core_reference_path.is_file() else {}
    techniques_payload = _load_json(root_path / "knowledge_base" / "techniques.json")
    bug_fixes_payload = _load_json(root_path / "knowledge_base" / "bug_fixes.json")
    innovations_payload = _load_json(root_path / "knowledge_base" / "constraint_innovations.json")
    automation_payload = _load_json(root_path / "knowledge_base" / "automation_patterns.json")
    session_history_payload = _load_json(root_path / "knowledge_base" / "session_history.json")
    kb_index_payload = _load_json(root_path / "knowledge_base" / "kb_index.json")
    component_index_payload = _load_json(root_path / "ai_docs" / "component_index.json")
    coverage_snapshot_path = root_path / "ai_docs" / "test_coverage_snapshot.json"
    coverage_snapshot_payload = _load_json(coverage_snapshot_path) if coverage_snapshot_path.is_file() else None
    component_docs: dict[str, dict[str, Any] | None] = {}
    for component in component_index_payload["components"]:
        documentation_path = root_path / str(component.get("documentation_path", ""))
        component_docs[str(component.get("component_id", "unknown"))] = (
            _load_json(documentation_path) if documentation_path.is_file() else None
        )
    return {
        "workspace_root": str(root_path),
        "core_reference_payload": core_reference_payload,
        "techniques": techniques_payload["techniques"],
        "bug_fixes": bug_fixes_payload["bug_fixes"],
        "innovations": innovations_payload["innovations"],
        "automation_patterns": automation_payload["automation_patterns"],
        "sessions": session_history_payload["sessions"],
        "techniques_payload": techniques_payload,
        "bug_fixes_payload": bug_fixes_payload,
        "innovations_payload": innovations_payload,
        "automation_payload": automation_payload,
        "session_history_payload": session_history_payload,
        "kb_index": kb_index_payload,
        "component_index_payload": component_index_payload,
        "coverage_snapshot_payload": coverage_snapshot_payload,
        "components": component_index_payload["components"],
        "component_docs": component_docs,
        "technique_ids": {item["id"] for item in techniques_payload["techniques"]},
        "technique_names": {item["name"] for item in techniques_payload["techniques"]},
    }


def _component_doc_required_fields(context: dict[str, Any]) -> list[str]:
    required_fields = (
        context.get("core_reference_payload", {})
        .get("documentation_schemas", {})
        .get("ai_reference_format", {})
        .get("required_fields", [])
    )
    return [str(field_name) for field_name in required_fields if field_name]


def _component_doc_expected_fields(context: dict[str, Any]) -> set[str]:
    return set(_component_doc_required_fields(context)) | {
        "component_name",
        "component_type",
        "file_paths",
        "notes",
        "related_techniques",
    }


def _sorted_unique_strings(values: list[Any]) -> list[str]:
    return sorted({str(value) for value in values})


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _duplicate_non_empty_component_ids(components: list[dict[str, Any]]) -> set[str]:
    counts: dict[str, int] = {}
    for component in components:
        component_id = component.get("component_id")
        if not _is_non_empty_string(component_id):
            continue
        normalized_component_id = str(component_id)
        counts[normalized_component_id] = counts.get(normalized_component_id, 0) + 1
    return {component_id for component_id, count in counts.items() if count > 1}


def _duplicate_non_empty_component_file_paths(components: list[dict[str, Any]]) -> set[str]:
    counts: dict[str, int] = {}
    for component in components:
        file_path = component.get("file_path")
        if not _is_non_empty_string(file_path):
            continue
        normalized_file_path = str(file_path)
        counts[normalized_file_path] = counts.get(normalized_file_path, 0) + 1
    return {file_path for file_path, count in counts.items() if count > 1}


def _duplicate_non_empty_component_names(components: list[dict[str, Any]]) -> set[str]:
    counts: dict[str, int] = {}
    for component in components:
        component_name = component.get("component_name")
        if not _is_non_empty_string(component_name):
            continue
        normalized_component_name = str(component_name)
        counts[normalized_component_name] = counts.get(normalized_component_name, 0) + 1
    return {component_name for component_name, count in counts.items() if count > 1}


def _has_duplicate_non_empty_string_entries(values: list[Any]) -> bool:
    normalized_values = [str(value) for value in values if isinstance(value, str) and value.strip()]
    return len(normalized_values) != len(set(normalized_values))


def _normalize_lookup_index_mapping(mapping: dict[str, Any]) -> dict[str, list[str]]:
    return {
        str(key): _sorted_unique_strings(list(values) if isinstance(values, list) else [])
        for key, values in sorted(mapping.items())
    }


def _max_non_empty_timestamps(values: list[Any]) -> str | None:
    timestamps = [str(value) for value in values if value]
    return max(timestamps) if timestamps else None


def _build_expected_kb_index_metadata(context: dict[str, Any]) -> dict[str, Any]:
    techniques = context["techniques"]
    bug_fixes = context["bug_fixes"]
    innovations = context["innovations"]
    automation_patterns = context["automation_patterns"]

    by_category: dict[str, list[str]] = {}
    for technique in techniques:
        category = technique.get("category")
        if category:
            by_category.setdefault(str(category), []).append(str(technique["id"]))
    for innovation in innovations:
        by_category.setdefault("innovation", []).append(str(innovation["id"]))

    by_constraint: dict[str, list[str]] = {}
    for technique in techniques:
        technique_id = str(technique["id"])
        for constraint in technique.get("constraints_compliance", []):
            by_constraint.setdefault(str(constraint), []).append(technique_id)
    for innovation in innovations:
        innovation_id = str(innovation["id"])
        for constraint in innovation.get("constraint_challenged", []):
            by_constraint.setdefault(str(constraint), []).append(innovation_id)

    by_error_code: dict[str, list[str]] = {}
    for bug_fix in bug_fixes:
        error_code = bug_fix.get("error_code")
        if error_code is not None:
            by_error_code.setdefault(str(error_code), []).append(str(bug_fix["id"]))

    by_automation_type: dict[str, list[str]] = {}
    for automation_pattern in automation_patterns:
        automation_type = automation_pattern.get("automation_type")
        if automation_type:
            by_automation_type.setdefault(str(automation_type), []).append(str(automation_pattern["id"]))

    total_automated_actions = len(automation_patterns)
    successful_automations = sum(float(automation_pattern.get("success_rate", 0.0)) > 0.0 for automation_pattern in automation_patterns)
    failed_automations = max(total_automated_actions - successful_automations, 0)
    aggregate_success_rate = (
        round(successful_automations / total_automated_actions, 4) if total_automated_actions else 0.0
    )
    session_timestamps = [session.get("created_timestamp") for session in context["sessions"]]
    kb_last_updated = _max_non_empty_timestamps(
        [
            context["techniques_payload"].get("metadata", {}).get("last_updated"),
            context["bug_fixes_payload"].get("metadata", {}).get("last_updated"),
            context["innovations_payload"].get("metadata", {}).get("last_updated"),
            context["automation_payload"].get("metadata", {}).get("last_updated"),
            context["session_history_payload"].get("metadata", {}).get("last_session"),
            *session_timestamps,
        ]
    )

    return {
        "last_updated": kb_last_updated,
        "total_techniques": len(techniques),
        "total_bug_fixes": len(bug_fixes),
        "total_innovations": len(innovations),
        "total_automation_patterns": len(automation_patterns),
        "constraint_compliance_stats": {
            "I1_compliant": sum("I1" in technique.get("constraints_compliance", []) for technique in techniques),
            "I2_compliant": sum("I2" in technique.get("constraints_compliance", []) for technique in techniques),
            "I3_compliant": sum("I3" in technique.get("constraints_compliance", []) for technique in techniques),
            "I4_compliant": sum("I4" in technique.get("constraints_compliance", []) for technique in techniques),
            "all_compliant": sum(VALID_CONSTRAINTS.issubset(set(technique.get("constraints_compliance", []))) for technique in techniques),
        },
        "automation_success_metrics": {
            "total_automated_actions": total_automated_actions,
            "successful_automations": successful_automations,
            "failed_automations": failed_automations,
            "success_rate": aggregate_success_rate,
        },
        "lookup_indices": {
            "by_category": {key: _sorted_unique_strings(values) for key, values in sorted(by_category.items())},
            "by_constraint": {key: _sorted_unique_strings(values) for key, values in sorted(by_constraint.items())},
            "by_error_code": {key: _sorted_unique_strings(values) for key, values in sorted(by_error_code.items())},
            "by_automation_type": {key: _sorted_unique_strings(values) for key, values in sorted(by_automation_type.items())},
        },
    }


def _kb_index_field_finding(field_name: str, actual: Any, expected: Any) -> RuleFinding:
    return RuleFinding(
        message=f"kb_index metadata drift for {field_name}: actual={actual!r}, expected={expected!r}",
        source_file="knowledge_base/kb_index.json",
        item_identifier="kb_index",
        field_name=field_name,
    )


def _metadata_count_finding(*, source_file: str, field_name: str, actual: Any, expected: Any) -> RuleFinding:
    return RuleFinding(
        message=f"Metadata count drift for {field_name}: actual={actual!r}, expected={expected!r}",
        source_file=source_file,
        item_identifier=source_file,
        field_name=field_name,
    )


def _metadata_timestamp_finding(*, source_file: str, field_name: str, actual: Any, expected: Any) -> RuleFinding:
    return RuleFinding(
        message=f"Metadata timestamp drift for {field_name}: actual={actual!r}, expected={expected!r}",
        source_file=source_file,
        item_identifier=source_file,
        field_name=field_name,
    )


def _component_index_field_finding(field_name: str, actual: Any, expected: Any) -> RuleFinding:
    return RuleFinding(
        message=f"component_index summary metadata drift for {field_name}: actual={actual!r}, expected={expected!r}",
        source_file="ai_docs/component_index.json",
        item_identifier="component_index",
        field_name=field_name,
    )


def _component_timestamp_finding(
    *,
    item_identifier: str,
    field_name: str,
    actual: Any,
    expected: Any,
    message_prefix: str,
) -> RuleFinding:
    return RuleFinding(
        message=f"{message_prefix}: actual={actual!r}, expected={expected!r}",
        source_file="ai_docs/component_index.json",
        item_identifier=item_identifier,
        field_name=field_name,
    )


def _is_valid_iso8601_utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False

    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False

    return True


def _unknown_technique_reference(
    *,
    source_file: str,
    item_identifier: str,
    field_name: str,
    technique_reference: str,
) -> RuleFinding:
    return RuleFinding(
        message=f"Unknown technique reference: {technique_reference}",
        source_file=source_file,
        item_identifier=item_identifier,
        field_name=field_name,
    )


def _evaluate_bug_fix_solution_technique_exists(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    for bug_fix in context["bug_fixes"]:
        technique_name = bug_fix.get("solution_technique")
        if technique_name not in context["technique_names"]:
            findings.append(
                _unknown_technique_reference(
                    source_file="knowledge_base/bug_fixes.json",
                    item_identifier=_item_label(bug_fix),
                    field_name="solution_technique",
                    technique_reference=str(technique_name),
                )
            )
    return findings


def _evaluate_innovation_creative_solution_exists(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    for innovation in context["innovations"]:
        creative_solution = innovation.get("creative_solution")
        if creative_solution not in context["technique_names"]:
            findings.append(
                _unknown_technique_reference(
                    source_file="knowledge_base/constraint_innovations.json",
                    item_identifier=_item_label(innovation),
                    field_name="creative_solution",
                    technique_reference=str(creative_solution),
                )
            )
    return findings


def _evaluate_innovation_constraints_valid(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    for innovation in context["innovations"]:
        for constraint in innovation.get("constraint_challenged", []):
            if constraint not in VALID_CONSTRAINTS:
                findings.append(
                    RuleFinding(
                        message=f"Invalid constraint value: {constraint}",
                        source_file="knowledge_base/constraint_innovations.json",
                        item_identifier=_item_label(innovation),
                        field_name="constraint_challenged",
                    )
                )
    return findings


def _evaluate_automation_related_techniques_exist(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    for automation_pattern in context["automation_patterns"]:
        for related_technique in automation_pattern.get("related_techniques", []):
            if related_technique not in context["technique_ids"] and related_technique not in context["technique_names"]:
                findings.append(
                    _unknown_technique_reference(
                        source_file="knowledge_base/automation_patterns.json",
                        item_identifier=_item_label(automation_pattern),
                        field_name="related_techniques",
                        technique_reference=str(related_technique),
                    )
                )
    return findings


def _evaluate_component_related_techniques_exist(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    for component in context["components"]:
        if any(
            not isinstance(related_technique, str) or not related_technique.strip()
            for related_technique in component.get("related_techniques", [])
        ):
            continue
        for related_technique in component.get("related_techniques", []):
            if related_technique not in context["technique_ids"] and related_technique not in context["technique_names"]:
                findings.append(
                    _unknown_technique_reference(
                        source_file="ai_docs/component_index.json",
                        item_identifier=_item_label(component),
                        field_name="related_techniques",
                        technique_reference=str(related_technique),
                    )
                )
    return findings


def _build_expected_component_dependents(components: list[dict[str, Any]]) -> dict[str, list[str]]:
    duplicate_component_ids = _duplicate_non_empty_component_ids(components)
    duplicate_file_paths = _duplicate_non_empty_component_file_paths(components)
    dependents_by_file_path: dict[str, list[str]] = {
        str(component.get("file_path", "")): []
        for component in components
        if component.get("file_path")
    }
    for component in components:
        component_id = component.get("component_id")
        if not _is_non_empty_string(component_id):
            continue
        if str(component_id) in duplicate_component_ids:
            continue
        for dependency in component.get("dependencies", []):
            dependency_key = str(dependency)
            if dependency_key in duplicate_file_paths:
                continue
            if dependency_key in dependents_by_file_path:
                dependents_by_file_path[dependency_key].append(str(component_id))

    return {
        str(component.get("component_id", "unknown")): _sorted_unique_strings(
            dependents_by_file_path.get(str(component.get("file_path", "")), [])
        )
        for component in components
    }


def _evaluate_component_index_dependents_parity(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    duplicate_component_ids = _duplicate_non_empty_component_ids(context["components"])
    duplicate_file_paths = _duplicate_non_empty_component_file_paths(context["components"])
    expected_dependents_by_component = _build_expected_component_dependents(context["components"])

    for component in context["components"]:
        component_id = _item_label(component)
        if not _is_non_empty_string(component.get("component_id")):
            continue
        if component_id in duplicate_component_ids:
            continue
        if str(component.get("file_path", "")) in duplicate_file_paths:
            continue
        if any(not isinstance(entry, str) or not entry.strip() for entry in component.get("dependents", [])):
            continue
        actual_dependents = _sorted_unique_strings(component.get("dependents", []))
        expected_dependents = expected_dependents_by_component.get(component_id, [])
        if actual_dependents != expected_dependents:
            findings.append(
                RuleFinding(
                    message=(
                        "Component dependents drift between component index and derived dependency topology: "
                        f"actual={actual_dependents!r}, expected={expected_dependents!r}"
                    ),
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="dependents",
                )
            )

    return findings


def _evaluate_component_doc_metadata_parity(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    duplicate_component_ids = _duplicate_non_empty_component_ids(context["components"])
    for component in context["components"]:
        component_id = _item_label(component)
        if not _is_non_empty_string(component.get("component_id")):
            continue
        if component_id in duplicate_component_ids:
            continue
        component_doc = context["component_docs"].get(component_id)
        documentation_path = str(component.get("documentation_path", "ai_docs/unknown.json"))

        if not isinstance(component.get("documentation_path"), str) or not str(component.get("documentation_path", "")).strip():
            continue

        if component_doc is None:
            findings.append(
                RuleFinding(
                    message="Component documentation file is missing or unreadable.",
                    source_file=documentation_path,
                    item_identifier=component_id,
                    field_name="documentation_path",
                )
            )
            continue

        compliance_status = component.get("compliance_status")
        if (
            not isinstance(compliance_status, str)
            or compliance_status not in _SUPPORTED_COMPONENT_INDEX_COMPLIANCE_STATUSES
        ):
            continue

        for field_name in ("component_id", "component_name", "component_type", "compliance_status"):
            if field_name == "component_name" and not _is_non_empty_string(component.get(field_name)):
                continue
            if field_name == "component_type" and component.get(field_name) not in _SUPPORTED_COMPONENT_INDEX_TYPES:
                continue
            index_value = component.get(field_name)
            doc_value = component_doc.get(field_name)
            if index_value != doc_value:
                findings.append(
                    RuleFinding(
                        message=f"Component metadata drift for {field_name}: index={index_value!r}, doc={doc_value!r}",
                        source_file=documentation_path,
                        item_identifier=component_id,
                        field_name=field_name,
                    )
                )

        index_creation_timestamp = component.get("creation_timestamp")
        if not _is_valid_iso8601_utc_timestamp(index_creation_timestamp):
            continue

        documented_creation_timestamp = component_doc.get("creation_timestamp")
        if index_creation_timestamp != documented_creation_timestamp:
            findings.append(
                RuleFinding(
                    message=(
                        "Component creation timestamp drift between component index and component doc: "
                        f"index={index_creation_timestamp!r}, doc={documented_creation_timestamp!r}"
                    ),
                    source_file=documentation_path,
                    item_identifier=component_id,
                    field_name="creation_timestamp",
                )
            )

        component_file_path = component.get("file_path")
        if not isinstance(component_file_path, str) or not component_file_path.strip():
            continue

        documented_file_paths = component_doc.get("file_paths", [])
        if component_file_path not in documented_file_paths:
            findings.append(
                RuleFinding(
                    message=f"Indexed file path {component_file_path!r} is not listed in component documentation file_paths.",
                    source_file=documentation_path,
                    item_identifier=component_id,
                    field_name="file_paths",
                )
            )

        index_dependencies = sorted(str(value) for value in component.get("dependencies", []))
        if any(not isinstance(value, str) or not value.strip() for value in component.get("dependencies", [])):
            continue
        if _has_duplicate_non_empty_string_entries(component.get("dependencies", [])):
            continue

        documented_dependencies = sorted(str(value) for value in component_doc.get("dependencies", []))
        if index_dependencies != documented_dependencies:
            findings.append(
                RuleFinding(
                    message=(
                        "Component dependency drift between component index and component doc: "
                        f"index={index_dependencies!r}, doc={documented_dependencies!r}"
                    ),
                    source_file=documentation_path,
                    item_identifier=component_id,
                    field_name="dependencies",
                )
            )

        index_related_techniques = sorted(str(value) for value in component.get("related_techniques", []))
        if any(not isinstance(value, str) or not value.strip() for value in component.get("related_techniques", [])):
            continue

        documented_related_techniques = sorted(str(value) for value in component_doc.get("related_techniques", []))
        if index_related_techniques != documented_related_techniques:
            findings.append(
                RuleFinding(
                    message=(
                        "Component technique traceability drift between component index and component doc: "
                        f"index={index_related_techniques!r}, doc={documented_related_techniques!r}"
                    ),
                    source_file=documentation_path,
                    item_identifier=component_id,
                    field_name="related_techniques",
                )
            )

    return findings


_EXPECTED_COMPONENT_INDEX_PERFORMANCE_METRIC_FIELDS = {
    "memory_profile",
    "response_latency_target",
}


def _evaluate_component_index_performance_metrics_field_set_exact(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        performance_metrics = component.get("performance_metrics")

        if not isinstance(performance_metrics, dict):
            continue

        actual_fields = set(performance_metrics.keys())
        if actual_fields != _EXPECTED_COMPONENT_INDEX_PERFORMANCE_METRIC_FIELDS:
            findings.append(
                RuleFinding(
                    message=(
                        "component_index.json performance_metrics must keep the governed field set exact: "
                        f"actual={sorted(actual_fields)!r}, expected={sorted(_EXPECTED_COMPONENT_INDEX_PERFORMANCE_METRIC_FIELDS)!r}"
                    ),
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="performance_metrics",
                )
            )

    return findings


def _evaluate_component_index_performance_metrics_values_non_empty(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        performance_metrics = component.get("performance_metrics")

        if not isinstance(performance_metrics, dict):
            continue

        actual_fields = set(performance_metrics.keys())
        if actual_fields != _EXPECTED_COMPONENT_INDEX_PERFORMANCE_METRIC_FIELDS:
            continue

        if any(not isinstance(value, str) or not value.strip() for value in performance_metrics.values()):
            findings.append(
                RuleFinding(
                    message="component_index.json performance_metrics values must be non-empty strings.",
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="performance_metrics",
                )
            )

    return findings


def _evaluate_component_index_known_issues_entries_non_empty(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        known_issues = component.get("known_issues")

        if not isinstance(known_issues, list):
            continue

        if any(not isinstance(issue, str) or not issue.strip() for issue in known_issues):
            findings.append(
                RuleFinding(
                    message="component_index.json known_issues entries must be non-empty strings.",
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="known_issues",
                )
            )

    return findings


def _evaluate_component_index_documentation_path_non_empty(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        documentation_path = component.get("documentation_path")

        if not isinstance(documentation_path, str) or not documentation_path.strip():
            findings.append(
                RuleFinding(
                    message="component_index.json documentation_path must be a non-empty string.",
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="documentation_path",
                )
            )

    return findings


def _evaluate_component_index_file_path_non_empty(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        file_path = component.get("file_path")

        if not isinstance(file_path, str) or not file_path.strip():
            findings.append(
                RuleFinding(
                    message="component_index.json file_path must be a non-empty string.",
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="file_path",
                )
            )

    return findings


def _evaluate_component_index_file_path_unique(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    duplicate_file_paths = _duplicate_non_empty_component_file_paths(context["components"])

    for component in context["components"]:
        component_id = _item_label(component)
        file_path = component.get("file_path")

        if not _is_non_empty_string(file_path):
            continue

        if str(file_path) in duplicate_file_paths:
            findings.append(
                RuleFinding(
                    message="component_index.json file_path values must be unique across components.",
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="file_path",
                )
            )

    return findings


def _evaluate_component_index_component_name_non_empty(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        component_name = component.get("component_name")

        if not _is_non_empty_string(component_name):
            findings.append(
                RuleFinding(
                    message="component_index.json component_name must be a non-empty string.",
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="component_name",
                )
            )

    return findings


def _evaluate_component_index_component_name_unique(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    duplicate_component_names = _duplicate_non_empty_component_names(context["components"])

    for component in context["components"]:
        component_id = _item_label(component)
        component_name = component.get("component_name")

        if not _is_non_empty_string(component_name):
            continue

        if str(component_name) in duplicate_component_names:
            findings.append(
                RuleFinding(
                    message="component_index.json component_name values must be unique across components.",
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="component_name",
                )
            )

    return findings


def _evaluate_component_index_component_id_non_empty(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        raw_component_id = component.get("component_id")

        if not _is_non_empty_string(raw_component_id):
            findings.append(
                RuleFinding(
                    message="component_index.json component_id must be a non-empty string.",
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="component_id",
                )
            )

    return findings


def _evaluate_component_index_component_id_unique(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    duplicate_component_ids = _duplicate_non_empty_component_ids(context["components"])

    for component in context["components"]:
        component_id = _item_label(component)
        raw_component_id = component.get("component_id")

        if not _is_non_empty_string(raw_component_id):
            continue

        normalized_component_id = str(raw_component_id)
        if normalized_component_id in duplicate_component_ids:
            findings.append(
                RuleFinding(
                    message="component_index.json component_id values must be unique across components.",
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="component_id",
                )
            )

    return findings


def _evaluate_component_index_component_type_valid(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        component_type = component.get("component_type")

        if component_type not in _SUPPORTED_COMPONENT_INDEX_TYPES:
            findings.append(
                RuleFinding(
                    message=(
                        "component_index.json component_type must be one of the governed values: "
                        f"actual={component_type!r}, expected={sorted(_SUPPORTED_COMPONENT_INDEX_TYPES)!r}"
                    ),
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="component_type",
                )
            )

    return findings


def _evaluate_component_index_health_status_valid(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        health_status = component.get("health_status")

        if not isinstance(health_status, str) or health_status not in _SUPPORTED_COMPONENT_INDEX_HEALTH_STATUSES:
            findings.append(
                RuleFinding(
                    message=(
                        "component_index.json health_status must be one of the governed values: "
                        f"actual={health_status!r}, expected={sorted(_SUPPORTED_COMPONENT_INDEX_HEALTH_STATUSES)!r}"
                    ),
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="health_status",
                )
            )

    return findings


def _evaluate_component_index_compliance_status_valid(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        compliance_status = component.get("compliance_status")

        if (
            not isinstance(compliance_status, str)
            or compliance_status not in _SUPPORTED_COMPONENT_INDEX_COMPLIANCE_STATUSES
        ):
            findings.append(
                RuleFinding(
                    message=(
                        "component_index.json compliance_status must be one of the governed values: "
                        f"actual={compliance_status!r}, expected={sorted(_SUPPORTED_COMPONENT_INDEX_COMPLIANCE_STATUSES)!r}"
                    ),
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="compliance_status",
                )
            )

    return findings


def _evaluate_component_index_complexity_score_non_negative_int(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        complexity_score = component.get("complexity_score")

        if complexity_score is None:
            continue

        if (
            not isinstance(complexity_score, int)
            or isinstance(complexity_score, bool)
            or complexity_score < 0
        ):
            findings.append(
                RuleFinding(
                    message="component_index.json complexity_score must be a non-negative integer.",
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="complexity_score",
                )
            )

    return findings


def _evaluate_component_index_test_coverage_percentage_valid(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        test_coverage_percentage = component.get("test_coverage_percentage")

        if test_coverage_percentage is None:
            continue

        if (
            not isinstance(test_coverage_percentage, int)
            or isinstance(test_coverage_percentage, bool)
            or test_coverage_percentage < 0
            or test_coverage_percentage > 100
        ):
            findings.append(
                RuleFinding(
                    message="component_index.json test_coverage_percentage must be an integer between 0 and 100.",
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="test_coverage_percentage",
                )
            )

    return findings


def _evaluate_component_index_timestamp_fields_valid(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)

        for field_name in ("creation_timestamp", "last_modified_timestamp"):
            timestamp_value = component.get(field_name)
            if _is_valid_iso8601_utc_timestamp(timestamp_value):
                continue

            findings.append(
                RuleFinding(
                    message=(
                        f"component_index.json {field_name} must be a non-empty ISO-8601 UTC timestamp "
                        "formatted as YYYY-MM-DDTHH:MM:SSZ."
                    ),
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name=field_name,
                )
            )

    return findings


def _evaluate_component_index_dependencies_entries_non_empty(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        dependencies = component.get("dependencies")

        if not isinstance(dependencies, list):
            continue

        if any(not isinstance(entry, str) or not entry.strip() for entry in dependencies):
            findings.append(
                RuleFinding(
                    message="component_index.json dependencies entries must be non-empty strings.",
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="dependencies",
                )
            )

    return findings


def _evaluate_component_index_dependencies_entries_unique(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        dependencies = component.get("dependencies")

        if not isinstance(dependencies, list):
            continue

        if any(not isinstance(entry, str) or not entry.strip() for entry in dependencies):
            continue

        if _has_duplicate_non_empty_string_entries(dependencies):
            findings.append(
                RuleFinding(
                    message="component_index.json dependencies entries must be unique strings.",
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="dependencies",
                )
            )

    return findings


def _evaluate_component_index_related_techniques_entries_non_empty(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        related_techniques = component.get("related_techniques")

        if not isinstance(related_techniques, list):
            continue

        if any(not isinstance(entry, str) or not entry.strip() for entry in related_techniques):
            findings.append(
                RuleFinding(
                    message="component_index.json related_techniques entries must be non-empty strings.",
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="related_techniques",
                )
            )

    return findings


def _evaluate_component_index_dependents_entries_non_empty(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        dependents = component.get("dependents")

        if not isinstance(dependents, list):
            continue

        if any(not isinstance(entry, str) or not entry.strip() for entry in dependents):
            findings.append(
                RuleFinding(
                    message="component_index.json dependents entries must be non-empty strings.",
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="dependents",
                )
            )

    return findings


def _evaluate_component_doc_required_fields_present(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    required_fields = _component_doc_required_fields(context)

    for component in context["components"]:
        component_id = _item_label(component)
        component_doc = context["component_docs"].get(component_id)
        documentation_path = str(component.get("documentation_path", "ai_docs/unknown.json"))

        if component_doc is None:
            continue

        for field_name in required_fields:
            if field_name not in component_doc:
                findings.append(
                    RuleFinding(
                        message=f"Component documentation missing required field {field_name!r} from ai_reference_format.",
                        source_file=documentation_path,
                        item_identifier=component_id,
                        field_name=field_name,
                    )
                )

    return findings


def _evaluate_component_doc_field_set_exact(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    expected_fields = _component_doc_expected_fields(context)
    required_fields = set(_component_doc_required_fields(context))

    for component in context["components"]:
        component_id = _item_label(component)
        component_doc = context["component_docs"].get(component_id)
        documentation_path = str(component.get("documentation_path", "ai_docs/unknown.json"))

        if component_doc is None:
            continue

        actual_fields = set(component_doc.keys())
        if not required_fields.issubset(actual_fields):
            continue
        if actual_fields != expected_fields:
            findings.append(
                RuleFinding(
                    message=(
                        "Companion component docs must keep the governed top-level field set exact: "
                        f"actual={sorted(actual_fields)!r}, expected={sorted(expected_fields)!r}"
                    ),
                    source_file=documentation_path,
                    item_identifier=component_id,
                    field_name="__root__",
                )
            )

    return findings


def _evaluate_component_doc_auto_generated_true(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        component_doc = context["component_docs"].get(component_id)
        documentation_path = str(component.get("documentation_path", "ai_docs/unknown.json"))

        if component_doc is None:
            continue

        if component_doc.get("auto_generated") is not True:
            findings.append(
                RuleFinding(
                    message=(
                        "Component documentation auto_generated must remain true for governed AI reference docs: "
                        f"actual={component_doc.get('auto_generated')!r}"
                    ),
                    source_file=documentation_path,
                    item_identifier=component_id,
                    field_name="auto_generated",
                )
            )

    return findings


def _evaluate_component_doc_targeted_test_file_exists(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    workspace_root = Path(context["workspace_root"])

    for component in context["components"]:
        component_id = _item_label(component)
        component_doc = context["component_docs"].get(component_id)
        documentation_path = str(component.get("documentation_path", "ai_docs/unknown.json"))

        if component_doc is None:
            continue

        test_coverage = component_doc.get("test_coverage")
        if not isinstance(test_coverage, dict) or "targeted_test_file" not in test_coverage:
            continue

        targeted_test_file = test_coverage.get("targeted_test_file")
        if not isinstance(targeted_test_file, str) or not targeted_test_file:
            findings.append(
                RuleFinding(
                    message=(
                        "Component documentation test_coverage.targeted_test_file must be a non-empty workspace-relative path."
                    ),
                    source_file=documentation_path,
                    item_identifier=component_id,
                    field_name="test_coverage.targeted_test_file",
                )
            )
            continue

        if not (workspace_root / targeted_test_file).is_file():
            findings.append(
                RuleFinding(
                    message=(
                        "Component documentation targeted test file must reference an existing workspace file: "
                        f"actual={targeted_test_file!r}"
                    ),
                    source_file=documentation_path,
                    item_identifier=component_id,
                    field_name="test_coverage.targeted_test_file",
                )
            )

    return findings


_SUPPORTED_COMPONENT_DOC_TEST_COVERAGE_STATUSES = {
    "generated_output_verified",
    "targeted_tests_added",
}

_EXPECTED_COMPONENT_DOC_TEST_COVERAGE_FIELDS = {
    "status",
    "targeted_test_file",
}

_COMPONENT_DOC_TEST_COVERAGE_STATUS_BY_TYPE = {
    "governance_artifact": "generated_output_verified",
    "python_module": "targeted_tests_added",
}

_SUPPORTED_COMPONENT_INDEX_HEALTH_STATUSES = {
    "healthy",
    "degraded",
    "failing",
}

_SUPPORTED_COMPONENT_INDEX_COMPLIANCE_STATUSES = {
    "I1_I2_I3_I4_compliant",
}


def _evaluate_component_doc_test_coverage_status_valid(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        component_doc = context["component_docs"].get(component_id)
        documentation_path = str(component.get("documentation_path", "ai_docs/unknown.json"))

        if component_doc is None:
            continue

        test_coverage = component_doc.get("test_coverage")
        if not isinstance(test_coverage, dict):
            continue

        status = test_coverage.get("status")
        if not isinstance(status, str) or status not in _SUPPORTED_COMPONENT_DOC_TEST_COVERAGE_STATUSES:
            findings.append(
                RuleFinding(
                    message=(
                        "Component documentation test_coverage.status must be one of the governed status values: "
                        f"actual={status!r}, expected={sorted(_SUPPORTED_COMPONENT_DOC_TEST_COVERAGE_STATUSES)!r}"
                    ),
                    source_file=documentation_path,
                    item_identifier=component_id,
                    field_name="test_coverage.status",
                )
            )

    return findings


def _evaluate_component_doc_test_coverage_field_set_exact(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        component_doc = context["component_docs"].get(component_id)
        documentation_path = str(component.get("documentation_path", "ai_docs/unknown.json"))

        if component_doc is None:
            continue

        test_coverage = component_doc.get("test_coverage")
        if not isinstance(test_coverage, dict):
            continue

        actual_fields = set(test_coverage.keys())
        if not _EXPECTED_COMPONENT_DOC_TEST_COVERAGE_FIELDS.issubset(actual_fields):
            continue

        if actual_fields != _EXPECTED_COMPONENT_DOC_TEST_COVERAGE_FIELDS:
            findings.append(
                RuleFinding(
                    message=(
                        "Component documentation test_coverage must keep the governed field set exact: "
                        f"actual={sorted(actual_fields)!r}, expected={sorted(_EXPECTED_COMPONENT_DOC_TEST_COVERAGE_FIELDS)!r}"
                    ),
                    source_file=documentation_path,
                    item_identifier=component_id,
                    field_name="test_coverage",
                )
            )

    return findings


def _evaluate_component_doc_test_coverage_status_matches_component_type(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        component_type = component.get("component_type")
        component_doc = context["component_docs"].get(component_id)
        documentation_path = str(component.get("documentation_path", "ai_docs/unknown.json"))

        if component_doc is None:
            continue

        expected_status = _COMPONENT_DOC_TEST_COVERAGE_STATUS_BY_TYPE.get(component_type)
        if expected_status is None:
            continue

        test_coverage = component_doc.get("test_coverage")
        status = test_coverage.get("status") if isinstance(test_coverage, dict) else None
        if status not in _SUPPORTED_COMPONENT_DOC_TEST_COVERAGE_STATUSES:
            continue

        if status != expected_status:
            findings.append(
                RuleFinding(
                    message=(
                        "Component documentation test_coverage.status must match the governed component type: "
                        f"component_type={component_type!r}, actual={status!r}, expected={expected_status!r}"
                    ),
                    source_file=documentation_path,
                    item_identifier=component_id,
                    field_name="test_coverage.status",
                )
            )

    return findings


def _evaluate_component_doc_interfaces_match_component_type(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        component_type = component.get("component_type")
        component_doc = context["component_docs"].get(component_id)
        documentation_path = str(component.get("documentation_path", "ai_docs/unknown.json"))

        if component_doc is None:
            continue

        interfaces = component_doc.get("interfaces")
        if not isinstance(interfaces, dict):
            continue

        if component_type == "python_module":
            if "python_api" not in interfaces:
                findings.append(
                    RuleFinding(
                        message="Python module component documentation must expose interfaces.python_api.",
                        source_file=documentation_path,
                        item_identifier=component_id,
                        field_name="interfaces.python_api",
                    )
                )
            continue

        if component_type == "governance_artifact":
            for field_name in ("artifact", "source_of_truth"):
                if field_name not in interfaces:
                    findings.append(
                        RuleFinding(
                            message=f"Governance artifact component documentation must expose interfaces.{field_name}.",
                            source_file=documentation_path,
                            item_identifier=component_id,
                            field_name=f"interfaces.{field_name}",
                        )
                    )

    return findings


def _evaluate_component_doc_interfaces_values_are_lists(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        component_doc = context["component_docs"].get(component_id)
        documentation_path = str(component.get("documentation_path", "ai_docs/unknown.json"))

        if component_doc is None:
            continue

        interfaces = component_doc.get("interfaces")
        if not isinstance(interfaces, dict):
            continue

        for field_name, values in interfaces.items():
            if not isinstance(values, list):
                findings.append(
                    RuleFinding(
                        message="Component documentation interfaces values must be lists.",
                        source_file=documentation_path,
                        item_identifier=component_id,
                        field_name=f"interfaces.{field_name}",
                    )
                )

    return findings


def _evaluate_component_doc_interfaces_entries_non_empty(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        component_doc = context["component_docs"].get(component_id)
        documentation_path = str(component.get("documentation_path", "ai_docs/unknown.json"))

        if component_doc is None:
            continue

        interfaces = component_doc.get("interfaces")
        if not isinstance(interfaces, dict):
            continue

        for field_name, values in interfaces.items():
            if not isinstance(values, list):
                continue
            if any(not isinstance(value, str) or not value.strip() for value in values):
                findings.append(
                    RuleFinding(
                        message="Component documentation interfaces list entries must be non-empty strings.",
                        source_file=documentation_path,
                        item_identifier=component_id,
                        field_name=f"interfaces.{field_name}",
                    )
                )

    return findings


def _evaluate_component_doc_performance_metrics_match_component_type(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    expected_keys_by_type = {
        "python_module": {"expected_latency", "memory_usage_pattern"},
        "governance_artifact": {"generation_frequency", "storage_pattern"},
    }

    for component in context["components"]:
        component_id = _item_label(component)
        component_type = component.get("component_type")
        component_doc = context["component_docs"].get(component_id)
        documentation_path = str(component.get("documentation_path", "ai_docs/unknown.json"))

        if component_doc is None:
            continue

        expected_keys = expected_keys_by_type.get(component_type)
        if expected_keys is None:
            continue

        performance_metrics = component_doc.get("performance_metrics")
        if not isinstance(performance_metrics, dict):
            continue

        actual_keys = set(performance_metrics.keys())
        if actual_keys != expected_keys:
            findings.append(
                RuleFinding(
                    message=(
                        "Component documentation performance_metrics keys must match the governed component type: "
                        f"component_type={component_type!r}, actual={sorted(actual_keys)!r}, expected={sorted(expected_keys)!r}"
                    ),
                    source_file=documentation_path,
                    item_identifier=component_id,
                    field_name="performance_metrics",
                )
            )

    return findings


def _evaluate_component_doc_performance_metrics_values_non_empty(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    expected_keys_by_type = {
        "python_module": {"expected_latency", "memory_usage_pattern"},
        "governance_artifact": {"generation_frequency", "storage_pattern"},
    }

    for component in context["components"]:
        component_id = _item_label(component)
        component_type = component.get("component_type")
        component_doc = context["component_docs"].get(component_id)
        documentation_path = str(component.get("documentation_path", "ai_docs/unknown.json"))

        if component_doc is None:
            continue

        expected_keys = expected_keys_by_type.get(component_type)
        if expected_keys is None:
            continue

        performance_metrics = component_doc.get("performance_metrics")
        if not isinstance(performance_metrics, dict):
            continue

        actual_keys = set(performance_metrics.keys())
        if actual_keys != expected_keys:
            continue

        if any(not isinstance(value, str) or not value.strip() for value in performance_metrics.values()):
            findings.append(
                RuleFinding(
                    message=(
                        "Component documentation performance_metrics values must be non-empty strings for the governed component type."
                    ),
                    source_file=documentation_path,
                    item_identifier=component_id,
                    field_name="performance_metrics",
                )
            )

    return findings


def _evaluate_component_doc_file_paths_exist(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    workspace_root = Path(context["workspace_root"])

    for component in context["components"]:
        component_id = _item_label(component)
        component_doc = context["component_docs"].get(component_id)
        documentation_path = str(component.get("documentation_path", "ai_docs/unknown.json"))

        if component_doc is None:
            continue

        file_paths = component_doc.get("file_paths")
        if not isinstance(file_paths, list):
            continue

        for file_path in file_paths:
            if not isinstance(file_path, str) or not file_path:
                findings.append(
                    RuleFinding(
                        message="Component documentation file_paths entries must be non-empty workspace-relative strings.",
                        source_file=documentation_path,
                        item_identifier=component_id,
                        field_name="file_paths",
                    )
                )
                continue

            if not (workspace_root / file_path).is_file():
                findings.append(
                    RuleFinding(
                        message=(
                            "Component documentation file_paths entries must reference existing workspace files: "
                            f"actual={file_path!r}"
                        ),
                        source_file=documentation_path,
                        item_identifier=component_id,
                        field_name="file_paths",
                    )
                )

    return findings


def _evaluate_component_doc_dependencies_exist(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    workspace_root = Path(context["workspace_root"])

    for component in context["components"]:
        component_id = _item_label(component)
        component_doc = context["component_docs"].get(component_id)
        documentation_path = str(component.get("documentation_path", "ai_docs/unknown.json"))

        if component_doc is None:
            continue

        dependencies = component_doc.get("dependencies")
        if not isinstance(dependencies, list):
            continue

        for dependency in dependencies:
            if not isinstance(dependency, str) or not dependency:
                findings.append(
                    RuleFinding(
                        message="Component documentation dependencies entries must be non-empty workspace-relative strings.",
                        source_file=documentation_path,
                        item_identifier=component_id,
                        field_name="dependencies",
                    )
                )
                continue

            if not (workspace_root / dependency).exists():
                findings.append(
                    RuleFinding(
                        message=(
                            "Component documentation dependencies entries must reference existing workspace paths: "
                            f"actual={dependency!r}"
                        ),
                        source_file=documentation_path,
                        item_identifier=component_id,
                        field_name="dependencies",
                    )
                )

    return findings


def _is_supported_cli_command(command: str) -> bool:
    normalized = command.strip()
    if not normalized:
        return False

    if normalized.startswith("PYTHONPATH=src /usr/bin/python3 -m inf_work "):
        return normalized.endswith("(no-install fallback)")

    if normalized.startswith("python -m inf_work.kb_check "):
        return True

    if normalized.startswith(".venv/bin/python -m inf_work.kb_check "):
        return True

    for prefix in ("python -m inf_work ", ".venv/bin/python -m inf_work "):
        if not normalized.startswith(prefix):
            continue

        remainder = normalized[len(prefix):]
        if remainder.startswith("[workspace_root]") and "legacy compatibility" in normalized:
            return True

        tokens = remainder.split()
        return tokens[0] in SUPPORTED_INF_WORK_SUBCOMMANDS

    return False


def _evaluate_component_doc_cli_commands_valid(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        component_doc = context["component_docs"].get(component_id)
        documentation_path = str(component.get("documentation_path", "ai_docs/unknown.json"))

        if component_doc is None:
            continue

        interfaces = component_doc.get("interfaces")
        cli_commands = interfaces.get("cli") if isinstance(interfaces, dict) else None
        if not isinstance(cli_commands, list):
            continue

        for command in cli_commands:
            if not isinstance(command, str) or not _is_supported_cli_command(command):
                findings.append(
                    RuleFinding(
                        message=(
                            "Component documentation interfaces.cli entries must map to the supported inf.work CLI surface: "
                            f"actual={command!r}"
                        ),
                        source_file=documentation_path,
                        item_identifier=component_id,
                        field_name="interfaces.cli",
                    )
                )

    return findings


def _extract_module_export_names(module_path: Path) -> tuple[set[str], set[str] | None]:
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


def _extract_documented_python_api_symbols(entry: str) -> tuple[set[str], str | None]:
    import_match = _PACKAGE_IMPORT_PATTERN.match(entry)
    if import_match is not None:
        imported_names = {
            part.strip()
            for part in import_match.group(1).split(",")
            if part.strip()
        }
        return imported_names, "package_import"

    symbol_match = _PYTHON_API_SYMBOL_PATTERN.match(entry)
    if symbol_match is not None:
        return {symbol_match.group(1)}, "callable"

    return set(), None


def _evaluate_component_doc_python_api_symbols_valid(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    workspace_root = Path(context["workspace_root"])

    for component in context["components"]:
        component_id = _item_label(component)
        component_doc = context["component_docs"].get(component_id)
        documentation_path = str(component.get("documentation_path", "ai_docs/unknown.json"))
        component_file_path = workspace_root / str(component.get("file_path", ""))

        if component_doc is None or not component_file_path.is_file():
            continue

        interfaces = component_doc.get("interfaces")
        python_api_entries = interfaces.get("python_api") if isinstance(interfaces, dict) else None
        if not isinstance(python_api_entries, list):
            continue

        exported_names, explicit_all = _extract_module_export_names(component_file_path)
        for entry in python_api_entries:
            if not isinstance(entry, str) or not entry.strip():
                continue

            documented_symbols, entry_kind = _extract_documented_python_api_symbols(entry)
            if not documented_symbols:
                findings.append(
                    RuleFinding(
                        message=(
                            "Component documentation interfaces.python_api entries must be callable signatures or `from inf_work import ...` surfaces: "
                            f"actual={entry!r}"
                        ),
                        source_file=documentation_path,
                        item_identifier=component_id,
                        field_name="interfaces.python_api",
                    )
                )
                continue

            expected_symbols = explicit_all if entry_kind == "package_import" and explicit_all is not None else exported_names
            missing_symbols = sorted(symbol for symbol in documented_symbols if symbol not in expected_symbols)
            if missing_symbols:
                findings.append(
                    RuleFinding(
                        message=(
                            "Component documentation interfaces.python_api references symbols not exported by the governed module: "
                            f"missing={missing_symbols!r}, actual={entry!r}"
                        ),
                        source_file=documentation_path,
                        item_identifier=component_id,
                        field_name="interfaces.python_api",
                    )
                )

    return findings


def _evaluate_component_doc_notes_non_empty(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for component in context["components"]:
        component_id = _item_label(component)
        component_doc = context["component_docs"].get(component_id)
        documentation_path = str(component.get("documentation_path", "ai_docs/unknown.json"))

        if component_doc is None:
            continue

        notes = component_doc.get("notes")
        if not isinstance(notes, list) or not notes:
            findings.append(
                RuleFinding(
                    message="Component documentation notes must be a non-empty list of strings.",
                    source_file=documentation_path,
                    item_identifier=component_id,
                    field_name="notes",
                )
            )
            continue

        if any(not isinstance(note, str) or not note.strip() for note in notes):
            findings.append(
                RuleFinding(
                    message="Component documentation notes entries must be non-empty strings.",
                    source_file=documentation_path,
                    item_identifier=component_id,
                    field_name="notes",
                )
            )

    return findings


def _evaluate_kb_index_metadata_parity(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    kb_index = context["kb_index"]
    expected_metadata = _build_expected_kb_index_metadata(context)

    actual_last_updated = kb_index.get("last_updated")
    expected_last_updated = expected_metadata["last_updated"]
    if actual_last_updated != expected_last_updated:
        findings.append(_kb_index_field_finding("last_updated", actual_last_updated, expected_last_updated))

    for field_name in (
        "total_techniques",
        "total_bug_fixes",
        "total_innovations",
        "total_automation_patterns",
    ):
        actual = kb_index.get(field_name)
        expected = expected_metadata[field_name]
        if actual != expected:
            findings.append(_kb_index_field_finding(field_name, actual, expected))

    actual_constraint_stats = kb_index.get("constraint_compliance_stats", {})
    expected_constraint_stats = expected_metadata["constraint_compliance_stats"]
    if actual_constraint_stats != expected_constraint_stats:
        findings.append(
            _kb_index_field_finding(
                "constraint_compliance_stats",
                actual_constraint_stats,
                expected_constraint_stats,
            )
        )

    actual_automation_success_metrics = kb_index.get("automation_success_metrics", {})
    expected_automation_success_metrics = expected_metadata["automation_success_metrics"]
    if actual_automation_success_metrics != expected_automation_success_metrics:
        findings.append(
            _kb_index_field_finding(
                "automation_success_metrics",
                actual_automation_success_metrics,
                expected_automation_success_metrics,
            )
        )

    actual_lookup_indices = kb_index.get("lookup_indices", {})
    expected_lookup_indices = expected_metadata["lookup_indices"]
    for lookup_field in ("by_category", "by_constraint", "by_error_code", "by_automation_type"):
        actual_lookup = _normalize_lookup_index_mapping(actual_lookup_indices.get(lookup_field, {}))
        expected_lookup = expected_lookup_indices[lookup_field]
        if actual_lookup != expected_lookup:
            findings.append(
                _kb_index_field_finding(
                    f"lookup_indices.{lookup_field}",
                    actual_lookup,
                    expected_lookup,
                )
            )

    return findings


def _evaluate_techniques_metadata_count_parity(context: dict[str, Any]) -> list[RuleFinding]:
    payload = context["techniques_payload"]
    actual = payload.get("metadata", {}).get("total_count")
    expected = len(context["techniques"])
    if actual == expected:
        return []
    return [
        _metadata_count_finding(
            source_file="knowledge_base/techniques.json",
            field_name="metadata.total_count",
            actual=actual,
            expected=expected,
        )
    ]


def _evaluate_bug_fixes_metadata_count_parity(context: dict[str, Any]) -> list[RuleFinding]:
    payload = context["bug_fixes_payload"]
    actual = payload.get("metadata", {}).get("total_count")
    expected = len(context["bug_fixes"])
    if actual == expected:
        return []
    return [
        _metadata_count_finding(
            source_file="knowledge_base/bug_fixes.json",
            field_name="metadata.total_count",
            actual=actual,
            expected=expected,
        )
    ]


def _evaluate_innovations_metadata_count_parity(context: dict[str, Any]) -> list[RuleFinding]:
    payload = context["innovations_payload"]
    actual = payload.get("metadata", {}).get("total_count")
    expected = len(context["innovations"])
    if actual == expected:
        return []
    return [
        _metadata_count_finding(
            source_file="knowledge_base/constraint_innovations.json",
            field_name="metadata.total_count",
            actual=actual,
            expected=expected,
        )
    ]


def _evaluate_automation_patterns_metadata_count_parity(context: dict[str, Any]) -> list[RuleFinding]:
    payload = context["automation_payload"]
    actual = payload.get("metadata", {}).get("total_count")
    expected = len(context["automation_patterns"])
    if actual == expected:
        return []
    return [
        _metadata_count_finding(
            source_file="knowledge_base/automation_patterns.json",
            field_name="metadata.total_count",
            actual=actual,
            expected=expected,
        )
    ]


def _evaluate_session_history_metadata_count_parity(context: dict[str, Any]) -> list[RuleFinding]:
    payload = context["session_history_payload"]
    actual = payload.get("metadata", {}).get("total_sessions")
    expected = len(context["sessions"])
    if actual == expected:
        return []
    return [
        _metadata_count_finding(
            source_file="knowledge_base/session_history.json",
            field_name="metadata.total_sessions",
            actual=actual,
            expected=expected,
        )
    ]


def _evaluate_techniques_metadata_last_updated_parity(context: dict[str, Any]) -> list[RuleFinding]:
    payload = context["techniques_payload"]
    actual = payload.get("metadata", {}).get("last_updated")
    expected = _max_non_empty_timestamps([item.get("created_timestamp") for item in context["techniques"]])
    if actual == expected:
        return []
    return [
        _metadata_timestamp_finding(
            source_file="knowledge_base/techniques.json",
            field_name="metadata.last_updated",
            actual=actual,
            expected=expected,
        )
    ]


def _evaluate_bug_fixes_metadata_last_updated_parity(context: dict[str, Any]) -> list[RuleFinding]:
    payload = context["bug_fixes_payload"]
    actual = payload.get("metadata", {}).get("last_updated")
    expected = _max_non_empty_timestamps([item.get("created_timestamp") for item in context["bug_fixes"]])
    if actual == expected:
        return []
    return [
        _metadata_timestamp_finding(
            source_file="knowledge_base/bug_fixes.json",
            field_name="metadata.last_updated",
            actual=actual,
            expected=expected,
        )
    ]


def _evaluate_innovations_metadata_last_updated_parity(context: dict[str, Any]) -> list[RuleFinding]:
    payload = context["innovations_payload"]
    actual = payload.get("metadata", {}).get("last_updated")
    expected = _max_non_empty_timestamps([item.get("created_timestamp") for item in context["innovations"]])
    if actual == expected:
        return []
    return [
        _metadata_timestamp_finding(
            source_file="knowledge_base/constraint_innovations.json",
            field_name="metadata.last_updated",
            actual=actual,
            expected=expected,
        )
    ]


def _evaluate_automation_patterns_metadata_last_updated_parity(context: dict[str, Any]) -> list[RuleFinding]:
    payload = context["automation_payload"]
    actual = payload.get("metadata", {}).get("last_updated")
    expected = _max_non_empty_timestamps([item.get("created_timestamp") for item in context["automation_patterns"]])
    if actual == expected:
        return []
    return [
        _metadata_timestamp_finding(
            source_file="knowledge_base/automation_patterns.json",
            field_name="metadata.last_updated",
            actual=actual,
            expected=expected,
        )
    ]


def _evaluate_session_history_temporal_metadata_parity(context: dict[str, Any]) -> list[RuleFinding]:
    payload = context["session_history_payload"]
    metadata = payload.get("metadata", {})
    timestamps = [session.get("created_timestamp") for session in context["sessions"]]
    expected_first = min(str(timestamp) for timestamp in timestamps if timestamp) if any(timestamps) else None
    expected_last = max(str(timestamp) for timestamp in timestamps if timestamp) if any(timestamps) else None
    findings: list[RuleFinding] = []

    actual_first = metadata.get("first_session")
    if actual_first != expected_first:
        findings.append(
            _metadata_timestamp_finding(
                source_file="knowledge_base/session_history.json",
                field_name="metadata.first_session",
                actual=actual_first,
                expected=expected_first,
            )
        )

    actual_last = metadata.get("last_session")
    if actual_last != expected_last:
        findings.append(
            _metadata_timestamp_finding(
                source_file="knowledge_base/session_history.json",
                field_name="metadata.last_session",
                actual=actual_last,
                expected=expected_last,
            )
        )

    return findings


def _evaluate_component_index_summary_metadata_parity(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    component_index_payload = context["component_index_payload"]
    components = context["components"]
    metadata = component_index_payload.get("metadata", {})
    health_status = component_index_payload.get("health_status", {})

    if any(
        not isinstance(component.get("health_status"), str)
        or component.get("health_status") not in _SUPPORTED_COMPONENT_INDEX_HEALTH_STATUSES
        for component in components
    ):
        return findings

    expected_total_components = len(components)
    actual_total_components = metadata.get("total_components")
    if actual_total_components != expected_total_components:
        findings.append(
            _component_index_field_finding(
                "metadata.total_components",
                actual_total_components,
                expected_total_components,
            )
        )

    expected_total_healthy = sum(component.get("health_status") == "healthy" for component in components)
    expected_total_degraded = sum(component.get("health_status") == "degraded" for component in components)
    expected_total_failing = sum(component.get("health_status") == "failing" for component in components)

    for field_name, expected in (
        ("health_status.total_healthy", expected_total_healthy),
        ("health_status.total_degraded", expected_total_degraded),
        ("health_status.total_failing", expected_total_failing),
    ):
        actual = health_status.get(field_name.split(".")[-1])
        if actual != expected:
            findings.append(_component_index_field_finding(field_name, actual, expected))

    return findings


def _evaluate_component_index_timestamp_metadata_parity(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    component_index_payload = context["component_index_payload"]
    components = context["components"]
    metadata = component_index_payload.get("metadata", {})

    component_last_modified_values: list[str] = []
    invalid_timestamp_fields_detected = False
    for component in components:
        component_id = _item_label(component)
        creation_timestamp = component.get("creation_timestamp")
        last_modified_timestamp = component.get("last_modified_timestamp")

        if not _is_valid_iso8601_utc_timestamp(creation_timestamp) or not _is_valid_iso8601_utc_timestamp(last_modified_timestamp):
            invalid_timestamp_fields_detected = True
            continue

        component_last_modified_values.append(str(last_modified_timestamp))
        if str(last_modified_timestamp) < str(creation_timestamp):
            findings.append(
                _component_timestamp_finding(
                    item_identifier=component_id,
                    field_name="last_modified_timestamp",
                    actual=last_modified_timestamp,
                    expected=f">= {creation_timestamp}",
                    message_prefix="Component timestamp ordering drift",
                )
            )

    if invalid_timestamp_fields_detected:
        return findings

    expected_last_updated = max(component_last_modified_values) if component_last_modified_values else None
    actual_last_updated = metadata.get("last_updated")
    if actual_last_updated != expected_last_updated:
        findings.append(
            _component_index_field_finding(
                "metadata.last_updated",
                actual_last_updated,
                expected_last_updated,
            )
        )

    return findings


def _evaluate_component_index_test_coverage_parity(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    duplicate_file_paths = _duplicate_non_empty_component_file_paths(context["components"])
    coverage_snapshot_payload = context.get("coverage_snapshot_payload")
    if coverage_snapshot_payload is None:
        return [
            RuleFinding(
                message="Coverage snapshot is missing; generate `ai_docs/test_coverage_snapshot.json` before validating component coverage parity.",
                source_file="ai_docs/test_coverage_snapshot.json",
                item_identifier="test_coverage_snapshot",
                field_name="coverage_snapshot",
            )
        ]

    coverage_by_module = {
        str(entry.get("module_path", "")): int(entry.get("coverage_percentage", 0))
        for entry in coverage_snapshot_payload.get("module_coverage", [])
    }

    for component in context["components"]:
        file_path = str(component.get("file_path", ""))
        if not file_path.endswith(".py"):
            continue
        if file_path in duplicate_file_paths:
            continue
        component_id = _item_label(component)
        if file_path not in coverage_by_module:
            findings.append(
                RuleFinding(
                    message=f"Missing module coverage entry for {file_path!r} in coverage snapshot.",
                    source_file="ai_docs/test_coverage_snapshot.json",
                    item_identifier=component_id,
                    field_name="module_coverage",
                )
            )
            continue

        actual = component.get("test_coverage_percentage")
        if (
            not isinstance(actual, int)
            or isinstance(actual, bool)
            or actual < 0
            or actual > 100
        ):
            continue

        expected = coverage_by_module[file_path]
        if actual != expected:
            findings.append(
                RuleFinding(
                    message=(
                        "Component coverage drift between component index and coverage snapshot: "
                        f"actual={actual!r}, expected={expected!r}"
                    ),
                    source_file="ai_docs/component_index.json",
                    item_identifier=component_id,
                    field_name="test_coverage_percentage",
                )
            )

    return findings


KNOWLEDGE_BASE_RULES = [
    ValidationRule(
        rule_id="knowledge_base.bug_fix_solution_technique_exists",
        domain="knowledge_base",
        category="cross_reference",
        severity="error",
        description="Bug fixes must reference a technique name that exists in techniques.json.",
        evaluator=_evaluate_bug_fix_solution_technique_exists,
    ),
    ValidationRule(
        rule_id="knowledge_base.innovation_creative_solution_exists",
        domain="knowledge_base",
        category="cross_reference",
        severity="error",
        description="Constraint innovations must reference an existing technique name.",
        evaluator=_evaluate_innovation_creative_solution_exists,
    ),
    ValidationRule(
        rule_id="knowledge_base.innovation_constraints_valid",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="Constraint innovations must reference only I1-I4 constraint identifiers.",
        evaluator=_evaluate_innovation_constraints_valid,
    ),
    ValidationRule(
        rule_id="knowledge_base.automation_related_techniques_exist",
        domain="knowledge_base",
        category="cross_reference",
        severity="error",
        description="Automation patterns must reference existing techniques by id or name.",
        evaluator=_evaluate_automation_related_techniques_exist,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_related_techniques_exist",
        domain="knowledge_base",
        category="cross_reference",
        severity="error",
        description="Components in component_index.json must reference existing techniques by id or name.",
        evaluator=_evaluate_component_related_techniques_exist,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_doc_metadata_parity",
        domain="knowledge_base",
        category="cross_reference",
        severity="error",
        description="Component index entries must stay aligned with their companion component docs for shared metadata, dependencies, and technique traceability.",
        evaluator=_evaluate_component_doc_metadata_parity,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_performance_metrics_field_set_exact",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json entries must keep the governed performance_metrics field set exact.",
        evaluator=_evaluate_component_index_performance_metrics_field_set_exact,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_performance_metrics_values_non_empty",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json entries must keep performance_metrics values as non-empty strings.",
        evaluator=_evaluate_component_index_performance_metrics_values_non_empty,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_known_issues_entries_non_empty",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json known_issues entries must remain a list of non-empty strings.",
        evaluator=_evaluate_component_index_known_issues_entries_non_empty,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_documentation_path_non_empty",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json documentation_path values must remain non-empty strings.",
        evaluator=_evaluate_component_index_documentation_path_non_empty,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_file_path_non_empty",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json file_path values must remain non-empty strings.",
        evaluator=_evaluate_component_index_file_path_non_empty,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_file_path_unique",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json file_path values must remain unique across components.",
        evaluator=_evaluate_component_index_file_path_unique,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_component_id_non_empty",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json component_id values must remain non-empty strings.",
        evaluator=_evaluate_component_index_component_id_non_empty,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_component_id_unique",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json component_id values must remain unique across components.",
        evaluator=_evaluate_component_index_component_id_unique,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_component_name_non_empty",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json component_name values must remain non-empty strings.",
        evaluator=_evaluate_component_index_component_name_non_empty,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_component_name_unique",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json component_name values must remain unique across components.",
        evaluator=_evaluate_component_index_component_name_unique,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_component_type_valid",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json component_type values must remain within the governed component-type vocabulary.",
        evaluator=_evaluate_component_index_component_type_valid,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_health_status_valid",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json health_status values must remain within the governed status vocabulary.",
        evaluator=_evaluate_component_index_health_status_valid,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_compliance_status_valid",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json compliance_status values must remain within the governed status vocabulary.",
        evaluator=_evaluate_component_index_compliance_status_valid,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_complexity_score_non_negative_int",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json complexity_score values must remain non-negative integers.",
        evaluator=_evaluate_component_index_complexity_score_non_negative_int,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_test_coverage_percentage_valid",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json test_coverage_percentage values must remain integers between 0 and 100.",
        evaluator=_evaluate_component_index_test_coverage_percentage_valid,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_timestamp_fields_valid",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json creation and last-modified timestamps must remain non-empty ISO-8601 UTC strings.",
        evaluator=_evaluate_component_index_timestamp_fields_valid,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_dependencies_entries_non_empty",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json dependencies entries must remain non-empty strings.",
        evaluator=_evaluate_component_index_dependencies_entries_non_empty,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_dependencies_entries_unique",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json dependencies entries must remain unique strings.",
        evaluator=_evaluate_component_index_dependencies_entries_unique,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_related_techniques_entries_non_empty",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json related_techniques entries must remain non-empty strings.",
        evaluator=_evaluate_component_index_related_techniques_entries_non_empty,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_dependents_entries_non_empty",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="component_index.json dependents entries must remain non-empty strings.",
        evaluator=_evaluate_component_index_dependents_entries_non_empty,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_doc_required_fields_present",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="Companion component docs must include every required ai_reference_format field from core_reference.json.",
        evaluator=_evaluate_component_doc_required_fields_present,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_doc_field_set_exact",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="Companion component docs must keep the governed top-level field set exact.",
        evaluator=_evaluate_component_doc_field_set_exact,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_doc_auto_generated_true",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="Companion component docs must keep `auto_generated` set to true for governed AI reference artifacts.",
        evaluator=_evaluate_component_doc_auto_generated_true,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_doc_targeted_test_file_exists",
        domain="knowledge_base",
        category="cross_reference",
        severity="error",
        description="Companion component docs must point test_coverage.targeted_test_file at an existing workspace test file.",
        evaluator=_evaluate_component_doc_targeted_test_file_exists,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_doc_test_coverage_field_set_exact",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="Companion component docs must keep the governed test_coverage field set exact.",
        evaluator=_evaluate_component_doc_test_coverage_field_set_exact,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_doc_test_coverage_status_valid",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="Companion component docs must keep test_coverage.status aligned with the governed status vocabulary.",
        evaluator=_evaluate_component_doc_test_coverage_status_valid,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_doc_test_coverage_status_matches_component_type",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="Companion component docs must keep test_coverage.status aligned with the governed component type.",
        evaluator=_evaluate_component_doc_test_coverage_status_matches_component_type,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_doc_interfaces_match_component_type",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="Companion component docs must keep interfaces aligned with the governed component type.",
        evaluator=_evaluate_component_doc_interfaces_match_component_type,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_doc_interfaces_entries_non_empty",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="Companion component docs must keep interfaces entries as non-empty string lists.",
        evaluator=_evaluate_component_doc_interfaces_entries_non_empty,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_doc_interfaces_values_are_lists",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="Companion component docs must keep interfaces values as lists.",
        evaluator=_evaluate_component_doc_interfaces_values_are_lists,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_doc_performance_metrics_match_component_type",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="Companion component docs must keep performance_metrics aligned with the governed component type.",
        evaluator=_evaluate_component_doc_performance_metrics_match_component_type,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_doc_performance_metrics_values_non_empty",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="Companion component docs must keep performance_metrics values as non-empty strings.",
        evaluator=_evaluate_component_doc_performance_metrics_values_non_empty,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_doc_file_paths_exist",
        domain="knowledge_base",
        category="cross_reference",
        severity="error",
        description="Companion component docs must point every file_paths entry at an existing workspace file.",
        evaluator=_evaluate_component_doc_file_paths_exist,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_doc_dependencies_exist",
        domain="knowledge_base",
        category="cross_reference",
        severity="error",
        description="Companion component docs must point every dependencies entry at an existing workspace path.",
        evaluator=_evaluate_component_doc_dependencies_exist,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_doc_cli_commands_valid",
        domain="knowledge_base",
        category="cross_reference",
        severity="error",
        description="Companion component docs must keep interfaces.cli entries aligned with the supported inf.work CLI command surface.",
        evaluator=_evaluate_component_doc_cli_commands_valid,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_doc_python_api_symbols_valid",
        domain="knowledge_base",
        category="cross_reference",
        severity="error",
        description="Companion component docs must keep interfaces.python_api entries aligned with symbols exported by the governed module.",
        evaluator=_evaluate_component_doc_python_api_symbols_valid,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_doc_notes_non_empty",
        domain="knowledge_base",
        category="schema",
        severity="error",
        description="Companion component docs must keep notes as a non-empty list of non-empty strings.",
        evaluator=_evaluate_component_doc_notes_non_empty,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_dependents_parity",
        domain="knowledge_base",
        category="cross_reference",
        severity="error",
        description="component_index.json dependents lists must match the live component dependency topology.",
        evaluator=_evaluate_component_index_dependents_parity,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_summary_metadata_parity",
        domain="knowledge_base",
        category="metadata",
        severity="error",
        description="component_index.json summary metadata must match the live component inventory and health-state totals.",
        evaluator=_evaluate_component_index_summary_metadata_parity,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_timestamp_metadata_parity",
        domain="knowledge_base",
        category="metadata",
        severity="error",
        description="component_index.json timestamp metadata must match live component modification state and preserve creation-to-modification ordering.",
        evaluator=_evaluate_component_index_timestamp_metadata_parity,
    ),
    ValidationRule(
        rule_id="knowledge_base.component_index_test_coverage_parity",
        domain="knowledge_base",
        category="metadata",
        severity="error",
        description="component_index.json test coverage percentages must match the canonical coverage snapshot for governed Python modules.",
        evaluator=_evaluate_component_index_test_coverage_parity,
    ),
    ValidationRule(
        rule_id="knowledge_base.kb_index_metadata_parity",
        domain="knowledge_base",
        category="cross_reference",
        severity="error",
        description="kb_index.json must stay aligned with source knowledge-base records for last-updated freshness, counts, automation success metrics, compliance stats, and lookup indices.",
        evaluator=_evaluate_kb_index_metadata_parity,
    ),
    ValidationRule(
        rule_id="knowledge_base.techniques_metadata_count_parity",
        domain="knowledge_base",
        category="metadata",
        severity="error",
        description="techniques.json metadata counts must match the catalogued technique entries.",
        evaluator=_evaluate_techniques_metadata_count_parity,
    ),
    ValidationRule(
        rule_id="knowledge_base.techniques_metadata_last_updated_parity",
        domain="knowledge_base",
        category="metadata",
        severity="error",
        description="techniques.json metadata last_updated must match the latest catalogued technique timestamp.",
        evaluator=_evaluate_techniques_metadata_last_updated_parity,
    ),
    ValidationRule(
        rule_id="knowledge_base.bug_fixes_metadata_count_parity",
        domain="knowledge_base",
        category="metadata",
        severity="error",
        description="bug_fixes.json metadata counts must match the recorded bug-fix entries.",
        evaluator=_evaluate_bug_fixes_metadata_count_parity,
    ),
    ValidationRule(
        rule_id="knowledge_base.bug_fixes_metadata_last_updated_parity",
        domain="knowledge_base",
        category="metadata",
        severity="error",
        description="bug_fixes.json metadata last_updated must match the latest recorded bug-fix timestamp.",
        evaluator=_evaluate_bug_fixes_metadata_last_updated_parity,
    ),
    ValidationRule(
        rule_id="knowledge_base.innovations_metadata_count_parity",
        domain="knowledge_base",
        category="metadata",
        severity="error",
        description="constraint_innovations.json metadata counts must match the recorded innovation entries.",
        evaluator=_evaluate_innovations_metadata_count_parity,
    ),
    ValidationRule(
        rule_id="knowledge_base.innovations_metadata_last_updated_parity",
        domain="knowledge_base",
        category="metadata",
        severity="error",
        description="constraint_innovations.json metadata last_updated must match the latest recorded innovation timestamp.",
        evaluator=_evaluate_innovations_metadata_last_updated_parity,
    ),
    ValidationRule(
        rule_id="knowledge_base.automation_patterns_metadata_count_parity",
        domain="knowledge_base",
        category="metadata",
        severity="error",
        description="automation_patterns.json metadata counts must match the recorded automation-pattern entries.",
        evaluator=_evaluate_automation_patterns_metadata_count_parity,
    ),
    ValidationRule(
        rule_id="knowledge_base.automation_patterns_metadata_last_updated_parity",
        domain="knowledge_base",
        category="metadata",
        severity="error",
        description="automation_patterns.json metadata last_updated must match the latest recorded automation-pattern timestamp.",
        evaluator=_evaluate_automation_patterns_metadata_last_updated_parity,
    ),
    ValidationRule(
        rule_id="knowledge_base.session_history_metadata_count_parity",
        domain="knowledge_base",
        category="metadata",
        severity="error",
        description="session_history.json metadata counts must match the recorded session entries.",
        evaluator=_evaluate_session_history_metadata_count_parity,
    ),
    ValidationRule(
        rule_id="knowledge_base.session_history_temporal_metadata_parity",
        domain="knowledge_base",
        category="metadata",
        severity="error",
        description="session_history.json temporal metadata must match the earliest and latest recorded session timestamps.",
        evaluator=_evaluate_session_history_temporal_metadata_parity,
    ),
]

register_rules(KNOWLEDGE_BASE_RULES)


def run_knowledge_base_rules(workspace_root: str | Path, rule_ids: set[str] | None = None) -> list[RuleResult]:
    root_path = Path(workspace_root).resolve()
    context = _build_knowledge_base_context(root_path)
    return run_registered_rules("knowledge_base", context, rule_ids)


def validate_knowledge_base(workspace_root: str | Path, rule_ids: set[str] | None = None) -> KnowledgeBaseValidationResult:
    root_path = Path(workspace_root).resolve()
    context = _build_knowledge_base_context(root_path)
    rule_results = run_registered_rules("knowledge_base", context, rule_ids)
    issues = [
        ReferenceIssue(
            source_file=finding.source_file,
            item_identifier=finding.item_identifier,
            field_name=finding.field_name,
            message=finding.message,
        )
        for rule_result in rule_results
        for finding in rule_result.findings
    ]

    return KnowledgeBaseValidationResult(
        workspace_root=str(root_path),
        compliant=not issues,
        issues=issues,
        rule_results=rule_results,
    )
