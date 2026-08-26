## Why

The provider-neutral blueprint qualifier now distinguishes static readiness from
executed readiness, but a whole-product DNA claim still needs explicit gates
for intent, runtime tests, real UI, external consumers, fault coverage,
platform/provider support, installation, incident backfeed, and release
identity. Without a single outer ledger, a caller can combine several narrow
green reports and accidentally present broad completion.

## What Changes

- Add one current typed DNA completion assessment with seventeen named layers,
  including independent observed-surface and bidirectional-traceability
  closure.
- Require one owner, input identity, terminal evidence identity, and claim
  boundary for every layer.
- Preserve failed, stale, skipped, not-run, not-applicable, self-reported, and
  unverified states as visible blockers; do not infer completion from status
  booleans or static model evidence.
- License `dna_complete` only for a broad assessment whose complete current
  layer set is terminal-success and whose input fingerprints match the frozen
  expected identities.

## Non-Goals

This change does not execute pytest, browsers, installers, external consumers,
platform matrices, or fault experiments. Those native owners must produce the
terminal artifacts consumed by this gate.
