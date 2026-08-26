"""Build a current, unresolved authoring context for reverse closure.

This command is deliberately not a mapper.  It joins the current independent
source discovery to the current Behavior Commitment Ledger and model-owner
catalogues, then leaves every implementation surface in ``needs_author``
state.  The resulting context is input to a human/target-owner authored
``implementation_surface_map.v1`` and the existing fail-closed audit.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flowguard.reverse_surface_authoring import (
    build_reverse_surface_authoring_context,
    validate_reverse_surface_authoring_context,
)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load JSON artifact {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON artifact {path} must contain an object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discovery", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--owner-bindings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validate", type=Path, help="Validate an existing context instead of rebuilding it.")
    args = parser.parse_args(argv)

    discovery = _read_json(args.discovery)
    ledger = _read_json(args.ledger)
    owner_bindings = _read_json(args.owner_bindings)
    if args.validate:
        context = _read_json(args.validate)
        result = validate_reverse_surface_authoring_context(
            context,
            discovery,
            ledger=ledger,
            owner_bindings=owner_bindings,
        )
    else:
        result = build_reverse_surface_authoring_context(
            discovery,
            ledger=ledger,
            owner_bindings=owner_bindings,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": result.get("status"), "output": str(args.output), "discovered_surface_count": result.get("discovered_surface_count")}, ensure_ascii=False, sort_keys=True))
    if args.validate:
        return 0 if result.get("status") == "passed" else 1
    return 0 if result.get("status") == "authoring_required" else 1


if __name__ == "__main__":
    raise SystemExit(main())
