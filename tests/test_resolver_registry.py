from __future__ import annotations

from pathlib import Path

import inf_work.resolver_registry as resolver_registry_module
from inf_work.resolver_registry import (
    build_resolver_capabilities,
    infer_route,
    list_registered_tiles,
    resolve_explicit_path,
    resolve_tile,
)


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


def _payload(result: object) -> dict[str, object]:
    return result.to_dict()


def test_build_resolver_capabilities_reports_multi_hop_registry() -> None:
    snapshot = build_resolver_capabilities(WORKSPACE_ROOT)
    payload = _payload(snapshot)

    assert payload["workspace_root"] == str(WORKSPACE_ROOT)
    assert payload["inference_modes_supported"] == {
        "single_hop": True,
        "multi_hop_explicit": True,
        "multi_hop_inferred": True,
    }
    assert [tile["tile_id"] for tile in payload["registered_tiles"]] == [
        "workspace_governance",
        "component_index",
        "knowledge_base_index",
    ]
    assert all(tile["available"] is True for tile in payload["registered_tiles"])
    assert payload["pressure_telemetry_status"]["enabled"] is True
    assert payload["pressure_telemetry_status"]["status"] == "configured"
    assert payload["pressure_telemetry_status"]["sampling_mode"] == "workspace_snapshot"
    assert len(payload["pressure_telemetry_status"]["tracked_metrics"]) >= 4
    assert payload["traversal_examples"]["explicit"]["complete"] is True
    assert payload["traversal_examples"]["inferred"]["complete"] is True


def test_list_registered_tiles_returns_deterministic_tile_order() -> None:
    tiles = list_registered_tiles(WORKSPACE_ROOT)

    assert [tile.tile_id for tile in tiles] == [
        "workspace_governance",
        "component_index",
        "knowledge_base_index",
    ]


def test_resolve_tile_returns_matching_tile() -> None:
    tile = resolve_tile(WORKSPACE_ROOT, "component_index")

    assert tile is not None
    assert tile.title == "Component Index"
    assert tile.target_path == "ai_docs/component_index.json"
    assert tile.available is True


def test_resolve_tile_returns_none_for_unknown_tile() -> None:
    assert resolve_tile(WORKSPACE_ROOT, "unknown_tile") is None


def test_resolve_explicit_path_returns_bounded_multi_hop_route() -> None:
    result = resolve_explicit_path(
        WORKSPACE_ROOT,
        ["workspace_governance", "component_index", "knowledge_base_index"],
    )

    payload = _payload(result)
    assert payload["complete"] is True
    assert payload["traversal_mode"] == "explicit"
    assert payload["total_hops"] == 2
    assert [step["tile_id"] for step in payload["resolved_steps"]] == [
        "workspace_governance",
        "component_index",
        "knowledge_base_index",
    ]


def test_resolve_explicit_path_reports_unknown_tile() -> None:
    result = resolve_explicit_path(
        WORKSPACE_ROOT,
        ["workspace_governance", "unknown_tile"],
    )

    payload = _payload(result)
    assert payload["complete"] is False
    assert payload["failure_reason"] == "unknown_tile:unknown_tile"


def test_resolve_explicit_path_reports_empty_path() -> None:
    result = resolve_explicit_path(WORKSPACE_ROOT, [])

    payload = _payload(result)
    assert payload["complete"] is False
    assert payload["failure_reason"] == "empty_path"


def test_resolve_explicit_path_reports_unavailable_tile(tmp_path: Path) -> None:
    (tmp_path / "core_reference.json").write_text("{}\n", encoding="utf-8")

    result = resolve_explicit_path(tmp_path, ["workspace_governance", "component_index"])

    payload = _payload(result)
    assert payload["complete"] is False
    assert payload["failure_reason"] == "unavailable_tile:component_index"


def test_resolve_explicit_path_reports_unlinked_path(tmp_path: Path) -> None:
    (tmp_path / "core_reference.json").write_text("{}\n", encoding="utf-8")

    result = resolve_explicit_path(tmp_path, ["workspace_governance", "workspace_governance"])

    payload = _payload(result)
    assert payload["complete"] is False
    assert payload["failure_reason"] == "unlinked_path:workspace_governance->workspace_governance"


def test_infer_route_finds_shortest_deterministic_path() -> None:
    result = infer_route(WORKSPACE_ROOT, "component_index", "workspace_governance")

    payload = _payload(result)
    assert payload["complete"] is True
    assert payload["traversal_mode"] == "inferred"
    assert payload["total_hops"] == 1
    assert [step["tile_id"] for step in payload["resolved_steps"]] == [
        "component_index",
        "workspace_governance",
    ]


def test_infer_route_reports_unknown_start_tile() -> None:
    result = infer_route(WORKSPACE_ROOT, "unknown_tile", "workspace_governance")

    payload = _payload(result)
    assert payload["complete"] is False
    assert payload["failure_reason"] == "unknown_tile:unknown_tile"


def test_infer_route_reports_unknown_target_tile() -> None:
    result = infer_route(WORKSPACE_ROOT, "workspace_governance", "unknown_tile")

    payload = _payload(result)
    assert payload["complete"] is False
    assert payload["failure_reason"] == "unknown_tile:unknown_tile"


def test_infer_route_reports_unavailable_start_tile(tmp_path: Path) -> None:
    (tmp_path / "knowledge_base").mkdir(parents=True, exist_ok=True)
    (tmp_path / "knowledge_base" / "kb_index.json").write_text("{}\n", encoding="utf-8")

    result = infer_route(tmp_path, "workspace_governance", "knowledge_base_index")

    payload = _payload(result)
    assert payload["complete"] is False
    assert payload["failure_reason"] == "unavailable_tile:workspace_governance"


def test_infer_route_reports_unavailable_target_tile(tmp_path: Path) -> None:
    (tmp_path / "core_reference.json").write_text("{}\n", encoding="utf-8")

    result = infer_route(tmp_path, "workspace_governance", "knowledge_base_index")

    payload = _payload(result)
    assert payload["complete"] is False
    assert payload["failure_reason"] == "unavailable_tile:knowledge_base_index"


def test_infer_route_reports_route_not_found_when_only_neighbor_is_unavailable(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "core_reference.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "knowledge_base").mkdir(parents=True, exist_ok=True)
    (tmp_path / "knowledge_base" / "kb_index.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        resolver_registry_module,
        "_TILE_LINKS",
        {
            "workspace_governance": ("component_index",),
            "component_index": (),
            "knowledge_base_index": (),
        },
    )

    result = infer_route(tmp_path, "workspace_governance", "knowledge_base_index")

    payload = _payload(result)
    assert payload["complete"] is False
    assert payload["failure_reason"] == "route_not_found:workspace_governance->knowledge_base_index"