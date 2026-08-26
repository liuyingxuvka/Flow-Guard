"""Fail-closed evidence reconciliation for finite fault/recovery matrices.

The contract-exhaustion planner owns the finite fault universe.  This module
only consumes a native owner's terminal rows and checks that every declared
fault case has an independently replayable result.  It never executes a
target, infers a root cause from a label, or treats a matrix summary as leaf
evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .portable_model import canonical_identity, canonical_json_bytes
from .proof_artifact import (
    ProofArtifactRef,
    coerce_proof_artifact_ref,
    is_sha256_fingerprint,
    proof_artifact_integrity_gap_codes,
)


FAULT_MATRIX_SCHEMA = "flowguard.fault_matrix_evidence.v1"
FAULT_MATRIX_EXECUTION_STATES = ("executed", "reused", "not_run")
FAULT_MATRIX_OUTCOMES = ("passed", "failed", "blocked", "skipped", "not_run")
FAULT_MATRIX_FAULT_CLASSES = (
    "invalid_input",
    "permission",
    "timeout",
    "partial_write",
    "retry",
    "recovery",
    "concurrency",
    "dependency",
    "corrupt_artifact",
    "provider",
    "other",
)


@dataclass(frozen=True)
class FaultMatrixFinding:
    code: str
    case_id: str = ""
    path: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "case_id": self.case_id,
            "path": self.path,
            "detail": self.detail,
        }


def fault_matrix_fingerprint(payload: Mapping[str, Any]) -> str:
    unsigned = dict(payload)
    unsigned.pop("matrix_fingerprint", None)
    return canonical_identity(unsigned)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _ids(value: Any, *, path: str, findings: list[FaultMatrixFinding]) -> list[str]:
    if not isinstance(value, list) or any(not _text(item) for item in value):
        findings.append(FaultMatrixFinding("fault_matrix_ids_invalid", path=path, detail="non-empty id array required"))
        return []
    result = [str(item).strip() for item in value]
    if len(result) != len(set(result)):
        findings.append(FaultMatrixFinding("fault_matrix_ids_duplicate", path=path, detail="ids must be unique"))
    return result


def _row_fingerprint(row: Mapping[str, Any]) -> str:
    unsigned = dict(row)
    unsigned.pop("case_fingerprint", None)
    return canonical_identity(unsigned)


def validate_fault_matrix(
    payload: object,
    *,
    expected_case_ids: Iterable[str] | None = None,
    expected_input_fingerprint: str = "",
    expected_owner_id: str = "",
    expected_source_fingerprint: str = "",
    expected_model_fingerprint: str = "",
    expected_toolchain_fingerprint: str = "",
    expected_environment_fingerprint: str = "",
    require_receipts: bool = True,
) -> tuple[FaultMatrixFinding, ...]:
    """Validate one finite matrix and return stable, actionable findings."""

    findings: list[FaultMatrixFinding] = []
    if not isinstance(payload, Mapping):
        return (FaultMatrixFinding("fault_matrix_shape_invalid", path="$", detail="object required"),)
    if payload.get("schema_version") != FAULT_MATRIX_SCHEMA:
        findings.append(FaultMatrixFinding("fault_matrix_schema_mismatch", path="$.schema_version", detail=FAULT_MATRIX_SCHEMA))
    for field in ("matrix_id", "subject_fingerprint", "claim_boundary"):
        if not _text(payload.get(field)):
            findings.append(FaultMatrixFinding("fault_matrix_required_field_missing", path=f"$.{field}"))
    subject = _text(payload.get("subject_fingerprint"))
    if subject and not is_sha256_fingerprint(subject):
        findings.append(FaultMatrixFinding("fault_matrix_subject_fingerprint_invalid", path="$.subject_fingerprint"))
    if expected_input_fingerprint and subject != expected_input_fingerprint:
        findings.append(FaultMatrixFinding("fault_matrix_input_identity_mismatch", path="$.subject_fingerprint", detail=expected_input_fingerprint))
    declared_ids = _ids(payload.get("required_case_ids"), path="$.required_case_ids", findings=findings)
    rows = payload.get("cases")
    if not isinstance(rows, list) or not rows:
        findings.append(FaultMatrixFinding("fault_matrix_cases_missing", path="$.cases", detail="at least one case is required"))
        rows = []
    row_ids: list[str] = []
    for index, raw in enumerate(rows):
        path = f"$.cases[{index}]"
        if not isinstance(raw, Mapping):
            findings.append(FaultMatrixFinding("fault_case_shape_invalid", path=path, detail="object required"))
            continue
        case_id = _text(raw.get("case_id"))
        if not case_id:
            findings.append(FaultMatrixFinding("fault_case_id_missing", path=f"{path}.case_id"))
            continue
        if case_id in row_ids:
            findings.append(FaultMatrixFinding("fault_case_id_duplicate", case_id=case_id, path=f"{path}.case_id"))
        row_ids.append(case_id)
        fault_class = _text(raw.get("fault_class"))
        if fault_class not in FAULT_MATRIX_FAULT_CLASSES:
            findings.append(FaultMatrixFinding("fault_case_class_invalid", case_id=case_id, path=f"{path}.fault_class", detail=fault_class))
        execution = _text(raw.get("execution_status"))
        outcome = _text(raw.get("outcome"))
        if execution not in FAULT_MATRIX_EXECUTION_STATES:
            findings.append(FaultMatrixFinding("fault_case_execution_state_invalid", case_id=case_id, path=f"{path}.execution_status"))
        if outcome not in FAULT_MATRIX_OUTCOMES:
            findings.append(FaultMatrixFinding("fault_case_outcome_invalid", case_id=case_id, path=f"{path}.outcome"))
        if execution == "not_run" and outcome != "not_run":
            findings.append(FaultMatrixFinding("fault_case_not_run_outcome_mismatch", case_id=case_id, path=path))
        if execution != "not_run" and outcome == "not_run":
            findings.append(FaultMatrixFinding("fault_case_missing_terminal_outcome", case_id=case_id, path=path))
        required = raw.get("required", True)
        if not isinstance(required, bool):
            findings.append(FaultMatrixFinding("fault_case_required_invalid", case_id=case_id, path=f"{path}.required"))
        for field in ("root_cause", "user_visible_result", "terminal_state"):
            if not _text(raw.get(field)):
                findings.append(FaultMatrixFinding("fault_case_terminal_field_missing", case_id=case_id, path=f"{path}.{field}", detail=field))
        reason = _text(raw.get("reason"))
        if outcome != "passed" and not reason and not _text(raw.get("root_cause")):
            findings.append(FaultMatrixFinding("fault_case_failure_reason_missing", case_id=case_id, path=path))
        recovery_required = bool(raw.get("recovery_required", fault_class in {"retry", "recovery", "partial_write", "timeout"}))
        recovery_outcome = _text(raw.get("recovery_outcome"))
        if recovery_required and (execution == "not_run" or not recovery_outcome):
            findings.append(FaultMatrixFinding("fault_case_recovery_evidence_missing", case_id=case_id, path=f"{path}.recovery_outcome"))
        if execution != "not_run" and outcome in {"passed", "failed", "blocked"}:
            artifact = coerce_proof_artifact_ref(raw.get("proof_artifact"))
            if artifact is None:
                findings.append(FaultMatrixFinding("fault_case_proof_artifact_missing", case_id=case_id, path=f"{path}.proof_artifact"))
            else:
                expected_artifact_status = "passed" if outcome == "passed" else outcome
                if artifact.result_status != expected_artifact_status:
                    findings.append(FaultMatrixFinding("fault_case_proof_status_mismatch", case_id=case_id, path=f"{path}.proof_artifact.result_status", detail=f"expected {expected_artifact_status}, got {artifact.result_status}"))
                gaps = proof_artifact_integrity_gap_codes(
                    artifact,
                    expected_owner_id=expected_owner_id,
                    expected_source_fingerprint=expected_source_fingerprint,
                    expected_model_fingerprint=expected_model_fingerprint,
                    expected_toolchain_fingerprint=expected_toolchain_fingerprint,
                    expected_environment_fingerprint=expected_environment_fingerprint,
                    require_receipt=require_receipts,
                    require_cleanup_confirmation=True,
                    require_canonical_receipt=require_receipts,
                )
                # A fault row deliberately records a terminal negative
                # result.  The generic proof verifier reports that such a
                # result is not a *passing* proof; that diagnostic is not a
                # missing-material finding for a negative case.  All identity,
                # path, hash, command, receipt, and cleanup findings remain
                # blockers.
                if outcome != "passed":
                    allowed_negative = {
                        "proof_artifact_not_passing",
                        "proof_artifact_nonzero_exit",
                        "proof_receipt_terminal_not_success",
                        "proof_receipt_nonzero_exit",
                    }
                    gaps = tuple(item for item in gaps if item[0] not in allowed_negative)
                findings.extend(FaultMatrixFinding(code, case_id=case_id, path=f"{path}.proof_artifact", detail=detail) for code, detail in gaps)
        stored_row_hash = _text(raw.get("case_fingerprint"))
        if not stored_row_hash or stored_row_hash != _row_fingerprint(raw):
            findings.append(FaultMatrixFinding("fault_case_fingerprint_mismatch", case_id=case_id, path=f"{path}.case_fingerprint"))
    if expected_case_ids is not None:
        expected = {str(item) for item in expected_case_ids}
        declared = set(declared_ids)
        actual = set(row_ids)
        for missing in sorted(expected - actual):
            findings.append(FaultMatrixFinding("fault_case_missing", case_id=missing, path="$.cases"))
        for orphan in sorted(actual - expected):
            findings.append(FaultMatrixFinding("fault_case_orphan", case_id=orphan, path="$.cases"))
        if declared != expected:
            findings.append(FaultMatrixFinding("fault_matrix_denominator_mismatch", path="$.required_case_ids", detail=f"declared={len(declared)} expected={len(expected)}"))
    if set(declared_ids) != set(row_ids):
        findings.append(FaultMatrixFinding("fault_matrix_row_denominator_mismatch", path="$.required_case_ids", detail=f"declared={len(declared_ids)} rows={len(row_ids)}"))
    stored = _text(payload.get("matrix_fingerprint"))
    if not stored:
        findings.append(FaultMatrixFinding("fault_matrix_fingerprint_missing", path="$.matrix_fingerprint"))
    elif stored != fault_matrix_fingerprint(payload):
        findings.append(FaultMatrixFinding("fault_matrix_fingerprint_mismatch", path="$.matrix_fingerprint"))
    return tuple(findings)


def review_fault_matrix(payload: Mapping[str, Any], **kwargs: Any) -> dict[str, Any]:
    findings = validate_fault_matrix(payload, **kwargs)
    return {
        "schema_version": FAULT_MATRIX_SCHEMA,
        "status": "passed" if not findings else "blocked",
        "matrix_id": _text(payload.get("matrix_id")),
        "case_count": len(payload.get("cases", [])) if isinstance(payload.get("cases"), list) else 0,
        "findings": [item.to_dict() for item in findings],
        "claim_boundary": _text(payload.get("claim_boundary")),
    }


def load_fault_matrix(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("fault matrix artifact must be an object")
    return value


__all__ = [
    "FAULT_MATRIX_SCHEMA",
    "FAULT_MATRIX_EXECUTION_STATES",
    "FAULT_MATRIX_OUTCOMES",
    "FAULT_MATRIX_FAULT_CLASSES",
    "FaultMatrixFinding",
    "fault_matrix_fingerprint",
    "validate_fault_matrix",
    "review_fault_matrix",
    "load_fault_matrix",
]
