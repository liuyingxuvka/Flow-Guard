## 1. Authority and coordination

- [x] 1.1 Verify the archived `human-readable-flowguard-layout` change, current FlowGuard and SkillGuard worktree identities, dirty paths, and zero active validation descendants.
- [x] 1.2 Freeze the exact FlowGuard implementation/test allowlist and keep unrelated user or peer dirty files out of edits and staging.
- [x] 1.3 Run strict OpenSpec validation for this change and confirm there is no competing active layout/currentness authority.

## 2. Observation telemetry

- [x] 2.1 Add invocation-local counters for layout walks, observed files, content hashes, bytes hashed, source observations, release-tree builds, Git hash-object calls, receipt scans/parses, owner-current builds, distribution inventories, evidence catalog walks, and phase elapsed time.
- [x] 2.2 Add tests that assert telemetry reflects real existing operations without triggering extra scans or changing pass/fail decisions.
- [x] 2.3 Record a pre-change baseline for layout size/lines/member rows and light/affected/full scan counts without changing current authority. The v2 report's absent counters/profile boundary is recorded explicitly in `performance-baseline.md`; no synthetic zero is introduced.

## 3. Compact layout shape

- [x] 3.1 Implement one-pass `LayoutObservation` and remove member-content reads from layout identity calculation.
- [x] 3.2 Implement six allowed on-demand destinations and route audits, projections, and transient work to their new destinations.
- [x] 3.3 Remove the nine-empty-root requirement and reject top-level retired roots, ambiguous DNA names, caches, bytecode, and reparse points.
- [x] 3.4 Make the current layout writer emit a compact v3 shape contract with no `inventory.members` or member content fingerprints.
- [x] 3.5 Make obsolete v2 layout input fail visibly without a compatibility reader, alias, or migration command.
- [x] 3.6 Add layout/adoption tests for optional roots, evidence opacity, path/role conservation, unsafe entries, duplicate-byte non-collision, bounded manifest size, one walker, and zero layout content hashes.

## 4. Currentness profiles and pointers

- [x] 4.1 Add the public `light`, `affected`, and `full` profiles with typed checks-run/not-run, blocked, and claim-boundary output.
- [x] 4.2 Implement exact changed-path to component/owner mapping and block unmapped or ambiguous paths before any owner executes.
- [x] 4.3 Make light validation read only shape/adoption/head controls and never claim live model, validation, or release currentness.
- [x] 4.4 Add an O(1) current parent/head index so current lookup does not scan historical receipt JSON files.
- [x] 4.5 Remove the old public static compatibility route while retaining internal ownership labels only where they are not public profiles.

## 5. Shared validation observation

- [x] 5.1 Extend the invocation observation with source manifest, receipt index, release-tree identity, external inventories, and metrics.
- [x] 5.2 Make owner planning, reuse, execution, publication, and parent composition project from the same frozen observation.
- [x] 5.3 Make parent currentness a pure frozen-plan projection and add a separate final freshness assertion.
- [x] 5.4 Remove per-owner receipt-store scans and duplicate source/release manifest construction.
- [x] 5.5 Add negative tests for source/receipt drift during execution and positive tests for one observation, zero per-owner scans, and one final reconciliation.

## 6. Distribution and model de-duplication

- [x] 6.1 Cache distribution inventories by resolved physical root plus member-policy identity within one invocation.
- [x] 6.2 Make distribution and parity owners consume the shared inventory and perform one final exact freshness check.
- [x] 6.3 Build one unique model-input catalog and pass computed identities into model instance and regression builders without rereading the same path.
- [x] 6.4 Restrict affected model audit to exact affected owners and preserve full 51-owner live observation only for full profile.
- [x] 6.5 Replace regression pre/post whole-repository hashing with Git status/index identity plus exact dirty/untracked hashes; block non-Git without a finite mutation boundary.
- [x] 6.6 Add tests for shared inputs, affected-only execution, Git mutation transitions, ignored evidence outputs, non-Git blocking, and reused-only no-full-snapshot behavior.

## 7. Evidence lifecycle and storage

- [x] 7.1 Implement one evidence catalog observation that supplies heads, pins, runs, objects, sizes, and lifecycle classes.
- [x] 7.2 Bound successful stdout/stderr capture and compute payload/manifest hashes once from exact serialized bytes.
- [x] 7.3 Use one evidence-root content-addressed object store with reference tracking and no per-run duplicate objects.
- [x] 7.4 After terminal publication, quarantine and purge only unreachable unpinned/unleased candidates after a same-operation reference replay.
- [x] 7.5 Preserve current, pinned, active-lease, and explicitly retained failure evidence; block deletion on changed plans, reparse points, outside-root paths, or active processes.
- [x] 7.6 Add evidence lifecycle tests for current/pinned protection, collectible cleanup, stale-plan refusal, object references, bounded output, and one catalog walk.

## 8. Compact artifacts and AI output

- [x] 8.1 Add compact summaries and artifact references for reverse discovery, model snapshots, receipt inventories, and full child payloads.
- [x] 8.2 Bound terminal envelopes to the agreed size and expose only counts, bounded findings, omitted counts, and artifact identities.
- [x] 8.3 Add deterministic pagination/slice retrieval for large machine artifacts without creating a second current authority.

## 9. Targeted verification and authority rebuild

- [x] 9.1 Run layout, adoption, validation ownership, full composition, distribution, model regression, model authority, evidence, CLI, affected-blocker, and OpenSpec tests in the prescribed narrow-to-wide order.
- [x] 9.2 Directly rewrite FlowGuard's own current layout and dispose old paths using the new v3 rules; do not upgrade another project.
- [x] 9.3 Create a new model snapshot, accepted revision set, activation receipt, and current head for the new layout/currentness identity.
- [x] 9.4 Rebuild reverse discovery and semantic closure from the new frozen denominator; require zero blocked gaps, zero unmapped/orphan obligations, zero unmodeled UI actions, zero ambiguous/unknown calls, and an exact new-generation join.
- [x] 9.5 Replace the stale hard-coded reverse-audit denominator text with a current/dynamic denominator description.
- [x] 9.6 Record performance and storage acceptance counters and require member-content layout hash count zero, one layout walk, affected-only exactness, shared full observations, bounded terminal output, and zero collectible bytes after postflight.

## 10. Final FlowGuard and SkillGuard validation

- [x] 10.1 Freeze final source, toolchain, OpenSpec, model-head, owner-plan, and distribution-root identities and run exactly one new FlowGuard full suite. The final local owner `v0.68.15-final11` is recorded as 10/10 passed with the cleanup-release gate passing.
- [x] 10.2 Require every FlowGuard owner to have a terminal disposition, no failed/blocked/not-run owner, and one parent receipt bound to the frozen inputs.
- [x] 10.3 Reissue SkillGuard current functional capability evidence against the current 24-obligation/1,968-surface inventory and current compiled contract.
- [x] 10.4 Reuse or rerun SkillGuard's 23-owner TestMesh only after exact source/contract/inventory identity comparison.
- [ ] 10.5 Complete SkillGuard real-E2E lifecycle, deterministic quality, release capability, consumer distribution/install/parity, and Windows/Linux CI evidence; stop at local release-candidate status if external publication is not authorized.
- [x] 10.6 Verify this change against all specs, leave no obsolete reader/profile/fallback residual, and only archive/commit/push/tag/release after separate user authorization and exact allowlist staging.

## Current acceptance boundary

The local implementation, compact-layout/currentness work, SkillGuard projection,
and reverse-closure work are complete for the authorized local release candidate.
The final FlowGuard parent is `pass` with 10/10 required owners passed, no failed,
blocked, or not-run owner, and one frozen parent receipt. The local SkillGuard
functional checks and formal/shadow/installed parity are also passing. The reverse
surface audit is current and complete: 15,024 discovered observations, 15,024 mapped
observations, 25 model obligations, zero unmapped/orphan/duplicate/UI-like findings,
and `reverse_closure_complete=true`.

Task 10.5 remains intentionally open only for external real-E2E, Windows/Linux CI,
and public release evidence, which was not authorized in this run. No fallback,
compatibility reader, alias, or automatic upgrade path was added. No archive,
commit, push, tag, or release action was performed; those remain separate
authorization gates.
