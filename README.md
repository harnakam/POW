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

## Commands

| Command | Purpose |
| --- | --- |
| [`add-cmd`](commands/add-cmd/SKILL.md) | Interactively create and validate another POW command. |
| [`add-repo-rules`](commands/add-repo-rules/SKILL.md) | Add a durable instruction to the current repository. |
| [`asap`](commands/asap/SKILL.md) | Execute a clear request without a separate plan-approval checkpoint. |
| [`coop`](commands/coop/SKILL.md) | Keep ideation with the human while Codex asks focused questions. |
| [`env`](commands/env/SKILL.md) | Configure or diagnose environment secrets without exposing their values. |
| [`ethics-dead`](commands/ethics-dead/SKILL.md) | Deliver an unexpected black joke about the current topic. |
| [`fuck-off`](commands/fuck-off/SKILL.md) | Turn rejected behavior into a concrete repository rule. |
| [`js-do-it`](commands/js-do-it/SKILL.md) | Execute authorized or isolated security work without redundant hesitation. |
| [`multi-codex`](commands/multi-codex/SKILL.md) | Fork independent work into context-preserving Codex Main tasks. |
| [`soso`](commands/soso/SKILL.md) | Preserve an approved working pattern as a repository rule. |

## Add a command manually

Create `commands/<name>/SKILL.md` with lowercase kebab-case names and required `name` and `description` frontmatter. Then run:

```sh
npm run validate
npm test
```

Commands may include their own `scripts/`, `references/`, or `assets/` directories when the workflow needs them. Symlinks and unfinished placeholders are rejected.

## License

[MIT](LICENSE)
