from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from flowguard.reverse_surface_semantic import (
    ReverseSurfaceSemanticAuthoringError,
    build_reverse_surface_semantic_map,
)


def _inputs() -> tuple[dict, dict]:
    discovery = {
        "schema_version": "flowguard.implementation_surface_audit.v1",
        "status": "passed",
        "discovery_fingerprint": "sha256:" + "a" * 64,
        "surfaces": [
            {
                "surface_id": "surface:class",
                "surface_kind": "class",
                "surface_class": "code",
                "review_group_id": "group:component",
                "review_granularity": "component",
                "source_path": "pkg/core.py",
                "source_ref": "pkg/core.py#Core",
                "source_fingerprint": "sha256:" + "b" * 64,
            },
            {
                "surface_id": "surface:function",
                "surface_kind": "function",
                "surface_class": "code",
                "review_group_id": "group:component",
                "review_granularity": "component",
                "source_path": "pkg/core.py",
                "source_ref": "pkg/core.py#helper",
                "source_fingerprint": "sha256:" + "b" * 64,
            },
            {
                "surface_id": "surface:cli",
                "surface_kind": "cli_command",
                "surface_class": "cli",
                "review_group_id": "group:cli",
                "review_granularity": "surface",
                "source_path": "pkg/cli.py",
                "source_ref": "pkg/cli.py#run",
                "source_fingerprint": "sha256:" + "c" * 64,
            },
        ],
    }
    context = {
        "schema_version": "flowguard.implementation_surface_authoring_context.v1",
        "discovery_fingerprint": discovery["discovery_fingerprint"],
        "review_groups": [
            {
                "review_group_id": "group:component",
                "review_granularity": "component",
                "surface_ids": ["surface:class", "surface:function"],
            },
            {
                "review_group_id": "group:cli",
                "review_granularity": "surface",
                "surface_ids": ["surface:cli"],
            },
        ],
        "current_model_obligation_catalog": [
            {
                "obligation_id": "obligation:component",
                "semantic_status": "needs_author",
            },
            {
                "obligation_id": "obligation:cli",
                "semantic_status": "needs_author",
            },
        ],
    }
    return discovery, context


def _component_decision() -> dict:
    return {
        "review_group_id": "group:component",
        "surface_ids": ["surface:class", "surface:function"],
        "disposition": "governed",
        "intent_id": "intent:component",
        "model_owner_id": "model:core",
        "model_obligation_ids": ["obligation:component"],
        "owner": "owner:core",
        "test_refs": ["tests/test_core.py#test_core"],
        "receipt_refs": ["receipts/core.json#receipt:core"],
    }


def _cli_decision() -> dict:
    return {
        "surface_id": "surface:cli",
        "disposition": "governed",
        "intent_id": "intent:cli",
        "model_owner_id": "model:cli",
        "model_obligation_ids": ["obligation:cli"],
        "owner": "owner:cli",
        "test_refs": ["tests/test_cli.py#test_cli"],
        "receipt_refs": ["receipts/cli.json#receipt:cli"],
    }


def _build(**overrides):
    discovery, context = _inputs()
    args = {
        "surface_decisions": [_cli_decision()],
        "component_group_decisions": [_component_decision()],
        "model_obligations": [
            {
                "obligation_id": "obligation:component",
                "disposition": "governed",
                "surface_ids": ["surface:class", "surface:function"],
                "intent_id": "intent:component",
                "model_owner_id": "model:core",
            },
            {
                "obligation_id": "obligation:cli",
                "disposition": "governed",
                "surface_ids": ["surface:cli"],
                "intent_id": "intent:cli",
                "model_owner_id": "model:cli",
            },
        ],
        "project_boundary": "fixture production boundary",
        "current_revision": "revision:current",
        "claim_boundary": "explicit semantic authoring only",
    }
    args.update(overrides)
    return build_reverse_surface_semantic_map(discovery, context, **args)


def test_materializer_conserves_surface_and_obligation_denominators() -> None:
    result = _build()

    assert result["authoring_status"] == "authored_pending_audit"
    assert len(result["surfaces"]) == 1
    assert result["component_groups"][0]["surface_ids"] == [
        "surface:class",
        "surface:function",
    ]
    assert sum(len(row["surface_ids"]) for row in result["component_groups"]) + len(
        result["surfaces"]
    ) == 3
    assert [row["obligation_id"] for row in result["model_obligations"]] == [
        "obligation:cli",
        "obligation:component",
    ]
    assert result["authoring_fingerprint"].startswith("sha256:")


def test_materializer_is_deterministic_and_does_not_infer_semantics() -> None:
    first = _build()
    second = _build()
    assert first == second
    assert first["surfaces"][0]["intent_id"] == "intent:cli"
    # A source name is copied only as structural provenance; it never becomes
    # an intent, model owner, obligation, test, or receipt value.
    assert first["surfaces"][0]["owner"] == "owner:cli"
    assert first["surfaces"][0]["model_obligation_ids"] == ["obligation:cli"]


def test_materializer_preserves_internal_proof_witness() -> None:
    internal = _component_decision()
    internal.update(
        {
            "disposition": "internal_proven",
            "proof_ref": "proofs/core-internal.json#proof:core",
            "reason": "the component is a current supporting implementation under the selected obligation",
        }
    )
    result = _build(component_group_decisions=[internal])
    group = result["component_groups"][0]
    assert group["disposition"] == "internal_proven"
    assert group["proof_ref"] == "proofs/core-internal.json#proof:core"
    assert group["reason"].startswith("the component is a current supporting")


def test_materializer_preserves_an_explicit_blocked_gap_without_receipt_claim() -> None:
    blocked_cli = _cli_decision()
    blocked_cli.update(
        {
            "disposition": "blocked_gap",
            "gap_reason": "dynamic callback has no current target-owned semantic binding",
            "receipt_refs": [],
        }
    )
    result = _build(
        surface_decisions=[blocked_cli],
        model_obligations=[
            {
                "obligation_id": "obligation:component",
                "disposition": "governed",
                "surface_ids": ["surface:class", "surface:function"],
                "intent_id": "intent:component",
                "model_owner_id": "model:core",
            },
            {
                "obligation_id": "obligation:cli",
                "disposition": "model_only_proven",
                "surface_ids": [],
                "proof_ref": "proofs/cli-model-only.json#proof",
                "reason": "the current model obligation has no implementation binding",
            },
        ],
    )

    row = result["surfaces"][0]
    assert row["disposition"] == "blocked_gap"
    assert row["gap_reason"].startswith("dynamic callback")
    assert "receipt_refs" not in row or row["receipt_refs"] == []
    cli_obligation = next(
        row for row in result["model_obligations"] if row["obligation_id"] == "obligation:cli"
    )
    assert cli_obligation["disposition"] == "model_only_proven"


def test_materializer_preserves_an_explicit_blocked_model_obligation_without_inference() -> None:
    result = _build(
        surface_decisions=[
            {
                **_cli_decision(),
                "disposition": "blocked_gap",
                "gap_reason": "target owner has not supplied a current obligation proof",
                "receipt_refs": [],
            }
        ],
        model_obligations=[
            {
                "obligation_id": "obligation:component",
                "disposition": "governed",
                "surface_ids": ["surface:class", "surface:function"],
                "intent_id": "intent:component",
                "model_owner_id": "model:core",
            },
            {
                "obligation_id": "obligation:cli",
                "disposition": "blocked_gap",
                "surface_ids": [],
                "gap_reason": "target owner has not supplied a current implementation or non-governed proof",
            },
        ],
    )
    obligation = next(
        row for row in result["model_obligations"] if row["obligation_id"] == "obligation:cli"
    )
    assert obligation["disposition"] == "blocked_gap"
    assert obligation["surface_ids"] == []
    assert obligation["gap_reason"].startswith("target owner")


def test_materializer_rejects_missing_surface_decision() -> None:
    with pytest.raises(ReverseSurfaceSemanticAuthoringError, match="omits current surfaces"):
        _build(surface_decisions=[])


def test_materializer_rejects_partial_or_overlapping_component_group() -> None:
    partial = _component_decision()
    partial["surface_ids"] = ["surface:class"]
    with pytest.raises(ReverseSurfaceSemanticAuthoringError, match="enumerate every current member"):
        _build(component_group_decisions=[partial])

    with pytest.raises(ReverseSurfaceSemanticAuthoringError, match="overlaps authored surfaces"):
        _build(surface_decisions=[_cli_decision(), {**_cli_decision(), "surface_id": "surface:class"}])


def test_materializer_rejects_unknown_and_duplicate_obligations() -> None:
    unknown = deepcopy(_component_decision())
    unknown["model_obligation_ids"] = ["obligation:unknown"]
    with pytest.raises(ReverseSurfaceSemanticAuthoringError, match="two-way|unknown"):
        _build(component_group_decisions=[unknown])

    obligations = [
        {
            "obligation_id": "obligation:component",
            "disposition": "governed",
            "surface_ids": ["surface:class", "surface:function"],
            "intent_id": "intent:component",
            "model_owner_id": "model:core",
        },
        {
            "obligation_id": "obligation:component",
            "disposition": "governed",
            "surface_ids": ["surface:class", "surface:function"],
            "intent_id": "intent:component",
            "model_owner_id": "model:core",
        },
        {
            "obligation_id": "obligation:cli",
            "disposition": "governed",
            "surface_ids": ["surface:cli"],
            "intent_id": "intent:cli",
            "model_owner_id": "model:cli",
        },
    ]
    with pytest.raises(ReverseSurfaceSemanticAuthoringError, match="duplicates"):
        _build(model_obligations=obligations)


def test_materializer_rejects_one_way_obligation_binding() -> None:
    obligation = {
        "obligation_id": "obligation:component",
        "disposition": "governed",
        "surface_ids": ["surface:class"],
        "intent_id": "intent:component",
        "model_owner_id": "model:core",
    }
    with pytest.raises(ReverseSurfaceSemanticAuthoringError, match="not two-way conserved"):
        _build(model_obligations=[obligation, {
            "obligation_id": "obligation:cli",
            "disposition": "governed",
            "surface_ids": ["surface:cli"],
            "intent_id": "intent:cli",
            "model_owner_id": "model:cli",
        }])


def test_materializer_requires_typed_proof_for_model_only_obligation() -> None:
    discovery, context = _inputs()
    context["current_model_obligation_catalog"].append(
        {"obligation_id": "obligation:abstract", "semantic_status": "needs_author"}
    )
    decisions = [_cli_decision()]
    with pytest.raises(ReverseSurfaceSemanticAuthoringError, match="proof_ref"):
        build_reverse_surface_semantic_map(
            discovery,
            context,
            surface_decisions=decisions,
            component_group_decisions=[_component_decision()],
            model_obligations=[
                {
                    "obligation_id": "obligation:component",
                    "disposition": "governed",
                    "surface_ids": ["surface:class", "surface:function"],
                    "intent_id": "intent:component",
                    "model_owner_id": "model:core",
                },
                {
                    "obligation_id": "obligation:cli",
                    "disposition": "governed",
                    "surface_ids": ["surface:cli"],
                    "intent_id": "intent:cli",
                    "model_owner_id": "model:cli",
                },
                {
                    "obligation_id": "obligation:abstract",
                    "disposition": "model_only_proven",
                    "surface_ids": [],
                },
            ],
            project_boundary="fixture",
            current_revision="revision:current",
            claim_boundary="fixture",
        )


def test_materializer_rejects_stale_context_identity_without_fallback() -> None:
    discovery, context = _inputs()
    context["discovery_fingerprint"] = "sha256:" + "z" * 64
    with pytest.raises(ReverseSurfaceSemanticAuthoringError, match="current discovery fingerprint"):
        build_reverse_surface_semantic_map(
            discovery,
            context,
            surface_decisions=[_cli_decision()],
            component_group_decisions=[_component_decision()],
            model_obligations=[
                {
                    "obligation_id": "obligation:component",
                    "disposition": "governed",
                    "surface_ids": ["surface:class", "surface:function"],
                    "intent_id": "intent:component",
                    "model_owner_id": "model:core",
                },
                {
                    "obligation_id": "obligation:cli",
                    "disposition": "governed",
                    "surface_ids": ["surface:cli"],
                    "intent_id": "intent:cli",
                    "model_owner_id": "model:cli",
                },
            ],
            project_boundary="fixture",
            current_revision="revision:current",
            claim_boundary="fixture",
        )


def test_semantic_authoring_cli_writes_only_explicit_current_map(tmp_path: Path) -> None:
    discovery, context = _inputs()
    decisions = {
        "surface_decisions": [_cli_decision()],
        "component_group_decisions": [_component_decision()],
        "model_obligations": [
            {
                "obligation_id": "obligation:component",
                "disposition": "governed",
                "surface_ids": ["surface:class", "surface:function"],
                "intent_id": "intent:component",
                "model_owner_id": "model:core",
            },
            {
                "obligation_id": "obligation:cli",
                "disposition": "governed",
                "surface_ids": ["surface:cli"],
                "intent_id": "intent:cli",
                "model_owner_id": "model:cli",
            },
        ],
        "project_boundary": "fixture production boundary",
        "current_revision": "revision:current",
        "claim_boundary": "explicit semantic authoring only",
    }
    discovery_path = tmp_path / "discovery.json"
    context_path = tmp_path / "context.json"
    decisions_path = tmp_path / "decisions.json"
    output_path = tmp_path / "implementation-surface-map.json"
    for path, payload in (
        (discovery_path, discovery),
        (context_path, context),
        (decisions_path, decisions),
    ):
        path.write_text(json.dumps(payload), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/author_reverse_surface_semantic_map.py",
            "--discovery",
            str(discovery_path),
            "--authoring-context",
            str(context_path),
            "--decisions",
            str(decisions_path),
            "--output",
            str(output_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "authored_pending_audit"
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["discovery_fingerprint"] == discovery["discovery_fingerprint"]
    assert written["authoring_status"] == "authored_pending_audit"


def test_semantic_authoring_cli_blocks_without_current_semantics(tmp_path: Path) -> None:
    discovery, context = _inputs()
    decisions = {"surface_decisions": [], "component_group_decisions": []}
    paths = {
        "discovery": tmp_path / "discovery.json",
        "authoring-context": tmp_path / "context.json",
        "decisions": tmp_path / "decisions.json",
        "output": tmp_path / "map.json",
    }
    for key, payload in (
        ("discovery", discovery),
        ("authoring-context", context),
        ("decisions", decisions),
    ):
        paths[key].write_text(json.dumps(payload), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/author_reverse_surface_semantic_map.py",
            "--discovery",
            str(paths["discovery"]),
            "--authoring-context",
            str(paths["authoring-context"]),
            "--decisions",
            str(paths["decisions"]),
            "--output",
            str(paths["output"]),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 2
    blocked = json.loads(completed.stdout)
    assert blocked["status"] == "blocked"
    assert blocked["output_written"] is False
    assert not paths["output"].exists()
