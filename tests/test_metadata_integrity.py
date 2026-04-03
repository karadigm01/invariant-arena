from __future__ import annotations

import json
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_workspace_json_files_parse() -> None:
    json_files = sorted(WORKSPACE_ROOT.glob("*.json"))
    json_files.extend(sorted((WORKSPACE_ROOT / "ai_docs").glob("*.json")))
    json_files.extend(sorted((WORKSPACE_ROOT / "knowledge_base").glob("*.json")))

    assert json_files
    for json_file in json_files:
        payload = load_json(json_file)
        assert isinstance(payload, dict), f"Expected object payload in {json_file}"


def test_component_index_documentation_paths_exist() -> None:
    component_index = load_json(WORKSPACE_ROOT / "ai_docs" / "component_index.json")
    components = component_index["components"]

    for component in components:
        documentation_path = WORKSPACE_ROOT / component["documentation_path"]
        file_path = WORKSPACE_ROOT / component["file_path"]
        assert documentation_path.is_file(), f"Missing documentation file: {documentation_path}"
        assert file_path.is_file(), f"Missing component file: {file_path}"


def test_component_index_counts_match_components() -> None:
    component_index = load_json(WORKSPACE_ROOT / "ai_docs" / "component_index.json")
    components = component_index["components"]
    metadata = component_index["metadata"]
    health_status = component_index["health_status"]

    assert metadata["total_components"] == len(components)
    assert health_status["total_healthy"] == sum(
        1 for component in components if component["health_status"] == "healthy"
    )


def test_knowledge_base_index_counts_match_files() -> None:
    techniques = load_json(WORKSPACE_ROOT / "knowledge_base" / "techniques.json")
    bug_fixes = load_json(WORKSPACE_ROOT / "knowledge_base" / "bug_fixes.json")
    innovations = load_json(WORKSPACE_ROOT / "knowledge_base" / "constraint_innovations.json")
    automation_patterns = load_json(WORKSPACE_ROOT / "knowledge_base" / "automation_patterns.json")
    kb_index = load_json(WORKSPACE_ROOT / "knowledge_base" / "kb_index.json")

    assert kb_index["total_techniques"] == len(techniques["techniques"])
    assert kb_index["total_bug_fixes"] == len(bug_fixes["bug_fixes"])
    assert kb_index["total_innovations"] == len(innovations["innovations"])
    assert kb_index["total_automation_patterns"] == len(automation_patterns["automation_patterns"])


def test_validator_workflow_exists() -> None:
    workflow_path = WORKSPACE_ROOT / ".github" / "workflows" / "validator-check.yml"
    assert workflow_path.is_file()


def test_validator_workflow_runs_aggregate_and_resolver_only_reports() -> None:
    workflow_path = WORKSPACE_ROOT / ".github" / "workflows" / "validator-check.yml"
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert "python -m inf_work all . --pretty" in workflow_text
    assert "python -m inf_work all . --pretty --profile resolver-only" in workflow_text
