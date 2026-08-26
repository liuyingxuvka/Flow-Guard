"""Read bounded, deterministic slices from a complete FlowGuard artifact.

Slices are read-only terminal projections.  They never become a current
authority, are never accepted as audit input, and do not hash or rewrite the
source artifact.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


ARTIFACT_SLICE_SCHEMA = "flowguard.artifact_slice.v1"
MAX_ARTIFACT_SLICE_ROWS = 500


class ArtifactSliceError(ValueError):
    """Raised when a requested artifact slice is not representable safely."""


def read_artifact_slice(
    artifact: str | Path,
    *,
    field: str,
    offset: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    """Return one bounded list slice from an existing complete JSON artifact."""

    path = Path(artifact).resolve()
    if not path.is_file():
        raise ArtifactSliceError(f"artifact is not a file: {path}")
    if not isinstance(field, str) or not field.strip():
        raise ArtifactSliceError("field must be a non-empty dotted JSON path")
    if offset < 0 or limit <= 0 or limit > MAX_ARTIFACT_SLICE_ROWS:
        raise ArtifactSliceError(
            f"offset must be >= 0 and limit must be 1..{MAX_ARTIFACT_SLICE_ROWS}"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ArtifactSliceError(f"cannot load JSON artifact {path}: {exc}") from exc
    value: Any = payload
    for part in (piece for piece in field.split(".") if piece):
        if not isinstance(value, Mapping) or part not in value:
            raise ArtifactSliceError(f"artifact field does not exist: {field}")
        value = value[part]
    if not isinstance(value, list):
        raise ArtifactSliceError(f"artifact field is not a JSON array: {field}")
    rows = value[offset : offset + limit]
    return {
        "schema_version": ARTIFACT_SLICE_SCHEMA,
        "claim_boundary": (
            "Read-only bounded projection of a complete artifact; this slice "
            "is not a current authority and cannot be used as audit input."
        ),
        "artifact_ref": str(path),
        "field": field,
        "offset": offset,
        "limit": limit,
        "total_count": len(value),
        "returned_count": len(rows),
        "omitted_before": offset,
        "omitted_after": max(0, len(value) - offset - len(rows)),
        "rows": rows,
    }


__all__ = ["ARTIFACT_SLICE_SCHEMA", "MAX_ARTIFACT_SLICE_ROWS", "ArtifactSliceError", "read_artifact_slice"]
