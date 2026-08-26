## Why

Every target project carries a `.flowguard` control plane, but historical
projects have mixed model, test, receipt, report, installation, and temporary
material in names that are difficult for a person to navigate.  A current
layout must be a single, readable authority and must stop before any old model
or evidence reader can silently treat history as current.

## What Changes

- **BREAKING** Make the current `.flowguard` layout mandatory and define one
  human-readable role root for behavior, models, structure, verification,
  evidence, audits, projections, history, and work.
- **BREAKING** Reject `DNA`, `dna_audit`, `software_dna`, temporary roots,
  unknown roots, flat legacy artifacts, duplicate authorities, and reparse
  points as current layout input.
- Make layout inspection read-only and run it before project model, test, or
  evidence authority is read.
- Require a current layout manifest with schema/version, project identity,
  role roots, member inventory/fingerprints, model-authority pointer, and
  explicit non-authority declarations for history, work, audits, and
  projections.
- Require a direct manual/AI rewrite of stale projects and rebuild affected
  model, test, contract, and receipt identities; provide no generic
  migration command, compatibility reader, alias, or fallback path.
- Add deterministic positive and negative fixtures for missing, stale, mixed,
  duplicated, moved, linked, and history-backed layouts.

## Capabilities

### New Capabilities

- `project-layout-contract`: Defines the current human-readable `.flowguard`
  role layout, read-only audit, authority boundaries, direct-current rewrite
  requirement, and fail-closed project-audit ordering.

### Modified Capabilities

- `project-adoption-version-gate`: Require the layout gate before model and
  evidence authority and make stale-layout dispositions direct-current only.
- `authoritative-model-system`: Make layout and role-member identity inputs to
  the current model authority and invalidate pointers after a layout change.

## Impact

- FlowGuard layout and adoption readers, project-audit ordering, project
  manifests, templates, current identity calculations, and layout/model tests.
- Existing target projects with old or mixed `.flowguard` trees will block
  until an AI or human performs a direct, item-by-item rewrite.
- No consumer package dependency or automatic migration surface is added.
