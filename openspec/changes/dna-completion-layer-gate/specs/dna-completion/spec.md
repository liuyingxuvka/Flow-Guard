## ADDED Requirements

### Requirement: Broad DNA completion is an explicit layered claim

A broad DNA completion assessment SHALL declare the complete current seventeen
layer set and SHALL preserve one typed evidence row for every required layer.
The aggregate `dna_complete` result SHALL be derived from those rows and SHALL
NOT be inferred from static blueprint, model, test-count, or caller-authored
boolean status.

#### Scenario: Static model readiness without runtime evidence

- **WHEN** static, semantic, code, and static-test rows pass but the runtime
  execution row is `not_run`
- **THEN** the assessment SHALL remain blocked and SHALL identify the runtime
  layer as non-terminal

#### Scenario: Current native layer evidence licenses broad completion

- **WHEN** every required layer has a current native owner, matching input
  identity, terminal-success evidence id and fingerprint, and external claim
  boundary
- **THEN** the assessment MAY report `dna_complete`

### Requirement: Non-pass and self-reported states remain visible

`failed`, `stale`, `skipped`, `not_run`, `missing`, `blocked`,
`not_applicable`, `self_reported_only`, and `unverified` SHALL never be
silently promoted to success. A required `not_applicable` row SHALL block a
broad claim even when it has a reason.

#### Scenario: Fake UI state cannot authorize a real UI layer

- **WHEN** a UI layer supplies only a boolean or caller-authored evidence kind
- **THEN** review SHALL classify it as self-reported or non-terminal and block
  broad DNA completion

### Requirement: Evidence identities are currentness inputs

Each required layer SHALL match its frozen expected input fingerprint. A source,
model, toolchain, environment, package, external-target, or release identity
mismatch SHALL block the aggregate claim rather than reusing an older row.

#### Scenario: Source revision changes after a passed receipt

- **WHEN** a passed layer's input fingerprint differs from the frozen expected
  source or model identity
- **THEN** review SHALL report an input-identity mismatch and keep the claim
  blocked

### Requirement: Native-owner inputs SHALL preserve the frozen assessment subject

The assessment ingress SHALL accept a typed native-owner input that names the
layer owner, frozen subject revision, layer input fingerprint, disposition,
evidence kind, and claim boundary. The ingress SHALL normalize only into the
current layer-evidence row; it SHALL not execute an owner or manufacture a
terminal receipt. Every required layer SHALL have an expected input fingerprint
in the assessment, and an omitted expected fingerprint SHALL be a visible
blocker rather than an implicit wildcard.

#### Scenario: A native owner supplies a bounded non-pass disposition

- **WHEN** an owner supplies a `not_run` or `blocked` input with a subject
  revision, input identity, and visible reason
- **THEN** the assessment SHALL retain the normalized row and SHALL keep the
  affected claim non-terminal

#### Scenario: A required layer omits its expected input identity

- **WHEN** the layer row has a receipt but the frozen assessment omits its
  expected input fingerprint
- **THEN** review SHALL report `dna_layer_expected_input_missing` for that
  layer and SHALL NOT treat the omitted value as a match

### Requirement: External-owner gaps SHALL remain explicit

The UI, external-consumer, fault-matrix, platform/provider, installation,
observed-miss-backfeed, and release-identity layers SHALL remain target-owned.
FlowGuard SHALL not install a product-specific owner map or mark one of these
layers passed from an in-memory fixture, boolean, progress signal, or local
placeholder. Until the real owner supplies current terminal evidence, the row
SHALL remain `blocked`, `not_run`, `stale`, `unverified`, or an explicitly
reasoned `not_applicable`; a required `not_applicable` row SHALL still block a
broad claim.

#### Scenario: External owner work is unavailable in the local audit

- **WHEN** no real UI, platform, fault, installation, incident, or release
  owner receipt is available under the frozen identity
- **THEN** the assessment SHALL retain a typed non-pass row and visible reason,
  leaving the parent-owned completion task open

#### Scenario: A clean wheel runs a documented CLI scenario

- **WHEN** a non-editable FlowGuard wheel is installed in a clean environment
  outside the source checkout and the documented `scenario-review` console
  command is invoked
- **THEN** the command SHALL execute its maintained example dependency from the
  installed wheel, return exit code `0`, and emit its terminal `status: OK`
  summary
- **AND** a `--help` success or package import success alone SHALL NOT satisfy
  this command-level consumer check

### Requirement: DNA evidence SHALL be independently replayable

The DNA gate SHALL consume an immutable producer receipt or an independently
verified receipt projection. A caller-provided `status: passed`, a
`sha256:`-prefixed string, an in-memory `evidence://` reference, or a result
path that is not opened and rehashed SHALL never satisfy a required layer.
Receipt verification SHALL bind the producer owner, source/model/toolchain/
environment identities, command and exit state, terminal and cleanup state,
and the receipt's own canonical hash. Expected input identities SHALL come
from a separately frozen authority, not from the evidence artifact being
verified.

#### Scenario: Shape-valid fake evidence is rejected

- **WHEN** a caller supplies seventeen `passed` rows with invented hash-prefix
  values or a nonexistent result path
- **THEN** the verifier SHALL return a visible blocker and SHALL NOT derive
  `dna_complete=true`

#### Scenario: Reused evidence has no producer receipt

- **WHEN** a runtime or contract row is marked reused without an immutable
  same-unit producer receipt and exact reuse identity
- **THEN** reconciliation SHALL classify the row as blocked or stale
  regardless of its outcome string

### Requirement: Broad behavior claims SHALL close both directions

The broad DNA gate SHALL require an independently discovered implementation
surface inventory and a conservation report that closes both directions:
every reachable code/API/CLI/config/effect/UI-like surface maps to one typed
intent/model/obligation/test disposition, and every claimed model obligation
maps back to an implementation surface or an explicitly verified
model-only/retired/not-applicable disposition. Unknown, orphaned, duplicate,
or happy-path-only rows remain blockers.

#### Scenario: Unmodelled reachable surface blocks

- **WHEN** a new public command, export, UI-like action, state-changing branch,
  file/config effect, or recovery path is discoverable but has no typed intent,
  owner, failure/recovery obligation, and test binding
- **THEN** reverse-closure review SHALL emit a blocker and SHALL NOT extend the
  current behavior denominator implicitly

### Requirement: Observed implementation surface completeness is an explicit DNA layer

The broad DNA assessment SHALL expose an explicit
`observed_implementation_surface_complete` result derived from an independent
source observation and a typed disposition for every discovered code, API,
CLI, configuration, file-format, effect, UI-like, installation, fault, and
recovery surface. A zero-row or self-authored inventory SHALL be treated as a
missing denominator, not as an empty complete product.

#### Scenario: Empty mapping is not a complete surface result

- **WHEN** source observation discovers surfaces but the semantic mapping has
  zero rows or no independent discovery authority
- **THEN** the surface layer SHALL remain blocked and SHALL report the missing
  denominator explicitly

### Requirement: Bidirectional traceability completeness is an explicit DNA layer

The broad DNA assessment SHALL expose an explicit
`bidirectional_traceability_complete` result only when every reachable surface
maps forward to intent, model, obligation, test, owner, and evidence, and every
model obligation maps backward to an implementation surface or an independent
typed model-only, retired, or not-applicable proof. Orphan code, orphan UI,
orphan tests, duplicate primary owners, unknown intents, and happy-path-only
bindings SHALL remain blockers.

#### Scenario: Orphaned test or model obligation blocks

- **WHEN** a test has no behavior/obligation binding or a model obligation has
  no implementation surface and no typed proof
- **THEN** bidirectional traceability SHALL report a stable blocker and SHALL
  not increase the completed behavior denominator

### Requirement: The project control plane has one human-readable current layout

Every adopted FlowGuard target SHALL expose one mandatory current
`.flowguard/layout.toml` that declares the exact role roots `behavior`,
`models`, `structure`, `verification`, `evidence`, `audits`, `projections`,
`history`, and `work`. The control-plane layout SHALL not use `DNA`,
`dna_audit`, `software_dna`, `tmp`, or `run_artifacts` as a role or authority
path. A navigation README MAY explain the roles but SHALL never be treated as
model, contract, receipt, or release authority.

#### Scenario: An old or ambiguous layout blocks before model reads

- **WHEN** a target has no current layout manifest, an unknown top-level entry,
  a missing role root, a role collision, or a retired layout component
- **THEN** project adoption/audit SHALL stop before reading old model or
  evidence paths as current authority
- **AND** the target SHALL report a direct-current rewrite action rather than
  offering a migration command, fallback reader, alias, or dual authority

#### Scenario: A newly adopted empty target receives only current navigation

- **WHEN** a target has no existing `.flowguard` artifacts and adoption is
  explicitly requested
- **THEN** adoption MAY create the current role roots, manifest, and navigation
  README
- **AND** it SHALL not classify, move, copy, or inherit historical artifacts

#### Scenario: History, audits, and work cannot silently become authority

- **WHEN** a model, receipt, or projection consumer points at `history/`,
  `audits/`, or `work/` as current authority
- **THEN** layout/currentness review SHALL block the claim until the maintainer
  directly rewrites the artifact into its current role and rebuilds its
  identity
