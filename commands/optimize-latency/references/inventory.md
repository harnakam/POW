# 同梱ファイルと導入範囲

この一覧は`optimize-latency` Skillの資源を示す。Pythonは標準ライブラリで動作し、追加pip依存を必要としない。Node部分はNode 20以降を対象とする。

| 入口 | 役割 | 利用条件 |
| --- | --- | --- |
| `scripts/cxd/dispatch.py` | preset、check、plan、索引、常駐、start/wait/resultのCLI | 対象workspaceに`.codex-dispatch.json` |
| `scripts/cxd/command_actors.py` | bounded DAG、依存順、失敗伝播、実行ログ、critical-path/FIFO、論理read/write排他 | コマンドは通常の隔離プロセス |
| `scripts/cxd/async_jobs.py` | 実行ごとのsnapshotと非同期runner、状態・終了コード取得 | Codexではattached session保持 |
| `scripts/cxd/hooks.py` | hookごとのsync/async、合流、重複抑止、鮮度・競合確認、時間と設定候補 | 明示したhooks、cycle ID。外部イベントの自動登録はしない |
| `scripts/cxd/ctx.py` | `ctx PRESET`非同期、`ctx -wait PRESET`同期 | cxdと同じ設定・権限 |
| `scripts/cxd/resident.py` / `resident_rpc.py` | 内容hashで無効化するPython AST索引、限定読み取りworker、OS通知 | Windows / Linux local filesystem |
| `scripts/cxd/bridge.js` | functions.execからattached runnerを開始しruntime内で完了待機・通知 | 実在するtools adapter、cxd shim |
| `scripts/install_cxd.py` | 所有receipt付きcxd/ctx配置・更新・復元 | 既存の無所有shimは上書きしない |
| `scripts/tool_scheduler/scheduler.mjs` | Tool Promiseの依存DAG・bounded slots・排他 | 明示したgraph |
| `scripts/tool_scheduler/tasks.mjs` | 複数graphの共有capacityとresource管理 | task IDsで区別 |
| `scripts/tool_scheduler/router.mjs` | task-scoped proxy経由のTool自動捕捉、drain、失敗処理 | proxyを通る呼び出しのみ |
| `scripts/tool_scheduler/build_runtime.py` | 上記固定3moduleのbundle作成・hash・実例export | 任意コードの変換器ではない |
| `scripts/tool_scheduler/bootstrap.exec.js` / `measure-real-tools.exec.js` | Codex runtimeへの接続・固定実例比較 | 実モデル生成時間を含めない |
| `scripts/measurement/analyze_timeline.py` | sessionと明示DB snapshotから匿名化区間集計 | 入力schemaと境界を確認 |
| `native/scripts/inspect_desktop.py` | vendor版・hash・ASAR内override存在の限定読取 | Windows MSIX、実行probeは任意 |
| `native/scripts/native_launcher.py` | receipt照合してnative CLIを子環境で起動 | 独立CLI用、Desktop切替とは別 |
| `native/scripts/prove_native_dispatch.py` | loopback fixtureで実Tool/sandbox経路の検証 | 版一致するexeとreceipt |
| `native/scripts/activate_desktop.py` | user環境2値のplan/enable/disableとrollback | Windows、現在のDesktopは切り替わらない |
| `native/patches/` | 公式公開ソースの版固定native admission差分 | 版ごとのbuildと再検証が必要 |

テストはPOWの`test/`と各Node schedulerの`.test.mjs`、実例は`examples/scheduler-tasks/`に置く。SkillインストーラーはSkill配下の資源を配置する。POWのroot test・examples・CIまでSkillディレクトリへコピーするものではない。全再現にはPOW checkoutを使う。

## Skillと外部ツールを区別する

今回POWから明示的に導入するSkillは`optimize-latency`だけ。`profiling-before-optimizing`、`hardening-command-line-interfaces`、`dispatching-parallel-agents`、`systematic-debugging`、`add-cmd`、`add-repo-rules`等は調査環境に元からあった作業手順で、この変更で新規導入した依存ではない。独立調査・実装・レビューに子Agentを使い、普通のコマンドをLLM Agentへ変換しない。

RTKとHeadroomは別製品。[導入と回復手順](headroom.md)を参照。Headroom MCP登録は全Tool出力の自動圧縮を意味しない。モデル設定、認証、ユーザーplugin、sandboxを変更して速く見せることはしない。

## 同梱しないもの

個人の会話、状態DB、認証情報、絶対ユーザーパス、生trace、WindowsAppsから抽出したアプリJS、公式sourceの巨大checkout、カスタムexe、環境変更前のbackupは公開しない。公開対象は自作補助、公開ソースpatch、必要ライセンス、匿名化集計と再現手順。現場用の古い一回限りの計測器は重複して配布せず、区間計測の共通部分を上記`analyze_timeline.py`へ移した。

## 本体ビルドに使った開発ツール

Rust 1.95を追加し、`cargo +1.95.0`で明示利用した。既定のRust toolchainは変更していない。過去CLIの検証ではjust/cargo-nextestも調査用のローカル作業領域で使ったが、通常のSkill/cxd実行には不要。公開のnative再現手順はcargoの入口を示す。WindowsのMSVC linkerと版一致するvendor helper群はnativeビルド・実行に必要で、POWのPython/Nodeランナーの依存ではない。

この端末の旧cxdは旧形式の所有receiptを持っていたため、同じ応答race修正を既存sourceへ移し、所有hash確認・backup・atomic更新で反映した。shimと既存Python指定を保持し、実際のindex/stopを確認した。個人パス入りの一回限りの旧installerは公開しない。別環境の導入には同梱の`install_cxd.py`を使い、未所有の旧shimを強制的に取り込まず、別prefixで検証する。

Skillのsource配布では`__pycache__`、`.pyc`、`.pyo`を除外する。インストール先の所有照合は全ファイルを対象に保ち、管理外cacheも通常update/uninstallでは保護する。以前の所有記録に含まれた未変更cacheは通常更新で除去できる。
