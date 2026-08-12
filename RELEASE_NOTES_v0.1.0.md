# Invariant Arena v0.1.0 — Validated Prototype Release

## What Invariant Arena Is

Invariant Arena (Python package `inf-work`, version 0.1.0) is a deterministic workspace-governance engine. It validates a repository's code, configuration, documentation, tests, and generated metadata against a single explicit machine-readable contract (`core_reference.json` plus registered validation rules), and repairs supported classes of drift through bounded, evidence-producing remediation: every repair is compiled into a deterministic plan, can be simulated before any file changes, is verified after application, and is rolled back automatically if verification fails. It is not a general autonomous coding agent — remediation is limited to explicitly supported drift classes, invoked by an operator.

## What This Release Demonstrates

- **Explicit rule-based validation.** 65 registered rules across three domains (`workspace`, `knowledge_base`, `status`) check governed directory structure, component metadata, knowledge-base cross-references, coverage claims, and derived status documents against the live workspace. Each rule emits a stable `rule_id`, category, severity, and findings.
- **Governance of generated artifacts.** Human-facing documents (`SYSTEM_STATUS.md`, `SYSTEM_SUMMARY.md`) are derived from a canonical JSON snapshot and validated against it; hand edits are detected as failing rules.
- **Deterministic behavior.** Repeated validation runs over the same workspace state produce byte-identical reports (verified by hashing consecutive runs during release preparation).
- **Bounded remediation with evidence.** Detected drift in two supported slices (status-artifact regeneration, package-export synchronization) is compiled into a deterministic plan carrying provenance (triggering rule IDs), a verification contract, and a rollback contract.
- **Simulation before mutation.** `remediation-plan --simulate` predicts exactly which files would change and which would not, with `workspace_mutation: false` — no files are touched until `--apply`.
- **Verification and rollback after mutation.** `--apply` re-validates the affected rules after writing; on verification failure or exception, the pre-remediation artifact state is restored (asserted end-to-end in the test suite, including a subprocess test that forces a verification failure and checks `rollback_performed: true` with the restored paths).
- **Deterministic resolver traversal.** A bounded three-tile resolver graph (core reference → component index → knowledge-base index) supports explicit and inferred routes and doubles as a runtime-integrity check.
- **Structured evidence.** Coverage metadata in the component registry is validated against a `pytest-cov`-generated snapshot; all canonical specification and knowledge-base files are valid JSON with cross-references checked on every run.

## Validation Evidence

All items marked **fresh** were reproduced during this release-preparation task; items marked **artifact** come from checked-in dated files.

| Claim | Value | Basis |
| ----- | ----- | ----- |
| Full test suite passes | 412 passed, 0 failed (11 test files) | **fresh** — `python -m pytest`, run twice (plain and under `pytest-cov`) |
| Governance contract size | 65 rules, 3 domains; 12 registered components | **fresh** — aggregate report + `ai_docs/component_index.json` |
| Aggregate report fully compliant | 65/65 rules passed, 0 findings | **fresh** — reproduced in a temporary clone after first-run `--fix-status` (see Limitations for why a fresh checkout starts with 2 findings) |
| End-to-end remediation | hand-edited drift in `SYSTEM_STATUS.md` → detected (exit 1) → plan `remediation_plan_status_artifact_regeneration` → simulation predicted 1 update + 2 no-ops → applied → post-apply validation exit 0 | **fresh** — executed in a temporary clone, not the release tree |
| Rollback on verification failure | pre-remediation state restored, `rollback_performed: true` | **fresh** — asserted by the E2E tests inside the 412-test run ([tests/test_remediation_e2e.py](tests/test_remediation_e2e.py)) |
| Deterministic reports | two consecutive aggregate runs byte-identical (equal SHA-256) | **fresh** |
| Line coverage | 100% on 10 of 11 modules; 92.9% on `system_status.py`; 98.1% overall | **fresh** — new `pytest-cov` run, matching the checked-in snapshot [ai_docs/test_coverage_snapshot.json](ai_docs/test_coverage_snapshot.json) (dated 2026-07-27) |
| Resolver traversal | inferred route completes deterministically (`complete: true`, 1 hop) | **fresh** |
| Canonical JSON validity | 12 specification/KB files parse and cross-validate | **fresh** |
| Mutation testing | no usable score — checked-in snapshot records 0 mutants | **artifact** — [ai_docs/mutation_test_snapshot.json](ai_docs/mutation_test_snapshot.json); treated as unmeasured |

No benchmark performance numbers are claimed: the benchmark harness is implemented and tested, but no result artifact is checked in.

## Reproducing the Core Result

From a fresh clone (Python 3.11+):

```bash
# 1. Setup (build/ and config/ are required by the contract but not git-tracked)
mkdir -p build config
python -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"

# 2. Tests
python -m pytest

# 3. Canonical validation (first run needs --fix-status to localize the status snapshot)
python -m inf_work all . --pretty --fix-status
python -m inf_work all . --pretty            # subsequent runs: 65/65, compliant

# 4. Bounded remediation demonstration (simulate is read-only)
python -m inf_work remediation-plan . --pretty --simulate
```

To see the full drift-repair journey, hand-edit a value in `SYSTEM_STATUS.md`, then run `status-check` (detects, exit 1), `remediation-plan --simulate` (predicts the exact diff), and `remediation-plan --apply` (repairs, verifies, reports rollback status). The complete command surface is in [docs/COMMAND_REFERENCE.md](docs/COMMAND_REFERENCE.md).

## Scope and Limitations

- **Remediation is intentionally bounded.** Only two drift slices are repairable (status-artifact regeneration, package-export synchronization); all other findings are report-only. This is not arbitrary autonomous code modification.
- **Passing validation is not formal verification.** Rules check declared metadata against observable workspace state, not program semantics; evidence applies to the included 65-rule set, this repository's own structure, and the tested workflows.
- **The rule set governs this repository specifically.** The contract in `core_reference.json` describes this workspace; the engine is not a drop-in governance tool for arbitrary repositories.
- **Fresh checkouts start non-compliant by design.** The status snapshot embeds the absolute path of the checkout that generated it, and two contract-required directories (`build/`, `config/`) are not git-tracked. A fresh clone reports findings until `mkdir -p build config` and one `--fix-status` run; this is detected-and-repairable drift, not silent breakage.
- **Running the full test suite regenerates status artifacts in place.** Subprocess CLI tests execute `inf_work status` against the checkout, so `git status` may show path-only churn in `SYSTEM_STATUS.md` and the snapshot afterward. Review or discard those diffs before committing.
- **Mutation-testing quality is unmeasured.** The `mutmut` pilot is configured for four modules but the checked-in snapshot records zero mutants (and embeds a stale development-machine path); no mutation score is claimed.
- **Research prototype, not production infrastructure.** The package is not published to a package index; installation is editable-only from a checkout.

## Development Provenance

This project was developed through a human-directed, AI-assisted workflow. Structured development records ([knowledge_base/session_history.json](knowledge_base/session_history.json), 58 sessions, plus archived working notes under `ai_docs/backups/`) establish provenance, but they are not the evidence base for this release: the current code, the 412-test suite, and the checked-in and freshly reproduced artifacts cited above are authoritative.
