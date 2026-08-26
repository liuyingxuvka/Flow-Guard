# FlowGuard execution profiles and reusable branch seeds

FlowGuard has one semantic model and three execution depths. The profiles are
not three different implementations and they do not weaken a route's semantic
checks.

| Profile | Use | What it closes |
| --- | --- | --- |
| `light` | routine invocation, currentness, layout, and pointer checks | exact identity, shape, bounded metadata, and cheap route admission |
| `affected` | ordinary software changes | the exact declared member set and its model/test/evidence dependencies; it requires explicit members and never falls back to `light` or `full` |
| `full` | release, integration, or an explicitly requested whole-system proof | every declared owner, complete model regression, strict OpenSpec/currentness, installation/projection, and release-facing gates |

Every FlowGuard satellite entry can be run at one of these depths when the
route exposes that profile. A specialist trigger selects the semantic route;
it does not silently promote the invocation to `full`. A normal code change is
therefore usually `affected`, while a final release claim is explicitly
`full`. If a change reveals a missed behavior class, the next route is
`model-miss-review`; if the model or tests are too large, use ModelMesh or
TestMesh. Those routes remain mandatory in `affected` mode—the profile changes
the closure denominator, not the obligation types.

## Current layout boundary

The consumer `.flowguard` directory uses these role roots when they are
needed: `behavior`, `models`, `structure`, `verification`, `evidence`,
`audits`, `projections`, `history`, and `work`. Empty optional roots are not
created just to make the tree look complete. Current owner source and runners
have unambiguous paths:

```text
.flowguard/models/owners/<owner>/model.py
.flowguard/verification/owners/<owner>/run_checks.py
```

The layout audit checks the role shape and safe containment. It does not hash
every file on every routine invocation. A current manifest or model authority
may still use a content fingerprint where that particular authority requires
one; that is a targeted identity check, not a per-file layout tax.

## Storage and evidence lifecycle

`storage-audit` performs one guarded directory walk and reports counts, bytes,
a bounded largest-item sample, lifecycle classes, and reparse/outside-root
findings. It reads no payload and computes no content hash. The explicit
cleanup sequence is:

```text
storage-audit --root .flowguard
  -> evidence-audit --root .flowguard/evidence
  -> evidence-gc-plan [--storage-audit]
  -> evidence-gc-apply (one exact plan)
  -> evidence-gc-restore or evidence-gc-purge (one exact quarantine)
```

The sequence is opt-in. Current heads, pins, and active leases are protected;
an evidence audit or stale plan blocks before any move. No background cleanup,
automatic deletion, compatibility reader, or fallback path is added.

## Reusable branch knowledge

The public seed layer is compact branch guidance, not target truth. A seed is
valid only with all four layers, exact applicability predicates, protected
errors, states/effects, positive/known-bad/false-friend cases, target fields,
and current proof references. Risk-template search may recommend a candidate,
but it may not invent any of those fields. Candidate seeds stay unapplied;
only an explicit privacy review and proof-complete promotion can make a seed
selectable. A fuzzy match, unknown route, multiple exact matches, private
provenance, stale proof, or pending target closure blocks with zero applied
seeds.

The current public template routes are:

```text
python -m flowguard model-mesh-template
python -m flowguard contract-exhaustion-template
python -m flowguard reverse-surface-closure-template
```

They generate current nested model/runner paths and reuse the existing
ModelMesh, ContractExhaustion, and reverse-surface engines; they do not copy a
second engine into each project.

## Direct-current rule

Old model/layout/seed records are not automatically inherited. If identity or
schema no longer matches, FlowGuard blocks and the author updates the record
manually to the current form. There is no dual reader, migration command,
alias, silent downgrade, or compatibility fallback.
