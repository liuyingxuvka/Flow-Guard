"""Author a fail-closed reverse surface-map skeleton.

The implementation-surface discovery is deliberately source-only.  It can
enumerate code, API, CLI, UI-like, configuration, effect, fault, recovery,
and installation observations, but it cannot decide what an observation
means, who owns it, which model obligation governs it, or which test receipt
proves it.  This command therefore emits an independently authored *shape*
for those decisions while leaving every semantic field empty and every row
typed as ``blocked_gap``.

The output is not an acceptance map and it must not be used as one.  It is a
deterministic handoff artifact for the owners who must supply intent/model/
obligation/test/owner/receipt evidence.  Dynamic/plugin observations and
unreachable or unbound surface rows retain explicit blocked dispositions, while
their call-graph edges are already closed to deterministic boundary identities
or exact finite dispatch sets.  No unresolved call-graph state is emitted.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping


MAP_SCHEMA = "flowguard.implementation_surface_map.v1"
BLOCKED_GAP = "blocked_gap"
COMPONENT_GROUP_MEMBER_KINDS = frozenset({"module", "function", "class"})


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load JSON artifact {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON artifact {path} must contain an object")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _gap_reason(row: Mapping[str, Any]) -> str:
    kind = str(row.get("surface_kind", ""))
    if kind in {"dynamic", "plugin"}:
        return (
            "static discovery found a dynamic/plugin surface row; call-graph "
            "edges carry deterministic boundary identities, but a native owner "
            "must still provide semantic closure or a current "
            "not_applicable_proven proof"
        )
    if kind == "unreachable_or_unbound":
        return (
            "static discovery found no uniquely resolved incoming owner or external "
            "binding; an owner must provide the binding or a current "
            "not_applicable_proven proof"
        )
    return (
        "source observation is structural only; an independent owner has not yet "
        "supplied intent, model obligation, test, owner, and terminal receipt "
        "bindings"
    )


def _surface_row(row: Mapping[str, Any]) -> dict[str, Any]:
    surface_id = str(row.get("surface_id", "")).strip()
    if not surface_id:
        raise ValueError("every source observation needs a surface_id")
    surface_kind = str(row.get("surface_kind", "")).strip()
    surface_class = str(row.get("surface_class", "")).strip()
    if not surface_kind or not surface_class:
        raise ValueError(f"surface {surface_id} is missing surface_kind or surface_class")
    review_group_id = str(row.get("review_group_id", "")).strip()
    review_granularity = str(row.get("review_granularity", "")).strip()
    if not review_group_id or review_granularity not in {"surface", "component"}:
        raise ValueError(
            f"surface {surface_id} is missing the current review grouping; "
            "source lines are anchors, not independent semantic rows"
        )
    return {
        "disposition": BLOCKED_GAP,
        "gap_reason": _gap_reason(row),
        "intent_id": "",
        "model_obligation_ids": [],
        "model_owner_id": "",
        "owner": "",
        "receipt_refs": [],
        "source_fingerprint": str(row.get("source_fingerprint", "")),
        "source_path": str(row.get("source_path", "")),
        "source_ref": str(row.get("source_ref", "")),
        "surface_class": surface_class,
        "surface_id": surface_id,
        "surface_kind": surface_kind,
        "review_group_id": review_group_id,
        "review_granularity": review_granularity,
        "test_refs": [],
    }


def _component_group_row(
    group_id: str,
    rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Create one blocked authoring row for an eligible implementation group."""

    return {
        "disposition": BLOCKED_GAP,
        "gap_reason": (
            "component-level authoring compression only: an independent owner "
            "must prove one shared binding for every listed module/function/class "
            "member before this group can close"
        ),
        "intent_id": "",
        "model_obligation_ids": [],
        "model_owner_id": "",
        "owner": "",
        "receipt_refs": [],
        "review_granularity": "component",
        "review_group_id": group_id,
        "surface_ids": sorted(str(row["surface_id"]) for row in rows),
        "test_refs": [],
    }


def build_reverse_surface_map_skeleton(
    discovery: Mapping[str, Any],
    *,
    plan: Mapping[str, Any] | None = None,
    inventory_id: str = "flowguard-reverse-surface-closure",
) -> dict[str, Any]:
    """Build a deterministic, explicitly blocked map shape from observations.

    No semantic identifier, test reference, owner, proof, or receipt is
    inferred here.  The only copied fields are source observation identities
    needed to make the later independent authoring reviewable.
    """

    raw_rows = discovery.get("surfaces")
    if not isinstance(raw_rows, list) or not raw_rows:
        raise ValueError("discovery must contain a non-empty surfaces array")
    rows = [_surface_row(row) for row in raw_rows if isinstance(row, Mapping)]
    if len(rows) != len(raw_rows):
        raise ValueError("discovery surfaces must contain only object rows")
    rows.sort(key=lambda row: row["surface_id"])
    surface_ids = [row["surface_id"] for row in rows]
    if len(surface_ids) != len(set(surface_ids)):
        raise ValueError("discovery contains duplicate surface_id values")

    kind_counts = Counter(row["surface_kind"] for row in rows)
    group_counts = Counter(row["review_group_id"] for row in rows)
    granularity_counts = Counter(row["review_granularity"] for row in rows)
    finding_counts = Counter(
        str(item.get("code", ""))
        for item in discovery.get("findings", ())
        if isinstance(item, Mapping) and str(item.get("code", ""))
    )
    plan = plan or {}
    plan_fingerprint = str(plan.get("plan_fingerprint", ""))
    discovery_fingerprint = str(discovery.get("discovery_fingerprint", ""))
    if not discovery_fingerprint:
        raise ValueError("discovery must contain a discovery_fingerprint")

    # Keep ordinary implementation members compressible while retaining
    # dynamic/plugin/placeholder/unbound observations as individual blocked
    # rows.  A group is emitted only when its complete deterministic review
    # boundary contains eligible members exclusively; no partial grouping is
    # inferred.
    rows_by_group: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    all_rows_by_group: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        group_id = str(row["review_group_id"])
        all_rows_by_group[group_id].append(row)
        if (
            row["review_granularity"] == "component"
            and row["surface_kind"] in COMPONENT_GROUP_MEMBER_KINDS
        ):
            rows_by_group[group_id].append(row)
    component_groups: list[dict[str, Any]] = []
    surface_rows: list[dict[str, Any]] = []
    grouped_surface_ids: set[str] = set()
    for group_id, group_rows in sorted(rows_by_group.items()):
        complete_group = all(
            item["review_granularity"] == "component"
            and item["surface_kind"] in COMPONENT_GROUP_MEMBER_KINDS
            for item in all_rows_by_group[group_id]
        )
        if complete_group:
            component_groups.append(_component_group_row(group_id, group_rows))
            grouped_surface_ids.update(str(row["surface_id"]) for row in group_rows)
    for row in rows:
        if str(row["surface_id"]) not in grouped_surface_ids:
            surface_rows.append(row)
    surface_rows.sort(key=lambda row: row["surface_id"])

    observation_dispositions = [
        {
            "count": kind_counts.get("dynamic", 0),
            "disposition": BLOCKED_GAP,
            "observation_type": "dynamic_surface",
            "reason": (
                "dynamic target identity is not inferred from source-only "
                "discovery"
            ),
            "surface_kind": "dynamic",
        },
        {
            "count": kind_counts.get("plugin", 0),
            "disposition": BLOCKED_GAP,
            "observation_type": "plugin_surface",
            "reason": (
                "plugin target identity and lifecycle owner require explicit "
                "native evidence"
            ),
            "surface_kind": "plugin",
        },
        {
            "count": kind_counts.get("unreachable_or_unbound", 0),
            "disposition": BLOCKED_GAP,
            "observation_type": "unreachable_or_unbound_surface",
            "reason": (
                "no unique incoming or external binding was proven by static "
                "discovery"
            ),
            "surface_kind": "unreachable_or_unbound",
        },
        {
            "count": sum(
                1
                for edge in discovery.get("call_graph", ())
                if isinstance(edge, Mapping)
                and str(edge.get("resolution", "")).strip() == "resolved_static_dispatch"
            ),
            "disposition": "resolved_static_dispatch",
            "observation_type": "finite_dispatch_call_graph",
            "reason": (
                "every finite dispatch edge preserves its complete exact source "
                "candidate set; no unresolved ambiguity is retained"
            ),
        },
    ]

    return {
        "schema_version": MAP_SCHEMA,
        "inventory_id": inventory_id,
        "project_boundary": (
            "FlowGuard production-source boundary observed by the complete "
            "implementation-surface shard plan"
        ),
        "current_revision": (
            "working-tree source identities anchored by the discovery "
            f"fingerprint {discovery_fingerprint}"
        ),
        "plan_fingerprint": plan_fingerprint,
        "discovery_fingerprint": discovery_fingerprint,
        "claim_boundary": (
            "Blocked reverse-map skeleton only.  Source observations are not "
            "semantic intent/model/test/owner claims, and no terminal receipt "
            "is supplied."
        ),
        "authoring_status": "blocked_gap_scaffold",
        "semantic_authority": "none",
        "terminal_receipt_refs": [],
        "model_obligations": [],
        "observation_dispositions": observation_dispositions,
        "source_observation": {
            "status": str(discovery.get("status", "")),
            "source_count": len(discovery.get("source_paths", ())),
            "surface_count": len(rows),
            "call_graph_count": len(discovery.get("call_graph", ())),
            "unbound_surface_count": len(discovery.get("unbound_surface_ids", ())),
            "finding_counts": dict(sorted(finding_counts.items())),
            "kind_counts": dict(sorted(kind_counts.items())),
            "review_group_count": len(group_counts),
            "review_granularity_counts": dict(sorted(granularity_counts.items())),
            "shard_ids": sorted(str(item) for item in discovery.get("shard_ids", ())),
        },
        "component_groups": component_groups,
        "surfaces": surface_rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discovery", type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inventory-id", default="flowguard-reverse-surface-closure")
    args = parser.parse_args(argv)
    discovery = _read_json(args.discovery)
    plan = _read_json(args.plan) if args.plan else None
    result = build_reverse_surface_map_skeleton(
        discovery,
        plan=plan,
        inventory_id=args.inventory_id,
    )
    _write_json(args.output, result)
    print(
        json.dumps(
            {
                "status": result["authoring_status"],
                "surface_count": len(result["surfaces"]),
                "discovery_fingerprint": result["discovery_fingerprint"],
                "output": str(args.output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
