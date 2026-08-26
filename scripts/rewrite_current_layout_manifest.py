"""Write one directly regenerated current layout manifest.

This is intentionally a narrow authoring helper, not a migration reader.  It
only writes `.flowguard/layout.toml` after the caller has manually classified
the target tree; the audit remains read-only and rejects the old manifest until
this direct rewrite is complete.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from flowguard.project_layout import current_layout_manifest_text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    flowguard_root = root / ".flowguard"
    if not flowguard_root.is_dir():
        raise SystemExit(f"missing current .flowguard directory: {flowguard_root}")
    destination = flowguard_root / "layout.toml"
    destination.write_text(current_layout_manifest_text(root), encoding="utf-8")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
