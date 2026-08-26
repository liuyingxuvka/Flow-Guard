"""Materialize one explicitly authored current reverse-surface semantic map.

The discovery and skeleton commands intentionally stop before assigning
meaning.  This command is the write boundary for the next step: it accepts a
single owner-authored JSON document, validates every identity and two-way
binding through :mod:`flowguard.reverse_surface_semantic`, and atomically
replaces only the explicitly selected current output.  It never reads a
legacy map, fills a missing field, or guesses from names, paths, checks, or
historical rows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from flowguard.reverse_surface_semantic import (
    ReverseSurfaceSemanticAuthoringError,
    build_reverse_surface_semantic_map,
)


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReverseSurfaceSemanticAuthoringError(
            f"cannot load current JSON input {path}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise ReverseSurfaceSemanticAuthoringError(
            f"current JSON input {path} must contain an object"
        )
    return value


def _write_current(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.current-tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize an explicitly authored FlowGuard reverse semantic map; "
            "missing or stale semantics block without fallback."
        )
    )
    parser.add_argument("--discovery", type=Path, required=True)
    parser.add_argument("--authoring-context", type=Path, required=True)
    parser.add_argument(
        "--decisions",
        type=Path,
        required=True,
        help=(
            "JSON object containing surface_decisions, component_group_decisions, "
            "model_obligations, project_boundary, current_revision, and claim_boundary"
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        discovery = _load_object(args.discovery)
        context = _load_object(args.authoring_context)
        decisions = _load_object(args.decisions)
        result = build_reverse_surface_semantic_map(
            discovery,
            context,
            surface_decisions=decisions.get("surface_decisions", ()),
            component_group_decisions=decisions.get("component_group_decisions", ()),
            model_obligations=decisions.get("model_obligations", ()),
            inventory_id=decisions.get(
                "inventory_id", "flowguard-reverse-surface-closure"
            ),
            project_boundary=decisions.get("project_boundary", ""),
            current_revision=decisions.get("current_revision", ""),
            claim_boundary=decisions.get("claim_boundary", ""),
            current_authority_join=decisions.get("current_authority_join"),
            current_behavior_ledger_join=decisions.get("current_behavior_ledger_join"),
        )
    except (OSError, UnicodeError, ReverseSurfaceSemanticAuthoringError) as exc:
        print(
            json.dumps(
                {
                    "schema_version": "flowguard.implementation_surface_semantic_authoring_result.v1",
                    "status": "blocked",
                    "code": "reverse_surface_semantic_authoring_blocked",
                    "error": str(exc),
                    "output_written": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2

    _write_current(args.output, result)
    print(
        json.dumps(
            {
                "schema_version": "flowguard.implementation_surface_semantic_authoring_result.v1",
                "status": "authored_pending_audit",
                "output": str(args.output),
                "authoring_fingerprint": result["authoring_fingerprint"],
                "discovery_fingerprint": result["discovery_fingerprint"],
                "surface_count": len(result["surfaces"])
                + sum(len(row["surface_ids"]) for row in result["component_groups"]),
                "model_obligation_count": len(result["model_obligations"]),
                "output_written": True,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
