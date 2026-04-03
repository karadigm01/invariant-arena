from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
import inf_work.system_status as system_status_module
from inf_work.rules import RuleFinding, RuleResult
from inf_work.system_status import (
    _count_with_label,
    _format_activity_label,
    _render_activity_context,
    _render_operator_shortcut_pairs,
    _render_recent_governance_lines,
    _render_where_to_look_first_lines,
    _render_system_summary_footer,
    SystemStatusSnapshot,
    build_system_status_snapshot,
    repair_and_validate_system_summary,
    repair_and_validate_system_status,
    render_system_summary_markdown,
    render_system_status_markdown,
    run_summary_rules,
    run_status_rules,
    validate_system_summary,
    validate_system_status,
    write_system_status_outputs,
)


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_workspace_json(relative_path: str) -> dict[str, object]:
    return json.loads((WORKSPACE_ROOT / relative_path).read_text(encoding="utf-8"))


def _minimal_status_snapshot_payload(workspace_root: Path) -> dict[str, object]:
    return {
        "generated_at": "2026-04-03T00:00:00Z",
        "workspace_root": str(workspace_root),
        "canonical_json_path": "ai_docs/system_status_snapshot.json",
        "derived_markdown_path": "SYSTEM_STATUS.md",
        "coverage_threshold": 85,
        "component_health": {
            "total_components": 0,
            "healthy_components": 0,
            "degraded_components": 0,
            "failing_components": 0,
            "below_threshold_components": [],
            "components": [],
        },
        "test_suite_summary": {
            "total_tests": 0,
            "summary_text": "0 collected",
            "pass_rate": 0.0,
            "pending_or_skipped_tests": 0,
            "coverage_by_module": [],
        },
        "knowledge_base_metrics": {
            "technique_count": 0,
            "latest_technique": None,
            "innovation_count": 0,
            "latest_innovation": None,
            "bug_fix_count": 0,
            "automation_pattern_count": 0,
            "last_kb_update_timestamp": "2026-04-03T00:00:00Z",
        },
        "recent_session_activity": {
            "session_count": 0,
            "latest_session": None,
            "latest_summary": "none",
            "latest_outcomes": [],
            "latest_automation_pattern": None,
            "latest_technique": None,
            "latest_bug_fix": None,
        },
        "schema_contract_integrity": {
            "schema_bundles": [],
            "workspace_coherence_validation": {"compliant": True, "missing_directories": []},
            "cross_reference_validation": {"compliant": True, "issue_count": 0, "issues": []},
            "orphaned_or_dangling_references": {"component_files": [], "component_docs": []},
        },
        "resolver_capabilities": {
            "inference_modes_supported": {"single_hop": True, "multi_hop_explicit": True, "multi_hop_inferred": True},
            "registered_tiles": [],
            "traversal_examples": {},
            "pressure_telemetry_status": {"status": "configured", "enabled": True},
        },
        "known_gaps_technical_debt": {
            "components_with_zero_percent_coverage": [],
            "missing_automation_patterns": [],
            "todo_fixme_items": [],
            "planned_but_unimplemented_features": [],
        },
        "architectural_invariant_compliance": {"I1": {"status": "compliant", "evidence": "ok"}},
        "operator_shortcuts": [],
        "next_recommended_actions": [],
    }


def _minimal_status_snapshot(workspace_root: Path) -> SystemStatusSnapshot:
    return SystemStatusSnapshot(**_minimal_status_snapshot_payload(workspace_root))


def test_build_system_status_snapshot_contains_required_sections() -> None:
    snapshot = build_system_status_snapshot(WORKSPACE_ROOT)
    payload = snapshot.to_dict()
    latest_session = payload["recent_session_activity"]["latest_session"]
    latest_automation_pattern = payload["recent_session_activity"]["latest_automation_pattern"]
    session_history = _read_workspace_json("knowledge_base/session_history.json")
    automation_patterns = _read_workspace_json("knowledge_base/automation_patterns.json")
    kb_index = _read_workspace_json("knowledge_base/kb_index.json")
    component_index = _read_workspace_json("ai_docs/component_index.json")
    coverage_snapshot = _read_workspace_json("ai_docs/test_coverage_snapshot.json")
    expected_generated_at = max(
        component_index["metadata"]["last_updated"],
        kb_index["last_updated"],
        session_history["metadata"]["last_session"],
        system_status_module._normalize_utc_timestamp(coverage_snapshot["generated_at"]),
    )

    assert payload["component_health"]["total_components"] >= 4
    assert payload["test_suite_summary"]["total_tests"] >= 1
    assert payload["test_suite_summary"]["summary_text"]
    assert payload["test_suite_summary"]["summary_text"].endswith("collected")
    assert payload["test_suite_summary"]["summary_mode"] == "collection_only"
    assert "raw_summary" not in payload["test_suite_summary"]
    assert payload["recent_session_activity"]["session_count"] >= 1
    assert latest_session["session_id"] == session_history["sessions"][-1]["session_id"]
    assert latest_automation_pattern["id"] == automation_patterns["automation_patterns"][-1]["id"]
    assert payload["recent_session_activity"]["latest_technique"]["id"] == "technique_deterministic_profile_surface_promotion"
    assert payload["recent_session_activity"]["latest_bug_fix"]["id"] == "bugfix_core_reference_malformed_schema_arrays"
    assert payload["knowledge_base_metrics"]["innovation_count"] == 2
    assert payload["knowledge_base_metrics"]["technique_count"] == kb_index["total_techniques"]
    assert payload["knowledge_base_metrics"]["latest_innovation"]["id"] == "innovation_bounded_resolver_multi_hop_enablement"
    assert payload["resolver_capabilities"]["inference_modes_supported"]["single_hop"] is True
    assert payload["resolver_capabilities"]["inference_modes_supported"]["multi_hop_explicit"] is True
    assert payload["resolver_capabilities"]["inference_modes_supported"]["multi_hop_inferred"] is True
    assert payload["resolver_capabilities"]["pressure_telemetry_status"]["enabled"] is True
    assert payload["resolver_capabilities"]["pressure_telemetry_status"]["status"] == "configured"
    assert len(payload["resolver_capabilities"]["registered_tiles"]) == 3
    assert payload["resolver_capabilities"]["traversal_examples"]["explicit"]["complete"] is True
    assert payload["resolver_capabilities"]["traversal_examples"]["inferred"]["complete"] is True
    assert "schema_bundles" in payload["schema_contract_integrity"]
    assert "I1" in payload["architectural_invariant_compliance"]
    assert payload["operator_shortcuts"][0]["command"] == "make all-report"
    assert payload["operator_shortcuts"][0]["task_label"] == "workspace: all"
    assert any(shortcut["command"] == "make resolver-report" for shortcut in payload["operator_shortcuts"])
    assert any(shortcut["task_label"] == "workspace: resolver-only" for shortcut in payload["operator_shortcuts"])
    assert any(shortcut["command"] == "make component-report" for shortcut in payload["operator_shortcuts"])
    assert any(shortcut["task_label"] == "workspace: component-governance" for shortcut in payload["operator_shortcuts"])
    assert any(shortcut["command"] == "make coverage-snapshot" for shortcut in payload["operator_shortcuts"])
    assert any(shortcut["task_label"] == "workspace: coverage-snapshot" for shortcut in payload["operator_shortcuts"])
    assert any(shortcut["command"] == "make refresh-artifacts" for shortcut in payload["operator_shortcuts"])
    assert any(shortcut["task_label"] == "workspace: refresh-artifacts" for shortcut in payload["operator_shortcuts"])
    assert payload["canonical_json_path"] == "ai_docs/system_status_snapshot.json"
    assert payload["generated_at"] == expected_generated_at
    planned_features = payload["known_gaps_technical_debt"]["planned_but_unimplemented_features"]
    assert all(feature["feature"] != "Session history rollups" for feature in planned_features)
    assert all(feature["feature"] != "Multi-hop resolver modes" for feature in planned_features)
    recommended_actions = payload["next_recommended_actions"]
    assert recommended_actions == []


def test_build_system_status_snapshot_surfaces_latest_kb_records_end_to_end() -> None:
    snapshot = build_system_status_snapshot(WORKSPACE_ROOT)
    session_history = _read_workspace_json("knowledge_base/session_history.json")
    automation_patterns = _read_workspace_json("knowledge_base/automation_patterns.json")

    latest_session = session_history["sessions"][-1]
    latest_automation_pattern = automation_patterns["automation_patterns"][-1]
    surfaced_session = snapshot.recent_session_activity["latest_session"]
    surfaced_automation_pattern = snapshot.recent_session_activity["latest_automation_pattern"]

    assert latest_session["session_id"].startswith("session_")
    assert latest_automation_pattern["id"].startswith("automation_")
    assert surfaced_session["session_id"] == latest_session["session_id"]
    assert surfaced_session["summary"] == latest_session["summary"]
    assert surfaced_session["related_automation_patterns"] == latest_session["related_automation_patterns"]
    assert surfaced_automation_pattern["id"] == latest_automation_pattern["id"]
    assert surfaced_automation_pattern["pattern_name"] == latest_automation_pattern["pattern_name"]
    assert surfaced_automation_pattern["related_techniques"] == latest_automation_pattern["related_techniques"]
    assert snapshot.recent_session_activity["latest_summary"] == latest_session["summary"]


def test_render_system_status_markdown_contains_canonical_sections() -> None:
    snapshot = build_system_status_snapshot(WORKSPACE_ROOT)
    markdown = render_system_status_markdown(snapshot)
    latest_session = snapshot.recent_session_activity["latest_session"]
    latest_automation_pattern = snapshot.recent_session_activity["latest_automation_pattern"]
    latest_technique = snapshot.recent_session_activity["latest_technique"]
    latest_bug_fix = snapshot.recent_session_activity["latest_bug_fix"]
    expected_highlights = (
        f"- **KB Highlights**: session `{_format_activity_label(latest_session['session_id'], latest_session.get('created_timestamp'))}`; "
        f"automation `{_format_activity_label(latest_automation_pattern['pattern_name'], latest_automation_pattern.get('created_timestamp'))}`; "
        f"technique `{_format_activity_label(latest_technique['name'], latest_technique.get('created_timestamp'))}`; "
        f"bug fix `{_format_activity_label(latest_bug_fix['id'], latest_bug_fix.get('created_timestamp'))}`"
    )
    technique_count = snapshot.knowledge_base_metrics["technique_count"]
    latest_technique_name = snapshot.knowledge_base_metrics["latest_technique"]["name"]

    assert "# System Status" in markdown
    assert "## 1. Component Health" in markdown
    assert "## 2. Test Inventory" in markdown
    assert "- **Collected Tests**:" in markdown
    assert "- **Collection Summary**:" in markdown
    assert f"- **Technique Count**: {technique_count} (latest: {latest_technique_name})" in markdown
    assert "- **Innovation Count**: 2 (latest: innovation_bounded_resolver_multi_hop_enablement)" in markdown
    assert "## 4. Recent Governance Highlights" in markdown
    assert expected_highlights in markdown
    assert f"- **Why It Matters**: {_render_activity_context(latest_session['summary'])}" in markdown
    assert "## 9. Operator Shortcuts" in markdown
    assert "## 10. Next Recommended Actions" in markdown
    assert "- **Single-Hop**: True" in markdown
    assert "- **Multi-Hop Explicit**: True" in markdown
    assert "- **Multi-Hop Inferred**: True" in markdown
    assert "- **Pressure Telemetry**: configured" in markdown
    assert "- **Explicit Route Example**: workspace_governance -> component_index -> knowledge_base_index" in markdown
    assert "- **Inferred Route Example**: workspace_governance -> knowledge_base_index" in markdown
    assert "`make all-report-fix-status`" in markdown
    assert "`make component-report`" in markdown
    assert "`workspace: component-governance`" in markdown
    assert "`make coverage-snapshot`" in markdown
    assert "`workspace: coverage-snapshot`" in markdown
    assert "`make refresh-artifacts`" in markdown
    assert "`workspace: refresh-artifacts`" in markdown
    assert "`workspace: all-fix-status`" in markdown
    assert "## Where to look first" in markdown
    assert "`README.md`" in markdown
    assert "`SYSTEM_SUMMARY.md`" in markdown
    assert "`ai_docs/system_status_snapshot.json`" in markdown
    assert "`ai_docs/component_index.json`" in markdown
    assert "`knowledge_base/kb_index.json`" in markdown
    assert "- **Actions**: no immediate follow-up recorded" in markdown


def test_status_validation_dataclasses_to_dict_serialize_nested_results() -> None:
    issue = system_status_module.StatusValidationIssue(
        source_file="SYSTEM_STATUS.md",
        item_identifier="summary",
        field_name="artifact_presence",
        message="missing",
    )
    rule_result = RuleResult(
        rule_id="status.artifacts_exist",
        domain="status",
        category="artifact_integrity",
        severity="error",
        description="status artifact exists",
        passed=False,
        findings=[
            RuleFinding(
                message="missing",
                source_file="SYSTEM_STATUS.md",
                item_identifier="summary",
                field_name="artifact_presence",
            )
        ],
    )
    result = system_status_module.StatusValidationResult(
        workspace_root=str(WORKSPACE_ROOT),
        snapshot_path="ai_docs/system_status_snapshot.json",
        markdown_path="SYSTEM_STATUS.md",
        summary_path="SYSTEM_SUMMARY.md",
        compliant=False,
        issues=[issue],
        rule_results=[rule_result],
    )

    assert issue.to_dict()["field_name"] == "artifact_presence"
    payload = result.to_dict()
    assert payload["issues"][0]["message"] == "missing"
    assert payload["rule_results"][0]["rule_id"] == "status.artifacts_exist"


def test_normalize_utc_timestamp_handles_blank_invalid_and_offsets() -> None:
    assert system_status_module._normalize_utc_timestamp("") == ""
    assert system_status_module._normalize_utc_timestamp("not-a-timestamp") == "not-a-timestamp"
    assert system_status_module._normalize_utc_timestamp("2026-04-03T10:00:00+02:00") == "2026-04-03T08:00:00Z"
    assert system_status_module._normalize_utc_timestamp("2026-04-03T10:00:00") == "2026-04-03T10:00:00Z"


def test_build_test_coverage_snapshot_filters_python_package_modules(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "build").mkdir(parents=True, exist_ok=True)
    (tmp_path / "build" / "runtime_test_coverage.json").write_text(
        json.dumps(
            {
                "meta": {"timestamp": "2026-04-03T10:00:00+00:00"},
                "files": {
                    "src/inf_work/a.py": {"summary": {"percent_covered_display": "100", "num_statements": 4, "covered_lines": 4, "missing_lines": 0}},
                    "tests/test_a.py": {"summary": {"percent_covered_display": "0", "num_statements": 4, "covered_lines": 0, "missing_lines": 4}},
                },
                "totals": {"percent_covered_display": "100", "num_statements": 4, "covered_lines": 4, "missing_lines": 0},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        system_status_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    snapshot = system_status_module.build_test_coverage_snapshot(tmp_path)

    assert snapshot["generated_at"] == "2026-04-03T10:00:00Z"
    assert snapshot["module_coverage"] == [
        {
            "module_path": "src/inf_work/a.py",
            "coverage_percentage": 100,
            "num_statements": 4,
            "covered_lines": 4,
            "missing_lines": 0,
        }
    ]


def test_build_test_coverage_snapshot_raises_when_pytest_cov_fails(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        system_status_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="boom"),
    )

    with pytest.raises(RuntimeError) as error:
        system_status_module.build_test_coverage_snapshot(tmp_path)
    assert "Unable to generate coverage snapshot" in str(error.value)


def test_sync_component_index_coverage_handles_missing_index_and_noop(tmp_path: Path) -> None:
    snapshot = {"generated_at": "2026-04-03T00:00:00Z", "module_coverage": []}

    assert system_status_module._sync_component_index_coverage(tmp_path, snapshot) is None

    component_index_payload = {
        "components": [
            {
                "component_id": "component_alpha",
                "component_name": "Component Alpha",
                "component_type": "python_module",
                "file_path": "src/component_alpha.py",
                "dependencies": [],
                "dependents": [],
                "creation_timestamp": "2026-04-03T00:00:00Z",
                "last_modified_timestamp": "2026-04-03T00:00:00Z",
                "health_status": "healthy",
                "test_coverage_percentage": 100,
                "compliance_status": "I1_I2_I3_I4_compliant",
                "documentation_path": "ai_docs/component_alpha.json",
                "performance_metrics": {"response_latency_target": "<1s", "memory_profile": "bounded"},
                "complexity_score": 1,
                "related_techniques": [],
                "known_issues": [],
            }
        ],
        "metadata": {"last_updated": "2026-04-03T00:00:00Z"},
        "health_status": {"total_healthy": 1, "total_degraded": 0, "total_failing": 0},
    }
    _write_json(tmp_path / "ai_docs" / "component_index.json", component_index_payload)
    matched_snapshot = {
        "generated_at": "2026-04-03T00:00:00Z",
        "module_coverage": [
            {"module_path": "src/component_alpha.py", "coverage_percentage": 100}
        ],
    }

    returned_payload = system_status_module._sync_component_index_coverage(tmp_path, matched_snapshot)

    assert returned_payload == component_index_payload


def test_sync_component_index_coverage_updates_without_generated_at_timestamp(tmp_path: Path) -> None:
    _write_json(
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
                    "creation_timestamp": "2026-04-03T00:00:00Z",
                    "last_modified_timestamp": "2026-04-03T00:00:00Z",
                    "health_status": "healthy",
                    "test_coverage_percentage": 80,
                    "compliance_status": "I1_I2_I3_I4_compliant",
                    "documentation_path": "ai_docs/component_alpha.json",
                }
            ],
            "metadata": {"last_updated": "2026-04-03T00:00:00Z"},
        },
    )

    updated_payload = system_status_module._sync_component_index_coverage(
        tmp_path,
        {"generated_at": "", "module_coverage": [{"module_path": "src/component_alpha.py", "coverage_percentage": 100}]},
    )

    assert updated_payload is not None
    assert updated_payload["components"][0]["test_coverage_percentage"] == 100
    assert updated_payload["components"][0]["last_modified_timestamp"] == "2026-04-03T00:00:00Z"
    assert updated_payload["metadata"]["last_updated"] == "2026-04-03T00:00:00Z"


def test_load_test_coverage_snapshot_and_normalize_payload_helpers(tmp_path: Path) -> None:
    payload = {
        "generated_at": "2026-04-03T00:00:00Z",
        "test_suite_summary": {
            "raw_summary": "remove",
            "command": "remove",
            "summary_mode": "remove",
            "keep": True,
        },
    }
    _write_json(tmp_path / "ai_docs" / "test_coverage_snapshot.json", payload)

    loaded = system_status_module._load_test_coverage_snapshot(tmp_path)

    assert loaded == payload
    assert system_status_module._load_test_coverage_snapshot(tmp_path / "missing") is None
    assert system_status_module._normalize_snapshot_payload(payload)["test_suite_summary"] == {"keep": True}


def test_find_latest_item_and_max_timestamp_helpers() -> None:
    assert system_status_module._find_latest_item([]) is None
    assert system_status_module._find_latest_item([{"id": 1}, {"id": 2}]) == {"id": 2}
    assert system_status_module._max_timestamp([]) is None
    assert system_status_module._max_timestamp(["2026-04-02T00:00:00Z", "2026-04-03T00:00:00Z"]) == "2026-04-03T00:00:00Z"


def test_collect_component_health_marks_below_threshold_and_derived_dependents(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "ai_docs" / "component_index.json",
        {
            "components": [
                {
                    "component_id": "alpha",
                    "component_name": "Alpha",
                    "component_type": "python_module",
                    "file_path": "src/alpha.py",
                    "dependencies": [],
                    "dependents": [],
                    "documentation_path": "ai_docs/alpha.json",
                    "health_status": "healthy",
                    "test_coverage_percentage": 100,
                    "compliance_status": "I1_I2_I3_I4_compliant",
                },
                {
                    "component_id": "beta",
                    "component_name": "Beta",
                    "component_type": "python_module",
                    "file_path": "src/beta.py",
                    "dependencies": ["src/alpha.py"],
                    "dependents": [],
                    "documentation_path": "ai_docs/beta.json",
                    "health_status": "healthy",
                    "test_coverage_percentage": 40,
                    "compliance_status": "I1_I2_I3_I4_compliant",
                },
            ],
            "health_status": {"total_healthy": 2, "total_degraded": 0, "total_failing": 0},
        },
    )

    payload = system_status_module._collect_component_health(tmp_path, 90)

    assert payload["below_threshold_components"] == ["beta"]
    alpha_row = next(component for component in payload["components"] if component["component_id"] == "alpha")
    beta_row = next(component for component in payload["components"] if component["component_id"] == "beta")
    assert alpha_row["derived_dependents"] == ["beta"]
    assert beta_row["coverage_flag"] == "below_threshold"


def test_parse_pytest_summary_handles_missing_and_present_counts() -> None:
    assert system_status_module._parse_pytest_summary("no summary here") == {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
        "errors": 0,
    }
    assert system_status_module._parse_pytest_summary("2 passed, 1 skipped, 3 errors in 0.10s") == {
        "passed": 2,
        "failed": 0,
        "skipped": 1,
        "xfailed": 0,
        "xpassed": 0,
        "errors": 3,
    }


def test_collect_test_suite_summary_tracks_unindexed_python_modules(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "src" / "inf_work").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "inf_work" / "tracked.py").write_text("pass\n", encoding="utf-8")
    (tmp_path / "src" / "inf_work" / "extra.py").write_text("pass\n", encoding="utf-8")
    _write_json(
        tmp_path / "ai_docs" / "component_index.json",
        {
            "components": [
                {
                    "component_id": "tracked_component",
                    "component_name": "Tracked",
                    "component_type": "python_module",
                    "file_path": "src/inf_work/tracked.py",
                    "dependencies": [],
                    "dependents": [],
                    "health_status": "healthy",
                    "test_coverage_percentage": 80,
                    "compliance_status": "I1_I2_I3_I4_compliant",
                }
            ]
        },
    )
    monkeypatch.setattr(
        system_status_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="tests/test_alpha.py\ntests/test_beta.py\n", stderr=""),
    )

    summary = system_status_module._collect_test_suite_summary(tmp_path, 90)

    assert summary["total_tests"] == 2
    assert summary["summary_text"] == "2 collected"
    assert summary["coverage_source"] == "component_index_fallback"
    assert any(module["module_path"] == "src/inf_work/extra.py" and module["tracked_in_component_index"] is False for module in summary["coverage_by_module"])


def test_collect_recent_session_activity_returns_empty_defaults(tmp_path: Path) -> None:
    _write_json(tmp_path / "knowledge_base" / "session_history.json", {"sessions": [], "metadata": {}})
    _write_json(tmp_path / "knowledge_base" / "automation_patterns.json", {"automation_patterns": [], "metadata": {}})
    _write_json(tmp_path / "knowledge_base" / "techniques.json", {"techniques": [], "metadata": {}})
    _write_json(tmp_path / "knowledge_base" / "bug_fixes.json", {"bug_fixes": [], "metadata": {}})

    activity = system_status_module._collect_recent_session_activity(tmp_path)

    assert activity["session_count"] == 0
    assert activity["latest_summary"] == "none"
    assert activity["latest_outcomes"] == []


def test_collect_known_gaps_surfaces_expected_planned_features(tmp_path: Path) -> None:
    _write_json(tmp_path / "knowledge_base" / "automation_patterns.json", {"automation_patterns": [], "metadata": {"total_count": 1}})
    _write_json(tmp_path / "knowledge_base" / "session_history.json", {"sessions": [], "metadata": {}})

    payload = system_status_module._collect_known_gaps(
        tmp_path,
        test_suite_summary={
            "coverage_by_module": [{"module_path": "src/inf_work/missing.py", "coverage_percentage": 0}],
        },
        resolver_capabilities={
            "inference_modes_supported": {"multi_hop_explicit": False, "multi_hop_inferred": False},
            "pressure_telemetry_status": {"enabled": False},
        },
    )

    assert payload["components_with_zero_percent_coverage"] == ["src/inf_work/missing.py"]
    assert payload["missing_automation_patterns"] == ["Status regeneration automation pattern is not yet catalogued."]
    feature_names = {feature["feature"] for feature in payload["planned_but_unimplemented_features"]}
    assert feature_names == {"Session history rollups", "Multi-hop resolver modes", "Pressure telemetry"}


def test_collect_schema_contract_integrity_reports_dangling_component_references(tmp_path: Path, monkeypatch) -> None:
    _write_json(tmp_path / "core_reference.json", {"system_identity": {"version": "2.0.0"}})
    _write_json(tmp_path / "behavioral_directives.json", {"system_identity": {"version": "2.0.0"}})
    _write_json(
        tmp_path / "ai_docs" / "component_index.json",
        {
            "components": [
                {
                    "component_id": "component_alpha",
                    "component_name": "Component Alpha",
                    "component_type": "python_module",
                    "file_path": "src/missing_alpha.py",
                    "documentation_path": "ai_docs/missing_alpha.json",
                }
            ],
            "metadata": {"schema_version": "2.0.0"},
        },
    )
    _write_json(tmp_path / "knowledge_base" / "techniques.json", {"techniques": [], "metadata": {"schema_version": "2.0.0"}})
    _write_json(tmp_path / "knowledge_base" / "bug_fixes.json", {"bug_fixes": [], "metadata": {"schema_version": "2.0.0"}})
    _write_json(tmp_path / "knowledge_base" / "constraint_innovations.json", {"innovations": [], "metadata": {"schema_version": "2.0.0"}})
    _write_json(tmp_path / "knowledge_base" / "automation_patterns.json", {"automation_patterns": [], "metadata": {"schema_version": "2.0.0"}})
    _write_json(tmp_path / "knowledge_base" / "kb_index.json", {"last_updated": "2026-04-03T00:00:00Z"})
    monkeypatch.setattr(system_status_module, "validate_knowledge_base", lambda root_path: SimpleNamespace(compliant=True, issues=[]))
    monkeypatch.setattr(system_status_module, "validate_workspace", lambda root_path: SimpleNamespace(compliant=True, missing_directories=[]))

    payload = system_status_module._collect_schema_contract_integrity(tmp_path)

    assert payload["orphaned_or_dangling_references"]["component_files"] == ["src/missing_alpha.py"]
    assert payload["orphaned_or_dangling_references"]["component_docs"] == ["ai_docs/missing_alpha.json"]


def test_find_todo_fixme_items_skips_governed_artifacts_and_finds_workspace_notes(tmp_path: Path) -> None:
    (tmp_path / ".venv").mkdir(parents=True, exist_ok=True)
    (tmp_path / "ai_docs" / "backups").mkdir(parents=True, exist_ok=True)
    (tmp_path / "notes.py").write_text("# TODO: cover me\n", encoding="utf-8")
    (tmp_path / "SYSTEM_STATUS.md").write_text("# System Status\n- TODO: ignore me\n", encoding="utf-8")
    (tmp_path / "ai_docs" / "backups" / "archived.md").write_text("- TODO: ignore archive\n", encoding="utf-8")

    findings = system_status_module._find_todo_fixme_items(tmp_path)

    assert findings == [{"path": "notes.py", "line_number": 1, "text": "# TODO: cover me"}]


def test_derive_system_health_label_prefers_failing_then_degraded() -> None:
    base_payload = build_system_status_snapshot(WORKSPACE_ROOT).to_dict()
    base_payload["component_health"]["failing_components"] = 1
    base_payload["component_health"]["degraded_components"] = 1
    failing_snapshot = SystemStatusSnapshot(**base_payload)
    assert system_status_module._derive_system_health_label(failing_snapshot) == "Failing"

    base_payload["component_health"]["failing_components"] = 0
    degraded_snapshot = SystemStatusSnapshot(**base_payload)
    assert system_status_module._derive_system_health_label(degraded_snapshot) == "Degraded"


def test_render_where_to_look_first_lines_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError) as error:
        system_status_module._render_where_to_look_first_lines("unknown")
    assert "Unsupported where-to-look-first mode" in str(error.value)


def test_build_recommended_actions_covers_all_branches() -> None:
    actions = system_status_module._build_recommended_actions(
        {
            "coverage_threshold": 85,
            "component_health": {"below_threshold_components": ["component_alpha"]},
            "known_gaps_technical_debt": {
                "components_with_zero_percent_coverage": ["src/inf_work/component_alpha.py"],
                "missing_automation_patterns": ["Status regeneration automation pattern is not yet catalogued."],
            },
            "knowledge_base_metrics": {"innovation_count": 0},
            "resolver_capabilities": {
                "inference_modes_supported": {"multi_hop_explicit": False, "multi_hop_inferred": False},
            },
        }
    )

    assert [action["priority"] for action in actions] == [1, 2, 3, 4]
    assert "0% modules" in actions[0]["reason"]


def test_build_recommended_actions_handles_below_threshold_without_zero_percent_modules() -> None:
    actions = system_status_module._build_recommended_actions(
        {
            "coverage_threshold": 85,
            "component_health": {"below_threshold_components": ["component_alpha"]},
            "known_gaps_technical_debt": {
                "components_with_zero_percent_coverage": [],
                "missing_automation_patterns": [],
            },
            "knowledge_base_metrics": {"innovation_count": 1},
            "resolver_capabilities": {
                "inference_modes_supported": {"multi_hop_explicit": True, "multi_hop_inferred": True},
            },
        }
    )

    assert len(actions) == 1
    assert "0% modules" not in actions[0]["reason"]


def test_build_status_context_handles_regeneration_exceptions(tmp_path: Path, monkeypatch) -> None:
    _write_json(tmp_path / "ai_docs" / "system_status_snapshot.json", _minimal_status_snapshot_payload(tmp_path))
    (tmp_path / "SYSTEM_STATUS.md").write_text("# System Status\n", encoding="utf-8")
    (tmp_path / "SYSTEM_SUMMARY.md").write_text("# System Summary\n", encoding="utf-8")
    monkeypatch.setattr(system_status_module, "build_system_status_snapshot", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("boom")))

    context = system_status_module._build_status_context(tmp_path)

    assert context["regenerated_snapshot"] is None
    assert context["regenerated_summary"] is None


def test_build_status_context_skips_regenerated_markdown_without_existing_snapshot(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "SYSTEM_STATUS.md").write_text("# System Status\n", encoding="utf-8")
    (tmp_path / "SYSTEM_SUMMARY.md").write_text("# System Summary\n", encoding="utf-8")
    monkeypatch.setattr(system_status_module, "build_system_status_snapshot", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("boom")))

    context = system_status_module._build_status_context(tmp_path)

    assert context["existing_snapshot"] is None
    assert context["regenerated_markdown"] is None


def test_render_system_status_markdown_preserves_planned_feature_entries() -> None:
    payload = build_system_status_snapshot(WORKSPACE_ROOT).to_dict()
    payload["known_gaps_technical_debt"]["planned_but_unimplemented_features"] = [
        {
            "feature": "Pressure telemetry expansion",
            "status": "planned",
            "evidence": "Queued for future governance work.",
        }
    ]

    markdown = render_system_status_markdown(SystemStatusSnapshot(**payload))

    assert "- **Pressure telemetry expansion**: planned — Queued for future governance work." in markdown


def test_status_consistency_helpers_short_circuit_when_artifacts_are_missing() -> None:
    assert system_status_module._evaluate_status_snapshot_matches_workspace(
        {"snapshot_exists": False, "existing_snapshot": None, "regenerated_snapshot": None, "snapshot_path": "snap.json"}
    ) == []
    assert system_status_module._evaluate_status_markdown_matches_snapshot(
        {"snapshot_exists": False, "markdown_exists": True, "existing_markdown": "", "regenerated_markdown": "", "markdown_path": "SYSTEM_STATUS.md"}
    ) == []
    assert system_status_module._evaluate_status_summary_matches_workspace(
        {"summary_exists": False, "existing_summary": None, "regenerated_summary": None, "summary_path": "SYSTEM_SUMMARY.md"}
    ) == []


def test_summary_and_status_artifact_rules_report_missing_files() -> None:
    summary_findings = system_status_module._evaluate_summary_artifact_exists(
        {"summary_exists": False, "summary_path": "SYSTEM_SUMMARY.md"}
    )
    artifact_findings = system_status_module._evaluate_status_artifacts_exist(
        {
            "snapshot_exists": False,
            "markdown_exists": False,
            "summary_exists": False,
            "snapshot_path": "ai_docs/system_status_snapshot.json",
            "markdown_path": "SYSTEM_STATUS.md",
            "summary_path": "SYSTEM_SUMMARY.md",
        }
    )

    assert summary_findings[0].field_name == "artifact_presence"
    assert len(artifact_findings) == 3


def test_run_status_rules_returns_empty_when_no_rules_registered(monkeypatch) -> None:
    monkeypatch.setattr(system_status_module, "get_registered_rules", lambda domain, rule_ids=None: [])

    assert system_status_module.run_status_rules(WORKSPACE_ROOT) == []


def test_write_system_status_outputs_bootstraps_missing_files(tmp_path: Path, monkeypatch) -> None:
    snapshot = _minimal_status_snapshot(tmp_path)
    _write_json(tmp_path / "ai_docs" / "component_index.json", {"components": [], "metadata": {"last_updated": "2026-04-03T00:00:00Z"}, "health_status": {"total_healthy": 0, "total_degraded": 0, "total_failing": 0}})
    _write_json(tmp_path / "knowledge_base" / "kb_index.json", {"last_updated": "2026-04-03T00:00:00Z", "total_techniques": 0, "total_bug_fixes": 0, "total_innovations": 0, "total_automation_patterns": 0})
    monkeypatch.setattr(system_status_module, "build_system_status_snapshot", lambda *args, **kwargs: snapshot)
    monkeypatch.setattr(system_status_module, "render_system_status_markdown", lambda built_snapshot: "# System Status\n")
    monkeypatch.setattr(system_status_module, "render_system_summary_markdown", lambda built_snapshot, component_index, kb_index: "# System Summary\n")

    written = write_system_status_outputs(tmp_path)

    assert written == snapshot
    assert (tmp_path / "SYSTEM_STATUS.md").read_text(encoding="utf-8") == "# System Status\n"
    assert (tmp_path / "SYSTEM_SUMMARY.md").read_text(encoding="utf-8") == "# System Summary\n"


def test_render_system_status_markdown_uses_singular_count_phrases() -> None:
    snapshot = build_system_status_snapshot(WORKSPACE_ROOT)
    payload = snapshot.to_dict()
    payload["component_health"]["components"][0]["dependencies"] = ["core_reference.json"]
    payload["component_health"]["components"][0]["dependents"] = ["src/inf_work/__main__.py"]
    payload["schema_contract_integrity"]["orphaned_or_dangling_references"]["component_files"] = ["src/missing.py"]
    payload["schema_contract_integrity"]["orphaned_or_dangling_references"]["component_docs"] = ["ai_docs/missing.json"]
    payload["resolver_capabilities"]["registered_tiles"] = ["tile_alpha"]

    markdown = render_system_status_markdown(SystemStatusSnapshot(**payload))

    assert "1 dependency, 1 dependent" in markdown
    assert "- **Dangling References**: 1 file, 1 doc" in markdown
    assert "- **Registered Tiles**: 1 registered tile" in markdown


def test_render_operator_shortcut_pairs_uses_shared_shortcut_model() -> None:
    snapshot = build_system_status_snapshot(WORKSPACE_ROOT)

    rendered_line = _render_operator_shortcut_pairs(snapshot.operator_shortcuts)

    assert rendered_line.startswith("- **Operator Shortcut Pairs:**")
    assert "`make all-report-fix-status` ↔ `workspace: all-fix-status`" in rendered_line
    assert "`make resolver-report` ↔ `workspace: resolver-only`" in rendered_line
    assert "`make component-report` ↔ `workspace: component-governance`" in rendered_line
    assert "`make coverage-snapshot` ↔ `workspace: coverage-snapshot`" in rendered_line
    assert "`make refresh-artifacts` ↔ `workspace: refresh-artifacts`" in rendered_line


def test_count_with_label_handles_singular_and_plural_forms() -> None:
    assert _count_with_label(1, "catalogued technique") == "1 catalogued technique"
    assert _count_with_label(2, "catalogued technique") == "2 catalogued techniques"
    assert _count_with_label(2, "dependency", "dependencies") == "2 dependencies"
    assert _count_with_label(1, "documented component and artifact", "documented components and artifacts") == (
        "1 documented component and artifact"
    )
    assert _count_with_label(3, "documented component and artifact", "documented components and artifacts") == (
        "3 documented components and artifacts"
    )


def test_format_activity_label_appends_date_when_present() -> None:
    assert _format_activity_label("item_alpha", "2026-03-31T00:00:00Z") == "item_alpha (2026-03-31)"
    assert _format_activity_label("item_beta", None) == "item_beta"


def test_render_activity_context_uses_latest_summary() -> None:
    assert _render_activity_context("Promoted package and CLI support modules.") == (
        "Latest governance work focused on promoted package and cli support modules."
    )
    assert _render_activity_context(
        "Adding a generated `Where to look first` block to `SYSTEM_STATUS.md` so the human-facing status artifact points operators directly at the canonical governance surfaces."
    ) == (
        "Latest governance work focused on adding a generated `Where to look first` block to `SYSTEM_STATUS.md` so the human-facing status artifact points operators directly at the canonical governance surfaces."
    )
    assert _render_activity_context("none") == "No recent governance context recorded."


def test_render_recent_governance_lines_uses_shared_activity_model() -> None:
    snapshot = build_system_status_snapshot(WORKSPACE_ROOT)

    summary_lines = _render_recent_governance_lines(
        snapshot.recent_session_activity,
        include_outcomes=False,
        colon_inside_bold=True,
    )
    status_lines = _render_recent_governance_lines(
        snapshot.recent_session_activity,
        include_outcomes=True,
        colon_inside_bold=False,
    )

    assert summary_lines[0] == f"- **Session Count:** {snapshot.recent_session_activity['session_count']}"
    assert summary_lines[1].startswith("- **KB Highlights:** session `")
    assert summary_lines[2] == f"- **Why It Matters:** {_render_activity_context(snapshot.recent_session_activity['latest_summary'])}"
    assert summary_lines[3] == f"- **Latest Summary:** {snapshot.recent_session_activity['latest_summary']}"
    assert len(summary_lines) == 4
    assert status_lines[0] == f"- **Session Count**: {snapshot.recent_session_activity['session_count']}"
    assert status_lines[1].startswith("- **KB Highlights**: session `")
    assert status_lines[2] == f"- **Why It Matters**: {_render_activity_context(snapshot.recent_session_activity['latest_summary'])}"
    assert status_lines[3] == f"- **Latest Summary**: {snapshot.recent_session_activity['latest_summary']}"
    assert all(line.startswith("- **Outcome**: ") for line in status_lines[4:])


def test_render_where_to_look_first_lines_preserves_document_variants() -> None:
    summary_lines = _render_where_to_look_first_lines("summary")
    status_lines = _render_where_to_look_first_lines("status")

    assert summary_lines == [
        "- **Guide:** `README.md` summarizes commands, validation surfaces, and governed workflow entry points.",
        "- **Live Snapshot:** `SYSTEM_STATUS.md` shows the latest derived operational status for components, KB metrics, and operator shortcuts.",
        "- **Canonical Status JSON:** `ai_docs/system_status_snapshot.json` is the structured source of truth for derived status artifacts.",
        "- **Component Registry:** `ai_docs/component_index.json` tracks governed components, dependencies, coverage metadata, and companion docs.",
        "- **KB Rollup:** `knowledge_base/kb_index.json` aggregates KB counts, freshness, lookup indices, and automation metrics.",
    ]
    assert status_lines == [
        "- **Guide**: `README.md` summarizes commands, validation surfaces, and governed workflow entry points.",
        "- **Structured Snapshot**: `ai_docs/system_status_snapshot.json` is the canonical status source of truth.",
        "- **Summary View**: `SYSTEM_SUMMARY.md` provides the condensed human-facing overview of the governed workspace.",
        "- **Component Registry**: `ai_docs/component_index.json` tracks governed components, dependencies, coverage metadata, and companion docs.",
        "- **KB Rollup**: `knowledge_base/kb_index.json` aggregates KB counts, freshness, lookup indices, and automation metrics.",
    ]


def test_render_system_summary_markdown_uses_shared_shortcut_model() -> None:
    snapshot = build_system_status_snapshot(WORKSPACE_ROOT)
    component_index = json.loads((WORKSPACE_ROOT / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    kb_index = json.loads((WORKSPACE_ROOT / "knowledge_base" / "kb_index.json").read_text(encoding="utf-8"))
    latest_session = snapshot.recent_session_activity["latest_session"]
    latest_automation_pattern = snapshot.recent_session_activity["latest_automation_pattern"]
    latest_technique = snapshot.recent_session_activity["latest_technique"]
    latest_bug_fix = snapshot.recent_session_activity["latest_bug_fix"]
    expected_highlights = (
        f"- **KB Highlights:** session `{_format_activity_label(latest_session['session_id'], latest_session.get('created_timestamp'))}`; "
        f"automation `{_format_activity_label(latest_automation_pattern['pattern_name'], latest_automation_pattern.get('created_timestamp'))}`; "
        f"technique `{_format_activity_label(latest_technique['name'], latest_technique.get('created_timestamp'))}`; "
        f"bug fix `{_format_activity_label(latest_bug_fix['id'], latest_bug_fix.get('created_timestamp'))}`"
    )

    summary_markdown = render_system_summary_markdown(
        snapshot,
        component_index=component_index,
        kb_index=kb_index,
    )
    technique_total = kb_index["total_techniques"]

    assert "# System Summary" in summary_markdown
    assert "**Total Components:** 10" in summary_markdown
    assert "**Test Inventory:**" in summary_markdown
    assert "collected" in summary_markdown
    assert "## Recent Governance Highlights" in summary_markdown
    assert expected_highlights in summary_markdown
    assert f"- **Why It Matters:** {_render_activity_context(latest_session['summary'])}" in summary_markdown
    assert "- **Operator Shortcut Pairs:**" in summary_markdown
    assert "## Where to look first" in summary_markdown
    assert "`README.md`" in summary_markdown
    assert "`SYSTEM_STATUS.md`" in summary_markdown
    assert "`ai_docs/system_status_snapshot.json`" in summary_markdown
    assert "`ai_docs/component_index.json`" in summary_markdown
    assert "`knowledge_base/kb_index.json`" in summary_markdown
    assert "`make resolver-report` ↔ `workspace: resolver-only`" in summary_markdown
    assert "`make component-report` ↔ `workspace: component-governance`" in summary_markdown
    assert "`make status-check` ↔ `workspace: status-check`" in summary_markdown
    assert "`make summary-check` ↔ `workspace: summary-check`" in summary_markdown
    assert "`make coverage-snapshot` ↔ `workspace: coverage-snapshot`" in summary_markdown
    assert "`make refresh-artifacts` ↔ `workspace: refresh-artifacts`" in summary_markdown
    assert "10 documented components and artifacts" in summary_markdown
    assert f"{technique_total} catalogued techniques" in summary_markdown
    assert "6 status rules" in summary_markdown


def test_render_system_summary_footer_uses_live_counts() -> None:
    snapshot = build_system_status_snapshot(WORKSPACE_ROOT)
    kb_index = json.loads((WORKSPACE_ROOT / "knowledge_base" / "kb_index.json").read_text(encoding="utf-8"))

    footer = _render_system_summary_footer(snapshot, kb_index=kb_index)

    assert footer.startswith("The system now includes 10 documented components and artifacts")
    assert f"{kb_index['total_techniques']} catalogued techniques" in footer
    assert "1 recorded bug fix pattern" in footer
    assert f"{kb_index['total_automation_patterns']} automation patterns" in footer
    assert "6 status rules" in footer


def test_write_system_status_outputs_writes_json_and_markdown(tmp_path: Path) -> None:
    json_path = "build/test_system_status_snapshot.json"
    markdown_path = "build/test_SYSTEM_STATUS.md"

    snapshot = write_system_status_outputs(
        WORKSPACE_ROOT,
        canonical_json_path=json_path,
        derived_markdown_path=markdown_path,
    )

    written_json = json.loads((WORKSPACE_ROOT / json_path).read_text(encoding="utf-8"))
    written_markdown = (WORKSPACE_ROOT / markdown_path).read_text(encoding="utf-8")
    written_summary = (WORKSPACE_ROOT / "SYSTEM_SUMMARY.md").read_text(encoding="utf-8")

    assert written_json["workspace_root"] == str(WORKSPACE_ROOT)
    assert snapshot.to_dict()["derived_markdown_path"] == markdown_path
    assert "# System Status" in written_markdown
    assert "## Where to look first" in written_markdown
    assert "`README.md`" in written_markdown
    assert "`SYSTEM_SUMMARY.md`" in written_markdown
    assert "`ai_docs/system_status_snapshot.json`" in written_markdown
    assert "`ai_docs/component_index.json`" in written_markdown
    assert "`knowledge_base/kb_index.json`" in written_markdown
    assert "- **Operator Shortcut Pairs:**" in written_summary
    assert "## Where to look first" in written_summary
    assert "`make resolver-report` ↔ `workspace: resolver-only`" in written_summary
    assert "`make component-report` ↔ `workspace: component-governance`" in written_summary
    assert "`make coverage-snapshot` ↔ `workspace: coverage-snapshot`" in written_summary
    assert "`make refresh-artifacts` ↔ `workspace: refresh-artifacts`" in written_summary
    assert "# System Summary" in written_summary

    (WORKSPACE_ROOT / json_path).unlink()
    (WORKSPACE_ROOT / markdown_path).unlink()


def test_write_test_coverage_snapshot_syncs_component_index_metadata(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir(parents=True, exist_ok=True)
    component_index_payload = {
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
                "health_status": "healthy",
                "test_coverage_percentage": 12,
                "compliance_status": "I1_I2_I3_I4_compliant",
                "performance_metrics": {
                    "response_latency_target": "<1s",
                    "memory_profile": "bounded"
                },
                "complexity_score": 1,
                "documentation_path": "ai_docs/component_alpha.json",
                "related_techniques": [],
                "known_issues": [],
            },
            {
                "component_id": "artifact_alpha",
                "component_name": "Artifact Alpha",
                "component_type": "governance_artifact",
                "file_path": "SYSTEM_STATUS.md",
                "dependencies": [],
                "dependents": [],
                "creation_timestamp": "2026-03-31T00:00:00Z",
                "last_modified_timestamp": "2026-03-31T00:00:00Z",
                "health_status": "healthy",
                "test_coverage_percentage": 100,
                "compliance_status": "I1_I2_I3_I4_compliant",
                "performance_metrics": {
                    "response_latency_target": "<1s",
                    "memory_profile": "bounded"
                },
                "complexity_score": 1,
                "documentation_path": "ai_docs/artifact_alpha.json",
                "related_techniques": [],
                "known_issues": [],
            },
        ],
        "metadata": {
            "last_updated": "2026-03-31T00:00:00Z",
            "total_components": 2,
            "schema_version": "2.0.0",
        },
        "health_status": {
            "total_healthy": 2,
            "total_degraded": 0,
            "total_failing": 0,
        },
    }
    (workspace_root / "ai_docs" / "component_index.json").write_text(
        json.dumps(component_index_payload, indent=2),
        encoding="utf-8",
    )
    expected_snapshot = {
        "generated_at": "2026-04-01T00:00:00Z",
        "workspace_root": str(workspace_root),
        "coverage_command": "pytest --cov",
        "coverage_source": "ai_docs/test_coverage_snapshot.json",
        "module_coverage": [
            {
                "module_path": "src/component_alpha.py",
                "coverage_percentage": 87,
                "num_statements": 10,
                "covered_lines": 9,
                "missing_lines": 1,
            }
        ],
        "totals": {
            "coverage_percentage": 87,
            "num_statements": 10,
            "covered_lines": 9,
            "missing_lines": 1,
        },
        "metadata": {
            "total_modules": 1,
            "schema_version": "2.0.0",
        },
    }

    monkeypatch.setattr(system_status_module, "build_test_coverage_snapshot", lambda root_path, coverage_snapshot_path="ai_docs/test_coverage_snapshot.json": expected_snapshot)

    snapshot = system_status_module.write_test_coverage_snapshot(workspace_root)

    synced_component_index = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    assert snapshot == expected_snapshot
    assert synced_component_index["components"][0]["test_coverage_percentage"] == 87
    assert synced_component_index["components"][0]["last_modified_timestamp"] == expected_snapshot["generated_at"]
    assert synced_component_index["components"][1]["test_coverage_percentage"] == 100
    assert synced_component_index["metadata"]["last_updated"] == expected_snapshot["generated_at"]


def test_write_test_coverage_snapshot_normalizes_existing_component_index_timestamps(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path
    (workspace_root / "ai_docs").mkdir()
    component_index_payload = {
        "components": [
            {
                "component_id": "component_alpha",
                "component_name": "Component Alpha",
                "component_type": "python_module",
                "file_path": "src/component_alpha.py",
                "dependencies": [],
                "dependents": [],
                "last_modified_timestamp": "2026-03-31T00:00:00Z",
                "health_status": "healthy",
                "test_coverage_percentage": 87,
                "compliance_status": "I1_I2_I3_I4_compliant",
                "performance_metrics": {
                    "response_latency_target": "<1s",
                    "memory_profile": "bounded"
                },
                "complexity_score": 1,
                "documentation_path": "ai_docs/component_alpha.json",
                "related_techniques": [],
                "known_issues": [],
            }
        ],
        "metadata": {
            "last_updated": "2026-03-31T00:00:00Z",
            "total_components": 1,
            "schema_version": "2.0.0",
        },
        "health_status": {
            "total_healthy": 1,
            "total_degraded": 0,
            "total_failing": 0,
        },
    }
    (workspace_root / "ai_docs" / "component_index.json").write_text(
        json.dumps(component_index_payload, indent=2),
        encoding="utf-8",
    )
    expected_snapshot = {
        "generated_at": "2026-04-01T00:00:00.123456",
        "workspace_root": str(workspace_root),
        "coverage_command": "pytest --cov",
        "coverage_source": "ai_docs/test_coverage_snapshot.json",
        "module_coverage": [
            {
                "module_path": "src/component_alpha.py",
                "coverage_percentage": 87,
                "num_statements": 10,
                "covered_lines": 9,
                "missing_lines": 1,
            }
        ],
        "totals": {
            "coverage_percentage": 87,
            "num_statements": 10,
            "covered_lines": 9,
            "missing_lines": 1,
        },
        "metadata": {
            "total_modules": 1,
            "schema_version": "2.0.0",
        },
    }

    monkeypatch.setattr(
        system_status_module,
        "build_test_coverage_snapshot",
        lambda root_path, coverage_snapshot_path="ai_docs/test_coverage_snapshot.json": expected_snapshot,
    )

    snapshot = system_status_module.write_test_coverage_snapshot(workspace_root)

    synced_component_index = json.loads((workspace_root / "ai_docs" / "component_index.json").read_text(encoding="utf-8"))
    assert snapshot["generated_at"] == "2026-04-01T00:00:00.123456"
    assert synced_component_index["components"][0]["last_modified_timestamp"] == "2026-04-01T00:00:00Z"
    assert synced_component_index["metadata"]["last_updated"] == "2026-04-01T00:00:00Z"


def test_write_system_status_outputs_repairs_stale_component_index_coverage_from_snapshot() -> None:
    component_index_path = WORKSPACE_ROOT / "ai_docs" / "component_index.json"
    original_component_index = component_index_path.read_text(encoding="utf-8")
    try:
        payload = json.loads(original_component_index)
        cli_component = next(
            component for component in payload["components"] if component["component_id"] == "unified_cli_entry_point"
        )
        cli_component["test_coverage_percentage"] = 0
        component_index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        snapshot = write_system_status_outputs(WORKSPACE_ROOT)
        repaired_component_index = json.loads(component_index_path.read_text(encoding="utf-8"))
        repaired_cli_component = next(
            component for component in repaired_component_index["components"] if component["component_id"] == "unified_cli_entry_point"
        )
        expected_coverage = next(
            entry["coverage_percentage"]
            for entry in snapshot.test_suite_summary["coverage_by_module"]
            if entry["module_path"] == "src/inf_work/__main__.py"
        )

        assert repaired_cli_component["test_coverage_percentage"] == expected_coverage
    finally:
        component_index_path.write_text(original_component_index, encoding="utf-8")
        write_system_status_outputs(WORKSPACE_ROOT)


def test_validate_system_status_passes_for_current_workspace() -> None:
    write_system_status_outputs(WORKSPACE_ROOT)

    result = validate_system_status(WORKSPACE_ROOT)

    assert result.compliant is True
    assert result.summary_path == "SYSTEM_SUMMARY.md"
    assert all(rule_result.passed for rule_result in result.rule_results)


def test_validate_system_status_detects_stale_summary() -> None:
    write_system_status_outputs(WORKSPACE_ROOT)
    summary_path = WORKSPACE_ROOT / "SYSTEM_SUMMARY.md"
    original_summary = summary_path.read_text(encoding="utf-8")
    try:
        summary_path.write_text(original_summary.replace("System Health:** Healthy", "System Health:** Drifted"), encoding="utf-8")

        result = validate_system_status(WORKSPACE_ROOT)

        assert result.compliant is False
        assert any(issue.field_name == "summary_consistency" for issue in result.issues)
    finally:
        write_system_status_outputs(WORKSPACE_ROOT)


def test_validate_system_summary_passes_for_current_workspace() -> None:
    write_system_status_outputs(WORKSPACE_ROOT)

    result = validate_system_summary(WORKSPACE_ROOT)

    assert result.compliant is True
    assert result.summary_path == "SYSTEM_SUMMARY.md"
    assert len(result.rule_results) == 2
    assert all(rule_result.passed for rule_result in result.rule_results)


def test_validate_system_summary_detects_stale_summary() -> None:
    write_system_status_outputs(WORKSPACE_ROOT)
    summary_path = WORKSPACE_ROOT / "SYSTEM_SUMMARY.md"
    original_summary = summary_path.read_text(encoding="utf-8")
    try:
        summary_path.write_text(original_summary.replace("System Health:** Healthy", "System Health:** Drifted"), encoding="utf-8")

        result = validate_system_summary(WORKSPACE_ROOT)

        assert result.compliant is False
        assert any(issue.field_name == "summary_consistency" for issue in result.issues)
    finally:
        write_system_status_outputs(WORKSPACE_ROOT)


def test_validate_system_status_detects_stale_snapshot() -> None:
    json_path = "build/test_status_validation_snapshot.json"
    markdown_path = "build/test_status_validation.md"
    write_system_status_outputs(
        WORKSPACE_ROOT,
        canonical_json_path=json_path,
        derived_markdown_path=markdown_path,
    )

    snapshot_payload = json.loads((WORKSPACE_ROOT / json_path).read_text(encoding="utf-8"))
    snapshot_payload["knowledge_base_metrics"]["innovation_count"] = 999
    (WORKSPACE_ROOT / json_path).write_text(json.dumps(snapshot_payload, indent=2), encoding="utf-8")

    result = validate_system_status(
        WORKSPACE_ROOT,
        canonical_json_path=json_path,
        derived_markdown_path=markdown_path,
    )

    assert result.compliant is False
    assert any(issue.field_name == "snapshot_consistency" for issue in result.issues)

    (WORKSPACE_ROOT / json_path).unlink()
    (WORKSPACE_ROOT / markdown_path).unlink()


def test_repair_and_validate_system_status_fixes_stale_artifacts() -> None:
    json_path = "build/test_repair_status_snapshot.json"
    markdown_path = "build/test_repair_status.md"
    write_system_status_outputs(
        WORKSPACE_ROOT,
        canonical_json_path=json_path,
        derived_markdown_path=markdown_path,
    )

    snapshot_payload = json.loads((WORKSPACE_ROOT / json_path).read_text(encoding="utf-8"))
    snapshot_payload["knowledge_base_metrics"]["innovation_count"] = 999
    (WORKSPACE_ROOT / json_path).write_text(json.dumps(snapshot_payload, indent=2), encoding="utf-8")

    result = repair_and_validate_system_status(
        WORKSPACE_ROOT,
        canonical_json_path=json_path,
        derived_markdown_path=markdown_path,
    )

    assert result.compliant is True
    assert all(rule_result.passed for rule_result in result.rule_results)

    (WORKSPACE_ROOT / json_path).unlink()
    (WORKSPACE_ROOT / markdown_path).unlink()


def test_repair_and_validate_system_summary_fixes_stale_summary() -> None:
    write_system_status_outputs(WORKSPACE_ROOT)
    summary_path = WORKSPACE_ROOT / "SYSTEM_SUMMARY.md"
    original_summary = summary_path.read_text(encoding="utf-8")
    try:
        summary_path.write_text(original_summary.replace("System Health:** Healthy", "System Health:** Drifted"), encoding="utf-8")

        result = repair_and_validate_system_summary(WORKSPACE_ROOT)

        assert result.compliant is True
        assert all(rule_result.passed for rule_result in result.rule_results)
    finally:
        write_system_status_outputs(WORKSPACE_ROOT)


def test_run_status_rules_can_select_specific_rule() -> None:
    write_system_status_outputs(WORKSPACE_ROOT)

    rule_results = run_status_rules(WORKSPACE_ROOT, {"status.artifacts_exist"})

    assert len(rule_results) == 1
    assert rule_results[0].rule_id == "status.artifacts_exist"
    assert rule_results[0].passed is True


def test_run_summary_rules_returns_summary_specific_rules() -> None:
    write_system_status_outputs(WORKSPACE_ROOT)

    rule_results = run_summary_rules(WORKSPACE_ROOT)

    assert [rule_result.rule_id for rule_result in rule_results] == [
        "summary.artifact_exists",
        "summary.matches_workspace",
    ]
    assert all(rule_result.passed for rule_result in rule_results)


def test_status_check_cli_succeeds_for_current_workspace() -> None:
    environment = {
        **os.environ,
        "PYTHONPATH": str(WORKSPACE_ROOT / "src"),
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "inf_work",
            "status-check",
            str(WORKSPACE_ROOT),
            "--pretty",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=WORKSPACE_ROOT,
        env=environment,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["compliant"] is True
    assert payload["rule_summary"]["total_rules"] == 6


def test_run_status_rules_returns_resolver_integrity_rules() -> None:
    write_system_status_outputs(WORKSPACE_ROOT)

    rule_results = run_status_rules(WORKSPACE_ROOT)

    assert "status.resolver_explicit_route_integrity" in [rule_result.rule_id for rule_result in rule_results]
    assert "status.resolver_inferred_route_integrity" in [rule_result.rule_id for rule_result in rule_results]
    assert all(rule_result.passed for rule_result in rule_results)


def test_run_status_rules_flags_explicit_route_drift(monkeypatch) -> None:
    write_system_status_outputs(WORKSPACE_ROOT)

    monkeypatch.setattr(
        system_status_module,
        "resolve_explicit_path",
        lambda workspace_root, tile_path: SimpleNamespace(
            complete=False,
            failure_reason="route_not_found",
            requested_path=list(tile_path),
            resolved_steps=[{"tile_id": tile_path[0]}],
            total_hops=0,
            to_dict=lambda: {
                "workspace_root": str(workspace_root),
                "traversal_mode": "explicit",
                "requested_path": list(tile_path),
                "resolved_steps": [{"tile_id": tile_path[0]}],
                "total_hops": 0,
                "complete": False,
                "failure_reason": "route_not_found",
            },
        ),
    )

    rule_results = run_status_rules(WORKSPACE_ROOT, {"status.resolver_explicit_route_integrity"})

    assert len(rule_results) == 1
    assert rule_results[0].passed is False
    assert rule_results[0].findings[0].field_name == "resolver_explicit_route_integrity"


def test_run_status_rules_flags_inferred_route_drift(monkeypatch) -> None:
    write_system_status_outputs(WORKSPACE_ROOT)

    monkeypatch.setattr(
        system_status_module,
        "infer_route",
        lambda workspace_root, start_tile_id, target_tile_id: SimpleNamespace(
            complete=False,
            failure_reason="route_not_found",
            requested_path=[start_tile_id, target_tile_id],
            resolved_steps=[{"tile_id": start_tile_id}],
            total_hops=0,
            to_dict=lambda: {
                "workspace_root": str(workspace_root),
                "traversal_mode": "inferred",
                "requested_path": [start_tile_id, target_tile_id],
                "resolved_steps": [{"tile_id": start_tile_id}],
                "total_hops": 0,
                "complete": False,
                "failure_reason": "route_not_found",
            },
        ),
    )

    rule_results = run_status_rules(WORKSPACE_ROOT, {"status.resolver_inferred_route_integrity"})

    assert len(rule_results) == 1
    assert rule_results[0].passed is False
    assert rule_results[0].findings[0].field_name == "resolver_inferred_route_integrity"


def test_status_check_cli_can_fix_stale_artifacts() -> None:
    json_path = WORKSPACE_ROOT / "build" / "test_cli_fix_status_snapshot.json"
    markdown_path = WORKSPACE_ROOT / "build" / "test_cli_fix_status.md"
    write_system_status_outputs(
        WORKSPACE_ROOT,
        canonical_json_path=str(json_path.relative_to(WORKSPACE_ROOT)),
        derived_markdown_path=str(markdown_path.relative_to(WORKSPACE_ROOT)),
    )
    snapshot_payload = json.loads(json_path.read_text(encoding="utf-8"))
    snapshot_payload["knowledge_base_metrics"]["innovation_count"] = 999
    json_path.write_text(json.dumps(snapshot_payload, indent=2), encoding="utf-8")

    environment = {
        **os.environ,
        "PYTHONPATH": str(WORKSPACE_ROOT / "src"),
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "inf_work",
            "status-check",
            str(WORKSPACE_ROOT),
            "--pretty",
            "--fix",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=WORKSPACE_ROOT,
        env=environment,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["compliant"] is True

    json_path.unlink()
    markdown_path.unlink()


def test_summary_check_cli_succeeds_for_current_workspace() -> None:
    environment = {
        **os.environ,
        "PYTHONPATH": str(WORKSPACE_ROOT / "src"),
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "inf_work",
            "summary-check",
            str(WORKSPACE_ROOT),
            "--pretty",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=WORKSPACE_ROOT,
        env=environment,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["compliant"] is True
    assert payload["rule_summary"]["total_rules"] == 2


def test_summary_check_cli_can_fix_stale_summary() -> None:
    write_system_status_outputs(WORKSPACE_ROOT)
    summary_path = WORKSPACE_ROOT / "SYSTEM_SUMMARY.md"
    original_summary = summary_path.read_text(encoding="utf-8")
    summary_path.write_text(original_summary.replace("System Health:** Healthy", "System Health:** Drifted"), encoding="utf-8")

    environment = {
        **os.environ,
        "PYTHONPATH": str(WORKSPACE_ROOT / "src"),
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "inf_work",
            "summary-check",
            str(WORKSPACE_ROOT),
            "--pretty",
            "--fix",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=WORKSPACE_ROOT,
        env=environment,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["compliant"] is True
    assert payload["rule_summary"]["total_rules"] == 2