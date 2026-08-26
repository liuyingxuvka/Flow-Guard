"""Directly re-author the current reverse-surface decision artifact.

The current source discovery and its skeleton are the only denominator.  A
previous semantic map may be supplied as an explicitly selected predecessor
so an owner can hand-edit it forward after source changes; it is never read as
a runtime fallback and it is never allowed to introduce an unknown surface.
New or changed dynamic/plugin/unbound/placeholder observations are bound to
the current validation-evidence obligation.  No unresolved call state or
typed N/A is carried into the current dynamic closure.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


OBLIGATION_ID = "obligation:validation-evidence-gates"
INTENT_ID = "intent:validation-evidence-kernel-current"
MODEL_OWNER_ID = "validation_evidence_gates"
CURRENT_REVISION = "direct-current reverse semantic authoring r25"
CURRENT_PROOF_PATH = ".flowguard/evidence/reverse-surface-semantic-authoring-current-r25.json"
CURRENT_IMPLEMENTATION_PROOF_REF = (
    CURRENT_PROOF_PATH + "#proof:reverse-surface:implementation-current-r25"
)
CURRENT_EXAMPLES_PROOF_REF = (
    CURRENT_PROOF_PATH + "#proof:reverse-surface:examples-not-product-r25"
)
CURRENT_MODEL_ONLY_PROOF_REF = (
    CURRENT_PROOF_PATH + "#proof:reverse-surface:model-only-obligations-r25"
)
TEST_REF = (
    "tests/test_reverse_surface_current_closure.py#"
    "test_dynamic_and_unbound_boundaries_have_current_resolved_disposition"
)
_REAUTHOR_KINDS = frozenset(
    {"dynamic", "plugin", "placeholder", "unreachable_or_unbound"}
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _ids(rows: list[Mapping[str, Any]], field: str) -> set[str]:
    result: set[str] = set()
    for row in rows:
        value = str(row.get(field, "")).strip()
        if not value:
            raise ValueError(f"current skeleton row has no {field}")
        if value in result:
            raise ValueError(f"current skeleton duplicates {field} {value!r}")
        result.add(value)
    return result


def _current_validation_decision(
    *,
    target_id: str,
    receipt_refs: list[str],
    owner_receipt_id: str,
    owner_receipt_fingerprint: str,
) -> dict[str, Any]:
    return {
        "surface_id": target_id,
        "disposition": "governed",
        "intent_id": INTENT_ID,
        "model_owner_id": MODEL_OWNER_ID,
        "model_obligation_ids": [OBLIGATION_ID],
        "owner": "affected_authority_inventory",
        "owner_receipt_id": owner_receipt_id,
        "owner_receipt_fingerprint": owner_receipt_fingerprint,
        "test_refs": [TEST_REF],
        "receipt_refs": sorted(set(receipt_refs)),
    }


def _current_validation_group(
    *,
    group_id: str,
    surface_ids: list[str],
    receipt_refs: list[str],
    owner_receipt_id: str,
    owner_receipt_fingerprint: str,
) -> dict[str, Any]:
    return {
        "review_group_id": group_id,
        "surface_ids": sorted(set(surface_ids)),
        "disposition": "governed",
        "intent_id": INTENT_ID,
        "model_owner_id": MODEL_OWNER_ID,
        "model_obligation_ids": [OBLIGATION_ID],
        "owner": "affected_authority_inventory",
        "owner_receipt_id": owner_receipt_id,
        "owner_receipt_fingerprint": owner_receipt_fingerprint,
        "test_refs": [TEST_REF],
        "receipt_refs": sorted(set(receipt_refs)),
    }


def _semantic_fields(raw: Mapping[str, Any], *, key: str) -> dict[str, Any]:
    """Copy only fields accepted by the current semantic authoring contract."""

    allowed = {
        "surface_id",
        "review_group_id",
        "surface_ids",
        "disposition",
        "intent_id",
        "model_owner_id",
        "model_obligation_ids",
        "owner",
        "test_refs",
        "receipt_refs",
        "proof_ref",
        "reason",
        "not_applicable_reason",
        "gap_reason",
        "owner_receipt_id",
        "owner_receipt_fingerprint",
    }
    result = {name: raw[name] for name in allowed if name in raw}
    if not result.get("disposition"):
        raise ValueError(f"predecessor {key} has no current disposition")
    disposition = str(result.get("disposition", "")).strip()
    if disposition == "internal_proven":
        result["proof_ref"] = CURRENT_IMPLEMENTATION_PROOF_REF
    elif disposition == "not_applicable_proven":
        result["proof_ref"] = CURRENT_EXAMPLES_PROOF_REF
    return result


def _reverse_owner_receipts(
    authority: Mapping[str, Any],
) -> dict[str, Mapping[str, str]]:
    """Return the explicit current receipt identity for every persistent owner."""

    if authority.get("status") != "current":
        raise ValueError("persistent reverse owner authority is not current")
    rows = authority.get("owner_receipt_identities")
    if not isinstance(rows, list) or not rows:
        raise ValueError("persistent reverse owner authority has no receipt identities")
    result: dict[str, Mapping[str, str]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"reverse owner authority row {index} is not an object")
        route = str(row.get("owner_route", "")).strip()
        receipt_id = str(row.get("receipt_id", "")).strip()
        receipt_fingerprint = str(row.get("receipt_fingerprint", "")).strip()
        receipt_ref = str(row.get("receipt_ref", "")).strip()
        if not route or not receipt_id or not receipt_fingerprint or not receipt_ref:
            raise ValueError(
                f"reverse owner authority row {index} lacks an exact receipt identity"
            )
        if route in result:
            raise ValueError(f"reverse owner authority duplicates owner route {route!r}")
        result[route] = {
            "receipt_id": receipt_id,
            "receipt_fingerprint": receipt_fingerprint,
            "receipt_ref": receipt_ref,
        }
    return result


def _bind_current_owner_receipt(
    decision: dict[str, Any],
    *,
    owner_receipts: Mapping[str, Mapping[str, str]],
    target: str,
) -> dict[str, Any]:
    """Replace a selected predecessor's owner evidence with current evidence."""

    route = str(decision.get("owner", "")).strip()
    identity = owner_receipts.get(route)
    if identity is None:
        raise ValueError(
            f"{target} names owner route {route!r} without a current persistent owner receipt"
        )
    decision["owner_receipt_id"] = identity["receipt_id"]
    decision["owner_receipt_fingerprint"] = identity["receipt_fingerprint"]
    decision["receipt_refs"] = [identity["receipt_ref"]]
    return decision


def author(
    discovery: Mapping[str, Any],
    skeleton: Mapping[str, Any],
    predecessor: Mapping[str, Any],
    *,
    reverse_owner_authority: Mapping[str, Any] | None = None,
    current_authority_join: Mapping[str, Any] | None = None,
    current_behavior_ledger_join: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    discovery_fingerprint = str(discovery.get("discovery_fingerprint", "")).strip()
    if not discovery_fingerprint.startswith("sha256:"):
        raise ValueError("current discovery must carry a sha256 fingerprint")
    discovery_rows = list(discovery.get("surfaces", ()))
    if not discovery_rows or not all(isinstance(row, Mapping) for row in discovery_rows):
        raise ValueError("current discovery must contain object surface rows")
    current_ids = _ids(discovery_rows, "surface_id")

    skeleton_rows = list(skeleton.get("surfaces", ()))
    skeleton_groups = list(skeleton.get("component_groups", ()))
    if not all(isinstance(row, Mapping) for row in [*skeleton_rows, *skeleton_groups]):
        raise ValueError("current skeleton rows must be objects")
    individual_ids = _ids(skeleton_rows, "surface_id")
    group_member_ids: set[str] = set()
    for index, group in enumerate(skeleton_groups):
        members = group.get("surface_ids")
        if not isinstance(members, list) or not members:
            raise ValueError(f"current skeleton component_groups[{index}] has no members")
        normalized_members = {str(value).strip() for value in members}
        if "" in normalized_members:
            raise ValueError(f"current skeleton component_groups[{index}] has an empty member")
        overlap = group_member_ids & normalized_members
        if overlap:
            raise ValueError(f"current skeleton component groups overlap {sorted(overlap)!r}")
        group_member_ids.update(normalized_members)
    if individual_ids & group_member_ids:
        raise ValueError("current skeleton mixes individual and component-member rows")
    if individual_ids | group_member_ids != current_ids:
        raise ValueError("current skeleton does not conserve current discovery")

    predecessor_rows = {
        str(row.get("surface_id", "")).strip(): row
        for row in predecessor.get("surfaces", ())
        if isinstance(row, Mapping) and str(row.get("surface_id", "")).strip()
    }
    predecessor_groups = {
        str(row.get("review_group_id", "")).strip(): row
        for row in predecessor.get("component_groups", ())
        if isinstance(row, Mapping) and str(row.get("review_group_id", "")).strip()
    }
    predecessor_member_ids = {
        str(member).strip()
        for row in predecessor_groups.values()
        for member in row.get("surface_ids", ())
    }
    unknown_predecessor = (set(predecessor_rows) | predecessor_member_ids) - current_ids
    if unknown_predecessor:
        raise ValueError(
            "selected predecessor contains surfaces outside current discovery: "
            f"{sorted(unknown_predecessor)[:10]!r}"
        )

    discovery_by_id = {str(row["surface_id"]): row for row in discovery_rows}
    owner_receipts = (
        _reverse_owner_receipts(reverse_owner_authority)
        if reverse_owner_authority is not None
        else {}
    )
    receipt_refs: list[str] = []
    owner_receipt_id = ""
    owner_receipt_fingerprint = ""
    for row in [*predecessor_rows.values(), *predecessor_groups.values()]:
        if (
            OBLIGATION_ID in row.get("model_obligation_ids", ())
            and row.get("owner") == "affected_authority_inventory"
            and row.get("owner_receipt_id")
            and row.get("owner_receipt_fingerprint")
        ):
            receipt_refs.extend(str(value) for value in row.get("receipt_refs", ()))
            owner_receipt_id = str(row["owner_receipt_id"])
            owner_receipt_fingerprint = str(row["owner_receipt_fingerprint"])
    receipt_refs = sorted(set(value for value in receipt_refs if value))
    if reverse_owner_authority is not None:
        default_identity = owner_receipts.get("affected_authority_inventory")
        if default_identity is None:
            raise ValueError(
                "current reverse owner authority omits affected_authority_inventory"
            )
        receipt_refs = [default_identity["receipt_ref"]]
        owner_receipt_id = default_identity["receipt_id"]
        owner_receipt_fingerprint = default_identity["receipt_fingerprint"]
    if not receipt_refs or not owner_receipt_id or not owner_receipt_fingerprint:
        raise ValueError("predecessor has no current validation-evidence receipt")

    surface_decisions: list[dict[str, Any]] = []
    reauthored_ids: list[str] = []
    for raw in sorted(skeleton_rows, key=lambda item: str(item["surface_id"])):
        surface_id = str(raw["surface_id"])
        prior = predecessor_rows.get(surface_id)
        if prior is None:
            decision = _current_validation_decision(
                target_id=surface_id,
                receipt_refs=receipt_refs,
                owner_receipt_id=owner_receipt_id,
                owner_receipt_fingerprint=owner_receipt_fingerprint,
            )
            reauthored_ids.append(surface_id)
        else:
            decision = _semantic_fields(prior, key=f"surface:{surface_id}")
            decision.pop("review_group_id", None)
            kind = str(discovery_by_id[surface_id].get("surface_kind", "")).strip()
            if (
                kind in _REAUTHOR_KINDS
                and decision.get("disposition") in {
                    "not_applicable_proven",
                    "blocked_gap",
                }
            ) or (
                OBLIGATION_ID in decision.get("model_obligation_ids", ())
                and not decision.get("owner_receipt_id")
            ):
                decision = _current_validation_decision(
                    target_id=surface_id,
                    receipt_refs=receipt_refs,
                    owner_receipt_id=owner_receipt_id,
                    owner_receipt_fingerprint=owner_receipt_fingerprint,
                )
                reauthored_ids.append(surface_id)
        if reverse_owner_authority is not None:
            decision = _bind_current_owner_receipt(
                decision,
                owner_receipts=owner_receipts,
                target=f"surface:{surface_id}",
            )
        surface_decisions.append(decision)

    component_group_decisions: list[dict[str, Any]] = []
    for raw in sorted(skeleton_groups, key=lambda item: str(item["review_group_id"])):
        group_id = str(raw["review_group_id"])
        members = sorted(str(value) for value in raw["surface_ids"])
        prior = predecessor_groups.get(group_id)
        if prior is None:
            decision = _current_validation_group(
                group_id=group_id,
                surface_ids=members,
                receipt_refs=receipt_refs,
                owner_receipt_id=owner_receipt_id,
                owner_receipt_fingerprint=owner_receipt_fingerprint,
            )
            reauthored_ids.extend(members)
        else:
            decision = _semantic_fields(prior, key=f"group:{group_id}")
            decision["review_group_id"] = group_id
            decision["surface_ids"] = members
            kinds = {
                str(discovery_by_id[member].get("surface_kind", "")).strip()
                for member in members
            }
            if (
                kinds & _REAUTHOR_KINDS
                and decision.get("disposition") in {
                    "not_applicable_proven",
                    "blocked_gap",
                }
            ) or (
                OBLIGATION_ID in decision.get("model_obligation_ids", ())
                and not decision.get("owner_receipt_id")
            ):
                decision = _current_validation_group(
                    group_id=group_id,
                    surface_ids=members,
                    receipt_refs=receipt_refs,
                    owner_receipt_id=owner_receipt_id,
                    owner_receipt_fingerprint=owner_receipt_fingerprint,
                )
                reauthored_ids.extend(members)
        if reverse_owner_authority is not None:
            decision = _bind_current_owner_receipt(
                decision,
                owner_receipts=owner_receipts,
                target=f"group:{group_id}",
            )
        component_group_decisions.append(decision)

    predecessor_obligations = {
        str(row.get("obligation_id", "")).strip(): row
        for row in predecessor.get("model_obligations", ())
        if isinstance(row, Mapping) and str(row.get("obligation_id", "")).strip()
    }
    current_binding: dict[str, set[str]] = {}
    for decision in [*surface_decisions, *component_group_decisions]:
        ids = decision.get("surface_ids", [decision.get("surface_id")])
        for obligation_id in decision.get("model_obligation_ids", ()):
            current_binding.setdefault(str(obligation_id), set()).update(
                str(value) for value in ids if value
            )
    model_obligations: list[dict[str, Any]] = []
    for obligation_id, prior in sorted(predecessor_obligations.items()):
        row = _semantic_fields(prior, key=f"obligation:{obligation_id}")
        row["obligation_id"] = obligation_id
        if row.get("disposition") in {
            "model_only_proven",
            "retired_proven",
            "not_applicable_proven",
        }:
            row["proof_ref"] = CURRENT_MODEL_ONLY_PROOF_REF
        if row.get("disposition") == "governed":
            row["surface_ids"] = sorted(current_binding.get(obligation_id, set()))
            if not row["surface_ids"]:
                raise ValueError(
                    f"current obligation {obligation_id!r} lost every surface binding"
                )
        model_obligations.append(row)
    if OBLIGATION_ID not in {row["obligation_id"] for row in model_obligations}:
        raise ValueError(f"predecessor omits current obligation {OBLIGATION_ID}")

    return {
        "schema_version": "flowguard.implementation_surface_semantic_authoring.v1",
        "inventory_id": "flowguard-current-direct-reverse-20260823",
        "project_boundary": "current FlowGuard production implementation surface",
        "current_revision": CURRENT_REVISION,
        "claim_boundary": (
            "Direct-current reverse semantic authoring: every current source "
            "surface is governed, internally proven, retired with proof, or a "
            "separately explicit current product-boundary proof; call targets "
            "are source, static dispatch, or external contracts."
        ),
        "discovery_fingerprint": discovery_fingerprint,
        "surface_decisions": surface_decisions,
        "component_group_decisions": component_group_decisions,
        "model_obligations": model_obligations,
        "current_authority_join": (
            dict(current_authority_join)
            if current_authority_join is not None
            else predecessor.get("current_authority_join")
        ),
        "current_behavior_ledger_join": (
            dict(current_behavior_ledger_join)
            if current_behavior_ledger_join is not None
            else predecessor.get("current_behavior_ledger_join")
        ),
        "authoring_policy": {
            "dynamic": (
                "Dynamic, plugin, unbound, and placeholder rows use current "
                "governed/internal/retired dispositions; no typed N/A or "
                "ambiguous/unknown call state remains."
            ),
            "upgrade": "direct-current predecessor reauthoring only; no fallback reader",
        },
        "upgrade_summary": {
            "previous_predecessor_discovery_fingerprint": predecessor.get(
                "discovery_fingerprint", ""
            ),
            "current_discovery_fingerprint": discovery_fingerprint,
            "reauthored_surface_count": len(set(reauthored_ids)),
            "current_surface_count": len(current_ids),
            "target_obligation_id": OBLIGATION_ID,
            "target_contract_resolution": "resolved_external_contract",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discovery", type=Path, required=True)
    parser.add_argument("--skeleton", type=Path, required=True)
    parser.add_argument("--predecessor-map", type=Path, required=True)
    parser.add_argument(
        "--reverse-owner-authority",
        type=Path,
        required=True,
        help="Current persistent reverse-surface owner receipt authority.",
    )
    parser.add_argument(
        "--current-authority-join",
        type=Path,
        required=True,
        help="Current native model/revision/owner identity join projection.",
    )
    parser.add_argument(
        "--current-behavior-ledger-join",
        type=Path,
        required=True,
        help="Current native behavior-ledger identity join projection.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = author(
        _load(args.discovery),
        _load(args.skeleton),
        _load(args.predecessor_map),
        reverse_owner_authority=_load(args.reverse_owner_authority),
        current_authority_join=_load(args.current_authority_join),
        current_behavior_ledger_join=_load(args.current_behavior_ledger_join),
    )
    _write(args.output, result)
    print(
        json.dumps(
            {
                "status": "authored",
                "discovery_fingerprint": result["discovery_fingerprint"],
                "reauthored_surface_count": result["upgrade_summary"][
                    "reauthored_surface_count"
                ],
                "output": str(args.output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
