"""Strict, human-readable layout governance for a target project's ``.flowguard``.

The project control plane is intentionally split by *role*, not by the order in
which historical checks happened to create files.  This module is read-only:
it audits the current directory and emits a direct-current repair plan, but it
never moves, copies, deletes, or silently reads an older layout.

The layout manifest is deliberately a small TOML document so a person can
understand it without opening the Python package.  Every current FlowGuard
project must use this layout: an unknown entry, a retired name such as
``dna_audit`` or ``tmp``, a path role collision, or a stale manifest blocks the
project.  A maintainer/AI must directly classify and rewrite an old target into
the current layout before retrying; this module never performs that rewrite and
there is no opt-in, compatibility reader, or automatic migration path.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .observation_metrics import InvocationMetrics


PROJECT_LAYOUT_SCHEMA = "flowguard.project_layout.v3"
PROJECT_LAYOUT_VERSION = 3
PROJECT_LAYOUT_INVENTORY_SCHEMA = "flowguard.project_layout_shape.v1"
PROJECT_LAYOUT_MANIFEST = ".flowguard/layout.toml"
PROJECT_LAYOUT_CLAIM_BOUNDARY = (
    "This audit proves only the exact .flowguard role layout, manifest identity, "
    "and direct-current naming boundary. It does not prove model semantics, "
    "tests, execution, installation, release, or business behavior."
)

# These are the only role roots a current target project may use.  The names
# describe what a human will find there; the word DNA is intentionally absent.
CANONICAL_ROLE_ROOTS: tuple[tuple[str, str], ...] = (
    ("behavior", "current_effective_intent_and_behavior_contracts"),
    ("models", "current_executable_model_authority"),
    ("structure", "surface_ownership_and_code_binding_maps"),
    ("verification", "test_and_check_definitions"),
    ("evidence", "immutable_execution_evidence"),
    ("history", "explicit_historical_context"),
)
CANONICAL_ROLE_ROOT_NAMES = frozenset(name for name, _ in CANONICAL_ROLE_ROOTS)
# Historical and transient material is deliberately not current authority.
# It may contain long receipt paths or tool-specific names that are valid as
# provenance but cannot affect the current model/verification layout.  Keep the
# complete contents opaque: the evidence/history owners validate their own
# pointers and payloads, while this module only proves that the two containers
# exist in the right role roots.
OPAQUE_ROLE_ROOTS = frozenset({"evidence", "history"})
CANONICAL_FILES: Mapping[str, str] = {
    "project.toml": "project_identity_and_policy",
    "layout.toml": "layout_authority",
    "adoption_log.jsonl": "process_log",
    "README.md": "human_navigation_only",
}

# A name that looks descriptive in an old checkout is not allowed to become a
# second authority in a current checkout.  Keep this list explicit and small;
# generic words such as ``reports`` are not rejected unless they occur in a
# forbidden position.
RETIRED_LAYOUT_COMPONENTS = frozenset(
    {
        "dna",
        "dna_audit",
        "software_dna",
        "portable_dna",
        "tmp",
        "temp",
        "run_artifacts",
        "materialization",
        "bundle",
        "bundles",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        ".hypothesis",
        "cache",
        "caches",
    }
)
BYTECODE_SUFFIXES = frozenset({".pyc", ".pyo"})
NON_AUTHORITY_ROLES = frozenset({"evidence", "history"})
CURRENT_AUTHORITY_ROLES = frozenset(
    name for name in CANONICAL_ROLE_ROOT_NAMES if name not in NON_AUTHORITY_ROLES
)
# Python package markers such as ``__init__.py`` are legitimate current
# content.  A leading dot remains disallowed so hidden temporary files cannot
# silently become part of the current control plane.
_SAFE_COMPONENT_RE = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9._-]*|[A-Za-z0-9][A-Za-z0-9._-]*)$")
_OWNER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


@dataclass(frozen=True)
class ProjectLayoutFinding:
    """One deterministic layout finding."""

    severity: str
    code: str
    path: str = ""
    message: str = ""
    recommendation: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.severity not in {"info", "warning", "blocked"}:
            raise ValueError("severity must be info, warning, or blocked")
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class LayoutObservation:
    """One guarded, invocation-local shape observation of ``.flowguard``.

    The observation contains paths and entry kinds only.  It deliberately has
    no member-content fingerprints; governed source identity is owned by the
    model/validation routes that consume the relevant files.
    """

    root: str
    paths: tuple[Path, ...] = ()
    traversal_findings: tuple[ProjectLayoutFinding, ...] = ()


@dataclass(frozen=True)
class ProjectLayoutReport:
    """Read-only result for the target project's current layout."""

    root: str
    flowguard_root: str
    status: str
    schema: str = PROJECT_LAYOUT_SCHEMA
    layout_version: int | None = None
    manifest_fingerprint: str = ""
    project_identity: str = ""
    inventory_fingerprint: str = ""
    observed_entries: tuple[str, ...] = ()
    role_counts: Mapping[str, int] = field(default_factory=dict)
    findings: tuple[ProjectLayoutFinding, ...] = ()
    claim_boundary: str = PROJECT_LAYOUT_CLAIM_BOUNDARY
    metrics: Mapping[str, object] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "pass" and not any(
            finding.severity == "blocked" for finding in self.findings
        )

    @property
    def blockers(self) -> tuple[ProjectLayoutFinding, ...]:
        return tuple(
            finding for finding in self.findings if finding.severity == "blocked"
        )

    @property
    def next_actions(self) -> tuple[str, ...]:
        if self.ok:
            return ()
        return (
            "Stop before reading old layout paths as current authority.",
            "Manually classify every blocked entry into one current role or an explicit retirement/history record.",
            "Create a new current .flowguard/layout.toml and rebuild affected model, contract, test, and evidence identities.",
            "Rerun project-layout-audit before project-audit, model work, or execution claims.",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": "flowguard_project_layout_report",
            "schema": self.schema,
            "root": self.root,
            "flowguard_root": self.flowguard_root,
            "status": self.status,
            "ok": self.ok,
            "layout_version": self.layout_version,
            "manifest_fingerprint": self.manifest_fingerprint,
            "project_identity": self.project_identity,
            "inventory_fingerprint": self.inventory_fingerprint,
            "observed_entries": list(self.observed_entries),
            "role_counts": dict(sorted(self.role_counts.items())),
            "findings": [finding.to_dict() for finding in self.findings],
            "blockers": [finding.to_dict() for finding in self.blockers],
            "next_actions": list(self.next_actions),
            "claim_boundary": self.claim_boundary,
            "metrics": dict(self.metrics),
        }

    def to_json_text(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)

    def format_text(self) -> str:
        lines = [
            f"FlowGuard project layout: {self.status}",
            f"root: {self.root}",
            f"layout version: {self.layout_version if self.layout_version is not None else 'unknown'}",
            f"project identity: {self.project_identity or 'unknown'}",
            f"entries: {len(self.observed_entries)}",
        ]
        if self.role_counts:
            lines.append("roles:")
            lines.extend(
                f"  - {role}: {count}" for role, count in sorted(self.role_counts.items())
            )
        if self.findings:
            lines.append("findings:")
            for finding in self.findings:
                suffix = f" [{finding.path}]" if finding.path else ""
                lines.append(f"  - {finding.severity}: {finding.code}{suffix}: {finding.message}")
        if self.next_actions:
            lines.append("next actions:")
            lines.extend(f"  - {action}" for action in self.next_actions)
        lines.append(f"claim boundary: {self.claim_boundary}")
        return "\n".join(lines)


def current_layout_manifest_text(
    root: str | Path | None = None, *, project_identity: str | None = None
) -> str:
    """Return the exact current manifest text for a direct manual rewrite.

    Supplying ``root`` emits the complete role-shape inventory for that
    target.  The rows contain only path, role, and entry kind; content
    currentness belongs to the owning model/validation route.  Omitting the
    root emits an empty deferred inventory for a brand-new scaffold.
    """

    root_path = Path(root).resolve() if root is not None else None
    flowguard_root = root_path / ".flowguard" if root_path is not None else None
    members, inventory_fingerprint, role_fingerprints = (
        _layout_inventory(flowguard_root)
        if flowguard_root is not None and flowguard_root.is_dir()
        else ((), _canonical_json_fingerprint([]), {})
    )
    identity = (
        str(project_identity)
        if project_identity is not None
        else (_project_identity(root_path) if root_path is not None else "")
    )
    identity_fingerprint = (
        _canonical_json_fingerprint({"project_identity": identity}) if identity else ""
    )
    authority_pointer, authority_fingerprint = (
        _model_authority_metadata(root_path) if root_path is not None else ("", "")
    )
    mode = "exact" if root_path is not None else "deferred"
    role_fingerprints = {
        role: role_fingerprints.get(role, _canonical_json_fingerprint([]))
        for role in sorted(CANONICAL_ROLE_ROOT_NAMES)
    }
    lines = [
        "[flowguard_layout]",
        f'schema = {json.dumps(PROJECT_LAYOUT_SCHEMA)}',
        f"version = {PROJECT_LAYOUT_VERSION}",
        'authority = "current"',
        'canonical_root = ".flowguard"',
        f'project_identity = {json.dumps(identity)}',
        f'project_identity_fingerprint = {json.dumps(identity_fingerprint)}',
        f'model_authority_pointer = {json.dumps(authority_pointer)}',
        f'model_authority_fingerprint = {json.dumps(authority_fingerprint)}',
        "non_authority_roots = " + json.dumps(sorted(NON_AUTHORITY_ROLES)),
        "",
        "[roots]",
    ]
    for name, role in CANONICAL_ROLE_ROOTS:
        lines.append(f'{name.replace("-", "_")} = "{name}"  # {role}')
    lines.extend(["", "[role_authority]"])
    for name, _role in CANONICAL_ROLE_ROOTS:
        state = "non_authority" if name in NON_AUTHORITY_ROLES else "current"
        lines.append(f'{name.replace("-", "_")} = "{state}"')
    lines.extend(
        [
            "",
            "[inventory]",
            f'schema = {json.dumps(PROJECT_LAYOUT_INVENTORY_SCHEMA)}',
            f'mode = {json.dumps(mode)}',
            f'fingerprint = {json.dumps(inventory_fingerprint)}',
            f"member_count = {len(members)}",
            "role_fingerprints = {"
            + ", ".join(
                f'{role} = {json.dumps(role_fingerprints[role])}'
                for role in sorted(role_fingerprints)
            )
            + "}",
        ]
    )
    if not members:
        # TOML needs an explicit empty array so the current parser can
        # distinguish an intentionally empty shape from an obsolete manifest
        # that omitted the inventory member field altogether.
        lines.append("members = []")
    for member in members:
        lines.extend(
            [
                "",
                "[[inventory.members]]",
                f'path = {json.dumps(member["path"])}',
                f'role = {json.dumps(member["role"])}',
                f'kind = {json.dumps(member["kind"])}',
            ]
        )
    return "\n".join(lines) + "\n"


def current_layout_readme_text() -> str:
    """Return the generated navigation note for a current target layout.

    The note is descriptive only.  It is never model, contract, receipt, or
    other authority, and editing it cannot make a stale layout current.
    """

    lines = [
        "# FlowGuard project control plane",
        "",
        "This directory is the current FlowGuard control plane. The folder name",
        "`software_dna`/`DNA` is intentionally not used: completion is a claim",
        "made from separate current evidence, not a directory containing it.",
        "",
        "| Folder | Meaning |",
        "| --- | --- |",
    ]
    for name, role in CANONICAL_ROLE_ROOTS:
        lines.append(f"| `{name}/` | {role.replace('_', ' ')} |")
    lines.extend(
        [
            "",
            "The six role folders are allowed destinations and are created only",
            "when an artifact owns that role; an empty project need not contain",
            "empty role folders. Required artifacts are checked by their native",
            "model/check owner, not by an empty-directory rule.",
            "",
            "`evidence/` is immutable proof and `history/` is provenance only.",
            "Transient work and diagnostic projections belong outside the current",
            "control-plane roots; neither can become model or execution authority",
            "without a direct current rewrite.",
            "",
            "This navigation file is not evidence and is not used to bypass any",
            "layout, model, receipt, consumer, or release gate.",
            "",
        ]
    )
    return "\n".join(lines)


def _sha256_bytes(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _canonical_json_fingerprint(value: Any) -> str:
    return _sha256_bytes(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    )


def _project_identity(root_path: Path) -> str:
    """Return the stable local project identity without reading model authority."""

    manifest_path = root_path / ".flowguard" / "project.toml"
    try:
        payload = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        flowguard_section = payload.get("flowguard")
        if isinstance(flowguard_section, Mapping):
            repository = str(flowguard_section.get("repository", "")).strip()
            if repository:
                return repository
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        pass
    return root_path.name


def _model_authority_metadata(root_path: Path) -> tuple[str, str]:
    """Read only the pointer identity needed by the layout contract.

    The layout gate never validates or consumes the pointed-to model.  It only
    records the current pointer and a fingerprint of the declared section so a
    later authority reader can detect that the layout identity changed.
    """

    manifest_path = root_path / ".flowguard" / "project.toml"
    try:
        raw = manifest_path.read_bytes()
        payload = tomllib.loads(raw.decode("utf-8"))
        section = payload.get("model_authority")
        if not isinstance(section, Mapping):
            return "", ""
        normalized = {str(key): section[key] for key in sorted(section)}
        return ".flowguard/project.toml#model_authority", _canonical_json_fingerprint(normalized)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return "", ""


def _layout_inventory(
    flowguard_root: Path,
    *,
    observation: LayoutObservation | None = None,
    metrics: InvocationMetrics | None = None,
) -> tuple[tuple[dict[str, str], ...], str, dict[str, str]]:
    """Build the current role *shape* inventory without reading member bytes.

    Control-plane files are governed by their own pointers and are not
    recursive role members.  The one guarded path observation is reused by the
    audit and inventory reconciliation, so layout work never hashes every
    evidence/report file merely to prove where it lives.
    """

    if not flowguard_root.is_dir():
        return (), _canonical_json_fingerprint([]), {}
    if observation is None:
        paths, traversal_findings = _walk_layout_entries(flowguard_root, metrics=metrics)
        observation = LayoutObservation(
            root=str(flowguard_root),
            paths=paths,
            traversal_findings=tuple(traversal_findings),
        )
    rows: list[dict[str, str]] = []
    for path in observation.paths:
        rel = path.relative_to(flowguard_root).as_posix()
        parts = Path(rel).parts
        if not parts or parts[0] not in CANONICAL_ROLE_ROOT_NAMES:
            continue
        role = parts[0]
        try:
            redirected = _path_is_reparse_or_symlink(path)
        except OSError:
            redirected = True
        if redirected:
            kind = "reparse"
        else:
            try:
                kind = "directory" if path.is_dir() else "file"
            except OSError:
                kind = "unreadable"
        rows.append({"path": rel, "role": role, "kind": kind})
        if metrics is not None:
            metrics.inc("shape_entries_observed")
    frozen_rows = tuple(sorted(rows, key=lambda row: row["path"]))
    role_fingerprints: dict[str, str] = {}
    for role in sorted(CANONICAL_ROLE_ROOT_NAMES):
        role_rows = [row for row in frozen_rows if row["role"] == role]
        role_fingerprints[role] = _canonical_json_fingerprint(role_rows)
    return frozen_rows, _canonical_json_fingerprint(frozen_rows), role_fingerprints


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _finding(
    code: str,
    *,
    path: str = "",
    message: str,
    recommendation: str,
    metadata: Mapping[str, Any] | None = None,
    severity: str = "blocked",
) -> ProjectLayoutFinding:
    return ProjectLayoutFinding(
        severity=severity,
        code=code,
        path=path,
        message=message,
        recommendation=recommendation,
        metadata=metadata or {},
    )


def _parse_manifest(
    path: Path, *, root_path: Path | None = None
) -> tuple[dict[str, Any] | None, list[ProjectLayoutFinding]]:
    findings: list[ProjectLayoutFinding] = []
    try:
        if (path.exists() or path.is_symlink()) and _path_is_reparse_or_symlink(path):
            return None, [
                _finding(
                    "layout_reparse_or_symlink",
                    path=PROJECT_LAYOUT_MANIFEST,
                    message="The current layout manifest is a symlink, junction, or other reparse point.",
                    recommendation="Replace it with one manually owned regular manifest and rebuild the layout identity.",
                )
            ]
    except OSError as exc:
        return None, [
            _finding(
                "layout_entry_unreadable",
                path=PROJECT_LAYOUT_MANIFEST,
                message=f"The current layout manifest identity cannot be inspected safely: {exc}",
                recommendation="Repair the regular manifest and rerun the audit; do not consult an alternate path.",
            )
        ]
    if not path.is_file():
        return None, [
            _finding(
                "layout_manifest_missing",
                path=PROJECT_LAYOUT_MANIFEST,
                message="The current .flowguard layout manifest is missing.",
                recommendation="Manually reorganize the target into the current role roots and create a new layout.toml; do not reuse an old layout reader.",
            )
        ]
    try:
        raw = path.read_bytes()
        payload = tomllib.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return None, [
            _finding(
                "layout_manifest_invalid",
                path=PROJECT_LAYOUT_MANIFEST,
                message=f"The current layout manifest cannot be parsed: {exc}",
                recommendation="Rewrite the manifest in the current schema and rerun this audit.",
            )
        ]
    if not isinstance(payload, dict):
        findings.append(
            _finding(
                "layout_manifest_invalid",
                path=PROJECT_LAYOUT_MANIFEST,
                message="The layout manifest root must be a TOML table.",
                recommendation="Rewrite the manifest with [flowguard_layout] and [roots] tables.",
            )
        )
        return None, findings
    expected_sections = {"flowguard_layout", "roots", "role_authority", "inventory"}
    if set(payload) != expected_sections:
        findings.append(
            _finding(
                "layout_manifest_unknown_section",
                path=PROJECT_LAYOUT_MANIFEST,
                message=f"Manifest sections must be exactly {sorted(expected_sections)}.",
                recommendation="Remove obsolete sections and manually rebuild the current manifest.",
                metadata={"observed_sections": sorted(payload)},
            )
        )
        return payload, findings
    header = payload.get("flowguard_layout")
    roots = payload.get("roots")
    role_authority = payload.get("role_authority")
    inventory = payload.get("inventory")
    if not all(
        isinstance(value, dict)
        for value in (header, roots, role_authority, inventory)
    ):
        findings.append(
            _finding(
                "layout_manifest_invalid",
                path=PROJECT_LAYOUT_MANIFEST,
                message="flowguard_layout, roots, role_authority, and inventory must be TOML tables.",
                recommendation="Rewrite the manifest with the current v2 table structure.",
            )
        )
        return payload, findings
    expected_header_keys = {
        "schema",
        "version",
        "authority",
        "canonical_root",
        "project_identity",
        "project_identity_fingerprint",
        "model_authority_pointer",
        "model_authority_fingerprint",
        "non_authority_roots",
    }
    if set(header) != expected_header_keys:
        findings.append(
            _finding(
                "layout_manifest_unknown_key",
                path=PROJECT_LAYOUT_MANIFEST,
                message="The flowguard_layout table must contain the complete current identity contract.",
                recommendation="Remove the old keys and manually write the current schema.",
                metadata={"observed_keys": sorted(header)},
            )
        )
    expected_role_authority_keys = set(CANONICAL_ROLE_ROOT_NAMES)
    if set(role_authority) != expected_role_authority_keys:
        findings.append(
            _finding(
                "layout_manifest_role_authority_set_mismatch",
                path=PROJECT_LAYOUT_MANIFEST,
                message="Every current role needs exactly one explicit authority disposition.",
                recommendation="Rewrite role_authority with all nine role names and no aliases.",
                metadata={"expected": sorted(expected_role_authority_keys), "observed": sorted(role_authority)},
            )
        )
    expected_inventory_keys = {"schema", "mode", "fingerprint", "member_count", "role_fingerprints", "members"}
    if set(inventory) != expected_inventory_keys:
        findings.append(
            _finding(
                "layout_manifest_inventory_schema_mismatch",
                path=PROJECT_LAYOUT_MANIFEST,
                message="The inventory table must contain schema, mode, member count, fingerprints, and members.",
                recommendation="Rebuild the current role-member inventory directly from the target tree.",
                metadata={"expected": sorted(expected_inventory_keys), "observed": sorted(inventory)},
            )
        )
    expected_root_keys = {name.replace("-", "_") for name in CANONICAL_ROLE_ROOT_NAMES}
    if set(roots) != expected_root_keys:
        findings.append(
            _finding(
                "layout_manifest_root_set_mismatch",
                path=PROJECT_LAYOUT_MANIFEST,
                message="The manifest must declare every current role root exactly once.",
                recommendation="Manually rebuild the role map; do not infer missing roots from old directories.",
                metadata={"expected": sorted(expected_root_keys), "observed": sorted(roots)},
            )
        )
    declared_paths: dict[str, list[str]] = {}
    for role_key, declared_path in roots.items():
        if isinstance(declared_path, str):
            declared_paths.setdefault(declared_path.casefold(), []).append(role_key)
    duplicate_paths = {
        path: tuple(sorted(role_keys))
        for path, role_keys in sorted(declared_paths.items())
        if len(role_keys) > 1
    }
    if duplicate_paths:
        findings.append(
            _finding(
                "layout_manifest_duplicate_role",
                path=PROJECT_LAYOUT_MANIFEST,
                message="Two or more current roles resolve to the same directory identity.",
                recommendation="Assign every current role one distinct canonical root and rebuild affected identities; do not share or alias roots.",
                metadata={"duplicates": duplicate_paths},
            )
        )
    if header.get("schema") != PROJECT_LAYOUT_SCHEMA:
        findings.append(
            _finding(
                "layout_manifest_schema_stale",
                path=PROJECT_LAYOUT_MANIFEST,
                message=f"Layout schema must be {PROJECT_LAYOUT_SCHEMA}.",
                recommendation="Rewrite the manifest against the current FlowGuard layout schema.",
            )
        )
    if header.get("version") != PROJECT_LAYOUT_VERSION:
        findings.append(
            _finding(
                "layout_manifest_version_stale",
                path=PROJECT_LAYOUT_MANIFEST,
                message=f"Layout version must be {PROJECT_LAYOUT_VERSION}.",
                recommendation="Perform a direct manual layout upgrade and create a new current manifest.",
                metadata={"observed_version": header.get("version")},
            )
        )
    if header.get("authority") != "current" or header.get("canonical_root") != ".flowguard":
        findings.append(
            _finding(
                "layout_manifest_not_current",
                path=PROJECT_LAYOUT_MANIFEST,
                message="The manifest is not marked as the sole current .flowguard layout authority.",
                recommendation="Create one current manifest; do not retain a parallel or fallback layout authority.",
            )
        )
    expected_values = {name.replace("-", "_"): name for name in CANONICAL_ROLE_ROOT_NAMES}
    for key, expected in sorted(expected_values.items()):
        if roots.get(key) != expected:
            findings.append(
                _finding(
                    "layout_manifest_root_identity_mismatch",
                    path=PROJECT_LAYOUT_MANIFEST,
                    message=f"Role {key} must point to .flowguard/{expected}.",
                    recommendation="Repair the root mapping manually and regenerate all affected current identities.",
                    metadata={"role": key, "expected": expected, "observed": roots.get(key)},
                )
            )
    if header.get("authority") != "current" or header.get("canonical_root") != ".flowguard":
        findings.append(
            _finding(
                "layout_manifest_not_current",
                path=PROJECT_LAYOUT_MANIFEST,
                message="The manifest is not marked as the sole current .flowguard layout authority.",
                recommendation="Create one current manifest; do not retain a parallel or fallback layout authority.",
            )
        )
    if root_path is not None:
        expected_identity = _project_identity(root_path)
        if header.get("project_identity") != expected_identity:
            findings.append(
                _finding(
                    "layout_project_identity_mismatch",
                    path=PROJECT_LAYOUT_MANIFEST,
                    message="The layout project identity does not match the current project manifest/root identity.",
                    recommendation="Rewrite the current layout identity and rebuild affected model, test, installation, and receipt identities.",
                    metadata={"expected": expected_identity, "observed": header.get("project_identity")},
                )
            )
        expected_identity_fingerprint = _canonical_json_fingerprint({"project_identity": expected_identity})
        if header.get("project_identity_fingerprint") != expected_identity_fingerprint:
            findings.append(
                _finding(
                    "layout_project_identity_fingerprint_stale",
                    path=PROJECT_LAYOUT_MANIFEST,
                    message="The project identity fingerprint is stale or forged.",
                    recommendation="Rebuild the current layout identity directly from the current project root.",
                )
            )
        expected_pointer, expected_pointer_fingerprint = _model_authority_metadata(root_path)
        if header.get("model_authority_pointer", "") != expected_pointer or header.get("model_authority_fingerprint", "") != expected_pointer_fingerprint:
            findings.append(
                _finding(
                    "layout_model_authority_pointer_stale",
                    path=PROJECT_LAYOUT_MANIFEST,
                    message="The layout model-authority pointer identity no longer matches the current project manifest.",
                    recommendation="Rebuild the current layout and model-authority identities together; do not read the old pointer.",
                    metadata={"expected_pointer": expected_pointer, "observed_pointer": header.get("model_authority_pointer", "")},
                )
            )
    expected_non_authority = sorted(NON_AUTHORITY_ROLES)
    if sorted(header.get("non_authority_roots", [])) != expected_non_authority:
        findings.append(
            _finding(
                "layout_non_authority_declaration_mismatch",
                path=PROJECT_LAYOUT_MANIFEST,
                message="History, work, audits, and projections must be explicitly declared non-authority roots.",
                recommendation="Rewrite the current role authority declarations; do not use these roots as fallback authority.",
            )
        )
    for role in sorted(CANONICAL_ROLE_ROOT_NAMES):
        expected_state = "non_authority" if role in NON_AUTHORITY_ROLES else "current"
        if role_authority.get(role) != expected_state:
            findings.append(
                _finding(
                    "layout_role_authority_mismatch",
                    path=PROJECT_LAYOUT_MANIFEST,
                    message=f"Role {role} must be declared {expected_state}.",
                    recommendation="Rewrite the role authority table and rebuild affected identities.",
                    metadata={"role": role, "expected": expected_state, "observed": role_authority.get(role)},
                )
            )
    if inventory.get("schema") != PROJECT_LAYOUT_INVENTORY_SCHEMA:
        findings.append(
            _finding(
                "layout_inventory_schema_stale",
                path=PROJECT_LAYOUT_MANIFEST,
                message=f"Inventory schema must be {PROJECT_LAYOUT_INVENTORY_SCHEMA}.",
                recommendation="Rebuild the current member inventory directly; no historical inventory reader exists.",
            )
        )
    if inventory.get("mode") not in {"exact", "deferred"}:
        findings.append(
            _finding(
                "layout_inventory_mode_invalid",
                path=PROJECT_LAYOUT_MANIFEST,
                message="Inventory mode must be exact or deferred.",
                recommendation="Rewrite the inventory in the current direct format.",
            )
        )
    return payload, findings


def _component_is_retired(component: str) -> bool:
    return component.casefold() in RETIRED_LAYOUT_COMPONENTS


def _path_is_reparse_or_symlink(path: Path) -> bool:
    """Return whether ``path`` can redirect traversal outside its owned role.

    ``Path.is_symlink()`` is not sufficient on Windows because directory
    junctions are reparse points without necessarily presenting as ordinary
    symbolic links.  ``lstat`` keeps this check read-only and inspects the link
    itself rather than its target.
    """

    if path.is_symlink():
        return True
    attributes = int(getattr(path.lstat(), "st_file_attributes", 0) or 0)
    reparse_mask = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return bool(attributes & reparse_mask)


def _walk_layout_entries(
    flowguard_root: Path,
    *,
    metrics: InvocationMetrics | None = None,
) -> tuple[tuple[Path, ...], list[ProjectLayoutFinding]]:
    """Collect entries deterministically without following redirected roots."""

    if metrics is not None:
        metrics.inc("directory_walk_count")
    entries: list[Path] = []
    findings: list[ProjectLayoutFinding] = []
    pending: list[Path] = [flowguard_root]
    while pending:
        parent = pending.pop()
        if parent != flowguard_root:
            try:
                parent_rel = _relative(parent, flowguard_root)
                parent_role = Path(parent_rel).parts[0] if parent_rel else ""
            except Exception:
                parent_role = ""
            if parent_role in OPAQUE_ROLE_ROOTS:
                # Evidence and history are non-authority payload containers.
                # Do not enumerate their children: adding a receipt, report,
                # quarantine item, or historical directory must not invalidate
                # the lightweight layout shape.  Their own lifecycle/audit
                # owners remain responsible for pointer and payload checks.
                continue
        try:
            children = sorted(
                parent.iterdir(),
                key=lambda child: (child.name.casefold(), child.name),
            )
        except OSError as exc:
            rel = ".flowguard" if parent == flowguard_root else _relative(parent, flowguard_root)
            findings.append(
                _finding(
                    "layout_entry_unreadable",
                    path=rel,
                    message=f"The layout entry cannot be inspected safely: {exc}",
                    recommendation="Repair the current regular path and rerun the audit; do not consult an alternate layout root.",
                )
            )
            continue

        child_directories: list[Path] = []
        for child in children:
            entries.append(child)
            if metrics is not None:
                metrics.inc("entries_observed")
            try:
                redirected = _path_is_reparse_or_symlink(child)
            except OSError as exc:
                findings.append(
                    _finding(
                        "layout_entry_unreadable",
                        path=_relative(child, flowguard_root),
                        message=f"The layout entry identity cannot be inspected safely: {exc}",
                        recommendation="Repair the current regular path and rerun the audit; do not consult an alternate layout root.",
                    )
                )
                continue
            if redirected:
                # The entry itself remains in the denominator and is reported
                # by _inspect_entries, but its target is never traversed.
                continue
            try:
                if child.is_dir():
                    child_directories.append(child)
                elif metrics is not None:
                    metrics.inc("files_observed")
            except OSError as exc:
                findings.append(
                    _finding(
                        "layout_entry_unreadable",
                        path=_relative(child, flowguard_root),
                        message=f"The layout entry type cannot be inspected safely: {exc}",
                        recommendation="Repair the current regular path and rerun the audit; do not consult an alternate layout root.",
                    )
                )
        pending.extend(reversed(child_directories))

    return (
        tuple(sorted(entries, key=lambda path: _relative(path, flowguard_root))),
        findings,
    )


def _inspect_entries(
    flowguard_root: Path,
    *,
    observation: LayoutObservation | None = None,
    metrics: InvocationMetrics | None = None,
) -> tuple[tuple[str, ...], dict[str, int], list[ProjectLayoutFinding]]:
    entries: list[str] = []
    role_counts: dict[str, int] = {}
    findings: list[ProjectLayoutFinding] = []
    try:
        root_exists = flowguard_root.exists() or flowguard_root.is_symlink()
    except OSError as exc:
        return (), {}, [
            _finding(
                "layout_entry_unreadable",
                path=".flowguard",
                message=f"The .flowguard root identity cannot be inspected safely: {exc}",
                recommendation="Repair the current regular directory and rerun the audit; do not consult an alternate root.",
            )
        ]
    if not root_exists:
        return (), {}, [
            _finding(
                "flowguard_directory_missing",
                message="The target has no .flowguard directory.",
                recommendation="Adopt FlowGuard first; this audit never creates a project control plane.",
            )
        ]
    try:
        if _path_is_reparse_or_symlink(flowguard_root):
            return (), {}, [
                _finding(
                    "layout_reparse_or_symlink",
                    path=".flowguard",
                    message="The .flowguard root is a symlink, junction, or other reparse point.",
                    recommendation="Replace it with one manually owned regular directory and rebuild all current layout identities.",
                )
            ]
    except OSError as exc:
        return (), {}, [
            _finding(
                "layout_entry_unreadable",
                path=".flowguard",
                message=f"The .flowguard root identity cannot be inspected safely: {exc}",
                recommendation="Repair the current regular directory and rerun the audit; do not consult an alternate root.",
            )
        ]
    if not flowguard_root.is_dir():
        return (), {}, [
            _finding(
                "flowguard_directory_not_directory",
                path=".flowguard",
                message="The .flowguard control-plane root is not a regular directory.",
                recommendation="Create one manually owned regular .flowguard directory; do not read an alternate path.",
            )
        ]

    # Role roots are semantic destinations, not a mandatory set of empty
    # directories.  A current project may materialize only the roots that own
    # an artifact; the owning model/check gate remains responsible for proving
    # required files.  This keeps adoption and light preflight cheap without
    # weakening path safety for roots that are present.
    for root_name, role in CANONICAL_ROLE_ROOTS:
        role_root = flowguard_root / root_name
        try:
            if role_root.exists() or role_root.is_symlink():
                if not _path_is_reparse_or_symlink(role_root) and not role_root.is_dir():
                    findings.append(
                        _finding(
                            "canonical_role_root_not_directory",
                            path=root_name,
                            message=f"Current role root '{root_name}' is not a regular directory.",
                            recommendation="Replace it with the exact regular role directory and rebuild affected identities.",
                            metadata={"role": role},
                        )
                    )
            # A missing root is valid when no current artifact owns that role.
            # Do not create it here and do not consult an older destination.
        except OSError as exc:
            findings.append(
                _finding(
                    "layout_entry_unreadable",
                    path=root_name,
                    message=f"Required role root '{root_name}' cannot be inspected safely: {exc}",
                    recommendation="Repair the current regular path and rerun the audit; do not consult an alternate root.",
                    metadata={"role": role},
                )
            )

    if observation is None:
        paths, traversal_findings = _walk_layout_entries(flowguard_root, metrics=metrics)
    else:
        paths, traversal_findings = observation.paths, list(observation.traversal_findings)
    findings.extend(traversal_findings)
    for path in paths:
        rel = _relative(path, flowguard_root)
        try:
            redirected = _path_is_reparse_or_symlink(path)
        except OSError:
            # _walk_layout_entries already emitted a blocking unreadable row.
            redirected = False
        try:
            is_directory = False if redirected else path.is_dir()
        except OSError:
            # _walk_layout_entries already emitted a blocking unreadable row.
            is_directory = False
        entries.append(rel + ("/" if is_directory else ""))
        if redirected:
            findings.append(
                _finding(
                    "layout_reparse_or_symlink",
                    path=rel,
                    message="Symlinks, junctions, and other reparse-point entries cannot define current authority.",
                    recommendation="Replace the link with a manually owned regular path and rebuild affected identities.",
                )
            )
        for component in Path(rel).parts:
            if _component_is_retired(component):
                findings.append(
                    _finding(
                        "retired_layout_name",
                        path=rel,
                        message=f"Retired or ambiguous layout component '{component}' is present.",
                        recommendation="Move the material manually to one current role or record an explicit retirement/history disposition; no fallback reader exists.",
                        metadata={"component": component},
                    )
                )
            if component.casefold() in {
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                ".tox",
                ".nox",
                ".hypothesis",
                "cache",
                "caches",
            }:
                findings.append(
                    _finding(
                        "layout_tool_cache",
                        path=rel,
                        message=f"Tool cache or bytecode directory '{component}' cannot be part of the current layout.",
                        recommendation="Remove the generated cache as a proven disposable artifact, then rebuild the current layout identity; do not move it into another authority root.",
                        metadata={"component": component},
                    )
                )
        if Path(rel).suffix.casefold() in BYTECODE_SUFFIXES:
            findings.append(
                _finding(
                    "layout_bytecode_artifact",
                    path=rel,
                    message="Python bytecode cannot be a current FlowGuard layout member.",
                    recommendation="Remove the generated bytecode as a proven disposable artifact and rebuild the current layout identity.",
                )
            )
        if not all(_SAFE_COMPONENT_RE.fullmatch(component) for component in Path(rel).parts):
            findings.append(
                _finding(
                    "layout_path_name_invalid",
                    path=rel,
                    message="A layout path contains a name outside the current portable naming grammar.",
                    recommendation="Rename the path manually and rebuild the affected current manifest/identities.",
                )
            )
        first = Path(rel).parts[0] if Path(rel).parts else ""
        if first in CANONICAL_ROLE_ROOT_NAMES:
            role = dict(CANONICAL_ROLE_ROOTS)[first]
            role_counts[role] = role_counts.get(role, 0) + 1
            name_lower = Path(rel).name.casefold()
            if first == "evidence" and len(Path(rel).parts) == 2 and (
                name_lower in {"model.py", "model.toml", "model-authority.json", "model-system.json"}
            ):
                findings.append(
                    _finding(
                        "layout_role_authority_mismatch",
                        path=rel,
                        message="A model/authority-looking artifact is under the evidence role.",
                        recommendation="Place current model authority under models and keep evidence as immutable proof only; rebuild affected identities.",
                        metadata={"role": first},
                    )
                )
            if first == "models" and len(Path(rel).parts) == 2 and (
                name_lower.startswith("receipt") or name_lower.endswith("-evidence.json")
            ):
                findings.append(
                    _finding(
                        "layout_role_authority_mismatch",
                        path=rel,
                        message="A receipt/evidence-looking artifact is under the models role.",
                        recommendation="Place immutable proof under evidence and rebuild affected identities; do not let it become model authority.",
                        metadata={"role": first},
                    )
                )
            if first == "structure" and len(Path(rel).parts) >= 3 and Path(rel).parts[1] == "owners":
                owner = Path(rel).parts[2]
                if not _OWNER_ID_RE.fullmatch(owner):
                    findings.append(
                        _finding(
                            "owner_path_invalid",
                            path=rel,
                            message="Owner directories under structure/owners must use a stable lowercase owner id.",
                            recommendation="Rename the owner path manually and rebind its contracts/tests/evidence.",
                        )
                    )
        elif rel in CANONICAL_FILES:
            role_counts[CANONICAL_FILES[rel]] = role_counts.get(CANONICAL_FILES[rel], 0) + 1
        else:
            # Every direct child must be a declared role root or canonical file.
            # Nested content is allowed only below a declared role root.
            if len(Path(rel).parts) == 1:
                findings.append(
                    _finding(
                        "unregistered_layout_entry",
                        path=rel,
                        message="This top-level .flowguard entry has no declared current role.",
                        recommendation="Place it under one current role root or give it an explicit historical/retired disposition before continuing.",
                    )
                )
    # Detect direct files under .flowguard that are old owner/model/check material.
    for path in (entry for entry in paths if entry.parent == flowguard_root):
        if path.name in CANONICAL_FILES or path.name in CANONICAL_ROLE_ROOT_NAMES:
            continue
        try:
            if _path_is_reparse_or_symlink(path):
                continue
            is_file = path.is_file()
        except OSError:
            # A blocking unreadable row was already emitted above.
            continue
        if is_file:
            findings.append(
                _finding(
                    "legacy_flat_artifact",
                    path=path.name,
                    message="A direct .flowguard file is not one of the three current control-plane records.",
                    recommendation="Assign it to behavior/models/structure/verification/evidence/history manually (audits and projections belong under their owning evidence/structure path, transient work stays outside .flowguard); do not keep a flat compatibility path.",
                )
            )
    return tuple(entries), role_counts, findings


def _inventory_findings(
    *,
    root_path: Path,
    flowguard_root: Path,
    manifest: Mapping[str, Any] | None,
    observation: LayoutObservation | None = None,
    metrics: InvocationMetrics | None = None,
) -> tuple[str, list[ProjectLayoutFinding]]:
    """Reconcile the declared shape rows with the current tree."""

    if not isinstance(manifest, Mapping):
        return "", []
    inventory = manifest.get("inventory")
    if not isinstance(inventory, Mapping):
        return "", []
    actual_members, actual_fingerprint, actual_role_fingerprints = _layout_inventory(
        flowguard_root, observation=observation, metrics=metrics
    )
    findings: list[ProjectLayoutFinding] = []
    raw_members = inventory.get("members")
    members: list[dict[str, str]] = []
    if isinstance(raw_members, list):
        for index, member in enumerate(raw_members):
            if not isinstance(member, Mapping):
                findings.append(
                    _finding(
                        "layout_inventory_member_invalid",
                        path=PROJECT_LAYOUT_MANIFEST,
                        message=f"Inventory member {index} is not a table.",
                        recommendation="Rebuild the exact current role-member inventory directly from disk.",
                    )
                )
                continue
            if set(member) != {"path", "role", "kind"}:
                findings.append(
                    _finding(
                        "layout_inventory_member_schema_mismatch",
                        path=PROJECT_LAYOUT_MANIFEST,
                        message=f"Inventory member {index} has obsolete or missing keys.",
                        recommendation="Rebuild the shape inventory using path, role, and kind only.",
                        metadata={"observed_keys": sorted(member)},
                    )
                )
                continue
            members.append(
                {
                    "path": str(member.get("path", "")),
                    "role": str(member.get("role", "")),
                    "kind": str(member.get("kind", "")),
                }
            )
    else:
        findings.append(
            _finding(
                "layout_inventory_members_missing",
                path=PROJECT_LAYOUT_MANIFEST,
                message="The current inventory has no members array.",
                recommendation="Rebuild the current manifest with an exact role-member inventory.",
            )
        )
    declared_members = tuple(sorted(members, key=lambda row: row["path"]))
    actual_members = tuple(sorted(actual_members, key=lambda row: row["path"]))
    declared_by_case: dict[str, list[str]] = {}
    for row in declared_members:
        declared_by_case.setdefault(row["path"].casefold(), []).append(row["path"])
    path_collisions = {
        key: tuple(sorted(values))
        for key, values in declared_by_case.items()
        if len(values) > 1
    }
    if path_collisions:
        findings.append(
            _finding(
                "layout_inventory_path_collision",
                path=PROJECT_LAYOUT_MANIFEST,
                message="The inventory declares multiple current members for one path identity.",
                recommendation="Keep one canonical path per current role and rebuild all affected identities.",
                metadata={"collisions": path_collisions},
            )
        )
    role_by_path = {row["path"]: row["role"] for row in declared_members}
    for row in declared_members:
        first = Path(row["path"]).parts[0] if Path(row["path"]).parts else ""
        if first != row["role"]:
            findings.append(
                _finding(
                    "layout_inventory_role_mismatch",
                    path=row["path"],
                    message="An inventory member is assigned to a role different from its canonical root.",
                    recommendation="Rewrite the member row with the exact current role root; do not alias it.",
                    metadata={"expected_role": first, "observed_role": row["role"]},
                )
            )
    if inventory.get("mode") == "deferred":
        non_root_members = [
            row for row in actual_members if len(Path(row["path"]).parts) > 1
        ]
        if non_root_members:
            findings.append(
                _finding(
                    "layout_inventory_deferred_with_members",
                    path=PROJECT_LAYOUT_MANIFEST,
                    message="A deferred scaffold inventory cannot govern a populated current project.",
                    recommendation="Directly regenerate the exact member inventory before reading model, test, or evidence authority.",
                    metadata={"extra_member_count": len(non_root_members)},
                )
            )
    elif inventory.get("mode") == "exact":
        if declared_members != actual_members:
            declared_paths = {row["path"] for row in declared_members}
            actual_paths = {row["path"] for row in actual_members}
            findings.append(
                _finding(
                    "layout_inventory_conservation_mismatch",
                    path=PROJECT_LAYOUT_MANIFEST,
                    message="The current shape inventory does not equal the observed role-member set.",
                    recommendation="Rebuild the current layout manifest directly from the current tree; old receipts become stale.",
                    metadata={
                        "missing_members": sorted(actual_paths - declared_paths),
                        "extra_members": sorted(declared_paths - actual_paths),
                    },
                )
            )
        if inventory.get("fingerprint") != actual_fingerprint:
            findings.append(
                _finding(
                    "layout_inventory_fingerprint_stale",
                    path=PROJECT_LAYOUT_MANIFEST,
                    message="The declared role-member inventory fingerprint is stale.",
                    recommendation="Regenerate the current inventory and rebuild affected identities.",
                    metadata={"expected": actual_fingerprint, "observed": inventory.get("fingerprint")},
                )
            )
        if inventory.get("member_count") != len(actual_members):
            findings.append(
                _finding(
                    "layout_inventory_count_mismatch",
                    path=PROJECT_LAYOUT_MANIFEST,
                    message="The declared inventory member count is stale.",
                    recommendation="Regenerate the current inventory before continuing.",
                    metadata={"expected": len(actual_members), "observed": inventory.get("member_count")},
                )
            )
        declared_roles = inventory.get("role_fingerprints")
        if not isinstance(declared_roles, Mapping) or {
            str(key): str(value) for key, value in declared_roles.items()
        } != actual_role_fingerprints:
            findings.append(
                _finding(
                    "layout_role_fingerprint_stale",
                    path=PROJECT_LAYOUT_MANIFEST,
                    message="One or more current role fingerprints are stale.",
                    recommendation="Regenerate the direct current role inventory and rebuild affected model/test/receipt identities.",
                    metadata={"expected": actual_role_fingerprints, "observed": dict(declared_roles or {})},
                )
            )
    return actual_fingerprint, findings


def audit_project_layout(
    root: str | Path = ".",
    *,
    metrics: InvocationMetrics | None = None,
) -> ProjectLayoutReport:
    """Audit one target project's current ``.flowguard`` layout read-only."""

    metrics = metrics or InvocationMetrics()
    root_path = Path(root).resolve()
    flowguard_root = root_path / ".flowguard"
    manifest_path = flowguard_root / "layout.toml"
    with metrics.phase("layout_manifest_parse"):
        _manifest, manifest_findings = _parse_manifest(manifest_path, root_path=root_path)
    manifest_fingerprint = ""
    if _manifest is not None:
        try:
            manifest_bytes = manifest_path.read_bytes()
            metrics.inc("content_hash_read_count")
            metrics.inc("content_bytes_hashed", len(manifest_bytes))
            manifest_fingerprint = _sha256_bytes(manifest_bytes)
        except OSError:
            manifest_fingerprint = ""
    observation = LayoutObservation(root=str(flowguard_root))
    try:
        if flowguard_root.is_dir() and not _path_is_reparse_or_symlink(flowguard_root):
            paths, traversal_findings = _walk_layout_entries(
                flowguard_root, metrics=metrics
            )
            observation = LayoutObservation(
                root=str(flowguard_root),
                paths=paths,
                traversal_findings=tuple(traversal_findings),
            )
    except OSError:
        # _inspect_entries emits the authoritative unreadable/reparse finding.
        observation = LayoutObservation(root=str(flowguard_root))
    with metrics.phase("layout_shape_inspection"):
        entries, role_counts, entry_findings = _inspect_entries(
            flowguard_root, observation=observation, metrics=metrics
        )
    with metrics.phase("layout_shape_reconciliation"):
        inventory_fingerprint, inventory_findings = _inventory_findings(
            root_path=root_path,
            flowguard_root=flowguard_root,
            manifest=_manifest,
            observation=observation,
            metrics=metrics,
        )
    findings = tuple(
        sorted(
            (*manifest_findings, *entry_findings, *inventory_findings),
            key=lambda finding: (finding.severity, finding.code, finding.path),
        )
    )
    status = "blocked" if any(finding.severity == "blocked" for finding in findings) else "pass"
    layout_version: int | None = None
    if _manifest and isinstance(_manifest.get("flowguard_layout"), Mapping):
        value = _manifest["flowguard_layout"].get("version")
        if isinstance(value, int) and not isinstance(value, bool):
            layout_version = value
    return ProjectLayoutReport(
        root=str(root_path),
        flowguard_root=str(flowguard_root),
        status=status,
        layout_version=layout_version,
        manifest_fingerprint=manifest_fingerprint,
        project_identity=_project_identity(root_path),
        inventory_fingerprint=inventory_fingerprint,
        observed_entries=entries,
        role_counts=role_counts,
        findings=findings,
        metrics=metrics.snapshot(),
    )


__all__ = [
    "CANONICAL_FILES",
    "CANONICAL_ROLE_ROOTS",
    "PROJECT_LAYOUT_CLAIM_BOUNDARY",
    "PROJECT_LAYOUT_MANIFEST",
    "PROJECT_LAYOUT_SCHEMA",
    "PROJECT_LAYOUT_VERSION",
    "LayoutObservation",
    "ProjectLayoutFinding",
    "ProjectLayoutReport",
    "audit_project_layout",
    "current_layout_manifest_text",
    "current_layout_readme_text",
]
