"""Emit and verify a source-only implementation-surface candidate report.

The report is a review handoff.  It preserves the independently discovered
surface denominator and deterministic structural triage labels, but it never
authors intent, model obligations, owners, tests, receipts, or dispositions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flowguard.behavior_surface_audit import (
    classify_implementation_surface_candidates,
    validate_implementation_surface_candidate_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discovery", type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        discovery: Any = json.loads(args.discovery.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load JSON artifact {args.discovery}: {exc}") from exc
    if not isinstance(discovery, dict):
        raise ValueError(f"JSON artifact {args.discovery} must contain an object")

    plan: dict[str, Any] | None = None
    if args.plan:
        try:
            loaded_plan: Any = json.loads(args.plan.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot load JSON artifact {args.plan}: {exc}") from exc
        if not isinstance(loaded_plan, dict):
            raise ValueError(f"JSON artifact {args.plan} must contain an object")
        plan = loaded_plan
    report = classify_implementation_surface_candidates(discovery, plan=plan)
    validation = validate_implementation_surface_candidate_report(
        report,
        discovery,
        plan=plan,
    )
    report["candidate_report_validation"] = validation
    # The validation object is part of the persisted handoff, so recalculate
    # the report fingerprint after attaching it.  The validator checks the
    # report body independently and never treats this nested result as proof
    # of semantic closure.
    from flowguard.behavior_surface_audit import _surface_hash  # local-only helper

    report.pop("evidence_fingerprint", None)
    report["evidence_fingerprint"] = _surface_hash(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "candidate_surface_count": report["candidate_surface_count"],
                "source_discovery_status": report["source_discovery_status"],
                "discovery_fingerprint": report["discovery_fingerprint"],
                "candidate_report_validation": validation["status"],
                "output": str(args.output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    # A candidate-only report is intentionally not a semantic pass.  Returning
    # zero means only that the structural handoff was emitted and validated;
    # the JSON status remains the claim boundary for consumers.
    return 0 if report["status"] == "candidate_only" and validation["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
