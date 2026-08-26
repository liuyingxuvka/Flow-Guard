## 1. Typed claim envelope

- [x] 1.1 Define the seventeen canonical DNA layers and explicit non-pass states.
- [x] 1.2 Add typed layer evidence with owner, input identity, terminal proof,
  evidence kind, and claim boundary validation.
- [x] 1.3 Add exact reconciliation, missing/unexpected/duplicate detection,
  input identity checks, and broad-versus-scoped status projection.

## 2. Serialization and integration

- [x] 2.1 Add current-schema canonical serialization, fingerprint, load/write,
  and package API export.
- [x] 2.2 Keep the gate read-only over native artifacts and document that it
  cannot execute or manufacture target evidence.

## 3. Negative evidence

- [x] 3.1 Test static-only/not-run runtime evidence, fake UI booleans, source or
  model identity mismatch, not-applicable, and unreplayed miss backfeed.
- [x] 3.2 Test scoped claims and canonical round-trip.
- [x] 3.3 Add the typed native-owner input schema and pure assessment factory;
  require a frozen subject revision and make an omitted required expected input
  fingerprint a visible blocker. Add negative coverage for conflicting subject
  identities and contradictory passed-row gap fields.
- [x] 3.4 Harden clean-consumer path classification so a venv retained below
  an audit workspace is not mistaken for repository-source import; require the
  imported package to remain inside the venv and add path-boundary regression
  coverage.
- [x] 3.5 Keep the documented console scenario executable from a clean wheel by
  packaging its maintained example dependency, and make the external-consumer
  verifier require the command's native terminal summary rather than relying
  on `--help` or import-only smoke.

## 4. Native completion (parent-owned)

- [ ] 4.1 Populate the current assessment from real native owners for every
  required layer under one frozen source/model/toolchain/environment identity.
- [ ] 4.2 Run the external UI, clean-install consumer, platform/provider,
  fault-matrix, incident-backfeed, and release gates; retain not-run gaps.
- [ ] 4.3 Consume the assessment only after project-audit and current model
  authority are unblocked; do not reuse stale receipts or run `--resume` as an
  audit shortcut.
- [x] 4.4 Define and implement the mandatory human-readable `.flowguard`
  layout contract with explicit behavior, models, structure, verification,
  evidence, audits, projections, history, and work roles; retire ambiguous
  `DNA`/`dna_audit`/`tmp`/`run_artifacts` paths without compatibility aliases.
- [x] 4.5 Add a read-only `project-layout-audit` entry point and make project
  adoption stop before model-authority reads when the layout is missing,
  stale, unknown, colliding, or retired; allow bootstrap only for an empty
  target and create a descriptive non-authoritative README.
- [ ] 4.6 Directly rewrite FlowGuard's existing dirty control-plane tree into
  the current layout, with a per-artifact disposition and rebuilt current
  identities; do not implement a generic migration or fallback reader.

## 5. Independent evidence and reverse closure

Implementation gap recorded before the authenticity hardening pass (2026-08-18):
the current verifier already re-reads result and receipt files, but it still
accepted contradictory receipt status/terminal fields, treated a missing exit
code as sufficient, and hard-coded the executed runtime/contract owner instead
of comparing the receipt with the frozen execution owner. Reuse rows also only
checked that `reuse_identity` was non-empty; they did not prove that the
identity belonged to the current execution unit. These are real evidence gaps,
not reasons to widen the DNA layer inventory.

The current change specification subsequently added two required reverse
closure layers (`observed_implementation_surface_complete` and
`bidirectional_traceability_complete`); the original fifteen-layer code
surface was therefore an interface mismatch. The canonical gate, assembler,
and API export now use the resulting seventeen-layer set, while missing native
surface/trace receipts remain non-terminal.

- [x] 5.1 Verify every passed layer from a real producer receipt: open and
  rehash result artifacts, verify the receipt's canonical hash, owner,
  source/model/toolchain/environment identities, command/exit/terminal state,
  and descendant cleanup; reject fake hash prefixes, nonexistent paths, and
  self-licensed expected inputs.
- [x] 5.2 Require producer receipt id, receipt hash, and exact same-unit reuse
  identity for every reused runtime or contract leaf; add timeout cleanup and
  old-receipt-renaming negative cases.
- [x] 5.3 Add an independently discovered implementation-surface denominator
  for public API, exports, CLI/options, templates, configuration, files,
  side-effects, UI-like actions, and failure/recovery branches.
- [x] 5.4 Add bidirectional conservation: every discovered surface has one
  intent/model/owner/test/failure/recovery disposition and every model
  obligation maps back to a surface or typed model-only/retired/N/A proof;
  add mutation tests for unmodelled code/UI/API/CLI and orphan tests.
- [x] 5.4a Freeze producer receipt/source/model/toolchain/environment/result
  identities outside each evidence row and reject a proof artifact that only
  agrees with caller-authored values copied from itself. Older assessments
  without this current field require direct manual rewrite.
- [ ] 5.5 Do not mark the broad DNA claim complete until reverse-closure,
  receipt replay, runtime leaves, real UI or verified N/A, fault matrix,
  installation, and source/model authority are all current under one frozen
  identity.

## 6. Native owner closure sequence

- [ ] 6.1 Freeze the source, accepted model head, toolchain, environment,
  surface inventory, contract universe, UI-like action inventory, fault matrix,
  platform/provider matrix, installation matrix, observed-miss set, and release
  identity before any broad owner execution.
- [ ] 6.2 Produce one independently replayable terminal receipt for each
  required DNA layer; distinguish executed, exact same-unit reused, skipped,
  not-run, stale, blocked, and not-applicable states without collapsing them.
- [ ] 6.3 Verify real UI or a verifier-backed no-GUI disposition. Fixture-only
  browser strings, booleans, screenshots without runtime identity, and fake
  manual methods are non-terminal.
- [ ] 6.4 Execute the finite contract/fault/recovery matrix against the native
  target, collecting root cause, user-visible result, terminal effect, and
  recovery outcome for each required case.
- [ ] 6.5 Reconcile clean external consumer, installation/rollback/recovery,
  platform/provider, observed-miss backfeed, and release identities as
  separate claim lanes; one lane's receipt must never authorize another.
- [ ] 6.6 After every source/model/owner change, invalidate affected receipts,
  rebuild the owner plan, and run one final full owner only after all affected
  lanes are current.
