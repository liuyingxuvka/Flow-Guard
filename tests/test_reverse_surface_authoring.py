from __future__ import annotations

from copy import deepcopy

import pytest

from flowguard.reverse_surface_authoring import (
    REVERSE_SURFACE_AUTHORING_CONTEXT_SCHEMA,
    ReverseSurfaceAuthoringError,
    build_reverse_surface_authoring_context,
    validate_reverse_surface_authoring_context,
)


def _inputs() -> tuple[dict, dict, dict]:
    discovery = {
        "status": "passed",
        "discovery_fingerprint": "sha256:" + "a" * 64,
        "surfaces": [
            {
                "surface_id": "surface:function:one",
                "surface_kind": "function",
                "surface_class": "code",
                "review_group_id": "group:one",
                "review_granularity": "component",
                "source_path": "pkg/one.py",
            },
            {
                "surface_id": "surface:cli:run",
                "surface_kind": "cli_command",
                "surface_class": "cli",
                "review_group_id": "group:run",
                "review_granularity": "surface",
                "source_path": "pkg/cli.py",
            },
        ],
    }
    ledger = {
        "commitments": [
            {
                "commitment_id": "commitment:run",
                "business_intent_id": "intent:run",
                "behavior_plane": "product_runtime",
                "primary_owner_model_id": "models/run.py",
                "source_surface_ids": ["surface:cli:run"],
            }
        ]
    }
    owner_bindings = {
        "bindings": [
            {"owner_route": "run", "model_ids": ["run_model"]},
        ]
    }
    return discovery, ledger, owner_bindings


def test_context_preserves_denominator_but_does_not_invent_mapping() -> None:
    discovery, ledger, owner_bindings = _inputs()
    context = build_reverse_surface_authoring_context(
        discovery,
        ledger=ledger,
        owner_bindings=owner_bindings,
    )

    assert context["schema_version"] == REVERSE_SURFACE_AUTHORING_CONTEXT_SCHEMA
    assert context["status"] == "authoring_required"
    assert context["discovered_surface_count"] == 2
    assert context["discovered_surface_ids"] == [
        "surface:cli:run",
        "surface:function:one",
    ]
    assert {row["semantic_status"] for row in context["review_groups"]} == {
        "needs_author"
    }
    # The authoring context exposes the current model-obligation vocabulary
    # separately from the observed source denominator.  The fixture ledger
    # intentionally has no evidence rows, so no obligation is invented.
    assert context["current_model_obligation_catalog"] == []
    assert "intent_id" in context["required_model_obligation_fields"]
    assert "intent_id" in context["required_surface_fields"]
    assert context["mapping_artifact"]["status"] == "not_supplied"


def test_context_is_deterministic_and_validation_is_current() -> None:
    discovery, ledger, owner_bindings = _inputs()
    first = build_reverse_surface_authoring_context(
        discovery,
        ledger=ledger,
        owner_bindings=owner_bindings,
    )
    second = build_reverse_surface_authoring_context(
        deepcopy(discovery),
        ledger=deepcopy(ledger),
        owner_bindings=deepcopy(owner_bindings),
    )
    assert first == second
    validation = validate_reverse_surface_authoring_context(
        first,
        discovery,
        ledger=ledger,
        owner_bindings=owner_bindings,
    )
    assert validation["status"] == "passed"


def test_context_rejects_stale_discovery_or_catalogue() -> None:
    discovery, ledger, owner_bindings = _inputs()
    context = build_reverse_surface_authoring_context(
        discovery,
        ledger=ledger,
        owner_bindings=owner_bindings,
    )
    stale = deepcopy(context)
    stale["discovery_fingerprint"] = "sha256:" + "b" * 64
    validation = validate_reverse_surface_authoring_context(
        stale,
        discovery,
        ledger=ledger,
        owner_bindings=owner_bindings,
    )
    assert validation["status"] == "blocked"
    assert any(item["code"] == "authoring_context_identity_mismatch" for item in validation["findings"])


def test_context_rejects_stale_model_obligation_catalogue() -> None:
    discovery, ledger, owner_bindings = _inputs()
    context = build_reverse_surface_authoring_context(
        discovery,
        ledger=ledger,
        owner_bindings=owner_bindings,
    )
    stale = deepcopy(context)
    stale["current_model_obligation_catalog"] = [
        {
            "obligation_id": "obligation:invented",
            "commitment_id": "commitment:run",
            "intent_id": "intent:run",
            "model_owner_id": "models/run.py",
            "status": "current",
            "semantic_status": "needs_author",
        }
    ]
    validation = validate_reverse_surface_authoring_context(
        stale,
        discovery,
        ledger=ledger,
        owner_bindings=owner_bindings,
    )
    assert validation["status"] == "blocked"
    assert any(
        item["code"] == "authoring_context_model_obligation_catalog_stale"
        for item in validation["findings"]
    )


def test_context_projects_current_model_obligation_inventory_without_mapping() -> None:
    discovery, ledger, owner_bindings = _inputs()
    ledger["commitments"][0]["evidence"] = {
        "model_obligation_ids": ["obligation:run"],
        "test_evidence_ids": ["tests.test_run"],
        "coverage_receipt_ids": ["receipt:run"],
        "evidence_state": "current_pass",
    }
    context = build_reverse_surface_authoring_context(
        discovery,
        ledger=ledger,
        owner_bindings=owner_bindings,
    )
    assert context["current_model_obligation_catalog"] == [
        {
            "obligation_id": "obligation:run",
            "commitment_id": "commitment:run",
            "intent_id": "intent:run",
            "model_owner_id": "models/run.py",
            "status": "current",
            "semantic_status": "needs_author",
        }
    ]
    # A catalog row is a current-authority input, not an implementation map.
    assert context["mapping_artifact"]["status"] == "not_supplied"


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "passed"),
        ("discovered_surface_ids", ["surface:cli:run"]),
    ],
)
def test_context_cannot_be_promoted_by_editing_status_or_denomination(field: str, value: object) -> None:
    discovery, ledger, owner_bindings = _inputs()
    context = build_reverse_surface_authoring_context(
        discovery,
        ledger=ledger,
        owner_bindings=owner_bindings,
    )
    context[field] = value
    validation = validate_reverse_surface_authoring_context(
        context,
        discovery,
        ledger=ledger,
        owner_bindings=owner_bindings,
    )
    assert validation["status"] == "blocked"


def test_discovery_without_terminal_pass_is_blocked() -> None:
    discovery, ledger, owner_bindings = _inputs()
    discovery["status"] = "candidate_only"
    with pytest.raises(ReverseSurfaceAuthoringError, match="terminal discovery"):
        build_reverse_surface_authoring_context(
            discovery,
            ledger=ledger,
            owner_bindings=owner_bindings,
        )


def test_complete_shard_denominator_with_closed_call_graph_is_authoring_input() -> None:
    discovery, ledger, owner_bindings = _inputs()
    discovery.update(
        {
            "status": "passed",
            "shard_ids": ["implementation-surface-0000"],
            "shard_plan_fingerprint": "sha256:" + "c" * 64,
            "findings": [],
        }
    )
    context = build_reverse_surface_authoring_context(
        discovery,
        ledger=ledger,
        owner_bindings=owner_bindings,
    )
    assert context["status"] == "authoring_required"


def test_authoring_rejects_legacy_blocked_discovery_artifact() -> None:
    discovery, ledger, owner_bindings = _inputs()
    discovery.update(
        {
            "status": "blocked",
            "shard_ids": ["implementation-surface-0000"],
            "shard_plan_fingerprint": "sha256:" + "c" * 64,
            "findings": [],
        }
    )
    with pytest.raises(ReverseSurfaceAuthoringError, match="terminal discovery"):
        build_reverse_surface_authoring_context(
            discovery,
            ledger=ledger,
            owner_bindings=owner_bindings,
        )


def test_context_exposes_blocked_gap_without_promoting_it_to_coverage() -> None:
    discovery, ledger, owner_bindings = _inputs()
    context = build_reverse_surface_authoring_context(
        discovery,
        ledger=ledger,
        owner_bindings=owner_bindings,
    )

    assert "blocked_gap" in context["allowed_surface_dispositions"]
    # The context remains an unresolved authoring input.  Adding a visible
    # blocker to the vocabulary must not change its status into semantic
    # closure or create a mapping artifact.
    assert context["status"] == "authoring_required"
    assert context["mapping_artifact"]["status"] == "not_supplied"
