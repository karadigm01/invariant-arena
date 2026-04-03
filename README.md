# inf.work

A small Python starter component for this workspace.

## Included

- `inf_work.core_reference`: loads `core_reference.json` and normalizes governed directory metadata
- `inf_work.rules`: registers reusable validation rules with standardized rule results
- `inf_work.resolver_registry`: exposes deterministic single-hop tiles, bounded explicit and inferred multi-hop traversal, and configured pressure telemetry metadata from the governed workspace
- `inf_work.kb_integrity`: validates knowledge-base and component-index cross references
- `inf_work.workspace_health`: validates governed directories from `core_reference.json`
- `python3 -m inf_work all`: prints a combined JSON report for workspace and knowledge-base validation after install, or with `PYTHONPATH=src`
- `python3 -m inf_work workspace`: prints a JSON health report for the workspace after install, or with `PYTHONPATH=src`
- `python3 -m inf_work kb`: prints a JSON knowledge-base cross-reference report after install, or with `PYTHONPATH=src`
- `python3 -m inf_work status`: regenerates canonical structured status data and the derived `SYSTEM_STATUS.md` snapshot
- `python3 -m inf_work status-check`: validates the canonical structured status data and the derived `SYSTEM_STATUS.md` snapshot, with optional `--fix` remediation
- `python3 -m inf_work summary-check`: validates the derived `SYSTEM_SUMMARY.md` artifact, with optional `--fix` remediation
- `python3 -m inf_work remediation-plan`: compiles a deterministic remediation payload for the supported remediation slices without mutating the workspace
- `python3 -m inf_work remediation-plan --intent intent.status.refresh_artifacts`: compiles the explicit governed status-refresh remediation plan even when the status artifacts are already compliant
- `python3 -m inf_work remediation-plan --simulate`: extends that payload with a dry-run remediation preview showing predicted diffs for the selected supported slice without mutating the workspace
- `python3 -m inf_work remediation-plan --apply`: executes the selected bounded remediation slice, including status-artifact regeneration or package-export source synchronization, verifies the result, and restores the pre-apply artifact state if verification fails
- `python3 -m inf_work coverage-snapshot`: generates the canonical `ai_docs/test_coverage_snapshot.json` artifact from a real `pytest-cov` run so component coverage metadata can be governed from runtime data
- `python3 -m inf_work refresh-artifacts`: refreshes the canonical coverage snapshot and then regenerates the governed status artifacts in one deterministic step
- `python3 -m inf_work resolve-path`: resolves an explicit path across the bounded resolver tile graph and prints the traversal payload as JSON
- `python3 -m inf_work infer-route`: infers a deterministic route between two resolver tiles and prints the traversal payload as JSON
- `python3 -m inf_work all --fix-status`: repairs stale canonical status artifacts before running the aggregate validation report
- `tests/test_core_reference.py`, `tests/test_workspace_health.py`, `tests/test_metadata_integrity.py`, `tests/test_kb_integrity.py`, `tests/test_rules.py`, `tests/test_cli_entrypoints.py`, `tests/test_resolver_registry.py`, and `tests/test_remediation.py`: focused tests for core loading, rule registration, validation, JSON/index integrity, KB cross references, package exports, CLI entrypoint wrappers, resolver capability plus multi-hop traversal reporting, and plan, dry-run, applied, plus bounded source-level remediation behavior
- `tests/test_system_status.py`: focused tests for canonical system status generation and markdown derivation
- `.github/workflows/validator-check.yml`: lightweight CI for focused tests, validator smoke checks, canonical status generation and validation, the aggregate governance report, and the dedicated `resolver-only` runtime-integrity profile
- `Makefile` and `.vscode/tasks.json`: local validation via `make bootstrap`, `make`, `make check`, `make test`, `make smoke`, `make kb-check`, `make all-report`, `make all-report-fix-status`, `make resolver-report`, `make component-report`, `make status`, `make status-check`, `make summary-check`, `make coverage-snapshot`, `make refresh-artifacts`, or the matching `workspace:*` tasks

## Reporting features

- Every validator now emits `rule_results` with stable `rule_id`, `category`, `severity`, and `findings` data.
- Every report includes a `rule_summary` or `aggregate_rule_summary` grouped by domain, category, and severity.
- CLI filters let you narrow reported rules in the output.
- `--rule-id` lets you execute only specific registered rules.
- `--profile` lets you execute stable named bundles of rules such as `ci`, `status-only`, `resolver-only`, `component-governance`, `kb-only`, `workspace-only`, and `kb-cross-reference`.
- `--profile` lets you execute stable named bundles of rules such as `ci`, `status-only`, `resolver-only`, `component-governance`, `kb-only`, `workspace-only`, `kb-cross-reference`, and `kb-metadata`.
- Knowledge-base validation now also checks component index ↔ component doc parity for shared metadata like component identity, type, creation timestamp, compliance status, indexed file path coverage, dependency alignment, and technique traceability.
- Knowledge-base validation now also checks companion component docs against the required `ai_reference_format` fields declared in `core_reference.json`.
- Knowledge-base validation now also checks each companion component doc top-level field set against the governed JSON shape so unexpected metadata fields cannot silently accumulate.
- Knowledge-base validation now also enforces `auto_generated: true` for governed companion component docs so AI reference artifacts cannot drift into manual-state markers.
- Knowledge-base validation now also checks each companion component doc `test_coverage.targeted_test_file` path against the live workspace so governed test references cannot drift to missing files.
- Knowledge-base validation now also checks each companion component doc `test_coverage` field set so unexpected nested metadata cannot accumulate outside the governed verification shape.
- Knowledge-base validation now also checks each companion component doc `test_coverage.status` value against the governed status vocabulary so coverage metadata cannot drift to ad-hoc labels.
- Knowledge-base validation now also checks each companion component doc `test_coverage.status` value against the governed `component_type` so runtime-backed artifacts and Python modules cannot silently swap coverage-verification modes.
- Knowledge-base validation now also checks each companion component doc `interfaces` shape against the governed `component_type` so Python modules keep a callable API surface and governance artifacts keep explicit artifact/source-of-truth links.
- Knowledge-base validation now also checks each companion component doc `interfaces` value types so every documented interface surface remains a JSON list instead of drifting to scalar metadata.
- Knowledge-base validation now also checks each companion component doc `interfaces` entries so every documented interface surface remains a non-empty list of non-empty strings.
- Knowledge-base validation now also checks each companion component doc `performance_metrics` shape against the governed `component_type` so Python modules keep runtime-oriented metrics and governance artifacts keep generation/storage metrics.
- Knowledge-base validation now also checks each companion component doc `performance_metrics` value payload so governed metrics remain non-empty strings instead of blank placeholders.
- Knowledge-base validation now also checks each companion component doc `file_paths` entry against the live workspace so governed implementation and test path inventories cannot drift to missing files.
- Knowledge-base validation now also checks each companion component doc `dependencies` entry against the live workspace so governed dependency inventories cannot drift to missing paths.
- Knowledge-base validation now also checks companion component doc `interfaces.cli` entries against the supported `inf_work` command surface so documented CLI workflows cannot drift to unsupported subcommands.
- Knowledge-base validation now also checks companion component doc `interfaces.python_api` entries against symbols exported by the governed module so documented Python surfaces cannot drift to missing callables or package exports.
- Knowledge-base validation now also keeps companion component doc `notes` arrays non-empty and string-only so governed implementation context cannot decay into blank placeholders.
- Component governance now also validates `ai_docs/component_index.json` `dependents` lists against the live component dependency topology so reverse links cannot drift.
- Component governance now also validates `ai_docs/component_index.json` `documentation_path` values so every governed component entry keeps a non-empty companion-doc path.
- Component governance now also validates `ai_docs/component_index.json` `file_path` values so every governed component entry keeps a non-empty implementation path before companion-doc parity is evaluated.
- Component governance now also validates `ai_docs/component_index.json` `file_path` values for uniqueness so every governed component entry keeps a distinct implementation path before dependency-topology and coverage parity are evaluated.
- Component governance now also validates `ai_docs/component_index.json` `health_status` values so every governed component entry stays inside the healthy/degraded/failing vocabulary before aggregate status totals are evaluated.
- Component governance now also validates `ai_docs/component_index.json` `compliance_status` values so every governed component entry stays on the documented compliance contract before companion-doc metadata parity is evaluated.
- Component governance now also validates `ai_docs/component_index.json` `complexity_score` values so every governed component entry keeps a non-negative integer complexity rating.
- Component governance now also validates `ai_docs/component_index.json` `test_coverage_percentage` values so every governed component entry keeps an integer coverage percentage inside the inclusive `0..100` range before coverage parity is evaluated.
- Component governance now also validates `ai_docs/component_index.json` `creation_timestamp` and `last_modified_timestamp` values so every governed component entry keeps non-empty ISO-8601 UTC timestamps before timestamp parity is evaluated.
- Component governance now also validates `ai_docs/component_index.json` `component_name` values so every governed component entry keeps a non-empty human-readable name before companion-doc metadata parity is evaluated.
- Component governance now also validates `ai_docs/component_index.json` `component_name` values for uniqueness so every governed component entry keeps a distinct human-readable name across the inventory.
- Component governance now also validates `ai_docs/component_index.json` `component_type` values so every governed component entry stays within the governed component-type vocabulary before companion-doc metadata parity is evaluated.
- Component governance now also validates `ai_docs/component_index.json` `component_id` values so every governed component entry keeps a non-empty stable identifier before companion-doc metadata and dependency-topology parity are evaluated.
- Component governance now also validates `ai_docs/component_index.json` `component_id` values for uniqueness so every governed component entry keeps a distinct stable identifier before companion-doc joins and dependency-topology parity are evaluated.
- Component governance now also validates `ai_docs/component_index.json` `dependencies` lists so governed component dependency inventories remain lists of non-empty strings.
- Component governance now also validates `ai_docs/component_index.json` `dependencies` lists for duplicate entries so governed component dependency inventories remain unique string lists before companion-doc dependency parity is evaluated.
- Component governance now also validates `ai_docs/component_index.json` `related_techniques` lists so governed technique-traceability inventories remain lists of non-empty strings.
- Component governance now also validates `ai_docs/component_index.json` `dependents` lists as non-empty strings before reverse-topology parity is evaluated.
- Component governance now also validates `ai_docs/component_index.json` `known_issues` lists so governed issue inventories remain lists of non-empty strings while still allowing empty lists.
- Component governance now also validates `ai_docs/component_index.json` `performance_metrics` field sets so governed component entries keep the exact latency/memory metadata shape.
- Component governance now also validates `ai_docs/component_index.json` `performance_metrics` values so governed latency and memory metadata remains non-empty string content.
- Component governance now also validates `ai_docs/component_index.json` summary metadata so `metadata.total_components` and the aggregate `health_status` counts stay aligned with the live component inventory.
- Component governance now also validates `ai_docs/component_index.json` timestamp integrity so each component preserves `creation_timestamp <= last_modified_timestamp` and `metadata.last_updated` matches the latest component modification timestamp.
- Knowledge-base validation also checks `knowledge_base/kb_index.json` parity for last-updated freshness, aggregate counts, automation success metrics, constraint-compliance totals, and lookup indices derived from the canonical KB source files.
- Knowledge-base validation also checks direct source-file metadata counts in `techniques.json`, `bug_fixes.json`, `constraint_innovations.json`, `automation_patterns.json`, and `session_history.json`.
- Knowledge-base validation now also checks direct source-file freshness metadata so `metadata.last_updated`, `metadata.first_session`, and `metadata.last_session` stay aligned with the entries recorded in each KB source file.
- Knowledge-base validation now also checks governed Python component `test_coverage_percentage` values against the canonical `ai_docs/test_coverage_snapshot.json` artifact generated from `pytest-cov`.
- `status-check` exposes the status artifact validator directly, and `all` now includes the `status` domain in aggregate reports.
- `status-check` now also includes runtime-integrity rules that fail if the canonical explicit or inferred resolver examples stop resolving the bounded governance routes.
- `summary-check` exposes a dedicated validator for the generated `SYSTEM_SUMMARY.md` artifact.
- `status-check --fix` regenerates stale status artifacts before validating them.
- `summary-check --fix` refreshes the governed status outputs before validating the generated summary artifact.
- `remediation-plan` now selects between the supported remediation slices, `remediation-plan --intent intent.status.refresh_artifacts` triggers the explicit governed status-refresh capability, `remediation-plan --simulate` previews deterministic diffs for status-artifact and package-export remediations, and `remediation-plan --apply` executes the bounded slice with verification and rollback.
- `all --fix-status` applies that same status-artifact remediation before the combined aggregate report runs.
- Canonical status rendering now surfaces threshold-aware follow-up actions when governed components fall below the configured coverage minimum and includes the `coverage-snapshot` operator shortcut alongside the other governed task pairs.
- Canonical status generation now derives `ai_docs/system_status_snapshot.json:generated_at` from the freshest governed source artifacts instead of preserving a stale fixed timestamp.
- The `refresh-artifacts` one-shot workflow is now cataloged in `knowledge_base/automation_patterns.json` as `automation_refresh_artifacts_operator_surface_promotion`, so the governed KB records it as a reusable documentation automation pattern rather than an undocumented convenience command.
- `--fail-on` lets you decide which severity threshold should produce a non-zero exit code.

## Governed automation patterns

- `knowledge_base/automation_patterns.json`: canonical catalog of reusable governed automation patterns, including operator-surface promotions such as `automation_refresh_artifacts_operator_surface_promotion`.
- `knowledge_base/session_history.json`: chronological rollout record showing when governed automation and operator-surface changes were introduced and revalidated.

## Where to look first

- `README.md`: human-facing overview of commands, validation surfaces, and governed workflow entry points.
- `SYSTEM_STATUS.md`: latest derived operational snapshot for component health, KB metrics, operator shortcuts, and current governed status.
- `ai_docs/system_status_snapshot.json`: canonical JSON status source of truth that drives `SYSTEM_STATUS.md` and `SYSTEM_SUMMARY.md`.
- `ai_docs/component_index.json`: live registry of governed components, dependencies, coverage metadata, and companion-doc links.
- `knowledge_base/kb_index.json`: aggregate KB rollup for counts, freshness, lookup indices, and automation success metrics.

## Quick start

```bash
make bootstrap
.venv/bin/python -m pytest tests/test_core_reference.py tests/test_workspace_health.py tests/test_metadata_integrity.py tests/test_kb_integrity.py
.venv/bin/python -m pytest tests/test_rules.py tests/test_system_status.py tests/test_cli_entrypoints.py tests/test_resolver_registry.py
.venv/bin/python -m inf_work all . --pretty
.venv/bin/python -m inf_work workspace . --pretty
.venv/bin/python -m inf_work kb . --pretty
.venv/bin/python -m inf_work status . --pretty
.venv/bin/python -m inf_work status-check . --pretty
.venv/bin/python -m inf_work status-check . --pretty --fix
.venv/bin/python -m inf_work summary-check . --pretty
.venv/bin/python -m inf_work summary-check . --pretty --fix
.venv/bin/python -m inf_work refresh-artifacts . --pretty
.venv/bin/python -m inf_work resolve-path workspace_governance component_index knowledge_base_index --workspace-root . --pretty
.venv/bin/python -m inf_work infer-route workspace_governance knowledge_base_index --workspace-root . --pretty
.venv/bin/python -m inf_work all . --pretty --fix-status
.venv/bin/python -m inf_work all . --pretty --profile ci
.venv/bin/python -m inf_work all . --pretty --only-failures --domain-filter knowledge_base --category cross_reference
```

## One-command check

```bash
make bootstrap
make
make check
make test
make smoke
make kb-check
make all-report
make all-report-fix-status
make resolver-report
make component-report
make status
make status-check
make summary-check
make coverage-snapshot
make refresh-artifacts
```

Use `make bootstrap` once to create `.venv` and install the project. After that, use `.venv/bin/python -m inf_work all` or `make all-report` for a single combined JSON report, use `make all-report-fix-status` when the aggregate report should refresh stale status artifacts first, use `make resolver-report` for the runtime-integrity resolver profile only, or use `make component-report` for the component-governance profile only. Use `.venv/bin/python -m inf_work status` or `make status` to regenerate `SYSTEM_STATUS.md`, use `.venv/bin/python -m inf_work status-check` or `make status-check` to validate the status artifacts, use `.venv/bin/python -m inf_work summary-check` or `make summary-check` to validate `SYSTEM_SUMMARY.md`, use `.venv/bin/python -m inf_work coverage-snapshot` or `make coverage-snapshot` to refresh the canonical runtime-backed coverage artifact, or use `.venv/bin/python -m inf_work refresh-artifacts` or `make refresh-artifacts` to refresh coverage and immediately regenerate governed status outputs in one step. Add `--fix` to repair stale artifacts before validating them. `make check` now regenerates the canonical status artifacts before validating them. `make test` runs pytest only, `make smoke` runs `workspace`, and `make kb-check` runs `kb`. In VS Code, run `workspace: bootstrap` once, then use `workspace: all`, `workspace: all-fix-status`, `workspace: resolver-only`, `workspace: component-governance`, `workspace: status`, `workspace: status-check`, `workspace: summary-check`, `workspace: coverage-snapshot`, `workspace: refresh-artifacts`, `workspace: check`, `workspace: test`, `workspace: smoke`, or `workspace: kb-check`.

Resolver traversal examples:

```bash
.venv/bin/python -m inf_work resolve-path workspace_governance component_index knowledge_base_index --workspace-root . --pretty
.venv/bin/python -m inf_work infer-route workspace_governance knowledge_base_index --workspace-root . --pretty
```

Useful report filters:

```bash
.venv/bin/python -m inf_work all . --pretty --only-failures
.venv/bin/python -m inf_work all . --pretty --severity error
.venv/bin/python -m inf_work all . --pretty --domain-filter knowledge_base --category cross_reference
.venv/bin/python -m inf_work all . --pretty --domain-filter status
.venv/bin/python -m inf_work all . --pretty --fix-status --profile status-only
.venv/bin/python -m inf_work all . --pretty --profile status-only
.venv/bin/python -m inf_work all . --pretty --profile resolver-only
.venv/bin/python -m inf_work all . --pretty --profile component-governance
.venv/bin/python -m inf_work all . --pretty --profile kb-only
.venv/bin/python -m inf_work all . --pretty --profile kb-cross-reference
.venv/bin/python -m inf_work all . --pretty --rule-id knowledge_base.bug_fix_solution_technique_exists
.venv/bin/python -m inf_work all . --pretty --profile workspace-only --rule-id knowledge_base.bug_fix_solution_technique_exists
.venv/bin/python -m inf_work all . --pretty --rule-id knowledge_base.bug_fix_solution_technique_exists --fail-on critical
```

Execution policy notes:

- `--profile` expands to a deterministic set of rule ids and can be combined with repeated `--rule-id` flags.
- `--rule-id` changes which rules are executed, not just which results are shown.
- `--fail-on error` is the default exit threshold.
- `--fail-on critical` allows error-level findings to appear in the report while still exiting with code `0`.

## Linux note

If you do not want to install into `.venv`, the no-install fallback is:

```bash
PYTHONPATH="$(pwd)/src" /usr/bin/python3 -m inf_work all . --pretty
```
