## Why

FlowGuard currently makes a layout audit act like a full content-integrity audit: a routine project check expands a large member inventory, reads and hashes evidence and other runtime outputs, and serializes the result into a multi-megabyte manifest. The validation parent then repeats source, receipt, distribution, and model observations that should have been reused inside one frozen invocation. This makes ordinary use slow, token-heavy, and capable of accumulating evidence far beyond the governed project.

The new requirement is to preserve strict direct-current authority while separating layout shape, governed source currentness, proof identity, and evidence retention. The change is needed now because the current layout contract is already complete under its old rules, so the performance and storage correction must be an explicit current replacement rather than a hidden optimization or compatibility reader.

## What Changes

- **BREAKING** Replace the nine mandatory physical role directories with six allowed, on-demand semantic destinations: `behavior`, `models`, `structure`, `verification`, `evidence`, and exceptional `history`.
- **BREAKING** Replace the member-content layout manifest with a compact shape contract; layout no longer reads or hashes every evidence, history, work, projection, or governed member file.
- **BREAKING** Retire top-level `audits`, `projections`, and `work` as current roots. Route durable audit/projection proof into evidence or structure and keep transient work outside the project control plane.
- Add explicit `light`, `affected`, and `full` currentness profiles with typed `checks_run`, `checks_not_run`, `blocked`, and claim-boundary results.
- Make affected-owner derivation exact and fail-closed; an unmapped or ambiguous changed path blocks instead of expanding to a full run.
- Reuse one invocation-local source, receipt, release-tree, model-input, and physical-distribution observation across all owners in that invocation.
- Keep exact hashes at immutable publication, dirty-input, proof-consumption, installation/parity, and frozen-release boundaries; remove redundant repeated full-tree hashing.
- Change evidence retention to current-plus-pinned references with automatic disposal of unreachable runs and objects after a reference recheck.
- Bound successful output and terminal envelopes; keep complete streams only when a native owner explicitly requires them or a current failure is explicitly retained.
- Keep direct-current replacement: obsolete layout schemas, profiles, readers, aliases, migration commands, and fallback success paths remain blocked and are removed rather than dual-read.

## Capabilities

### New Capabilities

- `flowguard-currentness-profiles`: Defines the light, affected, and full profiles, their claim boundaries, exact affected mapping, shared observations, and measurable scan/hash budgets.

### Modified Capabilities

- `project-layout-contract`: Separates layout shape identity from governed content identity and makes physical roots optional.
- `authoritative-model-system`: Binds model authority to shape and explicitly governed inputs rather than every runtime output.
- `project-adoption-version-gate`: Adds light/affected/full adoption gates and direct-current rejection of obsolete layout schemas.
- `directory-first-dna`: Limits content identity to bounded authority members and removes the interpretation that every control-plane file needs a layout hash.
- `development-process-flow`: Requires invocation-local observation reuse, affected-only execution, and one frozen full gate.
- `flowguard-validation-evidence-lifecycle`: Adds current-plus-pinned retention, automatic unreachable cleanup, bounded successful streams, and one evidence catalog observation.
- `flowguard-evidence-receipts`: Keeps exact receipt/proof identity while allowing indexed reuse instead of per-owner store scans.
- `flowguard-model-regression-orchestration`: Replaces full pre/post repository hashing with Git-aware dirty-input mutation observation and affected model execution.
- `flowguard-skill-suite-distribution`: Reuses inventories by resolved physical root and policy within one invocation.

## Impact

- FlowGuard layout, adoption, project-audit, model-authority, validation-ownership, model-regression, distribution, evidence-lifecycle, CLI, and suite-orchestration code.
- FlowGuard layout, adoption, validation, model-regression, distribution, evidence, CLI, and full-suite tests.
- Current FlowGuard model authority, reverse-surface evidence, and final suite evidence must be rebuilt after the new layout/currentness contract is active.
- SkillGuard author-side current functional and release evidence must be revalidated after the FlowGuard source and contract identities settle; ordinary consumer skills are outside this change.
- No other project is upgraded, migrated, or cleaned by this change. No fallback reader, compatibility path, automatic migration command, or alternate authority is introduced.
