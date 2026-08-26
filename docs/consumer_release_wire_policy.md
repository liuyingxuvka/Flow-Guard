# Consumer release wire identity

`consumer.skill_distribution.current` has one current wire policy. Both the
FlowGuard producer and the independent SkillGuard auditor must implement this
policy without importing either project's private runtime.

1. Build the unsigned identity object with exactly these fields:
   `schema_version`, `skill_id`, `projection_id`, `files`, and
   `author_control_excluded`.
2. Serialize the object as UTF-8 JSON with sorted keys, no indentation, and
   separators `,` and `:`. The digest input has no trailing newline.
3. Compute `release_id` as `sha256:` plus the lowercase hexadecimal SHA-256
   digest of that unsigned canonical JSON.
4. Add `release_id` and `claim_boundary` to form the manifest object.
5. Compute `manifest_hash` as `sha256:` plus the lowercase hexadecimal
   SHA-256 digest of that manifest object using the same canonical JSON rules.
6. Store the final manifest as the canonical JSON bytes followed by exactly one
   UTF-8 newline.

Pretty JSON, uppercase digests, missing prefixes, or a different newline rule
are not alternate formats. They are invalid current identities. A verifier
must parse the manifest, recompute both hashes, re-enumerate every file, and
compare the target release id; a self-consistent manifest does not prove that
its files came from the frozen producer authority.

This is a consumer projection identity only. It contains no SkillGuard
contract, owner receipt, router, Portfolio, or author-maintenance dependency.
