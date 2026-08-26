## MODIFIED Requirements

### Requirement: In-place verification is exact and bounded

FlowGuard SHALL verify the native directory shape, pointer chain, bounded authority-member identities, parent/child links, code/test/oracle bindings, and source revision without loading target software or executing a reconstruction. Layout shape verification SHALL not hash every evidence, history, work, or runtime-output member. Governed content identities SHALL be checked by their declared native owners, and unknown files, duplicate members, path escapes, stale governed identities, duplicate JSON keys, and non-finite numbers SHALL remain visible failures.

#### Scenario: Native directory verifies

- **WHEN** the current directory contains only declared native files, its shape is safe, and all governed identities close
- **THEN** verification SHALL return a terminal result tied to the same source and model fingerprints

#### Scenario: Runtime output changes

- **WHEN** a valid evidence or runtime-output member changes without changing the native shape or governed input
- **THEN** layout verification SHALL not reclassify the model as stale solely for that output change
- **AND** the evidence owner SHALL report its own currentness

#### Scenario: Native directory is tampered

- **WHEN** a model, binding, pointer, or governed test identity is changed, removed, or duplicated
- **THEN** verification SHALL return blocked with the exact affected path or ID and SHALL not reinterpret it through a compatibility reader
