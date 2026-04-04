from __future__ import annotations

import json
from pathlib import Path

import inf_work.core_reference as core_reference_module
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


def test_load_core_reference_reads_using_utf8_encoding(monkeypatch, tmp_path: Path) -> None:
    write_core_reference(tmp_path)

    original_read_text = Path.read_text

    def fake_read_text(self: Path, *args, **kwargs) -> str:
        assert self == (tmp_path / "core_reference.json")
        assert kwargs.get("encoding") == "utf-8"
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read_text)

    loaded = core_reference_module.load_core_reference(tmp_path)

    assert loaded["workspace_governance"]["directory_structure"]["src/"] == "Source code"


def test_extract_required_directories_strips_only_trailing_slashes() -> None:
    directories = extract_required_directories(
        {
            "workspace_governance": {
                "directory_structure": {
                    "src/X/": "Source",
                    "tests/": "Tests",
                }
            }
        }
    )

    assert directories == ["src/X", "tests"]
