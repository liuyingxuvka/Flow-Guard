from __future__ import annotations

import json

import pytest

from scripts.assemble_dna_completion_assessment import assemble_assessment


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_surface_audit_is_attached_as_a_blocked_reverse_layer(tmp_path):
    inventory = _write(
        tmp_path / "inventory.json",
        {
            "status": "passed",
            "evidence_fingerprint": "sha256:" + "1" * 64,
            "input_manifest_fingerprint": "sha256:" + "a" * 64,
            "claim_boundary": "scoped inventory",
            "inventory": {"discovery_fingerprint": "sha256:" + "2" * 64},
        },
    )
    consumer = _write(
        tmp_path / "consumer.json",
        {
            "status": "passed",
            "evidence_fingerprint": "sha256:" + "3" * 64,
            "claim_boundary": "consumer smoke",
            "wheel_sha256": "sha256:" + "4" * 64,
            "input_manifest_fingerprint": "sha256:" + "b" * 64,
        },
    )
    tests_receipt = tmp_path / "tests.xml"
    tests_receipt.write_text("<testsuite />", encoding="utf-8")
    surface = _write(
        tmp_path / "surface-audit.json",
        {
            "status": "blocked",
            "implementation_surface_audit": {
                "status": "blocked",
                "discovered_surface_count": 12,
                "mapping_surface_count": 12,
                "unmapped_surface_ids": [],
                "findings": [{"code": "implementation_surface_candidate_dispatch_reference_orphan"}],
                "discovery_fingerprint": "sha256:" + "5" * 64,
                "reverse_closure_complete": False,
                "unmapped_model_obligation_ids": [],
            },
        },
    )

    assessment = assemble_assessment(
        subject_revision="worktree:test+dirty",
        inventory_evidence=inventory,
        consumer_evidence=consumer,
        tests_receipt=tests_receipt,
        surface_audit=surface,
    )
    rows = {row.layer_id: row for row in assessment.layers}
    assert rows["observed_implementation_surface_complete"].status == "blocked"
    assert rows["bidirectional_traceability_complete"].status == "blocked"
    assert rows["observed_implementation_surface_complete"].input_fingerprint == "sha256:" + "5" * 64
    assert "discovered=12" in rows["observed_implementation_surface_complete"].gap_reason
    assert assessment.report.ok is False


def test_surface_report_status_pass_is_not_promoted_without_native_proof(tmp_path):
    inventory = _write(
        tmp_path / "inventory.json",
        {
            "status": "passed",
            "evidence_fingerprint": "sha256:" + "1" * 64,
            "input_manifest_fingerprint": "sha256:" + "a" * 64,
            "claim_boundary": "scoped inventory",
            "inventory": {"discovery_fingerprint": "sha256:" + "2" * 64},
        },
    )
    consumer = _write(
        tmp_path / "consumer.json",
        {
            "status": "passed",
            "evidence_fingerprint": "sha256:" + "3" * 64,
            "claim_boundary": "consumer smoke",
            "wheel_sha256": "sha256:" + "4" * 64,
            "input_manifest_fingerprint": "sha256:" + "b" * 64,
        },
    )
    tests_receipt = tmp_path / "tests.xml"
    tests_receipt.write_text("<testsuite />", encoding="utf-8")
    surface = _write(
        tmp_path / "surface-audit.json",
        {
            "status": "passed",
            "implementation_surface_audit": {
                "status": "passed",
                "discovered_surface_count": 1,
                "mapping_surface_count": 1,
                "unmapped_surface_ids": [],
                "findings": [],
                "discovery_fingerprint": "sha256:" + "5" * 64,
                "reverse_closure_complete": True,
                "unmapped_model_obligation_ids": [],
            },
        },
    )

    assessment = assemble_assessment(
        subject_revision="worktree:test+dirty",
        inventory_evidence=inventory,
        consumer_evidence=consumer,
        tests_receipt=tests_receipt,
        surface_audit=surface,
    )
    rows = {row.layer_id: row for row in assessment.layers}
    assert rows["observed_implementation_surface_complete"].status == "unverified"
    assert rows["bidirectional_traceability_complete"].status == "unverified"
    assert "not independently proof-bound" in rows["observed_implementation_surface_complete"].gap_reason


def test_producer_plan_is_separate_and_subject_bound(tmp_path):
    inventory = _write(
        tmp_path / "inventory.json",
        {
            "status": "passed",
            "evidence_fingerprint": "sha256:" + "1" * 64,
            "input_manifest_fingerprint": "sha256:" + "a" * 64,
            "claim_boundary": "scoped inventory",
            "inventory": {"discovery_fingerprint": "sha256:" + "2" * 64},
        },
    )
    consumer = _write(
        tmp_path / "consumer.json",
        {
            "status": "passed",
            "evidence_fingerprint": "sha256:" + "3" * 64,
            "claim_boundary": "consumer smoke",
            "wheel_sha256": "sha256:" + "4" * 64,
            "input_manifest_fingerprint": "sha256:" + "b" * 64,
        },
    )
    tests_receipt = tmp_path / "tests.xml"
    tests_receipt.write_text("<testsuite />", encoding="utf-8")
    surface = _write(
        tmp_path / "surface-audit.json",
        {
            "status": "blocked",
            "implementation_surface_audit": {
                "status": "blocked",
                "discovered_surface_count": 1,
                "mapping_surface_count": 1,
                "unmapped_surface_ids": [],
                "findings": [],
                "discovery_fingerprint": "sha256:" + "5" * 64,
                "reverse_closure_complete": False,
                "unmapped_model_obligation_ids": [],
            },
        },
    )
    plan = _write(
        tmp_path / "producer-plan.json",
        {
            "schema_version": "flowguard.dna_producer_plan.v1",
            "subject_revision": "worktree:test+dirty",
            "layers": {
                "intent_inventory_complete": {
                    field: ("owner:inventory" if field == "owner_id" else f"{field}:inventory")
                    for field in (
                        "owner_id", "evidence_id", "receipt_id", "receipt_fingerprint",
                        "source_fingerprint", "model_fingerprint", "toolchain_fingerprint",
                        "environment_fingerprint", "result_fingerprint",
                    )
                }
            },
        },
    )
    assessment = assemble_assessment(
        subject_revision="worktree:test+dirty",
        inventory_evidence=inventory,
        consumer_evidence=consumer,
        tests_receipt=tests_receipt,
        surface_audit=surface,
        producer_plan=plan,
    )
    assert "intent_inventory_complete" in assessment.expected_producer_identities
    assert "external_consumer_complete" not in assessment.expected_producer_identities
    assert any(
        finding.code == "dna_layer_expected_producer_identity_incomplete"
        for finding in assessment.report.findings
    ) is False

    bad_plan = _write(
        tmp_path / "bad-producer-plan.json",
        {
            "schema_version": "flowguard.dna_producer_plan.v1",
            "subject_revision": "other-subject",
            "layers": {},
        },
    )
    with pytest.raises(ValueError, match="subject_revision mismatch"):
        assemble_assessment(
            subject_revision="worktree:test+dirty",
            inventory_evidence=inventory,
            consumer_evidence=consumer,
            tests_receipt=tests_receipt,
            surface_audit=surface,
            producer_plan=bad_plan,
        )
