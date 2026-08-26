from pathlib import Path
import json

import pytest

from flowguard.dna_completion_gate import (
    DNA_COMPLETION_LAYER_IDS,
    DNA_LAYER_BIDIRECTIONAL_TRACEABILITY,
    DNA_LAYER_EXTERNAL_CONSUMER,
    DNA_LAYER_OBSERVED_MISS_BACKFEED,
    DNA_LAYER_OBSERVED_IMPLEMENTATION_SURFACE,
    DNA_LAYER_REAL_UI_SURFACE,
    DNA_LAYER_RUNTIME_TEST_EXECUTION,
    DnaCompletionAssessment,
    DnaCompletionError,
    DnaCompletionLayerEvidence,
    DnaCompletionNativeOwnerInput,
    load_dna_completion,
    review_dna_completion,
    serialize_dna_completion,
    write_dna_completion,
)
from flowguard.proof_artifact import ProofArtifactRef, sha256_fingerprint
from flowguard.evidence_receipts import EvidenceReceipt, build_environment_fingerprint, snapshot_bytes


def _layer(layer_id: str, *, status: str = "passed", **overrides):
    values = {
        "layer_id": layer_id,
        "owner_id": f"owner:{layer_id}",
        "status": status,
        "input_fingerprint": f"sha256:input-{layer_id}",
        "evidence_kind": "native_terminal_receipt",
        "evidence_id": f"evidence:{layer_id}",
        "evidence_fingerprint": f"sha256:evidence-{layer_id}",
        "claim_boundary": f"native {layer_id} only",
        "gap_reason": "",
        "not_applicable_reason": "",
    }
    if status != "passed" and status != "not_applicable":
        values["gap_reason"] = f"{layer_id} has not reached terminal success"
    if status == "not_applicable":
        values["not_applicable_reason"] = "target does not claim this optional surface"
    values.update(overrides)
    return DnaCompletionLayerEvidence(**values)


def _assessment(
    *,
    layers=None,
    required=DNA_COMPLETION_LAYER_IDS,
    scope="broad",
    expected=None,
    producer_expected=None,
):
    rows = tuple(layers or (_layer(layer_id) for layer_id in DNA_COMPLETION_LAYER_IDS))
    expected = expected or {
        row.layer_id: row.input_fingerprint for row in rows if row.layer_id in required
    }
    return DnaCompletionAssessment(
        assessment_id="dna-assessment:test",
        target_system_id="target:test",
        subject_revision="source:test",
        claim_scope=scope,
        required_layer_ids=tuple(required),
        layers=rows,
        expected_input_fingerprints=expected,
        claim_boundary="test-only DNA completion boundary",
        expected_producer_identities=producer_expected or {},
    )


def _canonical_receipt(
    *,
    receipt_id: str,
    result_fingerprint: str,
    source: str,
    model: str,
    toolchain: str,
    environment: str,
    proof_artifact_id: str,
) -> EvidenceReceipt:
    """Build the current receipt authority used by strict proof tests."""

    env = build_environment_fingerprint({"flowguard_version": "test"})
    assert environment == env.fingerprint
    return EvidenceReceipt(
        receipt_id=receipt_id,
        subject_id="ui:surface",
        subject_kind="ui_runtime",
        producer_id="native-ui-owner",
        producer_version="test-owner-v1",
        claim_scope="external_contract",
        command=("native-ui-check",),
        working_directory_token="<WORKSPACE>",
        started_at="2026-08-18T00:00:00+00:00",
        finished_at="2026-08-18T00:00:01+00:00",
        exit_code=0,
        environment_fingerprint=env.fingerprint,
        environment_metadata=dict(env.metadata),
        contract_hash="sha256:" + "a" * 64,
        check_manifest_hash="sha256:" + "b" * 64,
        suite_map_hash="sha256:" + "c" * 64,
        input_snapshots=(
            snapshot_bytes(
                "ui-input",
                b"ui-input",
                path_token="<WORKSPACE>/ui-input.json",
                obligation_ids=("ui.surface",),
            ),
        ),
        proof_artifact_id=proof_artifact_id,
        proof_artifact_fingerprint="sha256:" + "d" * 64,
        result_status="pass",
        result_fingerprint=result_fingerprint,
        covered_obligations=("ui.surface",),
        claim_boundary="strict UI runtime proof test",
        metadata={
            "source_fingerprint": source,
            "model_fingerprint": model,
            "toolchain_fingerprint": toolchain,
            "terminal_state": "passed",
            "cleanup_state": "confirmed",
            "cleanup_verified": True,
        },
    )


def test_current_broad_gate_exposes_the_two_reverse_closure_layers():
    assert len(DNA_COMPLETION_LAYER_IDS) == 17
    assert DNA_LAYER_OBSERVED_IMPLEMENTATION_SURFACE in DNA_COMPLETION_LAYER_IDS
    assert DNA_LAYER_BIDIRECTIONAL_TRACEABILITY in DNA_COMPLETION_LAYER_IDS


def test_shape_only_native_rows_do_not_license_broad_dna():
    assessment = _assessment()
    report = review_dna_completion(assessment)

    assert not report.ok
    assert not report.dna_complete
    assert assessment.status == "blocked"
    assert any(finding.code == "dna_layer_proof_artifact_missing" for finding in report.findings)
    assert any(finding.code == "dna_layer_independent_input_missing" for finding in report.findings)


def test_static_layers_without_runtime_execution_are_not_broad_complete():
    rows = [
        _layer(
            layer_id,
            status=("not_run" if layer_id == DNA_LAYER_RUNTIME_TEST_EXECUTION else "passed"),
        )
        for layer_id in DNA_COMPLETION_LAYER_IDS
    ]
    report = review_dna_completion(_assessment(layers=rows))

    assert not report.ok
    assert not report.dna_complete
    assert any(
        finding.layer_id == DNA_LAYER_RUNTIME_TEST_EXECUTION
        and finding.code == "dna_layer_not_terminal_success"
        for finding in report.findings
    )


def test_fake_ui_boolean_evidence_is_self_reported_only():
    rows = [
        _layer(
            layer_id,
            evidence_kind=("boolean_only" if layer_id == DNA_LAYER_REAL_UI_SURFACE else "native_terminal_receipt"),
        )
        for layer_id in DNA_COMPLETION_LAYER_IDS
    ]
    report = review_dna_completion(_assessment(layers=rows))

    assert not report.ok
    assert any(
        finding.layer_id == DNA_LAYER_REAL_UI_SURFACE
        and finding.code == "dna_layer_self_reported_only"
        for finding in report.findings
    )


def test_source_or_model_input_identity_mismatch_blocks_even_with_passed_receipt():
    rows = tuple(_layer(layer_id) for layer_id in DNA_COMPLETION_LAYER_IDS)
    expected = {row.layer_id: row.input_fingerprint for row in rows}
    expected[DNA_COMPLETION_LAYER_IDS[0]] = "sha256:source-from-another-revision"
    report = review_dna_completion(_assessment(layers=rows, expected=expected))

    assert not report.ok
    assert any(
        finding.code == "dna_layer_input_identity_mismatch"
        and finding.layer_id == DNA_COMPLETION_LAYER_IDS[0]
        for finding in report.findings
    )


def test_unreplayed_observed_miss_keeps_operational_claim_blocked():
    rows = [
        _layer(
            layer_id,
            status=("not_run" if layer_id == DNA_LAYER_OBSERVED_MISS_BACKFEED else "passed"),
        )
        for layer_id in DNA_COMPLETION_LAYER_IDS
    ]
    report = review_dna_completion(_assessment(layers=rows))

    assert not report.ok
    assert any(
        finding.layer_id == DNA_LAYER_OBSERVED_MISS_BACKFEED
        for finding in report.findings
    )


def test_required_not_applicable_is_visible_and_does_not_complete():
    rows = [
        _layer(
            layer_id,
            status=("not_applicable" if layer_id == DNA_LAYER_EXTERNAL_CONSUMER else "passed"),
        )
        for layer_id in DNA_COMPLETION_LAYER_IDS
    ]
    report = review_dna_completion(_assessment(layers=rows))

    assert not report.ok
    assert not report.dna_complete
    assert any(
        finding.layer_id == DNA_LAYER_EXTERNAL_CONSUMER
        and finding.code == "dna_layer_not_terminal_success"
        for finding in report.findings
    )


def test_scoped_shape_only_assessment_is_blocked_without_independent_proof(tmp_path: Path):
    assessment = _assessment(
        required=(DNA_LAYER_REAL_UI_SURFACE,),
        scope="scoped",
        layers=(_layer(DNA_LAYER_REAL_UI_SURFACE),),
    )
    assert not assessment.report.ok
    assert not assessment.dna_complete
    assert assessment.status == "blocked"

    path = tmp_path / "dna-completion.json"
    write_dna_completion(assessment, str(path))
    loaded = load_dna_completion(str(path))
    assert loaded == assessment
    assert serialize_dna_completion(loaded) == serialize_dna_completion(assessment)


def test_scoped_pass_requires_and_accepts_real_input_result_and_receipt(tmp_path: Path):
    input_path = tmp_path / "input-manifest.json"
    input_path.write_text('{"input":"ui"}', encoding="utf-8")
    input_fingerprint = sha256_fingerprint(input_path.read_bytes())
    result_path = tmp_path / "result.json"
    result_path.write_text('{"status":"passed"}', encoding="utf-8")
    result_fingerprint = sha256_fingerprint(result_path.read_bytes())
    source = "sha256:" + "1" * 64
    model = "sha256:" + "2" * 64
    toolchain = "sha256:" + "3" * 64
    environment = build_environment_fingerprint({"flowguard_version": "test"}).fingerprint
    receipt = _canonical_receipt(
        receipt_id="receipt:ui",
        result_fingerprint=result_fingerprint,
        source=source,
        model=model,
        toolchain=toolchain,
        environment=environment,
        proof_artifact_id="proof:ui",
    )
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(receipt.to_json(), encoding="utf-8")
    receipt_fingerprint = receipt.fingerprint
    proof = ProofArtifactRef(
        artifact_id="proof:ui",
        producer_route="native-ui-owner",
        command="native-ui-check",
        result_path=str(result_path),
        result_status="passed",
        exit_code=0,
        started_at="2026-08-18T00:00:00+00:00",
        finished_at="2026-08-18T00:00:01+00:00",
        subject_id="ui:surface",
        subject_fingerprint=source,
        artifact_fingerprints={"result": result_fingerprint},
        receipt_path=str(receipt_path),
        receipt_fingerprint=receipt_fingerprint,
        execution_owner_id="native-ui-owner",
        source_fingerprint=source,
        model_fingerprint=model,
        toolchain_fingerprint=toolchain,
        environment_fingerprint=environment,
        result_fingerprint=result_fingerprint,
        terminal_state="passed",
        cleanup_state="confirmed",
        cleanup_verified=True,
    )
    row = _layer(
        DNA_LAYER_REAL_UI_SURFACE,
        owner_id="native-ui-owner",
        evidence_id="receipt:ui",
        evidence_fingerprint=receipt_fingerprint,
        input_fingerprint=input_fingerprint,
        metadata={
            "subject_revision": "source:test",
            "input_manifest_path": str(input_path),
            "input_manifest_fingerprint": input_fingerprint,
            "source_fingerprint": source,
            "model_fingerprint": model,
            "toolchain_fingerprint": toolchain,
            "environment_fingerprint": environment,
            "proof_artifact": proof.to_dict(),
        },
    )
    assessment = _assessment(
        layers=(row,),
        required=(DNA_LAYER_REAL_UI_SURFACE,),
        scope="scoped",
        expected={DNA_LAYER_REAL_UI_SURFACE: input_fingerprint},
        producer_expected={
            DNA_LAYER_REAL_UI_SURFACE: {
                "owner_id": "native-ui-owner",
                "evidence_id": "receipt:ui",
                "receipt_id": "receipt:ui",
                "receipt_fingerprint": receipt_fingerprint,
                "source_fingerprint": source,
                "model_fingerprint": model,
                "toolchain_fingerprint": toolchain,
                "environment_fingerprint": environment,
                "result_fingerprint": result_fingerprint,
            }
        },
    )
    assert assessment.report.ok, assessment.report.to_dict()
    assert not assessment.dna_complete
    assert assessment.status == "scoped_complete"


def test_scoped_dna_does_not_derive_expected_identity_from_evidence_row():
    """A row cannot turn its own forged identities into the frozen plan."""

    row = _layer(
        DNA_LAYER_REAL_UI_SURFACE,
        owner_id="row-authored-owner",
        evidence_id="row-authored-evidence",
        evidence_fingerprint="sha256:" + "1" * 64,
        input_fingerprint="sha256:" + "2" * 64,
        metadata={
            "subject_revision": "source:test",
            "source_fingerprint": "sha256:" + "3" * 64,
            "model_fingerprint": "sha256:" + "4" * 64,
            "toolchain_fingerprint": "sha256:" + "5" * 64,
            "environment_fingerprint": "sha256:" + "6" * 64,
            "proof_artifact": ProofArtifactRef(
                artifact_id="proof:row-authored",
                producer_route="row-authored-owner",
                command="row-authored-command",
                result_status="passed",
                exit_code=0,
            ).to_dict(),
        },
    )
    frozen = {
        "owner_id": "frozen-owner",
        "evidence_id": "frozen-evidence",
        "receipt_id": "frozen-receipt",
        "receipt_fingerprint": "sha256:" + "7" * 64,
        "source_fingerprint": "sha256:" + "8" * 64,
        "model_fingerprint": "sha256:" + "9" * 64,
        "toolchain_fingerprint": "sha256:" + "a" * 64,
        "environment_fingerprint": "sha256:" + "b" * 64,
        "result_fingerprint": "sha256:" + "c" * 64,
    }
    report = _assessment(
        layers=(row,),
        required=(DNA_LAYER_REAL_UI_SURFACE,),
        scope="scoped",
        expected={DNA_LAYER_REAL_UI_SURFACE: row.input_fingerprint},
        producer_expected={DNA_LAYER_REAL_UI_SURFACE: frozen},
    ).report

    assert not report.ok
    assert any(finding.code == "dna_layer_producer_identity_mismatch" for finding in report.findings)
    assert any(finding.code == "proof_receipt_missing" for finding in report.findings)


def test_passed_layer_requires_terminal_evidence_identity():
    with pytest.raises(DnaCompletionError, match="terminal evidence id"):
        _layer(DNA_LAYER_REAL_UI_SURFACE, evidence_id="")


def test_required_layer_without_frozen_expected_input_is_an_explicit_blocker():
    rows = tuple(_layer(layer_id) for layer_id in DNA_COMPLETION_LAYER_IDS)
    expected = {
        row.layer_id: row.input_fingerprint
        for row in rows
        if row.layer_id != DNA_LAYER_REAL_UI_SURFACE
    }
    report = review_dna_completion(_assessment(layers=rows, expected=expected))

    assert not report.ok
    assert any(
        finding.code == "dna_layer_expected_input_missing"
        and finding.layer_id == DNA_LAYER_REAL_UI_SURFACE
        for finding in report.findings
    )


def test_native_owner_input_carries_subject_identity_and_round_trips():
    item = DnaCompletionNativeOwnerInput(
        layer_id=DNA_LAYER_REAL_UI_SURFACE,
        owner_id="native-ui-owner",
        subject_revision="source:current",
        status="not_run",
        input_fingerprint="sha256:ui-input",
        evidence_kind="native_owner_pending",
        claim_boundary="UI owner evidence only",
        gap_reason="no independent proof artifact was produced",
    )

    row = item.to_layer_evidence()
    assert row.metadata["subject_revision"] == "source:current"
    assert DnaCompletionNativeOwnerInput.from_dict(item.to_dict()) == item

    assessment = DnaCompletionAssessment.from_native_owner_inputs(
        assessment_id="dna-assessment:native-input",
        target_system_id="target:test",
        subject_revision="source:current",
        claim_scope="scoped",
        required_layer_ids=(DNA_LAYER_REAL_UI_SURFACE,),
        native_owner_inputs=(item,),
        expected_input_fingerprints={DNA_LAYER_REAL_UI_SURFACE: "sha256:ui-input"},
        claim_boundary="native UI assessment only",
    )
    assert assessment.report.findings[0].code == "dna_layer_not_terminal_success"


def test_native_owner_input_rejects_conflicting_subject_identity():
    with pytest.raises(DnaCompletionError, match="subject_revision differs"):
        DnaCompletionNativeOwnerInput(
            layer_id=DNA_LAYER_REAL_UI_SURFACE,
            owner_id="native-ui-owner",
            subject_revision="source:current",
            status="not_run",
            input_fingerprint="sha256:ui-input",
            evidence_kind="native_owner_pending",
            claim_boundary="UI owner evidence only",
            gap_reason="no independent proof artifact was produced",
            metadata={"subject_revision": "source:other"},
        )


def test_native_owner_factory_rejects_assessment_subject_mismatch():
    item = DnaCompletionNativeOwnerInput(
        layer_id=DNA_LAYER_REAL_UI_SURFACE,
        owner_id="native-ui-owner",
        subject_revision="source:other",
        status="not_run",
        input_fingerprint="sha256:ui-input",
        evidence_kind="native_owner_pending",
        claim_boundary="native UI assessment only",
        gap_reason="no independent proof artifact was produced",
    )
    with pytest.raises(DnaCompletionError, match="differs from the assessment"):
        DnaCompletionAssessment.from_native_owner_inputs(
            assessment_id="dna-assessment:mismatch",
            target_system_id="target:test",
            subject_revision="source:current",
            claim_scope="scoped",
            required_layer_ids=(DNA_LAYER_REAL_UI_SURFACE,),
            native_owner_inputs=(item,),
            expected_input_fingerprints={DNA_LAYER_REAL_UI_SURFACE: "sha256:ui-input"},
            claim_boundary="native UI assessment only",
        )


def test_passed_layer_cannot_carry_a_gap_or_not_applicable_reason():
    with pytest.raises(DnaCompletionError, match="passed DNA layer cannot carry"):
        _layer(
            DNA_LAYER_REAL_UI_SURFACE,
            gap_reason="receipt is from an older run",
        )
