# Make canonical status artifacts checkout-independent and keep test runs working-tree clean

**Labels:** maintenance, portability, governance
**Milestone:** post-v0.1.0

## Summary

Three related portability/release-polish limitations were identified during `v0.1.0` release validation. They are documented in `RELEASE_NOTES_v0.1.0.md`, are intentionally deferred from `v0.1.0` to avoid a broad status-system rewrite immediately before the first release, and do **not** invalidate the release evidence: the 65-rule validation, bounded remediation, rollback-on-failed-verification, deterministic repeated reporting, and 412-test results all hold as validated.

## Problems

1. **`build/` and `config/` are contract-required but absent from a fresh clone.**
   `core_reference.json` requires both directories (`workspace.required_directories_present`), but they contain no tracked files, so Git does not materialize them on clone. A fresh clone fails the rule until `mkdir -p build config` is run manually.

2. **Canonical status artifacts embed checkout-specific absolute path state.**
   `ai_docs/system_status_snapshot.json` (and the derived `SYSTEM_STATUS.md`) record the absolute workspace root and interpreter path of the checkout that generated them (e.g. `workspace_root`, `test_suite_summary.command`, `resolver_capabilities.*.workspace_root`). The staleness rules `status.snapshot_matches_workspace` / `status.summary_matches_workspace` compare regenerated content against the stored artifact, so cloning to a new location is reported as drift and requires one `--fix-status` (or `status`) run to localize the tracked artifacts.

3. **Some tests regenerate tracked status artifacts in place.**
   Subprocess CLI tests in `tests/test_rules.py` and direct `write_system_status_outputs(WORKSPACE_ROOT)` calls in `tests/test_system_status.py` (and one in `tests/test_kb_integrity.py`) run status regeneration against the real checkout. On a machine whose path differs from the artifact's recorded generation root, `python -m pytest` leaves path-only churn in `SYSTEM_STATUS.md` and `ai_docs/system_status_snapshot.json`.

All three are detected-and-repairable conditions, not silent breakage, but they prevent the ideal first-run journey: `clone → install → tests → validation → 65/65 compliant → clean working tree`.

## Proposed direction (not prescriptive)

- Track placeholder files (e.g. `.gitkeep`) in `build/` and `config/`, if consistent with governance rules.
- Make canonical status content location-independent (repository-relative paths, portable command strings), or exclude machine-local provenance fields from canonical equality the way `_normalize_snapshot_payload` already excludes `command` and mutation command fields — without hiding genuine drift.
- Point the artifact-writing tests at temporary governed workspace copies (the pattern already exists in `tests/test_remediation_e2e.py::_copy_governed_workspace`) instead of the active checkout.

## Acceptance criteria

- [ ] Fresh clone → install → `python -m pytest` → `python -m inf_work all . --pretty` succeeds with 65/65 rules passing and zero findings, without manual repair (`mkdir` or `--fix-status`).
- [ ] Canonical status artifacts contain no checkout-specific absolute paths that participate in contract compliance.
- [ ] `python -m pytest` leaves `git status --porcelain` empty on a clean checkout.
- [ ] The 65-rule contract, three governance domains, and the existing two-slice remediation scope remain unchanged.
- [ ] Simulation-before-mutation, post-apply verification, rollback-on-failed-verification, and byte-identical repeated reporting remain intact.
