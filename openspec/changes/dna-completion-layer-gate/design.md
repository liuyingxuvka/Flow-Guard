## Design

`DnaCompletionAssessment` is the outer claim envelope. It contains the frozen
required layer set, the target and subject identities, expected input
fingerprints, and one `DnaCompletionLayerEvidence` row per observed layer.
`review_dna_completion` performs exact row reconciliation and derives the
status; it never runs a target or creates model authority.

The canonical layers are static blueprint, semantic model, intent inventory,
observed implementation surface, bidirectional traceability, behavior binding,
code binding, static test binding, runtime test execution, contract universe,
real UI surface, external consumer, fault matrix, platform/provider,
installation, observed-miss backfeed, and release identity.

A layer with `passed` must carry a native owner, non-empty input identity,
terminal evidence id, `sha256:` evidence fingerprint, evidence kind, and claim
boundary. A caller-authored, boolean-only, progress-only, stale, skipped,
not-run, or unverified row is retained but cannot satisfy a required layer.
`not_applicable` requires a reason and remains non-success when the layer is in
the required broad set.

Native owners enter the gate through `DnaCompletionNativeOwnerInput`, which
requires the frozen assessment `subject_revision` in addition to the
layer-specific input fingerprint. `DnaCompletionAssessment.from_native_owner_inputs`
is a pure normalization path; it does not run an owner or create evidence.
Review also requires an expected input fingerprint for every required layer.
Missing expected identity is a typed blocker, not a wildcard match.

For every terminal-success layer, the assessment also freezes the independent
producer identity (`owner_id`, evidence/receipt ids and fingerprints, source,
model, toolchain, environment, and result).  The proof artifact is compared
against that frozen map; values copied from the artifact cannot become their
own expected identity.  An older assessment without this field is not read as
compatible current input and must be manually rewritten under the current
schema.

The external-owner layer set is provider-neutral and deliberately contains no
fixed owner ids. The local assembler may record `blocked`, `not_run`, `stale`,
`unverified`, or reasoned `not_applicable` rows for those layers, but only the
target-owned UI, consumer, fault, platform, installation, miss-backfeed, and
release owners can provide the terminal receipts needed to close them.

The existing provider-neutral qualifier remains a lower-level static/runtime
projection. This gate is the only new owner of the aggregate whole-target
`dna_complete` claim; it consumes evidence from native owners and does not
duplicate their semantics.
