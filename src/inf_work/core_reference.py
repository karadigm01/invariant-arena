from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CoreReferenceView:
    workspace_root: str
    core_reference_path: str
    required_directories: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_core_reference(workspace_root: str | Path) -> dict[str, Any]:
    root_path = Path(workspace_root).resolve()
    core_reference_path = root_path / "core_reference.json"
    return json.loads(core_reference_path.read_text(encoding="utf-8"))


def extract_required_directories(core_reference: dict[str, Any]) -> list[str]:
    directory_structure = core_reference["workspace_governance"]["directory_structure"]
    return sorted(name.rstrip("/") for name in directory_structure)


def build_core_reference_view(workspace_root: str | Path) -> CoreReferenceView:
    root_path = Path(workspace_root).resolve()
    core_reference_path = root_path / "core_reference.json"
    core_reference = load_core_reference(root_path)
    return CoreReferenceView(
        workspace_root=str(root_path),
        core_reference_path=str(core_reference_path),
        required_directories=extract_required_directories(core_reference),
    )
