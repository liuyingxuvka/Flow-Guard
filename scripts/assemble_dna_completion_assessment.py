"""Assemble a fail-closed DNA assessment from native evidence artifacts.

This command is an evidence assembler, not an executor.  It intentionally
marks the layers without a current native owner as ``stale``, ``not_run``, or
``blocked``.  A broad assessment is expected to remain blocked until every
layer is supplied under one frozen identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from flowguard.dna_completion_gate import (
    DNA_COMPLETION_LAYER_IDS,
    DNA_LAYER_BEHAVIOR_BINDING,
    DNA_LAYER_CODE_BINDING,
    DNA_LAYER_CONTRACT_UNIVERSE,
    DNA_LAYER_EXTERNAL_CONSUMER,
    DNA_LAYER_FAULT_MATRIX,
    DNA_LAYER_INSTALLATION,
    DNA_LAYER_INTENT_INVENTORY,
    DNA_LAYER_OBSERVED_IMPLEMENTATION_SURFACE,
    DNA_LAYER_BIDIRECTIONAL_TRACEABILITY,
    DNA_LAYER_OBSERVED_MISS_BACKFEED,
    DNA_LAYER_PLATFORM_PROVIDER,
    DNA_LAYER_REAL_UI_SURFACE,
    DNA_LAYER_RELEASE_IDENTITY,
    DNA_LAYER_RUNTIME_TEST_EXECUTION,
    DNA_LAYER_SEMANTIC_MODEL,
    DNA_LAYER_STATIC_BLUEPRINT,
    DNA_LAYER_STATIC_TEST_BINDING,
    DnaCompletionAssessment,
    DnaCompletionNativeOwnerInput,
    is_sha256_fingerprint,
    write_dna_completion,
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"evidence artifact must be an object: {path}")
    return value


_PRODUCER_IDENTITY_FIELDS = (
    "owner_id",
    "evidence_id",
    "receipt_id",
    "receipt_fingerprint",
    "source_fingerprint",
    "model_fingerprint",
    "toolchain_fingerprint",
    "environment_fingerprint",
    "result_fingerprint",
)


def _load_producer_plan(
    path: Path | None,
    *,
    subject_revision: str,
) -> dict[str, dict[str, str]]:
    """Load a separately authored expected producer identity plan.

    A plan is intentionally optional for the current blocked assessment, but
    when supplied it is a strict, independently frozen input.  The assembler
    never derives it from an observed evidence report; doing so would let a
    self-authored receipt define its own expected identity.
    """

    if path is None:
        return {}
    payload = _load_json(path)
    if payload.get("schema_version") != "flowguard.dna_producer_plan.v1":
        raise ValueError(f"producer plan schema mismatch: {path}")
    if str(payload.get("subject_revision") or "") != subject_revision:
        raise ValueError(f"producer plan subject_revision mismatch: {path}")
    layers = payload.get("layers")
    if not isinstance(layers, Mapping) or not layers:
        raise ValueError(f"producer plan layers must be a non-empty object: {path}")
    result: dict[str, dict[str, str]] = {}
    for layer_id, raw in layers.items():
        if not isinstance(layer_id, str) or not layer_id.strip():
            raise ValueError(f"producer plan has an invalid layer id: {path}")
        if not isinstance(raw, Mapping):
            raise ValueError(f"producer plan layer must be an object: {path}#{layer_id}")
        unknown = set(raw) - set(_PRODUCER_IDENTITY_FIELDS)
        if unknown:
            raise ValueError(
                f"producer plan layer has unknown fields: {path}#{layer_id}: {sorted(unknown)}"
            )
        missing = [field for field in _PRODUCER_IDENTITY_FIELDS if not str(raw.get(field) or "").strip()]
        if missing:
            raise ValueError(
                f"producer plan layer is incomplete: {path}#{layer_id}: {', '.join(missing)}"
            )
        result[layer_id] = {
            field: str(raw[field]).strip()
            for field in _PRODUCER_IDENTITY_FIELDS
        }
    return result


def _passed_row(
    *,
    layer_id: str,
    owner_id: str,
    subject_revision: str,
    input_fingerprint: str,
    evidence_kind: str,
    evidence_id: str,
    evidence_fingerprint: str,
    claim_boundary: str,
    metadata: Mapping[str, Any] | None = None,
) -> DnaCompletionNativeOwnerInput:
    return DnaCompletionNativeOwnerInput(
        layer_id=layer_id,
        owner_id=owner_id,
        subject_revision=subject_revision,
        status="passed",
        input_fingerprint=input_fingerprint,
        evidence_kind=evidence_kind,
        evidence_id=evidence_id,
        evidence_fingerprint=evidence_fingerprint,
        claim_boundary=claim_boundary,
        metadata=dict(metadata or {}),
    )


def _gap_row(
    *,
    layer_id: str,
    subject_revision: str,
    status: str,
    reason: str,
    owner_id: str,
    input_fingerprint: str | None = None,
) -> DnaCompletionNativeOwnerInput:
    return DnaCompletionNativeOwnerInput(
        layer_id=layer_id,
        owner_id=owner_id,
        subject_revision=subject_revision,
        status=status,
        input_fingerprint=input_fingerprint or subject_revision,
        evidence_kind="native_owner_pending",
        claim_boundary="Whole-product DNA claim; this layer has no current terminal proof in this assessment.",
        gap_reason=reason,
    )


def _native_pass_or_gap(
    *,
    evidence: Mapping[str, Any],
    evidence_path: Path,
    layer_id: str,
    owner_id: str,
    subject_revision: str,
    input_fingerprint: str,
    evidence_kind: str,
    claim_boundary: str,
) -> DnaCompletionNativeOwnerInput:
    """Only materialize a passed row when the evidence carries proof inputs.

    The assembler is not allowed to promote a JSON report, wheel hash, or
    JUnit file into terminal evidence by itself.  Native owners must attach a
    proof-artifact reference and an independently readable input manifest;
    otherwise the result is an explicit ``unverified`` row.
    """

    metadata = evidence.get("metadata")
    metadata = dict(metadata) if isinstance(metadata, Mapping) else {}
    proof = evidence.get("proof_artifact") or metadata.get("proof_artifact")
    input_path = evidence.get("input_manifest_path") or metadata.get("input_manifest_path")
    input_hash = evidence.get("input_manifest_fingerprint") or metadata.get("input_manifest_fingerprint")
    # The outer report fingerprint is not a terminal producer identity.  A
    # layer row must point at the independently verified result (or receipt)
    # bytes carried by the proof artifact.
    proof_result_fingerprint = str(
        proof.get("result_fingerprint") if isinstance(proof, Mapping) else ""
    )
    proof_receipt_fingerprint = str(
        proof.get("receipt_fingerprint") if isinstance(proof, Mapping) else ""
    )
    evidence_fingerprint = str(
        evidence.get("result_fingerprint")
        or proof_result_fingerprint
        or evidence.get("receipt_fingerprint")
        or proof_receipt_fingerprint
        or ""
    )
    if (
        not isinstance(proof, Mapping)
        or not isinstance(input_path, str)
        or not isinstance(input_hash, str)
        or not is_sha256_fingerprint(evidence_fingerprint)
    ):
        return _gap_row(
            layer_id=layer_id,
            subject_revision=subject_revision,
            status="unverified",
            reason=(
                f"{evidence_path} reports a result but has no independently bound "
                "proof_artifact and input_manifest_path/fingerprint; the assembler "
                "cannot license a passed DNA layer"
            ),
            owner_id=owner_id,
            input_fingerprint=input_fingerprint,
        )
    metadata.update(
        {
            "input_manifest_path": input_path,
            "input_manifest_fingerprint": input_hash,
            "proof_artifact": dict(proof),
        }
    )
    for key in (
        "receipt_fingerprint",
        "source_fingerprint",
        "model_fingerprint",
        "toolchain_fingerprint",
        "environment_fingerprint",
        "result_fingerprint",
    ):
        if key in evidence:
            metadata[key] = evidence[key]
    return _passed_row(
        layer_id=layer_id,
        owner_id=owner_id,
        subject_revision=subject_revision,
        input_fingerprint=input_fingerprint,
        evidence_kind=evidence_kind,
        evidence_id=str(evidence.get("evidence_id") or evidence_path),
        evidence_fingerprint=evidence_fingerprint,
        claim_boundary=claim_boundary,
        metadata=metadata,
    )


def assemble_assessment(
    *,
    subject_revision: str,
    inventory_evidence: Path,
    consumer_evidence: Path,
    tests_receipt: Path,
    surface_audit: Path,
    producer_plan: Path | None = None,
) -> DnaCompletionAssessment:
    inventory = _load_json(inventory_evidence)
    consumer = _load_json(consumer_evidence)
    if inventory.get("status") != "passed" or not inventory.get("evidence_fingerprint"):
        raise ValueError("behavior inventory evidence is not a current terminal pass")
    if consumer.get("status") != "passed" or not consumer.get("evidence_fingerprint"):
        raise ValueError("external consumer evidence is not a current terminal pass")
    tests_fingerprint = _sha256_file(tests_receipt)
    expected_producer_identities = _load_producer_plan(
        producer_plan,
        subject_revision=subject_revision,
    )
    inventory_payload = inventory.get("inventory") or {}
    inventory_discovery_fingerprint = str(inventory_payload.get("discovery_fingerprint", ""))
    if not inventory_discovery_fingerprint:
        raise ValueError("behavior inventory evidence has no discovery fingerprint")
    inventory_input = str(inventory.get("input_manifest_fingerprint", ""))
    if not is_sha256_fingerprint(inventory_input):
        raise ValueError("behavior inventory evidence has no current input manifest fingerprint")
    consumer_source_fingerprint = str(consumer.get("wheel_sha256", ""))
    if not consumer_source_fingerprint:
        raise ValueError("external consumer evidence has no wheel fingerprint")
    consumer_input = str(consumer.get("input_manifest_fingerprint", ""))
    if not is_sha256_fingerprint(consumer_input):
        raise ValueError("external consumer evidence has no current input manifest fingerprint")

    # The reverse implementation audit is a mandatory input for a broad DNA
    # assessment.  It is not itself a proof artifact: source observations and
    # map skeletons remain blocked until an independent native owner supplies
    # semantic intent/model/test/receipt proof.
    surface_payload = _load_json(surface_audit)
    implementation = surface_payload.get("implementation_surface_audit")
    implementation = implementation if isinstance(implementation, Mapping) else surface_payload
    discovered = implementation.get("discovered_surface_count")
    mapping_count = implementation.get("mapping_surface_count")
    unmapped = implementation.get("unmapped_surface_ids")
    findings = implementation.get("findings")
    discovery_fingerprint = str(
        implementation.get("discovery_fingerprint")
        or surface_payload.get("discovery_fingerprint")
        or ""
    )
    if not discovery_fingerprint:
        raise ValueError("reverse implementation audit has no discovery fingerprint")
    surface_input = discovery_fingerprint
    raw_status = str(implementation.get("status") or surface_payload.get("status") or "blocked")
    allowed_statuses = {"blocked", "stale", "not_run", "unverified", "not_applicable"}
    # A reverse audit report is not itself a DNA proof artifact.  Even a
    # report that says ``passed`` is conservatively downgraded until a
    # producer receipt, proof artifact, and frozen input manifest are
    # supplied through the normal native-owner path.
    normalized_status = raw_status if raw_status in allowed_statuses else "unverified"
    surface_status = normalized_status
    surface_reason = (
        f"{surface_audit} reverse implementation audit is {normalized_status}: "
        f"discovered={discovered!r}, mapped={mapping_count!r}, "
        f"unmapped={len(unmapped) if isinstance(unmapped, list) else unmapped!r}, "
        f"findings={len(findings) if isinstance(findings, list) else findings!r}; "
        "the audit preserves source-only ambiguity and does not supply semantic "
        "intent/model/test/receipt proof"
    )
    reverse_complete = implementation.get("reverse_closure_complete") is True
    model_obligations = implementation.get("unmapped_model_obligation_ids")
    if raw_status == "passed":
        surface_reason += "; a report status=passed is not independently proof-bound"
        normalized_status = "unverified"
        surface_status = "unverified"
    elif raw_status == "not_applicable":
        # A broad reverse denominator cannot be closed by a bare N/A string.
        # Keep it visibly blocked until the target supplies an independent
        # not-applicable proof and scope boundary.
        surface_reason += "; a bare not_applicable status has no independent scope proof"
        normalized_status = "blocked"
        surface_status = "blocked"
    trace_status = normalized_status
    trace_reason = (
        f"{surface_audit} bidirectional traceability is {normalized_status}: "
        f"reverse_closure_complete={reverse_complete!r}, "
        f"unmapped_model_obligations="
        f"{len(model_obligations) if isinstance(model_obligations, list) else model_obligations!r}; "
        "every model obligation still needs an independently authored surface "
        "or typed model-only/retired/not-applicable proof"
    )

    rows: list[DnaCompletionNativeOwnerInput] = [
        _gap_row(
            layer_id=DNA_LAYER_STATIC_BLUEPRINT,
            subject_revision=subject_revision,
            status="unverified",
            reason=(
                "current model authority was directly rebuilt and project/model "
                "audit is current, but no independently proof-bound whole-product "
                "static-blueprint receipt is attached to this assessment"
            ),
            owner_id="flowguard.target_system_blueprint",
        ),
        _gap_row(
            layer_id=DNA_LAYER_SEMANTIC_MODEL,
            subject_revision=subject_revision,
            status="unverified",
            reason=(
                "current model revision set and observed snapshot now share the "
                "direct-rebuild identity, but no independently proof-bound "
                "whole-product semantic-model receipt is attached"
            ),
            owner_id="flowguard.model_revision_set",
        ),
        _native_pass_or_gap(
            evidence=inventory,
            evidence_path=inventory_evidence,
            layer_id=DNA_LAYER_INTENT_INVENTORY,
            owner_id="flowguard-native-discovery-manifest:v1",
            subject_revision=subject_revision,
            input_fingerprint=inventory_input,
            evidence_kind="native_behavior_discovery",
            claim_boundary=str(inventory["claim_boundary"]),
        ),
        _gap_row(
            layer_id=DNA_LAYER_OBSERVED_IMPLEMENTATION_SURFACE,
            subject_revision=subject_revision,
            status=surface_status,
            reason=surface_reason,
            owner_id="flowguard.behavior_surface_audit",
            input_fingerprint=surface_input,
        ),
        _gap_row(
            layer_id=DNA_LAYER_BIDIRECTIONAL_TRACEABILITY,
            subject_revision=subject_revision,
            status=trace_status,
            reason=trace_reason,
            owner_id="flowguard.behavior_commitment",
            input_fingerprint=surface_input,
        ),
        _gap_row(
            layer_id=DNA_LAYER_BEHAVIOR_BINDING,
            subject_revision=subject_revision,
            status="blocked",
            reason="the scoped denominator is current only for evidence infrastructure; the whole-product behavior binding is not populated",
            owner_id="flowguard.behavior_commitment",
        ),
        _gap_row(
            layer_id=DNA_LAYER_CODE_BINDING,
            subject_revision=subject_revision,
            status="not_run",
            reason="no current whole-product function-block to implementation-owner reconciliation was executed",
            owner_id="flowguard.model_test_alignment",
        ),
        _gap_row(
            layer_id=DNA_LAYER_STATIC_TEST_BINDING,
            subject_revision=subject_revision,
            status="unverified",
            reason=(
                "focused JUnit output has no separate producer receipt, execution "
                "identity, or cleanup confirmation; a file hash alone cannot prove "
                "static test binding"
            ),
            owner_id="native-test-owner:focused-dna-audit",
            input_fingerprint=tests_fingerprint,
        ),
        _gap_row(
            layer_id=DNA_LAYER_RUNTIME_TEST_EXECUTION,
            subject_revision=subject_revision,
            status="not_run",
            reason="runtime reconciliation is implemented, but no native full leaf execution receipt is attached",
            owner_id="native-test-execution-owner",
        ),
        _gap_row(
            layer_id=DNA_LAYER_CONTRACT_UNIVERSE,
            subject_revision=subject_revision,
            status="not_run",
            reason="no frozen whole-product contract universe and Cartesian error matrix receipt is attached",
            owner_id="flowguard.contract_exhaustion",
        ),
        _gap_row(
            layer_id=DNA_LAYER_REAL_UI_SURFACE,
            subject_revision=subject_revision,
            status="blocked",
            reason="existing UI evidence is in-memory fixture data; no independently produced browser, desktop, or manual proof artifact exists",
            owner_id="flowguard.ui_structure",
        ),
        _native_pass_or_gap(
            evidence=_load_json(consumer_evidence),
            evidence_path=consumer_evidence,
            layer_id=DNA_LAYER_EXTERNAL_CONSUMER,
            owner_id="native-consumer-owner:clean-wheel",
            subject_revision=subject_revision,
            input_fingerprint=consumer_input,
            evidence_kind="clean_external_consumer_smoke",
            claim_boundary=str(consumer["claim_boundary"]),
        ),
        _gap_row(
            layer_id=DNA_LAYER_FAULT_MATRIX,
            subject_revision=subject_revision,
            status="not_run",
            reason="no native fault-injection campaign covering invalid input, permission, timeout, partial write, retry, and recovery classes is attached",
            owner_id="native-fault-matrix-owner",
        ),
        _gap_row(
            layer_id=DNA_LAYER_PLATFORM_PROVIDER,
            subject_revision=subject_revision,
            status="not_run",
            reason="no target platform/provider matrix and environment-specific terminal evidence is attached",
            owner_id="native-platform-provider-owner",
        ),
        _gap_row(
            layer_id=DNA_LAYER_INSTALLATION,
            subject_revision=subject_revision,
            status="not_run",
            reason="clean wheel installation smoke is not the official installer/upgrade/rollback contract",
            owner_id="native-installation-owner",
        ),
        _gap_row(
            layer_id=DNA_LAYER_OBSERVED_MISS_BACKFEED,
            subject_revision=subject_revision,
            status="blocked",
            reason="no current replay receipt proves a discovered miss was repaired, re-modeled, and re-tested under the same identity",
            owner_id="flowguard.model_miss_review",
        ),
        _gap_row(
            layer_id=DNA_LAYER_RELEASE_IDENTITY,
            subject_revision=subject_revision,
            status="blocked",
            reason="source/model/toolchain identity is still dirty and no release CI/tag receipt was authorized or produced",
            owner_id="native-release-owner",
        ),
    ]
    assessment = DnaCompletionAssessment.from_native_owner_inputs(
        assessment_id="flowguard-dna-audit-2026-08-18",
        target_system_id="flowguard-self-audit",
        subject_revision=subject_revision,
        claim_scope="broad",
        required_layer_ids=DNA_COMPLETION_LAYER_IDS,
        native_owner_inputs=tuple(rows),
        # Freeze one explicit input identity for every required layer.  Rows
        # without a native owner still remain non-terminal; an expected
        # identity is not a wildcard and does not manufacture evidence.
        expected_input_fingerprints={
            row.layer_id: row.input_fingerprint for row in rows
        },
        expected_producer_identities=expected_producer_identities,
        claim_boundary="Whole-product FlowGuard DNA claim; current evidence includes only explicitly bounded infrastructure slices and retains every broader gap.",
    )
    return assessment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject-revision", required=True)
    parser.add_argument("--inventory-evidence", type=Path, required=True)
    parser.add_argument("--consumer-evidence", type=Path, required=True)
    parser.add_argument("--tests-receipt", type=Path, required=True)
    parser.add_argument(
        "--producer-plan",
        type=Path,
        help=(
            "Separately authored frozen producer identities.  If omitted, "
            "any passed layer remains blocked by the DNA gate; observed reports "
            "are never used to manufacture this plan."
        ),
    )
    parser.add_argument(
        "--surface-audit",
        type=Path,
        required=True,
        help=(
            "Current reverse implementation-surface audit. This is mandatory "
            "for a broad DNA assessment; its status is attached to both reverse "
            "layers and never promoted without independent proof."
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    assessment = assemble_assessment(
        subject_revision=args.subject_revision,
        inventory_evidence=args.inventory_evidence,
        consumer_evidence=args.consumer_evidence,
        tests_receipt=args.tests_receipt,
        surface_audit=args.surface_audit,
        producer_plan=args.producer_plan,
    )
    write_dna_completion(assessment, str(args.output))
    print(json.dumps(assessment.to_dict(), ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if assessment.report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
