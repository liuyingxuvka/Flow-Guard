"""Read-light storage inventory for FlowGuard's evidence and role roots.

This route intentionally does not read payloads or hash content.  It performs
one guarded directory walk, reports counts/bytes, and leaves reachability
decisions to the evidence audit and exact GC plan.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


STORAGE_AUDIT_SCHEMA = "flowguard.storage_audit.v1"
_REPARSE_ATTRIBUTE = 0x0400


def _extended_lstat_path(path: Path) -> str | Path:
    """Return a metadata-only path that remains valid past Win32 MAX_PATH.

    ``os.walk`` can enumerate long paths on the supported Windows runtime, but
    a plain ``Path.lstat`` may still use the legacy 260-character API and
    report ``WinError 3`` for an existing entry.  The extended prefix changes
    only the OS path spelling; it does not follow links, read payloads, or
    provide a compatibility data reader.
    """

    raw = os.fspath(path)
    if os.name != "nt":
        return raw
    if raw.startswith("\\\\?\\"):
        return raw
    if raw.startswith("\\\\"):
        return "\\\\?\\UNC\\" + raw[2:]
    return "\\\\?\\" + raw


def _lstat_no_follow(path: Path):
    return os.lstat(_extended_lstat_path(path))


@dataclass(frozen=True)
class StorageAuditReport:
    status: str
    root: str
    directory_walk_count: int
    content_file_read_count: int
    content_hash_read_count: int
    content_bytes_read: int
    role_counts: Mapping[str, Mapping[str, int]]
    lifecycle_counts: Mapping[str, Mapping[str, int]]
    largest_items: tuple[Mapping[str, object], ...]
    largest_items_omitted: int
    findings: tuple[Mapping[str, str], ...]
    claim_boundary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": STORAGE_AUDIT_SCHEMA,
            "status": self.status,
            "root": self.root,
            "directory_walk_count": self.directory_walk_count,
            "content_file_read_count": self.content_file_read_count,
            "content_hash_read_count": self.content_hash_read_count,
            "content_bytes_read": self.content_bytes_read,
            "role_counts": {str(k): dict(v) for k, v in sorted(self.role_counts.items())},
            "lifecycle_counts": {str(k): dict(v) for k, v in sorted(self.lifecycle_counts.items())},
            "largest_items": [dict(item) for item in self.largest_items],
            "largest_items_omitted": self.largest_items_omitted,
            "findings": [dict(item) for item in self.findings],
            "claim_boundary": self.claim_boundary,
        }


def _role_for(relative: str) -> str:
    parts = Path(relative).parts
    if not parts:
        return "root"
    if parts[0] == ".flowguard" and len(parts) > 1:
        return str(parts[1])
    return str(parts[0])


def _lifecycle_for(relative: str, *, is_dir: bool) -> str:
    lowered = relative.lower().replace("\\", "/")
    if "/current-head" in lowered or lowered.endswith("/current.json") or "current-authority" in lowered:
        return "current"
    if "pin" in lowered or "/pinned" in lowered:
        return "pinned"
    if "lease" in lowered or "active-run" in lowered:
        return "active_lease"
    if ".flowguard/evidence" in lowered and not is_dir:
        # Without payload reads, ordinary evidence is conservatively unknown;
        # an exact GC plan must prove it collectible.
        return "unknown"
    return "unmanaged"


def audit_storage(
    root: str | Path = ".flowguard",
    *,
    max_largest_items: int = 20,
) -> StorageAuditReport:
    """Return one bounded, content-read-free storage inventory."""

    root_path = Path(root).expanduser().resolve()
    role_counts: dict[str, dict[str, int]] = {}
    lifecycle_counts: dict[str, dict[str, int]] = {}
    items: list[dict[str, object]] = []
    findings: list[dict[str, str]] = []
    if not root_path.exists():
        return StorageAuditReport(
            "blocked",
            str(root_path),
            0,
            0,
            0,
            0,
            {},
            {},
            (),
            0,
            ({"code": "root_missing", "path": str(root_path)},),
            "This read-light audit does not prove evidence reachability or current authority.",
        )
    if not root_path.is_dir() or root_path.is_symlink():
        findings.append({"code": "root_not_safe_directory", "path": str(root_path)})

    # os.walk is deliberately the only directory traversal.  We do not open
    # any file and do not call a content hashing helper on this route.
    walk_count = 1
    # Walk through the same extended spelling on Windows; otherwise
    # ``os.walk`` itself stops descending once an entry crosses MAX_PATH even
    # though the directory is present and can be enumerated through the
    # extended namespace.
    walk_root = Path(_extended_lstat_path(root_path))
    for current, dirnames, filenames in os.walk(walk_root, topdown=True, followlinks=False):
        current_path = Path(current)
        safe_dirs: list[str] = []
        for dirname in sorted(dirnames):
            path = current_path / dirname
            try:
                info = _lstat_no_follow(path)
            except OSError as exc:
                findings.append({"code": "stat_failed", "path": str(path), "message": str(exc)})
                continue
            if stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & _REPARSE_ATTRIBUTE):
                findings.append({"code": "reparse_or_symlink", "path": str(path)})
                continue
            safe_dirs.append(dirname)
        dirnames[:] = safe_dirs
        for filename in sorted(filenames):
            path = current_path / filename
            relative = str(path.relative_to(walk_root))
            try:
                info = _lstat_no_follow(path)
            except OSError as exc:
                findings.append({"code": "stat_failed", "path": relative, "message": str(exc)})
                continue
            if stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & _REPARSE_ATTRIBUTE):
                findings.append({"code": "reparse_or_symlink", "path": relative})
                continue
            size = int(info.st_size)
            role = _role_for(relative)
            role_bucket = role_counts.setdefault(role, {"files": 0, "bytes": 0})
            role_bucket["files"] += 1
            role_bucket["bytes"] += size
            lifecycle = _lifecycle_for(str(root_path / relative), is_dir=False)
            lifecycle_bucket = lifecycle_counts.setdefault(lifecycle, {"files": 0, "bytes": 0})
            lifecycle_bucket["files"] += 1
            lifecycle_bucket["bytes"] += size
            items.append({"path": relative, "bytes": size, "role": role, "lifecycle": lifecycle})

    items.sort(key=lambda item: (-int(item["bytes"]), str(item["path"])))
    bounded = tuple(items[:max(0, int(max_largest_items))])
    status = "blocked" if findings else "passed"
    return StorageAuditReport(
        status,
        str(root_path),
        walk_count,
        0,
        0,
        0,
        role_counts,
        lifecycle_counts,
        bounded,
        max(0, len(items) - len(bounded)),
        tuple(findings),
        "This read-light audit proves only path/count/byte observations; evidence reachability and current authority require the separate evidence audit and exact GC plan.",
    )


__all__ = ["STORAGE_AUDIT_SCHEMA", "StorageAuditReport", "audit_storage"]
