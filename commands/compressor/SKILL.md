---
name: compressor
description: Audit repository information density and maintenance burden, review evidence per file, and quarantine explicitly selected redundant files with verified backups and conflict-safe restore.
---

# Compressor

Reduce maintenance burden while preserving useful information and necessary verification. This is a repository audit and reversible cleanup mechanism, not prompt compression or a contest to minimize lines. It works alone with Node 20+ and optional Git; it imports no other Skill and installs no dependencies.

Use the bundled `scripts/compressor.mjs` by its absolute installed path. All examples below abbreviate that path as `<script>`. Set `<repo>` to the real repository root, and place reports outside that root. `help` prints the interface.

## Audit and review

1. Run `node <script> audit --root <repo> --out <outside>/audit.json`. Without `--out`, audit prints JSON and writes nothing. Existing report files are never overwritten. The audit scans regular files up to 2 MiB, excludes `.git/`, dependency/VCS directories and `.pow/compressor/`, and records skipped paths. It does not execute repository code or open network connections. Treat reports as private: they contain filenames, hashes and reference locations. Secret-looking paths are hashed but their contents are not analyzed.
2. Review exact duplicate groups, near-duplicate documents, generated markers, unresolved local document links, and files with no observed inbound literal references. Every candidate includes its file hash, protection reasons, references with file/line citations, evidence and uncertainty. Inspect the cited source and callers before deciding. Entry files, runtime-discovered plugins, package scripts, migrations, standalone docs, framework routes, reflection and dynamic imports routinely evade static detection. Review small abstractions with their actual callers; the CLI cannot prove an abstraction is unused or excessive.
3. Establish each artifact's purpose and owner. A generated marker needs a verified generator and regeneration command. A stale document needs a contradiction with current behavior or an explicit superseding document; age and a broken link alone are insufficient. For documentation consolidation, identify the authoritative destination and preserve unique constraints/examples before proposing removal. Byte identity can still represent separate entrypoints, audiences or required test discovery locations.
4. Run `node <script> plan --root <repo> --audit <outside>/audit.json --out <outside>/plan.json`. The plan starts every candidate at `action: "retain"`. Review the actual JSON before applying. There is no bulk automatic acceptance or permanent delete command.

## Selected reversible application

Git discovery disables filesystem-monitor hooks and external diff/text-conversion helpers. Nonordinary index states, including skip-worktree and assume-unchanged files, are explicitly protected even when `git diff` reports no change.

For each path actually authorized for quarantine, edit only its decision to `action: "quarantine"` and write a concrete `rationale`. Keep hashes, inventory and root identity intact. Protection requires the additional explicit per-path `allowProtected: true`: untracked/ignored files, dirty/index changes, unavailable Git status, licenses, secrets, configuration, instructions and hard links. Never infer permission from a duplicate group, filename, extension, age or test status. Prefer retaining protected artifacts unless the user's objective clearly calls for their removal and preservation.

Test removal/consolidation also requires a `verification` object with `rationale`, `preservedCapability`, nonempty `survivingPaths`, `command` and `observedResult`. Run the repository's existing relevant verification and record what actually happened; do not fabricate coverage equivalence from duplicate bytes or passing unrelated tests. Document scenario coverage, boundary/error cases, discovery and runtime differences. If equivalence is unproven, retain the test. The CLI validates the decision record and surviving files, but does not execute the recorded command or prove its truth. Also apply this rule manually to verification scripts whose filenames do not match common test conventions. Never remove necessary verification capability.

Run `node <script> apply --root <repo> --plan <outside>/plan.json` only after reviewing selected paths and rationales. It rechecks root identity, the entire inspected file inventory, skipped entries, current protection and selected hashes; a changed inventory requires a fresh audit/plan. It acquires an exclusive state lock, copies all selected bytes into private `.pow/compressor/<run>/` backups and verifies them before unlinking individual originals. It never recursively deletes directories, rewrites references, executes plan text, or removes backups. Record the printed run ID. Run repository-defined relevant checks after the change and review the diff; restore if behavior or links break. A successful quarantine alone is not evidence that the product still works.

## Recovery

Run `node <script> restore --root <repo> --run <run-id>`. Restore verifies root identity and backup hashes, creates missing parent directories, and copies with exclusive creation. New or modified files are reported as conflicts and left intact (exit 2); identical originals are left unchanged. Backups remain available after repeated restores. Move conflicting new work to a safe location before retrying; never overwrite it to force recovery. Interrupted applies have recovery information in `manifest.json` even without `completed.json`. If a crash leaves `.pow/compressor/lock`, confirm no compressor process is active before removing only that lock. Keep state private and outside commits; ask the repository owner to add `.pow/compressor/` to local ignore rules when appropriate. This command does not edit ignore configuration itself.

The tool rejects unsafe relative paths, case aliases/collisions, symlinks/junctions, root escapes and special files. Use it in a trusted, quiescent working tree: Node's portable path APIs do not make adversarial concurrent filesystem changes race-free. Backups preserve file bytes and permission bits on restore, not ownership, timestamps, ACLs or extended attributes. Do not quarantine files whose metadata must remain exact. Large/binary/dependency content and dynamic references require separate manual inspection. Similarity is token overlap, never a quality score. Near-document pair comparison is bounded to the first 300 eligible documents; exact byte grouping and inventory cover all inspected files.

Report selected/retained paths, cited reasons, the run ID and restore command, actual verification results, and unresolved uncertainty. See [the decision guide](references/review.md) for the compact review checklist.
