"""Fail-closed audit of older FlowGuard artifacts.

This module deliberately does not migrate or rewrite old data.  A legacy
artifact is evidence that the target still needs a direct current-authority
rewrite by the maintaining agent.  Keeping a deterministic ``--apply`` path
would create a second compatibility authority and would let an old artifact
become current without re-authoring its model, owner, tests, and receipts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .behavior_commitment import (
    BCL_LEDGER_ARTIFACT_TYPE,
    BCL_LEDGER_FORMAT_VERSION,
    behavior_commitment_ledger_from_mapping,
    behavior_commitment_ledger_to_mapping,
)
from .export import to_jsonable
from .schema import SCHEMA_VERSION


ARTIFACT_UPGRADE_STATUS_UNCHANGED = "unchanged"
ARTIFACT_UPGRADE_STATUS_BLOCKED = "blocked"
ARTIFACT_UPGRADE_STATUS_SKIPPED = "skipped"
ARTIFACT_UPGRADE_POLICY = "direct_current_rewrite_only"

ARTIFACT_UPGRADE_STATUSES = {
    ARTIFACT_UPGRADE_STATUS_UNCHANGED,
    ARTIFACT_UPGRADE_STATUS_BLOCKED,
    ARTIFACT_UPGRADE_STATUS_SKIPPED,
}

ARTIFACT_UPGRADE_TEXT_REPLACEMENTS = {
    "PlanIntakeSurface": "PlanIntakeRiskSurface",
    "PlanIntakeCompletenessFinding": "PlanIntakeFinding",
    "FalseNegativeBackpropagationCase": "FalseNegativeCase",
    "FlowGuardClaimFinding": "FlowGuardClaimChainFinding",
    "review_plan_mutation_results": "review_plan_mutations",
    "FunctionResult.state": "FunctionResult.new_state",
}

_DEFAULT_SCAN_DIRS = (
    ".flowguard",
    ".agents/skills",
    "docs",
    "examples",
    "scripts",
    "tests",
)
_TEXT_SUFFIXES = {".md", ".py", ".txt", ".rst"}
_JSON_SUFFIXES = {".json"}
_TOML_SUFFIXES = {".toml"}
_SCAN_SUFFIXES = _TEXT_SUFFIXES | _JSON_SUFFIXES | _TOML_SUFFIXES
_IGNORED_PARTS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "build",
    "dist",
    "flowguard.egg-info",
    "tmp",
}
_UNKNOWN_SCRIPT_MARKERS = (
    "legacy_flowguard_runtime_path",
    "old_flowguard_behavior",
    "flowguard_legacy_runtime_path",
)

_LEGACY_BCL_DEPENDENCY_FIELD = "dependency_commitment_ids"
# Exact `to_dict()` field sets from the final pre-migration producer commit
# 56083c1e47602654089e05701e9f5b42cce6c9a1. That producer emitted every
# listed key; none of these fields is optional in its serialized JSON shape.
_BCL_ENVELOPE_FIELDS = frozenset(
    {"artifact_type", "schema_version", "format_version", "ledger"}
)
_LEGACY_BCL_LEDGER_FIELDS = frozenset(
    {
        "ledger_id",
        "project_boundary",
        "current_revision",
        "commitments",
        "source_surfaces",
        "expected_commitment_ids",
        "claim_scope",
        "change_mode",
        "require_current_evidence",
        "require_risk_gates_for_broad_claim",
        "owner",
        "validation_boundary",
        "rationale",
        "metadata",
    }
)
_LEGACY_BCL_COMMITMENT_FIELDS = frozenset(
    {
        "commitment_id",
        "label",
        "commitment_kind",
        "actor",
        "trigger",
        "expected_result",
        "failure_boundary",
        "source_surface_ids",
        "source_refs",
        "primary_owner_model_id",
        "supporting_model_ids",
        "child_model_ids",
        "dependency_commitment_ids",
        "excluded_behavior_ids",
        "replacement_state",
        "model_sync_state",
        "miss_origin_state",
        "path_authority",
        "evidence",
        "in_scope",
        "scoped_out_reason",
        "owner",
        "validation_boundary",
        "rationale",
        "metadata",
    }
)
_LEGACY_BCL_SOURCE_SURFACE_FIELDS = frozenset(
    {
        "surface_id",
        "surface_kind",
        "label",
        "source_ref",
        "commitment_ids",
        "freshness_state",
        "in_scope",
        "scoped_out_reason",
        "owner",
        "validation_boundary",
        "rationale",
        "metadata",
    }
)
_LEGACY_BCL_EVIDENCE_FIELDS = frozenset(
    {
        "model_obligation_ids",
        "code_contract_ids",
        "test_evidence_ids",
        "proof_artifact_ids",
        "risk_gate_ids",
        "coverage_case_ids",
        "coverage_shard_ids",
        "coverage_receipt_ids",
        "evidence_state",
        "test_mesh_state",
        "current",
        "metadata",
    }
)
_LEGACY_BCL_PATH_AUTHORITY_FIELDS = frozenset(
    {
        "path_sensitive",
        "business_intent",
        "ppa_report_id",
        "ppa_decision",
        "ppa_confidence",
        "ppa_ok",
        "primary_path_ids",
        "fallback_candidate_ids",
        "ppa_coverage_receipt_ids",
        "ppa_coverage_shard_ids",
        "ppa_risk_gate_ids",
        "scoped_out_reason",
        "evidence_refs",
        "metadata",
    }
)


@dataclass(frozen=True)
class FlowGuardJsonArtifactRegistration:
    """Exact current-only producer shape for one FlowGuard JSON artifact."""

    artifact_type: str
    version_field: str
    current_versions: frozenset[str]
    allowed_fields: frozenset[str]
    field_types: tuple[tuple[str, type], ...]
    required_values: tuple[tuple[str, str], ...] = ()


_FLOWGUARD_JSON_ARTIFACT_REGISTRY: Mapping[
    str, FlowGuardJsonArtifactRegistration
] = MappingProxyType(
    {
        artifact_type: FlowGuardJsonArtifactRegistration(
            artifact_type=artifact_type,
            version_field="schema_version",
            current_versions=frozenset({SCHEMA_VERSION}),
            allowed_fields=frozenset(
                {
                    "schema_version",
                    "artifact_type",
                    "created_by",
                    "model_name",
                    "scenario_name",
                    "trace_id",
                    "payload",
                }
            ),
            field_types=(
                ("schema_version", str),
                ("artifact_type", str),
                ("created_by", str),
                ("model_name", str),
                ("scenario_name", str),
                ("trace_id", str),
            ),
            required_values=(("created_by", "flowguard"),),
        )
        for artifact_type in ("report", "trace")
    }
)


@dataclass(frozen=True)
class ArtifactUpgradeItem:
    """One file or artifact considered by an upgrade scan."""

    path: str
    item_kind: str
    status: str
    detected_shape: str = ""
    replacement: str = ""
    message: str = ""
    changed: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        status = str(self.status)
        if status not in ARTIFACT_UPGRADE_STATUSES:
            raise ValueError(f"unknown artifact upgrade status: {status!r}")
        object.__setattr__(self, "path", str(self.path))
        object.__setattr__(self, "item_kind", str(self.item_kind))
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "detected_shape", str(self.detected_shape))
        object.__setattr__(self, "replacement", str(self.replacement))
        object.__setattr__(self, "message", str(self.message))
        object.__setattr__(self, "changed", bool(self.changed))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "item_kind": self.item_kind,
            "status": self.status,
            "detected_shape": self.detected_shape,
            "replacement": self.replacement,
            "message": self.message,
            "changed": self.changed,
            "metadata": to_jsonable(dict(self.metadata)),
        }


@dataclass(frozen=True)
class ArtifactUpgradeReport:
    """Summary of an artifact/schema upgrade scan."""

    root: str
    apply: bool = False
    items: tuple[ArtifactUpgradeItem, ...] = ()
    summary: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", str(self.root))
        object.__setattr__(self, "items", tuple(self.items))
        if not self.summary:
            object.__setattr__(self, "summary", self._build_summary())

    @property
    def ok(self) -> bool:
        return not any(item.status == ARTIFACT_UPGRADE_STATUS_BLOCKED for item in self.items)

    @property
    def changed_files(self) -> tuple[str, ...]:
        return tuple(item.path for item in self.items if item.changed)

    @property
    def blocked_paths(self) -> tuple[str, ...]:
        return tuple(item.path for item in self.items if item.status == ARTIFACT_UPGRADE_STATUS_BLOCKED)

    @property
    def upgraded_count(self) -> int:
        # Kept as a zero-valued diagnostic field for the current report shape;
        # this module no longer exposes or performs any upgrade operation.
        return 0

    @property
    def blocked_count(self) -> int:
        return sum(1 for item in self.items if item.status == ARTIFACT_UPGRADE_STATUS_BLOCKED)

    @property
    def scanned_count(self) -> int:
        return len(self.items)

    def _build_summary(self) -> str:
        mode = "apply" if self.apply else "dry_run"
        return (
            f"{mode}: scanned={self.scanned_count} upgraded={self.upgraded_count} "
            f"blocked={self.blocked_count} changed={len(self.changed_files)}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": "flowguard_artifact_upgrade_report",
            "policy": ARTIFACT_UPGRADE_POLICY,
            "ok": self.ok,
            "root": self.root,
            "apply": self.apply,
            "summary": self.summary,
            "scanned_count": self.scanned_count,
            "upgraded_count": self.upgraded_count,
            "blocked_count": self.blocked_count,
            "changed_files": list(self.changed_files),
            "blocked_paths": list(self.blocked_paths),
            "items": [item.to_dict() for item in self.items],
            "validation_note": (
                "Legacy artifacts are rejected. No automatic migration or "
                "compatibility rewrite is performed; direct current-authority "
                "rewriting must be followed by current checks and receipts."
            ),
        }

    def to_json_text(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def format_text(self, max_items: int = 20) -> str:
        lines = [
            "=== flowguard artifact upgrade ===",
            f"status: {'pass' if self.ok else 'blocked'}",
            f"root: {self.root}",
            f"mode: {'apply' if self.apply else 'dry-run'}",
            f"summary: {self.summary}",
            "policy: legacy artifacts are rejected; no automatic migration or compatibility rewrite is performed.",
        ]
        for item in self.items[:max_items]:
            lines.extend(
                [
                    "",
                    f"- {item.status}: {item.path}",
                    f"  kind: {item.item_kind}",
                    f"  shape: {item.detected_shape or '(none)'}",
                    f"  message: {item.message}",
                ]
            )
            if item.replacement:
                lines.append(f"  replacement: {item.replacement}")
        if len(self.items) > max_items:
            lines.append(f"... {len(self.items) - max_items} more items")
        return "\n".join(lines)


def _is_json_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _has_exact_legacy_evidence_shape(value: Any) -> bool:
    if not isinstance(value, Mapping) or set(value) != _LEGACY_BCL_EVIDENCE_FIELDS:
        return False
    list_fields = _LEGACY_BCL_EVIDENCE_FIELDS - {
        "evidence_state",
        "test_mesh_state",
        "current",
        "metadata",
    }
    return (
        all(_is_json_string_list(value[field]) for field in list_fields)
        and isinstance(value["evidence_state"], str)
        and isinstance(value["test_mesh_state"], str)
        and isinstance(value["current"], bool)
        and isinstance(value["metadata"], Mapping)
    )


def _has_exact_legacy_path_authority_shape(value: Any) -> bool:
    if not isinstance(value, Mapping) or set(value) != _LEGACY_BCL_PATH_AUTHORITY_FIELDS:
        return False
    string_fields = {
        "business_intent",
        "ppa_report_id",
        "ppa_decision",
        "ppa_confidence",
        "scoped_out_reason",
    }
    list_fields = {
        "primary_path_ids",
        "fallback_candidate_ids",
        "ppa_coverage_receipt_ids",
        "ppa_coverage_shard_ids",
        "ppa_risk_gate_ids",
        "evidence_refs",
    }
    return (
        isinstance(value["path_sensitive"], bool)
        and all(isinstance(value[field], str) for field in string_fields)
        and (
            value["ppa_ok"] is None
            or isinstance(value["ppa_ok"], bool)
        )
        and all(_is_json_string_list(value[field]) for field in list_fields)
        and isinstance(value["metadata"], Mapping)
    )


def _has_exact_legacy_source_surface_shape(value: Any) -> bool:
    if not isinstance(value, Mapping) or set(value) != _LEGACY_BCL_SOURCE_SURFACE_FIELDS:
        return False
    string_fields = _LEGACY_BCL_SOURCE_SURFACE_FIELDS - {
        "commitment_ids",
        "in_scope",
        "metadata",
    }
    return (
        all(isinstance(value[field], str) for field in string_fields)
        and _is_json_string_list(value["commitment_ids"])
        and isinstance(value["in_scope"], bool)
        and isinstance(value["metadata"], Mapping)
    )


def _has_exact_legacy_commitment_shape(value: Any) -> bool:
    if not isinstance(value, Mapping) or set(value) != _LEGACY_BCL_COMMITMENT_FIELDS:
        return False
    string_fields = _LEGACY_BCL_COMMITMENT_FIELDS - {
        "source_surface_ids",
        "source_refs",
        "supporting_model_ids",
        "child_model_ids",
        _LEGACY_BCL_DEPENDENCY_FIELD,
        "excluded_behavior_ids",
        "path_authority",
        "evidence",
        "in_scope",
        "metadata",
    }
    list_fields = {
        "source_surface_ids",
        "source_refs",
        "supporting_model_ids",
        "child_model_ids",
        _LEGACY_BCL_DEPENDENCY_FIELD,
        "excluded_behavior_ids",
    }
    return (
        all(isinstance(value[field], str) for field in string_fields)
        and all(_is_json_string_list(value[field]) for field in list_fields)
        and _has_exact_legacy_path_authority_shape(value["path_authority"])
        and _has_exact_legacy_evidence_shape(value["evidence"])
        and isinstance(value["in_scope"], bool)
        and isinstance(value["metadata"], Mapping)
    )


def _has_exact_legacy_behavior_ledger_shape(data: Mapping[str, Any]) -> bool:
    if set(data) != _LEGACY_BCL_LEDGER_FIELDS:
        return False
    string_fields = _LEGACY_BCL_LEDGER_FIELDS - {
        "commitments",
        "source_surfaces",
        "expected_commitment_ids",
        "require_current_evidence",
        "require_risk_gates_for_broad_claim",
        "metadata",
    }
    commitments = data["commitments"]
    source_surfaces = data["source_surfaces"]
    return (
        all(isinstance(data[field], str) for field in string_fields)
        and isinstance(commitments, list)
        and all(_has_exact_legacy_commitment_shape(row) for row in commitments)
        and isinstance(source_surfaces, list)
        and all(
            _has_exact_legacy_source_surface_shape(surface)
            for surface in source_surfaces
        )
        and _is_json_string_list(data["expected_commitment_ids"])
        and isinstance(data["require_current_evidence"], bool)
        and isinstance(data["require_risk_gates_for_broad_claim"], bool)
        and isinstance(data["metadata"], Mapping)
    )


def _looks_like_behavior_ledger_mapping(data: Mapping[str, Any]) -> bool:
    if str(data.get("artifact_type", "")) == BCL_LEDGER_ARTIFACT_TYPE:
        return True
    if "artifact_type" in data or "ledger" in data:
        return False
    return _has_exact_legacy_behavior_ledger_shape(data)


def _current_behavior_ledger_envelope_findings(
    data: Mapping[str, Any],
) -> tuple[str, ...]:
    findings: list[str] = []
    actual_fields = set(data)
    if actual_fields != _BCL_ENVELOPE_FIELDS:
        missing = sorted(_BCL_ENVELOPE_FIELDS - actual_fields)
        extra = sorted(actual_fields - _BCL_ENVELOPE_FIELDS)
        if missing:
            findings.append(f"missing_fields:{','.join(missing)}")
        if extra:
            findings.append(f"extra_fields:{','.join(extra)}")
    if data.get("artifact_type") != BCL_LEDGER_ARTIFACT_TYPE:
        findings.append("artifact_type_not_current")
    if data.get("schema_version") != SCHEMA_VERSION:
        findings.append("schema_version_not_current")
    if data.get("format_version") != BCL_LEDGER_FORMAT_VERSION:
        findings.append("format_version_not_current")
    if findings:
        return tuple(findings)
    try:
        normalized = behavior_commitment_ledger_from_mapping(data)
        canonical = behavior_commitment_ledger_to_mapping(normalized)
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        return (f"current_payload_invalid:{type(exc).__name__}",)
    if canonical != dict(data):
        return ("current_payload_not_exact_canonical_shape",)
    return ()


def review_artifact_upgrades(
    root: str | Path = ".",
    *,
    include_dirs: Sequence[str] = _DEFAULT_SCAN_DIRS,
    paths: Sequence[str | Path] = (),
) -> ArtifactUpgradeReport:
    """Scan for stale FlowGuard artifacts without providing an upgrade path.

    This is a read-only currentness diagnostic.  It never produces an
    upgraded mapping, rewrites a source file, or accepts a historical shape.
    A blocked item is a handoff to the maintaining agent for direct current
    source/model authorship and fresh validation.
    """

    root_path = Path(root).resolve()
    candidates = tuple(_candidate_paths(root_path, include_dirs=include_dirs, paths=paths))
    items: list[ArtifactUpgradeItem] = []
    for path in candidates:
        item = _review_path(path, root_path=root_path)
        if item is not None:
            items.append(item)
    return ArtifactUpgradeReport(root=str(root_path), items=tuple(items))


def _candidate_paths(
    root_path: Path,
    *,
    include_dirs: Sequence[str],
    paths: Sequence[str | Path],
):
    explicit = tuple(paths)
    if explicit:
        for path in explicit:
            resolved = Path(path)
            if not resolved.is_absolute():
                resolved = root_path / resolved
            if resolved.is_file() and _is_scannable(resolved, root_path=root_path):
                yield resolved
            elif resolved.is_dir():
                yield from _walk_scannable(resolved, root_path=root_path)
        return
    for name in include_dirs:
        directory = root_path / name
        if directory.is_dir():
            yield from _walk_scannable(directory, root_path=root_path)


def _walk_scannable(directory: Path, *, root_path: Path):
    for path in sorted(directory.rglob("*")):
        if path.is_file() and _is_scannable(path, root_path=root_path):
            yield path


def _is_scannable(path: Path, *, root_path: Path | None = None) -> bool:
    if path.suffix.lower() not in _SCAN_SUFFIXES:
        return False
    parts = path.parts
    if root_path is not None:
        try:
            parts = path.resolve().relative_to(root_path).parts
        except ValueError:
            parts = path.parts
    return not any(part in _IGNORED_PARTS for part in parts)


def _review_path(path: Path, *, root_path: Path) -> ArtifactUpgradeItem | None:
    suffix = path.suffix.lower()
    rel_path = _relative_path(path, root_path)
    if suffix in _JSON_SUFFIXES:
        return _review_json_path(path, rel_path=rel_path)
    if suffix in _TEXT_SUFFIXES:
        return _review_text_path(path, rel_path=rel_path)
    if suffix in _TOML_SUFFIXES:
        return _review_toml_path(path, rel_path=rel_path)
    return None


def _review_json_path(path: Path, *, rel_path: str) -> ArtifactUpgradeItem | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None

    if str(data.get("artifact_type", "")) == BCL_LEDGER_ARTIFACT_TYPE:
        envelope_findings = _current_behavior_ledger_envelope_findings(data)
        if envelope_findings:
            return ArtifactUpgradeItem(
                rel_path,
                "behavior_commitment_ledger",
                ARTIFACT_UPGRADE_STATUS_BLOCKED,
                detected_shape="non_current_behavior_commitment_ledger",
                replacement="direct_current_model_and_ledger_rewrite",
                message=(
                    "behavior ledger is not the exact current canonical shape; "
                    "rewrite the current model and ledger directly, then rerun checks"
                ),
                metadata={
                    "findings": list(envelope_findings),
                    "policy": ARTIFACT_UPGRADE_POLICY,
                },
            )
        return ArtifactUpgradeItem(
            rel_path,
            "behavior_commitment_ledger",
            ARTIFACT_UPGRADE_STATUS_UNCHANGED,
            detected_shape="current_behavior_commitment_ledger",
            replacement=f"{BCL_LEDGER_ARTIFACT_TYPE}:{BCL_LEDGER_FORMAT_VERSION}",
            message="behavior ledger already uses the exact current canonical shape",
            metadata={"policy": ARTIFACT_UPGRADE_POLICY},
        )

    if _has_exact_legacy_behavior_ledger_shape(data):
        return ArtifactUpgradeItem(
            rel_path,
            "behavior_commitment_ledger",
            ARTIFACT_UPGRADE_STATUS_BLOCKED,
            detected_shape="legacy_behavior_commitment_ledger",
            replacement="direct_current_model_and_ledger_rewrite",
            message=(
                "legacy behavior ledger is rejected; no in-memory conversion or "
                "automatic rewrite is available; author the current model and ledger directly"
            ),
            metadata={
                "policy": ARTIFACT_UPGRADE_POLICY,
                "legacy_field": _LEGACY_BCL_DEPENDENCY_FIELD,
            },
        )

    registration = _registered_flowguard_json_artifact(data)
    if registration is None:
        return None

    shape_findings = _registration_shape_findings(data, registration)
    if shape_findings:
        return ArtifactUpgradeItem(
            rel_path,
            "registered_json_artifact",
            ARTIFACT_UPGRADE_STATUS_BLOCKED,
            detected_shape="malformed_registered_artifact",
            message="registered FlowGuard artifact does not match its exact producer shape",
            metadata={
                "artifact_type": registration.artifact_type,
                "version_field": registration.version_field,
                "findings": list(shape_findings),
            },
        )
    schema_version = data[registration.version_field]
    if schema_version in registration.current_versions:
        return ArtifactUpgradeItem(
            rel_path,
            "registered_json_artifact",
            ARTIFACT_UPGRADE_STATUS_UNCHANGED,
            detected_shape=f"schema_version:{schema_version}",
            message="registered FlowGuard artifact already uses the current schema",
            metadata={
                "artifact_type": registration.artifact_type,
                "version_field": registration.version_field,
                "current_versions": sorted(registration.current_versions),
            },
        )

    return ArtifactUpgradeItem(
        rel_path,
        "registered_json_artifact",
        ARTIFACT_UPGRADE_STATUS_BLOCKED,
        detected_shape=f"schema_version:{schema_version}",
        message="registered FlowGuard artifact version is not current and has no migration route",
        metadata={
            "artifact_type": registration.artifact_type,
            "version_field": registration.version_field,
            "current_versions": sorted(registration.current_versions),
            "policy": ARTIFACT_UPGRADE_POLICY,
        },
    )


def _registered_flowguard_json_artifact(
    data: Mapping[str, Any],
) -> FlowGuardJsonArtifactRegistration | None:
    artifact_type = str(data.get("artifact_type", ""))
    return _FLOWGUARD_JSON_ARTIFACT_REGISTRY.get(artifact_type)


def _registration_shape_findings(
    data: Mapping[str, Any],
    registration: FlowGuardJsonArtifactRegistration,
) -> tuple[str, ...]:
    findings: list[str] = []
    actual_fields = set(data)
    missing = sorted(registration.allowed_fields - actual_fields)
    extra = sorted(actual_fields - registration.allowed_fields)
    if missing:
        findings.append(f"missing_fields:{','.join(missing)}")
    if extra:
        findings.append(f"extra_fields:{','.join(extra)}")
    for field, expected_type in registration.field_types:
        if field in data and not isinstance(data[field], expected_type):
            findings.append(
                f"field_type:{field}:{type(data[field]).__name__}!={expected_type.__name__}"
            )
    for field, expected in registration.required_values:
        if field in data and data[field] != expected:
            findings.append(f"field_value:{field}:{data[field]!r}!={expected!r}")
    return tuple(findings)


def _review_text_path(path: Path, *, rel_path: str) -> ArtifactUpgradeItem | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    if rel_path == "docs/flowguard_adoption_log.md":
        return _skipped_text_item(rel_path, "historical_adoption_log")

    if (
        rel_path == ".flowguard/models/owners/behavior_commitment_ledger/model.py"
        and "load_behavior_commitment_ledger" not in text
        and ("BehaviorCommitment(" in text or "BehaviorCommitmentLedger(" in text)
    ):
        return ArtifactUpgradeItem(
            rel_path,
            "python_script",
            ARTIFACT_UPGRADE_STATUS_BLOCKED,
            detected_shape="embedded_python_behavior_ledger_inventory",
            replacement="canonical ledger.json plus thin loader",
            message=(
                "embedded Python behavior inventory is not executed by the audit; "
                "author or classify it into the canonical current ledger directly"
            ),
        )

    unknown_markers = tuple(marker for marker in _UNKNOWN_SCRIPT_MARKERS if marker in text)
    if path.suffix.lower() == ".py" and unknown_markers:
        return ArtifactUpgradeItem(
            rel_path,
            "python_script",
            ARTIFACT_UPGRADE_STATUS_BLOCKED,
            detected_shape="unknown_behavior_script",
            message="behavior-bearing script contains an unknown legacy FlowGuard marker",
            metadata={"markers": list(unknown_markers), "policy": ARTIFACT_UPGRADE_POLICY},
        )

    replacements = {
        old: new
        for old, new in ARTIFACT_UPGRADE_TEXT_REPLACEMENTS.items()
        if old in text
    }
    if not replacements:
        return None
    if rel_path.startswith("tests/") and ("removed_aliases" in text or "assertNotIn" in text):
        return _skipped_text_item(rel_path, "negative_legacy_test")
    return ArtifactUpgradeItem(
        rel_path,
        "text_reference" if path.suffix.lower() != ".py" else "python_script",
        ARTIFACT_UPGRADE_STATUS_BLOCKED,
        detected_shape="obsolete_api_aliases",
        replacement="current_route_first_api",
        message=(
            "obsolete FlowGuard aliases require a direct current-source rewrite; "
            "automatic compatibility replacement is disabled"
        ),
        changed=False,
        metadata={"replacements": replacements, "policy": ARTIFACT_UPGRADE_POLICY},
    )


def _skipped_text_item(rel_path: str, detected_shape: str) -> ArtifactUpgradeItem:
    return ArtifactUpgradeItem(
        rel_path,
        "text_reference",
        ARTIFACT_UPGRADE_STATUS_SKIPPED,
        detected_shape=detected_shape,
        message="historical or negative legacy evidence is preserved rather than rewritten",
    )


def _review_toml_path(path: Path, *, rel_path: str) -> ArtifactUpgradeItem | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if "schema_version" not in text or "flowguard" not in text.lower():
        return None
    if f'schema_version = "{SCHEMA_VERSION}"' in text:
        return ArtifactUpgradeItem(
            rel_path,
            "project_manifest",
            ARTIFACT_UPGRADE_STATUS_UNCHANGED,
            detected_shape=f"schema_version:{SCHEMA_VERSION}",
            message="project manifest already records the current FlowGuard schema",
        )
    return ArtifactUpgradeItem(
        rel_path,
        "project_manifest",
        ARTIFACT_UPGRADE_STATUS_BLOCKED,
        detected_shape="manifest_schema_mismatch",
        message=(
            "project manifest schema is not current; rewrite the manifest directly "
            "and rerun current adoption checks"
        ),
    )
def _relative_path(path: Path, root_path: Path) -> str:
    try:
        return path.resolve().relative_to(root_path).as_posix()
    except ValueError:
        return str(path.resolve())


__all__ = [
    "ARTIFACT_UPGRADE_POLICY",
    "ARTIFACT_UPGRADE_STATUS_BLOCKED",
    "ARTIFACT_UPGRADE_STATUS_SKIPPED",
    "ARTIFACT_UPGRADE_STATUS_UNCHANGED",
    "ARTIFACT_UPGRADE_STATUSES",
    "ARTIFACT_UPGRADE_TEXT_REPLACEMENTS",
    "ArtifactUpgradeItem",
    "ArtifactUpgradeReport",
    "review_artifact_upgrades",
]
