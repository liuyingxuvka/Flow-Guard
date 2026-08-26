"""Plan, execute, and merge bounded implementation-surface discovery shards.

The command is deliberately source-only.  It does not import a target package
and never turns model, test, or API declaration names into semantic rows.
Semantic intent/model/test ownership remains an independently authored map
consumed by audit_public_behavior_surface.py.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flowguard.behavior_surface_audit import (
    IMPLEMENTATION_SURFACE_SHARD_PLAN_SCHEMA,
    PublicBehaviorSurfaceAuditError,
    discover_implementation_surface_shard,
    merge_implementation_surface_shards,
    plan_implementation_surface_shards,
)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PublicBehaviorSurfaceAuditError(f"cannot load JSON artifact {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PublicBehaviorSurfaceAuditError(f"JSON artifact {path} must contain an object")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _compact_result(result: dict[str, Any], *, artifact: Path) -> dict[str, Any]:
    """Bound terminal output; the written artifact remains complete authority."""

    findings = result.get("findings", ())
    finding_counts: dict[str, int] = {}
    if isinstance(findings, list):
        for row in findings:
            code = str(row.get("code", "")).strip() if isinstance(row, dict) else "<invalid>"
            code = code or "<missing>"
            finding_counts[code] = finding_counts.get(code, 0) + 1
    summary: dict[str, Any] = {
        "schema_version": "flowguard.implementation_surface_shard_compact.v1",
        "claim_boundary": (
            "Bounded terminal projection only. The explicitly supplied output "
            "artifact is the sole complete source observation."
        ),
        "artifact_ref": str(artifact.resolve()),
        "status": result.get("status"),
        "shard_id": result.get("shard_id", ""),
        "shard_ids": result.get("shard_ids", []),
        "source_count": len(result.get("source_paths", ()))
        if isinstance(result.get("source_paths"), list)
        else int(result.get("source_count", 0) or 0),
        "surface_count": int(result.get("surface_count", len(result.get("surfaces", ()))) or 0),
        "call_graph_count": len(result.get("call_graph", ()))
        if isinstance(result.get("call_graph"), list)
        else 0,
        "external_contract_count": len(result.get("external_contracts", ()))
        if isinstance(result.get("external_contracts"), list)
        else 0,
        "finding_count": len(findings) if isinstance(findings, list) else 0,
        "finding_code_counts": dict(sorted(finding_counts.items())),
        "discovery_fingerprint": result.get("discovery_fingerprint", ""),
        "omitted_fields": ["surfaces", "call_graph", "external_contracts", "source_identities"],
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--mode",
        choices=("plan", "discover", "merge"),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--max-rows", type=int, default=5000)
    parser.add_argument("--shard-id")
    parser.add_argument(
        "--full-output",
        action="store_true",
        help="Print the complete shard artifact; default terminal output is bounded.",
    )
    parser.add_argument(
        "--shard-file",
        action="append",
        type=Path,
        default=[],
        help="Input shard JSON for merge; repeat once per shard.",
    )
    args = parser.parse_args(argv)

    try:
        if args.mode == "plan":
            result = plan_implementation_surface_shards(
                args.root,
                max_rows=args.max_rows,
            )
        elif args.mode == "discover":
            if args.plan is None or not args.shard_id:
                raise PublicBehaviorSurfaceAuditError(
                    "discover mode requires --plan and --shard-id"
                )
            plan = _read_json(args.plan)
            if plan.get("schema_version") != IMPLEMENTATION_SURFACE_SHARD_PLAN_SCHEMA:
                raise PublicBehaviorSurfaceAuditError("shard plan schema is not current")
            result = discover_implementation_surface_shard(
                args.root,
                plan,
                args.shard_id,
            )
        else:
            if args.plan is None or not args.shard_file:
                raise PublicBehaviorSurfaceAuditError(
                    "merge mode requires --plan and at least one --shard-file"
                )
            plan = _read_json(args.plan)
            shard_values = [_read_json(path) for path in args.shard_file]
            result = merge_implementation_surface_shards(
                args.root,
                plan,
                shard_values,
            )
    except PublicBehaviorSurfaceAuditError as exc:
        result = {
            "schema_version": "flowguard.implementation_surface_shard.v1",
            "status": "blocked",
            "claim_boundary": "bounded source-only shard discovery",
            "findings": [
                {
                    "code": "surface_shard_command_invalid",
                    "severity": "blocker",
                    "message": str(exc),
                }
            ],
        }

    _write_json(args.output, result)
    terminal = result if args.full_output else _compact_result(result, artifact=args.output)
    print(json.dumps(terminal, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result.get("status") in {"passed", "planned"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
