# Layout/currentness performance baseline

This file records the exact baseline that was available for the direct-current
layout replacement. It is evidence for the change plan only; it is not a model
authority, a validation receipt, or a release claim.

## Pre-change v2 observation

Source artifact:

`.flowguard/history/retired-layout-v2-20260824-1/audits/project-layout-audit-current-r7.json`

The archived report declares `flowguard.project_layout.v2` and contains:

- `observed_entries`: 17,775;
- immutable execution evidence entries: 16,847;
- transient work-product entries: 59;
- a member-oriented observed-entry list, including the old `audits/`,
  `projections/`, and `work/` roots;
- no invocation counters for directory walks, member reads, bytes hashed, or
  profile-specific scans.

The last point is deliberately recorded as **not instrumented**, not as zero.
The old implementation did not expose a trustworthy pre-change hash/read
counter, so this baseline does not invent one. The v2 contract also had no
public `light`, `affected`, or `full` profile, so profile-specific pre-change
counts are **not applicable**, rather than silently treated as passed or zero.

## Current v3 observation

Command:

```text
python -B -m flowguard project-layout-audit --root . --json
```

Current report facts (2026-08-25):

- layout schema: `flowguard.project_layout.v3`;
- observed entries: 889;
- observed files: 749;
- shape entries: 885;
- directory walks: 1;
- member-content hash reads: 0;
- layout manifest pointer read/hash: 1 small `layout.toml` read;
- content bytes read for that pointer: 134,177;
- findings/blockers: 0;
- current inventory fingerprint:
  `sha256:e08a15bae541f5827e513c226377efd607af3658323474fc0a4346cbccfd0800`;
- current layout-manifest fingerprint:
  `sha256:aff2d8f857481ca0a3a3e5f37ef42b8b13d24172fd91f00fb80b688d618df695`.

The `layout.toml` pointer hash is not a member-content scan. Governed source,
model, receipt, installation, and publication identities retain their own
exact checks at their owning boundaries; layout does not repeat those checks.

## Acceptance interpretation

The directly comparable shape denominator fell from 17,775 v2 observed entries
to 889 v3 observed entries, while the current layout operation performs one
shape walk and zero member-content hashes. The old profile counters remain
unavailable because v2 never had those profiles; future comparisons must use
the v3 invocation counters instead of reconstructing a synthetic v2 number.
