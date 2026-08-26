## MODIFIED Requirements

### Requirement: Canonical suite validation supports ownership-backed mixed roots

FlowGuard suite validation SHALL distinguish the canonical FlowGuard suite from unrelated skills co-located in the same skill root only when the package-owned consumer authority proves the exact current canonical member and file boundary. Membership MUST be derived from that authority and MUST NOT be repeated as a fixed literal list. Within one invocation, identical resolved physical roots and member policies SHALL share one frozen inventory observation; this reuse SHALL not become a cross-run fallback or persistent authority.

#### Scenario: Official suite is co-located with unrelated skills

- **WHEN** the package-owned authority names every current FlowGuard consumer member and owns every required member file
- **AND** every authority-declared member directory and required file exists
- **AND** additional non-FlowGuard skill directories also contain `SKILL.md`
- **THEN** suite validation SHALL pass for the authority-declared FlowGuard set
- **AND** it SHALL report unrelated directories separately as co-located skills outside the validation claim

#### Scenario: Same physical root is requested twice

- **WHEN** two owners request the same resolved distribution root with the same exclusion/member policy in one invocation
- **THEN** they SHALL consume one frozen inventory observation
- **AND** parity checks SHALL still perform one final exact freshness check before publishing a terminal result

#### Scenario: Mixed root lacks valid ownership evidence

- **WHEN** undeclared skill directories exist and the package authority is missing, unsupported, incomplete, or stale
- **THEN** validation SHALL remain blocked and report the authority defect

#### Scenario: Undeclared FlowGuard-like skill is present

- **WHEN** a valid package authority exists and an undeclared skill id uses a FlowGuard-reserved id or prefix
- **THEN** validation SHALL report that id as `extra_discovered_member` and the suite SHALL remain blocked

#### Scenario: Canonical member is missing from a mixed root

- **WHEN** a valid package authority exists and any authority-declared member directory or required file is missing
- **THEN** validation SHALL report the existing missing-member or missing-file finding and co-located skills SHALL not satisfy or hide the missing obligation
