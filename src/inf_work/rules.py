from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable


RuleEvaluator = Callable[[dict[str, Any]], list["RuleFinding"]]
SEVERITY_ORDER = ["info", "warning", "error", "critical"]
RULE_PROFILE_DEFINITIONS: dict[str, dict[str, str]] = {
    "ci": {
        "description": "Run every registered rule used by the standard governance workflow.",
    },
    "status-only": {
        "description": "Run only status artifact rules.",
    },
    "resolver-only": {
        "description": "Run only resolver runtime-integrity rules.",
    },
    "component-governance": {
        "description": "Run only component governance and metadata parity rules.",
    },
    "kb-only": {
        "description": "Run only knowledge-base rules.",
    },
    "workspace-only": {
        "description": "Run only workspace coherence rules.",
    },
    "kb-cross-reference": {
        "description": "Run only knowledge-base cross-reference rules.",
    },
    "kb-metadata": {
        "description": "Run only knowledge-base source metadata parity rules.",
    },
}


@dataclass(frozen=True)
class RuleFinding:
    message: str
    source_file: str
    item_identifier: str
    field_name: str
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    domain: str
    category: str
    severity: str
    description: str
    passed: bool
    findings: list[RuleFinding]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["findings"] = [finding.to_dict() for finding in self.findings]
        return payload


@dataclass(frozen=True)
class ValidationRule:
    rule_id: str
    domain: str
    category: str
    severity: str
    description: str
    evaluator: RuleEvaluator

    def run(self, context: dict[str, Any]) -> RuleResult:
        findings = self.evaluator(context)
        return RuleResult(
            rule_id=self.rule_id,
            domain=self.domain,
            category=self.category,
            severity=self.severity,
            description=self.description,
            passed=not findings,
            findings=findings,
        )


_RULE_REGISTRY: dict[str, dict[str, ValidationRule]] = {}


def register_rule(rule: ValidationRule) -> None:
    domain_registry = _RULE_REGISTRY.setdefault(rule.domain, {})
    domain_registry[rule.rule_id] = rule


def register_rules(rules: list[ValidationRule]) -> None:
    for rule in rules:
        register_rule(rule)


def get_registered_rules(domain: str | None = None, rule_ids: set[str] | None = None) -> list[ValidationRule]:
    if domain is not None:
        domain_rules = list(_RULE_REGISTRY.get(domain, {}).values())
        if rule_ids is None:
            return domain_rules
        return [rule for rule in domain_rules if rule.rule_id in rule_ids]

    registered_rules: list[ValidationRule] = []
    for domain_rules in _RULE_REGISTRY.values():
        registered_rules.extend(domain_rules.values())
    if rule_ids is not None:
        registered_rules = [rule for rule in registered_rules if rule.rule_id in rule_ids]
    return registered_rules


def run_registered_rules(domain: str, context: dict[str, Any], rule_ids: set[str] | None = None) -> list[RuleResult]:
    return [rule.run(context) for rule in get_registered_rules(domain, rule_ids)]


def get_rule_profiles() -> dict[str, dict[str, Any]]:
    knowledge_base_rules = get_registered_rules(domain="knowledge_base")
    status_rules = get_registered_rules(domain="status")
    workspace_rules = get_registered_rules(domain="workspace")
    all_rules = get_registered_rules()

    profile_rule_ids: dict[str, set[str]] = {
        "ci": {rule.rule_id for rule in all_rules},
        "status-only": {rule.rule_id for rule in status_rules},
        "resolver-only": {
            rule.rule_id
            for rule in status_rules
            if rule.category == "runtime_integrity"
        },
        "component-governance": {
            rule.rule_id
            for rule in knowledge_base_rules
            if rule.rule_id in {
                "knowledge_base.component_doc_auto_generated_true",
                "knowledge_base.component_doc_cli_commands_valid",
                "knowledge_base.component_doc_dependencies_exist",
                "knowledge_base.component_doc_field_set_exact",
                "knowledge_base.component_doc_file_paths_exist",
                "knowledge_base.component_doc_interfaces_entries_non_empty",
                "knowledge_base.component_doc_interfaces_match_component_type",
                "knowledge_base.component_doc_interfaces_values_are_lists",
                "knowledge_base.component_doc_notes_non_empty",
                "knowledge_base.component_doc_performance_metrics_match_component_type",
                "knowledge_base.component_doc_performance_metrics_values_non_empty",
                "knowledge_base.component_doc_required_fields_present",
                "knowledge_base.component_doc_test_coverage_field_set_exact",
                "knowledge_base.component_doc_test_coverage_status_matches_component_type",
                "knowledge_base.component_doc_test_coverage_status_valid",
                "knowledge_base.component_index_dependents_entries_non_empty",
                "knowledge_base.component_index_dependencies_entries_non_empty",
                "knowledge_base.component_index_documentation_path_non_empty",
                "knowledge_base.component_index_file_path_non_empty",
                "knowledge_base.component_index_file_path_unique",
                "knowledge_base.component_index_component_id_non_empty",
                "knowledge_base.component_index_component_id_unique",
                "knowledge_base.component_index_component_name_non_empty",
                "knowledge_base.component_index_component_name_unique",
                "knowledge_base.component_index_component_type_valid",
                "knowledge_base.component_index_dependencies_entries_unique",
                "knowledge_base.component_index_health_status_valid",
                "knowledge_base.component_index_compliance_status_valid",
                "knowledge_base.component_index_complexity_score_non_negative_int",
                "knowledge_base.component_index_test_coverage_percentage_valid",
                "knowledge_base.component_index_timestamp_fields_valid",
                "knowledge_base.component_index_known_issues_entries_non_empty",
                "knowledge_base.component_index_related_techniques_entries_non_empty",
                "knowledge_base.component_index_performance_metrics_field_set_exact",
                "knowledge_base.component_index_performance_metrics_values_non_empty",
                "knowledge_base.component_doc_python_api_symbols_valid",
                "knowledge_base.component_doc_targeted_test_file_exists",
                "knowledge_base.component_index_dependents_parity",
                "knowledge_base.component_index_summary_metadata_parity",
                "knowledge_base.component_index_test_coverage_parity",
                "knowledge_base.component_index_timestamp_metadata_parity",
                "knowledge_base.component_related_techniques_exist",
                "knowledge_base.component_doc_metadata_parity",
            }
        },
        "kb-only": {rule.rule_id for rule in knowledge_base_rules},
        "workspace-only": {rule.rule_id for rule in workspace_rules},
        "kb-cross-reference": {
            rule.rule_id
            for rule in knowledge_base_rules
            if rule.category == "cross_reference"
        },
        "kb-metadata": {
            rule.rule_id
            for rule in knowledge_base_rules
            if rule.category == "metadata"
        },
    }

    return {
        profile_name: {
            "description": RULE_PROFILE_DEFINITIONS[profile_name]["description"],
            "rule_ids": sorted(profile_rule_ids[profile_name]),
        }
        for profile_name in RULE_PROFILE_DEFINITIONS
    }


def resolve_rule_selection(
    *,
    profile_names: list[str] | None = None,
    rule_ids: list[str] | None = None,
) -> set[str] | None:
    selected_rule_ids = set(rule_ids or [])
    profiles = get_rule_profiles()

    for profile_name in profile_names or []:
        selected_rule_ids.update(profiles[profile_name]["rule_ids"])

    return selected_rule_ids or None


def severity_at_or_above(severity: str, threshold: str) -> bool:
    if threshold == "none":
        return False
    return SEVERITY_ORDER.index(severity) >= SEVERITY_ORDER.index(threshold)


def should_fail_rule_results(rule_results: list[RuleResult], fail_on: str) -> bool:
    return any(
        (not rule_result.passed) and severity_at_or_above(rule_result.severity, fail_on)
        for rule_result in rule_results
    )


def filter_rule_results(
    rule_results: list[RuleResult],
    *,
    categories: set[str] | None = None,
    severities: set[str] | None = None,
    domains: set[str] | None = None,
    only_failures: bool = False,
) -> list[RuleResult]:
    filtered_results: list[RuleResult] = []
    for rule_result in rule_results:
        if categories is not None and rule_result.category not in categories:
            continue
        if severities is not None and rule_result.severity not in severities:
            continue
        if domains is not None and rule_result.domain not in domains:
            continue
        if only_failures and rule_result.passed:
            continue
        filtered_results.append(rule_result)
    return filtered_results


def _empty_bucket() -> dict[str, int]:
    return {"rules": 0, "failed_rules": 0, "findings": 0}


def _increment_bucket(bucket: dict[str, int], rule_result: RuleResult) -> None:
    bucket["rules"] += 1
    bucket["findings"] += len(rule_result.findings)
    if not rule_result.passed:
        bucket["failed_rules"] += 1


def summarize_rule_results(rule_results: list[RuleResult]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "total_rules": len(rule_results),
        "passed_rules": sum(1 for rule_result in rule_results if rule_result.passed),
        "failed_rules": sum(1 for rule_result in rule_results if not rule_result.passed),
        "total_findings": sum(len(rule_result.findings) for rule_result in rule_results),
        "by_domain": {},
        "by_category": {},
        "by_severity": {},
    }

    for rule_result in rule_results:
        domain_bucket = summary["by_domain"].setdefault(rule_result.domain, _empty_bucket())
        category_bucket = summary["by_category"].setdefault(rule_result.category, _empty_bucket())
        severity_bucket = summary["by_severity"].setdefault(rule_result.severity, _empty_bucket())
        _increment_bucket(domain_bucket, rule_result)
        _increment_bucket(category_bucket, rule_result)
        _increment_bucket(severity_bucket, rule_result)

    return summary
