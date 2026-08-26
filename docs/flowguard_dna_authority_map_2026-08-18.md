# FlowGuard DNA audit authority map — 2026-08-18

This map is the integration boundary for the DNA audit. It assigns every
remaining OpenSpec surface to one current owner and records whether the work
can be closed from this checkout. It is deliberately not a replacement for a
native execution receipt, model authority, or release identity.

## Current frozen facts

- Repository: `FlowGuard_20260427`
- HEAD: `a5901a17e614ed67b5e5cb3d92097f7e2d04379f`
- Package: `flowguard 0.68.15`
- Schema: `1.0`
- Python: `3.12.10`
- Platform: Windows 11
- `project-audit`: `blocked`
- Blocking authority findings: `model_authority_invalid`,
  `observed_model_inventory_stale`, `observed_source_inventory_stale`, and
  `observed_owner_artifacts_stale`.
- The latest project audit no longer reports an unowned governed module after
  registering `behavior_surface_audit.py` and `contract_runtime_evidence.py`;
  it remains blocked solely because the accepted model/source/owner authority
  snapshot is stale relative to the dirty worktree.
- Peer-owned dirty paths preserved without reset, stash, checkout, format, or
  overwrite: `flowguard/explorer.py` and `flowguard/model_revision_set.py`.
- Final local audit snapshot after the reverse-closure and UI-proof hardening
  edits: dirty-path listing hash
  `sha256:3eb702b98cdf73dde30f2a3cf8baf281697e567b343f92084d378ffafcc6e84a`
  over 55 paths. This is an audit identity only; it is not an accepted model
  authority or release identity.
- The repository-local focused-test receipt is stale to the final proof-gate
  edits and cannot be reused.  The latest affected-test counts were run as a
  scoped diagnostic only (`167 passed, 2 skipped, 38 subtests`); no current
  immutable native producer receipt is claimed here.
- The current clean-consumer candidate is outside the repository: wheel
  `sha256:fd25adc33aa0007eaa461c31cf840afde44ff507057b2b962c50a1f132c92475`
  with evidence fingerprint
  `sha256:63401bf298997ac1e5cb9195022000ae2f0a532724bda455f57217644a4b7711`.
  It is scoped smoke evidence, not an approved release or DNA receipt.
- The current reverse source observation report (outside the repository,
  because it contains the full sharded denominator) is
  `sha256:a3aa088ce494fea0b92acbf6c01886b71120b91be693dbb274fcf55ee1d4cff6`
  and remains `blocked` with 14,717 discovered rows and 3,283 source-observation findings.

The current clean-consumer receipt is still a candidate scoped to the dirty
worktree, but it now includes a real installed-wheel `scenario-review` run
(exit code `0`, native `status: OK`). The packaging boundary was corrected to
include the maintained `examples*` packages; an earlier clean-wheel run had
exposed `ModuleNotFoundError: No module named 'examples'` even though
`--help` and import-only smoke were green.

## Change ownership

| OpenSpec change | Current owner | Status | Boundary |
|---|---|---|---|
| `layer-dna-qualification-evidence-gates` | `flowguard.target_system_blueprint` / `flowguard.software_blueprint_readiness` | complete | Static qualification is separate from runtime qualification. |
| `dna-completion-layer-gate` | `flowguard.dna_completion_gate` plus one native owner per layer | parent-owned remainder | The gate is implemented; rows 4.1–4.3 require current native evidence and cannot be closed by this assembler. |
| `independent-behavior-denominator` | `flowguard.behavior_commitment` plus native discovery owner | partially implemented | The materializer and conservation rules exist; the current manifest is still a scoped infrastructure subset. |
| `harden-currentness-validation-execution` | `flowguard.development_process_flow` / `flowguard.test_mesh` | active | Tasks 11.3–12.7 require a frozen authority, one full owner, clean projections, and release identity. |
| `close-provider-neutral-dna-and-self-mesh` | SkillGuard author owner, then ResearchGuard/PhysicsGuard/WorldGuard consumers | external handoff | Tasks 5.3–5.4 are not FlowGuard self-audit evidence and must not be simulated locally. |
| `repair-consumer-authority-v06814` | retired historical release lane | obsolete/superseded | Its target was 0.68.14; current package/adoption identity is 0.68.15. Do not execute its version bump, tag, or release tasks. |

## Layer owner map

| DNA layer | Native owner | Required current artifact |
|---|---|---|
| static blueprint | `flowguard.target_system_blueprint` | current self-blueprint qualification receipt |
| semantic model | `flowguard.model_revision_set` | accepted current model head and effective intent view |
| intent inventory | `flowguard.behavior_commitment` + discovery owner | independent manifest reconciliation |
| behavior binding | `flowguard.behavior_commitment` | one row per behavior with owner and disposition |
| code binding | `flowguard.model_test_alignment` | function/state/transition/code-owner reconciliation |
| static test binding | `flowguard.test_mesh` | static inventory and exact test obligations |
| runtime test execution | native test execution owner | concrete pytest leaf receipt |
| contract universe | `flowguard.contract_exhaustion` | finite dimensions, cases, oracles, exclusions, and coverage receipt |
| real UI surface | `flowguard.ui_structure` plus target UI owner | browser/desktop/manual proof artifacts |
| external consumer | clean consumer owner | non-editable package and public scenario receipt |
| fault matrix | native fault owner | isolated fault/recovery campaign receipt |
| platform/provider | native platform owner | declared support matrix with terminal rows |
| installation | native installation owner | install/upgrade/rollback matrix |
| observed miss backfeed | `flowguard.model_miss_review` | incident-to-model-to-replay closure receipt |
| release identity | release owner | frozen source/toolchain/CI/tag/release comparison |

The public-surface audit currently observes 5,091 declared Python names
(2,942 public `__all__` names and 2,867 unique registry names), 40 literal CLI
parser declarations, 27 template command declarations, and one console
script. These declarations are deliberately kept as a blocked gap report
rather than converted into semantic behavior rows; the four-row manifest
remains a scoped evidence-infrastructure denominator. The independent
source-only reverse observation has now been sharded across 303 files and
merged into 14,717 surface rows with 28,917 local call-graph edges. It is
current as an observation (`stale_fingerprint=0`) but blocked by 3,283
ambiguous call targets, 2,130 unbound/unreachable candidates, and the absence
of an independently authored semantic map. The ContractExhaustion runtime
adapter is likewise only a case-level reconciliation boundary: a native
runner must supply executed/reused rows and receipts.

## Rules for the next execution owner

1. Do not mark an OpenSpec task complete because a schema, fixture, or action
   list exists. The task needs the exact native artifact named by its owner.
2. Do not use the obsolete 0.68.14 change as a shortcut for current 0.68.15
   release work. If a release is later authorized, create a new current
   release change with a new identity.
3. Do not repair the observed model pointer while the peer-owned model files
   are unclaimed. Freeze ownership first, then use the repository's atomic
   authority rebuild route once.
4. A scoped evidence row can prove only its declared scope. It cannot close a
   sibling layer or widen the whole-product claim.
5. A missing external target is a visible `blocked` or explicit
   `not_applicable` decision, never a silently omitted row.
6. Run clean-consumer venvs outside the repository. A retained venv below the
   repository is itself discovered as governed Python input and contaminates
   project currentness with thousands of unowned package files.

## Current completion boundary

The local implementation currently proves the evidence infrastructure and a
bounded clean-consumer slice. It does not license a whole-product DNA claim.
The next owner must consume this map together with
`docs/flowguard_dna_audit_action_list_2026-08-18.md`, repair authority under a
frozen identity, and attach the native layer receipts before changing the
outer assessment.
