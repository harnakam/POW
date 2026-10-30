# Codex native hook の登録

`scripts/install_codex_hooks.py` は、インストール済みの `cxd/native_hooks.py` を Codex の lifecycle event に接続する。ユーザー共通の `$CODEX_HOME/hooks.json` に所有 group を追加し、RTK や他の hook、未知の設定キーを保持する。既定の `CODEX_HOME` は環境変数、未指定時は `~/.codex`。

```powershell
python -B scripts/install_codex_hooks.py plan --runtime "C:\path\to\pow-cxd\native_hooks.py"
python -B scripts/install_codex_hooks.py install --runtime "C:\path\to\pow-cxd\native_hooks.py"
python -B scripts/install_codex_hooks.py status
python -B scripts/install_codex_hooks.py uninstall
```

別の環境へ登録するときは全コマンドに `--codex-home <directory>` を指定する。Python は実行中の interpreter を使い、`--python <executable>` で明示できる。`--runtime` の既定値は `~/.local/share/pow-cxd/native_hooks.py`。`plan` と `install` は実在する runtime と interpreter を必要とし、runtime 自体はコピーしない。

`plan` は書き込まず、追加する全 handler、書き込み先、内容の SHA-256、削除先を JSON で返す。`install` だけが登録・更新し、再実行では同じ group を重複追加しない。成功は exit 0、設定の不整合や書き込み失敗は stderr の説明と exit 1。

| Event | Codex 側の実行 | Timeout |
| --- | --- | --- |
| `SessionStart` | 同期 | 5 秒 |
| `UserPromptSubmit` | 同期 | 5 秒 |
| `PostToolUse` | 同期 bridge | 60 秒 |
| `Stop` | 同期・必須 job の合流 | 60 秒 |
| `SessionEnd` | 同期 | 3 秒 |

`PostToolUse` は native の `async: false` を明示する。bridge が各プロジェクトの sync / async 指定を扱うため、同期 hook は tool の呼び出しに合流し、非同期 hook は cxd へ投入して戻る。native handler 全体を非同期にすると、この同期指定を保てない。

Windows の native hook はセッションで選んだ shell を使い、未指定時は `cmd.exe` を使う。`commandWindows` は両方で動く形式を使う。Python の絶対パスが英数字・`_:/\\.-` のみで、runtime パスに shell 展開文字がない場合は Python を直接起動する。それ以外は `powershell.exe -NoProfile -NonInteractive -EncodedCommand` で引用を保持する。payload は絶対パスを単一引用符で囲み、apostrophe を escape する。空白、Unicode、`%`、`!` を含むパスも shell 展開せず渡せる。fallback では子 PowerShell の起動費用が加わる。POSIX の `command` は shell 引用する。

所有情報は `$CODEX_HOME/.pow/native-hooks/receipt.json` に置く。所有 marker は `[pow-native-hooks:v1] EVENT`。receipt は matcher group 全体を記録するため、所有 handler の変更・削除・重複、または所有 group への別 handler の追加があれば、更新と削除を拒否して現状を保持する。無所有の同じ marker も取り込まない。

設定の置換前に `.pow/native-hooks/backups/hooks-<sha256>.json` へ元の bytes を保存し、設定と receipt を atomic replace する。途中で失敗した場合は変更済みファイルを復元する。`uninstall` は所有 group だけを除去し、追加された他の設定を保持する。他の変更がなければ登録前の bytes、または元の「ファイルなし」状態へ戻す。backup は削除しない。並行した install / uninstall は `install.lock` で拒否する。残存 lock は PID と実行中プロセスを調べてから扱う。

feature flag、権限、sandbox、hook の信頼設定は変更しない。`status` はローカルの `features.hooks` または `features.codex_hooks` の明示値を表示するだけで、実行可能・信頼済みという判定には使わない。登録後の信頼確認は Codex の標準フローを使う。[公式 hook 仕様](https://learn.chatgpt.com/docs/hooks)にある `commandWindows`、同期 / 非同期、`SessionEnd` の制限に従う。
