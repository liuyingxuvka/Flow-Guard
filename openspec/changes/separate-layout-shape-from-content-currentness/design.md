## Context

The previous layout implementation stores a large per-member inventory and hashes current-role files, including runtime evidence. The validation stack already has partial observation/reuse primitives, but project adoption, model authority, distribution parity, regression mutation guards, and evidence lifecycle each rebuild overlapping observations. The current repository is Git-backed and uses one observed model head; direct-current replacement and fail-closed authority are mandatory. See `proposal.md` and the delta specs for the externally visible contract.

## Goals / Non-Goals

**Goals:**

- Make layout a compact, one-pass shape observation with optional semantic roots.
- Separate layout shape identity, governed source identity, receipt/proof identity, and evidence reachability.
- Provide light, affected, and full profiles with explicit claim boundaries and no affected-to-full fallback.
- Reuse one invocation-local observation for source paths, receipt index, release tree, model inputs, and physical distribution roots.
- Keep exact integrity checks at immutable publication, dirty-input, proof-consumption, installation/parity, and frozen-release boundaries.
- Automatically dispose unreachable evidence after current/pin/lease replay while preserving current and pinned material.
- Return bounded terminal output and store complete machine detail behind one referenced artifact.

**Non-Goals:**

- No upgrade of any repository other than the FlowGuard and SkillGuard author workspaces in scope.
- No compatibility reader, dual manifest, alias, migration command, stale-cache fallback, or alternate current authority.
- No change to the semantic meaning of FlowGuard model obligations, reverse-surface closure, or SkillGuard target-owned domain checks.
- No automatic Git commit, push, tag, release, or remote CI dispatch.

## Decisions

### 1. Keep a compact shape contract, not a member-content manifest

`layout.toml` remains the human/machine entry point but contains schema, allowed destinations, routing rules, and safety policy only. The runtime builds one `LayoutObservation` containing normalized paths, roles, kinds, and reparse/cache findings. A small shape digest may cover canonical path/kind strings; no member bytes are read for layout identity. Evidence and exceptional history are opaque after root safety checks.

Alternative rejected: retaining a full member inventory and optimizing its hashing. That would preserve the wrong authority boundary and continue to serialize runtime output into the layout contract.

### 2. Use six allowed destinations and create them on demand

The current roots are `behavior`, `models`, `structure`, `verification`, `evidence`, and optional `history`. `audits` routes to `evidence/audits`, projection definitions to `structure/projections`, distribution proof to `evidence/installations`, and transient work to an OS temporary directory. Empty roots are absent rather than created. Obsolete v2 layouts are blocked and manually rewritten by the upgrade AI; no product reader or converter is added.

Alternative rejected: preserving nine mandatory empty roots. It keeps the user-visible clutter and makes layout presence, rather than actual project content, a false requirement.

### 3. Freeze one observation per invocation

Introduce invocation-local observations with explicit counters:

- source manifest and changed-path set;
- receipt inventory/index;
- release-tree identity;
- model input catalog;
- resolved physical distribution inventories;
- evidence catalog for explicit lifecycle operations.

Owner currentness and parent identities are projections of these observations. Cross-invocation reuse is allowed only through an immutable exact terminal receipt with matching unit, owner, request, inputs, dependencies, toolchain, environment, and claim boundary.

Alternative rejected: a persistent “fast cache” keyed only by mtime/size or a copied current flag. Such a cache would become an alternate authority and would hide source drift.

### 4. Make profile boundaries public and typed

`light` performs shape/adoption/head checks only; `affected` maps exact changed paths to a bounded owner closure and blocks unknown mappings; `full` freezes all required observations and publishes one parent receipt. Internal check owner names may remain for ownership accounting, but the old public static scope is not retained as a compatibility alias.

### 5. Use Git identity for clean tracked preimages

Release-tree and mutation guards use Git index/tree identity for unchanged tracked paths. Only dirty and untracked governed paths are read and hashed. A non-Git full mutation proof without a caller-declared finite boundary blocks visibly. This preserves exactness without a second full repository byte snapshot.

### 6. Make evidence reachability the retention authority

Publication writes the run manifest/result and updates the current head before lifecycle classification. A single evidence catalog builds current, pinned, active-lease, collectible, legacy, and invalid sets. Unreachable runs are quarantined, references are replayed, and the exact quarantine is purged in the same lifecycle operation. Current, pinned, and active-lease evidence is never deleted. Complete streams are retained only for explicit native evidence requirements or current failure debugging; successful default output is bounded.

### 7. Bound terminal projections

Routine results contain status, profile, claim boundary, counters, elapsed phases, affected/executed/reused counts, the first bounded findings, and an omitted count. Full inventories, child streams, and large reverse maps remain machine artifacts referenced by identity and lifecycle-managed like other evidence.

## Risks / Trade-offs

- [Risk] A shape-only layout audit could miss a semantic role error. → Keep native model, behavior, validation, distribution, and evidence owner checks responsible for semantic ownership; retain typed path/role violations in layout.
- [Risk] Optional roots could hide a missing required artifact. → Required artifacts remain declared by the owning model/check contract; layout only stops requiring empty directories.
- [Risk] Observation reuse could accept a source change during execution. → Freeze inputs before producers, run one final exact freshness reconciliation, and publish no parent on drift.
- [Risk] Automatic cleanup could delete useful diagnostics. → Preserve current, pinned, and active-lease evidence; require explicit pin for long-term debug retention; replay references before purge.
- [Risk] Replacing the old layout breaks existing projects. → Fail visibly on obsolete schema and require direct manual/AI rewrite; do not add a compatibility reader or silent migration.
- [Risk] Full profile remains expensive. → Keep it explicit, measure scan/hash counts, reuse all invocation-local observations, and reserve it for frozen integration/release boundaries.
