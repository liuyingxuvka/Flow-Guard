"""Render the native current authority join used by reverse authoring."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from flowguard.behavior_surface_audit import (
    _load_current_authority_join,
    _load_current_behavior_ledger_join,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--behavior-ledger-output",
        type=Path,
        help="Also render the native current behavior-ledger identity join.",
    )
    args = parser.parse_args()
    join = _load_current_authority_join(args.root.resolve())
    if not isinstance(join, dict) or join.get("status") == "blocked":
        raise ValueError(f"current authority join is blocked: {join}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(join, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    outputs = [str(args.output)]
    if args.behavior_ledger_output is not None:
        ledger_join = _load_current_behavior_ledger_join(args.root.resolve())
        if not isinstance(ledger_join, dict) or ledger_join.get("status") == "blocked":
            raise ValueError(f"current behavior-ledger join is blocked: {ledger_join}")
        args.behavior_ledger_output.parent.mkdir(parents=True, exist_ok=True)
        args.behavior_ledger_output.write_text(
            json.dumps(ledger_join, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        outputs.append(str(args.behavior_ledger_output))
    print(json.dumps({"status": "current", "outputs": outputs}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
