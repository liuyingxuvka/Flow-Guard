## ADDED Requirements

### Requirement: Project adoption checks the layout before authority

The existing project-adoption version gate SHALL run the current layout audit
before reading model, test, receipt, or evidence authority. A layout blocker
SHALL make those later checks `not_run`, SHALL preserve the exact blocker, and
SHALL require a direct current rewrite before adoption can pass.

#### Scenario: Layout is blocked before model authority

- **WHEN** the target layout is missing, stale, mixed, or unsafe
- **THEN** project adoption SHALL report `project_layout_invalid`
- **AND** model/test/evidence authority SHALL not be consulted

#### Scenario: Current layout allows authority checks

- **WHEN** the layout passes with a current manifest and conserved inventory
- **THEN** adoption MAY proceed to model and suite checks, each with its own
  current identity and claim boundary

### Requirement: Direct-current repair has no general migration path

Project adoption SHALL never add or call a general migration command,
compatibility reader, alias, dual manifest, or fallback layout authority.
Stale material SHALL remain historical input until an AI or human classifies
and directly rewrites it into the current layout.

#### Scenario: Historical material is available

- **WHEN** old paths or old manifests exist under history or elsewhere
- **THEN** adoption SHALL not use them as current authority and SHALL keep the
  target blocked until direct rewrite and identity rebuild complete
