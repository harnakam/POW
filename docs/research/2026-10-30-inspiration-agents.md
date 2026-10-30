# POW に取り込める agent・hook・workflow の仕組み

調査日 2026-10-30。GitHub connector で9件のmetadata・固定commit本文・licenseを確認。仕組み27件、障害報告4件。★はAPI取得値で品質順位ではない。push日はrepo全体の活動であり、HEAD更新日・保守保証とは異なる。実装確認とPOW案を分けた。導入・外部agent実行・テスト・ベンチマークは行っていない。

## 人気・同一性・保守・ライセンス

全件 API の archived=false。日付は `pushed_at` / 検査した HEAD の commit 日。ライセンス本文も確認した。

| 現行 repository / ★ | push / HEAD日 | 固定HEAD / license |
| --- | --- | --- |
| [openai/codex](https://github.com/openai/codex) / 131,614 | 10-30 / 10-30 | `c15d0ce323f2` / [Apache-2.0][cx-L] |
| [anomalyco/opencode](https://github.com/anomalyco/opencode) / 223,125 | 10-30 / 10-30 | `2d96b0f69fc1` / [MIT][oc-L] |
| [Aider-AI/aider](https://github.com/Aider-AI/aider) / 49,824 | 05-22 / 05-22 | `5dc9490bb35f` / [Apache-2.0][ai-L] |
| [SWE-agent/SWE-agent](https://github.com/SWE-agent/SWE-agent) / 20,682 | 10-26 / 07-16 | `3ea751c087f3` / [MIT][sw-L] |
| [SWE-agent/mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) / 8,961 | 10-26 / 09-03 | `04d809ceab9d` / [MIT][mi-L] |
| [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands) / 92,218 | 10-30 / 10-30 | `5e8052347cc0` / [MIT][oh-L] |
| [aaif-goose/goose](https://github.com/aaif-goose/goose) / 55,939 | 10-29 / 10-29 | `9fbb9a48e1d9` / [Apache-2.0][go-L] |
| [anthropics/claude-code](https://github.com/anthropics/claude-code) / 153,892 | 10-30 / 10-30 | `b3f291d13192` / [All rights reserved・商用規約][cl-L] |
| [obra/superpowers](https://github.com/obra/superpowers) / 308,770 | 10-29 / 10-21 | `2ce8aa15d05b` / [MIT][sp-L] |

旧 `All-Hands-AI/OpenHands`・`block/goose` はAPI移転応答と移転先metadataで確認。gooseは[移転告知](https://goose.vcorp.ai/blog/2026/04/07/goose-moves-to-aaif/)も参照。OpenCodeはdefault=`dev`、現行source=`packages/core`。Claude Code公開mods/例から非公開engine全体の動作は証明できない。

## 27 の具体的な着眼点

**Codex。** 実装: ①検索toolがあればMCPをdeferred公開、agent-plugin schemaは1件8,000・合計64,000 bytesを超えるとhidden。②同じ不変定義のhandler identityと検索indexを再利用。③user messageとsummaryを分け、goal ID・window情報を保存。[tool公開][cx-tools]・[compaction][cx-compact]。POW案: 復帰資料の原要求と生成要約を分離。byte上限はtoken/cost上限ではない。本体のtool基盤は再実装しない。

**OpenCode v2。** 実装: ④windowの15%・最低16kの余白と拒否時の段階縮小。⑤background summaryは既定off、開始量・失敗回数・保持tailを制限。⑥agent不在はdeny、設定denyをplugin評価より優先。[compaction][oc-compact]・[permission][oc-permission]。POW案: 入力上限と縮小失敗を明示。background要約は追加課金になるため自動採用せず、model固有閾値・実行基盤の権限境界を保つ。

**aider。** 実装: ⑦参照graphのPageRankと言及file/identifierで順位付け。⑧signature周辺を二分探索でtoken予算付近へ収容。⑨disk cache障害は再作成後memoryへ退避。[repomap.py][ai-map]。POW案: `cxd symbols`へ小さな依存近傍と出典を追加。NetworkX・tree-sitter・diskcache一式の移植は重い。mtime依存より既存の内容hashを維持する。

**SWE-agent。** 実装: ⑩古いobservationを省略件数へ置換、keep/remove tagsで例外指定。⑪同じfileの旧windowを省略。⑫polling間隔で履歴書換えを抑える。作者も書換えによるprompt-cache破壊を明記。[history_processors.py][sw-history]。POW案: 最新エラー・未解決制約・受入証跡を保護し、古い正常出力だけ参照付きで畳む。regex一括削除は避ける。

**mini-swe-agent。** 実装: ⑬query前にstep/cost/wall-clock確認。⑭format失敗も消費costへ加算、連続失敗制限。⑮finallyでtrajectoryとmodel/env/config/version/exit保存。[default.py][mi-agent]。POW案: 解析失敗もattempt・復帰資料へ記録。costは1call分超過し得る。wall-clock確認は進行中callの強制中断ではなく、0は無制限。不明costを0と扱わない。

**goose。** 実装: ⑯pre/postをtool_call_idで対応。⑰hook既定30秒、policy拒否と実行失敗を区別し、PreToolUse失敗のblock可否をon_failureで指定。⑱request/responseを対で縮約、相乗りcallの対応が崩れる組はskip。[hooks][go-hooks]・[pair compaction][go-pairs]。POW案: 元call IDとcauseを保持し、policy拒否をtransient retryへ流さない。通知hookの失敗方針を権限hookへ流用しない。

**OpenHands。** 実装: ⑲automation照会はFIFO・同時3件、待機中abortはnetworkへ送らない。⑳hook読込5秒、起動用のnull fallbackと表示用の失敗応答を分離。㉑履歴50件とseq cursor、cloud遅延copyは重複許容で再生。[limiter][oh-limit]・[hooks][oh-hooks]・[history][oh-history]。POW案: reportも件数上限・差分取得。本repoはCanvas側でSDK内部の検査ではない。null fallbackを必須policy gateに使わない。

**Claude Code公開mods/例。** 実装: ㉒Bash PreToolUse例はJSON入力、違反時exit 2。㉓AGENTS候補を正規化path・既読project本文で重複排除。㉔directory単位でinstruction順序へ挿入。[validator][cl-validator]・[dedup][cl-unseen]・[placement][cl-placement]。POW案: skill/AGENTSの二重注入を抑えscopeを保持。例示regexは安全境界ではない。All rights reservedのためコード転載せず独立設計の参考にする。

**superpowers。** instruction: ㉕全chatではなくtask brief・interface・制約を渡しledgerで復帰。㉖再reviewは指摘とfix差分だけ、最大5round。㉗成功主張前に実行結果確認。[SDD][sp-sdd]・[fix-loop][sp-fix]・[verification][sp-verify]。POW案: 指摘ID・変更file・証跡を限定して渡す。手順はruntime強制ではない。model変更・5回・毎task commit等を一括採用せず、POWの権限・検証方針を優先する。

## 事故例から残す制約

- [Codex #32360](https://github.com/openai/codex/issues/32360): 0.144.1でhookへ実workdirが落ちず別repoのpolicyを適用する報告。open。ただし[現行実装][cx-hook]にはtool_cwd引数がある。現在も同じ欠陥とは断定せず、実cwd・hook起動cwd・対応versionを分ける。
- [OpenCode #53242](https://github.com/anomalyco/opencode/issues/53242): v2.0.22・llama.cpp/Qwen系でtool result後の空summary。10-30更新、open。[現行実装][oc-compact]にはtemplate確認・nudge・空summary失敗があるが、全providerの解決は未確認。空要約を成功checkpointにしない。
- [mini #963](https://github.com/SWE-agent/mini-swe-agent/issues/963): 292step後、予算入力`$5`のparseで落ち復帰不能という利用者報告。09-19作成、open。保存と安全な再開は別。残予算・元契約・生存processを復帰契約に含める。
- [superpowers #2619](https://github.com/obra/superpowers/issues/2619): mkdir不可を所有権衝突と区別せず800回以上探索したfork利用者の報告。10-25作成、open。「衝突なら別名」「I/O不可なら停止」を分け、探索上限を設ける。

4件とも独立再現していない。openは現行欠陥の証明ではなく、発生率・脆弱性判定もしない。

## POW との照合と優先順位

既存[`resident.py`](../../commands/optimize-latency/scripts/cxd/resident.py)にhash付きAST索引、[`hooks.py`](../../commands/optimize-latency/scripts/cxd/hooks.py)にasync/join/onFailure、[`native_hooks.py`](../../commands/optimize-latency/scripts/cxd/native_hooks.py)にnative連携・承認・有限待機がある。[hatarake](../../commands/hatarake/SKILL.md)もloop境界・証跡hash・review gate・復帰を実装済み。以下は追加候補であり採用決定ではない。

| 順位 | 最小の追加候補 | 費用・依存・判断条件 |
| --- | --- | --- |
| 1 | 復帰capsuleに原要求・未解決制約・証跡path/hash・次の一手を別欄で固定（③⑮㉕） | 低、既存stateから生成、追加LLM不要。要約に原要求を上書きさせない。 |
| 2 | hook記録に実cwd・call ID・policy denial/実行失敗を保持（⑯⑰、#32360） | 低〜中、host payloadのcapability確認が先。権限gateを新設せず既存境界を保つ。 |
| 3 | 指摘ID付きreview packageとfix差分だけの再review（㉖） | 低、既存hatarakeのevidenceHashと接続。別のreview engineを作らない。 |
| 4 | context出力の保護tag・出典path・budget・省略件数（⑧⑩⑪） | 中、まず既存symbols/tree出力の限定整形。provider token推定を精密計測と呼ばない。 |
| 5 | instruction注入のpath/content重複監査とscope表示（㉓㉔） | 低、読み取り専用から開始。似た文章でも異なるscopeなら自動削除しない。 |

①②はCodex host側で重複し、独自tool基盤は不要。PageRank全面移植・background LLM要約・Docker agent serverは依存と運用費が増えるため後回し。性能は将来の比較で判断し、今回の読解から高速化率・token削減率を推定しない。

## 出典の再現性と空白

全9件にfull SHA固定source・licenseあり。非公開Claude engine、OpenHands SDK内部、provider課金の厳密性、Windows実動作、障害の独立再現は未確認。作者のcache説明・手順の効果はPOWの測定結果ではない。

[cx-L]: https://github.com/openai/codex/blob/c15d0ce323f2197da865871502dc6ea7ef5b8ddb/LICENSE
[oc-L]: https://github.com/anomalyco/opencode/blob/2d96b0f69fc1bdeedc55d500f2c41ae94db3a29c/LICENSE
[ai-L]: https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/LICENSE.txt
[sw-L]: https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/LICENSE
[mi-L]: https://github.com/SWE-agent/mini-swe-agent/blob/04d809ceab9df28f9adaed044884180159172930/LICENSE.md
[oh-L]: https://github.com/OpenHands/OpenHands/blob/5e8052347cc021b7657abc7f30828dead944a683/LICENSE
[go-L]: https://github.com/aaif-goose/goose/blob/9fbb9a48e1d952daede4ba3f234a22bfe9265027/LICENSE
[cl-L]: https://github.com/anthropics/claude-code/blob/b3f291d131924810e2b7713ededc144843a229d5/LICENSE.md
[sp-L]: https://github.com/obra/superpowers/blob/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b/LICENSE
[cx-tools]: https://github.com/openai/codex/blob/c15d0ce323f2197da865871502dc6ea7ef5b8ddb/codex-rs/core/src/mcp_tool_exposure.rs
[cx-compact]: https://github.com/openai/codex/blob/c15d0ce323f2197da865871502dc6ea7ef5b8ddb/codex-rs/core/src/compact.rs
[cx-hook]: https://github.com/openai/codex/blob/c15d0ce323f2197da865871502dc6ea7ef5b8ddb/codex-rs/core/src/hook_runtime.rs
[oc-compact]: https://github.com/anomalyco/opencode/blob/2d96b0f69fc1bdeedc55d500f2c41ae94db3a29c/packages/core/src/session/compaction.ts
[oc-permission]: https://github.com/anomalyco/opencode/blob/2d96b0f69fc1bdeedc55d500f2c41ae94db3a29c/packages/core/src/permission.ts
[ai-map]: https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/repomap.py
[sw-history]: https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/agent/history_processors.py
[mi-agent]: https://github.com/SWE-agent/mini-swe-agent/blob/04d809ceab9df28f9adaed044884180159172930/src/minisweagent/agents/default.py
[go-hooks]: https://github.com/aaif-goose/goose/blob/9fbb9a48e1d952daede4ba3f234a22bfe9265027/crates/goose/src/hooks/mod.rs
[go-pairs]: https://github.com/aaif-goose/goose/blob/9fbb9a48e1d952daede4ba3f234a22bfe9265027/crates/goose/src/agents/state_machine/ops_tool_pair_compaction.rs
[oh-limit]: https://github.com/OpenHands/OpenHands/blob/5e8052347cc021b7657abc7f30828dead944a683/src/hooks/query/concurrency-limiter.ts
[oh-hooks]: https://github.com/OpenHands/OpenHands/blob/5e8052347cc021b7657abc7f30828dead944a683/src/api/hooks-service.ts
[oh-history]: https://github.com/OpenHands/OpenHands/blob/5e8052347cc021b7657abc7f30828dead944a683/src/hooks/query/use-conversation-history.ts
[cl-validator]: https://github.com/anthropics/claude-code/blob/b3f291d131924810e2b7713ededc144843a229d5/examples/hooks/bash_command_validator_example.py
[cl-unseen]: https://github.com/anthropics/claude-code/blob/b3f291d131924810e2b7713ededc144843a229d5/mods/agents-md/hooks/files/unseen-files.ts
[cl-placement]: https://github.com/anthropics/claude-code/blob/b3f291d131924810e2b7713ededc144843a229d5/mods/agents-md/hooks/files/with-project-files.ts
[sp-sdd]: https://github.com/obra/superpowers/blob/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b/skills/subagent-driven-development/SKILL.md
[sp-fix]: https://github.com/obra/superpowers/blob/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b/skills/subagent-driven-development/references/fix-loop.md
[sp-verify]: https://github.com/obra/superpowers/blob/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b/skills/verification-before-completion/SKILL.md
