# FlowGuard / SkillGuard implementation baseline — 2026-08-18

This is a coordination baseline for the user-authorized implementation pass.
It is not a validation receipt and it does not make any source, model,
consumer, installation, Git, tag, or release claim current.

## Source boundaries

- FlowGuard source root: this repository (repository-relative paths only)
- FlowGuard observed `HEAD` at start: `a5901a17e614ed67b5e5cb3d92097f7e2d04379f`
- FlowGuard package/schema observed at start: `0.68.15` / `1.0`
- FlowGuard worktree contains pre-existing peer and user changes. Those paths
  remain owned by their existing authors; this pass does not reset, stash, or
  overwrite them.
- Protected peer paths include `flowguard/explorer.py` and
  `flowguard/model_revision_set.py`.
- A separate legacy SkillGuard checkout was dirty and was not an implementation
  target.
- The SkillGuard implementation target was a separate clean worktree, initially
  at v0.7.2 tag `c8b80c6906c0d290e443a40add070bf417c51d50`.

## Initial blockers

The initial FlowGuard `project-audit --json` was `blocked` because the stored
observed model inventory, source inventory, and owner-artifact identities were
stale against the live worktree. The audit reported no missing model IDs, but
that count is not current-authority proof.

The implementation therefore proceeds in phases: first make evidence and
reverse-surface checks independently verifiable, then freeze identities and
rebuild model/consumer/install evidence. No final broad claim is licensed by
this baseline.

## Required separation

SkillGuard remains author-side supervision. A normal graduated consumer must
not contain `.skillguard`, SkillGuard imports or commands, private receipts,
router/Portfolio state, or author-only identity fields. Consumer projection,
installation, registry, source, model, runtime, Git, tag, and publication are
separate claims and require separate current evidence.
