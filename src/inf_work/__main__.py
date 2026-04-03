from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any

from .kb_integrity import validate_knowledge_base
from .remediation import apply_status_artifact_remediation, compile_status_artifact_remediation_plan
from .resolver_registry import infer_route, resolve_explicit_path
from .rules import (
    filter_rule_results,
    get_rule_profiles,
    resolve_rule_selection,
    should_fail_rule_results,
    summarize_rule_results,
)
from .system_status import (
    repair_and_validate_system_status,
    repair_and_validate_system_summary,
    validate_system_status,
    validate_system_summary,
    write_test_coverage_snapshot,
    write_system_status_outputs,
)
from .workspace_health import validate_workspace


@dataclass(frozen=True)
class AggregateValidationResult:
    workspace_root: str
    compliant: bool
    workspace: dict[str, object]
    knowledge_base: dict[str, object]
    status: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "workspace_root": self.workspace_root,
            "compliant": self.compliant,
            "workspace": self.workspace,
            "knowledge_base": self.knowledge_base,
            "status": self.status,
        }


@dataclass(frozen=True)
class ArtifactRefreshResult:
    workspace_root: str
    coverage_snapshot: dict[str, object]
    status_snapshot: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "workspace_root": self.workspace_root,
            "coverage_snapshot": self.coverage_snapshot,
            "status_snapshot": self.status_snapshot,
        }


RULE_PROFILES = get_rule_profiles()


def _add_common_arguments(parser: argparse.ArgumentParser, help_text: str) -> None:
    parser.add_argument(
        "workspace_root",
        nargs="?",
        default=".",
        help=help_text,
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Print indented JSON output",
    )
    parser.add_argument(
        "--profile",
        action="append",
        choices=sorted(RULE_PROFILES),
        help="Execute a named bundle of rule ids. Repeat for multiple profiles.",
    )
    parser.add_argument(
        "--category",
        action="append",
        help="Filter reported rule results by category. Repeat for multiple categories.",
    )
    parser.add_argument(
        "--severity",
        action="append",
        help="Filter reported rule results by severity. Repeat for multiple severities.",
    )
    parser.add_argument(
        "--only-failures",
        action="store_true",
        help="Only include failing rule results in the report output.",
    )
    parser.add_argument(
        "--domain-filter",
        choices=["workspace", "knowledge_base", "status"],
        help="Filter reported rule results to a single domain, mainly for the `all` report.",
    )
    parser.add_argument(
        "--rule-id",
        action="append",
        help="Execute only the specified rule id. Repeat for multiple rules.",
    )
    parser.add_argument(
        "--fail-on",
        choices=["none", "info", "warning", "error", "critical"],
        default="error",
        help="Exit with a failure code only when a failed rule meets or exceeds this severity threshold.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run inf.work validation commands.")
    subparsers = parser.add_subparsers(dest="command")

    workspace_parser = subparsers.add_parser(
        "workspace",
        help="Validate the governed workspace layout.",
    )
    _add_common_arguments(
        workspace_parser,
        "Workspace root containing core_reference.json",
    )

    kb_parser = subparsers.add_parser(
        "kb",
        help="Validate knowledge-base cross references.",
    )
    _add_common_arguments(
        kb_parser,
        "Workspace root containing knowledge_base/ and ai_docs/",
    )

    all_parser = subparsers.add_parser(
        "all",
        help="Run workspace and knowledge-base validation together.",
    )
    _add_common_arguments(
        all_parser,
        "Workspace root containing core_reference.json, knowledge_base/, and ai_docs/",
    )
    all_parser.add_argument(
        "--fix-status",
        action="store_true",
        help="Regenerate the canonical status artifacts before running aggregate validation.",
    )

    status_parser = subparsers.add_parser(
        "status",
        help="Generate the canonical system status snapshot and derived markdown report.",
    )
    status_parser.add_argument(
        "workspace_root",
        nargs="?",
        default=".",
        help="Workspace root containing the governed status inputs.",
    )
    status_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Print indented JSON output",
    )
    status_parser.add_argument(
        "--json-output",
        default="ai_docs/system_status_snapshot.json",
        help="Write canonical structured status data to this path, relative to the workspace root.",
    )
    status_parser.add_argument(
        "--markdown-output",
        default="SYSTEM_STATUS.md",
        help="Write the derived markdown status report to this path, relative to the workspace root.",
    )

    status_check_parser = subparsers.add_parser(
        "status-check",
        help="Validate the canonical system status snapshot and derived markdown report.",
    )
    _add_common_arguments(
        status_check_parser,
        "Workspace root containing the canonical status artifacts.",
    )
    status_check_parser.add_argument(
        "--fix",
        action="store_true",
        help="Regenerate the canonical status artifacts before validating them.",
    )

    summary_check_parser = subparsers.add_parser(
        "summary-check",
        help="Validate the derived SYSTEM_SUMMARY.md report.",
    )
    _add_common_arguments(
        summary_check_parser,
        "Workspace root containing the governed summary artifact.",
    )
    summary_check_parser.add_argument(
        "--fix",
        action="store_true",
        help="Regenerate the governed status outputs before validating SYSTEM_SUMMARY.md.",
    )

    coverage_snapshot_parser = subparsers.add_parser(
        "coverage-snapshot",
        help="Generate the canonical Python test coverage snapshot artifact.",
    )
    coverage_snapshot_parser.add_argument(
        "workspace_root",
        nargs="?",
        default=".",
        help="Workspace root containing the governed Python modules and tests.",
    )
    coverage_snapshot_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Print indented JSON output",
    )

    refresh_artifacts_parser = subparsers.add_parser(
        "refresh-artifacts",
        help="Refresh the canonical coverage snapshot and regenerate governed status artifacts in one step.",
    )
    refresh_artifacts_parser.add_argument(
        "workspace_root",
        nargs="?",
        default=".",
        help="Workspace root containing the governed Python modules, tests, and status inputs.",
    )
    refresh_artifacts_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Print indented JSON output",
    )

    remediation_plan_parser = subparsers.add_parser(
        "remediation-plan",
        help="Compile a deterministic remediation plan for supported status-artifact drift rules, with optional dry-run simulation.",
    )
    remediation_plan_parser.add_argument(
        "workspace_root",
        nargs="?",
        default=".",
        help="Workspace root containing the governed status artifacts.",
    )
    remediation_plan_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Print indented JSON output",
    )
    remediation_plan_parser.add_argument(
        "--profile",
        action="append",
        choices=sorted(RULE_PROFILES),
        help="Restrict the underlying status validation to a named bundle of rule ids. Repeat for multiple profiles.",
    )
    remediation_plan_parser.add_argument(
        "--rule-id",
        action="append",
        help="Restrict the underlying status validation to specific rule ids. Repeat for multiple rules.",
    )
    remediation_mode_group = remediation_plan_parser.add_mutually_exclusive_group()
    remediation_mode_group.add_argument(
        "--simulate",
        action="store_true",
        help="Include the phase-2 dry-run structured remediation simulation with predicted artifact diffs.",
    )
    remediation_mode_group.add_argument(
        "--apply",
        action="store_true",
        help="Execute the bounded status-artifact remediation with verification and rollback.",
    )

    resolve_path_parser = subparsers.add_parser(
        "resolve-path",
        help="Resolve an explicit multi-hop path across the bounded resolver tile graph.",
    )
    resolve_path_parser.add_argument(
        "tile_ids",
        nargs="+",
        help="One or more resolver tile ids to traverse in order.",
    )
    resolve_path_parser.add_argument(
        "--workspace-root",
        default=".",
        help="Workspace root containing the governed resolver inputs.",
    )
    resolve_path_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Print indented JSON output",
    )

    infer_route_parser = subparsers.add_parser(
        "infer-route",
        help="Infer a deterministic route between two resolver tiles.",
    )
    infer_route_parser.add_argument(
        "start_tile_id",
        help="Resolver tile id to start from.",
    )
    infer_route_parser.add_argument(
        "target_tile_id",
        help="Resolver tile id to reach.",
    )
    infer_route_parser.add_argument(
        "--workspace-root",
        default=".",
        help="Workspace root containing the governed resolver inputs.",
    )
    infer_route_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Print indented JSON output",
    )
    return parser


def _print_result(result: object, pretty: bool) -> int:
    indent = 2 if pretty else None
    print(json.dumps(result.to_dict(), indent=indent, sort_keys=True))
    return 0 if result.compliant else 1


def _selected_set(values: list[str] | None) -> set[str] | None:
    return set(values) if values else None


def _report_filters(args: argparse.Namespace) -> dict[str, Any]:
    filters = {
        "profiles": args.profile or [],
        "categories": args.category or [],
        "severities": args.severity or [],
        "only_failures": args.only_failures,
        "domain_filter": args.domain_filter,
        "rule_ids": args.rule_id or [],
        "fail_on": args.fail_on,
    }
    if hasattr(args, "fix"):
        filters["fix"] = args.fix
    if hasattr(args, "fix_status"):
        filters["fix_status"] = args.fix_status
    return filters


def _build_filtered_rule_payload(
    result: object,
    *,
    categories: set[str] | None,
    severities: set[str] | None,
    domains: set[str] | None,
    only_failures: bool,
    include_filters: dict[str, Any],
) -> dict[str, Any]:
    payload = result.to_dict()
    rule_results = getattr(result, "rule_results", [])
    filtered_rule_results = filter_rule_results(
        rule_results,
        categories=categories,
        severities=severities,
        domains=domains,
        only_failures=only_failures,
    )
    payload["rule_results"] = [rule_result.to_dict() for rule_result in filtered_rule_results]
    payload["rule_summary"] = summarize_rule_results(filtered_rule_results)
    payload["report_filters"] = include_filters
    return payload


def main() -> int:
    argv = sys.argv[1:]

    if argv and argv[0] not in {"workspace", "kb", "all", "status", "status-check", "summary-check", "coverage-snapshot", "refresh-artifacts", "remediation-plan", "resolve-path", "infer-route", "-h", "--help"}:
        legacy_parser = argparse.ArgumentParser(
            description="Validate the governed workspace layout.",
        )
        _add_common_arguments(
            legacy_parser,
            "Workspace root containing core_reference.json",
        )
        args = legacy_parser.parse_args(argv)
        selected_rule_ids = resolve_rule_selection(
            profile_names=args.profile,
            rule_ids=args.rule_id,
        )
        result = validate_workspace(Path(args.workspace_root), selected_rule_ids)
        payload = _build_filtered_rule_payload(
            result,
            categories=_selected_set(args.category),
            severities=_selected_set(args.severity),
            domains={args.domain_filter} if args.domain_filter else None,
            only_failures=args.only_failures,
            include_filters=_report_filters(args),
        )
        exit_code = 1 if should_fail_rule_results(result.rule_results, args.fail_on) else 0
        return _print_result(type("Report", (), {"to_dict": lambda self: payload, "compliant": exit_code == 0})(), args.pretty)

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "resolve-path":
        result = resolve_explicit_path(Path(args.workspace_root), args.tile_ids)
        return _print_result(
            type("Report", (), {"to_dict": lambda self: result.to_dict(), "compliant": result.complete})(),
            args.pretty,
        )

    if args.command == "infer-route":
        result = infer_route(Path(args.workspace_root), args.start_tile_id, args.target_tile_id)
        return _print_result(
            type("Report", (), {"to_dict": lambda self: result.to_dict(), "compliant": result.complete})(),
            args.pretty,
        )

    if args.command == "status":
        snapshot = write_system_status_outputs(
            Path(args.workspace_root),
            canonical_json_path=args.json_output,
            derived_markdown_path=args.markdown_output,
        )
        return _print_result(type("Report", (), {"to_dict": lambda self: snapshot.to_dict(), "compliant": True})(), args.pretty)

    if args.command == "coverage-snapshot":
        snapshot = write_test_coverage_snapshot(Path(args.workspace_root))
        return _print_result(type("Report", (), {"to_dict": lambda self: snapshot, "compliant": True})(), args.pretty)

    if args.command == "refresh-artifacts":
        workspace_root = Path(args.workspace_root)
        coverage_snapshot = write_test_coverage_snapshot(workspace_root)
        status_snapshot = write_system_status_outputs(workspace_root)
        result = ArtifactRefreshResult(
            workspace_root=str(workspace_root.resolve()),
            coverage_snapshot=coverage_snapshot,
            status_snapshot=status_snapshot.to_dict(),
        )
        return _print_result(type("Report", (), {"to_dict": lambda self: result.to_dict(), "compliant": True})(), args.pretty)

    if args.command == "remediation-plan":
        selected_rule_ids = resolve_rule_selection(
            profile_names=args.profile,
            rule_ids=args.rule_id,
        )
        if args.apply:
            execution_result = apply_status_artifact_remediation(
                Path(args.workspace_root),
                selected_rule_ids,
            )
            return _print_result(
                type(
                    "Report",
                    (),
                    {"to_dict": lambda self: execution_result.to_dict(), "compliant": execution_result.compliant},
                )(),
                args.pretty,
            )

        plan = compile_status_artifact_remediation_plan(
            Path(args.workspace_root),
            selected_rule_ids,
            include_simulation=args.simulate,
        )
        return _print_result(type("Report", (), {"to_dict": lambda self: plan.to_dict(), "compliant": True})(), args.pretty)

    if args.command is None:
        result = validate_workspace(Path("."), None)
        return _print_result(result, False)

    categories = _selected_set(args.category)
    severities = _selected_set(args.severity)
    domain_filter = {args.domain_filter} if args.domain_filter else None
    report_filters = _report_filters(args)
    selected_rule_ids = resolve_rule_selection(
        profile_names=args.profile,
        rule_ids=args.rule_id,
    )

    if args.command == "kb":
        result = validate_knowledge_base(Path(args.workspace_root), selected_rule_ids)
        payload = _build_filtered_rule_payload(
            result,
            categories=categories,
            severities=severities,
            domains=domain_filter,
            only_failures=args.only_failures,
            include_filters=report_filters,
        )
        exit_code = 1 if should_fail_rule_results(result.rule_results, args.fail_on) else 0
        return _print_result(type("Report", (), {"to_dict": lambda self: payload, "compliant": exit_code == 0})(), args.pretty)

    if args.command == "all":
        workspace_result = validate_workspace(Path(args.workspace_root), selected_rule_ids)
        kb_result = validate_knowledge_base(Path(args.workspace_root), selected_rule_ids)
        if args.fix_status:
            status_result = repair_and_validate_system_status(Path(args.workspace_root), selected_rule_ids)
        else:
            status_result = validate_system_status(Path(args.workspace_root), selected_rule_ids)
        workspace_payload = _build_filtered_rule_payload(
            workspace_result,
            categories=categories,
            severities=severities,
            domains=domain_filter,
            only_failures=args.only_failures,
            include_filters=report_filters,
        )
        kb_payload = _build_filtered_rule_payload(
            kb_result,
            categories=categories,
            severities=severities,
            domains=domain_filter,
            only_failures=args.only_failures,
            include_filters=report_filters,
        )
        status_payload = _build_filtered_rule_payload(
            status_result,
            categories=categories,
            severities=severities,
            domains=domain_filter,
            only_failures=args.only_failures,
            include_filters=report_filters,
        )
        filtered_combined_results = filter_rule_results(
            workspace_result.rule_results + kb_result.rule_results + status_result.rule_results,
            categories=categories,
            severities=severities,
            domains=domain_filter,
            only_failures=args.only_failures,
        )
        result = AggregateValidationResult(
            workspace_root=str(Path(args.workspace_root).resolve()),
            compliant=workspace_result.compliant and kb_result.compliant and status_result.compliant,
            workspace=workspace_payload,
            knowledge_base=kb_payload,
            status=status_payload,
        )
        payload = result.to_dict()
        payload["aggregate_rule_summary"] = summarize_rule_results(filtered_combined_results)
        payload["report_filters"] = report_filters
        exit_code = 1 if should_fail_rule_results(workspace_result.rule_results + kb_result.rule_results + status_result.rule_results, args.fail_on) else 0
        return _print_result(type("Report", (), {"to_dict": lambda self: payload, "compliant": exit_code == 0})(), args.pretty)

    if args.command == "workspace":
        result = validate_workspace(Path(args.workspace_root), selected_rule_ids)
        payload = _build_filtered_rule_payload(
            result,
            categories=categories,
            severities=severities,
            domains=domain_filter,
            only_failures=args.only_failures,
            include_filters=report_filters,
        )
        exit_code = 1 if should_fail_rule_results(result.rule_results, args.fail_on) else 0
        return _print_result(type("Report", (), {"to_dict": lambda self: payload, "compliant": exit_code == 0})(), args.pretty)

    if args.command == "status-check":
        if args.fix:
            result = repair_and_validate_system_status(Path(args.workspace_root), selected_rule_ids)
        else:
            result = validate_system_status(Path(args.workspace_root), selected_rule_ids)
        payload = _build_filtered_rule_payload(
            result,
            categories=categories,
            severities=severities,
            domains=domain_filter,
            only_failures=args.only_failures,
            include_filters=report_filters,
        )
        exit_code = 1 if should_fail_rule_results(result.rule_results, args.fail_on) else 0
        return _print_result(type("Report", (), {"to_dict": lambda self: payload, "compliant": exit_code == 0})(), args.pretty)

    if args.fix:
        result = repair_and_validate_system_summary(Path(args.workspace_root))
    else:
        result = validate_system_summary(Path(args.workspace_root))
    payload = _build_filtered_rule_payload(
        result,
        categories=categories,
        severities=severities,
        domains=domain_filter,
        only_failures=args.only_failures,
        include_filters=report_filters,
    )
    exit_code = 1 if should_fail_rule_results(result.rule_results, args.fail_on) else 0
    return _print_result(type("Report", (), {"to_dict": lambda self: payload, "compliant": exit_code == 0})(), args.pretty)

if __name__ == "__main__":
    raise SystemExit(main())
