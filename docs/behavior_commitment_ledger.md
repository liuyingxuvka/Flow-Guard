# FlowGuard Behavior Commitment Ledger

Behavior Commitment Ledger is the full behavior account book for a project,
work package, or release boundary.

In plain language: before an AI says a feature, project, release, UI flow, CLI
command, skill, or workflow is covered, the ledger asks, "What exact external
behaviors are promised, where did those promises come from, and which model is
the one primary owner for each one?"

## What Counts As A Commitment

A commitment is an external, verifiable promise. Examples:

- a public API or CLI command behavior;
- a UI capability users can perform;
- a documented workflow;
- a skill or agent workflow behavior;
- a release, archive, publish, or process behavior that downstream work relies on.

A commitment is not every helper function, private class, implementation file,
internal field, or model. A model proves a commitment; it is not automatically
the whole feature inventory.

The ledger is also not a user-account, persona, or permission catalog for the
target software. Product roles such as administrator, operator, customer, or
service account belong in that software's own behavior model. The ledger only
registers the externally verifiable promise and its one primary model owner.

The read-only understanding-status API and CLI are therefore registered as one
FlowGuard product promise, not as new target-software roles and not as an
activity log. Its two public surfaces share one intent and one model owner.

## Execution Plane And Actor

Every production commitment is classified exactly once by who owns the
behavior:

| `behavior_plane` | Plain meaning | Typical `actor_kind` |
| --- | --- | --- |
| `product_runtime` | The application promises an external result. | `end_user`, `external_system`, `application` |
| `agent_operation` | The current AI agent operates tools to complete work. | `ai_agent` |
| `development_process` | Development, validation, installation, archive, publish, or release is governed. | `developer`, `automation` |

`commitment_kind` still describes the form (`ui`, `cli`, `workflow`, and so
on); it does not answer who owns the behavior. Product software that itself
contains an AI feature remains `product_runtime`. `agent_operation` is for the
Codex/development agent operating the project.

## Change Modes

Before editing or claiming behavior coverage, classify the ledger work:

- `bootstrap_ledger`: no baseline ledger exists, so the AI investigates README,
  docs, API/CLI, skills, templates, spec-tool records, issues, changelog, and
  historical traces.
- `add_behavior`: a new external behavior is added.
- `change_behavior`: an existing behavior changes.
- `remove_or_replace_behavior`: old behavior is removed, deprecated, or
  replaced; no old or alternate surface is left as a second success path.
- `coverage_gap_backfill`: a historical external behavior was visible but not
  registered.
- `model_miss_check`: a runtime/test/replay/manual failure after a green claim
  triggers a check for missing or stale behavior registration.

## Canonical Ledger And Relations

The project source of truth is the machine-readable
`.flowguard/behavior/inventory/ledger.json`. Its model owner is the separate
`.flowguard/models/owners/behavior_commitment_ledger/model.py`, and its native
verification owner is
`.flowguard/verification/owners/behavior_commitment_ledger/run_checks.py`.
Run outputs and receipts belong under the evidence/work roots; they are not
adjacent siblings and never become a second behavior inventory. Use
`load_behavior_commitment_ledger()`, `write_behavior_commitment_ledger()`, and
`behavior_commitment_ledger_fingerprint()` at tool boundaries.

The bundled public template emits the complete current canonical envelope.
The current loader rejects omitted default fields instead of filling them as a
compatibility path; update a producer directly whenever the current shape
changes.

Commitments connect through typed `BehaviorCommitmentRelation` rows:
`depends_on`, `invokes`, `validates`, `governs`, or
`requires_evidence_from`. Cross-plane relations need a reason and never move
the target commitment into the source plane. Legacy
`dependency_commitment_ids` is diagnostic evidence of a stale producer only;
it is never materialized by FlowGuard and never becomes a current relation.
The maintaining agent must author the current typed relations directly, then
rerun model, test, and receipt validation under the new identity.

## What The Ledger Checks

The ledger checks both directions:

- every in-scope source surface maps to one or more commitments;
- every in-scope commitment maps back to source evidence or source surfaces.

It also checks:

- missing expected commitments;
- extra invented commitments with no source;
- changed, missing, or unchecked source surfaces;
- one primary owner model per commitment;
- stale owner-model/sibling/child-model review;
- replaced or deprecated behavior without disposition;
- TestMesh shards that are stale, missing, progress-only, or release-only;
- model-miss backfeed that does not map to an existing commitment, owner model,
  and same-class/DCAR coverage;
- supporting or child models that accidentally overlap the primary owner;
- unknown relation targets, invalid relation types, disallowed cross-plane
  relations, or cross-plane relations without a rationale;
- scoped-out behavior without owner, reason, validation boundary, and rationale;
- broad claims without current evidence or risk gates.

The same exact external intent has one stable `business_intent_id` and one
active commitment. Surface shape is not identity: a page button, menu item,
API, CLI, alias, adapter, wrapper, or compatibility facade maps to the same
commitment when actor, preconditions, expected terminal, failure boundary,
material state writes, and side effects are the same. A separate intent needs
a typed external difference, owner, validation boundary, rationale, and
current evidence. A thin delegating surface never receives a second
"delegate commitment."

## Lookup Binding And Read-Only Query

`BehaviorLookupBinding` stores bounded recall clues: task terms, path patterns,
tool ids, error signatures, and workflow families. Lookup selects one primary
plane before scoring. Only same-plane hits can guide the current operation;
typed related hits are shown separately as invoked targets, validation targets,
governing processes, or evidence sources.

```powershell
python -m flowguard behavior-commitment-query "start the UI test and check the port bridge" --root . --plane agent_operation --term port_bridge --json
```

The output includes deterministic match reasons, relation roles, ambiguity or
fallback status, and the canonical ledger fingerprint. This is explainable
recall, not a runtime supervisor: it does not execute commitments, force every
ordinary action through FlowGuard, or guarantee future AI compliance.

## How It Connects To Primary Path Authority

The ledger is upstream. Primary Path Authority is downstream.

Use this rule:

```text
Behavior Commitment Ledger
-> path_sensitive=true commitment
-> Primary Path Authority
-> no automatic A failed -> B succeeded path
-> TestMesh shards + Risk Evidence Ledger gates
```

The ledger should not recreate alternate-path detection. If a behavior is
path-sensitive, attach PPA evidence with
`behavior_path_binding_from_primary_path_report()`. If PPA blocks, the ledger
blocks that commitment and any broad claim depending on it.

The current runtime binding accepts and emits only one `primary_path_id`.
Retired `primary_path_ids` is never a runtime input or compatibility alias.
Historical BCL producer shapes are inspected only to explain why the current
artifact is blocked. FlowGuard never materializes an old value, rewrites the
file, or treats a deterministic candidate as current. The maintaining agent
must directly author the singular current field and supply fresh model, test,
owner, and receipt evidence; any missing or ambiguous value remains blocked.

## Public API Shape

Core objects:

- `BehaviorCommitmentLedger`
- `BehaviorSourceSurface`
- `BehaviorCommitment`
- `BehaviorEvidenceBinding`
- `BehaviorExternalDifference`
- `BehaviorLookupBinding`
- `BehaviorCommitmentRelation`
- `BehaviorPathAuthorityBinding`
- `BehaviorLookupQuery`
- `BehaviorCommitmentHit`
- `BehaviorLookupReport`
- `review_behavior_commitment_ledger()`
- `query_behavior_commitments()`
- `query_behavior_commitments_from_path()`
- `load_behavior_commitment_ledger()`
- `write_behavior_commitment_ledger()`
- `behavior_path_binding_from_primary_path_report()`
- `behavior_commitment_contract_exhaustion_plan()`

Template:

```powershell
python -m flowguard behavior-commitment-ledger-template --output <target>
```

## Broad Claim Rule

For done, release, publish, archive, production, or full-confidence claims, use
current ledger evidence plus downstream evidence:

- ContractExhaustionMesh commitment coverage cases;
- TestMesh child shard ownership;
- Model-Test Alignment bindings to model obligations, code contracts, tests,
  and commitment ids;
- Risk Evidence Ledger gates;
- PPA evidence for every `path_sensitive=true` commitment.

If the ledger says behavior is missing, extra, overlapping, stale, or
PPA-blocked, repair the root commitment, owner model, evidence, or primary
path. Do not add a second runtime path as a workaround.

## Model Miss Backfeed

A model miss does not automatically mean a new feature exists. First classify
which execution plane's promise failed, then search that plane for an existing
commitment and owner model. If the commitment exists, repair the model, code
contract, tests, evidence, lookup error signatures, and DCAR/same-class
coverage under that commitment. Create or backfill a gap only when the
external behavior was never registered in the affected plane. Other planes
remain typed incident context and do not take over ownership.
