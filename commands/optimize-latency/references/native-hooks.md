# Codexで自動発火するPOW hooks

CodexのSessionStart / UserPromptSubmit / PostToolUse / Stop / SessionEndを、既存cxdのhookへ接続する。イベントを手動でemitする必要はない。対象プロジェクトは明示的に登録し、既存RTKなどのhookは保持する。モデル、認証、承認、sandboxを変更しない。

## 実行の流れ

1. UserPromptSubmitで宣言した入力の初期状態を記録する。promptやtranscript本文は保存しない。
2. PostToolUseで入力が変わったときにafterChangeを発火する。各hookのmodeがsyncなら待ち、asyncならcxdジョブへ投入して戻る。
3. 同じターン・同じ入力の重複呼び出しは同じ結果へ合流する。実行中にさらに編集された場合は、最後の入力世代を完了前に確認する。
4. Stopで実行中の仕事を待ち、最後の世代のafterChangeとbeforeCompleteを実行・合流する。完了確認中の再変更も検出する。成功した同一世代の処理は繰り返さない。
5. 失敗はCodexのStop継続理由として返す。既定1回の継続を使い切った場合は未完了を明記して停止する。同じ失敗・入力で検証を反復しない。

読み取りだけのターンでは既定で新しい検証を起動しない。既に動いているジョブの合流は省略しない。常に完了確認が必要ならcodexHooks.verifyReadOnlyTurnsをtrueにする。入力範囲外の変更は検知できない。

## プロジェクト設定

POW自身には[.codex-dispatch.json](../../../.codex-dispatch.json)を同梱した。変更後に既存/updateでworkflow情報を非同期更新し、完了時に既存Skill検証、Node構文確認、Python構文確認を行う。テストや公開は自動実行しない。

一般の設定は[hookガイド](hooks.md)のpreset/hooksへ、次を追加する。

```json
"codexHooks": {
  "enabled": true,
  "waitSeconds": 30,
  "maxStopContinuations": 1,
  "verifyReadOnlyTurns": false,
  "profileOnStop": true
}
```

既定のイベント対応はsessionStart / turnStart / afterChange / beforeComplete / sessionEnd。必要ならcodexHooks.eventsでnativeイベント名から論理名への対応を指定できる。afterChangeはinputsまたはinputRootsを必須とする。inputRootsは最大8個のディレクトリで、追加・削除も検出する。Git、依存、生成物、POW状態などを除外し、最大2000ファイル・総32 MiB・各2 MiBに制限する。上限超過は範囲を狭めて解決し、無視して通過させない。

blockingな非同期hookの合流先にはStopに対応する論理イベントが必要。そこへ合流するhookはturnStartかafterChangeで起動する。SessionEndはadvisoryなのでonFailure:recordを指定する。同期bridgeの内側でhookごとの非同期を扱うため、Codex側のPostToolUse handlerはasync:falseのままにする。

## 登録と信頼

先にoptimize-latency Skillをインストール・更新する。以下のscriptはそのSkillまたはPOWクローンのscripts/以下を指す。

```text
python -B scripts/install_codex_hooks.py plan --runtime <installed-skill>/scripts/cxd/native_hooks.py
python -B scripts/install_codex_hooks.py install --runtime <installed-skill>/scripts/cxd/native_hooks.py
python -B scripts/trust_codex_hooks.py --cwd <repo>
python -B scripts/trust_codex_hooks.py --cwd <repo> --apply
node scripts/pow.mjs /hooks native authorize --workspace <repo>
```

登録・復元の詳細は[installerガイド](native-hooks-install.md)。既存hooks.jsonとconfig.tomlは変更前のbytesをbackupする。信頼helperはCodexのhooks/listが返す実定義と所有receiptを照合し、標準/hooks画面と同じconfig/batchWriteで5つの所有hookだけを信頼登録する。独自の信頼hash生成やtrust bypassは使わない。対象Codexのnative hook機能が有効である必要がある。確認したCLI 0.156.1ではfeatures.codex_hooksが有効だった。別の版ではhook APIと有効化条件を再確認する。

プロジェクト登録はCODEX_HOME/.pow/native-hooks/projects.jsonへ、レビューした設定ファイルのhashを保存する。未登録プロジェクトでは何も実行しない。設定変更後は確認して再authorizeする。親ディレクトリをセッションrootにする場合はauthorize --session-root <parent>で対応を明示する。複数プロジェクトに曖昧に対応する場合は推測せず失敗する。

## 日々の調整

```text
node scripts/pow.mjs /hooks native profile --workspace <repo>
node scripts/pow.mjs /hooks native configure --workspace <repo> --hook <id> --mode async --required-at beforeComplete
node scripts/pow.mjs /hooks native configure --workspace <repo> --hook <id> --mode async --required-at beforeComplete --apply
node scripts/pow.mjs /hooks native configure --workspace <repo> --hook <id> --timeout-s 20 --apply
```

configureは既定でプレビューのみ。applyでは一般のhookとnative固有条件を先に検証し、元の設定を保存して反映・再登録する。変更を検知した設定は上書きせず、登録失敗時は元のbytesへ戻す。実行中のcycleは書き換えない。公開や破壊的なコマンドの登録には別途明示許可とレビューが必要で、ツール自体はコマンドの副作用を証明しない。

最適化は同じhook設定・コマンドの実装・platformの集団からp50/p95、待機、失敗、重複抑止を集計する。入力内容の異なる件数も表示する。入力の鮮度判定と計測集団を分けるので、普通にコードを変更しながら記録を蓄積できる。入力ごとの費用の違いは残り、速度改善率や品質保証へ読み替えない。3件以上の成功記録などの条件を満たした候補だけを表示し、自動変更はしない。

状態は.cxd/hooks/native/以下、実行の証拠は既存.cxd/async/以下。Stopでprofileを保存し、CLIからも集計を取得できる。ロック残留時は記録したPIDと子プロセスを調べて復旧する。native handlerは最大60秒、内部の待機は最大45秒で、SessionEndは短く扱う。未完了を成功扱いして無制限に待たない。

仕様確認: [OpenAI公式hooks](https://learn.chatgpt.com/docs/hooks)、[0.156.1の信頼登録実装](https://github.com/openai/codex/blob/rust-v0.156.1/codex-rs/tui/src/hooks_rpc.rs)。native hookの信頼hashはコマンド定義を対象とし、script内容自体のpinではない。所有しているSkillやscriptの変更も通常どおりレビューする。

## 2026-10-30の実行記録

- 既存RTKを保持して5つのhandlerを登録し、0.156.1 CLIと稼働中Desktopの0.164.0-alpha.11.1実行器の双方で、公式hooks/listが5つともtrustedと返した。モデルを起動しない信頼登録では既存の他の信頼状態と設定を保持した。
- 実際のCLIに、使い捨て作業場所でwelcome_back(name)関数を追加させ、一度実行してWelcome back, Adaを得た。hookの手動呼び出しは0回。SessionStart、UserPromptSubmit、PostToolUse、Stop、SessionEndが自動記録された。
- ツールの複数回利用に対して非同期索引は1回、同期構文確認は1回。索引artifactには追加した関数名が含まれ、両実行の終了コードは0。索引の実行器時間は約3.23秒で、Stop時の索引待ちは0秒だった。これは単一の正常ケースで、全体の速度改善率ではない。
- 最初の実CLI起動は、アカウントで非対応の既存gpt-6.1-sol指定によりmodel_not_foundで停止した。CLI一覧にあるgpt-6-solを検証用の単発起動だけに指定して成功した。普段のモデル・認証設定は変更していない。既存MCPの403/認証失敗ログも機能の成功と混同していない。
- 別の直接実行では、読み取りだけのターンでジョブが増えず、不正なソースによるStop拒否の後、同じ失敗を再実行せず継続予算で停止した。不正なnative合流設定はファイルを変更せず拒否した。installerは両Windows shellからの起動、RTK保持、変更済み所有設定の保護、byte単位の復元を確認した。

Linuxでのnative shell起動とDesktop GUI上の対話全体はこの検証では実行していない。起動中セッションの設定snapshotには影響が残るため、新規セッションで登録後の状態を読み込ませる。native hook信頼の確認とCLIによる実開発操作の確認を、GUIでの確認と同一視しない。
