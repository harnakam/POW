# POW runtime・hook・最適化の実装候補調査

2026-10-30。GitHub connectorで一次ソース・HEAD・metadataを取得。全10件archived=false、push日はUTC。ソースはcommit固定。実装・導入・計測なし。

| リポジトリ | stars | 最終push | 確認したライセンス |
|---|---:|---|---|
| [Turborepo](https://github.com/vercel/turborepo) | 31,278 | 10-30 | [MIT](https://github.com/vercel/turborepo/blob/main/LICENSE) |
| [Nx](https://github.com/nrwl/nx) | 29,435 | 10-30 | [MIT](https://github.com/nrwl/nx/blob/master/LICENSE) |
| [uv](https://github.com/astral-sh/uv) | 91,348 | 10-30 | [MIT](https://github.com/astral-sh/uv/blob/main/LICENSE-MIT) / [Apache-2.0](https://github.com/astral-sh/uv/blob/main/LICENSE-APACHE) |
| [Ruff](https://github.com/astral-sh/ruff) | 50,333 | 10-30 | [MIT](https://github.com/astral-sh/ruff/blob/main/LICENSE) |
| [ripgrep](https://github.com/BurntSushi/ripgrep) | 69,556 | 10-27 | [Unlicense / MIT](https://github.com/BurntSushi/ripgrep/blob/master/COPYING) |
| [pre-commit](https://github.com/pre-commit/pre-commit) | 15,672 | 10-20 | [MIT](https://github.com/pre-commit/pre-commit/blob/main/LICENSE) |
| [esbuild](https://github.com/evanw/esbuild) | 40,118 | 08-09 | [MIT](https://github.com/evanw/esbuild/blob/main/LICENSE.md) |
| [Watchexec](https://github.com/watchexec/watchexec) | 7,263 | 10-26 | [Apache-2.0](https://github.com/watchexec/watchexec/blob/main/LICENSE) |
| [BullMQ](https://github.com/taskforcesh/bullmq) | 9,559 | 10-30 | [MIT](https://github.com/taskforcesh/bullmq/blob/master/LICENSE) |
| [Temporal TS SDK](https://github.com/temporalio/sdk-typescript) | 943 | 10-29 | [MIT](https://github.com/temporalio/sdk-typescript/blob/main/LICENSE) |

POW は既に hook別sync/async、入力hash重複排除、Stop join、profile、資源競合制御、timeout時のprocess tree終了を持つ。Windows/Linuxの完了通知待ち、atomic JSON、内容一致時のAST再利用も実装済み。これらは新規案に数えない。[現行hook](../../commands/optimize-latency/scripts/cxd/hooks.py)、[native adapter](../../commands/optimize-latency/scripts/cxd/native_hooks.py)、[async実行](../../commands/optimize-latency/scripts/cxd/async_jobs.py)、[scheduler](../../commands/optimize-latency/scripts/cxd/command_actors.py)、[索引](../../commands/optimize-latency/scripts/cxd/resident.py)。

比較した仕組みは30件。

- **Turborepo M01–02**：入力・環境変数・依存task・出力定義・argvを合成したhash、外部依存の推移閉包hashの事前計算・再利用。失効要因の明示に使う。[crates/turborepo-task-hash/src/lib.rs L428/L684](https://github.com/vercel/turborepo/blob/bc86480310df70498dc8c303d92d3e578a33c4df/crates/turborepo-task-hash/src/lib.rs#L684)
- **Nx M03–05**：変更pathの集約、計算開始・公開時の設定hash/世代照合、古い計算のawait者を最新Promiseへ接続。処理中に設定が変わっても古い結果を公開しない。[packages/nx/src/daemon/server/project-graph-incremental-recomputation.ts L124/L376/L583](https://github.com/nrwl/nx/blob/97486838acdfd70a32329e6bf1f956cc7126a718/packages/nx/src/daemon/server/project-graph-incremental-recomputation.ts#L124)
- **uv M06–09**：形式別version付きbucket、利用中shared/削除時exclusive lock、entry/shard単位lock、対象package指定refresh。キャッシュ削除と利用の競合を設計対象にする。[crates/uv-cache/src/lib.rs L95/L233/L528/L1297/L1502](https://github.com/astral-sh/uv/blob/d041e5700a7bb39bff687ebbba4f6f6f2bda5cc8/crates/uv-cache/src/lib.rs#L233)
- **Ruff M10–12**：root＋settings＋tool versionで名前空間分離、変更なしなら書込省略、古いentryの期限整理。mtime＋権限keyでPOWの内容hashを置換しない。[crates/ruff/src/cache.rs L31/L94/L156/L211/L365](https://github.com/astral-sh/ruff/blob/dc988f67760053f7e7e2456dff2aed146b6accb9/crates/ruff/src/cache.rs#L94)
- **ripgrep M13–14**：LIFOの深さ優先work stealing、全worker共通の終了通知。広いtreeの幅優先展開を避ける一方、Quit後にも進行中結果が到着し得る契約を明記する。[crates/ignore/src/walk.rs L1331/L1450/L1662](https://github.com/BurntSushi/ripgrep/blob/91f5d22ef48bde459d90a8c7dbeab416e97d0f2b/crates/ignore/src/walk.rs#L1662)
- **pre-commit M15–17**：ファイルをprocess単位にbatch化、OS/Windows batch別のargv長制限、batch数以内の並列度。1ファイル1起動にも極小batch大量生成にも寄せない。[pre_commit/xargs.py L49/L76/L154/L175](https://github.com/pre-commit/pre-commit/blob/8cb5845c835b1ff72240eb2484239411ec481d92/pre_commit/xargs.py#L76)
- **esbuild M18–20**：async APIの常駐子process、sync APIの再利用worker thread、shutdown完了までchildをrefしてexit待機。生存期間・終了責任も必要。[lib/npm/node.ts L150/L255/L289](https://github.com/evanw/esbuild/blob/f6058f8364fe7ab91ca57a83e02577ed74c9cae4/lib/npm/node.ts#L255)
- **Watchexec M21–23**：最初のevent起点の固定throttle窓で集約、urgent eventの待機迂回、sync/async handlerの共通処理。静穏まで延々待つdebounceとは区別する。[crates/lib/src/action/worker.rs L51/L113/L180](https://github.com/watchexec/watchexec/blob/a7170667adbb828633c11764fa57c58147b83ccb/crates/lib/src/action/worker.rs#L113)
- **BullMQ M24–26**：token付きleaseの一括更新、stalled job回復回数の上限、通知待機watchdog。timeout時は未解決blocking接続をreset。[src/classes/lock-manager.ts L46/L97](https://github.com/taskforcesh/bullmq/blob/4d1631f9f74e258779ff1fa2c29de23577248147/src/classes/lock-manager.ts#L46)、[src/classes/redis-queue-backend.ts L2161/L2829](https://github.com/taskforcesh/bullmq/blob/4d1631f9f74e258779ff1fa2c29de23577248147/src/classes/redis-queue-backend.ts#L2829)
- **Temporal M27–29**：親子scopeへのcancel伝播とcleanup用scope、reserve/used/releaseを分けたslot、bundler使用時だけのdynamic import。[packages/workflow/src/cancellation-scope.ts](https://github.com/temporalio/sdk-typescript/blob/3a3e906c44ccc027d44b4312e8a1a35ea1c7d62c/packages/workflow/src/cancellation-scope.ts#L38)、[packages/worker/src/worker-tuner.ts](https://github.com/temporalio/sdk-typescript/blob/3a3e906c44ccc027d44b4312e8a1a35ea1c7d62c/packages/worker/src/worker-tuner.ts#L158)、[packages/worker/src/workflow/bundle-workflow-code.ts](https://github.com/temporalio/sdk-typescript/blob/3a3e906c44ccc027d44b4312e8a1a35ea1c7d62c/packages/worker/src/workflow/bundle-workflow-code.ts#L10)

一次の失敗事例は設計上の制約になる。Turborepoの[PR #14857](https://github.com/vercel/turborepo/pull/14857)は連続編集が複数buildへ分裂する問題を、静穏200ms・上限1秒・実行中の変更保持で修正。[PR #14872](https://github.com/vercel/turborepo/pull/14872)はdetached manifest書込が終了時に失われ、以降も全出力を書き直す問題をreturn前の書込に変更した。esbuildの[issue #3896](https://github.com/evanw/esbuild/issues/3896)と[PR #3701](https://github.com/evanw/esbuild/pull/3701)はawait stopでも子process終了が完了しないDenoの資源問題を示す。BullMQの[issue #4479](https://github.com/taskforcesh/bullmq/issues/4479)はprocessがrunningでもjob消費が止まった報告。上流の測定値はPOWの速度証拠ではない。

差分候補上位5件。効果は未検証。

1. **変更pathによる索引更新**：`ProjectIndex.refresh`は毎回列挙・全bytes hash。変更集約＋定期完全照合へ拡張する候補。watch overflow・rename・ignore変更時は完全失効。費用：中。
2. **入力世代で結果公開を制御**：既存のStop再照合に加え、run生成時の設定/入力世代と公開時を照合し、旧計算の公開を拒否。失効結果を成功扱いしない。費用：中。
3. **上限付きevent集約**：同一hash重複排除に加え、異なるhashの短い編集burstをまとめる。Stopは蓄積変更をflushし、実行中の変更は次世代へ保持。費用：中。
4. **owner identityと回復上限**：現行owner.jsonはPID。PID再利用と停止した生存processを区別する開始identity/tokenを検討。lease切れだけで二重起動せず、期限超過を未検証として残す。費用：中～高。
5. **起動依存とcancel budgetを明示**：status/profile/eventのimport graphを確認し、不要準備を遅延。既存async adapterはawait cancelで実行commandを止めないため、cancel伝播と短いcleanup期限を別途設計。費用：中。

導入は原理の小さな移植を優先する。Nx/Turborepo全体はmonorepo graph運用、Ruff/uv/ripgrepはRust資産、WatchexecはTokio/notify等を伴う。pre-commit自体にもvirtualenv等の依存がある。[setup.cfg](https://github.com/pre-commit/pre-commit/blob/8cb5845c835b1ff72240eb2484239411ec481d92/setup.cfg)、[Watchexec manifest](https://github.com/watchexec/watchexec/blob/a7170667adbb828633c11764fa57c58147b83ccb/crates/lib/Cargo.toml)。BullMQのbackendとTemporalのdurable workflow/core bridgeはローカルPOWには過大になり得る。[BullMQ package](https://github.com/taskforcesh/bullmq/blob/4d1631f9f74e258779ff1fa2c29de23577248147/package.json)、[Temporal worker package](https://github.com/temporalio/sdk-typescript/blob/3a3e906c44ccc027d44b4312e8a1a35ea1c7d62c/packages/worker/package.json)。コード転用時は上記licenseと依存先noticeを再確認する。push日は活動の証拠に限り、保守応答の保証ではない。

検証境界は未確定。既存cxd/profileでcold/warm、入力不変/変更burst、queue待ち・起動・実行・joinを分ける。end-to-endはevent受信から必要hook成功・出力確定まで。子process区間と混ぜず、成果物・exit code・最新入力一致も比較する。過去の検証成功を再利用しない。**M30** BullMQの[backoffs.ts](https://github.com/taskforcesh/bullmq/blob/4d1631f9f74e258779ff1fa2c29de23577248147/src/classes/backoffs.ts#L9)はfixed/exponential＋jitter。circuit breakerとは異なる。breakerは通信障害の反復を抑える候補で、必須検証は未完了としてblock。compile失敗を無限retryしない。
