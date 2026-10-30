# POW

> **License:** noncommercial use and modifications are free with **prominent public promotion** in your main README or primary public introduction. **Commercial use requires a paid agreement.** Optional support: [GitHub Sponsors](https://github.com/sponsors/harnakam). See [LICENSE](LICENSE) and the [Japanese guide](LICENSING.md).

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
| [`compressor`](commands/compressor/SKILL.md) | Audit repository bloat, quarantine reviewed files, and restore without overwriting new work. |
| [`design-reasoning`](commands/design-reasoning/SKILL.md) | Capture real desktop/mobile interactions and bind visual review to actual screenshots. |
| [`dopagaki`](commands/dopagaki/SKILL.md) | Deliver answers first; accelerate substantial work with parallel Codex CLI implementation, integration, and verification. |
| [`env`](commands/env/SKILL.md) | Configure or diagnose environment secrets without exposing their values. |
| [`ethics-dead`](commands/ethics-dead/SKILL.md) | Deliver an unexpected black joke about the current topic. |
| [`fuck-off`](commands/fuck-off/SKILL.md) | Turn rejected behavior into a concrete repository rule. |
| [`hatarake`](commands/hatarake/SKILL.md) | Bound implementation attempts and require artifact evidence and independent review before completion. |
| [`js-do-it`](commands/js-do-it/SKILL.md) | Execute authorized or isolated security work without redundant hesitation. |
| [`multi-codex`](commands/multi-codex/SKILL.md) | Fork independent work into context-preserving Codex Main tasks. |
| [`optimize-latency`](commands/optimize-latency/SKILL.md) | Diagnose slow tasks and reduce repeated code generation, model round trips, and orchestration costs using measured evidence. |
| [`pow-code-design`](commands/pow-code-design/SKILL.md) | Design readable code and focused extension boundaries from concrete change requirements. |
| [`pow-first-loop`](commands/pow-first-loop/SKILL.md) | Define an ideal outcome, consult a history-free AI, and build a real executable loop toward completion. |
| [`pow-reference`](commands/pow-reference/SKILL.md) | Learn a mechanism from pinned primary code, pass compact evidence, and retain facts with clear invalidation conditions. |
| [`prove`](commands/prove/SKILL.md) | Run an explicitly requested bounded execution comparison, preserving real outcomes and failure evidence. |
| [`repo-refactor`](commands/repo-refactor/SKILL.md) | Continuously improve repository structure, responsibility boundaries, and debugging through compatible refactoring and evidence-based cleanup. |
| [`soso`](commands/soso/SKILL.md) | Preserve an approved working pattern as a repository rule. |
| [`update`](commands/update/SKILL.md) | Discover evolving workflows and ordered CI declarations; run explicitly approved local Node steps. |

## Executable engineering commands

For automatic Codex lifecycle hooks, use the [explicit native integration](commands/optimize-latency/references/native-hooks.md). It preserves existing handlers, registers reviewed trust, and supports per-hook sync/async settings and measured tuning. Ordinary Skill installation does not change global hook settings.

Invoke `$update`, `$compressor`, `$hatarake`, or `$design-reasoning` in Codex after installation. Each Skill bundles its own standalone Node runtime and works without the other three. The clone also provides literal slash dispatch:

```sh
node scripts/pow.mjs /update scan --root .
node scripts/pow.mjs /compressor help
node scripts/pow.mjs /hatarake --help
node scripts/pow.mjs /design-reasoning help
```

The installer action `update` updates Skills; `/update` inspects a target repository. Runtime state lives under that target's `.pow/`, which should remain private and ignored. No model API, automatic hooks, publishing, or dependency installation is enabled. Browser capture requires Node 22+ and an existing Chrome/Edge executable. Read the [architecture, scenarios and limits](docs/engineering-commands.md) and each Skill's runtime reference before applying changes.

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

## Latency optimization

Use `$optimize-latency` when investigating slow Codex work. The [Japanese optimization procedure](commands/optimize-latency/references/workflow.md) covers reuse, command scheduling, selective sub-agents, measurement boundaries, and safe caching. The [2026-10-19 measured examples](commands/optimize-latency/references/measurements-2026-10-19.md) separate a comparable workflow experiment from unrelated task timings and document what remains unknown.

The command also bundles [cxd for Windows and Linux](commands/optimize-latency/references/cxd.md): a Python-standard-library command DAG runner, cached read-only worker, and an ownership-preserving installer. POW copies these resources with the Skill but does not automatically install a PATH command or start a worker. No API proxy or compressor is added. Simple tasks do not require a new harness or a team of agents.

To try the included example without installing cxd (use `python3` on Linux):

```sh
python -B commands/optimize-latency/scripts/cxd/dispatch.py --workspace examples/cxd check
python -B commands/optimize-latency/scripts/cxd/dispatch.py --workspace examples/cxd stop
```

The [cxd guide](commands/optimize-latency/references/cxd.md) covers explicit installation, short presets, resident sessions, result logs, and filesystem limitations. Python 3.10+ is required only for cxd; the POW installer remains Node-only.

For context compression, see the [RTK and Headroom guide](commands/optimize-latency/references/headroom.md). It covers isolated Headroom 0.41.0 installation, Codex stdio MCP integration without provider changes, local compression and retrieval, offline settings, and measured limits. These optional third-party tools are not downloaded or enabled by POW automatically.

For dependency scheduling and asynchronous execution, read the [scheduler guide](commands/optimize-latency/references/scheduler.md). The [investigation method](commands/optimize-latency/references/investigation.md) explains timing attribution, concurrency settings, reproducibility, and the native integration boundary. The [2026-10-27 measurements](commands/optimize-latency/references/measurements-2026-10-27.md) record real Tool verification of three projects and distinguish it from synthetic workloads and full-turn latency.

Install only this Skill with `node scripts/pow.mjs install --name optimize-latency`; use `update --name optimize-latency` for an owned installation. See the [file inventory](commands/optimize-latency/references/inventory.md) for Python/Node resources and the [native guide](commands/optimize-latency/native/README.md) for version-pinned Codex patches, Desktop inspection, isolated dispatch verification, activation, and rollback. Skill installation alone does not switch the running Desktop engine.

## Add a command manually

Create `commands/<name>/SKILL.md` with lowercase kebab-case names and required `name` and `description` frontmatter. Then run:

```sh
npm run validate
```

Commands may include their own `scripts/`, `references/`, or `assets/` directories when the workflow needs them. Symlinks and unfinished placeholders are rejected.

The existing test suite remains available through `npm test` for an explicitly requested test task; adding a Skill does not require new tests or a full-suite run.

## License

[POW Source-Available License 1.1](LICENSE). This is a custom source-available license with the following conditions:

- **Commercial use:** obtain a separate written commercial license from harnakam and pay the agreed fee before use. Internal business use and paid client work are included.
- **Prominent public promotion is required:** before operational use or redistribution, name POW and harnakam, link to this repository, and truthfully describe your use. Put the acknowledgment at the beginning of the main public README or in the primary introductory area of your main website or product page. Keep it prominent and publicly accessible while use continues; a footer, buried notice, collapsed section, or incidental social post alone is insufficient. Private work can use a public personal website or profile introduction without disclosing project details.
- **Modifications require no donation:** noncommercial modifications are free under the promotion and notice conditions. Ordinary configuration and unrelated generated output do not become POW derivatives merely through use.
- **Optional support:** contribute through [GitHub Sponsors](https://github.com/sponsors/harnakam) if you wish. Sponsorship does not buy commercial permission or replace promotion.
- **Notices:** retain the license and applicable copyright notices when redistributing, and identify your modifications.

Contact [harnakam through the project repository](https://github.com/harnakam/POW) to arrange commercial terms. No automatic collection is bundled. See the [Japanese licensing guide](LICENSING.md) for examples.

Previous MIT releases retain their existing permissions; the change does not charge retroactively for those copies. [LICENSE-MIT-LEGACY](LICENSE-MIT-LEGACY) preserves the historical text and does not license new material under MIT. Separately licensed third-party material keeps its original terms. The [full LICENSE](LICENSE) governs this version.
