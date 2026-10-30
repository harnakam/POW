# 共通ディスパッチャ cxd — Windows / Linux

Python 3.10以降の標準ライブラリだけで動く、コマンド実行器と読み取りワーカー。名前は `cxd`。LLM、APIキー、追加のPythonパッケージは不要。

hookごとの同期・非同期、重複起動抑止、必須イベントでの合流と計測に基づく設定候補は[hookガイド](hooks.md)を参照。`cxd hooks plan|emit|join|status|profile`を使う。既存の`.codex-dispatch.json`で明示したhookだけを実行する。

Codex自身のイベントから自動発火させる場合は[native統合](native-hooks.md)を明示的に登録する。`hooks native configure`で有効な設定候補を確認し、`--apply`で日々の同期・非同期とtimeoutを調整できる。

## インストールせず試す

POWリポジトリのルートで実行する。Linuxでは `python` を `python3` に読み替える。

```sh
python -B commands/optimize-latency/scripts/cxd/dispatch.py --workspace examples/cxd check
python -B commands/optimize-latency/scripts/cxd/dispatch.py --workspace examples/cxd inspect
python -B commands/optimize-latency/scripts/cxd/dispatch.py --workspace examples/cxd stop
```

サンプルの `check` は、実際の2テストとPython構文確認を実行する。`inspect` は索引更新後に `greet` シンボルを検索する。テスト成功をキャッシュしない。

## 短いコマンドをインストール

POWのSkillインストーラーは、同梱ファイルを配置するだけ。以下のcxdインストールはユーザーが明示的に実行する。

### Windows PowerShell

```powershell
python -B commands/optimize-latency/scripts/install_cxd.py install
& "$env:USERPROFILE\.local\bin\cxd.cmd" --workspace examples/cxd aliases
```

### Linux

```sh
python3 -B commands/optimize-latency/scripts/install_cxd.py install
~/.local/bin/cxd --workspace examples/cxd aliases
```

既定の配置先は `~/.local/share/pow-cxd` と `~/.local/bin`。PATHにbinディレクトリが入っていれば、以降は `cxd` で呼べる。PATH・シェルプロファイル・システムサービスは変更しない。Python実行ファイルの場所はインストール時に固定するため、そのPythonを移動・削除した場合はインストーラーで更新する。

`--bin-dir` と `--package-dir` で両方の配置先を変更できる。status/uninstallにも同じ指定を渡す。既存の別実装のcxdや、所有記録のないディレクトリは上書きしない。旧実験版のcxdが既にある場合は、まず別の配置先で試し、旧版を無断で置き換えない。

```sh
python -B commands/optimize-latency/scripts/install_cxd.py status
python -B commands/optimize-latency/scripts/install_cxd.py uninstall
```

所有ファイルのSHA-256を記録し、ローカル変更があれば更新・削除を拒否して保護する。uninstallは既知の実装ファイル・shim・所有記録だけを個別に削除し、未知のファイルやディレクトリは残す。失敗した更新は元ファイルへ戻す。Windowsでは `%`・`!`・引用符・改行を含むインストールパスは対応せず、書き込み前に拒否する。

## ワークスペースとプリセット

```sh
cxd init
cxd aliases
cxd check
cxd check --events --concurrency 3
cxd check --output .cxd/runs/manual-check
cxd index
cxd symbols main --limit 20
cxd tree --limit 20
```

`init` は `.codex-dispatch.json` のひな形を作り、既存設定は上書きしない。ひな形に `check` は登録されていないため、実在する検証コマンドを登録するか、`examples/cxd/.codex-dispatch.json` を参考にする。`--workspace PATH` を付ければ、呼び出し元ディレクトリに依存せず対象を指定できる。

設定は version=1、`source_roots`（空ではないディレクトリ一覧）、`presets`（名前からジョブ一覧への対応）。プリセット名は英小文字から始まる小文字・数字・ハイフンで、組み込み名は使えない。ジョブには一意な `id` を付け、次のいずれかを指定する。

- `argv`: 引数の配列。要素が正確に `{python}` の場合だけ、実行中のPythonの絶対パスへ置換する。シェル展開やevalは行わない。
- `operation`: 読み取り専用の `index`、`symbols`、`tree`、`syntax`、`timing` と `parameters`。

`cwd` はワークスペース基準で、既定もワークスペース。`depends_on` には前提ジョブのID、`timeout_s` にはプロセス起動後の待機上限を指定する。`syntax` のparametersは `paths`、`symbols` は `query` と `limit`、`tree` は `limit`、`timing` は `path`。制限は既定20件・最大200件。

`timing` は `total_s` が有限・非負であることを確認する。`exclusive_categories_s` があれば、各値と合計も確認する。過去の実験に固有なフェーズ数等は要求しない。この検証自体がCodex全体の時間を収集するわけではない。

コマンドは設定の作成者が指定した権限で通常の子プロセスとして動く。ディスパッチャはサンドボックスではなく、悪意あるプリセットを安全なプログラムへ変換しない。Windows固有の `.cmd` 等を実行するときは、そのOSの起動方法を明示する。設定を異なるOSへ共有する場合は、Python・Node等の共通実行ファイルを使う。

## 常駐読み取りワーカー

```sh
cxd serve --idle-seconds 900
```

`serve` は前景で待機する。別のツール呼び出しや端末から `cxd status`、`cxd index`、`cxd symbols NAME`、`cxd stop` を実行できる。短命なツール呼び出しの子が終了時に停止されるCodex環境では、`serve` を専用execセッションで保持する。通常端末では必要時の自動起動も使える。既定15分の無操作で終了する。

コード更新前には対象ワークスペースで `cxd stop` を実行する。稼働中のワーカーを自動的に新実装へ差し替えない。`worker.lock` はOSロックを保持するためのファイルで、正常終了後も残る仕様。ファイルの存在だけで稼働中とは判断しない。終了要求はPIDとワーカーごとのトークンに一致する対象だけに適用する。

通信は `.cxd` 内の要求・応答ファイル。WindowsはWin32変更通知、Linuxはinotifyとselectで待機する。TCPポート、任意Pythonコード評価、外部サーバーは使わない。常駐側はワークスペース内の読み取りだけを受け付け、コマンド実行は呼び出し側の分離されたプロセスで行う。

AST・クラス・関数・importの索引は内容ハッシュで更新する。変更・削除・構文エラーを反映し、同じ内容の索引を書き直さない。対象言語はPython。シンボル検索結果はJSONに含み、件数超過時は `truncated` を返す。

## OSとファイルシステムの条件

- Windows: Win32ファイル通知とプロセス機能を使用する。
- Linux: inotifyとPOSIXロック、0700の状態ディレクトリを利用できるローカルファイルシステムが必要。
- WSL: Linux側のファイルシステム上のワークスペースを使う。Windows共有の `/mnt/c` 等では通知・権限の挙動が異なり、cxdワークスペースの対象外。Windows側のcxdを使うか、Linux側へ配置する。状態ディレクトリのPOSIX権限が成立しない場合は明示的に失敗する。
- macOS: 常駐通知は未対応。POW本体の既存サポート範囲とは別。

`.cxd` にはログ、索引、PID、経過時間、元のコマンド出力が保存される。秘密情報を出力するコマンドには注意し、ログを自動で公開しない。`.cxd/.gitignore` でGitへの混入を防ぐ。

## 失敗と計測

失敗ジョブは元の終了コードとログを保持し、依存ジョブはblockedにする。独立ジョブは継続する。CLIは全成功なら0、それ以外は非ゼロ。タイムアウト時は、自分で開始したプロセスツリーだけを終了する。OSのプロセス作成そのものを中断する厳密な総時間上限ではない。

結果は `.cxd/runs/<ID>/result.json`、標準出力・標準エラーはジョブ別のログ。`--output` はワークスペース内の新規ディレクトリだけを使え、既存結果は上書きしない。elapsedはコマンドバッチの時間であり、モデルによる引数生成や最終回答を含むタスク時間ではない。イベントJSONは `--events` で取得できる。

検証は `python -B -m unittest discover -s test -p "test_cxd_*.py" -v`。WindowsとLinuxの同じテストをCIで実行し、インストールからshim起動、常駐の再利用・停止、依存順、失敗・タイムアウト、索引・状態・所有境界を確認する。

## 依存関係と非同期実行

`plan PRESET` は依存関係、論理的な読み書き競合、推定クリティカルパスを確認する。`depends_on` は必須の完了条件、`reads` / `writes` は完全一致する論理キーであり、OSのファイルアクセスを自動解析しない。同じキーのread/readは重ね、writeとの競合は直列にする。`estimated_s` は正の有限値。実行可能なジョブを同時実行数まで開始し、完了イベントで次を開始する。

```sh
cxd --workspace examples/scheduler-tasks plan verify-all
ctx -wait verify-all --workspace examples/scheduler-tasks
ctx verify-all --workspace examples/scheduler-tasks
ctx result RUN_ID --workspace examples/scheduler-tasks
ctx wait RUN_ID --workspace examples/scheduler-tasks --timeout 90
```

`ctx PRESET` は `cxd start PRESET`、`ctx -wait PRESET` は通常の同期実行に対応する。startの終了コード0と `submitted` / `running` は受付成功であり、テスト成功ではない。完了はwait/resultのstatusと各ジョブのexit codeで確認する。非同期結果は `.cxd/async/<RUN_ID>/` に保存し、過去結果を使い回さない。waitはrunner終了まで待ち、resultは現在の状態を読む。

Codexでは短命なshellの終了時に子プロセスが停止される環境がある。`--attached --compact` でexecセッションを維持し、同梱 `scripts/cxd/bridge.js` の `functions.exec` / `yield_control` / `notify` を使う。待機はruntime内に置き、モデルによる反復ポーリングを避ける。単にバックグラウンド起動するだけで実行継続を保証しない。

新版インストーラーはcxdとctxの両shimを管理する。既知の旧版所有記録は更新できるが、記録のないctxなどは上書きしない。既存の独自cxdがある場合は `--bin-dir` と `--package-dir` を別ディレクトリに指定して試す。

## Windows応答ファイルの共有競合

CIで応答JSONが存在しても`read_text`がPermissionErrorになるケースを確認した。stop応答を読めず、所有する子プロセスの終了待ちへ到達しないため、cleanupのworker.log/worker.lock占有エラーも連鎖した。実際にハンドルを保持したプロセスはCIログだけでは特定できない。

同じUUIDの応答read/unlinkだけを、既存の要求期限内で最大10ms刻みに再試行する。コマンドを再送せず、恒久拒否は元の例外で失敗し、権限を緩めない。共有ハンドルのcloseではファイル通知が必ず発生するわけではないため、この局所待機は通知待ちと区別する。実CreateFileWで共有を拒否した回復、stop時の一過性拒否と子の終了、期限と元例外保持を回帰テストで確認する。
