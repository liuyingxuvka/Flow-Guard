"""Materialize an explicitly authored reverse-surface semantic map.

The source-only reverse scanner and the authoring context deliberately stop
before assigning meaning.  This module is the narrow, current-only handoff
between an owner (human or target model owner) and the existing
``implementation_surface_map.v1`` audit:

* every observed surface is covered exactly once, either by an individual
  decision or by a complete component-group decision;
* every model obligation is supplied by the current authority catalogue and
  points back to the exact surfaces that name it;
* no intent, owner, test, receipt, or proof value is inferred from source
  names, paths, review groups, or historical rows; and
* stale, unknown, duplicate, or one-way inputs fail before a map is emitted.

The result is still an authored input, not an acceptance claim.  Callers must
run :func:`flowguard.behavior_surface_audit.audit_implementation_behavior_surface`
against the emitted map and current target root.  There is intentionally no
legacy reader, alias, migration, or fallback path.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence


REVERSE_SURFACE_SEMANTIC_AUTHORING_SCHEMA = (
    "flowguard.implementation_surface_semantic_authoring.v1"
)
IMPLEMENTATION_SURFACE_MAP_SCHEMA = "flowguard.implementation_surface_map.v1"

_SURFACE_DISPOSITIONS = frozenset(
    {
        "governed",
        "internal_proven",
        "retired_proven",
        "not_applicable_proven",
        "blocked_gap",
    }
)
_OBLIGATION_DISPOSITIONS = frozenset(
    {
        "governed",
        "model_only_proven",
        "retired_proven",
        "not_applicable_proven",
        "blocked_gap",
    }
)
_NON_GOVERNED_SURFACE_DISPOSITIONS = frozenset(
    {"retired_proven", "not_applicable_proven", "blocked_gap"}
)


class ReverseSurfaceSemanticAuthoringError(ValueError):
    """Raised when explicit semantic authoring cannot be safely materialized."""


def _text(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReverseSurfaceSemanticAuthoringError(f"{field} must be a non-empty string")
    return value.strip()


def _ids(value: Any, *, field: str, required: bool = False) -> list[str]:
    if not isinstance(value, (list, tuple)):
        raise ReverseSurfaceSemanticAuthoringError(f"{field} must be an array")
    result = []
    for index, item in enumerate(value):
        result.append(_text(item, field=f"{field}[{index}]"))
    if len(result) != len(set(result)):
        raise ReverseSurfaceSemanticAuthoringError(f"{field} contains duplicate ids")
    if required and not result:
        raise ReverseSurfaceSemanticAuthoringError(f"{field} must not be empty")
    return sorted(result)


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _discovery_rows(discovery: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    fingerprint = _text(
        discovery.get("discovery_fingerprint"), field="discovery.discovery_fingerprint"
    )
    if not fingerprint.startswith("sha256:"):
        raise ReverseSurfaceSemanticAuthoringError(
            "discovery.discovery_fingerprint must be a current sha256 identity"
        )
    if discovery.get("status") not in {"passed", "blocked"}:
        raise ReverseSurfaceSemanticAuthoringError(
            "semantic authoring requires a current terminal discovery or a complete blocked discovery"
        )
    raw_rows = discovery.get("surfaces")
    if not isinstance(raw_rows, list) or not raw_rows:
        raise ReverseSurfaceSemanticAuthoringError(
            "discovery.surfaces must be a non-empty array"
        )
    rows: dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(raw_rows):
        if not isinstance(row, Mapping):
            raise ReverseSurfaceSemanticAuthoringError(
                f"discovery.surfaces[{index}] must be an object"
            )
        surface_id = _text(row.get("surface_id"), field=f"surface[{index}].surface_id")
        if surface_id in rows:
            raise ReverseSurfaceSemanticAuthoringError(
                f"discovery contains duplicate surface_id {surface_id!r}"
            )
        _text(row.get("surface_kind"), field=f"{surface_id}.surface_kind")
        _text(row.get("surface_class"), field=f"{surface_id}.surface_class")
        _text(row.get("review_group_id"), field=f"{surface_id}.review_group_id")
        if row.get("review_granularity") not in {"surface", "component"}:
            raise ReverseSurfaceSemanticAuthoringError(
                f"{surface_id}.review_granularity must be surface or component"
            )
        rows[surface_id] = row
    return rows


def _context_groups(
    context: Mapping[str, Any], rows: Mapping[str, Mapping[str, Any]]
) -> dict[str, tuple[str, tuple[str, ...]]]:
    if context.get("discovery_fingerprint") != _text(
        # The call is intentionally repeated so a missing value cannot be
        # replaced by the current discovery through a truthiness fallback.
        context.get("discovery_fingerprint"),
        field="authoring_context.discovery_fingerprint",
    ):
        raise ReverseSurfaceSemanticAuthoringError(
            "authoring context discovery identity is missing"
        )
    raw_groups = context.get("review_groups")
    if not isinstance(raw_groups, list) or not raw_groups:
        raise ReverseSurfaceSemanticAuthoringError(
            "authoring_context.review_groups must be a non-empty array"
        )
    groups: dict[str, tuple[str, tuple[str, ...]]] = {}
    seen_members: set[str] = set()
    for index, group in enumerate(raw_groups):
        if not isinstance(group, Mapping):
            raise ReverseSurfaceSemanticAuthoringError(
                f"authoring_context.review_groups[{index}] must be an object"
            )
        group_id = _text(group.get("review_group_id"), field=f"review_group[{index}].review_group_id")
        granularity = _text(
            group.get("review_granularity"), field=f"{group_id}.review_granularity"
        )
        members = tuple(_ids(group.get("surface_ids"), field=f"{group_id}.surface_ids", required=True))
        if group_id in groups:
            raise ReverseSurfaceSemanticAuthoringError(
                f"authoring_context contains duplicate review_group_id {group_id!r}"
            )
        if any(member not in rows for member in members):
            unknown = sorted(member for member in members if member not in rows)
            raise ReverseSurfaceSemanticAuthoringError(
                f"review group {group_id!r} contains unknown surfaces: {unknown!r}"
            )
        overlap = sorted(set(members) & seen_members)
        if overlap:
            raise ReverseSurfaceSemanticAuthoringError(
                f"review groups overlap current surfaces: {overlap!r}"
            )
        seen_members.update(members)
        expected = tuple(
            sorted(
                surface_id
                for surface_id, row in rows.items()
                if str(row.get("review_group_id", "")).strip() == group_id
            )
        )
        if expected != members:
            raise ReverseSurfaceSemanticAuthoringError(
                f"review group {group_id!r} does not conserve the current discovery members"
            )
        groups[group_id] = (granularity, members)
    if seen_members != set(rows):
        missing = sorted(set(rows) - seen_members)
        raise ReverseSurfaceSemanticAuthoringError(
            f"authoring context review groups omit current surfaces: {missing!r}"
        )
    return groups


def _common_decision_fields(
    decision: Mapping[str, Any], *, target: str
) -> dict[str, Any]:
    disposition = _text(decision.get("disposition"), field=f"{target}.disposition")
    if disposition not in _SURFACE_DISPOSITIONS:
        raise ReverseSurfaceSemanticAuthoringError(
            f"{target}.disposition {disposition!r} is not current"
        )
    owner = _text(decision.get("owner"), field=f"{target}.owner")
    test_refs = _ids(decision.get("test_refs"), field=f"{target}.test_refs", required=True)
    receipt_refs = _ids(
        decision.get("receipt_refs"),
        field=f"{target}.receipt_refs",
        required=disposition != "blocked_gap",
    )
    result: dict[str, Any] = {
        "disposition": disposition,
        "owner": owner,
        "test_refs": test_refs,
        "receipt_refs": receipt_refs,
    }
    if disposition in {"governed", "internal_proven"}:
        result["intent_id"] = _text(decision.get("intent_id"), field=f"{target}.intent_id")
        result["model_owner_id"] = _text(
            decision.get("model_owner_id"), field=f"{target}.model_owner_id"
        )
        result["model_obligation_ids"] = _ids(
            decision.get("model_obligation_ids"),
            field=f"{target}.model_obligation_ids",
            required=True,
        )
        if disposition == "internal_proven":
            # ``internal_proven`` is still a semantic claim.  It must carry
            # the same current proof witness as the audit requires; silently
            # dropping these fields during materialization would turn an
            # explicitly authored proof into a missing-proof blocker.
            result["proof_ref"] = _text(
                decision.get("proof_ref"), field=f"{target}.proof_ref"
            )
            result["reason"] = _text(
                decision.get("reason"), field=f"{target}.reason"
            )
    elif disposition == "blocked_gap":
        result["gap_reason"] = _text(decision.get("gap_reason"), field=f"{target}.gap_reason")
    else:
        result["proof_ref"] = _text(decision.get("proof_ref"), field=f"{target}.proof_ref")
        result["reason"] = _text(decision.get("reason"), field=f"{target}.reason")
        if disposition == "not_applicable_proven":
            result["not_applicable_reason"] = result["reason"]
    for field in ("owner_receipt_id", "owner_receipt_fingerprint"):
        if field in decision:
            result[field] = _text(decision.get(field), field=f"{target}.{field}")
    return result


def _model_obligation_rows(
    value: Any,
    *,
    context: Mapping[str, Any],
    surface_ids: set[str],
    surface_bindings: Mapping[str, set[str]],
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ReverseSurfaceSemanticAuthoringError(
            "model_obligations must be an explicitly authored array"
        )
    catalog = context.get("current_model_obligation_catalog")
    if not isinstance(catalog, list):
        raise ReverseSurfaceSemanticAuthoringError(
            "authoring context must carry current_model_obligation_catalog"
        )
    expected_by_id = {}
    for index, row in enumerate(catalog):
        if not isinstance(row, Mapping):
            raise ReverseSurfaceSemanticAuthoringError(
                f"current_model_obligation_catalog[{index}] must be an object"
            )
        obligation_id = _text(row.get("obligation_id"), field=f"catalog[{index}].obligation_id")
        if obligation_id in expected_by_id:
            raise ReverseSurfaceSemanticAuthoringError(
                f"current model obligation catalog duplicates {obligation_id!r}"
            )
        expected_by_id[obligation_id] = row
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(value):
        if not isinstance(raw, Mapping):
            raise ReverseSurfaceSemanticAuthoringError(
                f"model_obligations[{index}] must be an object"
            )
        obligation_id = _text(raw.get("obligation_id"), field=f"model_obligations[{index}].obligation_id")
        if obligation_id in seen:
            raise ReverseSurfaceSemanticAuthoringError(
                f"model_obligations duplicates {obligation_id!r}"
            )
        seen.add(obligation_id)
        if obligation_id not in expected_by_id:
            raise ReverseSurfaceSemanticAuthoringError(
                f"model_obligations contains unknown current obligation {obligation_id!r}"
            )
        disposition = _text(
            raw.get("disposition"), field=f"model_obligations[{index}].disposition"
        )
        if disposition not in _OBLIGATION_DISPOSITIONS:
            raise ReverseSurfaceSemanticAuthoringError(
                f"model obligation {obligation_id!r} has a non-current disposition"
            )
        row: dict[str, Any] = {
            "obligation_id": obligation_id,
            "disposition": disposition,
        }
        if disposition == "governed":
            ids = _ids(
                raw.get("surface_ids"),
                field=f"model_obligations[{index}].surface_ids",
                required=True,
            )
            unknown = sorted(set(ids) - surface_ids)
            if unknown:
                raise ReverseSurfaceSemanticAuthoringError(
                    f"model obligation {obligation_id!r} references unknown surfaces: {unknown!r}"
                )
            expected_bound = sorted(
                surface_id
                for surface_id, obligation_ids in surface_bindings.items()
                if obligation_id in obligation_ids
            )
            if ids != expected_bound:
                raise ReverseSurfaceSemanticAuthoringError(
                    f"model obligation {obligation_id!r} is not two-way conserved: declared={ids!r}, surface_bindings={expected_bound!r}"
                )
            row["surface_ids"] = ids
            row["intent_id"] = _text(raw.get("intent_id"), field=f"model_obligations[{index}].intent_id")
            row["model_owner_id"] = _text(
                raw.get("model_owner_id"), field=f"model_obligations[{index}].model_owner_id"
            )
        elif disposition == "blocked_gap":
            ids = _ids(raw.get("surface_ids", []), field=f"model_obligations[{index}].surface_ids")
            if ids:
                raise ReverseSurfaceSemanticAuthoringError(
                    f"blocked-gap model obligation {obligation_id!r} cannot point to an implementation surface"
                )
            row["surface_ids"] = []
            row["gap_reason"] = _text(
                raw.get("gap_reason"),
                field=f"model_obligations[{index}].gap_reason",
            )
        else:
            ids = _ids(raw.get("surface_ids", []), field=f"model_obligations[{index}].surface_ids")
            if ids:
                raise ReverseSurfaceSemanticAuthoringError(
                    f"typed model obligation {obligation_id!r} cannot point to an implementation surface"
                )
            row["surface_ids"] = []
            row["proof_ref"] = _text(raw.get("proof_ref"), field=f"model_obligations[{index}].proof_ref")
            row["reason"] = _text(raw.get("reason"), field=f"model_obligations[{index}].reason")
        result.append(row)
    missing = sorted(set(expected_by_id) - seen)
    if missing:
        raise ReverseSurfaceSemanticAuthoringError(
            f"model_obligations omit current obligations: {missing!r}"
        )
    return sorted(result, key=lambda row: row["obligation_id"])


def build_reverse_surface_semantic_map(
    discovery: Mapping[str, Any],
    authoring_context: Mapping[str, Any],
    *,
    surface_decisions: Sequence[Mapping[str, Any]],
    component_group_decisions: Sequence[Mapping[str, Any]] = (),
    model_obligations: Sequence[Mapping[str, Any]],
    inventory_id: str = "flowguard-reverse-surface-closure",
    project_boundary: str,
    current_revision: str,
    claim_boundary: str,
    current_authority_join: Mapping[str, Any] | None = None,
    current_behavior_ledger_join: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one explicit current reverse map from owner-authored decisions.

    The function intentionally raises on any incomplete input.  Callers that
    need a user-facing report can catch :class:`ReverseSurfaceSemanticAuthoringError`
    and serialize the message as a blocked work item; there is no partial map
    and no automatic completion path.
    """

    rows = _discovery_rows(discovery)
    discovery_fingerprint = _text(
        discovery.get("discovery_fingerprint"), field="discovery.discovery_fingerprint"
    )
    if authoring_context.get("schema_version") != "flowguard.implementation_surface_authoring_context.v1":
        raise ReverseSurfaceSemanticAuthoringError(
            "authoring_context schema is not current"
        )
    if authoring_context.get("discovery_fingerprint") != discovery_fingerprint:
        raise ReverseSurfaceSemanticAuthoringError(
            "authoring context does not bind the current discovery fingerprint"
        )
    groups = _context_groups(authoring_context, rows)
    surface_bindings: dict[str, set[str]] = {}
    mapped_rows: list[dict[str, Any]] = []
    used_surface_ids: set[str] = set()
    used_group_ids: set[str] = set()

    def add_surface(surface_id: str, decision: Mapping[str, Any], *, target: str) -> None:
        if surface_id not in rows:
            raise ReverseSurfaceSemanticAuthoringError(
                f"{target} references unknown surface {surface_id!r}"
            )
        if surface_id in used_surface_ids:
            raise ReverseSurfaceSemanticAuthoringError(
                f"surface {surface_id!r} is authored more than once"
            )
        semantic = _common_decision_fields(decision, target=target)
        structural = {
            key: rows[surface_id][key]
            for key in (
                "surface_id",
                "surface_kind",
                "surface_class",
                "review_group_id",
                "review_granularity",
                "source_path",
                "source_ref",
                "source_fingerprint",
            )
            if key in rows[surface_id]
        }
        structural["surface_id"] = surface_id
        mapped_rows.append({**structural, **semantic})
        used_surface_ids.add(surface_id)
        surface_bindings[surface_id] = set(semantic.get("model_obligation_ids", ()))

    for index, decision in enumerate(surface_decisions):
        if not isinstance(decision, Mapping):
            raise ReverseSurfaceSemanticAuthoringError(
                f"surface_decisions[{index}] must be an object"
            )
        surface_id = _text(decision.get("surface_id"), field=f"surface_decisions[{index}].surface_id")
        if "review_group_id" in decision:
            raise ReverseSurfaceSemanticAuthoringError(
                f"surface_decisions[{index}] cannot use review_group_id; use component_group_decisions"
            )
        add_surface(surface_id, decision, target=f"surface_decisions[{index}]")

    component_groups: list[dict[str, Any]] = []
    for index, decision in enumerate(component_group_decisions):
        if not isinstance(decision, Mapping):
            raise ReverseSurfaceSemanticAuthoringError(
                f"component_group_decisions[{index}] must be an object"
            )
        group_id = _text(
            decision.get("review_group_id"),
            field=f"component_group_decisions[{index}].review_group_id",
        )
        if group_id in used_group_ids:
            raise ReverseSurfaceSemanticAuthoringError(
                f"component group {group_id!r} is authored more than once"
            )
        if group_id not in groups:
            raise ReverseSurfaceSemanticAuthoringError(
                f"component group {group_id!r} is not in the current authoring context"
            )
        granularity, members = groups[group_id]
        if granularity != "component":
            raise ReverseSurfaceSemanticAuthoringError(
                f"review group {group_id!r} is not a component boundary"
            )
        declared_members = _ids(
            decision.get("surface_ids"),
            field=f"component_group_decisions[{index}].surface_ids",
            required=True,
        )
        if declared_members != list(members):
            raise ReverseSurfaceSemanticAuthoringError(
                f"component group {group_id!r} must enumerate every current member exactly"
            )
        semantic = _common_decision_fields(
            decision, target=f"component_group_decisions[{index}]"
        )
        if any(member in used_surface_ids for member in members):
            overlap = sorted(member for member in members if member in used_surface_ids)
            raise ReverseSurfaceSemanticAuthoringError(
                f"component group {group_id!r} overlaps authored surfaces: {overlap!r}"
            )
        member_bindings: dict[str, set[str]] = {}
        for member in members:
            if member not in rows:
                raise ReverseSurfaceSemanticAuthoringError(
                    f"component group {group_id!r} references unknown member {member!r}"
                )
            if rows[member].get("surface_kind") not in {"module", "function", "class"}:
                raise ReverseSurfaceSemanticAuthoringError(
                    f"component group {group_id!r} contains an ineligible member {member!r}"
                )
            used_surface_ids.add(member)
            member_bindings[member] = set(semantic.get("model_obligation_ids", ()))
            surface_bindings[member] = set(semantic.get("model_obligation_ids", ()))
        base = dict(semantic)
        base["review_group_id"] = group_id
        base["review_granularity"] = "component"
        base["surface_ids"] = list(members)
        component_groups.append(base)
        used_group_ids.add(group_id)

    missing_surface_ids = sorted(set(rows) - used_surface_ids)
    if missing_surface_ids:
        raise ReverseSurfaceSemanticAuthoringError(
            f"semantic authoring omits current surfaces: {missing_surface_ids!r}"
        )
    if len(mapped_rows) + sum(len(group["surface_ids"]) for group in component_groups) != len(rows):
        raise ReverseSurfaceSemanticAuthoringError(
            "effective semantic surface count does not equal the discovery denominator"
        )

    obligation_rows = _model_obligation_rows(
        list(model_obligations),
        context=authoring_context,
        surface_ids=set(rows),
        surface_bindings=surface_bindings,
    )
    project_boundary = _text(project_boundary, field="project_boundary")
    current_revision = _text(current_revision, field="current_revision")
    claim_boundary = _text(claim_boundary, field="claim_boundary")
    map_payload: dict[str, Any] = {
        "schema_version": IMPLEMENTATION_SURFACE_MAP_SCHEMA,
        "inventory_id": _text(inventory_id, field="inventory_id"),
        "project_boundary": project_boundary,
        "current_revision": current_revision,
        "discovery_fingerprint": discovery_fingerprint,
        "claim_boundary": claim_boundary,
        "authoring_schema": REVERSE_SURFACE_SEMANTIC_AUTHORING_SCHEMA,
        "authoring_status": "authored_pending_audit",
        "semantic_authority": "explicit_target_owner",
        "no_fallback_policy": "stale, unknown, duplicate, or incomplete authoring blocks direct-current map materialization",
        "surfaces": sorted(mapped_rows, key=lambda row: row["surface_id"]),
        "component_groups": sorted(component_groups, key=lambda row: row["review_group_id"]),
        "model_obligations": obligation_rows,
        "terminal_receipt_refs": sorted(
            {
                reference
                for row in mapped_rows
                for reference in row.get("receipt_refs", [])
            }
            | {
                reference
                for row in component_groups
                for reference in row.get("receipt_refs", [])
            }
        ),
    }
    if current_authority_join is not None:
        if not isinstance(current_authority_join, Mapping):
            raise ReverseSurfaceSemanticAuthoringError(
                "current_authority_join must be an explicit object"
            )
        map_payload["current_authority_join"] = json.loads(
            json.dumps(current_authority_join, ensure_ascii=False, sort_keys=True)
        )
    if current_behavior_ledger_join is not None:
        if not isinstance(current_behavior_ledger_join, Mapping):
            raise ReverseSurfaceSemanticAuthoringError(
                "current_behavior_ledger_join must be an explicit object"
            )
        map_payload["current_behavior_ledger_join"] = json.loads(
            json.dumps(current_behavior_ledger_join, ensure_ascii=False, sort_keys=True)
        )
    map_payload["authoring_fingerprint"] = _canonical_hash(
        {key: value for key, value in map_payload.items() if key != "authoring_fingerprint"}
    )
    return map_payload


__all__ = [
    "REVERSE_SURFACE_SEMANTIC_AUTHORING_SCHEMA",
    "IMPLEMENTATION_SURFACE_MAP_SCHEMA",
    "ReverseSurfaceSemanticAuthoringError",
    "build_reverse_surface_semantic_map",
]
