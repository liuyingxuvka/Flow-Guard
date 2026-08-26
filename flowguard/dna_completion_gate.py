"""Fail-closed whole-target DNA completion assessment.

The provider-neutral blueprint qualifier answers a deliberately narrow
question: are the static model, semantic, code-binding, test-binding, and
native execution layers current?  A product-level DNA claim has a larger
boundary.  This module owns that outer claim without executing a target or
creating a second model authority.  Native owners submit one typed row for
each required layer; this gate checks identity, terminal evidence, and the
explicit status of every row.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .portable_model import canonical_identity, canonical_json_bytes
from .proof_artifact import (
    ProofArtifactRef,
    coerce_proof_artifact_ref,
    is_sha256_fingerprint,
    proof_artifact_gap_codes,
    sha256_fingerprint,
)


DNA_COMPLETION_SCHEMA = "flowguard.dna_completion_gate.v1"
DNA_NATIVE_OWNER_INPUT_SCHEMA = "flowguard.dna_completion_native_owner_input.v1"

DNA_LAYER_STATIC_BLUEPRINT = "static_blueprint_complete"
DNA_LAYER_SEMANTIC_MODEL = "semantic_model_complete"
DNA_LAYER_INTENT_INVENTORY = "intent_inventory_complete"
DNA_LAYER_OBSERVED_IMPLEMENTATION_SURFACE = "observed_implementation_surface_complete"
DNA_LAYER_BIDIRECTIONAL_TRACEABILITY = "bidirectional_traceability_complete"
DNA_LAYER_BEHAVIOR_BINDING = "behavior_binding_complete"
DNA_LAYER_CODE_BINDING = "code_binding_complete"
DNA_LAYER_STATIC_TEST_BINDING = "static_test_binding_complete"
DNA_LAYER_RUNTIME_TEST_EXECUTION = "runtime_test_execution_complete"
DNA_LAYER_CONTRACT_UNIVERSE = "contract_universe_complete"
DNA_LAYER_REAL_UI_SURFACE = "real_ui_surface_complete"
DNA_LAYER_EXTERNAL_CONSUMER = "external_consumer_complete"
DNA_LAYER_FAULT_MATRIX = "fault_matrix_complete"
DNA_LAYER_PLATFORM_PROVIDER = "platform_provider_complete"
DNA_LAYER_INSTALLATION = "installation_complete"
DNA_LAYER_OBSERVED_MISS_BACKFEED = "observed_miss_backfeed_complete"
DNA_LAYER_RELEASE_IDENTITY = "release_identity_complete"

DNA_COMPLETION_LAYER_IDS = (
    DNA_LAYER_STATIC_BLUEPRINT,
    DNA_LAYER_SEMANTIC_MODEL,
    DNA_LAYER_INTENT_INVENTORY,
    DNA_LAYER_OBSERVED_IMPLEMENTATION_SURFACE,
    DNA_LAYER_BIDIRECTIONAL_TRACEABILITY,
    DNA_LAYER_BEHAVIOR_BINDING,
    DNA_LAYER_CODE_BINDING,
    DNA_LAYER_STATIC_TEST_BINDING,
    DNA_LAYER_RUNTIME_TEST_EXECUTION,
    DNA_LAYER_CONTRACT_UNIVERSE,
    DNA_LAYER_REAL_UI_SURFACE,
    DNA_LAYER_EXTERNAL_CONSUMER,
    DNA_LAYER_FAULT_MATRIX,
    DNA_LAYER_PLATFORM_PROVIDER,
    DNA_LAYER_INSTALLATION,
    DNA_LAYER_OBSERVED_MISS_BACKFEED,
    DNA_LAYER_RELEASE_IDENTITY,
)

DNA_COMPLETION_STATUSES = (
    "passed",
    "failed",
    "skipped",
    "not_run",
    "stale",
    "missing",
    "blocked",
    "not_applicable",
    "self_reported_only",
    "unverified",
)
DNA_COMPLETION_CLAIM_SCOPES = ("broad", "scoped")
DNA_COMPLETION_TERMINAL_SUCCESS = "passed"
DNA_COMPLETION_SELF_REPORTED_KINDS = {
    "self_reported",
    "caller_declared",
    "boolean_only",
    "progress_only",
}

# These layers are intentionally named, but their owners remain target-owned.
# The core gate must not install a product-specific owner map or a fallback
# executor for them.
DNA_EXTERNAL_OWNER_LAYER_IDS = frozenset(
    {
        DNA_LAYER_REAL_UI_SURFACE,
        DNA_LAYER_EXTERNAL_CONSUMER,
        DNA_LAYER_FAULT_MATRIX,
        DNA_LAYER_PLATFORM_PROVIDER,
        DNA_LAYER_INSTALLATION,
        DNA_LAYER_OBSERVED_MISS_BACKFEED,
        DNA_LAYER_RELEASE_IDENTITY,
    }
)


class DnaCompletionError(ValueError):
    """Raised when a current DNA completion artifact is malformed."""


def _text(value: Any, *, context: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        qualifier = "a string" if allow_empty else "a non-empty string"
        raise DnaCompletionError(f"{context} must be {qualifier}")
    return value


def _strings(
    value: Any,
    *,
    context: str,
    allow_duplicates: bool = False,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise DnaCompletionError(f"{context} must be an array")
    result = tuple(
        _text(item, context=f"{context}[]", allow_empty=allow_empty)
        for item in value
    )
    if not allow_duplicates and len(result) != len(set(result)):
        raise DnaCompletionError(f"{context} contains duplicate values")
    return result


def _map(value: Mapping[str, Any] | None, *, context: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise DnaCompletionError(f"{context} must be an object")
    return {
        _text(key, context=f"{context} key"): _text(
            item, context=f"{context}[{key!r}]"
        )
        for key, item in value.items()
    }


_PRODUCER_IDENTITY_FIELDS = (
    "owner_id",
    "evidence_id",
    "receipt_id",
    "receipt_fingerprint",
    "source_fingerprint",
    "model_fingerprint",
    "toolchain_fingerprint",
    "environment_fingerprint",
    "result_fingerprint",
)


def _producer_identity_map(
    value: Mapping[str, Any] | None,
    *,
    context: str,
) -> dict[str, dict[str, str]]:
    """Normalize the frozen producer identity outside each evidence row.

    The assessment is the frozen plan; a proof artifact is only an observed
    result.  Keeping the expected receipt/source/result identities in the
    assessment prevents a caller from copying values out of a self-authored
    artifact and using those same values as its own expectation.
    """

    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise DnaCompletionError(f"{context} must be an object")
    result: dict[str, dict[str, str]] = {}
    for layer_id, raw in value.items():
        layer_key = _text(layer_id, context=f"{context} key")
        if not isinstance(raw, Mapping):
            raise DnaCompletionError(f"{context}[{layer_key!r}] must be an object")
        unknown = set(raw) - set(_PRODUCER_IDENTITY_FIELDS)
        if unknown:
            raise DnaCompletionError(
                f"{context}[{layer_key!r}] has unknown fields: {sorted(unknown)}"
            )
        result[layer_key] = {
            field: _text(raw[field], context=f"{context}[{layer_key!r}].{field}")
            for field in _PRODUCER_IDENTITY_FIELDS
            if field in raw
        }
    return result


def _strict_object(value: Any, *, context: str, required: Sequence[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DnaCompletionError(f"{context} must be an object")
    if set(value) != set(required):
        difference = sorted(set(value) ^ set(required))
        raise DnaCompletionError(
            f"{context} fields differ from the current schema: {difference}"
        )
    return value


@dataclass(frozen=True)
class DnaCompletionLayerEvidence:
    """One native owner's terminal disposition for one DNA layer."""

    layer_id: str
    owner_id: str
    status: str
    input_fingerprint: str
    evidence_kind: str
    evidence_id: str = ""
    evidence_fingerprint: str = ""
    claim_boundary: str = ""
    gap_reason: str = ""
    not_applicable_reason: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        layer_id = _text(self.layer_id, context="dna layer.layer_id")
        if layer_id not in DNA_COMPLETION_LAYER_IDS:
            raise DnaCompletionError(f"unknown DNA completion layer: {layer_id}")
        object.__setattr__(self, "layer_id", layer_id)
        for name in ("owner_id", "input_fingerprint", "evidence_kind", "claim_boundary"):
            object.__setattr__(
                self,
                name,
                _text(getattr(self, name), context=f"dna layer.{name}"),
            )
        status = _text(self.status, context="dna layer.status")
        if status not in DNA_COMPLETION_STATUSES:
            raise DnaCompletionError(f"unknown DNA completion status: {status}")
        for name in (
            "evidence_id",
            "evidence_fingerprint",
            "gap_reason",
            "not_applicable_reason",
        ):
            object.__setattr__(
                self,
                name,
                _text(getattr(self, name), context=f"dna layer.{name}", allow_empty=True),
            )
        if self.evidence_kind in DNA_COMPLETION_SELF_REPORTED_KINDS:
            # Keep the row materializable so review can return a typed blocker
            # rather than crashing an audit run.  Normalize before applying
            # the terminal/non-terminal field requirements below.
            status = "self_reported_only"
            if not self.gap_reason:
                object.__setattr__(
                    self,
                    "gap_reason",
                    "evidence kind is caller-authored and cannot authorize completion",
                )
        object.__setattr__(self, "status", status)
        if status == DNA_COMPLETION_TERMINAL_SUCCESS:
            if self.gap_reason or self.not_applicable_reason:
                raise DnaCompletionError(
                    f"passed DNA layer cannot carry a gap or not-applicable reason: {layer_id}"
                )
            if not self.evidence_id:
                raise DnaCompletionError(
                    f"passed DNA layer {layer_id} requires terminal evidence id"
                )
            if not self.evidence_fingerprint.startswith("sha256:"):
                raise DnaCompletionError(
                    f"passed DNA layer {layer_id} requires sha256 evidence fingerprint"
                )
        elif status == "not_applicable":
            if not self.not_applicable_reason:
                raise DnaCompletionError(
                    f"not_applicable DNA layer {layer_id} requires a reason"
                )
        elif not self.gap_reason:
            raise DnaCompletionError(
                f"non-passing DNA layer {layer_id} requires a visible gap reason"
            )
        if not isinstance(self.metadata, Mapping):
            raise DnaCompletionError("dna layer.metadata must be an object")
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def fingerprint(self) -> str:
        return canonical_identity(self._identity_payload())

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": DNA_COMPLETION_SCHEMA,
            "layer_id": self.layer_id,
            "owner_id": self.owner_id,
            "status": self.status,
            "input_fingerprint": self.input_fingerprint,
            "evidence_kind": self.evidence_kind,
            "evidence_id": self.evidence_id,
            "evidence_fingerprint": self.evidence_fingerprint,
            "claim_boundary": self.claim_boundary,
            "gap_reason": self.gap_reason,
            "not_applicable_reason": self.not_applicable_reason,
            "metadata": dict(self.metadata),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Any) -> "DnaCompletionLayerEvidence":
        fields = (
            "schema_version",
            "layer_id",
            "owner_id",
            "status",
            "input_fingerprint",
            "evidence_kind",
            "evidence_id",
            "evidence_fingerprint",
            "claim_boundary",
            "gap_reason",
            "not_applicable_reason",
            "metadata",
            "fingerprint",
        )
        data = _strict_object(value, context="dna completion layer", required=fields)
        if data["schema_version"] != DNA_COMPLETION_SCHEMA:
            raise DnaCompletionError("DNA completion layer schema is not current")
        layer = cls(
            layer_id=data["layer_id"],
            owner_id=data["owner_id"],
            status=data["status"],
            input_fingerprint=data["input_fingerprint"],
            evidence_kind=data["evidence_kind"],
            evidence_id=data["evidence_id"],
            evidence_fingerprint=data["evidence_fingerprint"],
            claim_boundary=data["claim_boundary"],
            gap_reason=data["gap_reason"],
            not_applicable_reason=data["not_applicable_reason"],
            metadata=data["metadata"],
        )
        if data["fingerprint"] != layer.fingerprint:
            raise DnaCompletionError("DNA completion layer fingerprint mismatch")
        return layer


@dataclass(frozen=True)
class DnaCompletionNativeOwnerInput:
    """Current native-owner input before it is normalized into a layer row.

    The outer assessment is intentionally provider-neutral.  A native owner
    supplies the frozen assessment subject revision and its layer-specific
    input identity; it may report a terminal receipt or a visible non-pass
    disposition.  This type does not execute an owner or turn a caller
    boolean into evidence.
    """

    layer_id: str
    owner_id: str
    subject_revision: str
    status: str
    input_fingerprint: str
    evidence_kind: str
    evidence_id: str = ""
    evidence_fingerprint: str = ""
    claim_boundary: str = ""
    gap_reason: str = ""
    not_applicable_reason: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        subject_revision = _text(
            self.subject_revision,
            context="native owner input.subject_revision",
        )
        object.__setattr__(self, "subject_revision", subject_revision)
        if not isinstance(self.metadata, Mapping):
            raise DnaCompletionError("native owner input.metadata must be an object")
        metadata = dict(self.metadata)
        declared_subject = metadata.get("subject_revision")
        if declared_subject is not None and declared_subject != subject_revision:
            raise DnaCompletionError(
                "native owner input metadata subject_revision differs from the input"
            )
        metadata["subject_revision"] = subject_revision
        object.__setattr__(self, "metadata", metadata)

        # Reuse the normalized layer contract so this ingress cannot carry a
        # status or evidence shape that the outer gate would later reinterpret.
        row = DnaCompletionLayerEvidence(
            layer_id=self.layer_id,
            owner_id=self.owner_id,
            status=self.status,
            input_fingerprint=self.input_fingerprint,
            evidence_kind=self.evidence_kind,
            evidence_id=self.evidence_id,
            evidence_fingerprint=self.evidence_fingerprint,
            claim_boundary=self.claim_boundary,
            gap_reason=self.gap_reason,
            not_applicable_reason=self.not_applicable_reason,
            metadata=metadata,
        )
        for name in (
            "layer_id",
            "owner_id",
            "status",
            "input_fingerprint",
            "evidence_kind",
            "evidence_id",
            "evidence_fingerprint",
            "claim_boundary",
            "gap_reason",
            "not_applicable_reason",
        ):
            object.__setattr__(self, name, getattr(row, name))

    @property
    def fingerprint(self) -> str:
        return canonical_identity(self.to_dict(include_fingerprint=False))

    def to_layer_evidence(self) -> DnaCompletionLayerEvidence:
        return DnaCompletionLayerEvidence(
            layer_id=self.layer_id,
            owner_id=self.owner_id,
            status=self.status,
            input_fingerprint=self.input_fingerprint,
            evidence_kind=self.evidence_kind,
            evidence_id=self.evidence_id,
            evidence_fingerprint=self.evidence_fingerprint,
            claim_boundary=self.claim_boundary,
            gap_reason=self.gap_reason,
            not_applicable_reason=self.not_applicable_reason,
            metadata=self.metadata,
        )

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": DNA_NATIVE_OWNER_INPUT_SCHEMA,
            "layer_id": self.layer_id,
            "owner_id": self.owner_id,
            "subject_revision": self.subject_revision,
            "status": self.status,
            "input_fingerprint": self.input_fingerprint,
            "evidence_kind": self.evidence_kind,
            "evidence_id": self.evidence_id,
            "evidence_fingerprint": self.evidence_fingerprint,
            "claim_boundary": self.claim_boundary,
            "gap_reason": self.gap_reason,
            "not_applicable_reason": self.not_applicable_reason,
            "metadata": dict(self.metadata),
        }
        if include_fingerprint:
            payload["fingerprint"] = self.fingerprint
        return payload

    @classmethod
    def from_dict(cls, value: Any) -> "DnaCompletionNativeOwnerInput":
        fields = (
            "schema_version",
            "layer_id",
            "owner_id",
            "subject_revision",
            "status",
            "input_fingerprint",
            "evidence_kind",
            "evidence_id",
            "evidence_fingerprint",
            "claim_boundary",
            "gap_reason",
            "not_applicable_reason",
            "metadata",
            "fingerprint",
        )
        data = _strict_object(value, context="native owner input", required=fields)
        if data["schema_version"] != DNA_NATIVE_OWNER_INPUT_SCHEMA:
            raise DnaCompletionError("native owner input schema is not current")
        item = cls(
            layer_id=data["layer_id"],
            owner_id=data["owner_id"],
            subject_revision=data["subject_revision"],
            status=data["status"],
            input_fingerprint=data["input_fingerprint"],
            evidence_kind=data["evidence_kind"],
            evidence_id=data["evidence_id"],
            evidence_fingerprint=data["evidence_fingerprint"],
            claim_boundary=data["claim_boundary"],
            gap_reason=data["gap_reason"],
            not_applicable_reason=data["not_applicable_reason"],
            metadata=data["metadata"],
        )
        if data["fingerprint"] != item.fingerprint:
            raise DnaCompletionError("native owner input fingerprint mismatch")
        return item


@dataclass(frozen=True)
class DnaCompletionFinding:
    code: str
    message: str
    layer_id: str = ""
    severity: str = "blocker"

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _text(self.code, context="DNA finding.code"))
        object.__setattr__(self, "message", _text(self.message, context="DNA finding.message"))
        object.__setattr__(self, "layer_id", _text(self.layer_id, context="DNA finding.layer_id", allow_empty=True))
        if self.severity not in {"info", "warning", "blocker"}:
            raise DnaCompletionError(f"unknown DNA finding severity: {self.severity}")

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "layer_id": self.layer_id,
            "severity": self.severity,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "DnaCompletionFinding":
        fields = ("code", "message", "layer_id", "severity")
        data = _strict_object(value, context="DNA completion finding", required=fields)
        return cls(**{name: data[name] for name in fields})


@dataclass(frozen=True)
class DnaCompletionAssessment:
    """Frozen layer plan plus native evidence rows for one broad claim."""

    assessment_id: str
    target_system_id: str
    subject_revision: str
    claim_scope: str
    required_layer_ids: tuple[str, ...]
    layers: tuple[DnaCompletionLayerEvidence, ...]
    expected_input_fingerprints: Mapping[str, str]
    claim_boundary: str
    expected_producer_identities: Mapping[str, Mapping[str, str]] = field(default_factory=dict)

    @classmethod
    def from_native_owner_inputs(
        cls,
        *,
        assessment_id: str,
        target_system_id: str,
        subject_revision: str,
        claim_scope: str,
        required_layer_ids: Sequence[str],
        native_owner_inputs: Sequence[DnaCompletionNativeOwnerInput],
        expected_input_fingerprints: Mapping[str, str],
        claim_boundary: str,
        expected_producer_identities: Mapping[str, Mapping[str, str]] | None = None,
    ) -> "DnaCompletionAssessment":
        """Build an assessment from target-owned, typed native inputs.

        The factory is deliberately pure: it only normalizes owner inputs into
        rows.  Missing external evidence stays a visible non-pass row and is
        not replaced with a synthetic success or an implicit owner.
        """

        inputs = tuple(native_owner_inputs)
        if any(not isinstance(item, DnaCompletionNativeOwnerInput) for item in inputs):
            raise DnaCompletionError(
                "DNA assessment native_owner_inputs require typed native-owner inputs"
            )
        mismatched_subjects = tuple(
            item.layer_id
            for item in inputs
            if item.subject_revision != subject_revision
        )
        if mismatched_subjects:
            raise DnaCompletionError(
                "native owner input subject_revision differs from the assessment: "
                + ", ".join(mismatched_subjects)
            )
        return cls(
            assessment_id=assessment_id,
            target_system_id=target_system_id,
            subject_revision=subject_revision,
            claim_scope=claim_scope,
            required_layer_ids=tuple(required_layer_ids),
            layers=tuple(item.to_layer_evidence() for item in inputs),
            expected_input_fingerprints=expected_input_fingerprints,
            claim_boundary=claim_boundary,
            expected_producer_identities=expected_producer_identities or {},
        )

    def __post_init__(self) -> None:
        for name in (
            "assessment_id",
            "target_system_id",
            "subject_revision",
            "claim_boundary",
        ):
            object.__setattr__(
                self,
                name,
                _text(getattr(self, name), context=f"DNA assessment.{name}"),
            )
        if self.claim_scope not in DNA_COMPLETION_CLAIM_SCOPES:
            raise DnaCompletionError(f"unknown DNA completion claim scope: {self.claim_scope}")
        object.__setattr__(self, "required_layer_ids", _strings(self.required_layer_ids, context="DNA assessment.required_layer_ids"))
        if not self.required_layer_ids:
            raise DnaCompletionError("DNA assessment requires at least one required layer")
        unknown_required = set(self.required_layer_ids) - set(DNA_COMPLETION_LAYER_IDS)
        if unknown_required:
            raise DnaCompletionError(f"DNA assessment names unknown required layers: {sorted(unknown_required)}")
        layers = tuple(self.layers)
        if any(not isinstance(layer, DnaCompletionLayerEvidence) for layer in layers):
            raise DnaCompletionError("DNA assessment layers require typed evidence rows")
        object.__setattr__(self, "layers", tuple(sorted(layers, key=lambda row: row.layer_id)))
        object.__setattr__(self, "expected_input_fingerprints", _map(self.expected_input_fingerprints, context="DNA assessment.expected_input_fingerprints"))
        if not set(self.expected_input_fingerprints).issubset(set(self.required_layer_ids)):
            raise DnaCompletionError("expected DNA input fingerprints must target required layers")
        object.__setattr__(
            self,
            "expected_producer_identities",
            _producer_identity_map(
                self.expected_producer_identities,
                context="DNA assessment.expected_producer_identities",
            ),
        )
        if not set(self.expected_producer_identities).issubset(set(self.required_layer_ids)):
            raise DnaCompletionError(
                "expected DNA producer identities must target required layers"
            )

    @property
    def fingerprint(self) -> str:
        return canonical_identity(self._identity_payload())

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": DNA_COMPLETION_SCHEMA,
            "assessment_id": self.assessment_id,
            "target_system_id": self.target_system_id,
            "subject_revision": self.subject_revision,
            "claim_scope": self.claim_scope,
            "required_layer_ids": list(self.required_layer_ids),
            "layers": [layer.to_dict() for layer in self.layers],
            "expected_input_fingerprints": dict(self.expected_input_fingerprints),
            "expected_producer_identities": {
                layer_id: dict(identity)
                for layer_id, identity in sorted(self.expected_producer_identities.items())
            },
            "claim_boundary": self.claim_boundary,
        }

    @property
    def report(self) -> "DnaCompletionReport":
        return review_dna_completion(self)

    @property
    def status(self) -> str:
        report = self.report
        if report.dna_complete:
            return "dna_complete"
        if report.ok:
            return "scoped_complete"
        return "blocked"

    @property
    def dna_complete(self) -> bool:
        return self.report.dna_complete

    def to_dict(self) -> dict[str, Any]:
        report = self.report
        return {
            **self._identity_payload(),
            "status": self.status,
            "dna_complete": self.dna_complete,
            "findings": [finding.to_dict() for finding in report.findings],
            "missing_layer_ids": list(report.missing_layer_ids),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "DnaCompletionAssessment":
        fields = (
            "schema_version",
            "assessment_id",
            "target_system_id",
            "subject_revision",
            "claim_scope",
            "required_layer_ids",
            "layers",
            "expected_input_fingerprints",
            "expected_producer_identities",
            "claim_boundary",
            "status",
            "dna_complete",
            "findings",
            "missing_layer_ids",
            "fingerprint",
        )
        data = _strict_object(value, context="DNA completion assessment", required=fields)
        if data["schema_version"] != DNA_COMPLETION_SCHEMA:
            raise DnaCompletionError("DNA completion assessment schema is not current")
        if not isinstance(data["layers"], list) or not isinstance(data["findings"], list):
            raise DnaCompletionError("DNA completion assessment arrays are malformed")
        assessment = cls(
            assessment_id=data["assessment_id"],
            target_system_id=data["target_system_id"],
            subject_revision=data["subject_revision"],
            claim_scope=data["claim_scope"],
            required_layer_ids=tuple(data["required_layer_ids"]),
            layers=tuple(DnaCompletionLayerEvidence.from_dict(row) for row in data["layers"]),
            expected_input_fingerprints=data["expected_input_fingerprints"],
            claim_boundary=data["claim_boundary"],
            expected_producer_identities=data["expected_producer_identities"],
        )
        report = assessment.report
        if (
            data["status"] != assessment.status
            or bool(data["dna_complete"]) != assessment.dna_complete
            or tuple(data["missing_layer_ids"]) != report.missing_layer_ids
            or tuple(DnaCompletionFinding.from_dict(row).to_dict() for row in data["findings"])
            != tuple(row.to_dict() for row in report.findings)
            or data["fingerprint"] != assessment.fingerprint
        ):
            raise DnaCompletionError("DNA completion assessment projection mismatch")
        return assessment


@dataclass(frozen=True)
class DnaCompletionReport:
    ok: bool
    dna_complete: bool
    assessment_fingerprint: str
    required_layer_ids: tuple[str, ...]
    present_layer_ids: tuple[str, ...]
    missing_layer_ids: tuple[str, ...]
    findings: tuple[DnaCompletionFinding, ...] = ()

    def __post_init__(self) -> None:
        for name in ("assessment_fingerprint",):
            object.__setattr__(self, name, _text(getattr(self, name), context=f"DNA report.{name}"))
        for name in ("required_layer_ids", "present_layer_ids", "missing_layer_ids"):
            object.__setattr__(self, name, _strings(getattr(self, name), context=f"DNA report.{name}"))
        object.__setattr__(self, "findings", tuple(self.findings))

    @property
    def status(self) -> str:
        if self.dna_complete:
            return "dna_complete"
        if self.ok:
            return "scoped_complete"
        return "blocked"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": DNA_COMPLETION_SCHEMA,
            "ok": self.ok,
            "dna_complete": self.dna_complete,
            "status": self.status,
            "assessment_fingerprint": self.assessment_fingerprint,
            "required_layer_ids": list(self.required_layer_ids),
            "present_layer_ids": list(self.present_layer_ids),
            "missing_layer_ids": list(self.missing_layer_ids),
            "findings": [finding.to_dict() for finding in self.findings],
        }


def _finding(code: str, message: str, *, layer_id: str = "") -> DnaCompletionFinding:
    return DnaCompletionFinding(code=code, message=message, layer_id=layer_id)


def _independent_input_findings(
    row: DnaCompletionLayerEvidence,
    *,
    expected_input: str,
) -> tuple[tuple[str, str], ...]:
    """Verify the frozen expected input from a file outside the evidence row.

    The evidence row is an observation and cannot be its own input inventory.
    A native owner therefore supplies ``input_manifest_path`` plus its
    independently captured hash in metadata.  This verifier re-reads the
    manifest and compares both the manifest hash and the expected layer input.
    """

    metadata = dict(row.metadata)
    manifest_path = metadata.get("input_manifest_path")
    manifest_fingerprint = str(metadata.get("input_manifest_fingerprint", ""))
    gaps: list[tuple[str, str]] = []
    if not isinstance(manifest_path, str) or not manifest_path.strip():
        return ((
            "dna_layer_independent_input_missing",
            "required DNA input identity has no independently verifiable manifest path",
        ),)
    if not is_sha256_fingerprint(manifest_fingerprint):
        gaps.append((
            "dna_layer_independent_input_fingerprint_invalid",
            "independent DNA input manifest fingerprint is not canonical",
        ))
    path = Path(manifest_path).expanduser()
    if not path.is_file():
        gaps.append((
            "dna_layer_independent_input_path_missing",
            "independent DNA input manifest path does not exist",
        ))
        return tuple(dict.fromkeys(gaps))
    try:
        actual = sha256_fingerprint(path.read_bytes())
    except OSError:
        gaps.append((
            "dna_layer_independent_input_unreadable",
            "independent DNA input manifest cannot be read",
        ))
        return tuple(dict.fromkeys(gaps))
    if actual != manifest_fingerprint:
        gaps.append((
            "dna_layer_independent_input_hash_mismatch",
            "independent DNA input manifest bytes do not match its declared hash",
        ))
    if expected_input != actual:
        gaps.append((
            "dna_layer_input_identity_mismatch",
            "frozen expected DNA input does not match the independently read manifest",
        ))
    return tuple(dict.fromkeys(gaps))


def _layer_proof_findings(
    row: DnaCompletionLayerEvidence,
    *,
    expected_identity: Mapping[str, str] | None,
) -> tuple[tuple[str, str], ...]:
    """Verify a layer's proof against the frozen producer plan.

    The evidence row is an observation, not an authority.  In particular, it
    may not invent the receipt id/hash or producer fingerprints and then ask
    this verifier to compare those values back to itself.  Broad DNA claims
    therefore require a complete expected identity supplied outside the row.
    """

    raw = dict(row.metadata).get("proof_artifact")
    if raw is None:
        return ((
            "dna_layer_proof_artifact_missing",
            "passed DNA layer has no independently loadable proof artifact",
        ),)
    if expected_identity is None:
        return (
            (
                "dna_layer_expected_producer_identity_missing",
                "passed DNA layer has no independently frozen producer identity",
            ),
        )
    missing = tuple(field for field in _PRODUCER_IDENTITY_FIELDS if not expected_identity.get(field))
    if missing:
        return (
            (
                "dna_layer_expected_producer_identity_incomplete",
                "frozen producer identity is missing: " + ", ".join(missing),
            ),
        )
    try:
        artifact = coerce_proof_artifact_ref(raw)
    except Exception as exc:
        return ((
            "dna_layer_proof_artifact_malformed",
            f"passed DNA layer proof artifact is malformed: {exc}",
        ),)
    expected = {
        "expected_receipt_id": expected_identity["receipt_id"],
        "expected_receipt_fingerprint": expected_identity["receipt_fingerprint"],
        "expected_owner_id": expected_identity["owner_id"],
        "expected_source_fingerprint": expected_identity["source_fingerprint"],
        "expected_model_fingerprint": expected_identity["model_fingerprint"],
        "expected_toolchain_fingerprint": expected_identity["toolchain_fingerprint"],
        "expected_environment_fingerprint": expected_identity["environment_fingerprint"],
        "expected_result_fingerprint": expected_identity["result_fingerprint"],
    }
    gaps = list(
        proof_artifact_gap_codes(
            artifact,
            declared_status="passed",
            require_verifiable_material=True,
            require_receipt=True,
            require_cleanup_confirmation=True,
            require_canonical_receipt=True,
            **expected,
        )
    )
    # The layer fingerprint must be bound to either the verified result or the
    # verified canonical receipt.  A detached, caller-authored hash is not a
    # terminal evidence identity.
    evidence_fingerprint = row.evidence_fingerprint
    if is_sha256_fingerprint(evidence_fingerprint):
        bound = {artifact.result_fingerprint, artifact.receipt_fingerprint}
        if evidence_fingerprint not in bound:
            gaps.append((
                "dna_layer_evidence_fingerprint_unbound",
                "DNA layer evidence fingerprint is not the verified result or receipt fingerprint",
            ))
    else:
        gaps.append((
            "dna_layer_evidence_fingerprint_invalid",
            "DNA layer evidence fingerprint is not canonical",
        ))
    return tuple(dict.fromkeys(gaps))


def _layer_subject_findings(
    row: DnaCompletionLayerEvidence,
    *,
    expected_subject_revision: str,
) -> tuple[tuple[str, str], ...]:
    """Ensure a terminal row keeps the assessment subject identity visible."""

    subject_revision = dict(row.metadata).get("subject_revision")
    if not isinstance(subject_revision, str) or not subject_revision.strip():
        return (
            (
                "dna_layer_subject_revision_missing",
                "passed DNA layer has no frozen assessment subject revision",
            ),
        )
    if subject_revision != expected_subject_revision:
        return (
            (
                "dna_layer_subject_revision_mismatch",
                "passed DNA layer subject revision differs from the assessment",
            ),
        )
    return ()


def _expected_producer_identity_findings(
    row: DnaCompletionLayerEvidence,
    *,
    expected: Mapping[str, str] | None,
) -> tuple[tuple[str, str], ...]:
    """Compare observed proof identities with the frozen assessment plan."""

    if expected is None:
        return (
            (
                "dna_layer_expected_producer_identity_missing",
                "passed DNA layer has no independently frozen producer identity",
            ),
        )
    missing = tuple(field for field in _PRODUCER_IDENTITY_FIELDS if not expected.get(field))
    if missing:
        return (
            (
                "dna_layer_expected_producer_identity_incomplete",
                "frozen producer identity is missing: " + ", ".join(missing),
            ),
        )
    try:
        artifact = coerce_proof_artifact_ref(dict(row.metadata).get("proof_artifact"))
    except Exception:
        # The proof-artifact validator reports the detailed shape/material
        # error.  This helper only owns the independent-identity join.
        return ()
    metadata = dict(row.metadata)
    observed = {
        "owner_id": row.owner_id,
        "evidence_id": row.evidence_id,
        "receipt_id": str(
            metadata.get("receipt_id")
            or metadata.get("producer_receipt_id")
            or getattr(artifact, "receipt_id", "")
            or row.evidence_id
        ),
        "receipt_fingerprint": str(
            metadata.get("receipt_fingerprint")
            or metadata.get("producer_receipt_fingerprint")
            or getattr(artifact, "receipt_fingerprint", "")
        ),
        "source_fingerprint": str(
            metadata.get("source_fingerprint")
            or getattr(artifact, "source_fingerprint", "")
        ),
        "model_fingerprint": str(
            metadata.get("model_fingerprint")
            or getattr(artifact, "model_fingerprint", "")
        ),
        "toolchain_fingerprint": str(
            metadata.get("toolchain_fingerprint")
            or getattr(artifact, "toolchain_fingerprint", "")
        ),
        "environment_fingerprint": str(
            metadata.get("environment_fingerprint")
            or getattr(artifact, "environment_fingerprint", "")
        ),
        "result_fingerprint": str(
            metadata.get("result_fingerprint")
            or getattr(artifact, "result_fingerprint", "")
        ),
    }
    return tuple(
        (
            "dna_layer_producer_identity_mismatch",
            f"observed {field} does not match the frozen producer identity",
        )
        for field in _PRODUCER_IDENTITY_FIELDS
        if observed.get(field) != expected.get(field)
    )


def review_dna_completion(assessment: DnaCompletionAssessment) -> DnaCompletionReport:
    """Reconcile every required DNA layer without executing target work."""

    if not isinstance(assessment, DnaCompletionAssessment):
        raise DnaCompletionError("DNA completion review requires a typed assessment")
    findings: list[DnaCompletionFinding] = []
    required = tuple(assessment.required_layer_ids)
    required_set = set(required)
    rows = tuple(assessment.layers)
    by_id: dict[str, DnaCompletionLayerEvidence] = {}
    duplicates: set[str] = set()
    for row in rows:
        if row.layer_id in by_id:
            duplicates.add(row.layer_id)
        by_id[row.layer_id] = row
    for layer_id in sorted(duplicates):
        findings.append(_finding("dna_layer_duplicate", "DNA completion has duplicate layer evidence", layer_id=layer_id))
    present = tuple(sorted(by_id))
    missing = tuple(sorted(required_set - set(by_id)))
    unexpected = tuple(sorted(set(by_id) - required_set))
    for layer_id in missing:
        findings.append(_finding("dna_layer_missing", "required DNA completion layer has no evidence row", layer_id=layer_id))
    for layer_id in unexpected:
        findings.append(_finding("dna_layer_unexpected", "DNA completion evidence is outside the frozen required layer set", layer_id=layer_id))
    if assessment.claim_scope == "broad" and required_set != set(DNA_COMPLETION_LAYER_IDS):
        findings.append(_finding("dna_broad_layer_set_incomplete", "broad DNA completion requires the complete current layer set"))
    missing_expected_inputs = tuple(
        sorted(required_set - set(assessment.expected_input_fingerprints))
    )
    for layer_id in missing_expected_inputs:
        findings.append(
            _finding(
                "dna_layer_expected_input_missing",
                "required DNA layer has no frozen expected input fingerprint",
                layer_id=layer_id,
            )
        )
    for layer_id, row in sorted(by_id.items()):
        expected_input = assessment.expected_input_fingerprints.get(layer_id)
        if (
            layer_id in required_set
            and row.status == DNA_COMPLETION_TERMINAL_SUCCESS
            and expected_input
            and not is_sha256_fingerprint(expected_input)
        ):
            findings.append(
                _finding(
                    "dna_layer_expected_input_invalid",
                    "frozen expected DNA input fingerprint is not a canonical SHA-256 digest",
                    layer_id=layer_id,
                )
            )
        if expected_input and row.input_fingerprint != expected_input:
            findings.append(_finding("dna_layer_input_identity_mismatch", "DNA layer input fingerprint does not match the frozen expected identity", layer_id=layer_id))
        if layer_id not in required_set:
            continue
        if row.status != DNA_COMPLETION_TERMINAL_SUCCESS:
            findings.append(_finding("dna_layer_not_terminal_success", f"required DNA layer status is {row.status}", layer_id=layer_id))
        if row.evidence_kind in DNA_COMPLETION_SELF_REPORTED_KINDS:
            findings.append(_finding("dna_layer_self_reported_only", "caller-authored evidence cannot license a DNA layer", layer_id=layer_id))
        if row.status == DNA_COMPLETION_TERMINAL_SUCCESS:
            if not is_sha256_fingerprint(row.input_fingerprint):
                findings.append(
                    _finding(
                        "dna_layer_input_fingerprint_invalid",
                        "passed DNA layer input fingerprint is not a canonical SHA-256 digest",
                        layer_id=layer_id,
                    )
                )
            if not is_sha256_fingerprint(row.evidence_fingerprint):
                findings.append(
                    _finding(
                        "dna_layer_evidence_identity_missing",
                        "passed DNA layer has no canonical terminal evidence fingerprint",
                        layer_id=layer_id,
                    )
                )
            for code, message in _layer_subject_findings(
                row,
                expected_subject_revision=assessment.subject_revision,
            ):
                findings.append(_finding(code, message, layer_id=layer_id))
            for code, message in _expected_producer_identity_findings(
                row,
                expected=assessment.expected_producer_identities.get(layer_id),
            ):
                findings.append(_finding(code, message, layer_id=layer_id))
            # These checks deliberately happen after status/identity checks so
            # malformed owner payloads become visible findings instead of
            # allowing a shape-only row to be treated as a pass.
            for code, message in _independent_input_findings(
                row,
                expected_input=expected_input or "",
            ):
                findings.append(_finding(code, message, layer_id=layer_id))
            for code, message in _layer_proof_findings(
                row,
                expected_identity=assessment.expected_producer_identities.get(layer_id),
            ):
                findings.append(_finding(code, message, layer_id=layer_id))
    ok = not findings
    dna_complete = ok and assessment.claim_scope == "broad" and required_set == set(DNA_COMPLETION_LAYER_IDS)
    return DnaCompletionReport(
        ok=ok,
        dna_complete=dna_complete,
        assessment_fingerprint=assessment.fingerprint,
        required_layer_ids=required,
        present_layer_ids=present,
        missing_layer_ids=missing,
        findings=tuple(findings),
    )


def serialize_dna_completion(assessment: DnaCompletionAssessment) -> bytes:
    return canonical_json_bytes(assessment.to_dict())


def write_dna_completion(assessment: DnaCompletionAssessment, path: str) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(serialize_dna_completion(assessment) + b"\n")
    return str(target)


def load_dna_completion(path: str) -> DnaCompletionAssessment:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DnaCompletionError(f"cannot load DNA completion artifact: {exc}") from exc
    return DnaCompletionAssessment.from_dict(value)


__all__ = [
    "DNA_COMPLETION_SCHEMA",
    "DNA_NATIVE_OWNER_INPUT_SCHEMA",
    "DNA_COMPLETION_LAYER_IDS",
    "DNA_COMPLETION_STATUSES",
    "DNA_COMPLETION_CLAIM_SCOPES",
    "DNA_COMPLETION_TERMINAL_SUCCESS",
    "DNA_EXTERNAL_OWNER_LAYER_IDS",
    "DNA_LAYER_STATIC_BLUEPRINT",
    "DNA_LAYER_SEMANTIC_MODEL",
    "DNA_LAYER_INTENT_INVENTORY",
    "DNA_LAYER_OBSERVED_IMPLEMENTATION_SURFACE",
    "DNA_LAYER_BIDIRECTIONAL_TRACEABILITY",
    "DNA_LAYER_BEHAVIOR_BINDING",
    "DNA_LAYER_CODE_BINDING",
    "DNA_LAYER_STATIC_TEST_BINDING",
    "DNA_LAYER_RUNTIME_TEST_EXECUTION",
    "DNA_LAYER_CONTRACT_UNIVERSE",
    "DNA_LAYER_REAL_UI_SURFACE",
    "DNA_LAYER_EXTERNAL_CONSUMER",
    "DNA_LAYER_FAULT_MATRIX",
    "DNA_LAYER_PLATFORM_PROVIDER",
    "DNA_LAYER_INSTALLATION",
    "DNA_LAYER_OBSERVED_MISS_BACKFEED",
    "DNA_LAYER_RELEASE_IDENTITY",
    "DnaCompletionError",
    "DnaCompletionLayerEvidence",
    "DnaCompletionNativeOwnerInput",
    "DnaCompletionFinding",
    "DnaCompletionAssessment",
    "DnaCompletionReport",
    "review_dna_completion",
    "serialize_dna_completion",
    "write_dna_completion",
    "load_dna_completion",
]
