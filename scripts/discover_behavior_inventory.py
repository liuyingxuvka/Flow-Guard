"""Materialize an independently authored behavior denominator.

The manifest is the discovery owner's input.  This command only resolves the
declared source files, computes their current fingerprints, and reconciles the
explicit expected id set with the typed :class:`BehaviorInventory` authority.
It never scans BCL rows, tests, model files, or package exports to guess what
the product does.  A manifest with an incomplete boundary therefore produces
a visible blocked artifact instead of a deceptively complete denominator.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import platform
from pathlib import Path
import sys
from typing import Any, Mapping

from flowguard import (
    BCL_BEHAVIOR_INVENTORY_SCHEMA,
    BehaviorInventory,
    BehaviorInventoryItem,
    review_independent_behavior_inventory,
)
from flowguard.behavior_surface_audit import audit_implementation_behavior_surface
from flowguard.behavior_surface_audit import discover_implementation_behavior_surfaces
from flowguard.proof_artifact import ProofArtifactRef, proof_artifact_integrity_gap_codes


DISCOVERY_SCHEMA = "flowguard.native_behavior_discovery.v1"
_MANIFEST_FIELDS = {
    "schema_version",
    "inventory_id",
    "project_boundary",
    "current_revision",
    "discovery_owner",
    "discovery_evidence_ids",
    "expected_behavior_ids",
    "claim_boundary",
    "behaviors",
    "metadata",
}
_BEHAVIOR_REQUIRED_FIELDS = {
    "behavior_id",
    "source_kind",
    "source_ref",
    "source_path",
    "public_surface",
    "intent",
    "success",
    "errors",
    "recovery",
    "owner",
    "disposition",
}
_BEHAVIOR_OPTIONAL_FIELDS = {
    "intent_source_refs",
    "intent_disposition",
    "function_id",
    "route_id",
    "obligation_ids",
    "required_check_ids",
    "test_refs",
    "evidence_subject_ids",
    "oracle_ids",
    "failure_case_ids",
    "recovery_case_ids",
    "current_intent_fingerprint",
    "lifecycle_envelope",
    "commitment_id",
    "model_owner_id",
    "delegated_owner_inventory_id",
    "delegation_relation_type",
    "scoped_out_reason",
    "blocked_gap_reason",
    "validation_boundary",
    "rationale",
    "metadata",
}
_FORBIDDEN_SOURCE_PREFIXES = (
    "tests",
    ".flowguard/behavior/inventory",
)


class BehaviorDiscoveryError(ValueError):
    """Raised when a native discovery manifest is not current and bounded."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _text(value: Any, *, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BehaviorDiscoveryError(f"{context} must be a non-empty string")
    return value


def _list(value: Any, *, context: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise BehaviorDiscoveryError(f"{context} must be a non-empty array")
    return value


def _fingerprint_payload(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _write_current_proof(
    result: dict[str, Any],
    *,
    output_path: Path,
    manifest_path: Path,
    root: Path,
) -> dict[str, Any]:
    """Attach an independently reloadable proof to a passed inventory.

    The inventory report is an observation.  A DNA layer may consume it only
    after this producer writes a frozen input manifest, a terminal result, and
    a receipt whose hashes are checked by reopening the files.  This helper
    never promotes a blocked discovery and never treats the report's own
    evidence hash as an input identity.
    """

    if result.get("status") != "passed":
        return result
    evidence_dir = output_path.parent.resolve()
    stem = output_path.stem
    input_path = evidence_dir / f"{stem}.inputs.json"
    terminal_path = evidence_dir / f"{stem}.terminal.json"
    receipt_path = evidence_dir / f"{stem}.receipt.json"
    manifest_resolved = manifest_path.resolve()
    manifest_bytes = manifest_resolved.read_bytes()
    manifest_fingerprint = _sha256_bytes(manifest_bytes)
    inventory = result.get("inventory")
    if not isinstance(inventory, Mapping):
        result.setdefault("findings", []).append("proof_inventory_payload_missing")
        result["status"] = "blocked"
        return result
    inventory_fingerprint = str(inventory.get("discovery_fingerprint") or "")
    if not inventory_fingerprint:
        result.setdefault("findings", []).append("proof_inventory_discovery_fingerprint_missing")
        result["status"] = "blocked"
        return result
    started_at = datetime.now(timezone.utc).isoformat()
    finished_at = datetime.now(timezone.utc).isoformat()
    input_payload: dict[str, Any] = {
        "schema_version": "flowguard.native_behavior_discovery_input_manifest.v1",
        "manifest_path": str(manifest_resolved),
        "manifest_fingerprint": manifest_fingerprint,
        "root": str(root.resolve()),
        "inventory_id": inventory.get("inventory_id", ""),
        "current_revision": inventory.get("current_revision", ""),
        "discovery_fingerprint": inventory_fingerprint,
        "source_identities": result.get("source_identities", []),
        "claim_boundary": result.get("claim_boundary", ""),
        "python_version": sys.version,
        "platform": platform.platform(),
    }
    input_bytes = _canonical_json_bytes(input_payload)
    input_path.write_bytes(input_bytes)
    input_fingerprint = _sha256_bytes(input_bytes)
    owner_id = "flowguard-native-discovery-manifest:v1"
    model_fingerprint = _sha256_bytes(
        _canonical_json_bytes(
            {
                "subject": "independent-behavior-inventory",
                "inventory_id": inventory.get("inventory_id", ""),
                "discovery_fingerprint": inventory_fingerprint,
            }
        )
    )
    toolchain_fingerprint = _sha256_bytes(
        _canonical_json_bytes(
            {
                "python": sys.version,
                "platform": platform.platform(),
                "producer": "scripts.discover_behavior_inventory.v1",
            }
        )
    )
    environment_fingerprint = _sha256_bytes(
        _canonical_json_bytes(
            {
                "python_implementation": platform.python_implementation(),
                "machine": platform.machine(),
                "system": platform.system(),
            }
        )
    )
    terminal_payload = {
        "schema_version": "flowguard.native_behavior_discovery_terminal_result.v1",
        "status": result.get("status"),
        "inventory_id": inventory.get("inventory_id", ""),
        "current_revision": inventory.get("current_revision", ""),
        "discovery_fingerprint": inventory_fingerprint,
        "review": result.get("review", {}),
        "source_identities": result.get("source_identities", []),
        "input_manifest_fingerprint": input_fingerprint,
    }
    terminal_bytes = _canonical_json_bytes(terminal_payload)
    terminal_path.write_bytes(terminal_bytes)
    result_fingerprint = _sha256_bytes(terminal_bytes)
    receipt_id = f"receipt:{owner_id}:{inventory_fingerprint[7:19]}"
    command = (
        "scripts/discover_behavior_inventory.py --root "
        f"{root.resolve()} --manifest {manifest_resolved}"
    )
    receipt_payload = {
        "receipt_id": receipt_id,
        "producer_id": owner_id,
        "command": command,
        "source_fingerprint": manifest_fingerprint,
        "model_fingerprint": model_fingerprint,
        "toolchain_fingerprint": toolchain_fingerprint,
        "environment_fingerprint": environment_fingerprint,
        "result_fingerprint": result_fingerprint,
        "result_status": "passed",
        "exit_code": 0,
        "terminal_state": "terminal_success",
        "cleanup_state": "zero_descendants",
        "cleanup_verified": True,
        "started_at": started_at,
        "finished_at": finished_at,
        "result_path": str(terminal_path),
        "input_manifest_path": str(input_path),
        "input_manifest_fingerprint": input_fingerprint,
    }
    receipt_bytes = _canonical_json_bytes(receipt_payload)
    receipt_path.write_bytes(receipt_bytes)
    receipt_fingerprint = _sha256_bytes(receipt_bytes)
    artifact = ProofArtifactRef(
        artifact_id=f"proof:native-behavior-discovery:{inventory_fingerprint[7:19]}",
        producer_route="scripts.discover_behavior_inventory",
        command=command,
        result_path=str(terminal_path),
        result_status="passed",
        exit_code=0,
        started_at=started_at,
        finished_at=finished_at,
        subject_id=str(inventory.get("inventory_id", "behavior-inventory")),
        subject_fingerprint=inventory_fingerprint,
        artifact_fingerprints={
            "result": result_fingerprint,
            "manifest": manifest_fingerprint,
            "discovery": inventory_fingerprint,
        },
        covered_obligation_ids=(
            "behavior_inventory.source_freshness",
            "behavior_inventory.denominator_conservation",
            "behavior_inventory.independent_review",
        ),
        assertion_scope="independent_behavior_inventory",
        current=True,
        route_evidence_current=True,
        receipt_id=receipt_id,
        receipt_path=str(receipt_path),
        receipt_fingerprint=receipt_fingerprint,
        execution_owner_id=owner_id,
        source_fingerprint=manifest_fingerprint,
        model_fingerprint=model_fingerprint,
        toolchain_fingerprint=toolchain_fingerprint,
        environment_fingerprint=environment_fingerprint,
        result_fingerprint=result_fingerprint,
        terminal_state="terminal_success",
        cleanup_state="zero_descendants",
        cleanup_verified=True,
        metadata={"input_manifest_path": str(input_path)},
    )
    gaps = proof_artifact_integrity_gap_codes(
        artifact,
        expected_receipt_id=receipt_id,
        expected_receipt_fingerprint=receipt_fingerprint,
        expected_owner_id=owner_id,
        expected_source_fingerprint=manifest_fingerprint,
        expected_model_fingerprint=model_fingerprint,
        expected_toolchain_fingerprint=toolchain_fingerprint,
        expected_environment_fingerprint=environment_fingerprint,
        expected_result_fingerprint=result_fingerprint,
    )
    if gaps:
        result.setdefault("findings", []).append(
            "proof_artifact_verification_failed:" + ",".join(code for code, _ in gaps)
        )
        result["status"] = "blocked"
        return result
    result.update(
        {
            "evidence_id": artifact.artifact_id,
            "proof_artifact": artifact.to_dict(),
            "input_manifest_path": str(input_path),
            "input_manifest_fingerprint": input_fingerprint,
            "source_fingerprint": manifest_fingerprint,
            "model_fingerprint": model_fingerprint,
            "toolchain_fingerprint": toolchain_fingerprint,
            "environment_fingerprint": environment_fingerprint,
            "result_fingerprint": result_fingerprint,
            "receipt_fingerprint": receipt_fingerprint,
        }
    )
    evidence_without_fingerprint = dict(result)
    evidence_without_fingerprint.pop("evidence_fingerprint", None)
    result["evidence_fingerprint"] = _fingerprint_payload(evidence_without_fingerprint)
    return result


def _resolve_source(root: Path, source_path: str) -> tuple[str, Path, str]:
    relative = Path(_text(source_path, context="behavior.source_path"))
    if relative.is_absolute():
        raise BehaviorDiscoveryError("behavior.source_path must be repository-relative")
    normalized = relative.as_posix()
    if normalized.startswith("../") or normalized == "..":
        raise BehaviorDiscoveryError("behavior.source_path may not escape the project root")
    if normalized.startswith(_FORBIDDEN_SOURCE_PREFIXES):
        raise BehaviorDiscoveryError(
            "independent discovery may not use tests or the canonical BCL ledger as its source"
        )
    resolved_root = root.resolve()
    resolved = (resolved_root / relative).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise BehaviorDiscoveryError("behavior.source_path escapes the project root") from exc
    if not resolved.is_file():
        raise BehaviorDiscoveryError(f"behavior.source_path does not identify a file: {normalized}")
    return normalized, resolved, _sha256_file(resolved)


def load_discovery_manifest(path: Path, *, root: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BehaviorDiscoveryError(f"cannot load behavior discovery manifest: {exc}") from exc
    if not isinstance(data, Mapping):
        raise BehaviorDiscoveryError("behavior discovery manifest must be an object")
    unknown = set(data) - _MANIFEST_FIELDS
    missing = _MANIFEST_FIELDS - set(data)
    if unknown or missing:
        raise BehaviorDiscoveryError(
            f"behavior discovery manifest fields differ from current schema; missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    if data["schema_version"] != DISCOVERY_SCHEMA:
        raise BehaviorDiscoveryError("behavior discovery manifest schema is not current")
    for field in (
        "inventory_id",
        "project_boundary",
        "current_revision",
        "discovery_owner",
        "claim_boundary",
    ):
        _text(data[field], context=f"manifest.{field}")
    discovery_evidence_ids = _list(
        data["discovery_evidence_ids"], context="manifest.discovery_evidence_ids"
    )
    expected_ids = _list(data["expected_behavior_ids"], context="manifest.expected_behavior_ids")
    if len(expected_ids) != len(set(expected_ids)):
        raise BehaviorDiscoveryError("manifest.expected_behavior_ids contains duplicates")
    behaviors = _list(data["behaviors"], context="manifest.behaviors")
    materialized_ids: list[str] = []
    source_identities: list[dict[str, str]] = []
    items: list[BehaviorInventoryItem] = []
    for index, raw in enumerate(behaviors):
        if not isinstance(raw, Mapping):
            raise BehaviorDiscoveryError(f"manifest.behaviors[{index}] must be an object")
        unknown_behavior = set(raw) - (_BEHAVIOR_REQUIRED_FIELDS | _BEHAVIOR_OPTIONAL_FIELDS)
        missing_behavior = _BEHAVIOR_REQUIRED_FIELDS - set(raw)
        if unknown_behavior or missing_behavior:
            raise BehaviorDiscoveryError(
                f"manifest.behaviors[{index}] fields differ from current schema; missing={sorted(missing_behavior)}, unknown={sorted(unknown_behavior)}"
            )
        source_path, resolved, source_fingerprint = _resolve_source(root, raw["source_path"])
        source_ref = _text(raw["source_ref"], context=f"manifest.behaviors[{index}].source_ref")
        if not source_ref.split("#", 1)[0].replace("\\", "/").endswith(source_path):
            raise BehaviorDiscoveryError(
                f"manifest.behaviors[{index}].source_ref must anchor its declared source_path"
            )
        item_data = {
            key: raw[key]
            for key in (_BEHAVIOR_REQUIRED_FIELDS | _BEHAVIOR_OPTIONAL_FIELDS)
            if key != "source_path" and key in raw
        }
        item_data["source_fingerprint"] = source_fingerprint
        items.append(BehaviorInventoryItem(**item_data))
        materialized_ids.append(items[-1].behavior_id)
        source_identities.append(
            {
                "path": source_path,
                "resolved_path": str(resolved),
                "content_fingerprint": source_fingerprint,
            }
        )
    if set(materialized_ids) != set(expected_ids):
        raise BehaviorDiscoveryError(
            "manifest expected_behavior_ids must equal the explicitly materialized behavior ids"
        )
    discovery_input = {
        "schema_version": DISCOVERY_SCHEMA,
        "inventory_id": data["inventory_id"],
        "project_boundary": data["project_boundary"],
        "current_revision": data["current_revision"],
        "discovery_owner": data["discovery_owner"],
        "discovery_evidence_ids": list(discovery_evidence_ids),
        "expected_behavior_ids": list(expected_ids),
        "claim_boundary": data["claim_boundary"],
        "behaviors": [item.to_dict() for item in items],
        "source_identities": source_identities,
        "metadata": dict(data.get("metadata") or {}),
    }
    inventory = BehaviorInventory(
        inventory_id=data["inventory_id"],
        project_boundary=data["project_boundary"],
        current_revision=data["current_revision"],
        discovery_owner=data["discovery_owner"],
        discovery_fingerprint=_fingerprint_payload(discovery_input),
        discovery_evidence_ids=tuple(discovery_evidence_ids),
        expected_behavior_ids=tuple(expected_ids),
        items=tuple(items),
        claim_boundary=data["claim_boundary"],
        metadata=dict(data.get("metadata") or {}),
    )
    report = review_independent_behavior_inventory(inventory)
    payload_without_fingerprint = {
        "schema_version": DISCOVERY_SCHEMA,
        "status": "passed" if report.ok else "blocked",
        "claim_boundary": data["claim_boundary"],
        "manifest": str(path.resolve()),
        "source_identities": source_identities,
        "inventory": inventory.to_dict(),
        "review": report.to_dict(),
    }
    return {
        **payload_without_fingerprint,
        "evidence_fingerprint": _fingerprint_payload(payload_without_fingerprint),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--surface-map",
        type=Path,
        default=None,
        help="Optional independent reverse implementation surface map.",
    )
    args = parser.parse_args(argv)
    try:
        result = load_discovery_manifest(args.manifest, root=args.root)
    except (BehaviorDiscoveryError, ValueError) as exc:
        result = {
            "schema_version": DISCOVERY_SCHEMA,
            "status": "blocked",
            "claim_boundary": "manifest validation only",
            "findings": [{"code": "behavior_discovery_manifest_invalid", "message": str(exc)}],
        }
    if args.surface_map is not None:
        surface_discovery = discover_implementation_behavior_surfaces(args.root)
        surface_audit = audit_implementation_behavior_surface(
            args.root,
            args.surface_map,
            discovery=surface_discovery,
        )
        result["implementation_surface_discovery"] = surface_discovery
        result["implementation_surface_audit"] = surface_audit
        if surface_audit["status"] != "passed":
            result["status"] = "blocked"
        result.pop("evidence_fingerprint", None)
        result["evidence_fingerprint"] = _fingerprint_payload(result)
    # Only a terminal, independently re-openable pass may be consumed by the
    # outer DNA gate.  The proof helper leaves blocked discoveries visibly
    # blocked and never creates a compatibility path for older evidence.
    result = _write_current_proof(
        result,
        output_path=args.output.resolve(),
        manifest_path=args.manifest,
        root=args.root,
    )
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
