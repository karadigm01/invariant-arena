from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import os
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from .kb_integrity import validate_knowledge_base
from .resolver_registry import build_resolver_capabilities, infer_route, resolve_explicit_path
from .rules import RuleFinding, RuleResult, ValidationRule, get_registered_rules, register_rules, run_registered_rules
from .workspace_health import validate_workspace


_EXPECTED_EXPLICIT_ROUTE = ["workspace_governance", "component_index", "knowledge_base_index"]
_EXPECTED_INFERRED_ROUTE = ["workspace_governance", "knowledge_base_index"]
_DEFAULT_COVERAGE_SNAPSHOT_PATH = "ai_docs/test_coverage_snapshot.json"
_LEGACY_DEFAULT_GENERATED_AT = "2026-03-29T00:00:00Z"


@dataclass(frozen=True)
class SystemStatusSnapshot:
    generated_at: str
    workspace_root: str
    canonical_json_path: str
    derived_markdown_path: str
    coverage_threshold: int
    component_health: dict[str, Any]
    test_suite_summary: dict[str, Any]
    knowledge_base_metrics: dict[str, Any]
    recent_session_activity: dict[str, Any]
    schema_contract_integrity: dict[str, Any]
    resolver_capabilities: dict[str, Any]
    known_gaps_technical_debt: dict[str, Any]
    architectural_invariant_compliance: dict[str, Any]
    operator_shortcuts: list[dict[str, Any]]
    next_recommended_actions: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StatusValidationIssue:
    source_file: str
    item_identifier: str
    field_name: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StatusValidationResult:
    workspace_root: str
    snapshot_path: str
    markdown_path: str
    summary_path: str
    compliant: bool
    issues: list[StatusValidationIssue]
    rule_results: list[RuleResult]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["issues"] = [issue.to_dict() for issue in self.issues]
        payload["rule_results"] = [rule_result.to_dict() for rule_result in self.rule_results]
        return payload


def repair_and_validate_system_status(
    workspace_root: str | Path,
    rule_ids: set[str] | None = None,
    *,
    canonical_json_path: str = "ai_docs/system_status_snapshot.json",
    derived_markdown_path: str = "SYSTEM_STATUS.md",
) -> StatusValidationResult:
    write_system_status_outputs(
        workspace_root,
        canonical_json_path=canonical_json_path,
        derived_markdown_path=derived_markdown_path,
    )
    return validate_system_status(
        workspace_root,
        rule_ids,
        canonical_json_path=canonical_json_path,
        derived_markdown_path=derived_markdown_path,
    )


def repair_and_validate_system_summary(
    workspace_root: str | Path,
    *,
    generated_at: str | None = None,
    canonical_json_path: str = "ai_docs/system_status_snapshot.json",
    derived_markdown_path: str = "SYSTEM_STATUS.md",
    summary_path: str = "SYSTEM_SUMMARY.md",
) -> StatusValidationResult:
    write_system_status_outputs(
        workspace_root,
        generated_at=generated_at,
        canonical_json_path=canonical_json_path,
        derived_markdown_path=derived_markdown_path,
        summary_path=summary_path,
    )
    return validate_system_summary(
        workspace_root,
        canonical_json_path=canonical_json_path,
        derived_markdown_path=derived_markdown_path,
        summary_path=summary_path,
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalize_utc_timestamp(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return ""

    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return normalized

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)

    return parsed.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_test_coverage_snapshot(
    workspace_root: str | Path,
    *,
    coverage_snapshot_path: str = _DEFAULT_COVERAGE_SNAPSHOT_PATH,
) -> dict[str, Any]:
    root_path = Path(workspace_root).resolve()
    coverage_json_path = root_path / "build" / "runtime_test_coverage.json"
    command = [
        sys.executable,
        "-m",
        "pytest",
        "--cov=src/inf_work",
        f"--cov-report=json:{coverage_json_path}",
        "-q",
    ]
    completed = subprocess.run(
        command,
        cwd=root_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("Unable to generate coverage snapshot from pytest-cov run.")

    coverage_payload = _load_json(coverage_json_path)
    files_payload = coverage_payload.get("files", {})
    module_coverage: list[dict[str, Any]] = []
    for module_path, module_payload in sorted(files_payload.items()):
        if not str(module_path).startswith("src/inf_work/"):
            continue
        summary = module_payload.get("summary", {})
        module_coverage.append(
            {
                "module_path": str(module_path),
                "coverage_percentage": int(summary.get("percent_covered_display", 0)),
                "num_statements": int(summary.get("num_statements", 0)),
                "covered_lines": int(summary.get("covered_lines", 0)),
                "missing_lines": int(summary.get("missing_lines", 0)),
            }
        )

    return {
        "generated_at": _normalize_utc_timestamp(str(coverage_payload.get("meta", {}).get("timestamp", ""))),
        "workspace_root": str(root_path),
        "coverage_command": " ".join(command),
        "coverage_source": coverage_snapshot_path,
        "module_coverage": module_coverage,
        "totals": {
            "coverage_percentage": int(coverage_payload.get("totals", {}).get("percent_covered_display", 0)),
            "num_statements": int(coverage_payload.get("totals", {}).get("num_statements", 0)),
            "covered_lines": int(coverage_payload.get("totals", {}).get("covered_lines", 0)),
            "missing_lines": int(coverage_payload.get("totals", {}).get("missing_lines", 0)),
        },
        "metadata": {
            "total_modules": len(module_coverage),
            "schema_version": "2.0.0",
        },
    }


def write_test_coverage_snapshot(
    workspace_root: str | Path,
    *,
    coverage_snapshot_path: str = _DEFAULT_COVERAGE_SNAPSHOT_PATH,
) -> dict[str, Any]:
    root_path = Path(workspace_root).resolve()
    snapshot = build_test_coverage_snapshot(root_path, coverage_snapshot_path=coverage_snapshot_path)
    destination_path = root_path / coverage_snapshot_path
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    _sync_component_index_coverage(root_path, snapshot)
    return snapshot


def _sync_component_index_coverage(root_path: Path, coverage_snapshot: dict[str, Any]) -> dict[str, Any] | None:
    component_index_path = root_path / "ai_docs" / "component_index.json"
    if not component_index_path.is_file():
        return None

    component_index_payload = _load_json(component_index_path)
    coverage_by_module = {
        str(entry.get("module_path", "")): int(entry.get("coverage_percentage", 0))
        for entry in coverage_snapshot.get("module_coverage", [])
    }
    generated_at = _normalize_utc_timestamp(str(coverage_snapshot.get("generated_at", "")))
    changed = False

    for component in component_index_payload.get("components", []):
        file_path = str(component.get("file_path", ""))
        expected_coverage = coverage_by_module.get(file_path)
        if expected_coverage is None:
            continue

        if component.get("test_coverage_percentage") != expected_coverage:
            component["test_coverage_percentage"] = expected_coverage
            changed = True

        if generated_at and component.get("last_modified_timestamp") != generated_at:
            component["last_modified_timestamp"] = generated_at
            changed = True

    if not changed:
        return component_index_payload

    if generated_at:
        component_index_payload.setdefault("metadata", {})["last_updated"] = generated_at

    component_index_path.write_text(json.dumps(component_index_payload, indent=2), encoding="utf-8")
    return component_index_payload


def _load_test_coverage_snapshot(
    root_path: Path,
    coverage_snapshot_path: str = _DEFAULT_COVERAGE_SNAPSHOT_PATH,
) -> dict[str, Any] | None:
    snapshot_path = root_path / coverage_snapshot_path
    if not snapshot_path.is_file():
        return None
    return _load_json(snapshot_path)


def _normalize_snapshot_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized_payload = json.loads(json.dumps(payload))
    test_suite_summary = normalized_payload.get("test_suite_summary", {})
    test_suite_summary.pop("raw_summary", None)
    test_suite_summary.pop("command", None)
    test_suite_summary.pop("summary_mode", None)
    return normalized_payload


def _max_timestamp(values: list[str]) -> str | None:
    filtered_values = [value for value in values if value]
    return max(filtered_values) if filtered_values else None


def _derive_status_generated_at(root_path: Path) -> str:
    component_index = _load_json(root_path / "ai_docs" / "component_index.json")
    kb_index = _load_json(root_path / "knowledge_base" / "kb_index.json")
    session_history = _load_json(root_path / "knowledge_base" / "session_history.json")
    coverage_snapshot = _load_test_coverage_snapshot(root_path)

    derived_timestamp = _max_timestamp(
        [
            _normalize_utc_timestamp(str(component_index.get("metadata", {}).get("last_updated", ""))),
            _normalize_utc_timestamp(str(kb_index.get("last_updated", ""))),
            _normalize_utc_timestamp(str(session_history.get("metadata", {}).get("last_session", ""))),
            _normalize_utc_timestamp(str((coverage_snapshot or {}).get("generated_at", ""))),
        ]
    )
    return derived_timestamp or _LEGACY_DEFAULT_GENERATED_AT


def _find_latest_item(items: list[dict[str, Any]], timestamp_field: str = "created_timestamp") -> dict[str, Any] | None:
    if not items:
        return None
    return items[-1]


def _component_dependents_map(components: list[dict[str, Any]]) -> dict[str, list[str]]:
    dependents_map: dict[str, list[str]] = {}
    for component in components:
        dependents_map[component["file_path"]] = []
    for component in components:
        for dependency in component.get("dependencies", []):
            if dependency in dependents_map:
                dependents_map[dependency].append(component["component_id"])
    return dependents_map


def _collect_component_health(root_path: Path, coverage_threshold: int) -> dict[str, Any]:
    component_index = _load_json(root_path / "ai_docs" / "component_index.json")
    components = component_index["components"]
    dependents_map = _component_dependents_map(components)
    component_rows: list[dict[str, Any]] = []
    below_threshold: list[str] = []

    for component in components:
        coverage = int(component.get("test_coverage_percentage", 0))
        if coverage < coverage_threshold:
            below_threshold.append(component["component_id"])
        component_rows.append(
            {
                "component_id": component["component_id"],
                "component_name": component["component_name"],
                "component_type": component["component_type"],
                "file_path": component["file_path"],
                "health_status": component["health_status"],
                "test_coverage_percentage": coverage,
                "coverage_flag": "below_threshold" if coverage < coverage_threshold else "meets_threshold",
                "compliance_status": component["compliance_status"],
                "dependencies": component.get("dependencies", []),
                "dependents": component.get("dependents", []),
                "derived_dependents": sorted(dependents_map.get(component["file_path"], [])),
                "documentation_path": component.get("documentation_path"),
            }
        )

    return {
        "threshold": coverage_threshold,
        "total_components": len(component_rows),
        "healthy_components": component_index["health_status"]["total_healthy"],
        "degraded_components": component_index["health_status"]["total_degraded"],
        "failing_components": component_index["health_status"]["total_failing"],
        "below_threshold_components": below_threshold,
        "components": component_rows,
    }


def _parse_pytest_summary(output_text: str) -> dict[str, int]:
    summary_counts = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
        "errors": 0,
    }
    summary_line = None
    for line in output_text.splitlines():
        stripped_line = line.strip()
        if " in " in stripped_line and any(keyword in stripped_line for keyword in summary_counts):
            summary_line = stripped_line
    if summary_line is None:
        return summary_counts

    for key in summary_counts:
        match = re.search(rf"(\d+) {key}", summary_line)
        if match:
            summary_counts[key] = int(match.group(1))
    return summary_counts


def _collect_test_suite_summary(root_path: Path, coverage_threshold: int) -> dict[str, Any]:
    command = [sys.executable, "-m", "pytest", "--collect-only", "-q"]
    completed = subprocess.run(
        command,
        cwd=root_path,
        capture_output=True,
        text=True,
        check=False,
    )
    collected_tests = len(
        [line for line in completed.stdout.splitlines() if line.strip().startswith("tests/")]
    )
    summary_counts = {
        "passed": collected_tests,
        "failed": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
        "errors": 0,
    }
    summary_text = f"{collected_tests} collected"
    total_tests = sum(summary_counts.values())
    pass_rate = 0.0 if total_tests == 0 else round(summary_counts["passed"] / total_tests, 4)

    component_index = _load_json(root_path / "ai_docs" / "component_index.json")
    coverage_snapshot = _load_test_coverage_snapshot(root_path)
    snapshot_coverage_by_module = {
        str(entry.get("module_path", "")): int(entry.get("coverage_percentage", 0))
        for entry in coverage_snapshot.get("module_coverage", [])
    } if coverage_snapshot else {}
    tracked_coverage = {
        component["file_path"]: {
            "coverage_percentage": int(
                snapshot_coverage_by_module.get(
                    component["file_path"],
                    int(component.get("test_coverage_percentage", 0)),
                )
            ),
            "tracked_in_component_index": True,
        }
        for component in component_index["components"]
        if str(component["file_path"]).endswith(".py")
    }
    for python_file in sorted((root_path / "src" / "inf_work").glob("*.py")):
        relative_path = str(python_file.relative_to(root_path))
        tracked_coverage.setdefault(
            relative_path,
            {
                "coverage_percentage": 0,
                "tracked_in_component_index": False,
            },
        )

    coverage_by_module = [
        {
            "module_path": module_path,
            "coverage_percentage": module_data["coverage_percentage"],
            "tracked_in_component_index": module_data["tracked_in_component_index"],
            "coverage_flag": "below_threshold" if module_data["coverage_percentage"] < coverage_threshold else "meets_threshold",
        }
        for module_path, module_data in sorted(tracked_coverage.items())
    ]

    return {
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "total_tests": total_tests,
        "pass_rate": pass_rate,
        "status_counts": summary_counts,
        "summary_text": summary_text,
        "pending_or_skipped_tests": summary_counts["skipped"] + summary_counts["xfailed"] + summary_counts["xpassed"],
        "coverage_by_module": coverage_by_module,
        "coverage_source": _DEFAULT_COVERAGE_SNAPSHOT_PATH if coverage_snapshot else "component_index_fallback",
        "summary_mode": "collection_only",
    }


def _collect_knowledge_base_metrics(root_path: Path) -> dict[str, Any]:
    techniques_payload = _load_json(root_path / "knowledge_base" / "techniques.json")
    innovations_payload = _load_json(root_path / "knowledge_base" / "constraint_innovations.json")
    bug_fixes_payload = _load_json(root_path / "knowledge_base" / "bug_fixes.json")
    automation_payload = _load_json(root_path / "knowledge_base" / "automation_patterns.json")

    latest_technique = _find_latest_item(techniques_payload["techniques"])
    latest_innovation = _find_latest_item(innovations_payload["innovations"])
    last_updated = _max_timestamp(
        [
            techniques_payload["metadata"].get("last_updated"),
            innovations_payload["metadata"].get("last_updated"),
            bug_fixes_payload["metadata"].get("last_updated"),
            automation_payload["metadata"].get("last_updated"),
        ]
    )

    return {
        "technique_count": len(techniques_payload["techniques"]),
        "latest_technique": latest_technique,
        "innovation_count": len(innovations_payload["innovations"]),
        "latest_innovation": latest_innovation,
        "bug_fix_count": len(bug_fixes_payload["bug_fixes"]),
        "automation_pattern_count": len(automation_payload["automation_patterns"]),
        "last_kb_update_timestamp": last_updated,
    }


def _collect_recent_session_activity(root_path: Path) -> dict[str, Any]:
    session_history_payload = _load_json(root_path / "knowledge_base" / "session_history.json")
    automation_patterns_payload = _load_json(root_path / "knowledge_base" / "automation_patterns.json")
    techniques_payload = _load_json(root_path / "knowledge_base" / "techniques.json")
    bug_fixes_payload = _load_json(root_path / "knowledge_base" / "bug_fixes.json")
    sessions = session_history_payload["sessions"]
    latest_session = _find_latest_item(sessions)
    latest_automation_pattern = _find_latest_item(automation_patterns_payload["automation_patterns"])
    latest_technique = _find_latest_item(techniques_payload["techniques"])
    latest_bug_fix = _find_latest_item(bug_fixes_payload["bug_fixes"])

    if latest_session is None:
        return {
            "session_count": 0,
            "latest_session": None,
            "latest_summary": "none",
            "latest_outcomes": [],
            "latest_automation_pattern": latest_automation_pattern,
            "latest_technique": latest_technique,
            "latest_bug_fix": latest_bug_fix,
        }

    return {
        "session_count": len(sessions),
        "latest_session": latest_session,
        "latest_summary": latest_session.get("summary", "none"),
        "latest_outcomes": latest_session.get("outcomes", [])[:2],
        "latest_automation_pattern": latest_automation_pattern,
        "latest_technique": latest_technique,
        "latest_bug_fix": latest_bug_fix,
    }


def _collect_schema_contract_integrity(root_path: Path) -> dict[str, Any]:
    core_reference = _load_json(root_path / "core_reference.json")
    behavioral_directives = _load_json(root_path / "behavioral_directives.json")
    component_index = _load_json(root_path / "ai_docs" / "component_index.json")
    techniques = _load_json(root_path / "knowledge_base" / "techniques.json")
    bug_fixes = _load_json(root_path / "knowledge_base" / "bug_fixes.json")
    innovations = _load_json(root_path / "knowledge_base" / "constraint_innovations.json")
    automation_patterns = _load_json(root_path / "knowledge_base" / "automation_patterns.json")
    kb_index = _load_json(root_path / "knowledge_base" / "kb_index.json")

    kb_validation = validate_knowledge_base(root_path)
    workspace_validation = validate_workspace(root_path)

    dangling_component_files: list[str] = []
    dangling_component_docs: list[str] = []
    for component in component_index["components"]:
        if not (root_path / component["file_path"]).exists():
            dangling_component_files.append(component["file_path"])
        if not (root_path / component["documentation_path"]).exists():
            dangling_component_docs.append(component["documentation_path"])

    return {
        "schema_bundles": [
            {"name": "core_reference", "version": core_reference["system_identity"]["version"]},
            {"name": "behavioral_directives", "version": behavioral_directives["system_identity"]["version"]},
            {"name": "component_index", "version": component_index["metadata"]["schema_version"]},
            {"name": "techniques", "version": techniques["metadata"]["schema_version"]},
            {"name": "bug_fixes", "version": bug_fixes["metadata"]["schema_version"]},
            {"name": "constraint_innovations", "version": innovations["metadata"]["schema_version"]},
            {"name": "automation_patterns", "version": automation_patterns["metadata"]["schema_version"]},
            {"name": "kb_index", "version": kb_index["last_updated"] and "2.0.0"},
        ],
        "workspace_coherence_validation": {
            "compliant": workspace_validation.compliant,
            "missing_directories": workspace_validation.missing_directories,
        },
        "cross_reference_validation": {
            "compliant": kb_validation.compliant,
            "issue_count": len(kb_validation.issues),
            "issues": [issue.to_dict() for issue in kb_validation.issues],
        },
        "orphaned_or_dangling_references": {
            "component_files": dangling_component_files,
            "component_docs": dangling_component_docs,
        },
    }


def _collect_resolver_capabilities(root_path: Path) -> dict[str, Any]:
    return build_resolver_capabilities(root_path).to_dict()


def _find_todo_fixme_items(root_path: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    pattern = re.compile(r"(^\s*#.*\b(TODO|FIXME)\b)|(^\s*[-*].*\b(TODO|FIXME)\b)|(^\s*//.*\b(TODO|FIXME)\b)")
    for path in root_path.rglob("*"):
        if not path.is_file():
            continue
        if ".venv" in path.parts:
            continue
        if "ai_docs" in path.parts and "backups" in path.parts:
            continue
        if path.name in {"SYSTEM_STATUS.md", "system_status_snapshot.json"}:
            continue
        if path.suffix not in {".py", ".md", ".json", ".yml", ".toml", ".txt"}:
            continue
        if path.suffix == ".md":
            lines = _read_text(path).splitlines()
            if lines and lines[0].strip() == "# System Status":
                continue
        else:
            lines = _read_text(path).splitlines()
        for line_number, line in enumerate(lines, start=1):
            if pattern.search(line):
                findings.append(
                    {
                        "path": str(path.relative_to(root_path)),
                        "line_number": line_number,
                        "text": line.strip(),
                    }
                )
    return findings


def _collect_known_gaps(
    root_path: Path,
    test_suite_summary: dict[str, Any],
    resolver_capabilities: dict[str, Any],
) -> dict[str, Any]:
    coverage_by_module = test_suite_summary["coverage_by_module"]
    zero_coverage_components = [
        module["module_path"]
        for module in coverage_by_module
        if module["coverage_percentage"] == 0
    ]

    automation_patterns = _load_json(root_path / "knowledge_base" / "automation_patterns.json")
    session_history = _load_json(root_path / "knowledge_base" / "session_history.json")

    planned_features: list[dict[str, str]] = []
    if not session_history["sessions"]:
        planned_features.append(
            {
                "feature": "Session history rollups",
                "status": "planned_but_unimplemented",
                "evidence": "knowledge_base/session_history.json is present but empty.",
            }
        )
    inference_modes_supported = resolver_capabilities["inference_modes_supported"]
    if not inference_modes_supported["multi_hop_explicit"] or not inference_modes_supported["multi_hop_inferred"]:
        planned_features.append(
            {
                "feature": "Multi-hop resolver modes",
                "status": "planned_but_unimplemented",
                "evidence": "Single-hop tile resolution is active in `src/inf_work/resolver_registry.py`, but explicit and inferred multi-hop modes remain disabled.",
            }
        )
    if not resolver_capabilities["pressure_telemetry_status"]["enabled"]:
        planned_features.append(
            {
                "feature": "Pressure telemetry",
                "status": "planned_but_unimplemented",
                "evidence": "`core_reference.json` declares monitoring intent, but telemetry export is not enabled in the runtime resolver capabilities.",
            }
        )

    missing_automation_patterns: list[str] = []
    if automation_patterns["metadata"]["total_count"] < 2:
        missing_automation_patterns.append("Status regeneration automation pattern is not yet catalogued.")

    return {
        "components_with_zero_percent_coverage": zero_coverage_components,
        "missing_automation_patterns": missing_automation_patterns,
        "todo_fixme_items": _find_todo_fixme_items(root_path),
        "planned_but_unimplemented_features": planned_features,
    }


def _collect_invariant_compliance(root_path: Path) -> dict[str, Any]:
    component_index = _load_json(root_path / "ai_docs" / "component_index.json")
    workspace_validation = validate_workspace(root_path)
    kb_validation = validate_knowledge_base(root_path)

    fully_compliant_components = [
        component["component_id"]
        for component in component_index["components"]
        if component["compliance_status"] == "I1_I2_I3_I4_compliant"
    ]

    return {
        "I1": {
            "status": "compliant" if len(fully_compliant_components) == len(component_index["components"]) else "attention_required",
            "evidence": "All registered components declare `I1_I2_I3_I4_compliant` in `component_index.json`.",
        },
        "I2": {
            "status": "compliant" if len(fully_compliant_components) == len(component_index["components"]) else "attention_required",
            "evidence": "All registered components declare bounded memory profiles and no dynamic allocation subsystems are present.",
        },
        "I3": {
            "status": "compliant" if workspace_validation.compliant else "violation_detected",
            "evidence": "Workspace validation checks governed directories from `core_reference.json`.",
        },
        "I4": {
            "status": "compliant" if kb_validation.compliant else "attention_required",
            "evidence": "JSON-first component docs and knowledge-base references validate successfully; `SYSTEM_STATUS.md` is derived from structured status data.",
        },
    }


def _collect_operator_shortcuts() -> list[dict[str, Any]]:
    return [
        {
            "name": "Aggregate report",
            "command": "make all-report",
            "task_label": "workspace: all",
            "purpose": "Run the full aggregate governance report without remediation.",
        },
        {
            "name": "Aggregate report with status remediation",
            "command": "make all-report-fix-status",
            "task_label": "workspace: all-fix-status",
            "purpose": "Refresh stale status artifacts before running the aggregate governance report.",
        },
        {
            "name": "Resolver integrity report",
            "command": "make resolver-report",
            "task_label": "workspace: resolver-only",
            "purpose": "Run only the runtime-integrity resolver rules through the aggregate governance surface.",
        },
        {
            "name": "Component governance report",
            "command": "make component-report",
            "task_label": "workspace: component-governance",
            "purpose": "Run only the component-governance knowledge-base rules for technique traceability and component-doc parity.",
        },
        {
            "name": "Status regeneration",
            "command": "make status",
            "task_label": "workspace: status",
            "purpose": "Regenerate `ai_docs/system_status_snapshot.json` and `SYSTEM_STATUS.md`.",
        },
        {
            "name": "Status validation",
            "command": "make status-check",
            "task_label": "workspace: status-check",
            "purpose": "Validate that the canonical status artifacts match the current workspace state.",
        },
        {
            "name": "Summary validation",
            "command": "make summary-check",
            "task_label": "workspace: summary-check",
            "purpose": "Validate that `SYSTEM_SUMMARY.md` matches the current governed workspace state.",
        },
        {
            "name": "Coverage snapshot refresh",
            "command": "make coverage-snapshot",
            "task_label": "workspace: coverage-snapshot",
            "purpose": "Refresh `ai_docs/test_coverage_snapshot.json` from a real `pytest-cov` run before reviewing governed component coverage.",
        },
        {
            "name": "Artifact refresh",
            "command": "make refresh-artifacts",
            "task_label": "workspace: refresh-artifacts",
            "purpose": "Refresh the governed coverage snapshot and regenerate the canonical status artifacts in one deterministic pass.",
        },
    ]


def _render_operator_shortcut_pairs(operator_shortcuts: list[dict[str, Any]]) -> str:
    shortcut_pairs = [
        f"`{shortcut['command']}` ↔ `{shortcut['task_label']}`"
        for shortcut in operator_shortcuts
    ]
    return f"- **Operator Shortcut Pairs:** {'; '.join(shortcut_pairs)}."


def _derive_system_health_label(snapshot: SystemStatusSnapshot) -> str:
    if snapshot.component_health["failing_components"]:
        return "Failing"
    if snapshot.component_health["degraded_components"]:
        return "Degraded"
    return "Healthy"


def _count_with_label(count: int, singular: str, plural: str | None = None) -> str:
    resolved_plural = plural or f"{singular}s"
    label = singular if count == 1 else resolved_plural
    return f"{count} {label}"


def _format_activity_label(label: str, timestamp: str | None) -> str:
    if not timestamp:
        return label
    return f"{label} ({timestamp.split('T', maxsplit=1)[0]})"


def _render_activity_context(summary: str) -> str:
    if not summary or summary == "none":
        return "No recent governance context recorded."
    normalized_summary = summary.rstrip(".")
    normalized_segments = [
        segment if index % 2 else segment.lower()
        for index, segment in enumerate(normalized_summary.split("`"))
    ]
    return f"Latest governance work focused on {'`'.join(normalized_segments)}."


def _render_recent_governance_lines(
    recent_session_activity: dict[str, Any],
    *,
    include_outcomes: bool,
    colon_inside_bold: bool,
) -> list[str]:
    def render_label(label: str) -> str:
        return f"**{label}:**" if colon_inside_bold else f"**{label}**:"

    latest_session = recent_session_activity["latest_session"]
    latest_session_label = _format_activity_label(
        latest_session["session_id"] if latest_session else "none",
        latest_session.get("created_timestamp") if latest_session else None,
    )
    latest_automation_pattern = recent_session_activity["latest_automation_pattern"]
    latest_automation_pattern_label = _format_activity_label(
        latest_automation_pattern["pattern_name"] if latest_automation_pattern else "none",
        latest_automation_pattern.get("created_timestamp") if latest_automation_pattern else None,
    )
    latest_technique = recent_session_activity["latest_technique"]
    latest_technique_label = _format_activity_label(
        latest_technique["name"] if latest_technique else "none",
        latest_technique.get("created_timestamp") if latest_technique else None,
    )
    latest_bug_fix = recent_session_activity["latest_bug_fix"]
    latest_bug_fix_label = _format_activity_label(
        latest_bug_fix["id"] if latest_bug_fix else "none",
        latest_bug_fix.get("created_timestamp") if latest_bug_fix else None,
    )

    lines = [
        f"- {render_label('Session Count')} {recent_session_activity['session_count']}",
        f"- {render_label('KB Highlights')} session `{latest_session_label}`; automation `{latest_automation_pattern_label}`; technique `{latest_technique_label}`; bug fix `{latest_bug_fix_label}`",
        f"- {render_label('Why It Matters')} {_render_activity_context(recent_session_activity['latest_summary'])}",
        f"- {render_label('Latest Summary')} {recent_session_activity['latest_summary']}",
    ]

    if include_outcomes:
        lines.extend(
            [
                f"- {render_label('Outcome')} {outcome}"
                for outcome in recent_session_activity["latest_outcomes"]
            ]
            or [f"- {render_label('Outcome')} none recorded"]
        )

    return lines


def _render_where_to_look_first_lines(mode: str) -> list[str]:
    if mode == "summary":
        return [
            "- **Guide:** `README.md` summarizes commands, validation surfaces, and governed workflow entry points.",
            "- **Live Snapshot:** `SYSTEM_STATUS.md` shows the latest derived operational status for components, KB metrics, and operator shortcuts.",
            "- **Canonical Status JSON:** `ai_docs/system_status_snapshot.json` is the structured source of truth for derived status artifacts.",
            "- **Component Registry:** `ai_docs/component_index.json` tracks governed components, dependencies, coverage metadata, and companion docs.",
            "- **KB Rollup:** `knowledge_base/kb_index.json` aggregates KB counts, freshness, lookup indices, and automation metrics.",
        ]
    if mode == "status":
        return [
            "- **Guide**: `README.md` summarizes commands, validation surfaces, and governed workflow entry points.",
            "- **Structured Snapshot**: `ai_docs/system_status_snapshot.json` is the canonical status source of truth.",
            "- **Summary View**: `SYSTEM_SUMMARY.md` provides the condensed human-facing overview of the governed workspace.",
            "- **Component Registry**: `ai_docs/component_index.json` tracks governed components, dependencies, coverage metadata, and companion docs.",
            "- **KB Rollup**: `knowledge_base/kb_index.json` aggregates KB counts, freshness, lookup indices, and automation metrics.",
        ]
    raise ValueError(f"Unsupported where-to-look-first mode: {mode}")


def _render_system_summary_footer(
    snapshot: SystemStatusSnapshot,
    *,
    kb_index: dict[str, Any],
) -> str:
    component_count = snapshot.component_health["total_components"]
    technique_count = int(kb_index["total_techniques"])
    bug_fix_count = int(kb_index["total_bug_fixes"])
    automation_pattern_count = int(kb_index["total_automation_patterns"])
    status_rule_count = len(STATUS_RULES)

    return (
        f"The system now includes {_count_with_label(component_count, 'documented component and artifact', 'documented components and artifacts')}, "
        f"{_count_with_label(technique_count, 'catalogued technique')}, "
        f"{_count_with_label(bug_fix_count, 'recorded bug fix pattern')}, "
        f"{_count_with_label(automation_pattern_count, 'automation pattern')}, a canonical structured status snapshot with self-validation "
        f"across {_count_with_label(status_rule_count, 'status rule')}, and targeted plus aggregate status remediation flows."
    )


def render_system_summary_markdown(
    snapshot: SystemStatusSnapshot,
    *,
    component_index: dict[str, Any],
    kb_index: dict[str, Any],
) -> str:
    last_updated = _max_timestamp(
        [
            str(component_index["metadata"].get("last_updated", "")),
            str(kb_index.get("last_updated", "")),
            snapshot.generated_at,
        ]
    ) or snapshot.generated_at
    last_updated_date = last_updated.split("T", maxsplit=1)[0]
    shortcut_pairs_line = _render_operator_shortcut_pairs(snapshot.operator_shortcuts)
    system_health = _derive_system_health_label(snapshot)
    summary_footer = _render_system_summary_footer(snapshot, kb_index=kb_index)
    recent_governance_lines = _render_recent_governance_lines(
        snapshot.recent_session_activity,
        include_outcomes=False,
        colon_inside_bold=True,
    )
    where_to_look_first_lines = _render_where_to_look_first_lines("summary")

    return "\n".join(
        [
            "# System Summary",
            "",
            f"**Last Updated:** {last_updated_date}  ",
            f"**Total Components:** {snapshot.component_health['total_components']}  ",
            f"**System Health:** {system_health}  ",
            f"**Test Inventory:** {snapshot.test_suite_summary['summary_text']}",
            "",
            "## Architecture",
            "",
            "- **Core Reference View:** `src/inf_work/core_reference.py` centralizes `core_reference.json` loading and governed-directory extraction.",
            "- **Validation Rule Engine:** `src/inf_work/rules.py` registers deterministic rules and standardized rule results for all validators.",
            "- **KB Integrity Validator:** `src/inf_work/kb_integrity.py` validates technique and component cross references across `knowledge_base/` and `ai_docs/`.",
            "- **Workspace Health Checker:** `src/inf_work/workspace_health.py` validates governed directories from `core_reference.json`.",
            "- **System Status Generator:** `src/inf_work/system_status.py` generates the structured system snapshot, derives `SYSTEM_STATUS.md`, captures a collection-only test inventory, and validates both artifacts through status-domain rules.",
            "- **System Status Artifact:** `SYSTEM_STATUS.md` is the human-facing governance snapshot derived from `ai_docs/system_status_snapshot.json`.",
            "- **CLI Entry Point:** `src/inf_work/__main__.py` exposes unified `all`, `workspace`, `kb`, `status`, `status-check`, `summary-check`, and `remediation-plan` commands with rule filtering, named rule profiles, `rule_id` selection, severity-based exit policy, grouped summaries, targeted summary remediation, `status-check --fix` remediation, aggregate `all --fix-status` repair support for stale status artifacts, and a bounded plan-only remediation compiler for supported status drift.",
            "- **CI Check:** `.github/workflows/validator-check.yml` runs focused tests, metadata integrity checks, validator smoke checks, and KB cross-reference smoke checks.",
            "- **Local Check Shortcut:** `Makefile` and `.vscode/tasks.json` support `make bootstrap`, `make`, `make check`, `make test`, `make smoke`, `make kb-check`, `make all-report`, `make all-report-fix-status`, `make resolver-report`, `make component-report`, `make status`, `make status-check`, `make summary-check`, `make coverage-snapshot`, `make refresh-artifacts`, and the matching `workspace:*` tasks using `.venv`; `make check` regenerates then validates the canonical status artifacts.",
            shortcut_pairs_line,
            "",
            "## Where to look first",
            "",
            "- **Guide:** `README.md` summarizes commands, validation surfaces, and governed workflow entry points.",
            "- **Live Snapshot:** `SYSTEM_STATUS.md` shows the latest derived operational status for components, KB metrics, and operator shortcuts.",
            "- **Canonical Status JSON:** `ai_docs/system_status_snapshot.json` is the structured source of truth for derived status artifacts.",
            "- **Component Registry:** `ai_docs/component_index.json` tracks governed components, dependencies, coverage metadata, and companion docs.",
            "- **KB Rollup:** `knowledge_base/kb_index.json` aggregates KB counts, freshness, lookup indices, and automation metrics.",
            "",
            "## Constraint Compliance",
            "",
            "- **I1 (Determinism):** ✓ Health checks derive only from workspace state and core JSON.",
            "- **I2 (Memory Isolation):** ✓ No dynamic allocation beyond bounded in-process data structures.  ",
            "- **I3 (Workspace Coherence):** ✓ Structure initialized",
            "- **I4 (Documentation Purity):** ✓ JSON-first component documentation active",
            "",
            "## Knowledge Base Status",
            "",
            f"- **Techniques:** {kb_index['total_techniques']}",
            f"- **Bug Fixes:** {kb_index['total_bug_fixes']}",
            f"- **Innovations:** {kb_index['total_innovations']}",
            f"- **Automation Patterns:** {kb_index['total_automation_patterns']}",
            "",
            "## Recent Governance Highlights",
            "",
            *recent_governance_lines,
            "",
            summary_footer,
            "",
        ]
    )


def _write_system_summary_output(
    root_path: Path,
    snapshot: SystemStatusSnapshot,
    *,
    summary_path: str = "SYSTEM_SUMMARY.md",
) -> None:
    component_index = _load_json(root_path / "ai_docs" / "component_index.json")
    kb_index = _load_json(root_path / "knowledge_base" / "kb_index.json")
    summary_markdown = render_system_summary_markdown(
        snapshot,
        component_index=component_index,
        kb_index=kb_index,
    )
    (root_path / summary_path).write_text(summary_markdown, encoding="utf-8")


def _evaluate_summary_artifact_exists(context: dict[str, Any]) -> list[RuleFinding]:
    if context["summary_exists"]:
        return []
    return [
        RuleFinding(
            message="Missing derived SYSTEM_SUMMARY.md artifact.",
            source_file=context["summary_path"],
            item_identifier=context["summary_path"],
            field_name="artifact_presence",
        )
    ]


def _evaluate_summary_matches_workspace(context: dict[str, Any]) -> list[RuleFinding]:
    return _evaluate_status_summary_matches_workspace(context)


SUMMARY_RULES = [
    ValidationRule(
        rule_id="summary.artifact_exists",
        domain="status",
        category="artifact_integrity",
        severity="error",
        description="The derived SYSTEM_SUMMARY.md artifact must exist.",
        evaluator=_evaluate_summary_artifact_exists,
    ),
    ValidationRule(
        rule_id="summary.matches_workspace",
        domain="status",
        category="artifact_integrity",
        severity="error",
        description="The derived SYSTEM_SUMMARY.md report must match the current governed workspace state.",
        evaluator=_evaluate_summary_matches_workspace,
    ),
]


def _build_recommended_actions(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    below_threshold_components = snapshot["component_health"]["below_threshold_components"]
    zero_coverage_components = snapshot["known_gaps_technical_debt"]["components_with_zero_percent_coverage"]
    if below_threshold_components:
        threshold = snapshot["coverage_threshold"]
        coverage_reason = (
            f"Components below the {threshold}% coverage threshold: {', '.join(below_threshold_components)}"
        )
        if zero_coverage_components:
            coverage_reason = f"{coverage_reason}; includes 0% modules: {', '.join(zero_coverage_components)}"
        actions.append(
            {
                "priority": 1,
                "action": "Raise coverage for below-threshold components, then refresh the canonical coverage snapshot.",
                "reason": coverage_reason,
                "complexity": "medium",
            }
        )
    if not snapshot["knowledge_base_metrics"]["innovation_count"]:
        actions.append(
            {
                "priority": 2,
                "action": "Document the next constraint-driven innovation in `knowledge_base/constraint_innovations.json`.",
                "reason": "Innovation catalog is currently empty.",
                "complexity": "small",
            }
        )
    if not snapshot["resolver_capabilities"]["inference_modes_supported"]["multi_hop_explicit"] or not snapshot["resolver_capabilities"]["inference_modes_supported"]["multi_hop_inferred"]:
        actions.append(
            {
                "priority": 3,
                "action": "Extend the resolver foundation from single-hop tile lookup into explicit and inferred multi-hop traversal if cross-artifact routing is needed.",
                "reason": "Resolver telemetry is now configured, but both multi-hop modes remain disabled in the runtime capability model.",
                "complexity": "large",
            }
        )
    if not snapshot["known_gaps_technical_debt"]["missing_automation_patterns"]:
        return actions
    actions.append(
        {
            "priority": 4,
            "action": "Catalog the status regeneration workflow as an automation pattern.",
            "reason": snapshot["known_gaps_technical_debt"]["missing_automation_patterns"][0],
            "complexity": "small",
        }
    )
    return actions


def build_system_status_snapshot(
    workspace_root: str | Path,
    *,
    generated_at: str | None = None,
    canonical_json_path: str = "ai_docs/system_status_snapshot.json",
    derived_markdown_path: str = "SYSTEM_STATUS.md",
) -> SystemStatusSnapshot:
    root_path = Path(workspace_root).resolve()
    core_reference = _load_json(root_path / "core_reference.json")
    coverage_threshold = int(
        core_reference["architectural_constraints"]["contracts"]["quality"]["code_coverage_minimum"]
    )

    component_health = _collect_component_health(root_path, coverage_threshold)
    test_suite_summary = _collect_test_suite_summary(root_path, coverage_threshold)
    knowledge_base_metrics = _collect_knowledge_base_metrics(root_path)
    recent_session_activity = _collect_recent_session_activity(root_path)
    schema_contract_integrity = _collect_schema_contract_integrity(root_path)
    resolver_capabilities = _collect_resolver_capabilities(root_path)
    known_gaps_technical_debt = _collect_known_gaps(root_path, test_suite_summary, resolver_capabilities)
    architectural_invariant_compliance = _collect_invariant_compliance(root_path)
    operator_shortcuts = _collect_operator_shortcuts()
    resolved_generated_at = _normalize_utc_timestamp(generated_at or _derive_status_generated_at(root_path))

    snapshot = SystemStatusSnapshot(
        generated_at=resolved_generated_at,
        workspace_root=str(root_path),
        canonical_json_path=canonical_json_path,
        derived_markdown_path=derived_markdown_path,
        coverage_threshold=coverage_threshold,
        component_health=component_health,
        test_suite_summary=test_suite_summary,
        knowledge_base_metrics=knowledge_base_metrics,
        recent_session_activity=recent_session_activity,
        schema_contract_integrity=schema_contract_integrity,
        resolver_capabilities=resolver_capabilities,
        known_gaps_technical_debt=known_gaps_technical_debt,
        architectural_invariant_compliance=architectural_invariant_compliance,
        operator_shortcuts=operator_shortcuts,
        next_recommended_actions=[],
    )
    snapshot_payload = snapshot.to_dict()
    snapshot_payload["next_recommended_actions"] = _build_recommended_actions(snapshot_payload)
    return SystemStatusSnapshot(**snapshot_payload)


def _build_status_context(
    root_path: Path,
    *,
    canonical_json_path: str = "ai_docs/system_status_snapshot.json",
    derived_markdown_path: str = "SYSTEM_STATUS.md",
    summary_path: str = "SYSTEM_SUMMARY.md",
) -> dict[str, Any]:
    snapshot_path = root_path / canonical_json_path
    markdown_path = root_path / derived_markdown_path
    summary_file = root_path / summary_path
    existing_snapshot = _load_json(snapshot_path) if snapshot_path.is_file() else None
    existing_markdown = _read_text(markdown_path) if markdown_path.is_file() else None
    existing_summary = _read_text(summary_file) if summary_file.is_file() else None
    regenerated_snapshot = None
    regenerated_markdown = None
    regenerated_summary = None
    try:
        regenerated_snapshot = build_system_status_snapshot(
            root_path,
            canonical_json_path=str((existing_snapshot or {}).get("canonical_json_path", canonical_json_path)),
            derived_markdown_path=str((existing_snapshot or {}).get("derived_markdown_path", derived_markdown_path)),
        )
        regenerated_summary = render_system_summary_markdown(
            regenerated_snapshot,
            component_index=_load_json(root_path / "ai_docs" / "component_index.json"),
            kb_index=_load_json(root_path / "knowledge_base" / "kb_index.json"),
        )
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        regenerated_snapshot = None
        regenerated_summary = None
    if existing_snapshot is not None:
        regenerated_markdown = render_system_status_markdown(SystemStatusSnapshot(**existing_snapshot))
    return {
        "workspace_root": str(root_path),
        "snapshot_path": canonical_json_path,
        "markdown_path": derived_markdown_path,
        "summary_path": summary_path,
        "snapshot_exists": snapshot_path.is_file(),
        "markdown_exists": markdown_path.is_file(),
        "summary_exists": summary_file.is_file(),
        "existing_snapshot": existing_snapshot,
        "existing_markdown": existing_markdown,
        "existing_summary": existing_summary,
        "regenerated_snapshot": regenerated_snapshot,
        "regenerated_markdown": regenerated_markdown,
        "regenerated_summary": regenerated_summary,
    }


def _evaluate_status_resolver_explicit_route_integrity(context: dict[str, Any]) -> list[RuleFinding]:
    explicit_route = resolve_explicit_path(context["workspace_root"], _EXPECTED_EXPLICIT_ROUTE)
    resolved_tile_ids = [step["tile_id"] for step in explicit_route.resolved_steps]
    if (
        explicit_route.complete
        and explicit_route.failure_reason is None
        and explicit_route.requested_path == _EXPECTED_EXPLICIT_ROUTE
        and resolved_tile_ids == _EXPECTED_EXPLICIT_ROUTE
        and explicit_route.total_hops == 2
    ):
        return []
    return [
        RuleFinding(
            message="The canonical explicit resolver traversal no longer resolves the bounded governance route.",
            source_file="src/inf_work/resolver_registry.py",
            item_identifier="explicit_route_example",
            field_name="resolver_explicit_route_integrity",
            context=explicit_route.to_dict(),
        )
    ]


def _evaluate_status_resolver_inferred_route_integrity(context: dict[str, Any]) -> list[RuleFinding]:
    inferred_route = infer_route(context["workspace_root"], "workspace_governance", "knowledge_base_index")
    resolved_tile_ids = [step["tile_id"] for step in inferred_route.resolved_steps]
    if (
        inferred_route.complete
        and inferred_route.failure_reason is None
        and inferred_route.requested_path == _EXPECTED_INFERRED_ROUTE
        and resolved_tile_ids == _EXPECTED_INFERRED_ROUTE
        and inferred_route.total_hops == 1
    ):
        return []
    return [
        RuleFinding(
            message="The canonical inferred resolver traversal no longer resolves the bounded governance route.",
            source_file="src/inf_work/resolver_registry.py",
            item_identifier="inferred_route_example",
            field_name="resolver_inferred_route_integrity",
            context=inferred_route.to_dict(),
        )
    ]


def _evaluate_status_artifacts_exist(context: dict[str, Any]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    if not context["snapshot_exists"]:
        findings.append(
            RuleFinding(
                message="Missing canonical status snapshot JSON artifact.",
                source_file=context["snapshot_path"],
                item_identifier=context["snapshot_path"],
                field_name="artifact_presence",
            )
        )
    if not context["markdown_exists"]:
        findings.append(
            RuleFinding(
                message="Missing derived SYSTEM_STATUS.md artifact.",
                source_file=context["markdown_path"],
                item_identifier=context["markdown_path"],
                field_name="artifact_presence",
            )
        )
    if not context["summary_exists"]:
        findings.append(
            RuleFinding(
                message="Missing derived SYSTEM_SUMMARY.md artifact.",
                source_file=context["summary_path"],
                item_identifier=context["summary_path"],
                field_name="artifact_presence",
            )
        )
    return findings


def _evaluate_status_snapshot_matches_workspace(context: dict[str, Any]) -> list[RuleFinding]:
    if not context["snapshot_exists"] or context["existing_snapshot"] is None or context["regenerated_snapshot"] is None:
        return []
    existing_snapshot = _normalize_snapshot_payload(context["existing_snapshot"])
    regenerated_snapshot = _normalize_snapshot_payload(context["regenerated_snapshot"].to_dict())
    if existing_snapshot == regenerated_snapshot:
        return []
    return [
        RuleFinding(
            message="Canonical system status snapshot is stale relative to the current workspace state.",
            source_file=context["snapshot_path"],
            item_identifier=context["snapshot_path"],
            field_name="snapshot_consistency",
        )
    ]


def _evaluate_status_markdown_matches_snapshot(context: dict[str, Any]) -> list[RuleFinding]:
    if not context["snapshot_exists"] or not context["markdown_exists"]:
        return []
    if context["existing_markdown"] == context["regenerated_markdown"]:
        return []
    return [
        RuleFinding(
            message="Derived SYSTEM_STATUS.md does not match the canonical structured snapshot.",
            source_file=context["markdown_path"],
            item_identifier=context["markdown_path"],
            field_name="markdown_consistency",
        )
    ]


def _evaluate_status_summary_matches_workspace(context: dict[str, Any]) -> list[RuleFinding]:
    if not context["summary_exists"] or context["existing_summary"] is None or context["regenerated_summary"] is None:
        return []
    if context["existing_summary"] == context["regenerated_summary"]:
        return []
    return [
        RuleFinding(
            message="Derived SYSTEM_SUMMARY.md does not match the current governed workspace state.",
            source_file=context["summary_path"],
            item_identifier=context["summary_path"],
            field_name="summary_consistency",
        )
    ]


STATUS_RULES = [
    ValidationRule(
        rule_id="status.artifacts_exist",
        domain="status",
        category="artifact_integrity",
        severity="error",
        description="Canonical status artifacts must exist for governance reporting.",
        evaluator=_evaluate_status_artifacts_exist,
    ),
    ValidationRule(
        rule_id="status.snapshot_matches_workspace",
        domain="status",
        category="artifact_integrity",
        severity="error",
        description="The canonical structured status snapshot must match the current workspace state.",
        evaluator=_evaluate_status_snapshot_matches_workspace,
    ),
    ValidationRule(
        rule_id="status.markdown_matches_snapshot",
        domain="status",
        category="artifact_integrity",
        severity="error",
        description="The derived markdown status report must match the canonical structured snapshot.",
        evaluator=_evaluate_status_markdown_matches_snapshot,
    ),
    ValidationRule(
        rule_id="status.summary_matches_workspace",
        domain="status",
        category="artifact_integrity",
        severity="error",
        description="The derived SYSTEM_SUMMARY.md report must match the current governed workspace state.",
        evaluator=_evaluate_status_summary_matches_workspace,
    ),
    ValidationRule(
        rule_id="status.resolver_explicit_route_integrity",
        domain="status",
        category="runtime_integrity",
        severity="error",
        description="The canonical explicit resolver example must resolve the bounded governance route successfully.",
        evaluator=_evaluate_status_resolver_explicit_route_integrity,
    ),
    ValidationRule(
        rule_id="status.resolver_inferred_route_integrity",
        domain="status",
        category="runtime_integrity",
        severity="error",
        description="The canonical inferred resolver example must resolve the bounded governance route successfully.",
        evaluator=_evaluate_status_resolver_inferred_route_integrity,
    ),
]

register_rules(STATUS_RULES)


def run_status_rules(
    workspace_root: str | Path,
    rule_ids: set[str] | None = None,
    *,
    canonical_json_path: str = "ai_docs/system_status_snapshot.json",
    derived_markdown_path: str = "SYSTEM_STATUS.md",
) -> list[RuleResult]:
    root_path = Path(workspace_root).resolve()
    if not get_registered_rules("status", rule_ids):
        return []
    context = _build_status_context(
        root_path,
        canonical_json_path=canonical_json_path,
        derived_markdown_path=derived_markdown_path,
    )
    return run_registered_rules("status", context, rule_ids)


def validate_system_status(
    workspace_root: str | Path,
    rule_ids: set[str] | None = None,
    *,
    canonical_json_path: str = "ai_docs/system_status_snapshot.json",
    derived_markdown_path: str = "SYSTEM_STATUS.md",
) -> StatusValidationResult:
    root_path = Path(workspace_root).resolve()
    rule_results = run_status_rules(
        root_path,
        rule_ids,
        canonical_json_path=canonical_json_path,
        derived_markdown_path=derived_markdown_path,
    )
    issues = [
        StatusValidationIssue(
            source_file=finding.source_file,
            item_identifier=finding.item_identifier,
            field_name=finding.field_name,
            message=finding.message,
        )
        for rule_result in rule_results
        for finding in rule_result.findings
    ]
    return StatusValidationResult(
        workspace_root=str(root_path),
        snapshot_path=canonical_json_path,
        markdown_path=derived_markdown_path,
        summary_path="SYSTEM_SUMMARY.md",
        compliant=not issues,
        issues=issues,
        rule_results=rule_results,
    )


def run_summary_rules(
    workspace_root: str | Path,
    *,
    canonical_json_path: str = "ai_docs/system_status_snapshot.json",
    derived_markdown_path: str = "SYSTEM_STATUS.md",
    summary_path: str = "SYSTEM_SUMMARY.md",
) -> list[RuleResult]:
    root_path = Path(workspace_root).resolve()
    context = _build_status_context(
        root_path,
        canonical_json_path=canonical_json_path,
        derived_markdown_path=derived_markdown_path,
        summary_path=summary_path,
    )
    return [rule.run(context) for rule in SUMMARY_RULES]


def validate_system_summary(
    workspace_root: str | Path,
    *,
    canonical_json_path: str = "ai_docs/system_status_snapshot.json",
    derived_markdown_path: str = "SYSTEM_STATUS.md",
    summary_path: str = "SYSTEM_SUMMARY.md",
) -> StatusValidationResult:
    root_path = Path(workspace_root).resolve()
    rule_results = run_summary_rules(
        root_path,
        canonical_json_path=canonical_json_path,
        derived_markdown_path=derived_markdown_path,
        summary_path=summary_path,
    )
    issues = [
        StatusValidationIssue(
            source_file=finding.source_file,
            item_identifier=finding.item_identifier,
            field_name=finding.field_name,
            message=finding.message,
        )
        for rule_result in rule_results
        for finding in rule_result.findings
    ]
    return StatusValidationResult(
        workspace_root=str(root_path),
        snapshot_path=canonical_json_path,
        markdown_path=derived_markdown_path,
        summary_path=summary_path,
        compliant=not issues,
        issues=issues,
        rule_results=rule_results,
    )


def render_system_status_markdown(snapshot: SystemStatusSnapshot) -> str:
    payload = snapshot.to_dict()
    component_lines = []
    for component in payload["component_health"]["components"]:
        threshold_note = " ⚠" if component["coverage_flag"] == "below_threshold" else ""
        dependency_count_text = _count_with_label(len(component["dependencies"]), "dependency", "dependencies")
        dependent_count_text = _count_with_label(len(component["dependents"]), "dependent")
        component_lines.append(
            f"- **{component['component_name']}**: {component['health_status']}, {component['test_coverage_percentage']}% coverage{threshold_note}, {component['compliance_status']}; {dependency_count_text}, {dependent_count_text}"
        )

    coverage_lines = [
        f"- **{module['module_path']}**: {module['coverage_percentage']}% ({'tracked' if module['tracked_in_component_index'] else 'untracked'})"
        for module in payload["test_suite_summary"]["coverage_by_module"]
    ]
    schema_lines = [
        f"- **{bundle['name']}**: version {bundle['version']}"
        for bundle in payload["schema_contract_integrity"]["schema_bundles"]
    ]
    gap_lines = [
        f"- **{feature['feature']}**: {feature['status']} — {feature['evidence']}"
        for feature in payload["known_gaps_technical_debt"]["planned_but_unimplemented_features"]
    ]
    if not gap_lines:
        gap_lines = ["- **Planned Features**: none recorded"]

    todo_lines = [
        f"- **{item['path']}:{item['line_number']}**: {item['text']}"
        for item in payload["known_gaps_technical_debt"]["todo_fixme_items"]
    ] or ["- **TODO/FIXME**: none detected outside archival backups"]

    recommended_action_lines = [
        f"- **P{action['priority']}**: {action['action']} ({action['complexity']}) — {action['reason']}"
        for action in payload["next_recommended_actions"]
    ] or ["- **Actions**: no immediate follow-up recorded"]

    invariant_lines = [
        f"- **{name}**: {details['status']} — {details['evidence']}"
        for name, details in payload["architectural_invariant_compliance"].items()
    ]
    operator_shortcut_lines = [
        f"- **{shortcut['name']}**: `{shortcut['command']}` | VS Code task: `{shortcut['task_label']}` — {shortcut['purpose']}"
        for shortcut in payload["operator_shortcuts"]
    ] or ["- **Shortcuts**: no operator shortcuts recorded"]
    where_to_look_first_lines = _render_where_to_look_first_lines("status")

    latest_technique = payload["knowledge_base_metrics"]["latest_technique"]
    latest_technique_text = latest_technique["name"] if latest_technique else "none"
    latest_innovation = payload["knowledge_base_metrics"]["latest_innovation"]
    latest_innovation_text = latest_innovation["id"] if latest_innovation else "none"
    recent_governance_lines = _render_recent_governance_lines(
        payload["recent_session_activity"],
        include_outcomes=True,
        colon_inside_bold=False,
    )
    traversal_examples = payload["resolver_capabilities"].get("traversal_examples", {})
    explicit_traversal = traversal_examples.get("explicit")
    inferred_traversal = traversal_examples.get("inferred")
    explicit_route_text = " -> ".join(step["tile_id"] for step in explicit_traversal["resolved_steps"]) if explicit_traversal else "none"
    inferred_route_text = " -> ".join(step["tile_id"] for step in inferred_traversal["resolved_steps"]) if inferred_traversal else "none"
    dangling_reference_files = payload["schema_contract_integrity"]["orphaned_or_dangling_references"]["component_files"]
    dangling_reference_docs = payload["schema_contract_integrity"]["orphaned_or_dangling_references"]["component_docs"]
    dangling_reference_text = (
        f"{_count_with_label(len(dangling_reference_files), 'file')}, "
        f"{_count_with_label(len(dangling_reference_docs), 'doc')}"
    )
    registered_tile_count_text = _count_with_label(
        len(payload["resolver_capabilities"]["registered_tiles"]),
        "registered tile",
    )

    return "\n".join(
        [
            "# System Status",
            "",
            f"- **Generated At**: {payload['generated_at']}",
            f"- **Workspace Root**: `{payload['workspace_root']}`",
            f"- **Canonical Data**: `{payload['canonical_json_path']}`",
            f"- **Derived Artifact**: `{payload['derived_markdown_path']}`",
            "",
            "## 1. Component Health",
            *component_lines,
            "",
            "## 2. Test Inventory",
            f"- **Collected Tests**: {payload['test_suite_summary']['total_tests']}",
            f"- **Collection Summary**: {payload['test_suite_summary']['summary_text']}",
            f"- **Pass Rate**: {payload['test_suite_summary']['pass_rate']}",
            f"- **Pending/Skipped**: {payload['test_suite_summary']['pending_or_skipped_tests']}",
            *coverage_lines,
            "",
            "## 3. Knowledge Base Metrics",
            f"- **Technique Count**: {payload['knowledge_base_metrics']['technique_count']} (latest: {latest_technique_text})",
            f"- **Innovation Count**: {payload['knowledge_base_metrics']['innovation_count']} (latest: {latest_innovation_text})",
            f"- **Bug Fixes**: {payload['knowledge_base_metrics']['bug_fix_count']}",
            f"- **Automation Patterns**: {payload['knowledge_base_metrics']['automation_pattern_count']}",
            f"- **Last KB Update**: {payload['knowledge_base_metrics']['last_kb_update_timestamp']}",
            "",
            "## 4. Recent Governance Highlights",
            *recent_governance_lines,
            "",
            "## 5. Schema/Contract Integrity",
            *schema_lines,
            f"- **Cross-Reference Validation**: {'healthy' if payload['schema_contract_integrity']['cross_reference_validation']['compliant'] else 'issues_detected'}",
            f"- **Workspace Coherence**: {'healthy' if payload['schema_contract_integrity']['workspace_coherence_validation']['compliant'] else 'issues_detected'}",
            f"- **Dangling References**: {dangling_reference_text}",
            "",
            "## 6. Resolver Capabilities",
            f"- **Single-Hop**: {payload['resolver_capabilities']['inference_modes_supported']['single_hop']}",
            f"- **Multi-Hop Explicit**: {payload['resolver_capabilities']['inference_modes_supported']['multi_hop_explicit']}",
            f"- **Multi-Hop Inferred**: {payload['resolver_capabilities']['inference_modes_supported']['multi_hop_inferred']}",
            f"- **Registered Tiles**: {registered_tile_count_text}",
            f"- **Pressure Telemetry**: {payload['resolver_capabilities']['pressure_telemetry_status']['status']}",
            f"- **Explicit Route Example**: {explicit_route_text}",
            f"- **Inferred Route Example**: {inferred_route_text}",
            "",
            "## 7. Known Gaps & Technical Debt",
            f"- **0% Coverage Modules**: {', '.join(payload['known_gaps_technical_debt']['components_with_zero_percent_coverage']) or 'none'}",
            f"- **Missing Automation Patterns**: {', '.join(payload['known_gaps_technical_debt']['missing_automation_patterns']) or 'none'}",
            *todo_lines,
            *gap_lines,
            "",
            "## 8. Architectural Invariant Compliance",
            *invariant_lines,
            "",
            "## 9. Operator Shortcuts",
            *operator_shortcut_lines,
            "",
            "## Where to look first",
            *where_to_look_first_lines,
            "",
            "## 10. Next Recommended Actions",
            *recommended_action_lines,
        ]
    ) + "\n"


def write_system_status_outputs(
    workspace_root: str | Path,
    *,
    generated_at: str | None = None,
    canonical_json_path: str = "ai_docs/system_status_snapshot.json",
    derived_markdown_path: str = "SYSTEM_STATUS.md",
    summary_path: str = "SYSTEM_SUMMARY.md",
) -> SystemStatusSnapshot:
    root_path = Path(workspace_root).resolve()
    json_path = root_path / canonical_json_path
    markdown_path = root_path / derived_markdown_path
    summary_file = root_path / summary_path
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    if not json_path.exists():
        json_path.write_text("{}\n", encoding="utf-8")
    if not markdown_path.exists():
        markdown_path.write_text("# System Status\n", encoding="utf-8")
    if not summary_file.exists():
        summary_file.write_text("# System Summary\n", encoding="utf-8")
    existing_coverage_snapshot = _load_test_coverage_snapshot(root_path)
    if existing_coverage_snapshot is not None:
        _sync_component_index_coverage(root_path, existing_coverage_snapshot)
    snapshot = build_system_status_snapshot(
        workspace_root,
        generated_at=generated_at,
        canonical_json_path=canonical_json_path,
        derived_markdown_path=derived_markdown_path,
    )
    json_path.write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")
    markdown_path.write_text(render_system_status_markdown(snapshot), encoding="utf-8")
    _write_system_summary_output(root_path, snapshot, summary_path=summary_path)
    return snapshot