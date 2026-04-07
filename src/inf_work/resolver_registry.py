from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .core_reference import load_core_reference


@dataclass(frozen=True)
class ResolverTile:
    tile_id: str
    title: str
    target_path: str
    inference_mode: str
    description: str
    capability_signature: str
    available: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResolverCapabilitiesSnapshot:
    workspace_root: str
    inference_modes_supported: dict[str, bool]
    registered_tiles: list[dict[str, Any]]
    traversal_examples: dict[str, Any]
    pressure_telemetry_status: dict[str, Any]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResolverTraversalStep:
    tile_id: str
    title: str
    target_path: str
    inference_mode: str
    available: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResolverTraversalResult:
    workspace_root: str
    traversal_mode: str
    requested_path: list[str]
    resolved_steps: list[dict[str, Any]]
    total_hops: int
    complete: bool
    failure_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_TILE_DEFINITIONS = (
    (
        "workspace_governance",
        "Workspace Governance",
        "core_reference.json",
        "single_hop",
        "Resolve the governed workspace contract from the immutable core reference.",
        "core_reference.read",
    ),
    (
        "component_index",
        "Component Index",
        "ai_docs/component_index.json",
        "single_hop",
        "Resolve the canonical component registry for governed modules and artifacts.",
        "component_index.read",
    ),
    (
        "knowledge_base_index",
        "Knowledge Base Index",
        "knowledge_base/kb_index.json",
        "single_hop",
        "Resolve the aggregated knowledge-base rollup for techniques, bug fixes, innovations, and automation patterns.",
        "knowledge_base.rollup_read",
    ),
)


_TILE_LINKS = {
    "workspace_governance": ("component_index", "knowledge_base_index"),
    "component_index": ("knowledge_base_index", "workspace_governance"),
    "knowledge_base_index": ("component_index", "workspace_governance"),
}


def _tile_map(workspace_root: str | Path) -> dict[str, ResolverTile]:
    return {tile.tile_id: tile for tile in list_registered_tiles(workspace_root)}


def _build_step(tile: ResolverTile) -> ResolverTraversalStep:
    return ResolverTraversalStep(
        tile_id=tile.tile_id,
        title=tile.title,
        target_path=tile.target_path,
        inference_mode=tile.inference_mode,
        available=tile.available,
    )


def list_registered_tiles(workspace_root: str | Path) -> list[ResolverTile]:
    root_path = Path(workspace_root).resolve()
    tiles: list[ResolverTile] = []
    for tile_id, title, target_path, inference_mode, description, capability_signature in _TILE_DEFINITIONS:
        tiles.append(
            ResolverTile(
                tile_id=tile_id,
                title=title,
                target_path=target_path,
                inference_mode=inference_mode,
                description=description,
                capability_signature=capability_signature,
                available=(root_path / target_path).is_file(),
            )
        )
    return tiles


def resolve_tile(workspace_root: str | Path, tile_id: str) -> ResolverTile | None:
    for tile in list_registered_tiles(workspace_root):
        if tile.tile_id == tile_id:
            return tile
    return None


def resolve_explicit_path(workspace_root: str | Path, tile_path: list[str]) -> ResolverTraversalResult:
    root_path = Path(workspace_root).resolve()
    tiles = _tile_map(root_path)
    resolved_steps: list[dict[str, Any]] = []

    if not tile_path:
        return ResolverTraversalResult(
            workspace_root=str(root_path),
            traversal_mode="explicit",
            requested_path=[],
            resolved_steps=[],
            total_hops=0,
            complete=False,
            failure_reason="empty_path",
        )

    for index, tile_id in enumerate(tile_path):
        tile = tiles.get(tile_id)
        if tile is None:
            return ResolverTraversalResult(
                workspace_root=str(root_path),
                traversal_mode="explicit",
                requested_path=tile_path,
                resolved_steps=resolved_steps,
                total_hops=max(0, len(resolved_steps) - 1),
                complete=False,
                failure_reason=f"unknown_tile:{tile_id}",
            )
        resolved_steps.append(_build_step(tile).to_dict())
        if not tile.available:
            return ResolverTraversalResult(
                workspace_root=str(root_path),
                traversal_mode="explicit",
                requested_path=tile_path,
                resolved_steps=resolved_steps,
                total_hops=max(0, len(resolved_steps) - 1),
                complete=False,
                failure_reason=f"unavailable_tile:{tile_id}",
            )
        if index == 0:
            continue
        previous_tile_id = tile_path[index - 1]
        if tile_id not in _TILE_LINKS.get(previous_tile_id, ()): 
            return ResolverTraversalResult(
                workspace_root=str(root_path),
                traversal_mode="explicit",
                requested_path=tile_path,
                resolved_steps=resolved_steps,
                total_hops=max(0, len(resolved_steps) - 1),
                complete=False,
                failure_reason=f"unlinked_path:{previous_tile_id}->{tile_id}",
            )

    return ResolverTraversalResult(
        workspace_root=str(root_path),
        traversal_mode="explicit",
        requested_path=tile_path,
        resolved_steps=resolved_steps,
        total_hops=max(0, len(tile_path) - 1),
        complete=True,
        failure_reason=None,
    )


def infer_route(workspace_root: str | Path, start_tile_id: str, target_tile_id: str) -> ResolverTraversalResult:
    root_path = Path(workspace_root).resolve()
    tiles = _tile_map(root_path)
    start_tile = tiles.get(start_tile_id)
    target_tile = tiles.get(target_tile_id)

    if start_tile is None:
        return ResolverTraversalResult(
            workspace_root=str(root_path),
            traversal_mode="inferred",
            requested_path=[start_tile_id, target_tile_id],
            resolved_steps=[],
            total_hops=0,
            complete=False,
            failure_reason=f"unknown_tile:{start_tile_id}",
        )
    if target_tile is None:
        return ResolverTraversalResult(
            workspace_root=str(root_path),
            traversal_mode="inferred",
            requested_path=[start_tile_id, target_tile_id],
            resolved_steps=[_build_step(start_tile).to_dict()],
            total_hops=0,
            complete=False,
            failure_reason=f"unknown_tile:{target_tile_id}",
        )
    if not start_tile.available:
        return ResolverTraversalResult(
            workspace_root=str(root_path),
            traversal_mode="inferred",
            requested_path=[start_tile_id, target_tile_id],
            resolved_steps=[_build_step(start_tile).to_dict()],
            total_hops=0,
            complete=False,
            failure_reason=f"unavailable_tile:{start_tile_id}",
        )
    if not target_tile.available:
        return ResolverTraversalResult(
            workspace_root=str(root_path),
            traversal_mode="inferred",
            requested_path=[start_tile_id, target_tile_id],
            resolved_steps=[_build_step(start_tile).to_dict(), _build_step(target_tile).to_dict()],
            total_hops=1,
            complete=False,
            failure_reason=f"unavailable_tile:{target_tile_id}",
        )

    queue: list[list[str]] = [[start_tile_id]]
    visited = {start_tile_id}

    while queue:
        current_path = queue.pop(0)
        current_tile_id = current_path[-1]
        if current_tile_id == target_tile_id:
            return ResolverTraversalResult(
                workspace_root=str(root_path),
                traversal_mode="inferred",
                requested_path=[start_tile_id, target_tile_id],
                resolved_steps=[_build_step(tiles[tile_id]).to_dict() for tile_id in current_path],
                total_hops=max(0, len(current_path) - 1),
                complete=True,
                failure_reason=None,
            )
        for neighbor_tile_id in sorted(_TILE_LINKS.get(current_tile_id, ())):
            if neighbor_tile_id in visited:
                continue
            if not tiles[neighbor_tile_id].available:
                continue
            visited.add(neighbor_tile_id)
            queue.append([*current_path, neighbor_tile_id])

    return ResolverTraversalResult(
        workspace_root=str(root_path),
        traversal_mode="inferred",
        requested_path=[start_tile_id, target_tile_id],
        resolved_steps=[_build_step(start_tile).to_dict()],
        total_hops=0,
        complete=False,
        failure_reason=f"route_not_found:{start_tile_id}->{target_tile_id}",
    )


def build_resolver_capabilities(workspace_root: str | Path) -> ResolverCapabilitiesSnapshot:
    root_path = Path(workspace_root).resolve()
    core_reference = load_core_reference(root_path)
    constraint_drift_detection = core_reference["continuous_monitoring"]["constraint_drift_detection"]
    performance_tracking = core_reference["continuous_monitoring"]["performance_tracking"]
    telemetry_enabled = bool(constraint_drift_detection["enabled"] and performance_tracking["enabled"])
    tracked_metrics = list(
        dict.fromkeys(
            [
                *constraint_drift_detection["metrics"],
                *performance_tracking["metrics"],
            ]
        )
    )
    registered_tiles = [tile.to_dict() for tile in list_registered_tiles(root_path)]
    explicit_route = resolve_explicit_path(
        root_path,
        ["workspace_governance", "component_index", "knowledge_base_index"],
    )
    inferred_route = infer_route(root_path, "workspace_governance", "knowledge_base_index")

    return ResolverCapabilitiesSnapshot(
        workspace_root=str(root_path),
        inference_modes_supported={
            "single_hop": True,
            "multi_hop_explicit": explicit_route.complete,
            "multi_hop_inferred": inferred_route.complete,
        },
        registered_tiles=registered_tiles,
        traversal_examples={
            "explicit": explicit_route.to_dict(),
            "inferred": inferred_route.to_dict(),
        },
        pressure_telemetry_status={
            "enabled": telemetry_enabled,
            "status": "configured" if telemetry_enabled else "disabled",
            "sampling_mode": "workspace_snapshot",
            "tracked_metrics": tracked_metrics,
            "alert_threshold": core_reference["architectural_constraints"]["contracts"]["performance"]["alert_threshold"],
        },
        notes=[
            "Single-hop and bounded multi-hop resolver support are backed by a deterministic in-process tile registry for governed workspace sources.",
            "Pressure telemetry surfaces configured continuous-monitoring metrics from `core_reference.json` without sampling mutable runtime state.",
        ],
    )