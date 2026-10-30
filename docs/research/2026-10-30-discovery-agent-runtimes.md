# 追加発掘: 小型agent runtime・終了イベント・復帰と後片付け

調査日: **2026-10-30、06:46 UTC前後**。既存の `2026-10-30-inspiration-*.md` と既知のloop群を除外し、**新規16 repoをscreening、うち6 repoを実装まで深掘り**した。GitHub connectorでmetadata、README、6件のroot LICENSE・固定commit・複数実装file・issue/source上の制約を読んだ。インストール、外部agent実行、テスト、性能測定、runtime変更はしていない。

狙いはloopのprompt交換ではなく、**終了を誰が証明するか、稼働中の実体と操作権限を分けるか、失敗後に費用・process・cleanupをどう残すか**。★は取得時の累計値で、短期増加率やGitHub Trending掲載の証拠ではない。「小型」は人気・規模の比較用であり品質認定ではない。

## 探索経路と採否

GitHub repository検索で `autonomous coding agent created:>2026-01-01 stars:>10 archived:false`、`coding agent orchestration checkpoint stars:>5 archived:false`、`coding agent orchestrator created:>2026-06-01 stars:>50 archived:false` を使用し、owner側codeへ辿った。検索hitだけのrepoは16件に数えていない。

Redditの[10月26日のPi利用者投稿](https://www.reddit.com/r/PiCodingAgent/comments/1xg0gu6/how_i_use_pi_as_the_builder_with_claude_code_as_a/)は、静かなpaneから完了を推測せず `agent_settled` のeventを待ち、agentの報告より先にdisk上の実物を調べる構成を説明する。作者自身の体験であり、速度・費用対効果の外部検証ではない。この発見を下のPi Herdsmanのruntime hook実装と照合した。同名Foremanが複数あるため、Redditの別ownerによるbotをVisionForge版の証拠には使わない。

次の16件すべてmetadataの `archived=false` を確認。作成日・push日はUTC、APIの `pushed_at` はrepo全体のpushであってdefault branchの実装更新日ではない。深掘り以外のlicenseはAPI表示までで、再利用許諾の本文確認済みを意味しない。

| repo / ★ | 作成 / push | 今回のscreening判断 |
| --- | --- | --- |
| [kelos-dev/kelos](https://api.github.com/repos/kelos-dev/kelos) / 350 | 02-01 / 10-30 | **深掘り**。Kubernetesのjob・budget admission・復帰lockを小さく移植する観点。[README](https://github.com/kelos-dev/kelos/blob/main/README.md) |
| [boadij/pi-herdsman](https://api.github.com/repos/boadij/pi-herdsman) / 213 | 09-07 / 10-30 | **深掘り**。最近の新設、session所有権・結果identity・実settled hook。[README](https://github.com/boadij/pi-herdsman/blob/main/README.md) |
| [Xuepoo/carryctx](https://api.github.com/repos/Xuepoo/carryctx) / 27 | 07-22 / 10-29 | **深掘り**。task状態とcleanup outboxのtransaction、未実装completion gateを明記。[README](https://github.com/Xuepoo/carryctx/blob/main/README.md) |
| [aiedwardyi/AgentLoop](https://api.github.com/repos/aiedwardyi/AgentLoop) / 12 | 07-15 / 10-13 | **深掘り**。依存なしNode、fresh worker/criticとWindows終了処理の具体例。[README](https://github.com/aiedwardyi/AgentLoop/blob/main/README.md) |
| [VisionForge-OU/foreman](https://api.github.com/repos/VisionForge-OU/foreman) / 443 | 06-17 / 06-29 | **深掘り**。独立command gate、cost/time/turn監視。新規だが直近のmain更新ではない。[README](https://github.com/VisionForge-OU/foreman/blob/main/README.md) |
| [blackms/aistack](https://api.github.com/repos/blackms/aistack) / 52 | 01-24 / 06-08 | **深掘り**。persist/review loopとsoft quota、hook失敗をどう扱うかの対照。[README](https://github.com/blackms/aistack/blob/main/README.md) |
| [nicobailon/pi-boomerang](https://api.github.com/repos/nicobailon/pi-boomerang) / 306 | 03-02 / 08-03 | **保留**。context collapseは実extensionだがroot LICENSEなし、実装は主にindex.ts一つ。深掘り6件の条件には含めない。[README](https://github.com/nicobailon/pi-boomerang/blob/main/README.md) |
| [myrialabs/clopen](https://api.github.com/repos/myrialabs/clopen) / 53 | 02-27 / 10-29 | **次候補**。会話checkpointを実git履歴と分離、engineごとのstate隔離。UI全体は今回不要。[README](https://github.com/myrialabs/clopen/blob/main/README.md) |
| [cosscom/shipyard](https://api.github.com/repos/cosscom/shipyard) / 330 | 10-02 / 10-29 | **次候補**。10月新設のdaemon/flow、shell hookとbefore gate。dev-box管理まで持ち込むのは過剰。[README](https://github.com/cosscom/shipyard/blob/main/README.md) |
| [SawyerHood/omegacode](https://api.github.com/repos/SawyerHood/omegacode) / 137 | 06-05 / 06-29 | **次候補**。code-based orchestrationと変更suffixだけresume。providerによってsandboxを強制できない点をREADMEが明示。[README](https://github.com/SawyerHood/omegacode/blob/main/README.md) |
| [olsenbrands/fable-foreman](https://api.github.com/repos/olsenbrands/fable-foreman) / 149 | 07-10 / 10-22 | **screening止まり**。skillと実scripts両方を要する構成。skill単体を実delegationと数えない。[README](https://github.com/olsenbrands/fable-foreman/blob/main/README.md) |
| [rokoss21/iosm-cli](https://api.github.com/repos/rokoss21/iosm-cli) / 143 | 03-09 / 04-11 | **screening止まり**。checkpoint/extension trustの参考。更新の新しさだけでは上位にできない。[README](https://github.com/rokoss21/iosm-cli/blob/main/README.md) |
| [google/mantis](https://api.github.com/repos/google/mantis) / 2,674 | 06-15 / 10-30 | **別用途**。脆弱性探索向けtoolkit。README自身が不安定性と隔離を要求し、無予算32並列例もある。POWの既定loopにしない。[README](https://github.com/google/mantis/blob/main/README.md) |
| [PrimeIntellect-ai/prime-agent](https://api.github.com/repos/PrimeIntellect-ai/prime-agent) / 22,453 | 05-08 / 10-30 | **別lane向け**。RLM/Python REPLとbounded autonomous mode、self-improvingを掲げる。実際の自己改善効果は今回未検証。[README](https://github.com/PrimeIntellect-ai/prime-agent/blob/main/README.md) |
| [Agent-Field/SWE-AF](https://api.github.com/repos/Agent-Field/SWE-AF) / 1,122 | 02-04 / 10-28 | **別規模**。checkpoint/resume_buildとworktree fleet。READMEの175 agentsは作者のartifact trail主張でPOW向け効率の証明ではない。[README](https://github.com/Agent-Field/SWE-AF/blob/main/README.md) |
| [PlamenTSV/plamen](https://api.github.com/repos/PlamenTSV/plamen) / 309 | 03-16 / 09-26 | **別用途**。Web3監査向け。WindowsやPython導入でhost設定に触れる手順があり、自動導入を今回の候補にしない。[README](https://github.com/PlamenTSV/plamen/blob/main/README.md) |

## 深掘り6件の固定点とlicense

本文の実装linkは次の**commit SHA固定**。API license検出とroot本文を分けた。6件ともroot本文を確認し、ForemanはAPIがNOASSERTIONでもrootはMIT、vendored skillsの帰属もroot LICENSEにある。

| repo | 固定HEAD / commit日 | root license |
| --- | --- | --- |
| Kelos | [`1e945106158e`](https://github.com/kelos-dev/kelos/commit/1e945106158ee1f84d7b8a60f48b70bc1c4e6d8f) / 10-29 | [Apache-2.0](https://github.com/kelos-dev/kelos/blob/1e945106158ee1f84d7b8a60f48b70bc1c4e6d8f/LICENSE) |
| Pi Herdsman | [`c7fe0516dfe4`](https://github.com/boadij/pi-herdsman/commit/c7fe0516dfe4c99db84cdddc0e2560c4502cfedc) / 10-30 | [Apache-2.0](https://github.com/boadij/pi-herdsman/blob/c7fe0516dfe4c99db84cdddc0e2560c4502cfedc/LICENSE) |
| CarryCtx | [`c20a9cb3a675`](https://github.com/Xuepoo/carryctx/commit/c20a9cb3a675172cc0de397bec0a9b0ace108c87) / 10-26 | [MIT](https://github.com/Xuepoo/carryctx/blob/c20a9cb3a675172cc0de397bec0a9b0ace108c87/LICENSE) |
| AgentLoop | [`f3cdcd096888`](https://github.com/aiedwardyi/AgentLoop/commit/f3cdcd096888eaa71588342435771dc3d4dc4c41) / 10-13 | [MIT](https://github.com/aiedwardyi/AgentLoop/blob/f3cdcd096888eaa71588342435771dc3d4dc4c41/LICENSE) |
| Foreman | [`92d7f7971ca4`](https://github.com/VisionForge-OU/foreman/commit/92d7f7971ca40442f95d552e167d214939a0390d) / 06-24 | [MIT・vendored帰属あり](https://github.com/VisionForge-OU/foreman/blob/92d7f7971ca40442f95d552e167d214939a0390d/LICENSE) |
| aistack | [`dda4ae3372bc`](https://github.com/blackms/aistack/commit/dda4ae3372bcbee37463f3ca876a2dd08f3f402d) / 06-08 | [MIT](https://github.com/blackms/aistack/blob/dda4ae3372bcbee37463f3ca876a2dd08f3f402d/LICENSE) |

### 1. Pi Herdsman: processの終端、taskの成功、操作できる資格を別々に扱う

**実装。** [managed-agent-runtime.ts](https://github.com/boadij/pi-herdsman/blob/c7fe0516dfe4c99db84cdddc0e2560c4502cfedc/extension/managed-agent-runtime.ts#L2265)はowner/session/workspace/run/request/paneのidentity付きで結果を組み立て、abort・error・空assistant textを成功にしない。未配達の直下childがあればsettleを待つ。`agent_settled` を実runtime eventとして購読し、session shutdownでcontroller・retry timer・metadata送信を掃除する。これはpromptの「終わったら報告」だけではない。[storage.ts](https://github.com/boadij/pi-herdsman/blob/c7fe0516dfe4c99db84cdddc0e2560c4502cfedc/extension/storage.ts#L39)はsource assignment・path・SHA-256を持つevidence snapshotと、result/evidence参照の二方向予約を照合する。16KiB/200行のevidence読取、1MiB snapshot制限はoutput量の上限で、LLM token/costの総予算ではない。

**失敗/限界。** [#686](https://github.com/boadij/pi-herdsman/issues/686)はbuild互換性のないlive Leadをpaused扱いし得るcode-pathを報告し、[統合commit #687](https://github.com/boadij/pi-herdsman/pull/687)で対応。このissue自身が実incidentのtraceではないと明記する。[supervision.ts](https://github.com/boadij/pi-herdsman/blob/c7fe0516dfe4c99db84cdddc0e2560c4502cfedc/extension/supervision.ts)には観測presenceとassignment由来の状態を扱う実装がある。結果textとevidence identityの整合は、機能の受入検証そのものではない。今回読んだ範囲では総token/costの強制quotaを確認できず、usage表示を予算制御と呼ばない。

**POWへ。** `native_hooks.py` のhost event→run記録で、**観測した終了状態**と**そのeventが操作を許可するか**を別fieldにする案が有益。build/capability不一致を「未稼働」へ変換せず、不明のまま残す。hatarakeの既存evidence hashにowner/run/実cwdを結び、空結果や古いsession結果を受理しない点を監査する。Herdr fleet・Chief/Manager階層全体や独自terminal監視は移植しない。4,000行級のsupervision/runtimeを丸ごと入れる保守費用は大きい。

### 2. CarryCtx: completion transactionとcleanupを分離し、未実装gateを隠さない

**実装。** [task.rs](https://github.com/Xuepoo/carryctx/blob/c20a9cb3a675172cc0de397bec0a9b0ace108c87/crates/carryctx-cli/src/application/task.rs#L835)はtask完了/取消、audit event、cleanup requestを同transactionで記録し、git副作用はcommit後へ出す。同task/worktreeのactive cleanupを再利用し、requestを増殖させない。[cleanup.rs](https://github.com/Xuepoo/carryctx/blob/c20a9cb3a675172cc0de397bec0a9b0ace108c87/crates/carryctx-cli/src/application/cleanup.rs#L238)はrequestをatomicにclaim・auditし、crashでrunningのまま残ったcleanupも再評価する。安全判定と実削除を分け、他者がclaim済みなら空の結果で終わる。branch削除の失敗はcleanup実行結果を偽装せずwarningを残す。

**失敗/限界。** open [#223](https://github.com/Xuepoo/carryctx/issues/223)は**native pre-completion hooksとverification profilesは未実装**と明記。`task complete` は検証commandが通った証明にならない。open [#224](https://github.com/Xuepoo/carryctx/issues/224)はsquash/rebase後にmergedを証明できずcleanupがblockedに溜まる実運用上の問題を述べる。Coreのzero-network方針もあり、task状態取消は実process中止を意味しない。モデル実行とtoken/time予算は外部harnessの責任。

**POWへ。** cxd async/runとhatarakeの完了stateから、cleanup依頼を**独立したdurable outcome**として扱う案。再起動後はtaskを再実行する前に未処理cleanupをidentity付きで照合する。実作業成功・検証成功・cleanup成功を一語のdoneへ潰さない。SQLite全体の採用、git worktree自動削除、issueの提案段階hookを「既に動く仕組み」として紹介することは避ける。

### 3. AgentLoop: fresh criticは有益だが、無変更の仕事と再起動を成功へ短絡しない

**実装。** [daemon.js](https://github.com/aiedwardyi/AgentLoop/blob/f3cdcd096888eaa71588342435771dc3d4dc4c41/src/daemon.js#L435)はcycle数を1–50、taskの連続retryを1–10に制限し、worker/criticごとのtimeoutを持つ。[engines.js](https://github.com/aiedwardyi/AgentLoop/blob/f3cdcd096888eaa71588342435771dc3d4dc4c41/src/engines.js#L63)でCLI argv・stream解析をengine別に分け、Codexのworkspace-write/network設定、Claudeのsafe-mode等は同一の安全特性と見なさない。[state.js](https://github.com/aiedwardyi/AgentLoop/blob/f3cdcd096888eaa71588342435771dc3d4dc4c41/src/state.js#L130)はtask別try・blocked・partial/incompleteを表示用に導く。再起動時はrunning cycleをfailedとして終端化し、完了済みPASSがある場合のみその事実を保持する。これは自動的に未完stepから処理を再開する仕組みではない。

**証拠と限界。** [作者のevaluation記録](https://github.com/aiedwardyi/AgentLoop/blob/f3cdcd096888eaa71588342435771dc3d4dc4c41/docs/evaluation.md)はfresh criticがworkerの9件greenを越えてpercent-decoding欠陥を見つけ、2cycle目に11件でPASSした例を示す。独立sessionのcriticであり、第三者ベンチマークではない。open [#16](https://github.com/aiedwardyi/AgentLoop/issues/16)はancestor/descendant rootのcheckpoint混入、git失敗のstate伝播、検証だけの無変更taskをcritic前に失敗扱いする点等を列挙。issue全項目を現HEADの未修正欠陥と断言せず、今回のcode確認では再起動終端化を確認した。Windowsのscripted SIGTERMではshutdown handlerが走らないというsource注記もある。

**POWへ。** hatarakeの既存有限loopを保ち、**writeがないことを失敗の代理にしない**受入契約を明文化する案。検証だけ、既に修正済み、対象ゼロはそれぞれ必要証拠を指定し、無意味なeditやretryを要求しない。shared/包含rootのjob ownershipは独立rootと同じ扱いにしない。自動 `git add -A`・commit、fresh processを毎cycle二重起動する運用、コスト不明を0として扱うことは取り込まない。

### 4. Foreman: completion evidenceの存在確認と、独立command結果を組み合わせる

**実装。** [verification/gate.py](https://github.com/VisionForge-OU/foreman/blob/92d7f7971ca40442f95d552e167d214939a0390d/src/foreman/verification/gate.py#L59)はevidence artifact、acceptance command、test/lint/typecheck、ratchetを合成して合否を決める。[runner.py](https://github.com/VisionForge-OU/foreman/blob/92d7f7971ca40442f95d552e167d214939a0390d/src/foreman/runner.py#L134)はasync event streamを監視し、turn/cost/wall-time/stuck/user cancelを別終端理由にする。cancelと次eventを並行で待ち、generatorのin-flight処理をdrainしてからcloseする。LLMが自己申告するPASSだけに依存しないengine側の制御。

**失敗/限界。** [evidence.py](https://github.com/VisionForge-OU/foreman/blob/92d7f7971ca40442f95d552e167d214939a0390d/src/foreman/verification/evidence.py#L31)のartifact判定は非空fileがあるか・申告fileがあるか。内容の正しさや対象revisionの新鮮さまで証明するものではない。costはstream eventの後に推定超過を見て止めるため、事前予約型hard quotaではない。open [#9](https://github.com/VisionForge-OU/foreman/issues/9)はphase=doneでもworkerがrunning表示のまま残る現象を作者のdogfood campaignが発見し、修正PR #25は観測時open。履歴stateの[再読込実装](https://github.com/VisionForge-OU/foreman/blob/92d7f7971ca40442f95d552e167d214939a0390d/src/foreman/state.py#L153)があっても、live process回収まで自動保証したとは数えない。

**POWへ。** 既存beforeComplete/verifyに、command失敗とagent verdictを別証跡として残すレビュー観点を追加できる。receiptは空でないだけでは不足で、入力hash・revision・argv・実cwd・exit codeを照合し、pending workerが残れば成功と区別する。TUI・十数段の開発pipeline・自動commit hook一式は不要。Foremanの名を冠した別repoや作者campaignの成功率を、そのままこの実装の一般性能に流用しない。

### 5. aistack: durable stateがあっても、hookとcost gateの強度を確認する

**実装。** [review-loop.ts](https://github.com/blackms/aistack/blob/dda4ae3372bcbee37463f3ca876a2dd08f3f402d/src/coordination/review-loop.ts#L278)にはcoder→adversarial reviewerのstate永続化、既定3iteration、5loop semaphore、APPROVE/上限到達の分岐がある。[checkpointer.ts](https://github.com/blackms/aistack/blob/dda4ae3372bcbee37463f3ca876a2dd08f3f402d/src/persistence/checkpointer.ts#L152)はsession全体のlatestとstep指定replayを別APIにする。latest保存があることと副作用を二重実行しないresumeは別条件で、callerがstep identityを正しく選ぶ必要がある。

**実hookの限界。** [hooks/index.ts](https://github.com/blackms/aistack/blob/dda4ae3372bcbee37463f3ca876a2dd08f3f402d/src/hooks/index.ts#L19)は実行可能なsession/task/workflow handlerだが、custom/builtin例外をlogして継続する。必須検証を失敗時blockするgateとは異なる。一方review loopにはblocking guardrail経路がある。[governance/enforcer.ts](https://github.com/blackms/aistack/blob/dda4ae3372bcbee37463f3ca876a2dd08f3f402d/src/governance/enforcer.ts#L1)は既定observe-only、blocking opt-in、check→spend間の同時callで超過し得るsoft capとsourceで明言する。open [#57](https://github.com/blackms/aistack/issues/57)は現固定commitのweb static handlerにpath traversalを報告。今回は再現/脆弱性確定しておらず、研究者の未解決報告として扱う。mainは6月以降の修正を確認できない。

**POWへ。** hookの「handlerがある」「例外を記録する」「失敗で完了を止める」を別capabilityにする。既存 `onFailure:block` と通知hookの用途を混ぜない。復帰はlatest artifactだけでなくstep/input identityを要求し、token/costが不明ならunknownを保持する。web server・SSO・federation・多数MCP toolsを導入せず、成熟度の自己表示だけで採用判断しない。

### 6. Kelos: admission、実行上限、post-run accountingは別の仕組み

**実装。** [task_budget_admission.go](https://github.com/kelos-dev/kelos/blob/1e945106158ee1f84d7b8a60f48b70bc1c4e6d8f/internal/controller/task_budget_admission.go#L37)はnamespace/selector/期間でTaskRecordを集計し、budgetが不正または読めなければ入場を拒否。超過時はWaitingにして最大5分後に再評価する。budgetなしは軽く通る。[task_controller.go](https://github.com/kelos-dev/kelos/blob/1e945106158ee1f84d7b8a60f48b70bc1c4e6d8f/internal/controller/task_controller.go#L138)はrestartで失われたmemory branch lockをpersist済みstatusから照合し、job重複実行を避ける。job消失後もusage recordを再作成し、削除時はworker cancellation応答を待つかJob削除を行う。[job_builder.go](https://github.com/kelos-dev/kelos/blob/1e945106158ee1f84d7b8a60f48b70bc1c4e6d8f/internal/controller/job_builder.go#L801)は明示したActiveDeadlineSecondsをJobへ渡す。

**失敗/限界。** TaskRecord集計によるadmissionは、実行中の全tokenを予約するhard quotaではない。deadlineも明示設定時の別機能。Job終了やcommit/PR取得は受入条件の独立検証そのものではない。open [#1412](https://github.com/kelos-dev/kelos/issues/1412)はself-development reviewerのAPPROVEが新PR headに更新されず残る具体例を継続記録している。自律self-updateの検査自体が動いても、修正がmainへ入ったとは限らない。issueが指す[固定reviewer設定](https://github.com/kelos-dev/kelos/blob/1e945106158ee1f84d7b8a60f48b70bc1c4e6d8f/self-development/kelos-reviewer.yaml#L124)とbodyの最新verdictを区別する。

**POWへ。** 既存hatarakeのattempt/deadlineを保ったまま、**入場時残予算・稼働中上限・終了時精算**のどこまで保証するかをreportに明記する案。古いreview receiptを新revisionへ使わず、終端状態の再照合でも外部processが停止した証拠を別途要する。Kubernetes・cert-manager・常時self-development fleet、無期限requeueをPOWローカルcommandへ移植しない。

## 保留候補から得る追加の一例: Pi Boomerang

[index.ts](https://github.com/nicobailon/pi-boomerang/blob/1a5985b2d92cfa84ce1f470d100d02b368711a91/index.ts)はPiのtree navigation/context eventに触れる実extensionで、単なる要約prompt集ではない。ただしanchorはmemory内のみ、取消はfile変更を戻さず、反復回数上限は1–999でも各passのtoken/wall-time上限を意味しない。[open #14](https://github.com/nicobailon/pi-boomerang/issues/14)はstreaming終了境界でtree navigateが拒否され、task自体が始まらない報告。[#9](https://github.com/nicobailon/pi-boomerang/issues/9)はsummary truncationが再質問と追加tokenを生んだ利用者報告。root LICENSEを確認できないためコード転載は候補にしない。POWでは保存した原要求を要約へ置換せず、summary生成成功と原work完了を別receiptにする着想だけ残す。

## 横断判定: 「動くloop」の要件を一括認定しない

以下は上記固定codeの確認範囲での判定。未確認を未実装と断定しない。

| 対象 | 完了の独立証拠 | 有限費用/時間 | crash・cancel・cleanup | cwd/identity・空work・保守 |
| --- | --- | --- | --- | --- |
| Herdsman | 実settledと結果/evidence binding。受入テスト合格は別 | 読取/通信byte上限あり。全体token/cost hard quotaは未確認 | abort/error/emptyを分離、shutdown掃除、persist result再送 | identityが濃い。空textはfailed。新設・更新中だがruntimeは大きい |
| CarryCtx | 完了gateは未実装とissue明記 | model実行を持たずharness責任 | transaction outbox・claim再評価。task cancelとprocess killは別 | project/task/worktreeを照合。claim競合はno-op。27★でも実コードあり |
| AgentLoop | fresh critic。作者記録でworker green後の欠陥発見 | cycle/retry/per-session timeout。総token上限は未確認 | restartは失敗終端化、完全な自動resumeではない | 包含root・無変更taskがissue対象。依存なしだがdaemon大 |
| Foreman | artifact＋独立command gate。非空artifactだけでは弱い | turn/cost/time/stuck監視。event後判定で超過余地 | cancel/drain/close、永続state。processの完全回収は未確認 | 実worktreeで検証。ghost worker issue。main更新は6月 |
| aistack | reviewer文字列とguardrail。hook例外は継続 | iteration/concurrencyあり、costは既定observe-only soft cap | checkpoint/replay APIとstop/cleanup。exactly-once副作用は未確認 | session/step分離。多数subsystem＋未解決security報告が保守負担 |
| Kelos | Job/TaskRecordは稼働結果。受入条件は別 | admission予算と明示deadlineが別。global hard token quotaとは呼べない | status復帰lock、usage再記録、finalizer取消 | namespace/task/branch。予算なし軽経路。K8s運用費が大 |

## POWで次に比較するなら

既にある `commands/hatarake/scripts/hatarake.mjs` の有限attempt/deadline・review・process ownership、`commands/optimize-latency/scripts/cxd/native_hooks.py` のnative event連携、`hooks.py` のasync/join/onFailure、`async_jobs.py` のrun ID付き結果を基盤にする。これらの置換や新harness作成は提案しない。

1. **最優先: truthと権限を分離した終端receipt。** settled/aborted/pending/unknownの観測、run/step/実cwd/revision、操作可能capabilityを別に記録する。Herdsman #686とKelos #1412が具体的な反例。既存eventが保証しないfieldを推測で埋めない。
2. **完了とcleanupの別outcome。** 既存run stateへrequest ID付きの未完cleanupを残し、再開前にprocess所有者を確認する。CarryCtxのtransaction outboxを小さなstate file契約に置き換え得る。自動削除や成功cacheを足す意味ではない。
3. **empty workを契約で決める。** 変更不要、対象ゼロ、読取検証だけを「editなし」だけで失敗にしない。必要な新鮮な証拠を定め、空summary・空結果とは区別する。
4. **budget表示の正確さ。** iteration/time/cost/token/output bytesを別欄にし、観測only・soft cap・実行中中断・不明を明示する。縮約やfresh criticのtoken削減率は実測前に書かない。
5. **小さな候補を先に読む順序。** CarryCtx→Herdsman→AgentLoopの上記file群。完成品導入ではなく、outbox/identity/empty-workの独立した設計比較として使う。Foreman/aistack/Kelosは反例も含めた参考で、依存と運用全体の導入順位ではない。

今回の限界: metadataは単一時点、issueは再現していない。第三者の費用・成功率比較、Windows実稼働の取消漏れ、licenseを含む全依存の監査は未実施。**screening16件/深掘り6件、深掘りのroot LICENSE6件、固定実装file2件以上を各repoで確認**。boomerangは追加読解したがこの6件に算入していない。
