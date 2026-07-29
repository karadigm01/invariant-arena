# Invariant Arena

A deterministic workspace-governance engine that validates a repository's code, configuration, documentation, tests, and generated metadata against a single machine-readable contract — and repairs two currently supported classes of drift through bounded, verified, rollback-capable remediation.

`inf.work` treats a repository as a governed system: `core_reference.json` defines the architectural contract, JSON documents in `ai_docs/` and `knowledge_base/` describe every component and recorded finding, and human-facing documents such as `SYSTEM_STATUS.md` are derived from that structured data rather than written by hand. A Python package (`inf_work`) enforces the contract through 65 registered validation rules, generates and validates the derived artifacts, and compiles deterministic remediation plans when drift is detected. The repository governs itself against its own declared 65-rule contract.

## Project Status

| Field              | Value |
| ------------------ | ----- |
| Project type       | Validation engine / workspace-governance CLI |
| Maturity           | Validated Prototype |
| Primary language   | Python (3.11+) |
| Deterministic core | Yes |
| Primary validation | 412-test pytest suite and a 65-rule aggregate governance report, both re-run during this documentation pass |
| License            | MIT |

Test and rule counts above come from a test run and an aggregate report executed while this README was written. Coverage figures cited later come from `ai_docs/test_coverage_snapshot.json`, regenerated from a real `pytest-cov` run during the same pass.

**What `compliant: true` means.** A compliant report means the workspace satisfies the 65 currently registered governance rules. It does not certify properties outside that rule set — for example artifact-path portability across machines, usable mutation-testing evidence, packaging or distribution readiness, or anything else no rule currently encodes. Known issues that are not represented as failing rules are listed under Known Limitations.

## Purpose

Complex workspaces drift: code changes but the documentation index does not; a test file is renamed but metadata still points to the old path; a status report claims coverage numbers no runtime ever produced. `inf.work` addresses that problem by making drift detectable and, for supported cases, mechanically repairable:

- Every fact represented by the current governance model — component inventory, dependencies, coverage metadata, knowledge-base cross references, and status snapshots — lives in canonical JSON.
- Validators check those facts against the live workspace on every run.
- Derived human-facing documents are regenerated from the JSON, never edited directly.
- Detected drift in supported slices can be simulated, applied, verified, and rolled back.

## Core Capabilities

- **Deterministic rule execution:** Runs 65 registered validation rules across three domains (`workspace`, `knowledge_base`, `status`), each emitting stable `rule_id`, `category`, `severity`, and `findings` data, with grouped summaries and severity-based exit codes.
- **Cross-reference integrity:** Validates knowledge-base and component-index metadata against the live workspace — file paths, dependencies, interfaces, coverage claims, timestamps, and technique traceability cannot silently point at things that no longer exist.
- **Derived status artifacts:** Generates `SYSTEM_STATUS.md` and `SYSTEM_SUMMARY.md` from a canonical JSON snapshot, then validates that the derived documents still match the workspace state.
- **Bounded remediation:** Compiles deterministic remediation plans for supported drift (status-artifact regeneration, package-export synchronization), previews predicted diffs with `--simulate`, and applies changes with verification and automatic rollback on failure.
- **Deterministic resolver traversal:** Resolves explicit and inferred routes across a bounded graph of governed artifact "tiles" (core reference → component index → knowledge-base index), used as a runtime-integrity check.
- **Evidence-backed quality metadata:** Coverage percentages in the component registry are validated against a `pytest-cov`-generated snapshot. A bounded `mutmut` mutation-testing pilot and an operator-workflow benchmark harness are implemented as additional quality surfaces, although neither currently provides a publishable result.

## How It Works

Validation, remediation, and artifact generation are three distinct, explicitly invoked flows:

```text
validation (all / workspace / kb / status-check)
  canonical contract + live workspace state
  → execute registered validators (65 rules)
  → findings + grouped summaries + compliance result

remediation (remediation-plan, all --fix-status)
  supported drift finding
  → compile deterministic plan
  → simulate predicted diffs (--simulate)
  → apply (--apply) → verify → rollback on verification failure

artifact generation (status / coverage-snapshot / refresh-artifacts)
  explicit regeneration command
  → rebuild canonical JSON snapshot + derived markdown
  → validate derived state
```

Validation never mutates the workspace; regeneration and remediation happen only through the explicit commands above.

| Layer | Responsibility |
| ----- | -------------- |
| `core_reference.py` | Loads `core_reference.json` and normalizes governed directory metadata |
| `rules.py` | Rule registry, profiles, filtering, severity policy, result serialization |
| `workspace_health.py` | Validates governed directories against the core reference |
| `kb_integrity.py` | Knowledge-base and component-index cross-reference validation |
| `system_status.py` | Canonical status snapshot generation, markdown derivation, status-domain rules |
| `remediation.py` | Plan compilation, dry-run simulation, bounded apply with verification and rollback |
| `resolver_registry.py` | Single-hop tiles, bounded explicit and inferred multi-hop traversal |
| `benchmark.py` | Operator-workflow benchmark against temporary workspace copies |
| `__main__.py` | Unified CLI (`all`, `workspace`, `kb`, `status`, `status-check`, `remediation-plan`, …) |

## Evidence

| Claim | Evidence | Reproduce or inspect |
| ----- | -------- | -------------------- |
| The full test suite passes (412 tests) | Test runs during this documentation pass, including one in a fresh venv with no inherited environment | `python -m pytest` |
| The aggregate governance report passes all 65 rules with zero findings | Fresh-environment first-run repair followed by a clean 65-rule validation (`compliant: true`) | `python -m inf_work all . --pretty --fix-status`, then `python -m inf_work all . --pretty` on subsequent runs |
| Hand-edited drift in a derived artifact is detected, planned, simulated, applied, and verified | Remediation journey executed in a disposable checkout during this pass (shown under Example) | `python -m inf_work remediation-plan . --pretty --simulate` |
| Inferred resolver routes complete deterministically across the governed tile graph | Current CLI run | `python -m inf_work infer-route workspace_governance knowledge_base_index --workspace-root . --pretty` |
| Remediation planning is side-effect-free and reports when no drift exists | Current CLI run (`plan_only: true`, empty operations on a compliant workspace) | `python -m inf_work remediation-plan . --pretty` |
| Line coverage is 100% for 10 of 11 modules (93% for `system_status.py`) | Coverage snapshot regenerated from `pytest-cov` during this pass | `ai_docs/test_coverage_snapshot.json` |
| End-to-end operator journeys (subprocess CLI remediation, rollback) are exercised | Test suite covers them; included in the 412-test run | `tests/test_remediation_e2e.py`, `tests/test_benchmark.py` |
| CI runs tests, smoke checks, status generation/validation, and the aggregate report | Workflow definition | `.github/workflows/validator-check.yml` |

### Current Results

| Metric | Result | Source |
| ------ | -----: | ------ |
| Tests | `412 passed` | Test runs during this documentation pass (repo checkout and fresh clean-environment install) |
| Governance rules | `65 passed, 0 findings` | `all` report run during this documentation pass |
| Line coverage | `100%` (10/11 modules), `93%` (`system_status.py`) | `ai_docs/test_coverage_snapshot.json`, regenerated during this pass |
| Mutation score | No usable current result | See Known Limitations |

The mutation-testing pilot is implemented and configured, but its checked-in snapshot (`ai_docs/mutation_test_snapshot.json`) records zero mutants — no meaningful score has been captured. Treat mutation quality as unmeasured until the pilot is re-run and triaged.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"

# Validate
python -m pytest

# Run the canonical workflow: the aggregate governance report
python -m inf_work all . --pretty --fix-status
```

This exact sequence was executed in a fresh virtual environment with no inherited configuration while this README was written (412 tests passed; report compliant). `--fix-status` matters on the first run: the checked-in status snapshot records the absolute path of the checkout that generated it, so on a freshly cloned copy the governance report correctly flags it as stale and `--fix-status` regenerates it for your checkout. After that, `python -m inf_work all . --pretty` suffices.

Equivalent Make shortcuts: `make bootstrap` once, then `make check` (tests + smoke checks + status regeneration and validation) or `make all-report-fix-status`.

Without installing, a no-install fallback works from the repository root:

```bash
PYTHONPATH="$(pwd)/src" python3 -m inf_work all . --pretty --fix-status
```

`--fix-status` may be omitted after the checkout-specific snapshot has been regenerated.

## Usage

### Run the aggregate governance report

```bash
python -m inf_work all . --pretty
python -m inf_work all . --pretty --only-failures
python -m inf_work all . --pretty --profile resolver-only
```

`--profile`, `--rule-id`, `--domain-filter`, `--category`, `--severity`, and `--fail-on` select and filter rules; see [docs/COMMAND_REFERENCE.md](docs/COMMAND_REFERENCE.md).

### Regenerate and validate status artifacts

```bash
python -m inf_work status . --pretty         # regenerate snapshot + SYSTEM_STATUS.md
python -m inf_work status-check . --pretty   # validate; add --fix to repair stale artifacts
python -m inf_work summary-check . --pretty  # validate SYSTEM_SUMMARY.md
```

### Plan, simulate, and apply a remediation

```bash
python -m inf_work remediation-plan . --pretty              # compile plan (no mutation)
python -m inf_work remediation-plan . --pretty --simulate   # preview predicted diffs
python -m inf_work remediation-plan . --pretty --apply      # apply with verify + rollback
```

### Refresh evidence artifacts

```bash
python -m inf_work coverage-snapshot . --pretty    # regenerate coverage snapshot from pytest-cov
python -m inf_work refresh-artifacts . --pretty    # coverage snapshot + status regeneration
python -m inf_work benchmark . --pretty            # operator-workflow benchmark pack
```

### Traverse the resolver graph

```bash
python -m inf_work resolve-path workspace_governance component_index knowledge_base_index --workspace-root . --pretty
python -m inf_work infer-route workspace_governance knowledge_base_index --workspace-root . --pretty
```

The complete command surface — all subcommands, filters, Make targets, VS Code tasks, and the mutation-testing workflow — is documented in [docs/COMMAND_REFERENCE.md](docs/COMMAND_REFERENCE.md).

## Example

### A full remediation journey

The sequence below was executed in a disposable copy of this repository while this README was written. A supported defect is introduced by hand-editing the derived `SYSTEM_STATUS.md` (changing the collected-test count from `412` to `999`), then detected, planned, simulated, applied, and verified. Output is excerpted from the real runs.

**1. Detect.** `python -m inf_work status-check .` exits `1` with a failing rule:

```json
{
  "rule_id": "status.markdown_matches_snapshot",
  "message": "Derived SYSTEM_STATUS.md does not match the canonical structured snapshot.",
  "source_file": "SYSTEM_STATUS.md"
}
```

**2. Plan.** `python -m inf_work remediation-plan .` compiles a deterministic plan without touching any file:

```json
{
  "plan_available": true,
  "plan_id": "remediation_plan_status_artifact_regeneration",
  "provenance": { "trigger_rule_ids": ["status.markdown_matches_snapshot"] },
  "affected_paths": ["ai_docs/system_status_snapshot.json", "SYSTEM_STATUS.md", "SYSTEM_SUMMARY.md"],
  "operations": [
    { "operation_id": "regenerate_status_outputs" },
    { "operation_id": "validate_status_artifacts" },
    { "operation_id": "validate_system_summary" }
  ]
}
```

**3. Simulate.** `remediation-plan . --simulate` predicts exactly what would change — the two clean artifacts report `"change_type": "noop"`, and the drifted one shows a unified diff:

```text
SYSTEM_STATUS.md | change_type: update | diff lines: 11
  --- a/SYSTEM_STATUS.md
  +++ b/SYSTEM_STATUS.md
  -- **Collected Tests**: 999
  +- **Collected Tests**: 412
```

**4. Apply and verify.** `remediation-plan . --apply` executes the slice, verifies, and reports `"applied": true, "rollback_performed": false`. A follow-up `status-check` exits `0`. If post-apply verification had failed, the pre-apply artifact state would have been restored.

### Deterministic resolver traversal

A second, smaller surface: asking the resolver to infer a route between two governed artifacts returns a deterministic traversal payload (output from a real run; `workspace_root` reflects the local checkout and is elided here):

```bash
python -m inf_work infer-route workspace_governance knowledge_base_index --workspace-root . --pretty
```

```json
{
  "complete": true,
  "failure_reason": null,
  "requested_path": ["workspace_governance", "knowledge_base_index"],
  "resolved_steps": [
    {
      "available": true,
      "inference_mode": "single_hop",
      "target_path": "core_reference.json",
      "tile_id": "workspace_governance",
      "title": "Workspace Governance"
    },
    {
      "available": true,
      "inference_mode": "single_hop",
      "target_path": "knowledge_base/kb_index.json",
      "tile_id": "knowledge_base_index",
      "title": "Knowledge Base Index"
    }
  ],
  "total_hops": 1,
  "traversal_mode": "inferred",
  "workspace_root": "<repository root>"
}
```

The same route is validated on every `status-check` run as a runtime-integrity rule: if the governed artifacts stop resolving, the status report fails.

## Repository Map

| Path | Purpose |
| ---- | ------- |
| `src/inf_work/` | Core implementation (validators, rules, status, remediation, resolver, benchmark, CLI) |
| `tests/` | Automated validation (412 tests across 11 files) |
| `core_reference.json` | Governed architectural contract and directory schema |
| `behavioral_directives.json` | Behavioral protocol definitions consumed by the governance system |
| `ai_docs/` | Machine-readable component docs, component index, coverage/mutation/status snapshots |
| `knowledge_base/` | Structured implementation history: techniques, bug fixes, innovations, automation patterns, sessions |
| `build/` | Generated coverage reports and workspace backups |
| `docs/` | Detailed command reference and validation-rule documentation |
| `mutants/` | `mutmut` working directory for the mutation-testing pilot |
| `.github/workflows/` | CI workflow (`validator-check.yml`) |
| `Makefile` | Local operator shortcuts (`make bootstrap`, `make check`, `make all-report`, …) |

## Scope and Limitations

### Supported

- Deterministic validation of this repository's governed structure, metadata, cross references, and derived status artifacts (65 rules, three domains).
- Regeneration and validation of derived markdown artifacts from canonical JSON.
- Bounded remediation of two supported drift slices (status-artifact regeneration, package-export synchronization) with simulation, verification, and rollback.
- Deterministic resolver traversal across three registered governance tiles.
- Coverage-snapshot generation from real `pytest-cov` runs, a bounded mutation-testing pilot, and an operator-workflow benchmark harness.

### Not Claimed

- Not a general-purpose linter, CI system, or drop-in governance tool for arbitrary repositories: the rules validate the specific schema defined by this repository's `core_reference.json`.
- Not autonomous self-modification: remediation is limited to explicitly supported, bounded slices with human-invoked commands.
- Not validated beyond this repository's own workspace and the temporary copies used by its tests and benchmark.
- Not a formal verification system: rules check declared metadata against observable workspace state, not program semantics.

### Known Limitations

- **No usable mutation result.** The mutation-testing pilot is configured for four modules, but the checked-in `ai_docs/mutation_test_snapshot.json` records zero mutants; no meaningful mutation score has been captured yet. A prior run recorded a large no-test mutant backlog concentrated in `remediation.py`, so the pilot needs triage before its slice is widened.
- **Status snapshots embed their generation path.** `ai_docs/system_status_snapshot.json` records the absolute root of the checkout that generated it (currently a neutral disposable path), so the first governance run on a fresh clone reports it stale until `--fix-status` or `status` regenerates it locally. This is detected-and-repairable drift, not silent breakage.
- The remediation engine supports only two drift slices; all other findings are report-only.
- The resolver graph contains three tiles; multi-hop traversal is bounded and not a general graph engine.
- The benchmark harness has tests but no benchmark result artifact is checked in, so no performance numbers are claimed.
- The `mutmut` pilot requires the console script (`.venv/bin/mutmut`) rather than `python -m mutmut` due to a multiprocessing entry-point issue observed in the development environment.
- The package is not published to a package index; installation is editable-only from a checkout.

## Documentation

- [SYSTEM_STATUS.md](SYSTEM_STATUS.md) — derived operational snapshot (component health, KB metrics, gaps, operator shortcuts); dated at generation and regenerable with `python -m inf_work status`
- [SYSTEM_SUMMARY.md](SYSTEM_SUMMARY.md) — condensed human-facing overview, also derived from canonical JSON
- [docs/COMMAND_REFERENCE.md](docs/COMMAND_REFERENCE.md) — complete CLI, Make, VS Code task, and mutation-pilot reference
- [docs/VALIDATION_RULES.md](docs/VALIDATION_RULES.md) — detailed inventory of validation and reporting behavior
- [ai_docs/component_index.json](ai_docs/component_index.json) — canonical registry of governed components
- [ai_docs/system_status_snapshot.json](ai_docs/system_status_snapshot.json) — canonical JSON status source of truth
- [knowledge_base/kb_index.json](knowledge_base/kb_index.json) — aggregate knowledge-base rollup

## Development Provenance

This project was developed through a human-directed, AI-assisted workflow. The repository includes structured development records: `knowledge_base/session_history.json` logs 58 development sessions, and `knowledge_base/` catalogs the techniques, bug fixes, innovations, and automation patterns produced along the way. Archived working notes live under `ai_docs/backups/`.

These records are provenance, not proof: the code and test suite are the authoritative implementation, and any conversational or historical claim should be checked against the repository's current state.

## Contributing

- Run `make check` (tests, smoke checks, status regeneration and validation) before submitting changes; CI runs the equivalent workflow.
- Derived artifacts (`SYSTEM_STATUS.md`, `SYSTEM_SUMMARY.md`, `ai_docs/system_status_snapshot.json`) must be regenerated, not hand-edited — use `python -m inf_work status` / `refresh-artifacts` and validate with `status-check` and `summary-check`.
- JSON component docs in `ai_docs/` and the knowledge base must stay synchronized with the code; the `kb` and `all` validators enforce this.
- Because status snapshots currently record the absolute workspace root, regeneration may change generated artifacts solely to reflect the contributor's checkout path. Review generated diffs before committing them.
- Deterministic behavior is required in core logic; architectural rules are defined in `core_reference.json` and `behavioral_directives.json`.

## License

MIT — see [LICENSE](LICENSE).
