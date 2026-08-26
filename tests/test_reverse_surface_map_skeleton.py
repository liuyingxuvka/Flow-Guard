from scripts.author_reverse_surface_map_skeleton import (
    BLOCKED_GAP,
    MAP_SCHEMA,
    build_reverse_surface_map_skeleton,
)


def _discovery():
    return {
        "status": "blocked",
        "discovery_fingerprint": "sha256:discovery",
        "source_paths": ["app.py"],
        "shard_ids": ["implementation-surface-0000"],
        "call_graph": [
            {
                "caller_surface_id": "surface:dynamic",
                "callee_name": "receiver.run",
                "resolution": "resolved_external_contract",
                "resolved_surface_ids": [],
                "external_contract_id": "contract:dynamic_receiver:" + "a" * 64,
                "boundary_kind": "dynamic_receiver",
                "target_kind": "external_contract",
                "target_identity": "contract:dynamic_receiver:" + "a" * 64,
                "target_status": "current_resolved",
                "target_proof": "external_contract_registry",
            }
        ],
        "unbound_surface_ids": ["surface:unbound"],
        "findings": [],
        "surfaces": [
            {
                "surface_id": "surface:dynamic",
                "surface_kind": "dynamic",
                "surface_class": "code",
                "source_fingerprint": "sha256:source",
                "source_path": "app.py",
                "source_ref": "app.py#dynamic",
                "review_group_id": "group:surface:dynamic",
                "review_granularity": "surface",
            },
            {
                "surface_id": "surface:unbound",
                "surface_kind": "unreachable_or_unbound",
                "surface_class": "code",
                "source_fingerprint": "sha256:source",
                "source_path": "app.py",
                "source_ref": "app.py#unbound",
                "review_group_id": "group:component:unbound",
                "review_granularity": "component",
            },
        ],
    }


def _component_discovery():
    return {
        "status": "passed",
        "discovery_fingerprint": "sha256:component-discovery",
        "source_paths": ["app.py"],
        "shard_ids": ["implementation-surface-0000"],
        "call_graph": [],
        "unbound_surface_ids": [],
        "findings": [],
        "surfaces": [
            {
                "surface_id": "surface:module",
                "surface_kind": "module",
                "surface_class": "code",
                "source_fingerprint": "sha256:source",
                "source_path": "app.py",
                "source_ref": "app.py#module",
                "review_group_id": "group:component:app",
                "review_granularity": "component",
            },
            {
                "surface_id": "surface:function",
                "surface_kind": "function",
                "surface_class": "code",
                "source_fingerprint": "sha256:source",
                "source_path": "app.py",
                "source_ref": "app.py#function",
                "review_group_id": "group:component:app",
                "review_granularity": "component",
            },
            {
                "surface_id": "surface:api",
                "surface_kind": "api",
                "surface_class": "api",
                "source_fingerprint": "sha256:source",
                "source_path": "app.py",
                "source_ref": "app.py#api",
                "review_group_id": "group:surface:api",
                "review_granularity": "surface",
            },
        ],
    }


def test_skeleton_preserves_denominator_without_inventing_semantics_or_receipts():
    result = build_reverse_surface_map_skeleton(
        _discovery(),
        plan={"plan_fingerprint": "sha256:plan"},
    )

    assert result["schema_version"] == MAP_SCHEMA
    assert result["authoring_status"] == "blocked_gap_scaffold"
    assert result["semantic_authority"] == "none"
    assert result["terminal_receipt_refs"] == []
    assert result["model_obligations"] == []
    assert [row["surface_id"] for row in result["surfaces"]] == [
        "surface:dynamic",
        "surface:unbound",
    ]
    for row in result["surfaces"]:
        assert row["disposition"] == BLOCKED_GAP
        assert row["intent_id"] == ""
        assert row["model_owner_id"] == ""
        assert row["model_obligation_ids"] == []
        assert row["owner"] == ""
        assert row["test_refs"] == []
        assert row["receipt_refs"] == []
        assert row["gap_reason"]

    dispositions = {
        item["observation_type"]: item
        for item in result["observation_dispositions"]
    }
    assert dispositions["dynamic_surface"]["count"] == 1
    assert dispositions["unreachable_or_unbound_surface"]["count"] == 1
    assert dispositions["finite_dispatch_call_graph"]["count"] == 0
    assert dispositions["finite_dispatch_call_graph"]["disposition"] == "resolved_static_dispatch"
    assert all(
        item["disposition"] == BLOCKED_GAP
        for key, item in dispositions.items()
        if key != "finite_dispatch_call_graph"
    )


def test_skeleton_is_deterministic_for_same_observation():
    first = build_reverse_surface_map_skeleton(
        _discovery(), plan={"plan_fingerprint": "sha256:plan"}
    )
    second = build_reverse_surface_map_skeleton(
        _discovery(), plan={"plan_fingerprint": "sha256:plan"}
    )
    assert first == second


def test_skeleton_compresses_only_complete_internal_component_groups():
    result = build_reverse_surface_map_skeleton(_component_discovery())

    assert [row["surface_id"] for row in result["surfaces"]] == ["surface:api"]
    assert len(result["component_groups"]) == 1
    assert result["component_groups"][0]["review_group_id"] == "group:component:app"
    assert result["component_groups"][0]["surface_ids"] == [
        "surface:function",
        "surface:module",
    ]
    assert result["source_observation"]["surface_count"] == 3
