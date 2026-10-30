# Codexで自動発火するPOW hooks

CodexのSessionStart / UserPromptSubmit / PostToolUse / Stop / SessionEndを、既存cxdのhookへ接続する。イベントを手動でemitする必要はない。対象プロジェクトは明示的に登録し、既存RTKなどのhookは保持する。モデル、認証、承認、sandboxを変更しない。

## 実行の流れ

1. UserPromptSubmitで宣言した全入力をbytesから読み、初期状態を記録する。promptやtranscript本文は保存しない。
2. PostToolUseでも対象treeを列挙し、追加・削除を確認する。前回とstatが同じファイルは内容hashを再利用し、変更候補はbytesを読む。入力の差分と走査件数・読込量を記録する。
3. 入力が変わった場合、同期afterChangeとそのイベントで必要な合流はその場で実行する。非同期afterChangeだけは静穏待ちと最大待ち時間で編集burstをまとめ、短命workerから既存cxdジョブへ投入する。Stopまで待ち続ける方式ではない。
4. 同じターン・同じ入力は同じ実行へ合流する。実行中の編集は次の入力世代として保持し、古い世代の完了を現在の入力の成功として公開しない。
5. Stopは保留workerを失効させ、蓄積した最新入力を待機窓なしでflushする。全入力をbytesから再確認し、実行中の仕事と最後のafterChange・beforeCompleteへ合流する。完了確認中の再変更も検出する。
6. 失敗は種別と証拠の場所を保ったままStop継続理由へ返す。既定1回の継続を使い切った場合は未完了を明記して停止する。同じ失敗・入力で検証を反復しない。

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
  "profileOnStop": true,
  "editQuietMs": 200,
  "editMaxMs": 1000,
  "editWorkerSeconds": 60
}
```

既定のイベント対応はsessionStart / turnStart / afterChange / beforeComplete / sessionEnd。必要ならcodexHooks.eventsでnativeイベント名から論理名への対応を指定できる。afterChangeはinputsまたはinputRootsを必須とする。inputRootsは最大8個のディレクトリで、追加・削除も検出する。Git、依存、生成物、POW状態などを除外し、最大2000ファイル・総32 MiB・各2 MiBに制限する。上限超過は範囲を狭めて解決し、無視して通過させない。

blockingな非同期hookの合流先にはStopに対応する論理イベントが必要。そこへ合流するhookはturnStartかafterChangeで起動する。SessionEndはadvisoryなのでonFailure:recordを指定する。同期bridgeの内側でhookごとの非同期を扱うため、Codex側のPostToolUse handlerはasync:falseのままにする。

`editQuietMs`は最後の変更からの静穏待ちで、既定200、範囲0..5000 ms。`editMaxMs`は最初の保留変更からの上限で、既定1000、範囲editQuietMs..10000 ms。先に達した時点で最新世代の投入を試みる。既存実行との資源競合があれば終了を待つため、最大待ち時間はコマンドの開始期限を保証しない。`editWorkerSeconds`は短命workerの生存上限で、既定60、範囲1..300秒。期限超過や起動失敗で保留入力を成功扱いせず、Stopで最新入力を確認する。workerは常駐サービスではなく、追加のLLMや外部依存も使わない。

statの再利用は変更検出の費用を減らすための観測であり、検証成功のキャッシュではない。UserPromptSubmitとStopはstatが同じでも全bytesを読む。入力状態が欠損・不正な場合は再構築する。宣言した範囲と上限、symlinkを拒否する条件は維持する。

## 失敗の記録

結果の`failure`は`kind`、`retryable`、`exitCode`、`evidencePath`を持ち、該当する場合は`jobId`と`nextAction`を含む。コマンドの非0終了、spawn失敗、timeout、依存失敗、worker中断、pending、stale、設定・認可の不整合を、観測できた原因に応じて区別する。元の終了コード、stdout/stderr、runner.log、result.jsonは既存の実行記録に残す。

stderrの単語からpolicy拒否や一時的通信障害を推測しない。原因を特定できない古い記録はunknownとして扱う。失敗記録は`retryable:false`とし、同じ失敗・入力を自動再実行しない。busyやpendingの待機と、失敗した検証の再実行は分ける。

Windowsで公開直後のJSONに共有handleが残る場合は、既存のI/O guardでファイル読込だけを最大250 ms、呼び出し側の残り期限以内で待つ。チェックは再実行しない。読み取れないままなら`evidence-unavailable`と正確なpathを保持し、実行結果を失敗へ書き換えない。その他のOSアクセスエラーも設定不正と区別する。

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
node scripts/pow.mjs /hooks native configure --workspace <repo> --hook <id> --edit-quiet-ms 200 --edit-max-ms 1000 --edit-worker-seconds 60
```

configureは既定でプレビューのみ。`--edit-*`はプロジェクト全体の集約設定を変更する。applyでは一般のhookとnative固有条件を先に検証し、元の設定を保存して反映・再登録する。変更を検知した設定は上書きせず、登録失敗時は元のbytesへ戻す。実行中のcycleは書き換えない。公開や破壊的なコマンドの登録には別途明示許可とレビューが必要で、ツール自体はコマンドの副作用を証明しない。

最適化は同じhook設定・コマンドの実装・platformの集団からp50/p95、待機、失敗、重複抑止を集計する。入力内容の異なる件数も表示する。入力の鮮度判定と計測集団を分けるので、普通にコードを変更しながら記録を蓄積できる。入力ごとの費用の違いは残り、速度改善率や品質保証へ読み替えない。3件以上の成功記録などの条件を満たした候補だけを表示し、自動変更はしない。

セッション状態は.cxd/hooks/native/以下、共有入力観測は.cxd/hooks/input-state.json、実行の証拠は既存.cxd/async/以下。Stopでprofileを保存し、CLIからも集計を取得できる。workerの所有権はOSロックと記録したtokenで確認し、残ったロックファイルの存在だけで稼働中とは判定しない。native handlerは最大60秒、呼び出し内の待機は最大45秒で、短命workerの生存上限とは別。SessionEndは短く扱う。未完了を成功扱いして無制限に待たない。

採用した原理は[既存調査のP0上位3件](https://github.com/harnakam/POW/blob/main/docs/research/2026-10-30-popular-repo-inspiration.md)に対応する。[Nxの世代照合とRuffの入力cache](https://github.com/harnakam/POW/blob/main/docs/research/2026-10-30-inspiration-runtime.md)を参考に観測と成功判定を分け、[Turborepo PR #14857](https://github.com/vercel/turborepo/pull/14857)の静穏待ち・上限・実行中の変更保持を小さく取り込んだ。失敗分類は[gooseとminiの調査](https://github.com/harnakam/POW/blob/main/docs/research/2026-10-30-inspiration-agents.md)を踏まえ、実際の終了と証拠を保持する。OSS本体やwatcher基盤の移植ではなく、上流の計測値もPOWの改善率には使わない。

仕様確認: [OpenAI公式hooks](https://learn.chatgpt.com/docs/hooks)、[0.156.1の信頼登録実装](https://github.com/openai/codex/blob/rust-v0.156.1/codex-rs/tui/src/hooks_rpc.rs)。native hookの信頼hashはコマンド定義を対象とし、script内容自体のpinではない。所有しているSkillやscriptの変更も通常どおりレビューする。

## 2026-10-30の実行記録

- 今回の差分追跡ではPOWの宣言入力97ファイル・834,836 bytesを全読込した後、未変更のPost相当の観測は97件を再利用し、内容の再読込は0 bytesだった。tree列挙・stat・起動費用は残るため、ターン全体の速度改善率とはしない。
- 直接実行で3回の連続編集を最新内容の非同期処理1回へ集約した。次のターンで静穏待ち中にStopを呼ぶと最新編集を即時flushした。別の実行では最初の処理が実行中に次の編集を投入し、Stopで両世代を処理、遅延workerによる追加実行は0回だった。
- 実際の同期hookのlock競合はbusyとしてblockし、処理は起動しなかった。exit 9のチェックはcheck-failedと実ログパスを保持し、未変更のPost・Stopを経ても実行数は1回だった。キャッシュの変更・rename・削除・破損復旧と、旧8-module receiptから10-moduleへの更新、未所有helperの保護、所有範囲だけのuninstallも直接実行した。新しいテスト・fixture・検証用harnessは追加していない。
- 実運用のStopで、成功済みresult.jsonの読込に一時的なPermissionErrorが発生した。Win32の実共有lockで同じエラーを再現し、修正後は短い競合から約62 msで回復した。長い競合は指定した40 ms期限でevidence-unavailableとなり、handle解放後も元のcompletedを読めた。実際のコマンド実行数は1回を維持した。
- 既存RTKを保持して5つのhandlerを登録し、0.156.1 CLIと稼働中Desktopの0.164.0-alpha.11.1実行器の双方で、公式hooks/listが5つともtrustedと返した。モデルを起動しない信頼登録では既存の他の信頼状態と設定を保持した。
- 実際のCLIに、使い捨て作業場所でwelcome_back(name)関数を追加させ、一度実行してWelcome back, Adaを得た。hookの手動呼び出しは0回。SessionStart、UserPromptSubmit、PostToolUse、Stop、SessionEndが自動記録された。
- ツールの複数回利用に対して非同期索引は1回、同期構文確認は1回。索引artifactには追加した関数名が含まれ、両実行の終了コードは0。索引の実行器時間は約3.23秒で、Stop時の索引待ちは0秒だった。これは単一の正常ケースで、全体の速度改善率ではない。
- 最初の実CLI起動は、アカウントで非対応の既存gpt-6.1-sol指定によりmodel_not_foundで停止した。CLI一覧にあるgpt-6-solを検証用の単発起動だけに指定して成功した。普段のモデル・認証設定は変更していない。既存MCPの403/認証失敗ログも機能の成功と混同していない。
- 別の直接実行では、読み取りだけのターンでジョブが増えず、不正なソースによるStop拒否の後、同じ失敗を再実行せず継続予算で停止した。不正なnative合流設定はファイルを変更せず拒否した。installerは両Windows shellからの起動、RTK保持、変更済み所有設定の保護、byte単位の復元を確認した。

Linuxでのnative shell起動とDesktop GUI上の対話全体はこの検証では実行していない。起動中セッションの設定snapshotには影響が残るため、新規セッションで登録後の状態を読み込ませる。native hook信頼の確認とCLIによる実開発操作の確認を、GUIでの確認と同一視しない。
