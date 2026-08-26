from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile

from flowguard.fault_matrix_evidence import (
    _row_fingerprint,
    fault_matrix_fingerprint,
    validate_fault_matrix,
)
from flowguard.evidence_receipts import EvidenceReceipt, fingerprint_value, snapshot_bytes


def _sha(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _valid_matrix(tmp: Path) -> dict[str, object]:
    result = tmp / "result.json"
    result.write_text('{"status":"passed"}\n', encoding="utf-8")
    result_hash = _sha(result.read_bytes())
    environment_metadata = {"platform_system": "test"}
    environment_fingerprint = fingerprint_value(environment_metadata)
    receipt = EvidenceReceipt(
        receipt_id="receipt:fault-1",
        subject_id="fault-1",
        subject_kind="fault_case",
        producer_id="owner:fault",
        producer_version="test",
        claim_scope="fault_matrix",
        command=("native-fault-runner", "--case", "fault-1"),
        working_directory_token="<WORKSPACE>",
        started_at="2026-08-18T00:00:00+00:00",
        finished_at="2026-08-18T00:00:01+00:00",
        exit_code=0,
        environment_fingerprint=environment_fingerprint,
        environment_metadata=environment_metadata,
        contract_hash=_sha(b"contract"),
        check_manifest_hash=_sha(b"manifest"),
        suite_map_hash=_sha(b"suite"),
        input_snapshots=(
            snapshot_bytes(
                "input:fault-1",
                b"subject",
                path_token="<SUBJECT>",
                obligation_ids=("fault-1",),
            ),
        ),
        proof_artifact_id="artifact:fault-1",
        proof_artifact_fingerprint=result_hash,
        result_status="pass",
        result_fingerprint=result_hash,
        covered_obligations=("fault-1",),
        claim_boundary="one finite native fault case",
        metadata={
            "source_fingerprint": _sha(b"source"),
            "model_fingerprint": _sha(b"model"),
            "toolchain_fingerprint": _sha(b"toolchain"),
            "subject_fingerprint": _sha(b"subject"),
            "terminal_state": "passed",
            "cleanup_verified": True,
        },
    )
    receipt_path = tmp / "receipt.json"
    receipt_path.write_text(receipt.to_json(), encoding="utf-8")
    row: dict[str, object] = {
        "case_id": "fault-1",
        "fault_class": "invalid_input",
        "required": True,
        "execution_status": "executed",
        "outcome": "passed",
        "root_cause": "input schema rejected",
        "user_visible_result": "clear validation error",
        "terminal_state": "passed",
        "reason": "",
        "recovery_required": False,
        "recovery_outcome": "not_applicable",
        "proof_artifact": {
            "artifact_id": "artifact:fault-1",
            "producer_route": "fault-route",
            "command": "native-fault-runner --case fault-1",
            "result_path": str(result),
            "result_status": "passed",
            "exit_code": 0,
            "started_at": "2026-08-18T00:00:00+00:00",
            "finished_at": "2026-08-18T00:00:01+00:00",
            "subject_id": "fault-1",
            "subject_fingerprint": _sha(b"subject"),
            "artifact_fingerprints": {"result": result_hash},
            "receipt_id": "receipt:fault-1",
            "receipt_path": str(receipt_path),
            "receipt_fingerprint": _sha(receipt_path.read_bytes()),
            "execution_owner_id": "owner:fault",
            "source_fingerprint": _sha(b"source"),
            "model_fingerprint": _sha(b"model"),
            "toolchain_fingerprint": _sha(b"toolchain"),
            "environment_fingerprint": environment_fingerprint,
            "result_fingerprint": result_hash,
            "terminal_state": "passed",
            "cleanup_verified": True,
        },
    }
    row["case_fingerprint"] = ""  # filled after row construction
    row["case_fingerprint"] = _row_fingerprint(row)
    payload: dict[str, object] = {
        "schema_version": "flowguard.fault_matrix_evidence.v1",
        "matrix_id": "matrix:test",
        "subject_fingerprint": _sha(b"subject"),
        "required_case_ids": ["fault-1"],
        "cases": [row],
        "claim_boundary": "one finite native fault case",
    }
    payload["matrix_fingerprint"] = fault_matrix_fingerprint(payload)
    return payload


def test_fault_matrix_requires_real_leaf_and_recovery_facts() -> None:
    with tempfile.TemporaryDirectory() as directory:
        payload = _valid_matrix(Path(directory))
        assert validate_fault_matrix(
            payload,
            expected_case_ids=["fault-1"],
            expected_input_fingerprint=_sha(b"subject"),
            expected_owner_id="owner:fault",
            expected_source_fingerprint=_sha(b"source"),
            expected_model_fingerprint=_sha(b"model"),
            expected_toolchain_fingerprint=_sha(b"toolchain"),
            expected_environment_fingerprint=fingerprint_value({"platform_system": "test"}),
        ) == ()


def test_fault_matrix_rejects_hash_reseal_and_missing_recovery() -> None:
    with tempfile.TemporaryDirectory() as directory:
        payload = _valid_matrix(Path(directory))
        row = payload["cases"][0]
        assert isinstance(row, dict)
        row["fault_class"] = "timeout"
        row["recovery_required"] = True
        row["recovery_outcome"] = ""
        row["case_fingerprint"] = _row_fingerprint(row)
        payload["matrix_fingerprint"] = fault_matrix_fingerprint(payload)
        codes = {item.code for item in validate_fault_matrix(payload)}
        assert "fault_case_recovery_evidence_missing" in codes


def test_fault_matrix_rejects_missing_case_and_fake_proof_path() -> None:
    with tempfile.TemporaryDirectory() as directory:
        payload = _valid_matrix(Path(directory))
        row = payload["cases"][0]
        assert isinstance(row, dict)
        proof = row["proof_artifact"]
        assert isinstance(proof, dict)
        proof["result_path"] = str(Path(directory) / "does-not-exist.json")
        row["case_fingerprint"] = _row_fingerprint(row)
        payload["matrix_fingerprint"] = fault_matrix_fingerprint(payload)
        codes = {item.code for item in validate_fault_matrix(payload, expected_case_ids=["fault-1", "fault-2"])}
        assert "fault_case_missing" in codes
        assert "proof_result_path_missing" in codes
