# 人気リポジトリから得るPOWの強化案

調査日: 2026-10-30。**44リポジトリ**を比較した。Agent、実行基盤、コード探索・整理、UIの4分野に加え、hook・開発タスク・状態管理の6件を掘った。GitHubの実metadata、commit固定の実装、Issue/PR、3論文と利用者の議論を参照した。以下の優先順位はPOWへの設計判断であり、性能の実証値ではない。

最も有望なのは、**変更の追跡を軽くする、古い結果を公開しない、失敗理由を区別する、必要な証拠だけ渡す、UIの状態遷移を確認する**こと。既存のcxd、native hook、hatarake、compressor、design-reasoningを拡張する候補とし、新しいAgent基盤を丸ごと追加しない。

## 調査の見取り図

| 分野 | 対象数 | 掘った設計観点 | 詳細 |
| --- | ---: | ---: | --- |
| Agent・hook・workflow | 9 | 27 | [Codex、OpenCode、aider、SWE/mini、goose、OpenHands、Claude公開資料、superpowers](2026-10-30-inspiration-agents.md) |
| 実行・キャッシュ・イベント | 10 | 30 | [Turborepo、Nx、uv、Ruff、ripgrep、pre-commit、esbuild、Watchexec、BullMQ、Temporal](2026-10-30-inspiration-runtime.md) |
| 情報密度・探索・整理 | 10 | 20 | [Watchman、Knip、Tree-sitter、SCIP、ast-grep、Pyright、Unimport、RTK、Headroom、depcheck](2026-10-30-inspiration-density.md) |
| UI・視覚・操作の品質 | 9 | 20 | [Playwright、Storybook、axe、Radix、React Aria、shadcn、Headless UI、Floating UI、Carbon](2026-10-30-inspiration-design.md) |
| 開発タスク・hook構成・状態管理 | 6 | 18 | 本文の追加比較 |

計115観点。これは異なる115機能の採用数ではなく、重なる原理も含む比較単位。popular判定の補助に観測時のstarsを使い、品質順位には使わない。専門比較のTemporal SDK・SCIP・Unimport、保守停止のdepcheck、engine非公開で公開資料のみのClaude Codeも明記した。各詳細に正規repo、更新、license、固定source、失敗報告、未確認事項を置いた。

## POWで優先したい12件

P0は既存経路に小さく差し込む候補、P1はデータ構造や操作観察の追加が必要な候補。費用は実装規模の判断で、所要日数や速度改善率の見積もりではない。

| 優先 | POWへ加える差分 | 着想元 | 期待する実用上の変化・境界 |
| --- | --- | --- | --- |
| P0 | **変更pathの集約と増分再解析** | Nx、Watchman、Ruff、mise | native callbackごとの全tree・全bytes確認を減らす。通知の欠落、rename、ignore変更、watch再起動では完全照合する。mtimeだけを内容一致の証拠にしない。 |
| P0 | **編集burstの集約と公開時の世代照合** | Turborepo、Watchexec、Nx | 静穏待ちの上限とStopでのflushを持ち、実行中の追加変更を次世代へ残す。既存の同一hash排除とは別に、異なるhashの連続編集をまとめる。 |
| P0 | **失敗種別を保った結果** | goose、mini、BullMQ | policy拒否、設定不正、spawn失敗、処理失敗、timeout、pending、staleを分ける。元のexit codeと原文を残し、retry可能と修正必須を混ぜない。 |
| P0 | **追加LLMなしの復帰capsule** | Codex、mini、superpowers | 原要求、未解決制約、入力世代、成果物hash、実行済み範囲、次の一手を既存stateから生成。要約が原要求を上書きしない。 |
| P0 | **原文へ戻れる証拠出力** | RTK、Headroom、SWE-agent | 失敗行・未解決制約・必要証跡を保護し、省略範囲と回収先を出す。原文保存失敗はrawへ戻す。短い出力には圧縮をかけない。 |
| P0 | **指摘ID単位の再review** | superpowers、Storybook | 変更箇所・指摘・対応証跡だけを渡す。解決済みの全履歴を毎回読ませず、未解決と未確認を残す。新しいreview engineや無限roundを作らない。 |
| P1 | **未使用候補へ入口coverageと確信度** | Knip、Unimport、ast-grep、SCIP | 「参照が見つからない」と「入口から未到達」を分ける。dynamic routeやpluginが未対応なら削除を保留。現在の隔離/restoreを再利用する。 |
| P1 | **native hookの実cwd・call ID・cause追跡** | Codex、goose | セッションcwdと実tool cwdを区別し、どの呼び出しの処理か対応付ける。入力全文を保存せず、別repoの規則を誤適用しない。host版によるfield差も扱う。 |
| P1 | **撮影の成立条件と環境記録** | Playwright、Storybook | fonts、主領域、データ反映、有限motionの完了を有限時間で観察。timeoutを成功にしない。ブラウザ・DPR・scroll・focusを比較可能に残す。 |
| P1 | **UIの関係・復旧を直接観察** | Radix、React Aria、Headless UI、Floating UI、Carbon | dialog close後のfocus・scroll・背面操作、popupと起点、実CSS breakpointの前後だけ確認。画像数を増やすより利用可能な状態へ戻ったかを見る。 |
| P1 | **ownerとcancel/cleanupの分離** | BullMQ、Temporal、Dagger | PIDだけに頼らず所有identityを保持。通常作業の取消後にも短いcleanup予算を与える。lease切れだけで同じ書込を二重実行しない。 |
| P1 | **状態・ログ・キャッシュの費用を管理** | uv、Dagger、just、prek | disk bytes、保持中の参照、metadata件数、起動・待機・実行を分ける。利用中の証拠を消さず、所有する終了済みartifactだけの整理planを作る。 |

根拠・制約は各分野の固定sourceと失敗例に紐づく。上流の数値や成功報告をPOWの改善率として転記しない。Codex本体のtool schema遅延公開はhostの機能であり、POWのhookだけで再実装できると扱わない。

## 追加6件の実装比較

stars・最終pushはGitHub APIで観測。全6件archived=false。licenseは固定HEADのルート本文も確認した。更新頻度だけで保守応答を保証しない。

| repo | stars / push UTC | 固定licenseと着眼点 |
| --- | --- | --- |
| [Lefthook](https://github.com/evilmartians/lefthook) | 8,963 / 10-26 | [MIT](https://github.com/evilmartians/lefthook/blob/13d66a090ac6e73f3ff44652761facb02b00e91c/LICENSE)・順序/並列/失敗後の後続抑止、scope |
| [prek](https://github.com/j178/prek) | 8,701 / 10-30 | [MIT](https://github.com/j178/prek/blob/7ca1efa86853c0b2124cef23dd7921cfba61a3ee/LICENSE)・環境再利用、hookとbatchの並列度 |
| [mise](https://github.com/jdx/mise) | 35,554 / 10-30 | [MIT](https://github.com/jdx/mise/blob/58c91be694fafd1eba72bd2b1532c55157c57f5d/LICENSE)・一括index、入力/出力宣言と監査 |
| [just](https://github.com/casey/just) | 36,482 / 10-27 | [CC0-1.0](https://github.com/casey/just/blob/c7317c85c21ebd83ea4bb8de26f8afec44c7e597/LICENSE)・説明可能なcache key、lock、出力の確認 |
| [Dagger](https://github.com/dagger/dagger) | 16,546 / 10-30 | [Apache-2.0](https://github.com/dagger/dagger/blob/2b5e3a9671a5957a76e757d8b02ecf78e2d953ab/LICENSE)・cache scope、所有lease、cleanup |
| [Bubble Tea](https://github.com/charmbracelet/bubbletea) | 45,556 / 10-28 | [MIT](https://github.com/charmbracelet/bubbletea/blob/67b4c7a8a2b34a0b1ce15261b0c705bc7e1a04b7/LICENSE)・明示した順序、空/単一処理の軽い経路 |

**Lefthook: X01–03。** [controller.go](https://github.com/evilmartians/lefthook/blob/13d66a090ac6e73f3ff44652761facb02b00e91c/internal/run/controller/controller.go#L134)は並列、順次、pipedで失敗後をskipする処理を分ける。[scope.go](https://github.com/evilmartians/lefthook/blob/13d66a090ac6e73f3ff44652761facb02b00e91c/internal/run/controller/scope.go#L51)はjobのglob/root/envを継承し、変更時にenvをcopyする。[guard.go](https://github.com/evilmartians/lefthook/blob/13d66a090ac6e73f3ff44652761facb02b00e91c/internal/run/controller/guard.go#L154)は前後のchangesetを照合する。POWでは「待つか」「何と重ねられるか」「先行失敗で止めるか」を別の契約にする。scopeの凍結と意図しないsource変更の報告を参考にし、自動stash・stage・巻戻しは採用しない。

**prek: X04–06。** [hook.rs](https://github.com/j178/prek/blob/7ca1efa86853c0b2124cef23dd7921cfba61a3ee/crates/prek/src/hook.rs#L549)は言語・repo・依存・言語版で環境を照合する。[concurrency.rs](https://github.com/j178/prek/blob/7ca1efa86853c0b2124cef23dd7921cfba61a3ee/crates/prek/src/concurrency.rs#L35)はhook並列とbatch並列を分け、小入力で起動を細分化し過ぎずargv上限も計算する。[resource_limit.rs](https://github.com/j178/prek/blob/7ca1efa86853c0b2124cef23dd7921cfba61a3ee/crates/prek/src/resource_limit.rs)はFD枯渇を扱う。POWは依存なしを維持し、任意adapterを足す段階だけ環境の共有条件を定める。CPU数だけで全段を並列化せず、FD/process/output容量も上限に含める。OS制限の自動引上げは移植しない。

**mise: X07–09。** [実際のperf commit](https://github.com/jdx/mise/commit/58c91be694fafd1eba72bd2b1532c55157c57f5d)はformula単位の反復取得からbulk indexへ移し、tap再走査も減らしている。置換URLが別の情報源を指す場合には流用しない。[task_cache_audit.rs](https://github.com/jdx/mise/blob/58c91be694fafd1eba72bd2b1532c55157c57f5d/src/task/task_cache_audit.rs#L93)は宣言外read/writeの監査を明示opt-inにし、実装はLinux/strace依存。[task_source_checker.rs](https://github.com/jdx/mise/blob/58c91be694fafd1eba72bd2b1532c55157c57f5d/src/task/task_source_checker.rs#L25)は再実行前に自前の成功markerを無効化する。POWではrootごとの走査を共有し、宣言範囲漏れを調べる任意診断とrun-scoped receiptを使う。過去markerで失敗を隠さず、監視・straceを既定にしない。

**just: X10–12。** [cache_key.rs](https://github.com/casey/just/blob/c7317c85c21ebd83ea4bb8de26f8afec44c7e597/src/cache_key.rs)はbody・環境・executor・入力・argv・cwdを含む。[cache.rs](https://github.com/casey/just/blob/c7317c85c21ebd83ea4bb8de26f8afec44c7e597/src/cache.rs#L11)はkeyを説明でき、file lockを取り、出力が欠けていればmissにする。POWでは失効の理由を読めるようにし、環境値は必要項目のdigest/秘匿表示にする。ただし「出力が存在する」は内容・新鮮さの証明ではない。検証成功をcacheから返す仕組みは採用せず、再利用対象を解析・索引・取得済み資料へ限定する。

**Dagger: X13–15。** [cache_inputs.go](https://github.com/dagger/dagger/blob/2b5e3a9671a5957a76e757d8b02ecf78e2d953ab/dagql/cache_inputs.go)はclient/session/call/schemaと明示generationのscopeを区別。[cache_part_lazy.go](https://github.com/dagger/dagger/blob/2b5e3a9671a5957a76e757d8b02ecf78e2d953ab/dagql/cache_part_lazy.go#L13)は通常cancelとcleanupを分け、成功後に保持closureを解放する。[cache.go](https://github.com/dagger/dagger/blob/2b5e3a9671a5957a76e757d8b02ecf78e2d953ab/dagql/cache.go#L76)はdiskとmetadataの費用を分ける。POWでは共有可能なsource取得とturn内成果物を分け、cleanupにも上限を置き、利用中artifactを整理から除外する。コンテナengine・e-graph・分散cacheは移植しない。

**Bubble Tea: X16–18。** [commands.go](https://github.com/charmbracelet/bubbletea/blob/67b4c7a8a2b34a0b1ce15261b0c705bc7e1a04b7/commands.go#L7)は順序保証のないBatchと順次Sequenceを別にし、空ならnil、1件なら直接返す。Tick/Everyは1回の通知で、繰り返すなら明示的に再投入する。POWでも空イベントと単一hookを軽くし、状態変更と副作用を分け、定期処理の再投入を無制限の暗黙loopにしない。CLI UIのGo依存を追加する意図ではない。

追加の障害例として、[uv #16999](https://github.com/astral-sh/uv/issues/16999)は大量処理時のFD枯渇を報告しclosed/completed。並列数をCPUだけで決めない理由になる。miseのperf commitにある元環境の時間・要求数も、作者による特定環境の報告であり、POWでの再現値ではない。

## 論文と利用者の議論から補う判断

- [Lost in the Middle v3](https://arxiv.org/abs/2307.03172v3)は、検査したモデル・検索課題で情報位置による性能差を示す。POWへの推論は「重要制約と現在の証拠を埋もれさせない」。2026年の全モデルにも同率で起こるとは結論しない。
- [Agentless v2](https://arxiv.org/abs/2407.01489v2)はlocalization→repair→validationの単純な分割も比較対象にする。POWはAgent数で品質を代用せず、狭い入口と実行可能な一巡を先に作る。過去benchmark順位・費用を現在値として転用しない。
- [SWE-agent v3](https://arxiv.org/abs/2405.15793v3)はAgent向けの探索・編集・実行interfaceを研究対象にした。POWへの推論は、長い指示を足す前に観測可能で短いTool応答・正確な失敗状態を設計すること。
- [Claude Code利用者の追試付き投稿](https://www.reddit.com/r/ClaudeCode/comments/1s3xjn4/i_measured_claude_codes_hidden_token_overhead/)は、起動context増加の報告と、4turnではquota急増を再現できなかった追記を両方含む。投稿者の数字を製品の一般仕様や課金根拠にしない。context量、累積入力、cache入力、quota表示、実費を分けて測る必要がある。

## 取り込まないもの・実装前に残す条件

大規模workflow server、Redis、全言語parser、常時browser/watcher、background LLM要約、Agent軍団は、必要性と費用が示されるまで追加しない。人気UIの外観を横移植せず、brand・情報階層・操作の関係を評価する。既存テスト・verification能力を失わせるためにcompressorを使わない。

次に着手するなら、まず既存のprofileで**走査・起動・queue待ち・実行・join**を分け、遅い区間を1つ選ぶ。正常終了・最新入力・原文回収・必要な操作状態を維持できたことをcompile/buildまたは直接実行で確認する。新しいテスト、fixture、snapshot、benchmark/harnessは増やさない。計測・watch・report自体の費用も残す。

後続の実装では、選んだ1項目・既存経路・関連する固定sourceだけを短いbriefへ抽出する。再確認の条件は対象repoの版、POWの入出力契約、host hookの版、利用platform、licenseの変更。今回の大量調査を毎回のSkill入力へ注入する運用にはしない。

今回は調査文書だけを追加した。OSSコード・デザイン素材の転載、依存追加、設定やhookの変更、実行再現・性能測定は行っていない。Issueは過去/未解決の利用者報告として扱い、最新全環境の欠陥や頻度には読み替えない。コードを実際に転用する際は、ルートlicenseだけでなく対象ファイル・依存のNOTICEまで再確認する。
