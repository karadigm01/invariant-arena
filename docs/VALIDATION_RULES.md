# Validation Rules and Reporting Behavior

This document preserves the detailed inventory of validation and reporting behavior that the
`inf_work` validators implement. The aggregate governance report currently executes 65
registered rules across the `workspace`, `knowledge_base`, and `status` domains.

## Report structure

- Every validator emits `rule_results` with stable `rule_id`, `category`, `severity`, and `findings` data.
- Every report includes a `rule_summary` or `aggregate_rule_summary` grouped by domain, category, and severity.
- CLI filters narrow reported rules in the output (`--only-failures`, `--severity`, `--domain-filter`, `--category`).
- `--rule-id` executes only specific registered rules.
- `--profile` executes stable named bundles of rules: `ci`, `status-only`, `resolver-only`, `component-governance`, `kb-only`, `workspace-only`, `kb-cross-reference`, and `kb-metadata`.
- `--fail-on` decides which severity threshold produces a non-zero exit code (`error` is the default).

## Knowledge-base validation

Knowledge-base validation checks:

- Component index ↔ component doc parity for shared metadata: component identity, type, creation timestamp, compliance status, indexed file path coverage, dependency alignment, and technique traceability.
- Companion component docs against the required `ai_reference_format` fields declared in `core_reference.json`.
- Each companion component doc top-level field set against the governed JSON shape, so unexpected metadata fields cannot silently accumulate.
- `auto_generated: true` for governed companion component docs, so AI reference artifacts cannot drift into manual-state markers.
- Each companion doc `test_coverage.targeted_test_file` path against the live workspace, so governed test references cannot drift to missing files.
- Each companion doc `test_coverage` field set, so unexpected nested metadata cannot accumulate outside the governed verification shape.
- Each companion doc `test_coverage.status` value against the governed status vocabulary, so coverage metadata cannot drift to ad-hoc labels.
- Each companion doc `test_coverage.status` value against the governed `component_type`, so runtime-backed artifacts and Python modules cannot silently swap coverage-verification modes.
- Each companion doc `interfaces` shape against the governed `component_type`, so Python modules keep a callable API surface and governance artifacts keep explicit artifact/source-of-truth links.
- Each companion doc `interfaces` value types, so every documented interface surface remains a JSON list instead of drifting to scalar metadata.
- Each companion doc `interfaces` entries, so every documented interface surface remains a non-empty list of non-empty strings.
- Each companion doc `performance_metrics` shape against the governed `component_type`, so Python modules keep runtime-oriented metrics and governance artifacts keep generation/storage metrics.
- Each companion doc `performance_metrics` value payload, so governed metrics remain non-empty strings instead of blank placeholders.
- Each companion doc `file_paths` entry against the live workspace, so governed implementation and test path inventories cannot drift to missing files.
- Each companion doc `dependencies` entry against the live workspace, so governed dependency inventories cannot drift to missing paths.
- Companion doc `interfaces.cli` entries against the supported `inf_work` command surface, so documented CLI workflows cannot drift to unsupported subcommands.
- Companion doc `interfaces.python_api` entries against symbols exported by the governed module, so documented Python surfaces cannot drift to missing callables or package exports.
- Companion doc `notes` arrays stay non-empty and string-only, so governed implementation context cannot decay into blank placeholders.
- `knowledge_base/kb_index.json` parity for last-updated freshness, aggregate counts, automation success metrics, constraint-compliance totals, and lookup indices derived from the canonical KB source files.
- Direct source-file metadata counts in `techniques.json`, `bug_fixes.json`, `constraint_innovations.json`, `automation_patterns.json`, and `session_history.json`.
- Direct source-file freshness metadata, so `metadata.last_updated`, `metadata.first_session`, and `metadata.last_session` stay aligned with the entries recorded in each KB source file.
- Governed Python component `test_coverage_percentage` values against the canonical `ai_docs/test_coverage_snapshot.json` artifact generated from `pytest-cov`.

## Component governance

Component governance validates `ai_docs/component_index.json`:

- `dependents` lists against the live component dependency topology, so reverse links cannot drift; entries must be non-empty strings.
- `documentation_path` values, so every governed component entry keeps a non-empty companion-doc path.
- `file_path` values, so every entry keeps a non-empty implementation path; values must also be unique across the inventory.
- `health_status` values within the healthy/degraded/failing vocabulary before aggregate status totals are evaluated.
- `compliance_status` values on the documented compliance contract before companion-doc metadata parity is evaluated.
- `complexity_score` values as non-negative integers.
- `test_coverage_percentage` values as integers inside the inclusive `0..100` range before coverage parity is evaluated.
- `creation_timestamp` and `last_modified_timestamp` values as non-empty ISO-8601 UTC timestamps before timestamp parity is evaluated.
- `component_name` values as non-empty human-readable names; values must also be unique.
- `component_type` values within the governed component-type vocabulary.
- `component_id` values as non-empty stable identifiers; values must also be unique.
- `dependencies` lists as unique lists of non-empty strings.
- `related_techniques` lists as lists of non-empty strings.
- `known_issues` lists as lists of non-empty strings (empty lists allowed).
- `performance_metrics` field sets, keeping the exact latency/memory metadata shape with non-empty string content.
- Summary metadata, so `metadata.total_components` and the aggregate `health_status` counts stay aligned with the live component inventory.
- Timestamp integrity, so each component preserves `creation_timestamp <= last_modified_timestamp` and `metadata.last_updated` matches the latest component modification timestamp.

## Status-domain validation

- `status-check` exposes the status artifact validator directly, and `all` includes the `status` domain in aggregate reports.
- `status-check` includes runtime-integrity rules that fail if the canonical explicit or inferred resolver examples stop resolving the bounded governance routes.
- `summary-check` exposes a dedicated validator for the generated `SYSTEM_SUMMARY.md` artifact.
- `status-check --fix` regenerates stale status artifacts before validating them.
- `summary-check --fix` refreshes the governed status outputs before validating the generated summary artifact.
- Canonical status rendering surfaces threshold-aware follow-up actions when governed components fall below the configured coverage minimum, and includes the `coverage-snapshot` operator shortcut alongside the other governed task pairs.
- Canonical status generation derives `ai_docs/system_status_snapshot.json:generated_at` from the freshest governed source artifacts instead of preserving a stale fixed timestamp.

## Remediation

- `remediation-plan` selects between the supported remediation slices.
- `remediation-plan --intent intent.status.refresh_artifacts` triggers the explicit governed status-refresh capability.
- `remediation-plan --simulate` previews deterministic diffs for status-artifact and package-export remediations.
- `remediation-plan --apply` executes the bounded slice with verification and rollback.
- `all --fix-status` applies the status-artifact remediation before the combined aggregate report runs.

## Governed automation patterns

- `knowledge_base/automation_patterns.json` is the canonical catalog of reusable governed automation patterns, including operator-surface promotions such as `automation_refresh_artifacts_operator_surface_promotion` (the `refresh-artifacts` one-shot workflow).
- `knowledge_base/session_history.json` is the chronological rollout record showing when governed automation and operator-surface changes were introduced and revalidated.
