# Command Reference

Complete command surface for `inf.work`. All commands run from the repository root.
`make bootstrap` creates `.venv` and installs the project in editable mode with dev extras;
afterwards `.venv/bin/python` has the `inf_work` package available. Without an install, the
no-install fallback is:

```bash
PYTHONPATH="$(pwd)/src" python3 -m inf_work all . --pretty
```

## CLI subcommands (`python -m inf_work ...`)

| Command | Purpose |
| --- | --- |
| `all` | Combined JSON report for workspace, knowledge-base, and status validation |
| `all --fix-status` | Repairs stale canonical status artifacts before running the aggregate report |
| `workspace` | JSON health report for governed workspace directories |
| `kb` | JSON knowledge-base cross-reference report |
| `status` | Regenerates canonical structured status data and the derived `SYSTEM_STATUS.md` |
| `status-check` | Validates the canonical status data and derived `SYSTEM_STATUS.md`; supports `--fix` |
| `summary-check` | Validates the derived `SYSTEM_SUMMARY.md` artifact; supports `--fix` |
| `remediation-plan` | Compiles a deterministic remediation payload for supported slices without mutating the workspace |
| `remediation-plan --intent intent.status.refresh_artifacts` | Compiles the explicit governed status-refresh plan even when status artifacts are already compliant |
| `remediation-plan --simulate` | Adds a dry-run preview with predicted diffs for the selected slice, without mutating the workspace |
| `remediation-plan --apply` | Executes the selected bounded remediation slice, verifies the result, and restores pre-apply state if verification fails |
| `coverage-snapshot` | Generates `ai_docs/test_coverage_snapshot.json` from a real `pytest-cov` run |
| `mutation-snapshot` | Runs the bounded `mutmut` pilot and writes `ai_docs/mutation_test_snapshot.json` |
| `refresh-artifacts` | Refreshes the coverage snapshot, then regenerates the governed status artifacts in one deterministic step |
| `benchmark` | Runs the governed operator-workflow benchmark against temporary workspace copies and scores validation, remediation, rollback, and simulation determinism |
| `resolve-path` | Resolves an explicit path across the bounded resolver tile graph and prints the traversal payload as JSON |
| `infer-route` | Infers a deterministic route between two resolver tiles and prints the traversal payload as JSON |

Console scripts installed by the package: `kb-check` (`inf_work.kb_check:main`) and
`workspace-health` (`inf_work.__main__:main`).

### Resolver traversal examples

```bash
.venv/bin/python -m inf_work resolve-path workspace_governance component_index knowledge_base_index --workspace-root . --pretty
.venv/bin/python -m inf_work infer-route workspace_governance knowledge_base_index --workspace-root . --pretty
```

### Report filters

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

### Execution policy

- `--profile` expands to a deterministic set of rule ids and can be combined with repeated `--rule-id` flags. Available profiles include `ci`, `status-only`, `resolver-only`, `component-governance`, `kb-only`, `workspace-only`, `kb-cross-reference`, and `kb-metadata`.
- `--rule-id` changes which rules are executed, not just which results are shown.
- `--fail-on error` is the default exit threshold.
- `--fail-on critical` allows error-level findings to appear in the report while still exiting with code `0`.

## Make targets

```bash
make bootstrap             # create .venv and install the project with dev extras
make                       # default target: runs `make check`
make check                 # test + smoke + kb-check + status + status-check
make test                  # pytest across the focused test files
make smoke                 # workspace health report
make kb-check              # knowledge-base cross-reference report
make all-report            # aggregate governance report
make all-report-fix-status # aggregate report, repairing stale status artifacts first
make resolver-report       # resolver runtime-integrity profile only
make component-report      # component-governance profile only
make status                # regenerate canonical status artifacts
make status-check          # validate canonical status artifacts
make summary-check         # validate SYSTEM_SUMMARY.md
make coverage-snapshot     # refresh ai_docs/test_coverage_snapshot.json from pytest-cov
make mutation-snapshot     # run the bounded mutmut pilot and write the mutation snapshot
make refresh-artifacts     # coverage snapshot + status regeneration in one pass
make benchmark             # deterministic operator-workflow benchmark pack
make mutation              # run the focused mutmut pilot (uses .venv/bin/mutmut)
make mutation-results      # summarize surviving mutants from the last run
```

`make check` regenerates the canonical status artifacts before validating them.

## VS Code tasks

Each make target has a matching `workspace:*` task in `.vscode/tasks.json`:
`workspace: bootstrap`, `workspace: all`, `workspace: all-fix-status`,
`workspace: resolver-only`, `workspace: component-governance`, `workspace: status`,
`workspace: status-check`, `workspace: summary-check`, `workspace: coverage-snapshot`,
`workspace: mutation-snapshot`, `workspace: refresh-artifacts`, `workspace: benchmark`,
`workspace: mutation`, `workspace: mutation-results`, `workspace: check`,
`workspace: test`, `workspace: smoke`, `workspace: kb-check`.

## Mutation testing pilot

The repository includes a focused `mutmut` pilot configured in `setup.cfg`. The mutation
slice is intentionally bounded so runs finish in a practical amount of time while still
stress-testing real validation logic.

Configured mutation targets (`setup.cfg`, `paths_to_mutate`):

- `src/inf_work/workspace_health.py`
- `src/inf_work/core_reference.py`
- `src/inf_work/rules.py`
- `src/inf_work/remediation.py`

Targeted tests are selected via `pytest_add_cli_args_test_selection` in `setup.cfg`.

Typical flow:

```bash
make mutation
make mutation-results
make mutation-snapshot
```

The governed mutation snapshot is written to `ai_docs/mutation_test_snapshot.json` and is
what `SYSTEM_STATUS.md` / `SYSTEM_SUMMARY.md` read when they summarize mutation quality.

Notes:

- The pilot intentionally uses the `.venv/bin/mutmut` console script because it avoids a
  module-entrypoint multiprocessing issue triggered by `python -m mutmut` in this
  environment.
- After the baseline is stable, expand `paths_to_mutate` and
  `pytest_add_cli_args_test_selection` in `setup.cfg` to cover additional modules.

## Continuous integration

`.github/workflows/validator-check.yml` runs on push and pull requests:

1. Focused pytest run
2. `python -m inf_work workspace . --pretty` smoke check
3. `python -m inf_work kb . --pretty` smoke check
4. Canonical status generation and validation
5. Aggregate governance report (`all`)
6. Resolver-only governance profile
