from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from inf_work.kb_integrity import run_knowledge_base_rules
from inf_work.rules import (
    RuleFinding,
    RuleResult,
    ValidationRule,
    filter_rule_results,
    get_registered_rules,
    get_rule_profiles,
    resolve_rule_selection,
    should_fail_rule_results,
    summarize_rule_results,
)
from inf_work.workspace_health import run_workspace_rules


BASE_TIMESTAMP = "2026-03-31T00:00:00Z"


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def make_rule_result(
    *,
    rule_id: str,
    domain: str,
    category: str = "governance",
    severity: str = "warning",
    description: str = "description",
    passed: bool = True,
    findings: list[RuleFinding] | None = None,
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        domain=domain,
        category=category,
        severity=severity,
        description=description,
        passed=passed,
        findings=[] if findings is None else findings,
    )


def create_workspace(tmp_path: Path, *, broken_reference: bool = False) -> Path:
    (tmp_path / "ai_docs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "knowledge_base").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "build").mkdir(parents=True, exist_ok=True)

    write_json(
        tmp_path / "core_reference.json",
        {
            "workspace_governance": {
                "directory_structure": {
                    "ai_docs/": "AI docs",
                    "knowledge_base/": "Knowledge base",
                    "src/": "Source code",
                    "tests/": "Tests",
                    "config/": "Configuration",
                    "build/": "Build artifacts",
                }
            },
            "documentation_schemas": {
                "ai_reference_format": {
                    "required_fields": [
                        "component_id",
                        "creation_timestamp",
                        "dependencies",
                        "interfaces",
                        "performance_metrics",
                        "test_coverage",
                        "compliance_status",
                        "auto_generated",
                    ]
                }
            }
        },
    )
    write_json(
        tmp_path / "knowledge_base" / "techniques.json",
        {
            "techniques": [
                {
                    "id": "technique_alpha",
                    "name": "Technique Alpha",
                    "category": "architectural",
                    "created_timestamp": BASE_TIMESTAMP,
                    "constraints_compliance": ["I1", "I2", "I3", "I4"],
                }
            ],
            "metadata": {"total_count": 1, "last_updated": BASE_TIMESTAMP},
        },
    )
    write_json(
        tmp_path / "knowledge_base" / "bug_fixes.json",
        {
            "bug_fixes": [
                {
                    "id": "bug_fix_alpha",
                    "error_code": 1100,
                    "created_timestamp": BASE_TIMESTAMP,
                    "solution_technique": "Missing Technique" if broken_reference else "Technique Alpha",
                }
            ],
            "metadata": {"total_count": 1, "last_updated": BASE_TIMESTAMP},
        },
    )
    write_json(
        tmp_path / "knowledge_base" / "constraint_innovations.json",
        {
            "innovations": [
                {
                    "id": "innovation_alpha",
                    "creative_solution": "Technique Alpha",
                    "created_timestamp": BASE_TIMESTAMP,
                    "constraint_challenged": ["I1"],
                }
            ],
            "metadata": {"total_count": 1, "last_updated": BASE_TIMESTAMP},
        },
    )
    write_json(
        tmp_path / "knowledge_base" / "automation_patterns.json",
        {
            "automation_patterns": [
                {
                    "id": "automation_alpha",
                    "automation_type": "validation",
                    "pattern_name": "Automation Alpha",
                    "created_timestamp": BASE_TIMESTAMP,
                    "success_rate": 1.0,
                    "false_positive_rate": 0.0,
                    "related_techniques": ["technique_alpha"],
                }
            ],
            "metadata": {"total_count": 1, "last_updated": BASE_TIMESTAMP},
        },
    )
    write_json(
        tmp_path / "knowledge_base" / "session_history.json",
        {
            "sessions": [
                {
                    "session_id": "session_alpha",
                    "created_timestamp": BASE_TIMESTAMP,
                    "summary": "Session Alpha",
                }
            ],
            "metadata": {"total_sessions": 1, "first_session": BASE_TIMESTAMP, "last_session": BASE_TIMESTAMP},
        },
    )
    write_json(
        tmp_path / "knowledge_base" / "kb_index.json",
        {
            "last_updated": BASE_TIMESTAMP,
            "total_techniques": 1,
            "total_bug_fixes": 1,
            "total_innovations": 1,
            "total_automation_patterns": 1,
            "constraint_compliance_stats": {
                "I1_compliant": 1,
                "I2_compliant": 1,
                "I3_compliant": 1,
                "I4_compliant": 1,
                "all_compliant": 1,
            },
            "automation_success_metrics": {
                "total_automated_actions": 1,
                "successful_automations": 1,
                "failed_automations": 0,
                "success_rate": 1.0,
            },
            "lookup_indices": {
                "by_category": {
                    "architectural": ["technique_alpha"],
                    "innovation": ["innovation_alpha"],
                },
                "by_constraint": {
                    "I1": ["innovation_alpha", "technique_alpha"],
                    "I2": ["technique_alpha"],
                    "I3": ["technique_alpha"],
                    "I4": ["technique_alpha"],
                },
                "by_error_code": {
                    "1100": ["bug_fix_alpha"]
                },
                "by_automation_type": {
                    "validation": ["automation_alpha"]
                },
            },
        },
    )
    write_json(
        tmp_path / "ai_docs" / "component_index.json",
        {
            "components": [
                {
                    "component_id": "component_alpha",
                    "component_name": "Component Alpha",
                    "component_type": "python_module",
                    "file_path": "src/component_alpha.py",
                    "dependencies": [],
                    "dependents": [],
                    "known_issues": [],
                    "creation_timestamp": BASE_TIMESTAMP,
                    "last_modified_timestamp": BASE_TIMESTAMP,
                    "documentation_path": "ai_docs/component_alpha.json",
                    "health_status": "healthy",
                    "test_coverage_percentage": 100,
                    "compliance_status": "I1_I2_I3_I4_compliant",
                    "related_techniques": ["technique_alpha"],
                }
            ],
            "metadata": {"total_components": 1, "last_updated": BASE_TIMESTAMP},
            "health_status": {"total_healthy": 1, "total_degraded": 0, "total_failing": 0},
        },
    )
    write_json(
        tmp_path / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "python_module",
            "creation_timestamp": BASE_TIMESTAMP,
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": [],
            "interfaces": {"python_api": ["run() -> None"]},
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "targeted_tests_added"},
            "auto_generated": True,
            "file_paths": ["src/component_alpha.py"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Component Alpha remains synchronized with the component index."],
        },
    )
    write_json(
        tmp_path / "ai_docs" / "test_coverage_snapshot.json",
        {
            "generated_at": BASE_TIMESTAMP,
            "workspace_root": str(tmp_path),
            "coverage_command": "/venv/bin/python -m pytest --cov=src/inf_work --cov-report=json",
            "coverage_source": "ai_docs/test_coverage_snapshot.json",
            "module_coverage": [
                {
                    "module_path": "src/component_alpha.py",
                    "coverage_percentage": 100,
                    "num_statements": 10,
                    "covered_lines": 10,
                    "missing_lines": 0,
                }
            ],
            "totals": {
                "coverage_percentage": 100,
                "num_statements": 10,
                "covered_lines": 10,
                "missing_lines": 0,
            },
            "metadata": {"total_modules": 1, "schema_version": "2.0.0"},
        },
    )
    (tmp_path / "src" / "component_alpha.py").write_text("def run() -> None:\n    return None\n", encoding="utf-8")
    (tmp_path / "tests" / "test_component_alpha.py").write_text(
        "from component_alpha import run\n\n\ndef test_run() -> None:\n    assert run() is None\n",
        encoding="utf-8",
    )
    return tmp_path


def test_rule_registry_contains_workspace_and_kb_rules() -> None:
    rule_ids = {rule.rule_id for rule in get_registered_rules()}

    assert "workspace.required_directories_present" in rule_ids
    assert "knowledge_base.bug_fix_solution_technique_exists" in rule_ids
    assert "knowledge_base.component_related_techniques_exist" in rule_ids
    assert "knowledge_base.component_doc_metadata_parity" in rule_ids
    assert "knowledge_base.component_doc_auto_generated_true" in rule_ids
    assert "knowledge_base.component_doc_cli_commands_valid" in rule_ids
    assert "knowledge_base.component_doc_dependencies_exist" in rule_ids
    assert "knowledge_base.component_doc_field_set_exact" in rule_ids
    assert "knowledge_base.component_doc_file_paths_exist" in rule_ids
    assert "knowledge_base.component_doc_interfaces_entries_non_empty" in rule_ids
    assert "knowledge_base.component_doc_interfaces_match_component_type" in rule_ids
    assert "knowledge_base.component_doc_interfaces_values_are_lists" in rule_ids
    assert "knowledge_base.component_doc_notes_non_empty" in rule_ids
    assert "knowledge_base.component_doc_performance_metrics_match_component_type" in rule_ids
    assert "knowledge_base.component_doc_performance_metrics_values_non_empty" in rule_ids
    assert "knowledge_base.component_doc_python_api_symbols_valid" in rule_ids
    assert "knowledge_base.component_doc_required_fields_present" in rule_ids
    assert "knowledge_base.component_doc_test_coverage_field_set_exact" in rule_ids
    assert "knowledge_base.component_doc_test_coverage_status_matches_component_type" in rule_ids
    assert "knowledge_base.component_doc_test_coverage_status_valid" in rule_ids
    assert "knowledge_base.component_doc_targeted_test_file_exists" in rule_ids
    assert "knowledge_base.component_index_dependents_entries_non_empty" in rule_ids
    assert "knowledge_base.component_index_related_techniques_entries_non_empty" in rule_ids
    assert "knowledge_base.component_index_dependents_parity" in rule_ids
    assert "knowledge_base.component_index_dependencies_entries_non_empty" in rule_ids
    assert "knowledge_base.component_index_documentation_path_non_empty" in rule_ids
    assert "knowledge_base.component_index_file_path_non_empty" in rule_ids
    assert "knowledge_base.component_index_file_path_unique" in rule_ids
    assert "knowledge_base.component_index_component_id_non_empty" in rule_ids
    assert "knowledge_base.component_index_component_id_unique" in rule_ids
    assert "knowledge_base.component_index_component_name_non_empty" in rule_ids
    assert "knowledge_base.component_index_component_name_unique" in rule_ids
    assert "knowledge_base.component_index_component_type_valid" in rule_ids
    assert "knowledge_base.component_index_dependencies_entries_unique" in rule_ids
    assert "knowledge_base.component_index_health_status_valid" in rule_ids
    assert "knowledge_base.component_index_compliance_status_valid" in rule_ids
    assert "knowledge_base.component_index_complexity_score_non_negative_int" in rule_ids
    assert "knowledge_base.component_index_test_coverage_percentage_valid" in rule_ids
    assert "knowledge_base.component_index_timestamp_fields_valid" in rule_ids
    assert "knowledge_base.component_index_known_issues_entries_non_empty" in rule_ids
    assert "knowledge_base.component_index_performance_metrics_field_set_exact" in rule_ids
    assert "knowledge_base.component_index_performance_metrics_values_non_empty" in rule_ids
    assert "knowledge_base.component_index_summary_metadata_parity" in rule_ids
    assert "knowledge_base.component_index_test_coverage_parity" in rule_ids
    assert "knowledge_base.component_index_timestamp_metadata_parity" in rule_ids
    assert "knowledge_base.kb_index_metadata_parity" in rule_ids
    assert "knowledge_base.automation_patterns_metadata_count_parity" in rule_ids
    assert "knowledge_base.automation_patterns_metadata_last_updated_parity" in rule_ids
    assert "knowledge_base.bug_fixes_metadata_last_updated_parity" in rule_ids
    assert "knowledge_base.session_history_metadata_count_parity" in rule_ids
    assert "knowledge_base.session_history_temporal_metadata_parity" in rule_ids
    assert "knowledge_base.techniques_metadata_last_updated_parity" in rule_ids
    assert "knowledge_base.innovations_metadata_last_updated_parity" in rule_ids
    assert "status.artifacts_exist" in rule_ids
    assert "status.summary_matches_workspace" in rule_ids
    assert "status.resolver_explicit_route_integrity" in rule_ids
    assert "status.resolver_inferred_route_integrity" in rule_ids


def test_rule_finding_to_dict_round_trips_context() -> None:
    finding = RuleFinding(
        message="message",
        source_file="source.json",
        item_identifier="item",
        field_name="field",
        context={"severity": "warning"},
    )

    assert finding.to_dict() == {
        "message": "message",
        "source_file": "source.json",
        "item_identifier": "item",
        "field_name": "field",
        "context": {"severity": "warning"},
    }


def test_rule_result_to_dict_serializes_nested_findings() -> None:
    result = make_rule_result(
        rule_id="workspace.rule",
        domain="workspace",
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

    payload = result.to_dict()

    assert payload["rule_id"] == "workspace.rule"
    assert payload["findings"][0]["field_name"] == "field"


def test_get_registered_rules_filters_by_rule_ids() -> None:
    selected = get_registered_rules(rule_ids={"workspace.required_directories_present"})

    assert selected
    assert {rule.rule_id for rule in selected} == {"workspace.required_directories_present"}


def test_filter_rule_results_filters_severity_and_domain() -> None:
    passing = make_rule_result(rule_id="workspace.ok", domain="workspace", description="ok")
    failing = make_rule_result(
        rule_id="status.fail",
        domain="status",
        category="artifact_integrity",
        severity="error",
        description="fail",
        passed=False,
    )

    filtered = filter_rule_results(
        [passing, failing],
        severities={"error"},
        domains={"status"},
    )

    assert filtered == [failing]


def test_filter_rule_results_skips_domain_mismatches_after_severity_match() -> None:
    wrong_domain = make_rule_result(
        rule_id="workspace.error",
        domain="workspace",
        severity="error",
        description="wrong domain",
        passed=False,
    )
    matching = make_rule_result(
        rule_id="status.error",
        domain="status",
        severity="error",
        description="matching domain",
        passed=False,
    )

    filtered = filter_rule_results(
        [wrong_domain, matching],
        severities={"error"},
        domains={"status"},
    )

    assert filtered == [matching]


def test_rule_profiles_expand_to_stable_rule_sets() -> None:
    profiles = get_rule_profiles()

    assert "ci" in profiles
    assert "status-only" in profiles
    assert "resolver-only" in profiles
    assert "component-governance" in profiles
    assert "kb-metadata" in profiles
    assert profiles["workspace-only"]["rule_ids"] == ["workspace.required_directories_present"]
    assert "status.artifacts_exist" in profiles["status-only"]["rule_ids"]
    assert profiles["resolver-only"]["rule_ids"] == [
        "status.resolver_explicit_route_integrity",
        "status.resolver_inferred_route_integrity",
    ]
    assert profiles["component-governance"]["rule_ids"] == [
        "knowledge_base.component_doc_auto_generated_true",
        "knowledge_base.component_doc_cli_commands_valid",
        "knowledge_base.component_doc_dependencies_exist",
        "knowledge_base.component_doc_field_set_exact",
        "knowledge_base.component_doc_file_paths_exist",
        "knowledge_base.component_doc_interfaces_entries_non_empty",
        "knowledge_base.component_doc_interfaces_match_component_type",
        "knowledge_base.component_doc_interfaces_values_are_lists",
        "knowledge_base.component_doc_metadata_parity",
        "knowledge_base.component_doc_notes_non_empty",
        "knowledge_base.component_doc_performance_metrics_match_component_type",
        "knowledge_base.component_doc_performance_metrics_values_non_empty",
        "knowledge_base.component_doc_python_api_symbols_valid",
        "knowledge_base.component_doc_required_fields_present",
        "knowledge_base.component_doc_targeted_test_file_exists",
        "knowledge_base.component_doc_test_coverage_field_set_exact",
        "knowledge_base.component_doc_test_coverage_status_matches_component_type",
        "knowledge_base.component_doc_test_coverage_status_valid",
        "knowledge_base.component_index_complexity_score_non_negative_int",
        "knowledge_base.component_index_compliance_status_valid",
        "knowledge_base.component_index_component_id_non_empty",
        "knowledge_base.component_index_component_id_unique",
        "knowledge_base.component_index_component_name_non_empty",
        "knowledge_base.component_index_component_name_unique",
        "knowledge_base.component_index_component_type_valid",
        "knowledge_base.component_index_dependencies_entries_non_empty",
        "knowledge_base.component_index_dependencies_entries_unique",
        "knowledge_base.component_index_dependents_entries_non_empty",
        "knowledge_base.component_index_dependents_parity",
        "knowledge_base.component_index_documentation_path_non_empty",
        "knowledge_base.component_index_file_path_non_empty",
        "knowledge_base.component_index_file_path_unique",
        "knowledge_base.component_index_health_status_valid",
        "knowledge_base.component_index_known_issues_entries_non_empty",
        "knowledge_base.component_index_performance_metrics_field_set_exact",
        "knowledge_base.component_index_performance_metrics_values_non_empty",
        "knowledge_base.component_index_related_techniques_entries_non_empty",
        "knowledge_base.component_index_summary_metadata_parity",
        "knowledge_base.component_index_test_coverage_parity",
        "knowledge_base.component_index_test_coverage_percentage_valid",
        "knowledge_base.component_index_timestamp_fields_valid",
        "knowledge_base.component_index_timestamp_metadata_parity",
        "knowledge_base.component_related_techniques_exist",
    ]
    assert "knowledge_base.bug_fix_solution_technique_exists" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_doc_auto_generated_true" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_doc_cli_commands_valid" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_doc_dependencies_exist" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_doc_field_set_exact" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_doc_file_paths_exist" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_doc_interfaces_entries_non_empty" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_doc_interfaces_match_component_type" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_doc_interfaces_values_are_lists" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_doc_metadata_parity" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_doc_notes_non_empty" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_doc_performance_metrics_match_component_type" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_doc_performance_metrics_values_non_empty" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_doc_python_api_symbols_valid" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_doc_required_fields_present" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_doc_test_coverage_field_set_exact" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_doc_test_coverage_status_matches_component_type" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_doc_test_coverage_status_valid" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_complexity_score_non_negative_int" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_component_id_non_empty" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_component_id_unique" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_component_type_valid" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_test_coverage_percentage_valid" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_timestamp_fields_valid" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_dependents_entries_non_empty" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_dependencies_entries_non_empty" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_dependencies_entries_unique" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_compliance_status_valid" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_component_name_non_empty" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_component_name_unique" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_documentation_path_non_empty" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_health_status_valid" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_known_issues_entries_non_empty" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_related_techniques_entries_non_empty" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_performance_metrics_field_set_exact" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_performance_metrics_values_non_empty" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_index_file_path_unique" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.component_doc_targeted_test_file_exists" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.kb_index_metadata_parity" in profiles["kb-only"]["rule_ids"]
    assert "knowledge_base.kb_index_metadata_parity" in profiles["kb-cross-reference"]["rule_ids"]
    assert profiles["kb-metadata"]["rule_ids"] == [
        "knowledge_base.automation_patterns_metadata_count_parity",
        "knowledge_base.automation_patterns_metadata_last_updated_parity",
        "knowledge_base.bug_fixes_metadata_count_parity",
        "knowledge_base.bug_fixes_metadata_last_updated_parity",
        "knowledge_base.component_index_summary_metadata_parity",
        "knowledge_base.component_index_test_coverage_parity",
        "knowledge_base.component_index_timestamp_metadata_parity",
        "knowledge_base.innovations_metadata_count_parity",
        "knowledge_base.innovations_metadata_last_updated_parity",
        "knowledge_base.session_history_metadata_count_parity",
        "knowledge_base.session_history_temporal_metadata_parity",
        "knowledge_base.techniques_metadata_count_parity",
        "knowledge_base.techniques_metadata_last_updated_parity",
    ]
    assert all(rule_id.startswith("knowledge_base.") for rule_id in profiles["kb-cross-reference"]["rule_ids"])


def test_rule_selection_can_merge_profiles_and_explicit_ids() -> None:
    selected_rule_ids = resolve_rule_selection(
        profile_names=["workspace-only"],
        rule_ids=["knowledge_base.bug_fix_solution_technique_exists"],
    )

    assert selected_rule_ids == {
        "workspace.required_directories_present",
        "knowledge_base.bug_fix_solution_technique_exists",
    }


def test_workspace_rules_report_missing_directories(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    (workspace_root / "build").rmdir()

    rule_results = run_workspace_rules(workspace_root)

    assert len(rule_results) == 1
    assert rule_results[0].passed is False
    assert rule_results[0].findings[0].item_identifier == "build"


def test_rule_runner_can_select_specific_rule_ids(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path, broken_reference=True)

    rule_results = run_knowledge_base_rules(
        workspace_root,
        {"knowledge_base.bug_fix_solution_technique_exists"},
    )

    assert len(rule_results) == 1
    assert rule_results[0].rule_id == "knowledge_base.bug_fix_solution_technique_exists"
    assert rule_results[0].passed is False


def test_kb_rules_report_broken_references(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path, broken_reference=True)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.bug_fix_solution_technique_exists"
    assert failing_results[0].findings[0].field_name == "solution_technique"


def test_kb_rules_report_component_doc_parity_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Drifted Alpha",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-30T00:00:00Z",
            "compliance_status": "violations_detected",
            "dependencies": ["src/component_alpha.py"],
            "interfaces": {"python_api": ["run() -> None"]},
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "targeted_tests_added"},
            "auto_generated": True,
            "file_paths": ["src/component_alpha.py"],
            "related_techniques": ["technique_beta"],
            "notes": ["Metadata drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_metadata_parity"
    failing_fields = {finding.field_name for finding in failing_results[0].findings}
    assert {"component_name", "creation_timestamp", "compliance_status", "dependencies", "related_techniques"}.issubset(failing_fields)


def test_kb_rules_report_component_doc_required_field_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": [],
            "interfaces": {"python_api": ["run() -> None"]},
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "auto_generated": True,
            "file_paths": ["src/component_alpha.py"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Required-field drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_required_fields_present"
    assert {finding.field_name for finding in failing_results[0].findings} == {"test_coverage"}


def test_kb_rules_report_component_doc_field_set_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_alpha.json").read_text(encoding="utf-8"))
    payload["unexpected_field"] = "drift"
    write_json(workspace_root / "ai_docs" / "component_alpha.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_field_set_exact"
    assert {finding.field_name for finding in failing_results[0].findings} == {"__root__"}


def test_kb_rules_report_component_doc_auto_generated_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": [],
            "interfaces": {"python_api": ["run() -> None"]},
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "targeted_tests_added"},
            "auto_generated": False,
            "file_paths": ["src/component_alpha.py"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Auto-generated drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_auto_generated_true"
    assert {finding.field_name for finding in failing_results[0].findings} == {"auto_generated"}


def test_kb_rules_report_component_doc_targeted_test_file_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": [],
            "interfaces": {"python_api": ["run() -> None"]},
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_missing_component_alpha.py", "status": "targeted_tests_added"},
            "auto_generated": True,
            "file_paths": ["src/component_alpha.py"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Targeted-test drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_targeted_test_file_exists"
    assert {finding.field_name for finding in failing_results[0].findings} == {"test_coverage.targeted_test_file"}


def test_kb_rules_report_component_doc_test_coverage_field_set_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_alpha.json").read_text(encoding="utf-8"))
    payload["test_coverage"]["unexpected_field"] = "drift"
    write_json(workspace_root / "ai_docs" / "component_alpha.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_test_coverage_field_set_exact"
    assert {finding.field_name for finding in failing_results[0].findings} == {"test_coverage"}


def test_kb_rules_report_component_doc_test_coverage_status_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": [],
            "interfaces": {"python_api": ["run() -> None"]},
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "manual_guess"},
            "auto_generated": True,
            "file_paths": ["src/component_alpha.py"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Coverage-status drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_test_coverage_status_valid"
    assert {finding.field_name for finding in failing_results[0].findings} == {"test_coverage.status"}


def test_kb_rules_report_component_doc_test_coverage_status_component_type_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": [],
            "interfaces": {"python_api": ["run() -> None"]},
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "generated_output_verified"},
            "auto_generated": True,
            "file_paths": ["src/component_alpha.py"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Coverage-status component-type drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_test_coverage_status_matches_component_type"
    assert {finding.field_name for finding in failing_results[0].findings} == {"test_coverage.status"}


def test_kb_rules_report_component_doc_interfaces_component_type_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": [],
            "interfaces": {"cli": []},
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "targeted_tests_added"},
            "auto_generated": True,
            "file_paths": ["src/component_alpha.py"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Interfaces component-type drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_interfaces_match_component_type"
    assert {finding.field_name for finding in failing_results[0].findings} == {"interfaces.python_api"}


def test_kb_rules_report_governance_artifact_interface_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_index.json",
        {
            "components": [
                {
                    "component_id": "component_alpha",
                    "component_name": "Component Alpha",
                    "component_type": "governance_artifact",
                    "file_path": "SYSTEM_ALPHA.md",
                    "dependencies": ["ai_docs/component_alpha_snapshot.json"],
                    "dependents": [],
                    "creation_timestamp": "2026-03-31T00:00:00Z",
                    "last_modified_timestamp": "2026-03-31T00:00:00Z",
                    "documentation_path": "ai_docs/component_alpha.json",
                    "health_status": "healthy",
                    "test_coverage_percentage": 100,
                    "compliance_status": "I1_I2_I3_I4_compliant",
                    "related_techniques": ["technique_alpha"],
                }
            ],
            "metadata": {"total_components": 1, "last_updated": "2026-03-31T00:00:00Z"},
            "health_status": {"total_healthy": 1, "total_degraded": 0, "total_failing": 0},
        },
    )
    (workspace_root / "SYSTEM_ALPHA.md").write_text("# Alpha\n", encoding="utf-8")
    write_json(workspace_root / "ai_docs" / "component_alpha_snapshot.json", {"status": "ok"})
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "governance_artifact",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": ["ai_docs/component_alpha_snapshot.json"],
            "interfaces": {"artifact": ["SYSTEM_ALPHA.md"]},
            "performance_metrics": {"generation_frequency": "on demand", "storage_pattern": "derived markdown"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "generated_output_verified"},
            "auto_generated": True,
            "file_paths": ["SYSTEM_ALPHA.md", "ai_docs/component_alpha_snapshot.json"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Governance-artifact interface drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_interfaces_match_component_type"
    assert {finding.field_name for finding in failing_results[0].findings} == {"interfaces.source_of_truth"}


def test_kb_rules_report_component_doc_interface_value_type_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": [],
            "interfaces": {"python_api": "run() -> None", "cli": []},
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "targeted_tests_added"},
            "auto_generated": True,
            "file_paths": ["src/component_alpha.py"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Interface value-type drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_interfaces_values_are_lists"
    assert {finding.field_name for finding in failing_results[0].findings} == {"interfaces.python_api"}


def test_kb_rules_report_governance_artifact_interface_value_type_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_index.json",
        {
            "components": [
                {
                    "component_id": "component_alpha",
                    "component_name": "Component Alpha",
                    "component_type": "governance_artifact",
                    "file_path": "SYSTEM_ALPHA.md",
                    "dependencies": ["ai_docs/component_alpha_snapshot.json"],
                    "dependents": [],
                    "creation_timestamp": "2026-03-31T00:00:00Z",
                    "last_modified_timestamp": "2026-03-31T00:00:00Z",
                    "documentation_path": "ai_docs/component_alpha.json",
                    "health_status": "healthy",
                    "test_coverage_percentage": 100,
                    "compliance_status": "I1_I2_I3_I4_compliant",
                    "related_techniques": ["technique_alpha"],
                }
            ],
            "metadata": {"total_components": 1, "last_updated": "2026-03-31T00:00:00Z"},
            "health_status": {"total_healthy": 1, "total_degraded": 0, "total_failing": 0},
        },
    )
    (workspace_root / "SYSTEM_ALPHA.md").write_text("# Alpha\n", encoding="utf-8")
    write_json(workspace_root / "ai_docs" / "component_alpha_snapshot.json", {"status": "ok"})
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "governance_artifact",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": ["ai_docs/component_alpha_snapshot.json"],
            "interfaces": {
                "artifact": ["SYSTEM_ALPHA.md"],
                "source_of_truth": "ai_docs/component_alpha_snapshot.json"
            },
            "performance_metrics": {"generation_frequency": "on demand", "storage_pattern": "derived markdown"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "generated_output_verified"},
            "auto_generated": True,
            "file_paths": ["SYSTEM_ALPHA.md", "ai_docs/component_alpha_snapshot.json"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Governance-artifact interface value-type drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_interfaces_values_are_lists"
    assert {finding.field_name for finding in failing_results[0].findings} == {"interfaces.source_of_truth"}


def test_kb_rules_report_component_doc_interface_entries_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": [],
            "interfaces": {"python_api": [""], "cli": []},
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "targeted_tests_added"},
            "auto_generated": True,
            "file_paths": ["src/component_alpha.py"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Interface entry drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_interfaces_entries_non_empty"
    assert {finding.field_name for finding in failing_results[0].findings} == {"interfaces.python_api"}


def test_kb_rules_report_governance_artifact_interface_entries_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_index.json",
        {
            "components": [
                {
                    "component_id": "component_alpha",
                    "component_name": "Component Alpha",
                    "component_type": "governance_artifact",
                    "file_path": "SYSTEM_ALPHA.md",
                    "dependencies": ["ai_docs/component_alpha_snapshot.json"],
                    "dependents": [],
                    "creation_timestamp": "2026-03-31T00:00:00Z",
                    "last_modified_timestamp": "2026-03-31T00:00:00Z",
                    "documentation_path": "ai_docs/component_alpha.json",
                    "health_status": "healthy",
                    "test_coverage_percentage": 100,
                    "compliance_status": "I1_I2_I3_I4_compliant",
                    "related_techniques": ["technique_alpha"],
                }
            ],
            "metadata": {"total_components": 1, "last_updated": "2026-03-31T00:00:00Z"},
            "health_status": {"total_healthy": 1, "total_degraded": 0, "total_failing": 0},
        },
    )
    (workspace_root / "SYSTEM_ALPHA.md").write_text("# Alpha\n", encoding="utf-8")
    write_json(workspace_root / "ai_docs" / "component_alpha_snapshot.json", {"status": "ok"})
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "governance_artifact",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": ["ai_docs/component_alpha_snapshot.json"],
            "interfaces": {
                "artifact": ["SYSTEM_ALPHA.md"],
                "source_of_truth": [""]
            },
            "performance_metrics": {"generation_frequency": "on demand", "storage_pattern": "derived markdown"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "generated_output_verified"},
            "auto_generated": True,
            "file_paths": ["SYSTEM_ALPHA.md", "ai_docs/component_alpha_snapshot.json"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Governance-artifact interface entry drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_interfaces_entries_non_empty"
    assert {finding.field_name for finding in failing_results[0].findings} == {"interfaces.source_of_truth"}


def test_kb_rules_report_component_doc_performance_metrics_component_type_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": [],
            "interfaces": {"python_api": ["run() -> None"]},
            "performance_metrics": {"generation_frequency": "on demand", "storage_pattern": "derived markdown"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "targeted_tests_added"},
            "auto_generated": True,
            "file_paths": ["src/component_alpha.py"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Performance-metrics type drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_performance_metrics_match_component_type"
    assert {finding.field_name for finding in failing_results[0].findings} == {"performance_metrics"}


def test_kb_rules_report_governance_artifact_performance_metrics_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_index.json",
        {
            "components": [
                {
                    "component_id": "component_alpha",
                    "component_name": "Component Alpha",
                    "component_type": "governance_artifact",
                    "file_path": "SYSTEM_ALPHA.md",
                    "dependencies": ["ai_docs/component_alpha_snapshot.json"],
                    "dependents": [],
                    "creation_timestamp": "2026-03-31T00:00:00Z",
                    "last_modified_timestamp": "2026-03-31T00:00:00Z",
                    "documentation_path": "ai_docs/component_alpha.json",
                    "health_status": "healthy",
                    "test_coverage_percentage": 100,
                    "compliance_status": "I1_I2_I3_I4_compliant",
                    "related_techniques": ["technique_alpha"],
                }
            ],
            "metadata": {"total_components": 1, "last_updated": "2026-03-31T00:00:00Z"},
            "health_status": {"total_healthy": 1, "total_degraded": 0, "total_failing": 0},
        },
    )
    (workspace_root / "SYSTEM_ALPHA.md").write_text("# Alpha\n", encoding="utf-8")
    write_json(workspace_root / "ai_docs" / "component_alpha_snapshot.json", {"status": "ok"})
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "governance_artifact",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": ["ai_docs/component_alpha_snapshot.json"],
            "interfaces": {
                "artifact": ["SYSTEM_ALPHA.md"],
                "source_of_truth": ["ai_docs/component_alpha_snapshot.json"],
            },
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "generated_output_verified"},
            "auto_generated": True,
            "file_paths": ["SYSTEM_ALPHA.md", "ai_docs/component_alpha_snapshot.json"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Governance-artifact performance-metrics drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_performance_metrics_match_component_type"
    assert {finding.field_name for finding in failing_results[0].findings} == {"performance_metrics"}


def test_kb_rules_report_component_doc_performance_metrics_value_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": [],
            "interfaces": {"python_api": ["run() -> None"]},
            "performance_metrics": {"expected_latency": "", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "targeted_tests_added"},
            "auto_generated": True,
            "file_paths": ["src/component_alpha.py"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Performance-metrics value drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_performance_metrics_values_non_empty"
    assert {finding.field_name for finding in failing_results[0].findings} == {"performance_metrics"}


def test_kb_rules_report_governance_artifact_performance_metrics_value_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_index.json",
        {
            "components": [
                {
                    "component_id": "component_alpha",
                    "component_name": "Component Alpha",
                    "component_type": "governance_artifact",
                    "file_path": "SYSTEM_ALPHA.md",
                    "dependencies": ["ai_docs/component_alpha_snapshot.json"],
                    "dependents": [],
                    "creation_timestamp": "2026-03-31T00:00:00Z",
                    "last_modified_timestamp": "2026-03-31T00:00:00Z",
                    "documentation_path": "ai_docs/component_alpha.json",
                    "health_status": "healthy",
                    "test_coverage_percentage": 100,
                    "compliance_status": "I1_I2_I3_I4_compliant",
                    "related_techniques": ["technique_alpha"],
                }
            ],
            "metadata": {"total_components": 1, "last_updated": "2026-03-31T00:00:00Z"},
            "health_status": {"total_healthy": 1, "total_degraded": 0, "total_failing": 0},
        },
    )
    (workspace_root / "SYSTEM_ALPHA.md").write_text("# Alpha\n", encoding="utf-8")
    write_json(workspace_root / "ai_docs" / "component_alpha_snapshot.json", {"status": "ok"})
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "governance_artifact",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": ["ai_docs/component_alpha_snapshot.json"],
            "interfaces": {
                "artifact": ["SYSTEM_ALPHA.md"],
                "source_of_truth": ["ai_docs/component_alpha_snapshot.json"],
            },
            "performance_metrics": {"generation_frequency": "on demand", "storage_pattern": ""},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "generated_output_verified"},
            "auto_generated": True,
            "file_paths": ["SYSTEM_ALPHA.md", "ai_docs/component_alpha_snapshot.json"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Governance-artifact performance-metrics value drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_performance_metrics_values_non_empty"
    assert {finding.field_name for finding in failing_results[0].findings} == {"performance_metrics"}


def test_kb_rules_report_component_doc_file_paths_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": [],
            "interfaces": {"python_api": ["run() -> None"]},
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "targeted_tests_added"},
            "auto_generated": True,
            "file_paths": ["src/component_alpha.py", "src/missing_component_alpha.py"],
            "related_techniques": ["technique_alpha"],
            "notes": ["File-path drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_file_paths_exist"
    assert {finding.field_name for finding in failing_results[0].findings} == {"file_paths"}


def test_kb_rules_report_component_doc_dependencies_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_index.json",
        {
            "components": [
                {
                    "component_id": "component_alpha",
                    "component_name": "Component Alpha",
                    "component_type": "python_module",
                    "file_path": "src/component_alpha.py",
                    "dependencies": ["src/missing_component_alpha_dependency.py"],
                    "dependents": [],
                    "creation_timestamp": "2026-03-31T00:00:00Z",
                    "last_modified_timestamp": "2026-03-31T00:00:00Z",
                    "documentation_path": "ai_docs/component_alpha.json",
                    "health_status": "healthy",
                    "test_coverage_percentage": 100,
                    "compliance_status": "I1_I2_I3_I4_compliant",
                    "related_techniques": ["technique_alpha"],
                }
            ],
            "metadata": {"total_components": 1, "last_updated": "2026-03-31T00:00:00Z"},
            "health_status": {"total_healthy": 1, "total_degraded": 0, "total_failing": 0},
        },
    )
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": ["src/missing_component_alpha_dependency.py"],
            "interfaces": {"python_api": ["run() -> None"]},
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "targeted_tests_added"},
            "auto_generated": True,
            "file_paths": ["src/component_alpha.py"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Dependency drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_dependencies_exist"
    assert {finding.field_name for finding in failing_results[0].findings} == {"dependencies"}


def test_kb_rules_report_component_doc_cli_command_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": [],
            "interfaces": {
                "python_api": ["run() -> None"],
                "cli": ["python -m inf_work imaginary-command <workspace_root> --pretty"],
            },
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "targeted_tests_added"},
            "auto_generated": True,
            "file_paths": ["src/component_alpha.py"],
            "related_techniques": ["technique_alpha"],
            "notes": ["CLI drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_cli_commands_valid"
    assert {finding.field_name for finding in failing_results[0].findings} == {"interfaces.cli"}


def test_kb_rules_accept_refresh_artifacts_cli_command(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": [],
            "interfaces": {
                "python_api": ["run() -> None"],
                "cli": ["python -m inf_work refresh-artifacts <workspace_root> --pretty"],
            },
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "targeted_tests_added"},
            "auto_generated": True,
            "file_paths": ["src/component_alpha.py"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Refresh artifacts CLI remains part of the supported surface."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert failing_results == []


def test_kb_rules_report_component_doc_python_api_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": [],
            "interfaces": {
                "python_api": ["missing_run() -> None"],
                "cli": [],
            },
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "targeted_tests_added"},
            "auto_generated": True,
            "file_paths": ["src/component_alpha.py"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Python API drift fixture keeps notes valid."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_python_api_symbols_valid"
    assert {finding.field_name for finding in failing_results[0].findings} == {"interfaces.python_api"}


def test_kb_rules_report_component_doc_notes_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_alpha.json",
        {
            "component_id": "component_alpha",
            "component_name": "Component Alpha",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": [],
            "interfaces": {
                "python_api": ["run() -> None"],
                "cli": [],
            },
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "targeted_tests_added"},
            "auto_generated": True,
            "file_paths": ["src/component_alpha.py"],
            "related_techniques": ["technique_alpha"],
            "notes": [""],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_doc_notes_non_empty"
    assert {finding.field_name for finding in failing_results[0].findings} == {"notes"}


def test_kb_rules_report_component_index_dependents_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_index.json",
        {
            "components": [
                {
                    "component_id": "component_alpha",
                    "component_name": "Component Alpha",
                    "component_type": "python_module",
                    "file_path": "src/component_alpha.py",
                    "dependencies": [],
                    "dependents": ["component_beta"],
                    "creation_timestamp": "2026-03-31T00:00:00Z",
                    "last_modified_timestamp": "2026-03-31T00:00:00Z",
                    "documentation_path": "ai_docs/component_alpha.json",
                    "health_status": "healthy",
                    "test_coverage_percentage": 100,
                    "compliance_status": "I1_I2_I3_I4_compliant",
                    "related_techniques": ["technique_alpha"],
                }
            ],
            "metadata": {"total_components": 1, "last_updated": "2026-03-31T00:00:00Z"},
            "health_status": {"total_healthy": 1, "total_degraded": 0, "total_failing": 0},
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_dependents_parity"
    assert {finding.field_name for finding in failing_results[0].findings} == {"dependents"}


def test_kb_rules_report_component_index_dependents_entry_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["dependents"] = [""]
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_dependents_entries_non_empty"
    assert {finding.field_name for finding in failing_results[0].findings} == {"dependents"}


def test_kb_rules_report_component_index_file_path_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["file_path"] = ""
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_file_path_non_empty"
    assert {finding.field_name for finding in failing_results[0].findings} == {"file_path"}


def test_kb_rules_report_component_index_file_path_uniqueness_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    duplicate_component = dict(payload["components"][0])
    duplicate_component["component_id"] = "component_beta"
    duplicate_component["component_name"] = "Component Beta"
    duplicate_component["documentation_path"] = "ai_docs/component_beta.json"
    payload["components"].append(duplicate_component)
    payload["metadata"]["total_components"] = 2
    payload["health_status"]["total_healthy"] = 2
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)
    write_json(
        workspace_root / "ai_docs" / "component_beta.json",
        {
            "component_id": "component_beta",
            "component_name": "Component Beta",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": [],
            "interfaces": {"python_api": ["run() -> None"]},
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "targeted_tests_added"},
            "auto_generated": True,
            "file_paths": ["src/component_alpha.py"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Component Beta mirrors the shared file path for uniqueness drift coverage."],
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_file_path_unique"
    assert {finding.field_name for finding in failing_results[0].findings} == {"file_path"}


def test_kb_rules_report_component_index_performance_metrics_field_set_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["performance_metrics"] = {
        "response_latency_target": "<5s",
        "memory_profile": "bounded",
        "unexpected_field": "drift",
    }
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_performance_metrics_field_set_exact"
    assert {finding.field_name for finding in failing_results[0].findings} == {"performance_metrics"}


def test_kb_rules_report_component_index_performance_metrics_value_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["performance_metrics"] = {
        "response_latency_target": "",
        "memory_profile": "bounded",
    }
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_performance_metrics_values_non_empty"
    assert {finding.field_name for finding in failing_results[0].findings} == {"performance_metrics"}


def test_kb_rules_report_component_index_known_issues_entry_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["known_issues"] = [""]
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_known_issues_entries_non_empty"
    assert {finding.field_name for finding in failing_results[0].findings} == {"known_issues"}


def test_kb_rules_report_component_index_documentation_path_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["documentation_path"] = ""
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_documentation_path_non_empty"
    assert {finding.field_name for finding in failing_results[0].findings} == {"documentation_path"}


def test_kb_rules_report_component_index_component_name_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["component_name"] = ""
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_component_name_non_empty"
    assert {finding.field_name for finding in failing_results[0].findings} == {"component_name"}


def test_kb_rules_report_component_index_component_name_uniqueness_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    duplicate_component = dict(payload["components"][0])
    duplicate_component["component_id"] = "component_beta"
    duplicate_component["file_path"] = "src/component_beta.py"
    duplicate_component["documentation_path"] = "ai_docs/component_beta.json"
    payload["components"].append(duplicate_component)
    payload["metadata"]["total_components"] = 2
    payload["health_status"]["total_healthy"] = 2
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)
    write_json(
        workspace_root / "ai_docs" / "component_beta.json",
        {
            "component_id": "component_beta",
            "component_name": "Component Alpha",
            "component_type": "python_module",
            "creation_timestamp": "2026-03-31T00:00:00Z",
            "compliance_status": "I1_I2_I3_I4_compliant",
            "dependencies": [],
            "interfaces": {"python_api": ["run() -> None"]},
            "performance_metrics": {"expected_latency": "sub-second", "memory_usage_pattern": "bounded"},
            "test_coverage": {"targeted_test_file": "tests/test_component_alpha.py", "status": "targeted_tests_added"},
            "auto_generated": True,
            "file_paths": ["src/component_beta.py"],
            "related_techniques": ["technique_alpha"],
            "notes": ["Component Beta mirrors the shared component name for uniqueness drift coverage."],
        },
    )
    (workspace_root / "src" / "component_beta.py").write_text("def run() -> None:\n    return None\n", encoding="utf-8")
    coverage_snapshot = json.loads((workspace_root / "ai_docs" / "test_coverage_snapshot.json").read_text(encoding="utf-8"))
    coverage_snapshot["module_coverage"].append(
        {
            "module_path": "src/component_beta.py",
            "coverage_percentage": 100,
            "num_statements": 10,
            "covered_lines": 10,
            "missing_lines": 0,
        }
    )
    write_json(workspace_root / "ai_docs" / "test_coverage_snapshot.json", coverage_snapshot)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_component_name_unique"
    assert {finding.field_name for finding in failing_results[0].findings} == {"component_name"}


def test_kb_rules_report_component_index_component_id_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["component_id"] = ""
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_component_id_non_empty"
    assert {finding.field_name for finding in failing_results[0].findings} == {"component_id"}


def test_kb_rules_report_component_index_component_id_uniqueness_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    duplicate_component = dict(payload["components"][0])
    duplicate_component["component_name"] = "Component Beta"
    duplicate_component["file_path"] = "src/component_beta.py"
    payload["components"].append(duplicate_component)
    payload["metadata"]["total_components"] = 2
    payload["health_status"]["total_healthy"] = 2
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)
    (workspace_root / "src" / "component_beta.py").write_text("def run() -> None:\n    return None\n", encoding="utf-8")
    coverage_snapshot = json.loads((workspace_root / "ai_docs" / "test_coverage_snapshot.json").read_text(encoding="utf-8"))
    coverage_snapshot["module_coverage"].append(
        {
            "module_path": "src/component_beta.py",
            "coverage_percentage": 100,
            "num_statements": 10,
            "covered_lines": 10,
            "missing_lines": 0,
        }
    )
    write_json(workspace_root / "ai_docs" / "test_coverage_snapshot.json", coverage_snapshot)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_component_id_unique"
    assert {finding.field_name for finding in failing_results[0].findings} == {"component_id"}


def test_kb_rules_report_component_index_component_type_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["component_type"] = "unknown_type"
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_component_type_valid"
    assert {finding.field_name for finding in failing_results[0].findings} == {"component_type"}


def test_kb_rules_report_component_index_dependencies_entry_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["dependencies"] = [""]
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_dependencies_entries_non_empty"
    assert {finding.field_name for finding in failing_results[0].findings} == {"dependencies"}


def test_kb_rules_report_component_index_dependencies_entry_uniqueness_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["dependencies"] = ["src/dup.py", "src/dup.py"]
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_dependencies_entries_unique"
    assert {finding.field_name for finding in failing_results[0].findings} == {"dependencies"}


def test_kb_rules_report_component_index_related_techniques_entry_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["related_techniques"] = [""]
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_related_techniques_entries_non_empty"
    assert {finding.field_name for finding in failing_results[0].findings} == {"related_techniques"}


def test_kb_rules_report_kb_index_metadata_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "knowledge_base" / "kb_index.json",
        {
            "last_updated": "2026-03-31T00:00:00Z",
            "total_techniques": 0,
            "total_bug_fixes": 1,
            "total_innovations": 1,
            "total_automation_patterns": 0,
            "constraint_compliance_stats": {
                "I1_compliant": 0,
                "I2_compliant": 0,
                "I3_compliant": 0,
                "I4_compliant": 0,
                "all_compliant": 0,
            },
            "automation_success_metrics": {
                "total_automated_actions": 0,
                "successful_automations": 0,
                "failed_automations": 0,
                "success_rate": 0.0,
            },
            "lookup_indices": {
                "by_category": {},
                "by_constraint": {},
                "by_error_code": {},
                "by_automation_type": {},
            },
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.kb_index_metadata_parity"
    failing_fields = {finding.field_name for finding in failing_results[0].findings}
    assert {
        "total_techniques",
        "total_automation_patterns",
        "constraint_compliance_stats",
        "automation_success_metrics",
        "lookup_indices.by_category",
    }.issubset(failing_fields)


def test_kb_rules_report_kb_index_last_updated_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "knowledge_base" / "kb_index.json",
        {
            "last_updated": "2026-03-30T00:00:00Z",
            "total_techniques": 1,
            "total_bug_fixes": 1,
            "total_innovations": 1,
            "total_automation_patterns": 1,
            "constraint_compliance_stats": {
                "I1_compliant": 1,
                "I2_compliant": 1,
                "I3_compliant": 1,
                "I4_compliant": 1,
                "all_compliant": 1,
            },
            "automation_success_metrics": {
                "total_automated_actions": 1,
                "successful_automations": 1,
                "failed_automations": 0,
                "success_rate": 1.0,
            },
            "lookup_indices": {
                "by_category": {
                    "architectural": ["technique_alpha"],
                    "innovation": ["innovation_alpha"],
                },
                "by_constraint": {
                    "I1": ["innovation_alpha", "technique_alpha"],
                    "I2": ["technique_alpha"],
                    "I3": ["technique_alpha"],
                    "I4": ["technique_alpha"],
                },
                "by_error_code": {"1100": ["bug_fix_alpha"]},
                "by_automation_type": {"validation": ["automation_alpha"]},
            },
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.kb_index_metadata_parity"
    assert {finding.field_name for finding in failing_results[0].findings} == {"last_updated"}


def test_kb_rules_report_source_metadata_count_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "knowledge_base" / "techniques.json",
        {
            "techniques": [
                {
                    "id": "technique_alpha",
                    "name": "Technique Alpha",
                    "category": "architectural",
                    "constraints_compliance": ["I1", "I2", "I3", "I4"],
                }
            ],
            "metadata": {"total_count": 3},
        },
    )
    write_json(
        workspace_root / "knowledge_base" / "session_history.json",
        {
            "sessions": [
                {
                    "session_id": "session_alpha",
                    "summary": "Session Alpha",
                }
            ],
            "metadata": {"total_sessions": 7},
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    failing_rule_ids = {result.rule_id for result in failing_results}
    assert "knowledge_base.techniques_metadata_count_parity" in failing_rule_ids
    assert "knowledge_base.session_history_metadata_count_parity" in failing_rule_ids


def test_kb_rules_report_source_metadata_timestamp_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "knowledge_base" / "automation_patterns.json",
        {
            "automation_patterns": [
                {
                    "id": "automation_alpha",
                    "automation_type": "validation",
                    "pattern_name": "Automation Alpha",
                    "created_timestamp": "2026-03-31T00:00:00Z",
                    "success_rate": 1.0,
                    "false_positive_rate": 0.0,
                    "related_techniques": ["technique_alpha"],
                }
            ],
            "metadata": {"total_count": 1, "last_updated": "2026-03-30T00:00:00Z"},
        },
    )
    write_json(
        workspace_root / "knowledge_base" / "session_history.json",
        {
            "sessions": [
                {
                    "session_id": "session_alpha",
                    "created_timestamp": "2026-03-31T00:00:00Z",
                    "summary": "Session Alpha",
                }
            ],
            "metadata": {
                "total_sessions": 1,
                "first_session": "2026-03-30T00:00:00Z",
                "last_session": "2026-03-30T00:00:00Z",
            },
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    failing_rule_ids = {result.rule_id for result in failing_results}
    assert "knowledge_base.automation_patterns_metadata_last_updated_parity" in failing_rule_ids
    assert "knowledge_base.session_history_temporal_metadata_parity" in failing_rule_ids


def test_kb_rules_report_component_index_summary_metadata_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_index.json",
        {
            "components": [
                {
                    "component_id": "component_alpha",
                    "component_name": "Component Alpha",
                    "component_type": "python_module",
                    "file_path": "src/component_alpha.py",
                    "dependencies": [],
                    "dependents": [],
                    "creation_timestamp": "2026-03-31T00:00:00Z",
                    "last_modified_timestamp": "2026-03-31T00:00:00Z",
                    "documentation_path": "ai_docs/component_alpha.json",
                    "health_status": "healthy",
                    "test_coverage_percentage": 100,
                    "compliance_status": "I1_I2_I3_I4_compliant",
                    "related_techniques": ["technique_alpha"],
                }
            ],
            "metadata": {"total_components": 4, "last_updated": "2026-03-31T00:00:00Z"},
            "health_status": {"total_healthy": 0, "total_degraded": 1, "total_failing": 1},
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_summary_metadata_parity"
    failing_fields = {finding.field_name for finding in failing_results[0].findings}
    assert {
        "metadata.total_components",
        "health_status.total_healthy",
        "health_status.total_degraded",
        "health_status.total_failing",
    }.issubset(failing_fields)


def test_kb_rules_report_component_index_timestamp_metadata_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_index.json",
        {
            "components": [
                {
                    "component_id": "component_alpha",
                    "component_name": "Component Alpha",
                    "component_type": "python_module",
                    "file_path": "src/component_alpha.py",
                    "dependencies": [],
                    "dependents": [],
                    "creation_timestamp": "2026-03-31T00:00:00Z",
                    "last_modified_timestamp": "2026-03-30T00:00:00Z",
                    "documentation_path": "ai_docs/component_alpha.json",
                    "health_status": "healthy",
                    "test_coverage_percentage": 100,
                    "compliance_status": "I1_I2_I3_I4_compliant",
                    "related_techniques": ["technique_alpha"],
                }
            ],
            "metadata": {"total_components": 1, "last_updated": "2026-03-29T00:00:00Z"},
            "health_status": {"total_healthy": 1, "total_degraded": 0, "total_failing": 0},
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_timestamp_metadata_parity"
    failing_fields = {finding.field_name for finding in failing_results[0].findings}
    assert {"last_modified_timestamp", "metadata.last_updated"} == failing_fields


def test_kb_rules_report_component_index_timestamp_shape_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["creation_timestamp"] = "2026-03-31"
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_timestamp_fields_valid"
    assert {finding.field_name for finding in failing_results[0].findings} == {"creation_timestamp"}


def test_kb_rules_report_component_index_test_coverage_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "ai_docs" / "component_index.json",
        {
            "components": [
                {
                    "component_id": "component_alpha",
                    "component_name": "Component Alpha",
                    "component_type": "python_module",
                    "file_path": "src/component_alpha.py",
                    "dependencies": [],
                    "dependents": [],
                    "creation_timestamp": "2026-03-31T00:00:00Z",
                    "last_modified_timestamp": "2026-03-31T00:00:00Z",
                    "documentation_path": "ai_docs/component_alpha.json",
                    "health_status": "healthy",
                    "test_coverage_percentage": 91,
                    "compliance_status": "I1_I2_I3_I4_compliant",
                    "related_techniques": ["technique_alpha"],
                }
            ],
            "metadata": {"total_components": 1, "last_updated": "2026-03-31T00:00:00Z"},
            "health_status": {"total_healthy": 1, "total_degraded": 0, "total_failing": 0},
        },
    )

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_test_coverage_parity"
    assert {finding.field_name for finding in failing_results[0].findings} == {"test_coverage_percentage"}


def test_kb_rules_report_component_index_health_status_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["health_status"] = "unknown"
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_health_status_valid"
    assert {finding.field_name for finding in failing_results[0].findings} == {"health_status"}


def test_kb_rules_report_component_index_compliance_status_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["compliance_status"] = "violations_detected"
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_compliance_status_valid"
    assert {finding.field_name for finding in failing_results[0].findings} == {"compliance_status"}


def test_kb_rules_report_component_index_complexity_score_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["complexity_score"] = -1
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_complexity_score_non_negative_int"
    assert {finding.field_name for finding in failing_results[0].findings} == {"complexity_score"}


def test_kb_rules_report_component_index_test_coverage_percentage_shape_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["test_coverage_percentage"] = 101
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = [result for result in rule_results if not result.passed]

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.component_index_test_coverage_percentage_valid"
    assert {finding.field_name for finding in failing_results[0].findings} == {"test_coverage_percentage"}


def test_rule_helpers_filter_and_summarize_results(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path, broken_reference=True)

    rule_results = run_knowledge_base_rules(workspace_root)
    failing_results = filter_rule_results(rule_results, only_failures=True, categories={"cross_reference"})
    summary = summarize_rule_results(failing_results)

    assert len(failing_results) == 1
    assert failing_results[0].rule_id == "knowledge_base.bug_fix_solution_technique_exists"
    assert summary["total_rules"] == 1
    assert summary["failed_rules"] == 1
    assert summary["by_category"]["cross_reference"]["failed_rules"] == 1
    assert summary["by_severity"]["error"]["findings"] == 1


def test_severity_threshold_can_ignore_error_failures(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path, broken_reference=True)

    rule_results = run_knowledge_base_rules(
        workspace_root,
        {"knowledge_base.bug_fix_solution_technique_exists"},
    )

    assert should_fail_rule_results(rule_results, "error") is True
    assert should_fail_rule_results(rule_results, "critical") is False
    assert should_fail_rule_results(rule_results, "none") is False


def test_all_cli_can_filter_to_failing_kb_cross_reference_rules(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path, broken_reference=True)
    environment = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "inf_work",
            "all",
            str(workspace_root),
            "--pretty",
            "--only-failures",
            "--domain-filter",
            "knowledge_base",
            "--category",
            "cross_reference",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["aggregate_rule_summary"]["failed_rules"] == 1
    assert payload["workspace"]["rule_summary"]["total_rules"] == 0
    assert payload["knowledge_base"]["rule_summary"]["failed_rules"] == 1
    assert payload["knowledge_base"]["rule_results"][0]["rule_id"] == "knowledge_base.bug_fix_solution_technique_exists"


def test_all_cli_can_execute_selected_rule_id_only(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path, broken_reference=True)
    environment = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "inf_work",
            "all",
            str(workspace_root),
            "--pretty",
            "--rule-id",
            "knowledge_base.bug_fix_solution_technique_exists",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["aggregate_rule_summary"]["total_rules"] == 1
    assert payload["knowledge_base"]["rule_results"][0]["rule_id"] == "knowledge_base.bug_fix_solution_technique_exists"
    assert payload["workspace"]["rule_summary"]["total_rules"] == 0


def test_all_cli_can_adjust_exit_policy_by_severity(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path, broken_reference=True)
    environment = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "inf_work",
            "all",
            str(workspace_root),
            "--pretty",
            "--rule-id",
            "knowledge_base.bug_fix_solution_technique_exists",
            "--fail-on",
            "critical",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["knowledge_base"]["rule_results"][0]["passed"] is False
    assert payload["report_filters"]["fail_on"] == "critical"


def test_all_cli_can_execute_kb_only_profile(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path, broken_reference=True)
    environment = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "inf_work",
            "all",
            str(workspace_root),
            "--pretty",
            "--profile",
            "kb-only",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["report_filters"]["profiles"] == ["kb-only"]
    assert payload["workspace"]["rule_summary"]["total_rules"] == 0
    assert payload["knowledge_base"]["rule_summary"]["total_rules"] == 58


def test_all_cli_can_execute_kb_metadata_profile(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    environment = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "inf_work",
            "all",
            str(workspace_root),
            "--pretty",
            "--profile",
            "kb-metadata",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["report_filters"]["profiles"] == ["kb-metadata"]
    assert payload["workspace"]["rule_summary"]["total_rules"] == 0
    assert payload["status"]["rule_summary"]["total_rules"] == 0
    assert payload["knowledge_base"]["rule_summary"]["total_rules"] == 13
    assert payload["knowledge_base"]["rule_summary"]["by_category"]["metadata"]["rules"] == 13


def test_all_cli_can_execute_workspace_only_profile(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    environment = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "inf_work",
            "all",
            str(workspace_root),
            "--pretty",
            "--profile",
            "workspace-only",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["report_filters"]["profiles"] == ["workspace-only"]
    assert payload["aggregate_rule_summary"]["total_rules"] == 1
    assert payload["workspace"]["rule_summary"]["total_rules"] == 1
    assert payload["knowledge_base"]["rule_summary"]["total_rules"] == 0
    workspace_root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, "-m", "inf_work", "status", str(workspace_root), "--pretty"],
        check=True,
        capture_output=True,
        text=True,
        cwd=workspace_root,
        env={**os.environ, "PYTHONPATH": str(workspace_root / "src")},
    )
    environment = {
        **os.environ,
        "PYTHONPATH": str(workspace_root / "src"),
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "inf_work",
            "all",
            str(workspace_root),
            "--pretty",
            "--profile",
            "status-only",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=workspace_root,
        env=environment,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["report_filters"]["profiles"] == ["status-only"]
    assert payload["workspace"]["rule_summary"]["total_rules"] == 0
    assert payload["knowledge_base"]["rule_summary"]["total_rules"] == 0
    assert payload["status"]["rule_summary"]["total_rules"] == 6


def test_all_cli_can_execute_resolver_only_profile() -> None:
    workspace_root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, "-m", "inf_work", "status", str(workspace_root), "--pretty"],
        check=True,
        capture_output=True,
        text=True,
        cwd=workspace_root,
        env={**os.environ, "PYTHONPATH": str(workspace_root / "src")},
    )
    environment = {
        **os.environ,
        "PYTHONPATH": str(workspace_root / "src"),
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "inf_work",
            "all",
            str(workspace_root),
            "--pretty",
            "--profile",
            "resolver-only",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=workspace_root,
        env=environment,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["report_filters"]["profiles"] == ["resolver-only"]
    assert payload["workspace"]["rule_summary"]["total_rules"] == 0
    assert payload["knowledge_base"]["rule_summary"]["total_rules"] == 0
    assert payload["status"]["rule_summary"]["total_rules"] == 2
    assert payload["aggregate_rule_summary"]["by_category"]["runtime_integrity"]["rules"] == 2


def test_all_cli_can_execute_component_governance_profile(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    environment = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "inf_work",
            "all",
            str(workspace_root),
            "--pretty",
            "--profile",
            "component-governance",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["report_filters"]["profiles"] == ["component-governance"]
    assert payload["workspace"]["rule_summary"]["total_rules"] == 0
    assert payload["status"]["rule_summary"]["total_rules"] == 0
    assert payload["knowledge_base"]["rule_summary"]["total_rules"] == 43
    assert payload["knowledge_base"]["rule_summary"]["by_category"]["cross_reference"]["rules"] == 8
    assert payload["knowledge_base"]["rule_summary"]["by_category"]["metadata"]["rules"] == 3
    assert payload["knowledge_base"]["rule_summary"]["by_category"]["schema"]["rules"] == 32


def test_all_cli_can_fix_stale_status_artifacts() -> None:
    workspace_root = Path(__file__).resolve().parents[1]
    snapshot_path = workspace_root / "ai_docs" / "system_status_snapshot.json"
    original_payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    stale_payload = json.loads(json.dumps(original_payload))
    stale_payload["knowledge_base_metrics"]["innovation_count"] = 999
    snapshot_path.write_text(json.dumps(stale_payload, indent=2), encoding="utf-8")

    environment = {
        **os.environ,
        "PYTHONPATH": str(workspace_root / "src"),
    }

    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "inf_work",
                "all",
                str(workspace_root),
                "--pretty",
                "--profile",
                "status-only",
                "--fix-status",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=workspace_root,
            env=environment,
        )

        assert completed.returncode == 0
        payload = json.loads(completed.stdout)
        assert payload["compliant"] is True
        assert payload["report_filters"]["fix_status"] is True
        assert payload["status"]["compliant"] is True
        assert payload["status"]["rule_summary"]["total_rules"] == 6

        repaired_payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert repaired_payload["knowledge_base_metrics"]["innovation_count"] != 999
    finally:
        subprocess.run(
            [sys.executable, "-m", "inf_work", "status", str(workspace_root), "--pretty"],
            check=True,
            capture_output=True,
            text=True,
            cwd=workspace_root,
            env=environment,
        )
