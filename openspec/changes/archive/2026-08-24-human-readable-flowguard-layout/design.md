## Context

The current repository contains a large historical `.flowguard` tree and a
newer role-oriented layout implementation. The implementation must be made
current without turning the old tree into a second authority or hiding
uncertain material behind a generic migration utility. Layout is a preflight
boundary: if it is not current, later model and evidence checks are not run.

## Decisions

### 1. One readable role vocabulary

The current role set is fixed to:

| Role | Current meaning | May license current claims? |
| --- | --- | --- |
| `behavior` | accepted current intent and behavior contracts | only through its own current contract joins |
| `models` | executable model authority and revisions | only through current model authority |
| `structure` | surface ownership and code binding maps | only through current map joins |
| `verification` | test/check definitions and inventories | only through native execution evidence |
| `evidence` | immutable terminal results and receipts | yes, when independently verified |
| `audits` | read-only diagnostic reports | no |
| `projections` | installation and consumer projections | only through their own projection/currentness checks |
| `history` | immutable provenance and superseded material | no |
| `work` | transient shards, logs, and intermediate products | no |

`DNA` is a conceptual claim, not a filesystem authority. The layout therefore
does not use a `DNA` directory.

### 2. Read-only preflight, direct-current repair

`audit_project_layout()` remains read-only. It calculates manifest and member
identities, rejects unsafe entries, and returns typed findings. Project
adoption calls it first. Repair is performed manually by the upgrade AI in a
separate owned worktree or source edit; no normal-runtime migration command,
fallback reader, alias, or dual manifest is introduced.

### 3. Identity propagation

The layout manifest fingerprint is an input to project adoption and the model
authority revision. Role/member changes invalidate only the affected current
identities, but any receipt bound to a changed identity is stale. A receipt
with equal result bytes is not reusable when its source or layout identity is
different.

### 4. Test strategy

Use temporary fixtures for every negative case in the specification. Each
fixture is hashed before and after audit to prove read-only behavior. Add
integration tests that assert layout failure is the first project-adoption
finding and that later authority checks are marked `not_run`. Keep test
fixtures and generated reports outside current authority roles.

### 5. Existing implementation ownership

The untracked `flowguard/project_layout.py` is treated as a shared draft until
its ownership is recorded in the coordination ledger. During that review,
other paths may be changed only by their explicit owner. Once the draft is
accepted as the current implementation, the owner records its source hash and
all subsequent edits are narrow, reviewed, and followed by layout tests.

## Rejected Alternatives

- A generic `migrate-layout` command: rejected because it would guess artifact
  meaning and create a long-lived compatibility surface.
- Reading old and new roots together: rejected because it creates dual
  authority and allows stale receipts to appear current.
- Naming the role root `DNA`: rejected because it hides distinct model,
  behavior, test, evidence, and history responsibilities from human readers.
- Treating a passing layout report as model or release proof: rejected because
  layout, model, execution, installation, Git, and release identities remain
  separate evidence surfaces.
