from __future__ import annotations

import json
from pathlib import Path

from inf_work.core_reference import build_core_reference_view, extract_required_directories, load_core_reference


def write_core_reference(workspace_root: Path) -> dict[str, object]:
    payload = {
        "workspace_governance": {
            "directory_structure": {
                "tests/": "Tests",
                "ai_docs/": "AI docs",
                "src/": "Source code",
            }
        }
    }
    (workspace_root / "core_reference.json").write_text(json.dumps(payload), encoding="utf-8")
    return payload


def test_load_core_reference_reads_json(tmp_path: Path) -> None:
    payload = write_core_reference(tmp_path)

    loaded = load_core_reference(tmp_path)

    assert loaded == payload


def test_extract_required_directories_normalizes_and_sorts() -> None:
    directories = extract_required_directories(
        {
            "workspace_governance": {
                "directory_structure": {
                    "tests/": "Tests",
                    "ai_docs/": "Docs",
                    "src/": "Source",
                }
            }
        }
    )

    assert directories == ["ai_docs", "src", "tests"]


def test_build_core_reference_view_reports_paths(tmp_path: Path) -> None:
    write_core_reference(tmp_path)

    view = build_core_reference_view(tmp_path)

    assert view.workspace_root == str(tmp_path.resolve())
    assert view.core_reference_path == str((tmp_path / "core_reference.json").resolve())
    assert view.required_directories == ["ai_docs", "src", "tests"]
    assert view.to_dict()["required_directories"] == ["ai_docs", "src", "tests"]
