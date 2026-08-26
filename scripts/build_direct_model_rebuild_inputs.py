"""Create explicit current-model rebuild inputs after manual intent review.

This helper is deliberately not an upgrade reader.  It requires the caller to
name every model that was reviewed.  Unnamed models block instead of being
silently inherited.  Unchanged rows are emitted as explicit ``retain``
transitions; changed rows receive a new contribution id and an explicit
``supersede`` transition.  The old contribution is used only as provenance for
the new decision and never remains authoritative by accident.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from flowguard.model_authority_store import (
    load_current_accepted_revision_set,
    load_observed_model_system,
)
from flowguard.model_intent import ModelIntentDisposition
from flowguard.model_intent_authority import EffectiveIntentTransition
from flowguard.model_path_quality import PathQualityResult, PathQualitySubject
from flowguard.model_revision_set import derive_revision_snapshot_diff
from flowguard.model_system_inventory import build_manifest_model_system_snapshot
from flowguard.self_path_quality import compile_flowguard_self_path_quality_material
from flowguard.source_identity import source_file_fingerprint


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _changed_models(diff) -> tuple[str, ...]:
    return tuple(
        sorted(
            member.member_id
            for member in diff.members
            if member.operation in {"add", "replace"}
        )
    )


def _relation_targets(
    diff,
    changed_models: Iterable[str],
    manual_assignments: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, tuple[str, ...]]:
    models = tuple(sorted(changed_models))
    rows: dict[str, list[str]] = {model: [] for model in models}
    assignments = {
        str(model): tuple(str(relation_id) for relation_id in relation_ids)
        for model, relation_ids in (manual_assignments or {}).items()
    }
    unknown_models = sorted(set(assignments) - set(models))
    if unknown_models:
        raise RuntimeError(
            "manual relation assignment names an unreviewed model: "
            + ", ".join(unknown_models)
        )
    changed_relation_ids = set(diff.changed_relation_ids)
    assigned_ids: dict[str, str] = {}
    for model, relation_ids in assignments.items():
        for relation_id in relation_ids:
            if relation_id not in changed_relation_ids:
                raise RuntimeError(
                    f"manual relation assignment names a non-current changed relation: {relation_id}"
                )
            previous = assigned_ids.get(relation_id)
            if previous is not None and previous != model:
                raise RuntimeError(
                    f"changed relation is assigned to multiple models: {relation_id}"
                )
            assigned_ids[relation_id] = model
            rows[model].append(relation_id)
    unassigned: list[str] = []
    for relation_id in diff.changed_relation_ids:
        if relation_id in assigned_ids:
            continue
        matches = [
            model
            for model in models
            if model in relation_id or model.replace("_", "-") in relation_id
        ]
        if len(matches) == 1:
            rows[matches[0]].append(relation_id)
        else:
            unassigned.append(relation_id)
    if unassigned:
        raise RuntimeError(
            "changed relation ids need an explicit manual model assignment: "
            + ", ".join(unassigned)
        )
    return {model: tuple(sorted(values)) for model, values in rows.items()}


def build_inputs(
    root: Path,
    *,
    snapshot_id: str,
    revision_token: str,
    reviewed_models: tuple[str, ...],
    relation_assignments: Mapping[str, Sequence[str]] | None = None,
    intent_output: Path,
    path_quality_output: Path,
) -> dict[str, object]:
    head, base = load_observed_model_system(root)
    revision = load_current_accepted_revision_set(root, head=head, snapshot=base)
    if revision is None:
        raise RuntimeError("a current accepted revision is required for direct rebuild")
    candidate = build_manifest_model_system_snapshot(
        root,
        snapshot_id=snapshot_id,
        system_id=base.system_id,
        subject_lane=base.subject_lane,
        lifecycle=base.lifecycle,
    )
    diff = derive_revision_snapshot_diff(base, candidate)
    changed = _changed_models(diff)
    reviewed = tuple(sorted(set(reviewed_models)))
    if reviewed != tuple(sorted(changed)):
        raise RuntimeError(
            "manual review set must exactly equal changed model set; "
            f"changed={changed}; reviewed={reviewed}"
        )
    relation_targets = _relation_targets(diff, changed, relation_assignments)
    active = revision.current_effective_intent_view.active_contributions
    active_by_model = {
        item.logical_model_id.removeprefix("model:"): item for item in active
    }
    missing = tuple(sorted(set(changed) - set(active_by_model)))
    if missing:
        raise RuntimeError("changed models have no prior reviewed intent: " + ", ".join(missing))

    contributions = []
    dispositions = []
    transitions = []
    replacement_counts: dict[str, int] = {}
    for prior in active:
        model_name = prior.logical_model_id.removeprefix("model:")
        if model_name not in changed:
            transitions.append(
                EffectiveIntentTransition(
                    prior_contribution_id=prior.contribution_id,
                    prior_contribution_fingerprint=prior.fingerprint,
                    action="retain",
                    replacement_contribution_ids=(),
                    reason=(
                        "Manual current-standard review retained this historical "
                        "intent as provenance-compatible; no automatic inheritance "
                        "or legacy reader is authorized."
                    ),
                )
            )
            continue
        replacement_counts[model_name] = replacement_counts.get(model_name, 0) + 1
        new_id = (
            f"current-design:{revision_token}:{model_name}:"
            f"{replacement_counts[model_name]}"
        )
        # A direct current rewrite must re-bind the reviewed contribution to
        # the bytes that are current *now*.  Keeping the predecessor's source
        # fingerprint would make the official builder reject the explicit
        # review as stale; silently retaining it would be an accidental
        # compatibility path.  The caller has already named this model in the
        # exact reviewed-model set, so refreshing this project-file identity
        # is part of that manual current decision.  WorkContext-backed
        # contributions remain strict: their declared context/artifact
        # identity is validated by the official builder and is never guessed.
        refreshed_source_fingerprint = prior.source_fingerprint
        if not prior.work_context_id:
            source_path = (root / prior.source_ref).resolve(strict=True)
            if root not in source_path.parents:
                raise RuntimeError(
                    "reviewed intent source escapes the project root: "
                    + prior.source_ref
                )
            refreshed_source_fingerprint = source_file_fingerprint(source_path)
        new_contribution = replace(
            prior,
            contribution_id=new_id,
            supersedes_contribution_ids=(prior.contribution_id,),
            effective_revision=revision_token,
            source_fingerprint=refreshed_source_fingerprint,
            rationale=(
                "Manual review of the historical specification accepted this "
                "intent as the current design source for a direct model rebuild. "
                "The implementation identity changed, so the old contribution "
                "is superseded explicitly; no compatibility or automatic "
                "inheritance path exists."
            ),
        )
        contributions.append(new_contribution)
        dispositions.append(
            ModelIntentDisposition(
                contribution_id=new_id,
                contribution_fingerprint=new_contribution.fingerprint,
                disposition="accepted",
                changed_obligation_ids=(),
                changed_state_ids=(),
                changed_transition_ids=(),
                changed_invariant_ids=(),
                changed_relation_ids=relation_targets[model_name],
                scoped_gap_ids=(),
                conflict_ids=(),
                unresolved_effect_ids=(),
                unreachable_terminal_state_ids=(),
                unconsumed_output_ids=(),
                reason=(
                    "Manual review accepted the historical intent as current "
                    "provenance for the changed implementation; all changed "
                    "semantic relations are explicitly assigned to this intent."
                ),
            )
        )
        transitions.append(
            EffectiveIntentTransition(
                prior_contribution_id=prior.contribution_id,
                prior_contribution_fingerprint=prior.fingerprint,
                action="supersede",
                replacement_contribution_ids=(new_id,),
                reason=(
                    "Direct current-standard rebuild after observed implementation "
                    "identity drift; the predecessor remains provenance only and "
                    "is not automatically inherited."
                ),
            )
        )

    _write_json(
        intent_output,
        {
            "contributions": [item.to_dict() for item in sorted(contributions, key=lambda x: x.contribution_id)],
            "dispositions": [item.to_dict() for item in sorted(dispositions, key=lambda x: x.contribution_id)],
            "effective_intent_transitions": [item.to_dict() for item in sorted(transitions, key=lambda x: x.prior_contribution_id)],
        },
    )

    material = compile_flowguard_self_path_quality_material(
        root,
        candidate,
    )
    _write_json(
        path_quality_output,
        {
            "subjects": [item.to_dict() for item in material.review.subjects],
            "results": [item.to_dict() for item in material.review.results],
        },
    )
    return {
        "status": "pass",
        "base_snapshot_fingerprint": base.fingerprint,
        "candidate_snapshot_fingerprint": candidate.fingerprint,
        "changed_models": list(changed),
        "active_intent_count": len(active),
        "explicit_retain_count": len(active) - len(contributions),
        "explicit_supersede_count": len(contributions),
        "intent_output": str(intent_output),
        "path_quality_output": str(path_quality_output),
        "path_quality_result_count": len(material.review.results),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--revision-token", required=True)
    parser.add_argument("--reviewed-model", action="append", required=True)
    parser.add_argument(
        "--relation-assignment",
        action="append",
        default=[],
        metavar="MODEL=RELATION_ID",
        help="Explicitly assign an ambiguous changed relation to a reviewed model; repeat for multiple relations.",
    )
    parser.add_argument("--intent-output", required=True, type=Path)
    parser.add_argument("--path-quality-output", required=True, type=Path)
    args = parser.parse_args()
    relation_assignments: dict[str, list[str]] = {}
    for raw_assignment in args.relation_assignment:
        if "=" not in raw_assignment:
            parser.error("--relation-assignment must use MODEL=RELATION_ID")
        model, relation_id = raw_assignment.split("=", 1)
        model = model.strip()
        relation_id = relation_id.strip()
        if not model or not relation_id:
            parser.error("--relation-assignment must use non-empty MODEL=RELATION_ID")
        relation_assignments.setdefault(model, []).append(relation_id)
    try:
        payload = build_inputs(
            args.root.resolve(),
            snapshot_id=args.snapshot_id,
            revision_token=args.revision_token,
            reviewed_models=tuple(args.reviewed_model),
            relation_assignments=relation_assignments,
            intent_output=args.intent_output.resolve(),
            path_quality_output=args.path_quality_output.resolve(),
        )
    except (OSError, RuntimeError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
