# 依存関係・非同期実行・Toolルーティング

このSkillはPythonのコマンド実行器とNode.jsのToolスケジューラーを同梱する。前者は登録済みコマンド、後者は呼び出し側が渡すTool adapterを実行する。モデル生成を速くする機能や、Desktop全体のToolを捕捉するインストーラーではない。実測と適用境界は[調査手順](investigation.md)と[2026-10-27の記録](measurements-2026-10-27.md)を参照。

## 導入する範囲を選ぶ

POWルートで `node scripts/pow.mjs install` を実行するとSkillと同梱資料・スクリプトがコピーされる。既存導入の更新は `node scripts/pow.mjs update`。新しいCodexチャットで `$optimize-latency` を使う。POW管理外のSkillは上書きしない。必要条件はNode.js 20以上、cxdを使う場合のみPython 3.10以上。これらの操作だけではPATH、常駐プロセス、MCP、フック、モデル設定は変更されない。

cxdの明示的な導入・削除・所有ハッシュ保護・OS条件は[cxdガイド](cxd.md)。既存の `.codex-dispatch.json` があれば `cxd aliases` と `cxd check` などの短い登録済み入口を優先する。別実装を無断で置き換えない。既存コマンドで足りる作業のために、新しい計測器やAgentを作らない。

## PythonのコマンドDAG

`../scripts/cxd/` の `dispatch.py` が入口、`command_actors.py` が実行器、`async_jobs.py` が開始済み実行の保存・待機、`ctx.py` が短い入口を担当する。`resident.py` と `resident_rpc.py` は読み取りワーカー用。コマンドは通常の分離された子プロセスで実行し、読み取りワーカーへ任意コマンドを委ねない。

プリセットのジョブには一意な `id`、`argv` または読み取り用 `operation` を指定する。依存は `depends_on`、共有リソースは `reads` / `writes`、正の有限推定時間は `estimated_s`。プリセットに `scheduling: "critical_path"` を指定でき、比較・切り戻しは `"fifo"` を使う。

```json
{
  "scheduling": "critical_path",
  "jobs": [
    {"id": "index", "operation": "index", "reads": ["repo:source"], "estimated_s": 2},
    {"id": "symbols", "operation": "symbols", "parameters": {"query": "main"}, "depends_on": ["index"], "reads": ["repo:source"]}
  ]
}
```

空き枠ができた時点で実行可能なジョブを選ぶ。優先度は自身の推定時間と最長の後続依存鎖から求め、同順位は定義順。既定推定は1秒で、自動学習した値ではない。最短スケジュールの保証はない。前提失敗時は依存先をblockedにし、独立処理は続ける。終了コード、タイムアウト、ジョブ別原文ログ、開始・完了イベントを保持する。

同じキーのread/readは並行可能、write/readとwrite/writeは排他。キーは完全一致する論理名で、パスの包含や暗黙のI/Oは推測しない。先に書いてから読む意味上の順序には `depends_on` も必要。排他は1バッチ内だけで、別プロセスや別実行を保護するOSロックではない。

## start / wait / result

```sh
cxd plan check --concurrency 3
cxd start check --attached --compact
cxd wait RUN_ID --timeout 60
cxd result RUN_ID --compact
```

ctxを明示的に導入した環境では `ctx check` が非同期投入、`ctx -wait check` が同期、`ctx wait RUN_ID` と `ctx result RUN_ID` が既存実行の参照。PRESETは登録名で、任意シェル文字列のevalではない。

startの応答は投入済みを意味し、コマンドの成功ではない。resultは再実行せず保存済み状態を返す。実行中のresultが終了コード0でも成功判定には使わない。waitの待機期限切れは124で実行を止めない。ジョブ固有のタイムアウトとは別。結果ファイルの完成とランナープロセス終了にも差があり、直後の削除・移動にはwaitで終了まで確認する。

通常端末では切り離した実行が継続しても、Codexのサンドボックスでシェル終了時に子も終了する場合がある。Codex内では同梱 `../scripts/cxd/bridge.js` のattached経路でシェルセッションを保持する。bridgeは `functions.exec` の `yield_control` で親へ制御を返し、ランタイム内でセッションを待機して `notify` で完了を伝える。結果が必要な依存境界でセルIDを `functions.wait` へ渡す。毎回の状態確認だけのためにモデル要求を発生させない。

bridgeセルとセッションは完了まで保持する。ホスト・セル終了後の継続や終了した親ターンの自動再開は保証しない。CLIの短いaliasだけで親のモデル生成を再開できるわけではない。start後のプリセット定義は保存されるがソース自体は固定されないため、実行中の検証対象を書き換えない。

読み取りワーカーの `cxd serve` は専用execセッションで保持し、`cxd status` で確認、不要になれば `cxd stop`。これは非同期コマンドの停止操作ではない。索引の内容ハッシュで変更・削除・構文エラーを反映する。テスト成功をキャッシュしない。

## Node.jsの3つの入口

`../scripts/tool_scheduler/` の追加依存なしES moduleを、Nodeホストでimportして使う。

| 入口 | 入力と依存 | 用途 |
| --- | --- | --- |
| `runJobs` (`scheduler.mjs`) | ジョブID間のDAG | adapter呼び出しを明示的に計画 |
| `runTasks` (`tasks.mjs`) | タスク内ジョブ間のみ | 複数グラフを1つの共有枠へ投入 |
| `runToolTasks` (`router.mjs`) | タスクID間のDAG | タスクへ渡したTool proxyの呼び出しを自動捕捉 |

```js
import { runToolTasks } from './commands/optimize-latency/scripts/tool_scheduler/router.mjs';

const result = await runToolTasks([
  { id: 'inspect', reads: ['source'], run: t =>
    t.exec_command({ cmd: 'git status --short' }) },
  { id: 'verify', depends_on: ['inspect'], reads: ['source'], run: async t => {
    let r = await t.exec_command({ cmd: 'node --test' });
    while (r.session_id) r = await t.write_stdin({ session_id: r.session_id, chars: '' });
    if (r.exit_code !== 0) throw new Error('verification failed');
    return r;
  } },
], { tools, taskConcurrency: 3, toolConcurrency: 3 });
```

この例の `tools` はホストが渡す実adapter。Toolが正常応答してもコマンド終了コードが非ゼロなら、callbackが失敗を明示する。Toolの例外とアプリケーション上の失敗を混同しない。

runToolTasksはタスク数と共有Tool枠をそれぞれ制限し、タスク内は1呼び出しずつ投入順で実行する。既定は両方3。引数・receiver・戻り値・例外を元のToolへ引き継ぎ、通常の権限・承認判断を変更しない。callbackが例外を捕捉しても、捕捉済みTool失敗はタスク失敗として残る。独立タスクは継続し、失敗した前提を持つタスクはblockedになる。

タスクのリソースleaseはcallbackと捕捉済み呼び出しがすべて終了するまで保持する。await忘れやcallback例外があっても処理の途中で解除しない。callback終了後に保持したproxyから追加呼び出しはできない。まだ呼び出しを投入していない遅延callbackは捕捉対象外なので、切り離した処理を予約しない。

`session_id` はToolの応答で、プロセス終了ではない。callbackはネイティブセッションを最後まで待ってから戻る必要がある。AbortSignalも協調キャンセルで、実処理を強制停止・ロールバックしない。処理が続いているのにタイムアウト競争だけでPromiseをrejectすると排他を早く解除するため、adapterは実停止まで待つ。

runJobsは既定同時実行4、policyは `critical-path` / `fifo`。runTasksの同時実行上限は全グラフ共通で、リソースキーもタスク横断で共通。タスク間依存はrunTasksでは指定できず、runToolTasksを使う。observerの例外は別途記録し、実行中処理を放置しない。イベントには原文引数・結果を含めず、実結果・原文ログの保管範囲は呼び出し側で管理する。

## functions.execへの接続と適用境界

functions.execはローカルES moduleを直接importできない。短い独立呼び出しには `await Promise.allSettled([...])` を使う。再利用するグラフは `build_runtime.py` が固定の3モジュールから生成するbundleを、対応するホスト入口から読み込む。利用可能なbootstrapと測定入口は同梱ファイルとテストを確認する。

生成sourceの `Function(source)()` 評価は自分で確認した固定ローカルコードに限定する。任意Tool出力・Webページ・ユーザー入力を評価しない。SHA-256は版照合であり承認の代わりではない。更新後はbundleとbootstrapの版を揃える。

自動ルーティングは渡したproxyを通った呼び出しだけ。raw tools、別セル、別チャットは対象外。AGENTS.mdの運用指示はネイティブな強制適用ではない。Desktop全体への導入状況は[調査手順の本体境界](investigation.md#本体の自動適用を検証する)で確認する。


proxyを通さない生Tool経路のnative admissionとDesktop接続補助は[nativeガイド](../native/README.md)を参照する。通常N枠＋review reserve1の本体制限は、この資料のDAG・read/write排他とは別実装である。ビルド・隔離接続と稼働Desktopへの適用を分けて判定する。
