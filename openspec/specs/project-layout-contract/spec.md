# project-layout-contract Specification

## Purpose
Define the compact, shape-only `.flowguard` layout that keeps current source,
model authority, verification, evidence, and explicitly non-authoritative
history readable without turning layout inspection into a repository-wide
content-hash operation.
## Requirements
### Requirement: Current layout is mandatory and human-readable

Every adopted target SHALL have exactly one current `.flowguard/layout.toml`
whose schema, version, project identity, current authority, and nine role roots
are current. The role roots SHALL be `behavior`, `models`, `structure`,
`verification`, `evidence`, `audits`, `projections`, `history`, and `work`.
The current role names SHALL NOT contain `DNA`, `dna_audit`, `software_dna`,
or an equivalent ambiguous authority name.

#### Scenario: Complete current layout passes

- **WHEN** the manifest is current, the nine roots exist, and every inspected
  entry belongs to exactly one declared role
- **THEN** the layout audit SHALL pass without writing any file

#### Scenario: Missing or stale layout blocks

- **WHEN** `.flowguard`, `layout.toml`, a required role, or the current schema
  is missing or stale
- **THEN** the layout audit SHALL block before model, test, or evidence
  authority is read

### Requirement: Role authority is explicit and conserved

The current manifest SHALL bind project identity, role roots, role-member
inventory/fingerprints, the current model-authority pointer, and explicit
non-authority declarations for `history`, `work`, `audits`, and `projections`.
Each real entry SHALL belong to exactly one role. Duplicate paths, duplicate
content identities, duplicate current authority, missing inventory members,
and inventory members absent from disk SHALL block.

#### Scenario: Material is placed in the wrong role

- **WHEN** a model is under `evidence`, a receipt is under `models`, a current
  artifact is under `history`, or an audit/work artifact is used as current
  evidence
- **THEN** audit SHALL report a typed role-authority blocker

#### Scenario: Inventory is not conserved

- **WHEN** the manifest inventory and current disk entries differ by path or
  fingerprint
- **THEN** audit SHALL block and SHALL NOT read an alternate path

### Requirement: Audit is read-only and fail-closed

Layout audit SHALL not create directories, move files, write a manifest,
repair content, or select an older layout. A failed audit SHALL mark later
model/test/evidence checks `not_run` and SHALL NOT inspect history as a
fallback current source.

#### Scenario: Audit observes an old project

- **WHEN** a legacy or mixed layout is present
- **THEN** the report SHALL recommend a direct manual/AI rewrite and SHALL
  contain no migration command, compatibility reader, alias, or fallback
  authority

### Requirement: Unsafe and ambiguous filesystem entries are rejected

The audit SHALL reject symlinks, junctions, Windows reparse points,
`__pycache__`, `.pyc`, `.pyo`, tool caches, unknown top-level entries, flat
legacy model/runner/PID artifacts, and any current path collision.

#### Scenario: Reparse point or bytecode is present

- **WHEN** a role contains a reparse point, bytecode, or cache entry
- **THEN** the current layout SHALL remain blocked

### Requirement: Layout changes stale current identities

Any role membership, path, or content fingerprint change SHALL invalidate the
affected project, model, contract, test, installation, and receipt identities.
No old receipt may remain current solely because its content bytes are equal.

#### Scenario: A current model moves roles

- **WHEN** a model path or role changes after a receipt was issued
- **THEN** the previous model and affected receipts SHALL be stale until a
  direct current rebuild produces new identities
