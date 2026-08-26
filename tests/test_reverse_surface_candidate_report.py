from __future__ import annotations

from copy import deepcopy

from flowguard.behavior_surface_audit import (
    IMPLEMENTATION_SURFACE_CANDIDATE_REPORT_SCHEMA,
    classify_implementation_surface_candidates,
    validate_implementation_surface_candidate_report,
)


def _row(surface_id: str, kind: str, surface_class: str, *, line: int) -> dict:
    return {
        "surface_id": surface_id,
        "surface_kind": kind,
        "surface_class": surface_class,
        "source_path": "app.py",
        "source_ref": f"app.py#{surface_id}@L{line}:C0-L{line}:C10",
        "source_fingerprint": "sha256:" + "1" * 64,
        "surface_fingerprint": "sha256:" + "2" * 64,
        "review_group_id": f"group:{surface_id}",
        "review_granularity": "surface",
    }


def _discovery() -> dict:
    return {
        "schema_version": "flowguard.implementation_surface_audit.v1",
        "status": "passed",
        "discovery_fingerprint": "sha256:" + "3" * 64,
        "shard_plan_fingerprint": "sha256:" + "4" * 64,
        "source_paths": ["app.py"],
        "shard_ids": ["shard-0"],
        "surfaces": [
            _row("surface:function:a", "function", "code", line=1),
            _row("surface:ui:b", "ui_like_action", "ui_like", line=10),
            _row(
                "surface:unbound:c",
                "unreachable_or_unbound",
                "code",
                line=20,
            ),
        ],
        "unbound_surface_ids": ["surface:unbound:c"],
        "findings": [],
        "call_graph": [
            {
                "caller_surface_id": "surface:function:a",
                "call_name": "dispatch",
                "resolution": "resolved_static_dispatch",
                "resolved_surface_ids": ["surface:ui:b", "surface:function:a"],
                "dispatch_kind": "source_candidate_set",
            }
        ],
    }


def test_candidate_report_is_structural_only_and_conserves_discovery():
    discovery = _discovery()
    plan = {"plan_fingerprint": discovery["shard_plan_fingerprint"]}

    report = classify_implementation_surface_candidates(discovery, plan=plan)
    assert report["schema_version"] == IMPLEMENTATION_SURFACE_CANDIDATE_REPORT_SCHEMA
    assert report["status"] == "candidate_only"
    assert report["candidate_only"] is True
    assert report["semantic_authority"] == "none"
    assert report["reverse_closure_complete"] is False
    assert report["candidate_conservation"]["status"] == "passed"
    assert report["candidate_surface_count"] == len(discovery["surfaces"])
    assert report["candidate_class_counts"] == {
        "implementation_code": 1,
        "ui_like": 1,
        "unbound_or_unreachable": 1,
    }
    assert "finite_dispatch_candidate_reference" in report["candidate_reason_counts"]
    assert "unbound_denominator_reference" in report["candidate_reason_counts"]
    semantic_fields = {
        "intent_id",
        "model_owner_id",
        "model_obligation_ids",
        "owner",
        "test_refs",
        "receipt_refs",
        "disposition",
    }
    assert all(not (semantic_fields & set(row)) for row in report["candidates"])

    validation = validate_implementation_surface_candidate_report(
        report,
        discovery,
        plan=plan,
    )
    assert validation["status"] == "passed"
    assert validation["findings"] == []


def test_candidate_report_rejects_missing_surface_row():
    discovery = _discovery()
    plan = {"plan_fingerprint": discovery["shard_plan_fingerprint"]}
    report = classify_implementation_surface_candidates(discovery, plan=plan)
    report["candidates"] = report["candidates"][:-1]

    validation = validate_implementation_surface_candidate_report(
        report,
        discovery,
        plan=plan,
    )
    codes = {item["code"] for item in validation["findings"]}
    assert validation["status"] == "blocked"
    assert "implementation_surface_candidate_report_conservation_failed" in codes
    assert "implementation_surface_candidate_report_id_projection_mismatch" in codes
    assert "implementation_surface_candidate_evidence_fingerprint_mismatch" in codes


def test_candidate_report_rejects_unknown_or_duplicate_surface_identity():
    discovery = _discovery()
    duplicate_discovery = deepcopy(discovery)
    duplicate_discovery["surfaces"].append(
        deepcopy(duplicate_discovery["surfaces"][0])
    )
    duplicate_report = classify_implementation_surface_candidates(duplicate_discovery)
    assert duplicate_report["status"] == "blocked"
    codes = {item["code"] for item in duplicate_report["findings"]}
    assert "implementation_surface_candidate_discovery_duplicate_id" in codes

    plan = {"plan_fingerprint": discovery["shard_plan_fingerprint"]}
    report = classify_implementation_surface_candidates(discovery, plan=plan)
    report["candidates"].append(
        {
            **report["candidates"][0],
            "surface_id": "surface:foreign",
        }
    )
    report["candidate_surface_ids"].append("surface:foreign")
    validation = validate_implementation_surface_candidate_report(
        report,
        discovery,
        plan=plan,
    )
    codes = {item["code"] for item in validation["findings"]}
    assert validation["status"] == "blocked"
    assert "implementation_surface_candidate_report_conservation_failed" in codes


def test_candidate_report_rejects_semantic_binding_injection():
    discovery = _discovery()
    plan = {"plan_fingerprint": discovery["shard_plan_fingerprint"]}
    report = classify_implementation_surface_candidates(discovery, plan=plan)
    report["candidates"][0]["intent_id"] = "intent:guessed"

    validation = validate_implementation_surface_candidate_report(
        report,
        discovery,
        plan=plan,
    )
    codes = {item["code"] for item in validation["findings"]}
    assert validation["status"] == "blocked"
    assert "implementation_surface_candidate_semantic_field_forbidden" in codes
    assert "implementation_surface_candidate_row_mismatch" in codes
