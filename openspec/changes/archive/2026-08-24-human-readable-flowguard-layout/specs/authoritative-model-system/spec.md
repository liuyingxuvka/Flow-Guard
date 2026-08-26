## ADDED Requirements

### Requirement: Current model authority includes layout identity

The current observed model head SHALL bind the current project-layout
manifest identity and role-member inventory. A layout change SHALL make the
model authority stale until one accepted current `ModelRevisionSet` rebuilds
the affected snapshot, owner evidence, and pointer.

#### Scenario: Stored model points at a changed layout

- **WHEN** the live layout identity differs from the identity bound by the
  accepted model revision
- **THEN** authority audit SHALL block with a stale layout/model identity and
  SHALL not select an older snapshot

#### Scenario: Direct model rebuild follows layout rewrite

- **WHEN** a current layout and affected source/model inputs are frozen
- **THEN** one accepted revision set MAY replace the observed head and produce
  a new current snapshot and activation receipt
