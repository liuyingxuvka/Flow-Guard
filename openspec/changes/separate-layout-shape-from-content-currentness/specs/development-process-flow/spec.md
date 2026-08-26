## MODIFIED Requirements

### Requirement: Evidence freshness and proof artifacts

FlowGuard SHALL let DevelopmentProcessFlow consume proof artifact metadata as the concrete evidence boundary for validation freshness when a staged done, release, archive, publish, or full-confidence claim depends on current proof. The process SHALL build one invocation-local observation and reuse it across affected owners; a broad full validation SHALL run only once after the source, toolchain, impact graph, and checks are frozen. Reports, progress logs, and runtime outputs SHALL not refresh source authority unless a native contract explicitly declares them as functional inputs.

#### Scenario: Evidence result path is missing

- **WHEN** strict process evidence is required and validation evidence declares a pass but has no result path or proof artifact reference
- **THEN** DevelopmentProcessFlow SHALL report incomplete validation evidence

#### Scenario: Artifact versions changed after proof

- **WHEN** a proof artifact covers older artifact versions than the current model, code, test, adapter, or requirement artifact
- **THEN** DevelopmentProcessFlow SHALL mark the proof stale and recommend affected revalidation

#### Scenario: Unchanged owner is reused inside one invocation

- **WHEN** an owner has an immutable terminal-success receipt matching the frozen unit, inputs, dependencies, toolchain, environment, and claim boundary
- **THEN** the process MAY project that receipt without rescanning the receipt store for each sibling owner

#### Scenario: Changed component has no mapping

- **WHEN** a changed component is unmapped or ambiguously owned
- **THEN** the process SHALL block the affected plan and SHALL not run every owner as a fallback
