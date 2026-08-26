## 1. Authority and scope

- [x] 1.1 Record one owner for the untracked `project_layout.py` draft and
  freeze its reviewed source hash before editing it.
- [x] 1.2 Record FlowGuard source, model, installed, Git, tag, and receipt
  identities separately; mark stale observations as historical inputs.
- [x] 1.3 Confirm this change is the sole current layout authority and that no
  superseded change is used by runtime readers.

## 2. Contract artifacts

- [x] 2.1 Implement the nine-role current layout manifest and member inventory.
- [x] 2.2 Bind project identity, model authority pointer, role fingerprints,
  and non-authority declarations for history/work/audits/projections.
- [x] 2.3 Add layout findings for missing roots, unknown roots, old schema,
  DNA names, flat artifacts, mixed roles, duplicate authority, and history
  fallback attempts.
- [x] 2.4 Add reparse-point, bytecode/cache, path-collision, content-collision,
  and manifest-conservation checks.

## 3. Gate integration and tests

- [x] 3.1 Run layout audit before all model/test/evidence reads in project audit.
- [x] 3.2 Add read-only hash-preservation fixtures for every required negative
  case and one complete positive fixture.
- [x] 3.3 Assert layout failures make later checks `not_run` and never consult
  history or alternate roots.
- [x] 3.4 Rebuild current model authority after layout identity changes.

## 4. Direct current project rewrite

- [x] 4.1 Build an inventory ledger for every current and historical
  `.flowguard` entry with owner, fingerprint, disposition, target role, and
  affected identities.
- [x] 4.2 Resolve every row to `move_current`, `rewrite_current`,
  `history_only`, `retire_proven`, `delete_proven`, or `unresolved`.
- [x] 4.3 Keep execution blocked while any row is `unresolved`.
- [x] 4.4 Directly place current artifacts under their roles and rebuild all
  affected model, contract, test, projection, and receipt identities.
- [x] 4.5 Verify no old current path, alias, junction, symlink, or fallback
  reader remains.

## 5. Verification and handoff

- [x] 5.1 Run focused layout, adoption, model-authority, and reverse-surface
  tests after each affected owner change.
- [x] 5.2 Run strict OpenSpec validation and check proposal/design/spec/tasks
  consistency.
- [x] 5.3 Run one final frozen layout/model/project validation only after all
  affected identities are current.
- [x] 5.4 Leave OpenSpec checkboxes open until the matching implementation,
  test, and terminal receipt exist.
