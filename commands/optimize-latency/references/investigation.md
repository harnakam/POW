# 遅延調査を再現し、原因と適用範囲を分ける

調査開始時に、ユーザーが待つ対象を固定する。完成物と検証と最終回答までか、複数コマンドの完了までか、Tool応答までかを明記する。既存の[手順](workflow.md)、[cxd](cxd.md)、[スケジューラー](scheduler.md)を使い、調査専用コードの再生成を先に増やさない。

## 1. 実装と入口を棚卸しする

package scripts、README、CI、`.codex-dispatch.json`、既存work/outputsの計測器と保存済み結果を読む。cxdがあれば `cxd aliases`、`cxd status`、Pythonシンボルなら `cxd index` / `cxd symbols NAME` を優先する。通常の検証はリポジトリ既定の入口を1回実行し、反復は「何を比較する実験か」を決めてから行う。

今回の同梱範囲はoptimize-latency Skill、そのreferences、Pythonランナー群、Nodeスケジューラー群。調査で利用した他のローカルSkillが自動的にPOWへ同梱・インストールされるわけではない。ユーザーの端末パス、設定バックアップ、会話ログ、認証情報を公開用資料に含めない。

## 2. タイムラインを分解する

要求の開始・終了、出力項目の追加・完了、Tool引数の到着、Tool開始・終了、子プロセス開始・テスト終了、最終回答の完了を、取得できる範囲で対応付ける。単調時計は同一プロセス内の経過時間に使い、別プロセスの時刻対応には時計と精度の違いを記録する。

| 区間 | 分かること | これだけでは分からないこと |
| --- | --- | --- |
| モデル要求→最初の出力項目 | 最初の項目までの待ち | 純粋な推論CPU時間、ネットワークだけの時間 |
| Tool引数生成・受信 | 引数が届く区間 | 全区間がモデル計算なのか輸送なのか |
| Tool開始→結果受信 | Tool境界の待ち | フック・起動・コマンド・輸送の個別原因 |
| 子プロセス内テスト | テスト処理 | アプリ作成や回答までの全工程 |
| 最初の要求→最終完了 | ユーザーが待った全体 | 単一の内部ボトルネック |

191.270秒の過去タスクではTool待ち103.170秒、引数生成・受信40.390秒、最初の出力項目待ち18.079秒、その他29.631秒だった。その他にreasoning項目の包絡時間16.271秒も含む。これらを「純粋なthinking」や「Desktop固有の費用」に置き換えない。詳細は[2026-10-19の記録](measurements-2026-10-19.md)。UIのThinking表示はプロファイラーではない。

分類の合計、重複、取りこぼしを計時算術で確認する。取得できない内訳はunknownとして残す。新しい計測自体が追加したモデル要求・プロセス・ログ出力も測定費用に含める。

## 3. 並行実行の単位を選ぶ

独立コマンドはID・依存・リソース・終了コード・完了イベントを持つ既存ランナーで束ねる。競合書き込みは直列化する。長いコマンドと親の独立作業はattached bridgeで重ね、依存境界でだけ待つ。LLM Agentをコマンドの実行・待機役にしない。

複数の独立した実装・調査・レビューが十分大きい場合だけ、必要最小限のAgentに所有ファイルと完了条件を渡す。短い密結合の変更は親で扱う。親はAgentの完了まで独立した統合作業を進める。単一の親モデル要求内で複数の文章生成が並行するという意味ではない。

Codex 0.156.1公開ソースではV2の同時Agent枠の既定は4。調査環境は2026-10-20に `agents.max_concurrent_threads_per_session` を15へ変更し、親を含む16枠の利用可能性を確認した。これはモデルToolの同時実行枠、cxdのconcurrency、routerのtoolConcurrencyとは別の上限。値を増やすだけの速度改善は実証していない。各環境では実効設定と実際のハーネス表示を確認し、POWはその設定を自動変更しない。

## 4. 比較実験を固定する

同じソース・テスト・引数・終了判定で逐次/並列を比較する。ソースSHA-256を前後照合し、毎回本物の検証を再実行する。開始前に対象件数、順序、標本数、上限、測定境界、キャッシュ条件、失敗時の扱いを記録する。ABBAやABBAABなどで順序を混ぜ、中央値だけでなく各標本と範囲を保存する。

測定器と回帰テストを同時実行して干渉させない。元のbaselineは保存し、新しい実験は別ファイルへ出す。sleepの合成負荷はアルゴリズムを調べる用途に限定し、実Tool・実テストの結果と区別する。過去と違うタスクの所要時間から倍率を出さない。

実Tool接続ではexec_commandのsession_idをwrite_stdin等で最後まで待つ。Tool例外だけでなく終了コードとテスト件数も確認する。bundle/bootstrapの読み込みを測定窓から除くなら明記し、全ユーザーターンの速度と呼ばない。今回の標本・比較条件は[測定記録](measurements-2026-10-27.md)。

## 5. 出力圧縮を別の因果経路として調べる

既存RTKフックを優先して、対応するノイズの多い出力を縮める。正確なJSON・ソース・タイミングは原文を保つ。失敗出力に回復IDがあれば `rtk recall` で原文を取得してから診断し、元の非ゼロ終了コードを維持する。

Headroom 0.41.0は隔離したstdio MCPとして扱い、[RTKとHeadroomガイド](headroom.md)の導入・設定・取得経路を使う。POWはHeadroomを自動取得せず、全Tool出力を自動proxyへ流さず、モデル品質・API経路・ユーザープラグインも変更しない。圧縮文字数の低下を、そのままトークン費用や全タスク時間の改善として報告しない。

## 本体の自動適用を検証する

JavaScript版の実Tool確認範囲は、runToolTasksへ渡したproxy内。Desktopの全Tool、全セル、全チャットへのネイティブな強制適用は、このproxyだけでは成立しない。その後、別途Codex本体のdispatch admissionパッチをビルド・隔離検証した。

0.156.1の版固定公開ソースで確認した境界は次の通り。

- [registry.rs L130](https://github.com/openai/codex/blob/rust-v0.156.1/codex-rs/core/src/tools/registry.rs#L130): 標準pre_tool_use_payloadはFunction以外でNoneを返す。
- [execute_handler.rs L241](https://github.com/openai/codex/blob/rust-v0.156.1/codex-rs/core/src/tools/code_mode/execute_handler.rs#L241): 外側のCode Mode execはCustom payloadを受け、上記処理を上書きしていない。
- [config.rs](https://github.com/openai/codex/blob/rust-v0.156.1/codex-rs/core/src/config/mod.rs): V2の枠と設定解決は対象タグで確認し、別版へ一般化しない。

globalThis.toolsが変更可能という観測だけでは、毎セルの自動注入入口の存在を証明しない。個々のToolのpre-hookで引数を調整できても、外側のJavaScript全体を安全な依存グラフへ変換できるとは限らない。公開CLIと私有Desktopの全内部実装の同一性も未確認。

本体へ導入する場合は、外側のCustom payloadまたはTool dispatchにmiddleware/preludeを追加するnative forkを用意し、対象バイナリをビルドして実接続する必要がある。その完了判定は、ソース差分・ビルド結果・対象バイナリの版とハッシュ・生Tool経路を含む実行テスト・承認/サンドボックス維持・戻し方の記録まで含む。proxyの20テスト成功は、その代わりにならない。Desktop対応版0.164.0-alpha.11.1（commit 6905ecede7816e91373e9eabda3f6b0368fc747b）はビルド成功と実Code ModeからのWindows unelevated sandbox実行を確認した。対応版はレビュー後の待機キャンセル修正を含む9 native testsが成功。修正済みrelease buildは実行検証前、live Desktopは未切り替え。0.156.1独立CLIの検証結果とは分ける。[nativeガイド](../native/README.md)に版・SHA・適用範囲・再起動・rollback・helperを記録する。稼働Desktopの全経路への導入成功は主張しない。

## 6. 結果を残す

実行した検証と失敗、変更ファイル、比較境界、全標本、キャッシュ変動、原データ名、未知の内訳、OS条件を保存する。公開版には匿名化した集約値と再現可能な一般手順だけを持ち出す。元の私用アプリや生ログが必要な実験は、その非同梱を明記する。検証成功・実Tool接続・本体全体への導入を分けて報告する。

## 同梱の区間計測器を実行する

`../scripts/measurement/analyze_timeline.py` は、既存の `analyze_model_timeline.py`、`measure_desktop_timing.py`、`measure_task.py` で使ったJSONL/SQLiteの対応付けと区間分割を、単一のオフライン入口へ整理したもの。Python 3.10以上の標準ライブラリだけを使い、常駐・自動探索・監視・外部通信は追加しない。過去の特定14 Tool/15 requestという件数、私用パス、固定ID、テストアプリの成功JSONには依存しない。

入力は利用者が選んだローカルのsession JSONL、thread/turn selector、必要ならSQLiteの**整合したstandalone snapshot**。SQLiteの `logs` テーブルに `id, ts, ts_nanos, target, feedback_log_body, thread_id`、sessionにはtask_started/task_complete・response_item・AgentMessageのitem_completedがある形式を対象にする。内部ログ形式は版で変わるため、別形式を推測して変換しない。

SQLiteは `mode=ro&immutable=1` とquery_onlyで読み、接続を明示的に閉じる。入力DBを変更せず、journal/shared-memoryファイルも作らないため、書き込み中DBや単純にmainファイルだけコピーしたWAL DBを入力しない。SQLiteのbackup機能などで作成済みの整合したsnapshotを指定する。隣に `-wal` / `-journal` があれば、未反映行を黙って無視せず拒否する。snapshot自体も会話・ログ本文を含み得るので、ローカルで保管し公開しない。DBなしでもsession上のTool・文章・その他区間だけを計測でき、その場合model_requestsは0ではなくnullになる。

POWリポジトリルートで、例のファイル名・selectorを対象の実入力へ置き換えて実行する。

```powershell
python -B commands/optimize-latency/scripts/measurement/analyze_timeline.py --session .\private-session.jsonl --database .\private-timing-snapshot.sqlite --thread THREAD_ID --turn TURN_ID --output .\timing-summary-new.json
```

DBを使わない場合は `--database` を省く。出力先は既存ディレクトリ内の**新しいファイル**を指定する。既存baselineは上書きしない。stdoutも同じ匿名化集計JSONのみで、入力パス・thread/turn/call/item ID・Tool名・本文・推論内容・引数原文・絶対時刻を出力しない。引数は合計文字数のみ記録する。診断にも生の解析行を出さない。

完了イベントがないturnは、明示的な `--cutoff-unix` がないと失敗する。観測済みの最終イベント以降のUnix秒を指定した暫定集計は `complete: false` とpending件数を返す。最終回答後の完了イベントを含むsnapshotを取得したら、別出力ファイルで再計測する。自動ポーリングや「最新turn」の推測はしない。追記中sessionの不完全な最終JSON行だけは無視してフラグを返し、それ以外の壊れたJSONは失敗する。

区間の優先順位はTool待ち→文章stream→Tool引数stream→reasoning項目stream→requestから最初の項目→その他。重なりを二重加算せず、合計がtask_startedからtask_completeまたは明示cutoffまでに一致することを検証する。この開始はsubmissionやUI受付ではないので、その前の待ち時間は含まない。model_requestsはログで観測した件数で、欠落ログから真の要求数を保証する値ではない。

model_event_gapsには、出力項目を見つけられないrequest、未完了項目、対応しないdone、複数候補があって推測できないdispatchの件数を返す。対応不能を見つけた結果は精密な原因帰属として使わない。たとえ分類の算術が一致しても、元ログの欠落がないという証明にはならない。

```sh
python -B -m unittest discover -s test -p "test_measurement*.py" -v
```

同梱テストは架空の機密文字列を含むローカルfixtureで、選択したturnの範囲、重なりと算術、識別子・本文の非出力、DBの不変性、WAL拒否、暫定pending、不完全な最終行、曖昧なdispatch、baseline保護を確認する。実ユーザーの会話やDBはテストで読まない。

### UIに見えるコマンド長とモデル引数を分ける

シェルカードには、モデルが渡した`cmd`に加えて、実行器が選んだPowerShellの絶対パス、起動オプション、引用符を含む解決後のコマンドが表示されることがある。今回のTool要求でも、短い`cmd`がUI記録では長いPowerShell呼び出しへ展開された。カードの全長をそのままモデルが生成した文字数として数えない。

raw response_itemのinput/arguments、実際のTool要求、実行後カードのcommandを対応させる。alias/保存スクリプトは繰り返すモデル引数を短くできるが、ホストが表示する外側のruntimeパスまで消す仕組みではない。両者の差を確認してから、引数生成・輸送・プロセス起動のどこを改善したか判断する。
