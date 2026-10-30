# POW

POW is a small, growing collection of extra commands for Codex. Each command is packaged as an [Agent Skill](https://developers.openai.com/codex/skills), so Codex can invoke it explicitly or select it when the request matches.

## Requirements

- Codex CLI or the Codex desktop app
- Node.js 20 or newer
- Git, if you want to contribute commands

## Install

```sh
git clone https://github.com/harnakam/POW.git
cd POW
node scripts/pow.mjs install
```

Start a new Codex chat after installation. For example:

```text
$add-cmd
```

Run `$add-cmd` from your POW clone to design, create, and validate the next command interactively. The full collection is listed below.

## Manage installed commands

```sh
node scripts/pow.mjs list
node scripts/pow.mjs update
node scripts/pow.mjs uninstall
```

POW installs commands into `${CODEX_HOME:-~/.codex}/skills` and records SHA-256 hashes in `${CODEX_HOME:-~/.codex}/.pow/manifest.json`.

- Existing Skills that are not owned by POW are never overwritten.
- Locally modified POW files are preserved during normal updates and uninstall.
- `node scripts/pow.mjs update --force` replaces only commands already recorded as POW-owned.
- The installer performs no network requests and runs no external commands.
- Each installed command carries `LICENSE` and the historical MIT notice. Installation does not publish promotions, send money, or accept a commercial agreement on your behalf.

## Commands

| Command | Purpose |
| --- | --- |
| [`add-cmd`](commands/add-cmd/SKILL.md) | Interactively create and validate another POW command. |
| [`add-repo-rules`](commands/add-repo-rules/SKILL.md) | Add a durable instruction to the current repository. |
| [`asap`](commands/asap/SKILL.md) | Execute a clear request without a separate plan-approval checkpoint. |
| [`coop`](commands/coop/SKILL.md) | Keep ideation with the human while Codex asks focused questions. |
| [`dopagaki`](commands/dopagaki/SKILL.md) | Deliver answers first; accelerate substantial work with parallel Codex CLI implementation, integration, and verification. |
| [`env`](commands/env/SKILL.md) | Configure or diagnose environment secrets without exposing their values. |
| [`ethics-dead`](commands/ethics-dead/SKILL.md) | Deliver an unexpected black joke about the current topic. |
| [`fuck-off`](commands/fuck-off/SKILL.md) | Turn rejected behavior into a concrete repository rule. |
| [`js-do-it`](commands/js-do-it/SKILL.md) | Execute authorized or isolated security work without redundant hesitation. |
| [`multi-codex`](commands/multi-codex/SKILL.md) | Fork independent work into context-preserving Codex Main tasks. |
| [`pow-code-design`](commands/pow-code-design/SKILL.md) | Design readable code and focused extension boundaries from concrete change requirements. |
| [`pow-first-loop`](commands/pow-first-loop/SKILL.md) | Define an ideal outcome, consult a history-free AI, and build a real executable loop toward completion. |
| [`pow-reference`](commands/pow-reference/SKILL.md) | Learn a mechanism from pinned primary code, pass compact evidence, and retain facts with clear invalidation conditions. |
| [`prove`](commands/prove/SKILL.md) | Run an explicitly requested bounded execution comparison, preserving real outcomes and failure evidence. |
| [`soso`](commands/soso/SKILL.md) | Preserve an approved working pattern as a repository rule. |

## Evaluation and parallel work

`$prove` is for an explicitly requested comparison. It can reuse an existing Node evaluator to record input hashes, paired outcomes, execution failures, and process duration, or compare existing compile/run commands directly without building another harness. See its [runner contract](commands/prove/references/runner.md). If you explicitly want to run the bundled parser comparison (no model calls), choose a new output directory:

```sh
node commands/prove/scripts/prove.mjs run examples/prove/suite.json ../pow-parser-results
```

`$dopagaki` now includes a [persistent task ledger](commands/dopagaki/references/parallel-cli.md#executable-work-ledger) that checks dependencies and overlapping ownership before workers start, and records evidence before tasks finish. Both tools use Node standard libraries and are bundled by the existing installer.

## Reference-driven implementation

Use `$pow-reference` for unfamiliar APIs, mechanisms or ports: retrieve a relevant implementation, extract its actual contract, and adapt only what the current project needs. Evidence carries source revisions and locations; reusable project facts keep applicability, verification level, and invalidation conditions. `$pow-code-design` uses those facts for boundaries, while `$pow-first-loop` supplies a neutral evidence brief to its one history-free consultation and follows the real entry point through to the result. No search server or memory database is required.

Verification stops at compilation/build or direct execution of the affected flow. Use existing commands, finite timeouts, and an expected result; stop when successful and retry only after a relevant change or concrete new failure. Do not add tests, fixtures, snapshots, benchmark suites, or verification harnesses unless explicitly requested. Preserve existing tests and required build controls; report compilation-only coverage honestly. `$prove` is an explicitly requested bounded comparison, not a finishing step for every implementation. Measured duration and actual provider tokens can be reported; unknown tokens stay unknown.

This workflow takes reference retrieval, source locators, compact output, and counted usage as design inspiration from [XERJ](https://github.com/xerj-org/xerj/tree/59a4617416258a8192981e49b7d82b83fd6d4307). POW does not bundle its engine, packs, background services, or automatic external feedback.

## Add a command manually

Create `commands/<name>/SKILL.md` with lowercase kebab-case names and required `name` and `description` frontmatter. Then run:

```sh
npm run validate
```

Commands may include their own `scripts/`, `references/`, or `assets/` directories when the workflow needs them. Symlinks and unfinished placeholders are rejected.

The existing test suite remains available through `npm test` for an explicitly requested test task; adding a Skill does not require new tests or a full-suite run.

## License

[POW Source-Available License 1.0](LICENSE). This is a custom source-available license with the following conditions:

- **Commercial use:** obtain a separate written commercial license from harnakam and pay the agreed fee before use. Internal business use and paid client work are included.
- **Public promotion is required:** before operational use or redistribution, publish a truthful acknowledgment naming POW and harnakam with a link to this repository. Choose your own public README, website, article, or social post. One acknowledgment covers continuing use; repeated posts, a positive review, or a star are not required.
- **Modifications require a support payment:** before using or redistributing your modified version, pay any positive amount of your choice once per derivative project. Further edits or releases of that same project do not require repeated payments. Ordinary configuration and unrelated generated output are not modifications of POW.
- **Notices:** retain the license and applicable copyright notices when redistributing. A support payment does not buy commercial permission.

Contact [harnakam through the project repository](https://github.com/harnakam/POW) to arrange commercial terms or a support-payment method. No payment service or automatic collection is bundled. See the [Japanese licensing guide](LICENSING.md) for examples.

Previous MIT releases retain their existing permissions; the change does not charge retroactively for those copies. [LICENSE-MIT-LEGACY](LICENSE-MIT-LEGACY) preserves the historical text and does not license new material under MIT. Separately licensed third-party material keeps its original terms. The [full LICENSE](LICENSE) governs this version.
