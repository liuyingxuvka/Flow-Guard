## MODIFIED Requirements

### Requirement: Non-Mutating Default

Default regression execution MUST NOT modify tracked repository files. A mutating runner SHALL require explicit authorization and an isolated output or worktree policy; mutation discovered in default mode MUST fail the run. Mutation observation SHALL use Git index identities for clean tracked preimages and exact hashes only for dirty or untracked governed paths; a non-Git run without an explicit finite mutation boundary SHALL block instead of falling back to a full repository byte scan.

#### Scenario: Runner rewrites result json in default mode

- **WHEN** a runner modifies a tracked `result.json` during default execution
- **THEN** the orchestrator SHALL mark a mutation-policy failure and full validation SHALL be blocked

#### Scenario: Reused-only regression has no source mutation

- **WHEN** every model result is reused from an exact current receipt and no governed path changes
- **THEN** the orchestrator SHALL not perform a pre/post full repository byte hash

#### Scenario: Non-Git mutation boundary is absent

- **WHEN** a non-Git repository requests full mutation proof without a caller-declared finite boundary
- **THEN** the orchestrator SHALL return a typed blocked result and SHALL not scan the entire repository as a fallback
