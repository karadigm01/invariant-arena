from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import inf_work.kb_integrity as kb_integrity_module
from inf_work.rules import RuleFinding, RuleResult
from inf_work.kb_integrity import validate_knowledge_base
from inf_work.system_status import write_system_status_outputs


BASE_TIMESTAMP = "2026-03-31T00:00:00Z"
COMPONENT_ALPHA_DOC_PATH = "ai_docs/component_alpha.json"


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def component_alpha_doc(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
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
    }
    payload.update(overrides)
    return payload


def write_component_alpha_doc(workspace_root: Path, **overrides: object) -> None:
    write_json(workspace_root / COMPONENT_ALPHA_DOC_PATH, component_alpha_doc(**overrides))


def create_workspace(tmp_path: Path, *, broken_reference: bool = False) -> Path:
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    write_json(
        tmp_path / "core_reference.json",
        {
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
                    "documentation_path": COMPONENT_ALPHA_DOC_PATH,
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
    write_component_alpha_doc(tmp_path)
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


def test_validate_knowledge_base_reports_compliance(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is True
    assert result.issues == []


def test_validate_knowledge_base_reports_missing_technique_reference(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path, broken_reference=True)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert len(result.issues) == 1
    assert result.issues[0].field_name == "solution_technique"
    assert result.issues[0].source_file == "knowledge_base/bug_fixes.json"


def test_validate_knowledge_base_reports_component_doc_metadata_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_component_alpha_doc(
        workspace_root,
        component_name="Drifted Alpha",
        creation_timestamp="2026-03-30T00:00:00Z",
        compliance_status="violations_detected",
        dependencies=["src/other_alpha_dependency.py"],
        file_paths=["src/other_alpha.py"],
        related_techniques=["technique_beta"],
        notes=["Metadata drift fixture keeps notes valid."],
    )

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "component_name" for issue in result.issues)
    assert any(issue.field_name == "creation_timestamp" for issue in result.issues)
    assert any(issue.field_name == "compliance_status" for issue in result.issues)
    assert any(issue.field_name == "dependencies" for issue in result.issues)
    assert any(issue.field_name == "file_paths" for issue in result.issues)
    assert any(issue.field_name == "related_techniques" for issue in result.issues)


def test_validate_knowledge_base_reports_component_doc_required_field_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = component_alpha_doc(notes=["Required-field drift fixture keeps notes valid."])
    payload.pop("test_coverage")
    write_json(workspace_root / COMPONENT_ALPHA_DOC_PATH, payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "test_coverage" for issue in result.issues)


def test_validate_knowledge_base_reports_component_doc_field_set_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = read_json(workspace_root / COMPONENT_ALPHA_DOC_PATH)
    payload["unexpected_field"] = "drift"
    write_json(workspace_root / COMPONENT_ALPHA_DOC_PATH, payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "__root__" for issue in result.issues)


def test_reference_issue_and_validation_result_to_dict() -> None:
    issue = kb_integrity_module.ReferenceIssue(
        source_file="knowledge_base/kb_index.json",
        item_identifier="kb_index",
        field_name="last_updated",
        message="drift",
    )
    result = kb_integrity_module.KnowledgeBaseValidationResult(
        workspace_root="/workspace",
        compliant=False,
        issues=[issue],
        rule_results=[
            RuleResult(
                rule_id="knowledge_base.rule",
                domain="knowledge_base",
                category="metadata",
                severity="error",
                description="description",
                passed=False,
                findings=[
                    RuleFinding(
                        message="failed",
                        source_file="knowledge_base/kb_index.json",
                        item_identifier="kb_index",
                        field_name="last_updated",
                    )
                ],
            )
        ],
    )

    assert issue.to_dict()["field_name"] == "last_updated"
    payload = result.to_dict()
    assert payload["issues"][0]["message"] == "drift"
    assert payload["rule_results"][0]["rule_id"] == "knowledge_base.rule"


def test_build_expected_kb_index_metadata_skips_missing_optional_index_keys() -> None:
    payload = kb_integrity_module._build_expected_kb_index_metadata(
        {
            "techniques": [
                {
                    "id": "technique_alpha",
                    "category": "architectural",
                    "constraints_compliance": ["I1"],
                },
                {
                    "id": "technique_beta",
                    "constraints_compliance": [],
                },
            ],
            "bug_fixes": [
                {"id": "bug_fix_alpha", "error_code": 1100},
                {"id": "bug_fix_beta", "error_code": None},
            ],
            "innovations": [{"id": "innovation_alpha", "constraint_challenged": ["I2"]}],
            "automation_patterns": [
                {"id": "automation_alpha", "automation_type": "validation", "success_rate": 1.0},
                {"id": "automation_beta", "success_rate": 0.0},
            ],
            "sessions": [{"created_timestamp": "2026-04-03T00:00:00Z"}],
            "techniques_payload": {"metadata": {"last_updated": "2026-04-03T00:00:00Z"}},
            "bug_fixes_payload": {"metadata": {"last_updated": "2026-04-03T00:00:00Z"}},
            "innovations_payload": {"metadata": {"last_updated": "2026-04-03T00:00:00Z"}},
            "automation_payload": {"metadata": {"last_updated": "2026-04-03T00:00:00Z"}},
            "session_history_payload": {"metadata": {"last_session": "2026-04-03T00:00:00Z"}},
        }
    )

    assert payload["lookup_indices"]["by_category"] == {
        "architectural": ["technique_alpha"],
        "innovation": ["innovation_alpha"],
    }
    assert payload["lookup_indices"]["by_error_code"] == {"1100": ["bug_fix_alpha"]}
    assert payload["lookup_indices"]["by_automation_type"] == {"validation": ["automation_alpha"]}


def test_internal_cross_reference_helpers_cover_unknown_and_valid_values(tmp_path: Path) -> None:
    assert kb_integrity_module._is_valid_iso8601_utc_timestamp("") is False
    assert kb_integrity_module._is_valid_iso8601_utc_timestamp("2026-04-03T00:00:00Z") is True

    context = {
        "innovations": [{"id": "innovation_alpha", "creative_solution": "missing", "constraint_challenged": ["I9"]}],
        "automation_patterns": [{"id": "automation_alpha", "related_techniques": ["missing"]}],
        "components": [{"component_id": "component_alpha", "related_techniques": ["missing"], "dependencies": [], "file_path": "src/component_alpha.py"}],
        "technique_ids": {"technique_alpha"},
        "technique_names": {"Technique Alpha"},
    }

    assert kb_integrity_module._evaluate_innovation_creative_solution_exists(context)[0].field_name == "creative_solution"
    assert kb_integrity_module._evaluate_innovation_constraints_valid(context)[0].field_name == "constraint_challenged"
    assert kb_integrity_module._evaluate_automation_related_techniques_exist(context)[0].field_name == "related_techniques"
    assert kb_integrity_module._evaluate_component_related_techniques_exist(context)[0].field_name == "related_techniques"


def test_component_doc_metadata_parity_reports_missing_documentation() -> None:
    findings = kb_integrity_module._evaluate_component_doc_metadata_parity(
        {
            "components": [
                {
                    "component_id": "component_alpha",
                    "documentation_path": "ai_docs/component_alpha.json",
                    "compliance_status": "I1_I2_I3_I4_compliant",
                }
            ],
            "component_docs": {},
        }
    )

    assert findings[0].field_name == "documentation_path"


def test_component_doc_metadata_parity_skips_blank_component_identifier_field() -> None:
    findings = kb_integrity_module._evaluate_component_doc_metadata_parity(
        {
            "components": [
                {
                    "component_id": "",
                    "component_name": "Component Alpha",
                    "component_type": "module",
                    "documentation_path": "ai_docs/component_alpha.json",
                    "compliance_status": "I1_I2_I3_I4_compliant",
                }
            ],
            "component_docs": {
                "Component Alpha": {
                    "component_id": "component_alpha",
                    "component_name": "Component Alpha",
                    "component_type": "module",
                    "compliance_status": "I1_I2_I3_I4_compliant",
                }
            },
        }
    )

    assert findings == []


def test_build_expected_component_dependents_skips_dependencies_with_duplicate_file_paths() -> None:
    dependents = kb_integrity_module._build_expected_component_dependents(
        [
            {"component_id": "duplicate_a", "file_path": "src/shared.py", "dependencies": []},
            {"component_id": "duplicate_b", "file_path": "src/shared.py", "dependencies": []},
            {"component_id": "consumer", "file_path": "src/consumer.py", "dependencies": ["src/shared.py"]},
        ]
    )

    assert dependents["duplicate_a"] == []
    assert dependents["duplicate_b"] == []


def test_component_index_schema_helpers_skip_non_list_or_none_inputs() -> None:
    context = {
        "components": [
            {
                "component_id": "component_alpha",
                "test_coverage_percentage": None,
                "creation_timestamp": "2026-04-03T00:00:00Z",
                "last_modified_timestamp": "2026-04-03T00:00:00Z",
                "dependencies": "not-a-list",
                "related_techniques": "not-a-list",
                "dependents": "not-a-list",
            }
        ]
    }

    assert kb_integrity_module._evaluate_component_index_test_coverage_percentage_valid(context) == []
    assert kb_integrity_module._evaluate_component_index_timestamp_fields_valid(context) == []
    assert kb_integrity_module._evaluate_component_index_dependencies_entries_non_empty(context) == []
    assert kb_integrity_module._evaluate_component_index_dependencies_entries_unique(context) == []
    assert kb_integrity_module._evaluate_component_index_related_techniques_entries_non_empty(context) == []
    assert kb_integrity_module._evaluate_component_index_dependents_entries_non_empty(context) == []


def test_component_doc_targeted_test_file_rule_catches_blank_path(tmp_path: Path) -> None:
    findings = kb_integrity_module._evaluate_component_doc_targeted_test_file_exists(
        {
            "workspace_root": str(tmp_path),
            "components": [{"component_id": "component_alpha", "documentation_path": "ai_docs/component_alpha.json"}],
            "component_docs": {
                "component_alpha": {"test_coverage": {"targeted_test_file": ""}}
            },
        }
    )

    assert findings[0].field_name == "test_coverage.targeted_test_file"


def test_component_doc_test_coverage_field_set_exact_skips_until_expected_fields_exist() -> None:
    findings = kb_integrity_module._evaluate_component_doc_test_coverage_field_set_exact(
        {
            "components": [{"component_id": "component_alpha", "documentation_path": "ai_docs/component_alpha.json"}],
            "component_docs": {"component_alpha": {"test_coverage": {"status": "targeted_tests_added"}}},
        }
    )

    assert findings == []


def test_component_doc_path_and_dependency_rules_catch_invalid_entries(tmp_path: Path) -> None:
    file_path_findings = kb_integrity_module._evaluate_component_doc_file_paths_exist(
        {
            "workspace_root": str(tmp_path),
            "components": [
                {"component_id": "component_alpha", "documentation_path": "ai_docs/component_alpha.json"},
                {"component_id": "component_beta", "documentation_path": "ai_docs/component_beta.json"},
            ],
            "component_docs": {
                "component_alpha": {"file_paths": "not-a-list"},
                "component_beta": {"file_paths": [""]},
            },
        }
    )
    dependency_findings = kb_integrity_module._evaluate_component_doc_dependencies_exist(
        {
            "workspace_root": str(tmp_path),
            "components": [
                {"component_id": "component_alpha", "documentation_path": "ai_docs/component_alpha.json"},
                {"component_id": "component_beta", "documentation_path": "ai_docs/component_beta.json"},
            ],
            "component_docs": {
                "component_alpha": {"dependencies": "not-a-list"},
                "component_beta": {"dependencies": [""]},
            },
        }
    )

    assert len(file_path_findings) == 1
    assert file_path_findings[0].field_name == "file_paths"
    assert len(dependency_findings) == 1
    assert dependency_findings[0].field_name == "dependencies"


def test_supported_cli_command_rejects_blank_missing_tokens_and_unknown_commands() -> None:
    assert kb_integrity_module._is_supported_cli_command("") is False
    assert kb_integrity_module._is_supported_cli_command("echo not-inf-work") is False
    assert kb_integrity_module._is_supported_cli_command("python -m inf_work unsupported") is False


def test_python_api_helpers_cover_invalid_exports_and_entries(tmp_path: Path) -> None:
    module_path = tmp_path / "src" / "component_alpha.py"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text("__all__ = unknown_name\nexported_symbol = 1\n", encoding="utf-8")

    exported_names, explicit_all = kb_integrity_module._extract_module_export_names(module_path)
    documented_symbols, entry_kind = kb_integrity_module._extract_documented_python_api_symbols("not a valid api entry")
    findings = kb_integrity_module._evaluate_component_doc_python_api_symbols_valid(
        {
            "workspace_root": str(tmp_path),
            "components": [
                {
                    "component_id": "component_alpha",
                    "documentation_path": "ai_docs/component_alpha.json",
                    "file_path": "src/component_alpha.py",
                }
            ],
            "component_docs": {
                "component_alpha": {"interfaces": {"python_api": ["not a valid api entry"]}}
            },
        }
    )

    assert "exported_symbol" in exported_names
    assert explicit_all is None
    assert documented_symbols == set()
    assert entry_kind is None
    assert findings[0].field_name == "interfaces.python_api"


def test_component_doc_notes_non_empty_reports_empty_notes() -> None:
    findings = kb_integrity_module._evaluate_component_doc_notes_non_empty(
        {
            "components": [{"component_id": "component_alpha", "documentation_path": "ai_docs/component_alpha.json"}],
            "component_docs": {"component_alpha": {"notes": []}},
        }
    )

    assert findings[0].field_name == "notes"


def test_component_doc_interface_and_performance_metric_helpers_skip_non_dict_values() -> None:
    context = {
        "components": [
            {
                "component_id": "component_alpha",
                "component_type": "python_module",
                "documentation_path": COMPONENT_ALPHA_DOC_PATH,
            }
        ],
        "component_docs": {
            "component_alpha": {
                "interfaces": [],
                "performance_metrics": [],
            }
        },
    }

    assert kb_integrity_module._evaluate_component_doc_interfaces_match_component_type(context) == []
    assert kb_integrity_module._evaluate_component_doc_interfaces_values_are_lists(context) == []
    assert kb_integrity_module._evaluate_component_doc_interfaces_entries_non_empty(context) == []
    assert kb_integrity_module._evaluate_component_doc_performance_metrics_match_component_type(context) == []
    assert kb_integrity_module._evaluate_component_doc_performance_metrics_values_non_empty(context) == []


def test_metadata_parity_helpers_report_mismatched_counts_and_timestamps() -> None:
    context = {
        "bug_fixes": [{"created_timestamp": "2026-04-03T00:00:00Z"}],
        "innovations": [{"created_timestamp": "2026-04-03T00:00:00Z"}],
        "automation_patterns": [{"created_timestamp": "2026-04-03T00:00:00Z"}],
        "sessions": [{"created_timestamp": "2026-04-03T00:00:00Z"}],
        "techniques": [{"created_timestamp": "2026-04-03T00:00:00Z"}],
        "bug_fixes_payload": {"metadata": {"total_count": 0, "last_updated": "stale"}},
        "innovations_payload": {"metadata": {"total_count": 0, "last_updated": "stale"}},
        "automation_payload": {"metadata": {"total_count": 0, "last_updated": "stale"}},
        "session_history_payload": {"metadata": {"total_sessions": 0}},
        "techniques_payload": {"metadata": {"last_updated": "stale"}},
    }

    assert kb_integrity_module._evaluate_bug_fixes_metadata_count_parity(context)[0].field_name == "metadata.total_count"
    assert kb_integrity_module._evaluate_innovations_metadata_count_parity(context)[0].field_name == "metadata.total_count"
    assert kb_integrity_module._evaluate_automation_patterns_metadata_count_parity(context)[0].field_name == "metadata.total_count"
    assert kb_integrity_module._evaluate_session_history_metadata_count_parity(context)[0].field_name == "metadata.total_sessions"
    assert kb_integrity_module._evaluate_techniques_metadata_last_updated_parity(context)[0].field_name == "metadata.last_updated"
    assert kb_integrity_module._evaluate_bug_fixes_metadata_last_updated_parity(context)[0].field_name == "metadata.last_updated"
    assert kb_integrity_module._evaluate_innovations_metadata_last_updated_parity(context)[0].field_name == "metadata.last_updated"


def test_component_index_test_coverage_parity_reports_missing_snapshot_and_module_entries() -> None:
    context = {
        "components": [{"component_id": "component_alpha", "file_path": "src/component_alpha.py", "test_coverage_percentage": 90}],
        "coverage_snapshot_payload": None,
    }
    missing_snapshot_findings = kb_integrity_module._evaluate_component_index_test_coverage_parity(context)
    missing_module_findings = kb_integrity_module._evaluate_component_index_test_coverage_parity(
        {
            "components": [{"component_id": "component_alpha", "file_path": "src/component_alpha.py", "test_coverage_percentage": 90}],
            "coverage_snapshot_payload": {"module_coverage": []},
        }
    )

    assert missing_snapshot_findings[0].field_name == "coverage_snapshot"
    assert missing_module_findings[0].field_name == "module_coverage"


def test_validate_knowledge_base_reports_component_doc_auto_generated_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_component_alpha_doc(
        workspace_root,
        auto_generated=False,
        notes=["Auto-generated drift fixture keeps notes valid."],
    )

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "auto_generated" for issue in result.issues)


def test_validate_knowledge_base_reports_component_doc_targeted_test_file_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_component_alpha_doc(
        workspace_root,
        test_coverage={"targeted_test_file": "tests/test_missing_component_alpha.py", "status": "targeted_tests_added"},
        notes=["Targeted-test drift fixture keeps notes valid."],
    )

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "test_coverage.targeted_test_file" for issue in result.issues)


def test_validate_knowledge_base_reports_component_doc_test_coverage_field_set_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_alpha.json").read_text(encoding="utf-8"))
    payload["test_coverage"]["unexpected_field"] = "drift"
    write_json(workspace_root / "ai_docs" / "component_alpha.json", payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "test_coverage" for issue in result.issues)


def test_validate_knowledge_base_reports_component_doc_test_coverage_status_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "test_coverage.status" for issue in result.issues)


def test_validate_knowledge_base_reports_component_doc_test_coverage_status_component_type_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "test_coverage.status" for issue in result.issues)


def test_validate_knowledge_base_reports_component_doc_interfaces_component_type_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "interfaces.python_api" for issue in result.issues)


def test_validate_knowledge_base_reports_governance_artifact_interface_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "interfaces.source_of_truth" for issue in result.issues)


def test_validate_knowledge_base_reports_component_doc_interface_value_type_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "interfaces.python_api" for issue in result.issues)


def test_validate_knowledge_base_reports_governance_artifact_interface_value_type_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "interfaces.source_of_truth" for issue in result.issues)


def test_validate_knowledge_base_reports_component_doc_interface_entries_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "interfaces.python_api" for issue in result.issues)


def test_validate_knowledge_base_reports_governance_artifact_interface_entries_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "interfaces.source_of_truth" for issue in result.issues)


def test_validate_knowledge_base_reports_component_doc_performance_metrics_component_type_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "performance_metrics" for issue in result.issues)


def test_validate_knowledge_base_reports_governance_artifact_performance_metrics_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "performance_metrics" for issue in result.issues)


def test_validate_knowledge_base_reports_component_doc_performance_metrics_value_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "performance_metrics" for issue in result.issues)


def test_validate_knowledge_base_reports_governance_artifact_performance_metrics_value_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "performance_metrics" for issue in result.issues)


def test_validate_knowledge_base_reports_component_doc_file_paths_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "file_paths" for issue in result.issues)


def test_validate_knowledge_base_reports_component_doc_dependencies_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "dependencies" for issue in result.issues)


def test_validate_knowledge_base_reports_component_doc_cli_command_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "interfaces.cli" for issue in result.issues)


def test_validate_knowledge_base_accepts_refresh_artifacts_cli_command(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is True
    assert result.issues == []


def test_validate_knowledge_base_reports_component_doc_python_api_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "interfaces.python_api" for issue in result.issues)


def test_validate_knowledge_base_reports_component_doc_notes_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "notes" for issue in result.issues)


def test_validate_knowledge_base_reports_component_index_dependents_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(
        issue.source_file == "ai_docs/component_index.json" and issue.field_name == "dependents"
        for issue in result.issues
    )


def test_validate_knowledge_base_reports_component_index_dependents_entry_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["dependents"] = [""]
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(
        issue.source_file == "ai_docs/component_index.json" and issue.field_name == "dependents"
        for issue in result.issues
    )


def test_validate_knowledge_base_reports_component_index_file_path_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["file_path"] = ""
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(
        issue.source_file == "ai_docs/component_index.json" and issue.field_name == "file_path"
        for issue in result.issues
    )


def test_validate_knowledge_base_reports_component_index_performance_metrics_field_set_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["performance_metrics"] = {
        "response_latency_target": "<5s",
        "memory_profile": "bounded",
        "unexpected_field": "drift",
    }
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(
        issue.source_file == "ai_docs/component_index.json" and issue.field_name == "performance_metrics"
        for issue in result.issues
    )


def test_validate_knowledge_base_reports_component_index_performance_metrics_value_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["performance_metrics"] = {
        "response_latency_target": "",
        "memory_profile": "bounded",
    }
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(
        issue.source_file == "ai_docs/component_index.json" and issue.field_name == "performance_metrics"
        for issue in result.issues
    )


def test_validate_knowledge_base_reports_component_index_known_issues_entry_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["known_issues"] = [""]
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(
        issue.source_file == "ai_docs/component_index.json" and issue.field_name == "known_issues"
        for issue in result.issues
    )


def test_validate_knowledge_base_reports_component_index_documentation_path_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["documentation_path"] = ""
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    documentation_path_issues = [
        issue
        for issue in result.issues
        if issue.source_file == "ai_docs/component_index.json" and issue.field_name == "documentation_path"
    ]
    assert len(documentation_path_issues) == 1


def test_validate_knowledge_base_reports_component_index_component_name_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["component_name"] = ""
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    failing_pairs = {(issue.source_file, issue.field_name) for issue in result.issues}
    assert ("ai_docs/component_index.json", "component_name") in failing_pairs


def test_validate_knowledge_base_reports_component_index_component_name_uniqueness_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    failing_pairs = {(issue.source_file, issue.field_name) for issue in result.issues}
    assert ("ai_docs/component_index.json", "component_name") in failing_pairs


def test_validate_knowledge_base_reports_component_index_component_id_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["component_id"] = ""
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    failing_pairs = {(issue.source_file, issue.field_name) for issue in result.issues}
    assert ("ai_docs/component_index.json", "component_id") in failing_pairs


def test_validate_knowledge_base_reports_component_index_component_id_uniqueness_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    failing_pairs = {(issue.source_file, issue.field_name) for issue in result.issues}
    assert ("ai_docs/component_index.json", "component_id") in failing_pairs


def test_validate_knowledge_base_reports_component_index_file_path_uniqueness_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    failing_pairs = {(issue.source_file, issue.field_name) for issue in result.issues}
    assert ("ai_docs/component_index.json", "file_path") in failing_pairs


def test_validate_knowledge_base_reports_component_index_component_type_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["component_type"] = "unknown_type"
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    failing_pairs = {(issue.source_file, issue.field_name) for issue in result.issues}
    assert ("ai_docs/component_index.json", "component_type") in failing_pairs


def test_validate_knowledge_base_reports_component_index_dependencies_entry_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["dependencies"] = [""]
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(
        issue.source_file == "ai_docs/component_index.json" and issue.field_name == "dependencies"
        for issue in result.issues
    )


def test_validate_knowledge_base_reports_component_index_dependencies_entry_uniqueness_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["dependencies"] = ["src/dup.py", "src/dup.py"]
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(
        issue.source_file == "ai_docs/component_index.json" and issue.field_name == "dependencies"
        for issue in result.issues
    )


def test_validate_knowledge_base_reports_component_index_related_techniques_entry_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["related_techniques"] = [""]
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(
        issue.source_file == "ai_docs/component_index.json" and issue.field_name == "related_techniques"
        for issue in result.issues
    )


def test_validate_knowledge_base_reports_kb_index_metadata_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "knowledge_base" / "kb_index.json",
        {
            "last_updated": "2026-03-31T00:00:00Z",
            "total_techniques": 999,
            "total_bug_fixes": 1,
            "total_innovations": 1,
            "total_automation_patterns": 2,
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
                "by_category": {
                    "architectural": ["wrong_technique"]
                },
                "by_constraint": {},
                "by_error_code": {},
                "by_automation_type": {},
            },
        },
    )

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    failing_fields = {issue.field_name for issue in result.issues}
    assert "total_techniques" in failing_fields
    assert "total_automation_patterns" in failing_fields
    assert "constraint_compliance_stats" in failing_fields
    assert "automation_success_metrics" in failing_fields
    assert "lookup_indices.by_category" in failing_fields
    assert "lookup_indices.by_constraint" in failing_fields


def test_validate_knowledge_base_reports_kb_index_last_updated_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(issue.field_name == "last_updated" for issue in result.issues)


def test_validate_knowledge_base_reports_source_metadata_count_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "knowledge_base" / "automation_patterns.json",
        {
            "automation_patterns": [
                {
                    "id": "automation_alpha",
                    "automation_type": "validation",
                    "pattern_name": "Automation Alpha",
                    "success_rate": 1.0,
                    "false_positive_rate": 0.0,
                    "related_techniques": ["technique_alpha"],
                }
            ],
            "metadata": {"total_count": 9},
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
            "metadata": {"total_sessions": 99},
        },
    )

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    failing_pairs = {(issue.source_file, issue.field_name) for issue in result.issues}
    assert ("knowledge_base/automation_patterns.json", "metadata.total_count") in failing_pairs
    assert ("knowledge_base/session_history.json", "metadata.total_sessions") in failing_pairs


def test_validate_knowledge_base_reports_source_metadata_timestamp_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    write_json(
        workspace_root / "knowledge_base" / "techniques.json",
        {
            "techniques": [
                {
                    "id": "technique_alpha",
                    "name": "Technique Alpha",
                    "category": "architectural",
                    "created_timestamp": "2026-03-31T00:00:00Z",
                    "constraints_compliance": ["I1", "I2", "I3", "I4"],
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    failing_pairs = {(issue.source_file, issue.field_name) for issue in result.issues}
    assert ("knowledge_base/techniques.json", "metadata.last_updated") in failing_pairs
    assert ("knowledge_base/session_history.json", "metadata.first_session") in failing_pairs
    assert ("knowledge_base/session_history.json", "metadata.last_session") in failing_pairs


def test_validate_knowledge_base_reports_component_index_summary_metadata_drift(tmp_path: Path) -> None:
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
            "metadata": {"total_components": 9, "last_updated": "2026-03-31T00:00:00Z"},
            "health_status": {"total_healthy": 0, "total_degraded": 2, "total_failing": 1},
        },
    )

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    failing_pairs = {(issue.source_file, issue.field_name) for issue in result.issues}
    assert ("ai_docs/component_index.json", "metadata.total_components") in failing_pairs
    assert ("ai_docs/component_index.json", "health_status.total_healthy") in failing_pairs
    assert ("ai_docs/component_index.json", "health_status.total_degraded") in failing_pairs
    assert ("ai_docs/component_index.json", "health_status.total_failing") in failing_pairs


def test_validate_knowledge_base_reports_component_index_timestamp_metadata_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    failing_pairs = {(issue.source_file, issue.field_name) for issue in result.issues}
    assert ("ai_docs/component_index.json", "last_modified_timestamp") in failing_pairs
    assert ("ai_docs/component_index.json", "metadata.last_updated") in failing_pairs


def test_validate_knowledge_base_reports_component_index_test_coverage_drift(tmp_path: Path) -> None:
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

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(
        issue.source_file == "ai_docs/component_index.json" and issue.field_name == "test_coverage_percentage"
        for issue in result.issues
    )


def test_validate_knowledge_base_reports_component_index_timestamp_shape_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["creation_timestamp"] = "2026-03-31"
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    failing_pairs = {(issue.source_file, issue.field_name) for issue in result.issues}
    assert ("ai_docs/component_index.json", "creation_timestamp") in failing_pairs
    assert ("ai_docs/component_index.json", "metadata.last_updated") not in failing_pairs


def test_validate_knowledge_base_reports_component_index_health_status_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["health_status"] = "unknown"
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(
        issue.source_file == "ai_docs/component_index.json" and issue.field_name == "health_status"
        for issue in result.issues
    )


def test_validate_knowledge_base_reports_component_index_compliance_status_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["compliance_status"] = "violations_detected"
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(
        issue.source_file == "ai_docs/component_index.json" and issue.field_name == "compliance_status"
        for issue in result.issues
    )


def test_validate_knowledge_base_reports_component_index_complexity_score_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["complexity_score"] = -1
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(
        issue.source_file == "ai_docs/component_index.json" and issue.field_name == "complexity_score"
        for issue in result.issues
    )


def test_validate_knowledge_base_reports_component_index_test_coverage_percentage_shape_drift(tmp_path: Path) -> None:
    workspace_root = create_workspace(tmp_path)
    payload = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    payload["components"][0]["test_coverage_percentage"] = 101
    write_json(workspace_root / "ai_docs" / "component_index.json", payload)

    result = validate_knowledge_base(workspace_root)

    assert result.compliant is False
    assert any(
        issue.source_file == "ai_docs/component_index.json" and issue.field_name == "test_coverage_percentage"
        for issue in result.issues
    )


def test_kb_check_cli_outputs_json_for_current_workspace() -> None:
    workspace_root = Path(__file__).resolve().parents[1]
    environment = {
        **os.environ,
        "PYTHONPATH": str(workspace_root / "src"),
    }
    completed = subprocess.run(
        [sys.executable, "-m", "inf_work.kb_check", str(workspace_root), "--pretty"],
        check=False,
        capture_output=True,
        text=True,
        cwd=workspace_root,
        env=environment,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["compliant"] is True
    assert payload["issues"] == []


def test_unified_kb_subcommand_outputs_json_for_current_workspace() -> None:
    workspace_root = Path(__file__).resolve().parents[1]
    environment = {
        **os.environ,
        "PYTHONPATH": str(workspace_root / "src"),
    }
    completed = subprocess.run(
        [sys.executable, "-m", "inf_work", "kb", str(workspace_root), "--pretty"],
        check=False,
        capture_output=True,
        text=True,
        cwd=workspace_root,
        env=environment,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["compliant"] is True
    assert payload["issues"] == []


def test_unified_all_subcommand_outputs_kb_results_for_current_workspace() -> None:
    workspace_root = Path(__file__).resolve().parents[1]
    write_system_status_outputs(workspace_root)
    environment = {
        **os.environ,
        "PYTHONPATH": str(workspace_root / "src"),
    }
    completed = subprocess.run(
        [sys.executable, "-m", "inf_work", "all", str(workspace_root), "--pretty"],
        check=False,
        capture_output=True,
        text=True,
        cwd=workspace_root,
        env=environment,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["compliant"] is True
    assert payload["knowledge_base"]["compliant"] is True
    assert payload["knowledge_base"]["issues"] == []
