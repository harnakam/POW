# 実行器と実Tool接続の測定記録 — 2026-10-27

Windowsの調査で得た匿名化集約値。私用パス、スレッドID、会話本文、認証情報、生Tool結果は含めない。原データはローカル調査の `command-actors/async-benchmark.json`、`scheduler-benchmark.json`、`tool-scheduler/benchmark-results.json`、`real-tool-benchmark-final.json`、`real-tool-verification.json`。実装・テスト6ファイルを同じSHA-256のままexamples/scheduler-tasksへ同梱した。生ログと私用パスは公開せず、匿名化した原データは[data/real-tools-2026-10-27.json](data/real-tools-2026-10-27.json)へ保存した。同じソースの検証は再実行できるが、環境差による所要時間の一致は保証しない。

## 実Toolで3つの検証タスクを実行

ジャンケン8テスト、迷路7テスト、TODO・永続化4テストを毎回実行した。sleep・架空の成功・成功結果キャッシュは使わない。実際のexec_commandと、session_idが返る場合のwrite_stdinを通し、実コマンド終了まで待った。

同じソース・引数・タスクに対して、taskConcurrencyを逐次1/並列3で比較し、toolConcurrencyは両方3。順序はABBAAB、各方式3標本。実装・テスト6ファイルのSHA-256は実験前後で一致。6実行すべて各19テスト成功。

| 順序 | 方式 | 完了まで秒 | 最大同時Tool呼び出し |
| --- | --- | ---: | ---: |
| 1 | 逐次 | 21.563 | 1 |
| 2 | 並列 | 5.147 | 3 |
| 3 | 並列 | 5.218 | 3 |
| 4 | 逐次 | 20.058 | 1 |
| 5 | 逐次 | 16.288 | 1 |
| 6 | 並列 | 4.874 | 3 |

中央値は20.058秒から5.147秒。観測差14.911秒、74.34%短縮、比率3.897倍。Tool通信・フック・コマンド起動・テスト・結果確認を含み、モデルのコード生成、Tool引数生成、初回ランタイムbootstrapは含まない。アプリを最初から作る全工程のA/Bではない。

OS負荷・キャッシュ・プロセス起動変動は固定していない。3タスクで比率が3を超えるので、比率全体を並列枠だけの効果とは説明しない。各3標本の観測を普遍的な速度保証へ広げない。初期の各2標本の結果は別保存し、最終比較へ混ぜていない。

## 非同期で親の独立作業を重ねる

2秒コマンドと2秒独立作業をsleepで代替し、両方の完了まで測定した。CLIとジョブのプロセス数を揃え、attached経路、ABBAAB、各3標本。

| 指標 | 逐次 | 非同期 |
| --- | ---: | ---: |
| 中央値 | 8.005秒 | 4.812秒 |
| 最小 | 7.599秒 | 4.496秒 |
| 最大 | 10.035秒 | 6.743秒 |

39.9%短縮、比率1.664倍。ただし差3.193秒は独立作業2秒を超え、起動・スケジューリングの変動も含む。実モデル生成を含む全タスク比較ではない。

別の重なり確認では30秒コマンド中に親が資料とbridgeを生成・保存した。コマンド開始後15.955秒で保存、30.014秒でコマンド完了。保存後も約14.059秒コマンドが継続した。これは実際の生成とコマンドの重なりの証拠で、同条件のモデル生成A/Bやモデル自体の高速化ではない。

単純な切り離し方式では1.2秒コマンド＋0.8秒独立作業が逐次3.212秒/非同期4.755秒（各3標本）、6秒＋4秒が12.880秒/17.143秒（各2標本）となり悪化した。探索中は他検証との干渉もあるため、最終比較から速度差を算出しない。短い仕事は追加プロセスの費用が上回り得る。

## 依存鎖優先の合成負荷

Pythonは独立3件＋依存2件の固定5ジョブ、正確な推定を与えたsleep負荷、各3標本。中央値は逐次485ms、FIFO並列328ms、依存鎖優先250ms。FIFOに対し23.8%短縮。Node側の別負荷はFIFO200.39ms/依存鎖優先142.79ms（各3標本）。負荷が異なるため合算しない。

どちらも起動、実Tool通信、モデル要求を含まない。通知API追加後は正しさのテストのみ再実行し、上記合成比較を再測定していない。推定時間の誤りは正しさを変えないが、性能効果を変える。

## 検証と導入範囲

POW移植後の検証は[検証記録](data/verification-2026-10-27.json)に保存した。初期Node37件、初期cxd44件（Windows2件skip、Linux1件skip）、native補助26件、区間計測10件を確認。後二者もWindows/Linuxで実行した。GitHub CIのNode20/22×Windows/Linux/macOS、Python3.10/3.12×Windows/Linuxが成功。最初のWindows Node CIはbundleの改行変換で失敗し、byte保持のGit属性を追加して再実行した。失敗を除外して成功扱いにはしない。

元のPythonランナー20テスト、Nodeスケジューラー群20テストが成功した記録を確認。依存順、FIFO切り替え、上限、read/read並行とwrite排他、失敗とblocked、通知例外、協調キャンセル、複数タスク共有枠、proxy、await忘れ待機、session_id維持、固定bundleを対象にした。これは調査時点の検証記録で、POWへの移植後の検証結果とは分ける。

実Tool接続はWindowsで確認した。Linuxの実Tool接続は未検証。Python側の一般OS条件とCIは[cxdガイド](cxd.md)を参照。proxyを通ったToolの自動捕捉は確認済みだが、稼働Desktop全体へのネイティブな強制適用は未確認。導入判定に必要な証拠は[調査手順](investigation.md#本体の自動適用を検証する)。モデル品質、認証、セキュリティ保護を下げる変更はこの実験に含めない。

## native本体への接続は別の検証

proxyとは別に、Desktop対応版0.164.0-alpha.11.1のnative dispatch admissionパッチをビルドした。基点commitは `6905ecede7816e91373e9eabda3f6b0368fc747b`、カスタムexe SHA-256は `33df991bcfacc632d942a140b5a03ef68821eae36ff466ae21088ffe48a3f53b`。loopback fixtureから実Code Mode→exec_command→Windows unelevated readonly sandboxを通り、実コマンド終了コード0を取得した。N=1と別review reserve=1をtraceで確認。有料モデル要求0、fixture要求2回。

対応版は初期8 native testsが成功した後、レビューで待機中キャンセルの問題を発見し修正した。実Dynamic Toolの待機キャンセル回帰を含む修正後9 native testsが成功（実行0.40秒、再コンパイル4分07秒）。初期exeのE2Eを修正後binaryの証明に転用しない。過去のCLI0.156.1では別途8 native testsと直接Tool/Code Modeのsandbox検証が成功しているが、別版への転用はしない。稼働Desktopはまだ切り替えていない。実行器の速度比較ではなく、呼び出し経路と通常の権限境界の接続確認である。[nativeガイド](../native/README.md)に制約と再現・接続・復元手順を記録した。

上記Desktop対応exeはdev opt0のE2E用ビルド。元のvendor releaseより遅くなる恐れがあるため、常用切り替えしない。正式なrelease buildはキャンセル修正後の9テスト成功を受け、修正済みsourceで開始した。完了・実行はまだ検証されていない。dev E2E成功はrelease buildの成功・稼働・速度を証明しない。

Windows応答ファイルの共有競合を追加CIで確認し、要求期限内のread/unlinkだけを再試行する修正を追加した。実共有ハンドル・stop時の回復・期限上限の3回帰を加えた最終cxdは47件（Windows2件skip、Linux4件skip）。修正後の全CIが成功した。ハンドル保持プロセスの正体は未特定で、恒久拒否を成功扱いにする変更はない。

Skill配布sourceのPython cache混入も修正した。source除外・旧所有cache移行・未所有cache保護・source symlink拒否を加えたNode最終検証は41件すべて成功（Windowsの承認された通常実行、一時領域はworkspace内）。インストール先の所有検査は除外しない。

## 2026-10-28: releaseと次回起動用設定

修正後releaseのビルドと、unelevated/MXCを明示選択した実dispatchが両方成功した。各2回のloopback provider要求・有料モデル要求0回、実command exit0、native admissionを確認。User環境へ通常16枠＋Guardian予約1の実行器設定を保存し、Windows通知と2値の再照合が成功した。稼働Desktopの切り替えと再起動後の実測は未実施。既存の3.90倍のTool比較はnative版の速度比較へ読み替えない。[release記録](data/native-release-2026-10-28.json)に版・SHA・compiler差・スリープ区間を保存した。
