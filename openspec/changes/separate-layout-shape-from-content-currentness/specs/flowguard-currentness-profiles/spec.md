## Purpose

This capability defines bounded currentness profiles so ordinary FlowGuard use can remain fast while full model, proof, installation, and release claims stay exact and fail-closed.

## ADDED Requirements

### Requirement: Light currentness is shape and pointer only

FlowGuard SHALL provide a `light` profile that checks the current layout shape, adoption controls, and the sole current authority pointer without scanning evidence descendants, receipt stores, distribution trees, or all governed source content. The result SHALL mark semantic model, validation, and release checks as `not_run`.

#### Scenario: Small current project passes light preflight

- **WHEN** the allowed roots, current schema, adoption record, and referenced head/manifest exist and are structurally valid
- **THEN** light preflight SHALL pass with `layout_shape_current` and `head_pointer_current`
- **AND** it SHALL report semantic model, validation, and release currentness as `not_run`

#### Scenario: Light preflight sees an unsafe shape

- **WHEN** an unknown root, reparse point, bytecode/cache entry, obsolete current schema, or invalid current pointer is present
- **THEN** light preflight SHALL block with a typed finding before reading deep model or evidence authority

### Requirement: Affected currentness is exact and fail-closed

FlowGuard SHALL provide an `affected` profile that derives changed paths and maps them to exact governed components and owners. An unmapped or multiply mapped changed path SHALL block before execution; affected currentness SHALL NOT expand to a full or run-all validation as a fallback.

#### Scenario: One changed component selects one owner closure

- **WHEN** every changed governed path maps to an unambiguous component and owner closure
- **THEN** affected validation SHALL observe the union of those inputs once and execute only stale owners in that closure

#### Scenario: Changed path has no exact owner

- **WHEN** a changed path is unmapped or has multiple possible owners
- **THEN** affected validation SHALL return `unmapped_changed_component` or `ambiguous_component_owner`
- **AND** it SHALL start no validation owner

### Requirement: Full validation consumes one frozen observation

FlowGuard SHALL provide a `full` profile for activation, installation, release, and explicitly requested complete validation. One full invocation SHALL freeze its source, receipt, release-tree, model, toolchain, and physical-distribution observations and SHALL project all owner checks from those observations before one final freshness reconciliation.

#### Scenario: Frozen full validation closes

- **WHEN** the source, toolchain, owner graph, and required checks are frozen and every executed owner terminates successfully
- **THEN** the parent SHALL publish one terminal receipt bound to the frozen inputs and final reconciliation

#### Scenario: Full input changes during execution

- **WHEN** a governed source, toolchain, receipt, or release input changes after the frozen observation
- **THEN** final reconciliation SHALL block the parent and SHALL NOT reuse the stale child set

### Requirement: Profile output is bounded and explicit

Every profile SHALL return typed `checks_run`, `checks_not_run`, `blocked`, `claim_boundary`, elapsed phase metrics, and bounded findings. Routine terminal output SHALL omit full inventories and payloads and SHALL reference one machine artifact when complete detail is needed.

#### Scenario: Large inventory is available

- **WHEN** a profile observes more than the bounded finding or output limit
- **THEN** the terminal result SHALL include counts, the first bounded findings, and `omitted_count`
- **AND** it SHALL not embed the complete inventory in the terminal envelope
