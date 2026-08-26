"""Build the explicit authoring context for reverse implementation closure.

The reverse source scanner can tell us what is physically present in a target
repository.  It cannot decide whether a function is an external behavior,
which current intent owns it, or which test receipt proves it.  This module is
the small bridge between those two facts: it emits a deterministic catalogue
of the *available current authorities* and the review groups that still need
an author's semantic decision.

It deliberately does not populate a surface mapping.  A generated mapping
would turn names and path similarity into false proof.  Callers must author a
current ``implementation_surface_map.v1`` and pass it to the existing
fail-closed reverse audit.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence


REVERSE_SURFACE_AUTHORING_CONTEXT_SCHEMA = (
    "flowguard.implementation_surface_authoring_context.v1"
)
_ALLOWED_DISPOSITIONS = (
    "governed",
    "internal_proven",
    "retired_proven",
    "not_applicable_proven",
    # A dynamic, ambiguous, or otherwise unresolved source observation may be
    # represented explicitly as a visible gap.  The reverse audit treats this
    # as a blocker; omitting it from the authoring vocabulary would force the
    # author either to invent semantic coverage or to bypass the authoring
    # context entirely.
    "blocked_gap",
)


class ReverseSurfaceAuthoringError(ValueError):
    """Raised when a context would hide or invent reverse-closure rows."""


def _canonical_hash(value: Any) -> str:
    body = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(body).hexdigest()}"


def _string(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReverseSurfaceAuthoringError(f"{field} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, (list, tuple)):
        raise ReverseSurfaceAuthoringError(f"{field} must be an array")
    result = []
    for item in value:
        result.append(_string(item, field=field))
    if len(result) != len(set(result)):
        raise ReverseSurfaceAuthoringError(f"{field} contains duplicate ids")
    return sorted(result)


def _logical_model_id(value: Any) -> str:
    """Project a canonical ledger model path to its logical model id."""

    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return ""
    parts = PurePosixPath(text).parts
    try:
        index = parts.index("owners")
    except ValueError:
        return text
    return str(parts[index + 1]).strip() if index + 1 < len(parts) else text


def _evidence_ids(row: Mapping[str, Any], field: str) -> list[str]:
    evidence = row.get("evidence")
    if evidence is None:
        return []
    if not isinstance(evidence, Mapping):
        raise ReverseSurfaceAuthoringError(
            f"{row.get('commitment_id', '<commitment>')}.evidence must be an object"
        )
    value = evidence.get(field, ())
    if not isinstance(value, (list, tuple)):
        raise ReverseSurfaceAuthoringError(
            f"{row.get('commitment_id', '<commitment>')}.evidence.{field} must be an array"
        )
    return _string_list(value, field=f"{row.get('commitment_id', '<commitment>')}.evidence.{field}")


def _surface_rows(discovery: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    status = discovery.get("status")
    if status != "passed":
        raise ReverseSurfaceAuthoringError(
            "reverse authoring context requires a current terminal discovery pass"
        )
    rows = discovery.get("surfaces")
    if not isinstance(rows, list) or not rows:
        raise ReverseSurfaceAuthoringError(
            "current discovery must contain a non-empty surfaces array"
        )
    result: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise ReverseSurfaceAuthoringError("every discovery surface must be an object")
        surface_id = _string(row.get("surface_id"), field="surface_id")
        if surface_id in seen:
            raise ReverseSurfaceAuthoringError(
                f"discovery contains duplicate surface_id {surface_id!r}"
            )
        seen.add(surface_id)
        _string(row.get("surface_kind"), field=f"{surface_id}.surface_kind")
        _string(row.get("surface_class"), field=f"{surface_id}.surface_class")
        _string(row.get("review_group_id"), field=f"{surface_id}.review_group_id")
        if row.get("review_granularity") not in {"surface", "component"}:
            raise ReverseSurfaceAuthoringError(
                f"{surface_id}.review_granularity must be surface or component"
            )
        result.append(row)
    return sorted(result, key=lambda row: str(row["surface_id"]))


def _commitment_catalog(ledger: Mapping[str, Any]) -> list[dict[str, Any]]:
    commitments = ledger.get("commitments")
    if not isinstance(commitments, list) or not commitments:
        raise ReverseSurfaceAuthoringError(
            "current behavior ledger must contain commitments"
        )
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in commitments:
        if not isinstance(row, Mapping):
            raise ReverseSurfaceAuthoringError("every ledger commitment must be an object")
        commitment_id = _string(row.get("commitment_id"), field="commitment_id")
        if commitment_id in seen:
            raise ReverseSurfaceAuthoringError(
                f"ledger contains duplicate commitment_id {commitment_id!r}"
            )
        seen.add(commitment_id)
        result.append(
            {
                "commitment_id": commitment_id,
                "business_intent_id": _string(
                    row.get("business_intent_id"),
                    field=f"{commitment_id}.business_intent_id",
                ),
                "behavior_plane": _string(
                    row.get("behavior_plane"),
                    field=f"{commitment_id}.behavior_plane",
                ),
                "primary_owner_model_id": _string(
                    row.get("primary_owner_model_id"),
                    field=f"{commitment_id}.primary_owner_model_id",
                ),
                "logical_model_id": _logical_model_id(
                    row.get("primary_owner_model_id")
                ),
                "source_surface_ids": sorted(
                    str(item)
                    for item in row.get("source_surface_ids", ())
                    if isinstance(item, str) and item.strip()
                ),
                "model_obligation_ids": _evidence_ids(
                    row, "model_obligation_ids"
                ),
                "test_evidence_ids": _evidence_ids(row, "test_evidence_ids"),
                "coverage_receipt_ids": _evidence_ids(
                    row, "coverage_receipt_ids"
                ),
                "evidence_state": str(
                    (row.get("evidence") or {}).get("evidence_state", "")
                    if isinstance(row.get("evidence"), Mapping)
                    else ""
                ).strip(),
            }
        )
    return sorted(result, key=lambda row: row["commitment_id"])


def _owner_catalog(bindings: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = bindings.get("bindings")
    if not isinstance(rows, list) or not rows:
        raise ReverseSurfaceAuthoringError(
            "current owner-bindings authority must contain bindings"
        )
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise ReverseSurfaceAuthoringError("every owner binding must be an object")
        route = _string(row.get("owner_route"), field="owner_route")
        if route in seen:
            raise ReverseSurfaceAuthoringError(
                f"owner-bindings contains duplicate owner_route {route!r}"
            )
        seen.add(route)
        model_ids = _string_list(row.get("model_ids", ()), field=f"{route}.model_ids")
        result.append({"owner_route": route, "model_ids": model_ids})
    return sorted(result, key=lambda row: row["owner_route"])


def build_reverse_surface_authoring_context(
    discovery: Mapping[str, Any],
    *,
    ledger: Mapping[str, Any],
    owner_bindings: Mapping[str, Any],
    inventory_id: str = "flowguard-reverse-surface-closure",
) -> dict[str, Any]:
    """Create a deterministic, still-unresolved semantic authoring context.

    The context is intentionally *not* an acceptance map.  It contains the
    complete discovered denominator, grouped at the scanner's approved review
    granularity, plus the current BCL and model-owner catalogues.  No
    ``intent_id``, obligation, test, owner, receipt, or disposition is inferred
    for a source row.
    """

    inventory_id = _string(inventory_id, field="inventory_id")
    rows = _surface_rows(discovery)
    commitments = _commitment_catalog(ledger)
    owners = _owner_catalog(owner_bindings)
    model_obligation_catalog: list[dict[str, Any]] = []
    obligation_owner: dict[str, str] = {}
    for commitment in commitments:
        for obligation_id in commitment["model_obligation_ids"]:
            if obligation_id in obligation_owner:
                raise ReverseSurfaceAuthoringError(
                    "current behavior ledger maps one model obligation to more "
                    f"than one commitment: {obligation_id!r}"
                )
            obligation_owner[obligation_id] = commitment["commitment_id"]
            model_obligation_catalog.append(
                {
                    "obligation_id": obligation_id,
                    "commitment_id": commitment["commitment_id"],
                    "intent_id": commitment["business_intent_id"],
                    "model_owner_id": commitment["logical_model_id"],
                    "status": "current",
                    "semantic_status": "needs_author",
                }
            )
    model_obligation_catalog.sort(key=lambda row: row["obligation_id"])
    groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        group_id = str(row["review_group_id"])
        group = groups.setdefault(
            group_id,
            {
                "review_group_id": group_id,
                "review_granularity": row["review_granularity"],
                "surface_ids": [],
                "surface_kinds": set(),
                "surface_classes": set(),
                "source_paths": set(),
            },
        )
        if group["review_granularity"] != row["review_granularity"]:
            raise ReverseSurfaceAuthoringError(
                f"review group {group_id!r} mixes surface and component granularity"
            )
        group["surface_ids"].append(str(row["surface_id"]))
        group["surface_kinds"].add(str(row["surface_kind"]))
        group["surface_classes"].add(str(row["surface_class"]))
        group["source_paths"].add(str(row.get("source_path", "")))
    normalized_groups = []
    for group_id, group in sorted(groups.items()):
        normalized_groups.append(
            {
                "review_group_id": group_id,
                "review_granularity": group["review_granularity"],
                "surface_ids": sorted(group["surface_ids"]),
                "surface_count": len(group["surface_ids"]),
                "surface_kinds": sorted(group["surface_kinds"]),
                "surface_classes": sorted(group["surface_classes"]),
                "source_paths": sorted(group["source_paths"]),
                "semantic_status": "needs_author",
            }
        )
    kind_counts = Counter(str(row["surface_kind"]) for row in rows)
    class_counts = Counter(str(row["surface_class"]) for row in rows)
    return {
        "schema_version": REVERSE_SURFACE_AUTHORING_CONTEXT_SCHEMA,
        "inventory_id": inventory_id,
        "status": "authoring_required",
        "semantic_authority": "human_or_target_model_owner",
        "claim_boundary": (
            "Current source-surface denominator and authority catalogues only; "
            "no source row is considered mapped until an independently authored "
            "implementation_surface_map.v1 passes the reverse audit."
        ),
        "no_fallback_policy": (
            "A stale or unknown identity blocks direct-current authoring; this "
            "context never reads an older map, alias, or compatibility projection."
        ),
        "discovery_fingerprint": _string(
            discovery.get("discovery_fingerprint"),
            field="discovery_fingerprint",
        ),
        "discovered_surface_count": len(rows),
        "discovered_surface_ids": [str(row["surface_id"]) for row in rows],
        "surface_kind_counts": dict(sorted(kind_counts.items())),
        "surface_class_counts": dict(sorted(class_counts.items())),
        "review_groups": normalized_groups,
        "current_intent_catalog": commitments,
        "current_model_obligation_catalog": model_obligation_catalog,
        "current_model_owner_catalog": owners,
        "required_surface_fields": [
            "disposition",
            "intent_id",
            "model_obligation_ids",
            "model_owner_id",
            "owner",
            "test_refs",
            "receipt_refs",
        ],
        "required_model_obligation_fields": [
            "obligation_id",
            "disposition",
            "surface_ids",
            "intent_id",
            "model_owner_id",
            "proof_ref",
            "reason",
        ],
        "allowed_surface_dispositions": list(_ALLOWED_DISPOSITIONS),
        "mapping_artifact": {
            "schema_version": "flowguard.implementation_surface_map.v1",
            "path": ".flowguard/structure/reverse-surfaces/implementation-surface-map.json",
            "status": "not_supplied",
        },
    }


def validate_reverse_surface_authoring_context(
    context: Mapping[str, Any],
    discovery: Mapping[str, Any],
    *,
    ledger: Mapping[str, Any],
    owner_bindings: Mapping[str, Any],
) -> dict[str, Any]:
    """Check context identity and conservation without granting semantics."""

    findings: list[dict[str, Any]] = []
    try:
        expected = build_reverse_surface_authoring_context(
            discovery,
            ledger=ledger,
            owner_bindings=owner_bindings,
            inventory_id=str(context.get("inventory_id", "flowguard-reverse-surface-closure")),
        )
    except ReverseSurfaceAuthoringError as exc:
        return {
            "schema_version": "flowguard.reverse_surface_authoring_validation.v1",
            "status": "blocked",
            "findings": [{"code": "authoring_context_input_invalid", "message": str(exc)}],
        }
    if context.get("schema_version") != REVERSE_SURFACE_AUTHORING_CONTEXT_SCHEMA:
        findings.append({"code": "authoring_context_schema_stale", "message": "authoring context schema is not current"})
    for field in ("discovery_fingerprint", "discovered_surface_count", "discovered_surface_ids"):
        if context.get(field) != expected.get(field):
            findings.append({"code": "authoring_context_identity_mismatch", "field": field, "message": f"{field} does not match current discovery"})
    if context.get("review_groups") != expected.get("review_groups"):
        findings.append({"code": "authoring_context_group_denominator_mismatch", "message": "review groups do not conserve the current discovered surface denominator"})
    if context.get("current_intent_catalog") != expected.get("current_intent_catalog"):
        findings.append({"code": "authoring_context_intent_catalog_stale", "message": "intent catalogue is not the current ledger projection"})
    if context.get("current_model_obligation_catalog") != expected.get("current_model_obligation_catalog"):
        findings.append({"code": "authoring_context_model_obligation_catalog_stale", "message": "model-obligation catalogue is not the current ledger projection"})
    if context.get("current_model_owner_catalog") != expected.get("current_model_owner_catalog"):
        findings.append({"code": "authoring_context_owner_catalog_stale", "message": "model-owner catalogue is not the current owner-bindings projection"})
    if context.get("status") != "authoring_required":
        findings.append({"code": "authoring_context_status_invalid", "message": "context cannot claim semantic closure"})
    return {
        "schema_version": "flowguard.reverse_surface_authoring_validation.v1",
        "status": "passed" if not findings else "blocked",
        "discovery_fingerprint": expected["discovery_fingerprint"],
        "discovered_surface_count": expected["discovered_surface_count"],
        "findings": findings,
        "claim_boundary": "identity/conservation validation only; semantic mapping still requires the reverse audit",
    }


__all__ = [
    "REVERSE_SURFACE_AUTHORING_CONTEXT_SCHEMA",
    "ReverseSurfaceAuthoringError",
    "build_reverse_surface_authoring_context",
    "validate_reverse_surface_authoring_context",
]
