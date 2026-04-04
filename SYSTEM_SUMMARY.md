# System Summary

**Last Updated:** 2026-04-03  
**Total Components:** 12  
**System Health:** Healthy  
**Test Inventory:** 309 collected

## Architecture

- **Core Reference View:** `src/inf_work/core_reference.py` centralizes `core_reference.json` loading and governed-directory extraction.
- **Validation Rule Engine:** `src/inf_work/rules.py` registers deterministic rules and standardized rule results for all validators.
- **KB Integrity Validator:** `src/inf_work/kb_integrity.py` validates technique and component cross references across `knowledge_base/` and `ai_docs/`.
- **Workspace Health Checker:** `src/inf_work/workspace_health.py` validates governed directories from `core_reference.json`.
- **System Status Generator:** `src/inf_work/system_status.py` generates the structured system snapshot, derives `SYSTEM_STATUS.md`, captures a collection-only test inventory, and validates both artifacts through status-domain rules.
- **System Status Artifact:** `SYSTEM_STATUS.md` is the human-facing governance snapshot derived from `ai_docs/system_status_snapshot.json`.
- **CLI Entry Point:** `src/inf_work/__main__.py` exposes unified `all`, `workspace`, `kb`, `status`, `status-check`, `summary-check`, and `remediation-plan` commands with rule filtering, named rule profiles, `rule_id` selection, severity-based exit policy, grouped summaries, targeted summary remediation, `status-check --fix` remediation, aggregate `all --fix-status` repair support for stale status artifacts, explicit governed status-refresh intent routing, and bounded remediation slices for status-artifact drift plus package-export source synchronization.
- **CI Check:** `.github/workflows/validator-check.yml` runs focused tests, metadata integrity checks, validator smoke checks, and KB cross-reference smoke checks.
- **Local Check Shortcut:** `Makefile` and `.vscode/tasks.json` support `make bootstrap`, `make`, `make check`, `make test`, `make smoke`, `make kb-check`, `make all-report`, `make all-report-fix-status`, `make resolver-report`, `make component-report`, `make status`, `make status-check`, `make summary-check`, `make coverage-snapshot`, `make refresh-artifacts`, and the matching `workspace:*` tasks using `.venv`; `make check` regenerates then validates the canonical status artifacts.
- **Operator Shortcut Pairs:** `make all-report` ↔ `workspace: all`; `make all-report-fix-status` ↔ `workspace: all-fix-status`; `make resolver-report` ↔ `workspace: resolver-only`; `make component-report` ↔ `workspace: component-governance`; `make status` ↔ `workspace: status`; `make status-check` ↔ `workspace: status-check`; `make summary-check` ↔ `workspace: summary-check`; `make coverage-snapshot` ↔ `workspace: coverage-snapshot`; `make refresh-artifacts` ↔ `workspace: refresh-artifacts`.

## Where to look first

- **Guide:** `README.md` summarizes commands, validation surfaces, and governed workflow entry points.
- **Live Snapshot:** `SYSTEM_STATUS.md` shows the latest derived operational status for components, KB metrics, and operator shortcuts.
- **Canonical Status JSON:** `ai_docs/system_status_snapshot.json` is the structured source of truth for derived status artifacts.
- **Component Registry:** `ai_docs/component_index.json` tracks governed components, dependencies, coverage metadata, and companion docs.
- **KB Rollup:** `knowledge_base/kb_index.json` aggregates KB counts, freshness, lookup indices, and automation metrics.

## Constraint Compliance

- **I1 (Determinism):** ✓ Health checks derive only from workspace state and core JSON.
- **I2 (Memory Isolation):** ✓ No dynamic allocation beyond bounded in-process data structures.  
- **I3 (Workspace Coherence):** ✓ Structure initialized
- **I4 (Documentation Purity):** ✓ JSON-first component documentation active

## Knowledge Base Status

- **Techniques:** 9
- **Bug Fixes:** 1
- **Innovations:** 2
- **Automation Patterns:** 59

## Recent Governance Highlights

- **Session Count:** 57
- **KB Highlights:** session `session_20260403_status_markdown_shared_block_consolidation (2026-04-03)`; automation `Status markdown shared-block consolidation (2026-04-03)`; technique `Deterministic profile surface promotion (2026-03-31)`; bug fix `bugfix_core_reference_malformed_schema_arrays (2026-03-28)`
- **Why It Matters:** Latest governance work focused on consolidating shared recent-governance and navigation markdown blocks so `SYSTEM_STATUS.md` and `SYSTEM_SUMMARY.md` stay aligned without losing document-specific wording.
- **Latest Summary:** Consolidating shared recent-governance and navigation markdown blocks so `SYSTEM_STATUS.md` and `SYSTEM_SUMMARY.md` stay aligned without losing document-specific wording.

The system now includes 12 documented components and artifacts, 9 catalogued techniques, 1 recorded bug fix pattern, 59 automation patterns, a canonical structured status snapshot with self-validation across 6 status rules, and targeted plus aggregate status remediation flows.
