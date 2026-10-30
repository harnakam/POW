# 全チャット向けの運用指示

調査環境のグローバルAGENTS.mdには、以下の3ブロックが登録済みであることを確認した。コマンドのまとめ方、worker再利用、必要な場合だけのAgent委譲を指示する。これはモデルへの運用指示であり、native強制制御とは区別する。

他の環境で使う場合は、実際のCODEX_HOME配下のAGENTS.md（既定はWindows `%USERPROFILE%\.codex\AGENTS.md`、Linux `~/.codex/AGENTS.md`）を先にbackupする。既存の他の指示を保持し、同じmarkerがあればその範囲だけ更新する。重複して追記しない。Skillインストーラーはこのグローバルファイルを自動変更しない。

```markdown
<!-- command-scheduling-policy -->
## Command scheduling

Batch independent shell work into one tool invocation and execute it concurrently with a bounded limit. Represent command jobs with IDs, dependencies, exit codes, and completion events; do not create an LLM agent merely to run a command. For long batches, use functions.exec yield_control and notify so the parent can continue useful work; keep session waiting inside the runtime, not repeated model turns. Reuse existing runners instead of generating new monitoring scripts. Wait only when a dependent result is needed. Keep normal permissions, failure logs, and validation intact; serialize conflicting writes.
<!-- /command-scheduling-policy -->

<!-- common-dispatcher-policy -->
When cxd is available and the workspace has .codex-dispatch.json, prefer its registered short presets (cxd aliases, cxd check) and cached Python symbol lookup (cxd index, cxd symbols NAME) over generating new scripts or rereading whole files. In Codex, keep cxd serve in a dedicated exec session for cross-call worker reuse; use cxd status to inspect it and cxd stop when no longer needed. Resident workers only handle scoped read operations; commands and tests keep normal process isolation and permissions. Do not reuse a cached test success.
<!-- /common-dispatcher-policy -->

<!-- adaptive-delegation-policy -->
## Harness reuse and selective multi-agent work

Before writing orchestration, measurement, or diagnostic code, inspect and reuse existing dispatcher presets, scripts, and workers; extend the smallest existing entry point only when a concrete capability is missing. Do not build new tooling for a simple task unless the task requires it.

Handle simple, short, tightly coupled tasks in the parent without sub-agents. Use multi-agent work when there are substantial independent investigations, implementation units, or reviews and useful overlap is likely to outweigh startup, context transfer, and integration costs. This policy authorizes selective delegation for those tasks, not delegation of every command. Use the smallest useful team and give each agent a bounded objective, necessary context, and clear file ownership or read-only scope.

Start independent work together. While agents or commands run, the parent should perform useful independent work and consume completion messages; wait only when a required dependency blocks further progress. Serialize conflicting writes and review and verify the integrated result. Keep ordinary command execution in the existing command scheduler, not an LLM agent. Do not describe concurrent sub-agent execution as parallel generation within the parent's single model request, or claim speedups without comparable measurements.
<!-- /adaptive-delegation-policy -->
```

これらの指示は、存在しないpresetを作ったことにしたり、テスト成功をcacheから返したりする許可ではない。ユーザーの明示的な依頼・権限・失敗ログを維持する。単純な作業には追加のrunnerや子Agentを作らない。
