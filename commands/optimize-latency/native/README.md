# Codex本体のTool admissionとDesktop接続

このディレクトリは、JavaScript proxyを使わない生のTool dispatchにも上限を設けるためのnative patch、検証入口、Desktop接続補助を扱う。[Nodeスケジューラー](../references/scheduler.md)のDAG・リソース排他と、本体のadmissionは別の実装。現在のDesktopプロセスへの適用成功は確認していない。

## 対象版と確認済みの段階

| 対象 | 確認結果 | 適用範囲 |
| --- | --- | --- |
| CLI 0.156.1 | 8 native tests、直接ToolとCode Modeのsandbox検証成功 | 過去の独立CLI。本番Desktop用として使わない |
| Desktop対応 0.164.0-alpha.11.1 | 実行器ビルド成功、実Code Mode→exec_command→Windows unelevated sandboxで終了コード0 | 版一致するカスタム実行器の隔離検証。live Desktop未切り替え |
| Desktop対応版の正式release build | 完成。unelevated・MXC両経路で実コマンドexit0、native admission確認 | 修正後releaseの隔離検証成功。live Desktopは再起動待ち |
| Desktop対応版のnative tests | 初期8件成功後、レビューで待機中キャンセルを修正。追加回帰を含む9件成功 | 修正後sourceの検証。旧exeの再利用を意味しない |
| Desktopユーザー環境への設定 | 2026-10-28にenable・Windows通知・User値の照合が成功 | 次回起動用設定済み。現Desktopは未切り替え |

最終releaseの証拠は[2026-10-28の記録](../references/data/native-release-2026-10-28.json)。exe SHA-256は`15d458361b6d972f3b8b25755049dc25534de02a65c6cb868cbe7527c8b6bcbd`、修正後patch SHA-256は`99b648ea8a035ea16c9413d773f5ab49df6cbbdefbb1102c4002c0d3c7345a7c`。通常Tool上限16、Guardian予約1で次回Desktop起動の実行器を設定し、2値を再読取して一致を確認した。16は親＋最大15 Agentを妨げにくくする設定上の選択で、最適値を比較実験で求めた数ではない。別プロセス・ExecServerのみの経路・provider hosted Toolまで制御する意味ではない。

下記exe/patchのSHAは初期dev版の履歴である。27日のproof JSONは当時の状態を残し、最終releaseは28日の別記録で区別する。

Desktop対応版の基点は公式タグ `rust-v0.164.0-alpha.11.1`、commit `6905ecede7816e91373e9eabda3f6b0368fc747b`。調査時のvendor exe SHA-256は `1103e9e09c71fa2cd0afd6d8f3b9a2d63174fe8efd7cb5bd09f1cb14ef58a098`、ビルドしたカスタムexeは `33df991bcfacc632d942a140b5a03ef68821eae36ff466ae21088ffe48a3f53b`。patch SHA-256は `8e5544e74e2303194cac57a82708d7b0300db2b19bdf17f4056d50d28b1aa18e`。再ビルド結果のハッシュが同じになる保証ではない。

カスタム実行器はRust 1.95で `cargo +1.95.0 build -p codex-cli --bin codex` を実行して成功。これはdev opt0版のE2E確認用ビルドで、最適化済みreleaseの速度測定ではない。元のvendor releaseより遅くなる恐れがあるため、このdev版へ常用切り替えしない。レビューで待機中キャンセルを修正し、追加回帰を含む9件が成功した。修正済みsourceの正式な `--release` ビルドと両sandbox経路の実行確認は28日に完了した。最終配置先でもMXC経路を再確認してから次回起動用設定を反映した。dev版のE2E成功をrelease版の稼働確認として扱わない。同じ版のDesktop helper群5ファイルを変更せず対応させた実行パッケージで隔離検証した。exeだけを違う版のhelper群と混ぜない。exeやユーザー設定バックアップはGitへ同梱しない。

## 何を自動的に制限するか

パッチは共通の `handle_any_tool` 経路で実行開始を調整する。通常のLeaf Toolはプロセス全体で共有するFIFO semaphoreのN枠へ入る。Code Mode内のネイティブcallbackも同じ経路を通るため、呼び出しごとのJavaScript wrapper定義を必要としない。

外側のCode Mode exec/wait、Agent調整、ユーザー入力待ちは明示的なControl metadataを使い、外側が枠を握ったまま内側ToolやAgentを待つデッドロックを避ける。metadataはwrapper越しにも保持する。Guardianによる正規のレビュー経路は、実際のturn.session_sourceを既存のcanonical判定で確認し、通常N枠とは別の最大1枠のreview reserveへ入る。引数内の文字列や任意Tool名をレビュー経路の認定に使う仕組みではない。

`CODEX_NATIVE_TOOL_CONCURRENCY` が未設定ならこの制限は無効。不正な値はfail closed、設定可能な整数範囲は1〜1024。上限を上げるだけで速度改善するという証拠はない。

承認・sandbox・既存の並行可否判定を置き換えない。Control経路を含むすべての呼び出しを単純なN枠へ押し込む仕組みでもない。プロセス間の共有quota、DAGのcritical-path優先、read/writeキーの推測、JavaScriptのawait書き換え、ExecServerだけを通る独立経路までの保証は含まない。provider側で実行されるhosted builtinは、ローカルdispatchの対象外。

## どう検証したか

実モデルの代わりにloopback provider fixtureを使い、実際のカスタムバイナリへTool callを供給した。Desktop対応版ではCode Modeからexec_commandを呼び、native admission traceでN=1・review reserve=1を確認し、readonly・never承認設定のWindows unelevated sandbox内で実コマンドの出力と終了コード0を取得した。fixtureへの要求は2回、有料モデル要求は0回。

隔離した子プロセスではplugin起動を無効化し、ChatGPT baseもloopbackへ向け、外部通信を発生させない構成で確認した。ユーザーの通常環境に同じ検証用設定を適用するものではない。Desktop対応版のauthoritative catalogはCodeModeOnlyのため、直接Tool呼び出しはそのcatalog条件下でadvertiseされず、対応版の直接Tool E2E成功までは主張しない。0.156.1の直接Tool成功を別版の証拠に転用しない。

原調査のartifact名は `desktop-native-investigation/build-receipt.json`、`verification.json`、`build.log`、`dispatch-proof-loopback-only/code_mode/result.json` と `native-trace.jsonl`。これらのローカル生ログやソースcheckoutはそのまま公開しない。公開用の集約記録は[測定資料](../references/measurements-2026-10-27.md)と各版の同梱receipt・patchを確認する。

## 入口と導入するSkill

POWが追加・更新するSkillは **optimize-latency**。cxd、Node scheduler、native補助スクリプトはその同梱資源で、別Skillではない。

```sh
node scripts/pow.mjs install --name optimize-latency
node scripts/pow.mjs update --name optimize-latency
```

既存RTK 1.0.1とHeadroom 0.41.0は調査環境で確認した別ツール。これらや他のローカルSkillは上記操作で自動導入しない。[RTK/Headroom資料](../references/headroom.md)で明示的な導入範囲を確認する。POWのSkill導入だけではnative実行器やDesktopの接続先も変わらない。

- `scripts/inspect_desktop.py`: 選択したMSIX packageのmanifest、exe SHA、ASARに見える内部overrideキーを読み取る。`--probe-version` を付けた場合だけvendor exeへ `--version` を実行する。
- `scripts/activate_desktop.py`: 次節のplan/enable/disable。2つのユーザー環境変数だけを所有状態つきで扱う。
- `scripts/native_launcher.py`: 0.156.1独立CLI用のreceipt照合と子プロセス環境の入口。Desktop activationとは別。
- `scripts/prove_native_dispatch.py`: 版に対応したカスタム実行器の隔離fixture。実行可能な引数は各スクリプトの `--help` で確認する。検証結果の版・binary SHAを保存する。

通常のアプリ開発のたびに本体forkを作り直す必要はない。まず[調査方法](../references/investigation.md)で支配的な遅延と必要な適用境界を確認する。コマンドだけならcxd、制御できる複数Toolタスクならproxy、本体dispatchへの強制的な上限が必要な場合にnativeを検討する。

---

# Desktop用ネイティブ実行器の明示的な切り替え

`activate_desktop.py` はWindowsのユーザー環境変数を使い、**次の新しいDesktopプロセス**が使う実行器を選ぶ補助ツール。現在動いているDesktopを切り替えるものではない。今回の端末ではenableと環境通知を実行済みで、Desktop終了・再起動は未実施。以下のconcurrency=3は一般例であり、既存の所有stateがある場合はその値（今回16）と一致させる。

調査対象のDesktop同梱実行器は `codex-cli 0.164.0-alpha.11.1`。以前調査したCLI `0.156.1` とは互換性確認の対象版が異なる。カスタム版は実際に使うDesktop同梱vendor実行器との `--version` 完全一致を必須とし、古いCLIのパッチをそのまま接続しない。対象のソース版、ビルド、ネイティブ実行テストの証拠は別途確認する。バイナリがまだ生成・検証できない時点ではplanも成功しない。

## 確認する

Windowsで、実在するカスタム実行器・Desktop同梱実行器・状態ファイルの保存先を明示する。

```powershell
python -B scripts/activate_desktop.py plan --binary C:\native-build\codex.exe --vendor-binary C:\desktop-runtime\codex.exe --concurrency 3 --state C:\workspace\native-activation.json
```

例のパスは利用者が実ファイルへ置き換える。planはレジストリ・状態ファイルを変更しない。次を検査してJSONを標準出力へ返す。

- 両ファイルが存在し、別パス・別SHA-256であること。
- カスタム版に `CODEX_NATIVE_TOOL_CONCURRENCY` と `review_limit` のバイト列が含まれること。
- それぞれの `--version` が終了コード0で10秒以内に完了し、結果が完全一致すること。
- バージョン確認前後で各バイナリのハッシュが変わらないこと。
- concurrencyが整数1〜1024であること。
- 状態ファイルがあれば所有者・厳密なキー・値・型・ハッシュの形式が正しく、現在の設定と衝突しないこと。

ハッシュとマーカー検査は1MiB単位でストリーム処理し、大きなexe全体をメモリーへ読み込まない。マーカーやハッシュは成果物の整合確認であり、署名・出所の信頼・承認・ネイティブテスト成功の証明ではない。実行器を実行してよいかは利用者が判断した上で渡す。`--version` 以外の子プロセスは起動しない。

## 有効化と復元

planの内容を確認した後、同じ引数で `plan` を `enable` に変える。enableはすべての検査を再実行する。書き込み先は次の2値だけ。

```text
HKCU\Environment\CODEX_CLI_PATH
HKCU\Environment\CODEX_NATIVE_TOOL_CONCURRENCY
```

前者はカスタムexeの絶対パス、後者は指定した並行数。両方をREG_SZで設定する。以前の値と型・不存在は先に原子的な状態JSONへ保存し、復元ではREG_EXPAND_SZも元の型のまま扱う。既存値が文字列型でなければ、書き換えず失敗する。PATH、CODEX_HOME、モデル、認証、WindowsApps内のファイル、Desktop設定は変更しない。

状態JSONは復元の所有記録なので、ローカルで保管する。バイナリのパスと変更前の環境変数値を含むため、自動公開しない。状態ファイルの場所は `--state` で毎回同じものを指定する。別の状態ファイルを使った複数の有効化を重ねない。同じ状態ファイルの操作は排他lockで直列化し、既存lockがあれば失敗する。クラッシュ後のlockは実行中操作がないことを確認してから利用者が除去する。

```powershell
python -B scripts/activate_desktop.py disable --state C:\workspace\native-activation.json
```

disableは元の値・型・不存在を復元し、成功後に所有状態を削除する。状態がなければ何も復元せずabsentを返す。カスタムexeが削除済みでも、厳密に検証した所有状態から復元できる。

enable済みの同じ設定は再実行しても上書きしない。状態ファイルと異なるバイナリ・並行数・環境変数になっていれば拒否する。disableも現在値が自分で適用した値か既に復元された元値と一致するときだけ書き戻す。外部の編集を勝手に上書きしない。

レジストリ書き込みが途中で失敗した場合、現在値を確認して元値へ戻す。復元にも失敗した場合や外部編集を検出した場合は所有状態を残し、失敗を報告する。レジストリ2値にOSレベルの原子的トランザクションを提供する機能ではない。失敗を成功として返さない。正常時はJSONを標準出力、診断は標準エラー、失敗終了コードは1。

## 起動環境と適用範囲

環境変数は起動時に継承されるため、現在のDesktopには反映されない。この補助ツールはUIを閉じず、プロセスを強制終了せず、アプリを起動しない。既定ではWindowsの環境変更broadcastも送らないので、既存のExplorerや端末から起動すると古い環境が引き継がれる場合がある。更新されたユーザー環境を持つ起動元を使うか、必要ならサインアウト後に新しく起動する。単にウィンドウを閉じるだけでバックグラウンドプロセスが残るケースにも注意する。

CODEX_CLI_PATHを認識するDesktopと対応するネイティブパッチの組み合わせが必要。設定ファイル・マーカーの存在だけで全Tool経路が有効になったとは報告しない。新しいDesktop実行器の実パスと版を確認し、承認・サンドボックスを保ったまま、生Tool・Code Mode・待機経路のネイティブ検証を行って適用を判定する。

## 検証

```sh
python -B -m unittest discover -s test -p "test_native_activation.py" -v
```

検証コマンドはPOWリポジトリルートで実行する。activation例は本ディレクトリで実行する。テストはRegistry adapterとversion呼び出しをmockし、実際のレジストリ・グローバル設定・Desktopへ書き込まない。バージョン・ハッシュ・マーカー、型と不存在の復元、不正値、外部編集、同時操作、部分書き込み、復元失敗、状態保存失敗を確認する。これはネイティブ本体のテストとは別の検証。

## 環境変更を任意でWindowsへ通知する

enable/disableに `--notify-environment` を付けると、レジストリ操作の成功後だけ標準の `WM_SETTINGCHANGE`（文字列 `Environment`）をWindowsへbroadcastする。Explorer等が更新されたUser環境を読み直し、通常の新規起動へ反映しやすくするための任意機能。planとの組み合わせはレジストリへのアクセス前に拒否し、既定の通知なし動作は変えない。

```powershell
python -B scripts/activate_desktop.py enable --binary C:\native-build\codex.exe --vendor-binary C:\desktop-runtime\codex.exe --concurrency 3 --state C:\workspace\native-activation.json --notify-environment
python -B scripts/activate_desktop.py disable --state C:\workspace\native-activation.json --notify-environment
```

通知には標準ライブラリctypesから `SendMessageTimeoutW`、`HWND_BROADCAST`、`SMTO_ABORTIFHUNG` を使い、APIのtimeoutは2秒。broadcastのtimeoutは各windowへ適用されるため、補助ツール側の待機もdaemon threadで最大3秒に制限する。実行中Desktopや既存PowerShellのProcess環境を変更・再起動する処理ではなく、通知成功でも全受信側の更新を保証しない。

結果JSONの `environment_notification` は `sent`、`failed_or_timed_out`、`failed`、`wait_timed_out` を区別する。全体待機の期限切れでは `delivery_unknown: true` とし、通知が届かなかったと断定しない。通知の失敗・期限切れはレジストリ成功の `registry_configured` / `restored` と分けて記録し、成功済みの環境設定や復元をrollbackしない。通知だけの失敗でCLIを失敗終了にはしない。`running_engine_verified: false` と `restart_required: true` も維持する。通知要求を省略した結果には追加fieldを出さない。

この通知を使っても、次節の2値だけをコピーする明示的な新規起動手順は利用できる。テストではRegistryとWindows APIをmockし、実レジストリ・実通知は実行しない。

## 新しいDesktopプロセスへ2値だけ渡す

enableのJSONで `status: "registry_configured"` はユーザーレジストリの設定完了を意味する。実行中エンジンの切り替えを意味しない。plan/enable/disableはすべて `running_engine_verified: false` と `restart_required: true` を返す。

現在のアプリを利用者が閉じ、対象のMSIX配下のChatGPT.exe実パスを確認してから、新しいPowerShellで次を実行する。パッケージを1件に確定して実パスを取得する。enableと同じconcurrencyを指定し直し、アプリ更新後も現在のvendor版と一致するかplanを再実行する。これは補助ツールが自動実行する処理ではない。

```powershell
$package = @(Get-AppxPackage -Name OpenAI.Codex)
if ($package.Count -ne 1) { throw '対象のOpenAI.Codexパッケージを1件に確定できません' }
$DesktopExe = Join-Path $package[0].InstallLocation 'app\ChatGPT.exe'
$VendorExe = Join-Path $package[0].InstallLocation 'app\resources\codex.exe'
if (-not (Test-Path -LiteralPath $DesktopExe -PathType Leaf)) { throw 'ChatGPT.exeが見つかりません' }
# $ActivationState: enableで使った状態JSONの絶対パス
if (-not $ActivationState) { throw 'enableで使ったActivationStateを設定してください' }
$custom = [Environment]::GetEnvironmentVariable('CODEX_CLI_PATH', 'User')
if (-not $custom) { throw 'カスタム実行器がUser環境に設定されていません' }
python -B .\scripts\activate_desktop.py plan --binary $custom --vendor-binary $VendorExe --state $ActivationState --concurrency 3
if ($LASTEXITCODE -ne 0) { throw '現在のDesktop同梱版との再確認に失敗しました' }
foreach ($name in @('CODEX_CLI_PATH', 'CODEX_NATIVE_TOOL_CONCURRENCY')) {
    $value = [Environment]::GetEnvironmentVariable($name, 'User')
    [Environment]::SetEnvironmentVariable($name, $value, 'Process')
}
Start-Process -FilePath $DesktopExe -WindowStyle Hidden
```

この手順は2値だけをUser環境から起動元PowerShellのProcess環境へコピーする。ほかのユーザー環境変数や認証値はコピーしない。既存Desktopプロセスが残っていると、そのプロセスへ接続するだけの場合がある。起動コマンドの成功だけでは切り替え成功と判断せず、新しい実プロセスの実行器パス・版とネイティブ検証結果を確認する。

この環境変数による起動経路は調査対象の実装で確認した内部の仕組みで、公開された安定APIという保証はない。パッケージ構成・バージョンが変わった場合は再確認する。

## ソースから再構築する

公式公開ソースだけを取得し、対象版を固定してから対応patchを適用する。以下はDesktop対応版の例。POWのcheckoutの絶対パスを`POW_ROOT`へ指定し、新しい作業ディレクトリで実行する（Windows PowerShellでは環境に合う変数記法に読み替える）。

```sh
git clone --branch rust-v0.164.0-alpha.11.1 --depth 1 https://github.com/openai/codex.git codex-native
cd codex-native
git rev-parse HEAD
# 6905ecede7816e91373e9eabda3f6b0368fc747b と一致すること
git apply --check "$POW_ROOT/commands/optimize-latency/native/patches/codex-0.164.0-alpha.11.1-native-admission.patch"
git apply "$POW_ROOT/commands/optimize-latency/native/patches/codex-0.164.0-alpha.11.1-native-admission.patch"
cd codex-rs
cargo +1.95.0 test -p codex-core --lib native_scheduler
cargo +1.95.0 build --release -p codex-cli --bin codex
```

実行にはその版のupstream開発環境（Rust、C/C++ linker、protobuf等）が必要。初回は依存取得が必要なのでofflineを指定しない。調査端末では取得済みcacheを使うため`--offline`で検証した。標準toolchainを変更せず`+1.95.0`を明示した。upstreamのtoolchain指定は別版の場合があり、この資料は任意の将来版で1.95が使える保証ではない。

`git apply --check`が失敗する版へ強制適用しない。Windowsでは`target/release/codex.exe`、Linuxでは`target/release/codex`が生成される。Linuxのnative本体のビルド・Desktop接続はこの調査では未検証。cxdのWindows/Linux検証と区別する。WindowsのDesktopへ配置する場合は、版一致するvendor helper群を別のローカルディレクトリへ揃え、元の署名付きパッケージを直接変更しない。

調査した0.164のWindows packageでは、`codex.exe`と同じ配置に`codex-code-mode-host.exe`、`codex-command-runner.exe`、`codex-windows-sandbox-service.exe`、`codex-windows-sandbox-setup.exe`、`rg.exe`を対応させた。これらは同じvendor packageの未改変ファイルを使い、それぞれのSHA-256もローカルreceiptへ記録する。別版のhelperを流用しない。配布物の構成が変わったら再調査する。

0.156.1の再現はタグ`rust-v0.156.1`、commit`b412ff32c417f855c2b2d1581b77058eed87c84b`と`codex-0.156.1-native-admission.patch`を使う。Desktop向けの0.164patchと混在させない。

隔離dispatchの確認はPOWルートから次のように行う。receiptには自分のビルドexeのSHA-256を記録する。過去のreceiptで新ビルドの同一性を確認しない。

```sh
python -B commands/optimize-latency/native/scripts/prove_native_dispatch.py --binary CUSTOM_EXE --receipt BUILD_RECEIPT --output NEW_LOCAL_OUTPUT --mode code_mode
```

fixtureは本物のモデル性能を測るものではない。実プロセス・Tool経路・sandbox実行をローカルの固定応答で検証する。出力にはローカルパスと実行ログを含むので公開前に集約する。`direct`は版のcatalog次第で利用できず、0.164ではCode Mode経路を検証した。receiptは成果物照合であり、第三者の署名による配布証明ではない。

### Windowsビルドの調査上の注意

Cargoは作業ディレクトリから`.cargo/config.toml`を探索する。親workspaceから`--manifest-path`だけ渡す実行と、`codex-rs`へ移動した実行は同条件ではない。今回の正式ビルドは`codex-rs`をcwdとし、公式MSVCのstack設定と`+crt-static`を適用する。誤ったcwdで開始した試行は停止し、別ログとして保持した。

対象タグのCargo.lockにはworkspace packageの版が0.0.0のものが残り、Cargoが166項目を0.164.0-alpha.11.1へ正規化した。削除・追加行の対応を確認し、外部依存の変更はなかった。これはnative schedulerの差分とは別の生成差分として記録する。

サンドボックス内でvendored protocがWindows DLL再配置エラー623を返した試行は、同じ実行ファイルの`--version`を承認された通常実行で比較し、そちらは`libprotoc 31.1`で成功した。source、認証、sandbox設定の恒久的な変更で回避せず、ビルド処理を適切な権限経路で実行する。失敗時間も調査費用であり、schedulerの処理時間やモデル推論時間へ分類しない。

正式releaseビルド中の一回の資源観測では、端末RAM31.22GiBに対し空き0.71GiB、rustcのworking set18.97GiB・private memory25.66GiBだった。累積CPU時間は5225秒（複数coreの合計であり壁時計ではない）。メモリー余裕が少ない状態を確認したが、単一snapshotから遅延の何%がpagingだったかは求めない。他の重いbuildを追加せず、ユーザーのアプリ・WSL・保護設定を停止/変更して数値を改善する操作は行わなかった。

### スリープを計算時間へ混ぜない

今回の継続ビルドでは日付変更後もprocessが残っていた。WindowsのSystemログ（Power-Troubleshooter、event1）のSleepTime/WakeTimeから、途中に13時間41分52秒のスリープ区間を確認した。再開後は同じrustcが1秒あたり約1.83秒の累積CPUを使っていた。これは複数coreで稼働している観測であり、14時間超の壁時計を全てコンパイラーやモデルの処理時間とは扱わない。

監査ではowned PIDの開始時刻・CPU増分、buildログ末尾、成果物の有無、OSのsleep/resumeイベントを組み合わせた。SleepTime/WakeTimeには端末利用時刻が含まれるため、公開版には期間だけを残す。電源設定を変えていない。ビルド結果のraw経過時間と、スリープを除いた概算覚醒時間も区別する。CPU時間の合計をそのまま壁時計から引かない。

コンパイラーの差も残る。対象sourceのrust-toolchain.tomlは1.99.1を指定しているが、この検証は既存の追加済み1.95を使った。1.99.1が入手不可だったという証拠はない。1.95でdev・core tests・releaseの主要crateが通ったことは、その版が最低要件だという保証でも、推奨toolchainとの性能比較でもない。特にLTO時間への影響は未比較である。再現時はこの差を記録し、推奨版を使う場合も新しいbuild/proofとして保存する。

## 版固定overrideの更新時の扱い

User環境のCODEX_CLI_PATHはDesktop更新後も残る。現在版との一致を確認するplanはenable時・明示的な起動前に実行するもので、通常のショートカット起動に将来の自動互換性判定を追加したものではない。Desktop更新時はoverrideをdisableし、新vendor版に合わせて再build・proof・enableする。署名付きWindowsApps本体と自動更新設定は変更していない。
