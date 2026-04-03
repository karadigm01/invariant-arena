# System Status

- **Generated At**: 2026-04-03T16:56:41Z
- **Workspace Root**: `/home/j/Desktop/inf.work`
- **Canonical Data**: `ai_docs/system_status_snapshot.json`
- **Derived Artifact**: `SYSTEM_STATUS.md`

## 1. Component Health
- **Workspace Health Checker**: healthy, 100% coverage, I1_I2_I3_I4_compliant; 2 dependencies, 4 dependents
- **Core Reference View**: healthy, 100% coverage, I1_I2_I3_I4_compliant; 1 dependency, 2 dependents
- **Validation Rule Engine**: healthy, 100% coverage, I1_I2_I3_I4_compliant; 2 dependencies, 5 dependents
- **Knowledge Base Cross-Reference Validator**: healthy, 100% coverage, I1_I2_I3_I4_compliant; 9 dependencies, 6 dependents
- **System Status Generator**: healthy, 100% coverage, I1_I2_I3_I4_compliant; 12 dependencies, 4 dependents
- **Package Public API Surface**: healthy, 100% coverage, I1_I2_I3_I4_compliant; 7 dependencies, 0 dependents
- **Unified CLI Entry Point**: healthy, 100% coverage, I1_I2_I3_I4_compliant; 6 dependencies, 1 dependent
- **KB Check Compatibility Wrapper**: healthy, 100% coverage, I1_I2_I3_I4_compliant; 2 dependencies, 0 dependents
- **Remediation Plan Compiler**: healthy, 100% coverage, I1_I2_I3_I4_compliant; 3 dependencies, 2 dependents
- **Resolver Capability Registry**: healthy, 100% coverage, I1_I2_I3_I4_compliant; 2 dependencies, 3 dependents
- **System Status Governance Artifact**: healthy, 100% coverage, I1_I2_I3_I4_compliant; 2 dependencies, 0 dependents

## 2. Test Inventory
- **Collected Tests**: 281
- **Collection Summary**: 281 collected
- **Pass Rate**: 1.0
- **Pending/Skipped**: 0
- **src/inf_work/__init__.py**: 100% (tracked)
- **src/inf_work/__main__.py**: 100% (tracked)
- **src/inf_work/core_reference.py**: 100% (tracked)
- **src/inf_work/kb_check.py**: 100% (tracked)
- **src/inf_work/kb_integrity.py**: 100% (tracked)
- **src/inf_work/remediation.py**: 100% (tracked)
- **src/inf_work/resolver_registry.py**: 100% (tracked)
- **src/inf_work/rules.py**: 100% (tracked)
- **src/inf_work/system_status.py**: 100% (tracked)
- **src/inf_work/workspace_health.py**: 100% (tracked)

## 3. Knowledge Base Metrics
- **Technique Count**: 9 (latest: Deterministic profile surface promotion)
- **Innovation Count**: 2 (latest: innovation_bounded_resolver_multi_hop_enablement)
- **Bug Fixes**: 1
- **Automation Patterns**: 59
- **Last KB Update**: 2026-04-03T00:00:00Z

## 4. Recent Governance Highlights
- **Session Count**: 57
- **KB Highlights**: session `session_20260403_status_markdown_shared_block_consolidation (2026-04-03)`; automation `Status markdown shared-block consolidation (2026-04-03)`; technique `Deterministic profile surface promotion (2026-03-31)`; bug fix `bugfix_core_reference_malformed_schema_arrays (2026-03-28)`
- **Why It Matters**: Latest governance work focused on consolidating shared recent-governance and navigation markdown blocks so `SYSTEM_STATUS.md` and `SYSTEM_SUMMARY.md` stay aligned without losing document-specific wording.
- **Latest Summary**: Consolidating shared recent-governance and navigation markdown blocks so `SYSTEM_STATUS.md` and `SYSTEM_SUMMARY.md` stay aligned without losing document-specific wording.
- **Outcome**: `SYSTEM_STATUS.md` and `SYSTEM_SUMMARY.md` now share a single source of truth for the recent-governance and navigation blocks instead of duplicating those line lists inline.
- **Outcome**: The shared helpers keep the intended wording and punctuation differences between the status and summary documents while reducing future drift risk.

## 5. Schema/Contract Integrity
- **core_reference**: version 2.0.0
- **behavioral_directives**: version 2.0.0
- **component_index**: version 2.0.0
- **techniques**: version 2.0.0
- **bug_fixes**: version 2.0.0
- **constraint_innovations**: version 2.0.0
- **automation_patterns**: version 2.0.0
- **kb_index**: version 2.0.0
- **Cross-Reference Validation**: healthy
- **Workspace Coherence**: healthy
- **Dangling References**: 0 files, 0 docs

## 6. Resolver Capabilities
- **Single-Hop**: True
- **Multi-Hop Explicit**: True
- **Multi-Hop Inferred**: True
- **Registered Tiles**: 3 registered tiles
- **Pressure Telemetry**: configured
- **Explicit Route Example**: workspace_governance -> component_index -> knowledge_base_index
- **Inferred Route Example**: workspace_governance -> knowledge_base_index

## 7. Known Gaps & Technical Debt
- **0% Coverage Modules**: none
- **Missing Automation Patterns**: none
- **TODO/FIXME**: none detected outside archival backups
- **Planned Features**: none recorded

## 8. Architectural Invariant Compliance
- **I1**: compliant — All registered components declare `I1_I2_I3_I4_compliant` in `component_index.json`.
- **I2**: compliant — All registered components declare bounded memory profiles and no dynamic allocation subsystems are present.
- **I3**: compliant — Workspace validation checks governed directories from `core_reference.json`.
- **I4**: compliant — JSON-first component docs and knowledge-base references validate successfully; `SYSTEM_STATUS.md` is derived from structured status data.

## 9. Operator Shortcuts
- **Aggregate report**: `make all-report` | VS Code task: `workspace: all` — Run the full aggregate governance report without remediation.
- **Aggregate report with status remediation**: `make all-report-fix-status` | VS Code task: `workspace: all-fix-status` — Refresh stale status artifacts before running the aggregate governance report.
- **Resolver integrity report**: `make resolver-report` | VS Code task: `workspace: resolver-only` — Run only the runtime-integrity resolver rules through the aggregate governance surface.
- **Component governance report**: `make component-report` | VS Code task: `workspace: component-governance` — Run only the component-governance knowledge-base rules for technique traceability and component-doc parity.
- **Status regeneration**: `make status` | VS Code task: `workspace: status` — Regenerate `ai_docs/system_status_snapshot.json` and `SYSTEM_STATUS.md`.
- **Status validation**: `make status-check` | VS Code task: `workspace: status-check` — Validate that the canonical status artifacts match the current workspace state.
- **Summary validation**: `make summary-check` | VS Code task: `workspace: summary-check` — Validate that `SYSTEM_SUMMARY.md` matches the current governed workspace state.
- **Coverage snapshot refresh**: `make coverage-snapshot` | VS Code task: `workspace: coverage-snapshot` — Refresh `ai_docs/test_coverage_snapshot.json` from a real `pytest-cov` run before reviewing governed component coverage.
- **Artifact refresh**: `make refresh-artifacts` | VS Code task: `workspace: refresh-artifacts` — Refresh the governed coverage snapshot and regenerate the canonical status artifacts in one deterministic pass.

## Where to look first
- **Guide**: `README.md` summarizes commands, validation surfaces, and governed workflow entry points.
- **Structured Snapshot**: `ai_docs/system_status_snapshot.json` is the canonical status source of truth.
- **Summary View**: `SYSTEM_SUMMARY.md` provides the condensed human-facing overview of the governed workspace.
- **Component Registry**: `ai_docs/component_index.json` tracks governed components, dependencies, coverage metadata, and companion docs.
- **KB Rollup**: `knowledge_base/kb_index.json` aggregates KB counts, freshness, lookup indices, and automation metrics.

## 10. Next Recommended Actions
- **Actions**: no immediate follow-up recorded
