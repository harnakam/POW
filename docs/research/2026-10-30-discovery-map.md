# POWの追加発掘: 自己進化・経験学習・独立評価

調査日: **2026-10-30**。ライブ検索から**新規76 repoを選別し、うち30件を固定commitの具体的な実装まで読んだ**。76件には採用を見送ったもの、READMEだけの候補も含む。100★未満は36件。過去の研究ノートのrepo URLとも照合し、既知のGEPAとcass_memory_systemは再確認枠に分け、新規件数には入れていない。

POWへ近いのは、**経験をそのまま命令にしない、改善候補と採用を分ける、成功を実際の変更後の結果に結ぶ、評価不能を隠さない、評価役にも予算を持たせる**仕組みだった。自己書換えloop全体の導入より、既存の`update`・`hatarake`・`pow-reference`・native hookへ小さく加える方が適合する。これは設計判断であり、POWでの効果測定ではない。

## 調査の範囲

| 分野 / 詳細 | 新規選別 | 新規実装深掘り | 主な発見 |
| --- | ---: | ---: | --- |
| [自己進化・探索・改善器](2026-10-30-discovery-self-evolution.md) | 22 | 6 | Hyperagents、RRSI、AgentDescent、PromptPotter、go-go-gepa、gemini-evolve |
| [経験学習・手順記憶・文脈](2026-10-30-discovery-memory-learning.md) | 15 | 6 | MuscleMemory、SEPM、scriptflow、brainbox、MemFlow、MemSkill |
| [小型runtime・終了・復帰](2026-10-30-discovery-agent-runtimes.md) | 16 | 6 | Pi Herdsman、CarryCtx、AgentLoop、Foreman、aistack、Kelos |
| [独立評価・失敗帰属・judge](2026-10-30-discovery-independent-evaluation.md) | 15 | 6 | OpenJudge、AgentRx、AgentDebug、Agent-as-a-Judge、Apple evaluator、Gandalf |
| [Trending・証跡・視覚品質](2026-10-30-discovery-trends-and-audits.md) | 8 | 6 | ThinkRail、Maka、Switchyard、Archify、CopilotKit/OpenBot、保留例SH-MAS |
| **重複除外後** | **76** | **30** | 5分野間にもrepo重複なし |

選別は個別metadataとREADME等の確認、深掘りは固定revisionの複数実装・ライセンスの有無/本文・一次の失敗資料や制約まで確認した範囲。深掘り30件中、SH-MASはルートLICENSEを確認できなかった保留例で、30件すべてがライセンス確認済みの採用可能OSSという意味ではない。

探索はGitHub repository search・Topics・Trending・新しい論文・作者投稿・Redditを併用した。会話履歴を渡さない4担当が別分野を検索し、親がTrendingと既知候補の重複を確認した。これは以前の結論に引っ張られにくくするための分業であり、独立した実験再現ではない。

**流行の扱い:** daily TrendingにはThinkRailなどが実掲載されていた。一方monthlyページは検索cacheの鮮度に限界があるため、直近30日の伸び率とは扱わない。各repoのstars・作成日・最終push・archive・licenseはAPIの観測値で、増加率・保守品質・機能の有効性とは別。参照したsourceはcommit固定、metadataとissueのopen/closedは観測時点である。

## 最初に読む12件

★は今回観測した累計。「小粒」は発見しにくさの目安で、完成度や導入可否を保証するものではない。ここは調査結果の読み順であり、依存追加や自動導入の順位ではない。

| 候補 | ★ | 何が面白いか | 採る際に残す境界 |
| --- | ---: | --- | --- |
| [TheWariend/MuscleMemory](https://github.com/TheWariend/MuscleMemory) | 40 | 最終変更後の成功と対象skillの実行を結び、削除したskillの再抽出を防ぐ | POWでは既存のcompile/run結果を利用する。追加testを回して信頼を稼がない。POSIX前提のfile実装は移植しない |
| [cookieApril/SEPM](https://github.com/cookieApril/SEPM) | 3 | 手順のcandidate→promotion→version→retirement、適用条件を満たしたものだけranking | 因果やverifiedはcaller入力で、既定1trial。gate名だけで実証としない |
| [skhynix/MemFlow](https://github.com/skhynix/MemFlow) | 10 | instruction/data/blockedを分け、圧縮後は上限付きIDから原文を読み直す | 取得できたことと信頼できることを分ける。本文変更時のtrust持越しはPOWへ採らない |
| [google-research/rrsi](https://github.com/google-research/rrsi) | 1,679 | 編集量・費用・雑音・欠測を含めて改善候補を選ぶ | 先行gate拒否がcached評価で覆るとのissueあり。同系列modelの別roleは独立証拠でない |
| [Birfy/agentdescent](https://github.com/Birfy/agentdescent) | 203 | stale候補、競合統合、promotion、proxyとoracleの違いを扱う | 同じscorerの再採点ではscorerの偏りを検出できない。分散探索全体は不要 |
| [facebookresearch/Hyperagents](https://github.com/facebookresearch/Hyperagents) | 2,850 | 作業agentだけでなく改善器自体も可変にする研究実装 | test情報へのアクセス報告・未使用budget引数あり。CC BY-NC-SA 4.0、研究環境と長期実用品を分ける |
| [boadij/pi-herdsman](https://github.com/boadij/pi-herdsman) | 213 | 静かな画面ではなく実settled eventとowner/run/workspace/evidence identityを照合 | process終端と要求達成、観測状態と操作資格は別。fleet階層は移植しない |
| [Xuepoo/carryctx](https://github.com/Xuepoo/carryctx) | 27 | task完了とcleanup outboxをtransaction化、再開時に後片付けを再照合 | native completion gateは未実装と作者issue明記。task completeを検証合格と呼ばない |
| [microsoft/AgentRx](https://github.com/microsoft/AgentRx) | 163 | 最初のエラーと、後で回復できなくなった原因を区別する | invariant生成やjudgeはLLMで、雑音が誤帰属を増やす。全step採点は不要 |
| [Handshake-AI-Research/gandalf-the-grader](https://github.com/Handshake-AI-Research/gandalf-the-grader) | 58 | 最終文章ではなく実成果環境を見に行くjudge | 固定版に文字列`"false"`をTrueへ変換するparserがある。強いjudgeでも結果型で壊れる |
| [JetBrains/thinkrail](https://github.com/JetBrains/thinkrail) | 6,187 | 再送ID×payload fingerprint、保持し切れない既実行結果を再実行しない設計 | 自分で道具を作る構想はREADME上今後の領域。living specsを自動的な能力向上としない |
| [NVIDIA-NeMo/Switchyard](https://github.com/NVIDIA-NeMo/Switchyard) | 3,466 | review枠の予約・refund・別失敗上限、破棄回答の費用も記録 | advisor失敗/parse不能の既定通過をPOWの合格判定へ採らない。モデルrouting変更は今回の目的でない |

小粒の次候補には[scriptflow](https://github.com/GrappinoRoot/scriptflow) 1★、[brainbox](https://github.com/thebasedcapital/brainbox) 14★、[go-go-gepa](https://github.com/go-go-golems/go-go-gepa) 0★もある。どれも実装の面白さと未確立部分を詳細ノートで分けた。さらに[RSIHub](https://github.com/simple-agent-lab/RSIHub)、[cap-evolve](https://github.com/skillberry-ai/cap-evolve)、[hone](https://github.com/twaldin/hone)、[KADATH](https://github.com/i3T4AN/KADATH)は今回READMEまでの選別なので、可変領域と固定評価の分離を次にcodeで確かめる候補として残す。

## 「自己進化」を何が変わるかで分ける

| 種類 | 今回確認した例 | POWでの意味 |
| --- | --- | --- |
| 検索・再注入・圧縮後の復帰 | MemFlow | 文脈を必要時に届ける。能力を獲得したという意味ではない |
| 経験を外部の手順にする | MuscleMemory、SEPM、scriptflow、brainbox | 繰り返した作業を適用条件付きの候補へ。役に立ったかは別の実作業結果で判断する |
| prompt/Skill/harnessの候補探索 | RRSI、AgentDescent、go-go-gepa、PromptPotter | 基盤modelの重みは変わらない。探索費用、採用候補、評価した実体を対応させる |
| 自身のcode・改善器を改変する | Hyperagents。DGM/HGM等はREADME選別 | 可変箇所と固定contractを明示する。全repoや採点器まで自由に変える仕組みをPOWへ持ち込まない |
| 学習controllerやpolicyを更新する | MemSkill、AgentEvolver等 | MemSkillは記憶選択controllerのPPOで、base LLM全体の更新ではない。訓練基盤の導入は別問題 |
| 自動研究で得た固定機能を配布する | SoL-Pi | 公開extensionの利用と、その場で継続的に自己進化することを分ける |

この分類の根拠と、実装まで読んだ例/READMEだけの例は各分野のノートにある。loopが存在すること、保存量が増えること、同じ課題の点数が上がること、未知課題へ転移することは別の結果である。

## 採用判断を変えた反例

| 見つかった反例 | 一次資料から分かる範囲 | POWへの判断 |
| --- | --- | --- |
| 評価に失敗した例が消えると成績が良く見える | [OpenJudge #195](https://github.com/agentscope-ai/OpenJudge/issues/195)は修正済み。gemini-evolveのholdoutにも失敗skipがある | 対象数、観測数、失敗、不明を分ける。欠測を成功率の分母から黙って外さない |
| 候補を実際に適用していない | gemini-evolveのGA pathは受け取ったinstructionsをCLIに渡さない。GEPA既定pathは別に候補を配置する | source/artifact hashと実行対象を結ぶ。全engineの欠陥へ一般化しない |
| 独立役を増やしても同じ誤りを持つ | [Agent-as-a-Judgeのablation](https://arxiv.org/html/2410.10934v2#S4.SS1)は評価memoryでの誤り連鎖も報告 | clean reviewerへ原要求と原文証拠を渡し、親や前reviewの結論を正解として渡さない |
| 判定parserが意味を逆転する | [Gandalf #47](https://github.com/Handshake-AI-Research/gandalf-the-grader/issues/47)と固定sourceの`bool(raw_met)` | 型不正・parse失敗はunknown。criticの文章だけで実行成功を上書きしない |
| 仕様宣伝と実装段階が違う | Hermes self-evolutionはSkill以外planned、CarryCtxのcompletion gateも未実装 | 実装済み、提案中、README主張、未確認を別に記載する |
| 人気やAPIのlicense表示だけでは使えない | Acontextはarchive済み。Hyperagentsは非商用share-alike、PromptPotterは独自MIT-RG、nightly版OpenBotはPolyForm Noncommercial | 設計着想とコード採用を分け、保守・対象file・依存の条件を再確認する |
| 論文風の見た目が裏付けにならない | SH-MASのRESEARCH_PAPERには著者・DOI placeholderが残る。実コードとrepair上限自体はある | 掲載・再現の証拠なしで成功率を採用根拠にしない。repo全体を架空と断定することもしない |

これらはcode読解と一次の報告からの判断で、今回実行再現した障害ではない。open issueを現行全環境の欠陥・頻度とせず、修正済みのものは詳細にその状態を残した。

## POWに取り込むならこの順

既存の`pow-reference`はsource/version/locator/適用条件/観測段階を持つ。`update`はsource hashと失敗記録、`hatarake`は固定contract・有限attempt・独立review、native hookは入力世代と実行結果を持つ。新しい自己進化基盤を並立させず、足りない差分に限定する。

1. **経験entryの候補・有効・古い・撤回を区別する。** 今のentryにsource hash、適用条件、最終変更後の既存compile/run結果、反証、撤回理由を結ぶ。削除した経験を同じtraceから復活させない。既に持つprovenanceと重複するfieldは足さない。
2. **検索の前に適用条件を確認する。** project・platform・tool schema・関連sourceの世代が合わなければ表示しない。成功回数やrelevance scoreで範囲外のruleを押し込まない。候補を最大数件と根拠locatorだけに絞る。
3. **復帰は原文を上限付きで再確認する。** 読んだID/hashと未解決制約だけをcapsuleに残す。圧縮後に古いSkill本文を命令として復活させず、現在のsourceを必要な分だけ読む。本文更新なら信頼も再確認する。
4. **成功・失敗・未評価の対象範囲を報告する。** 既存outcomeに対象数/観測数と根拠を結ぶ。ファイル存在、process終端、agentのPASS、受入条件達成、cleanup終了を一語のdoneへ潰さない。stale世代のreviewは採用しない。
5. **reviewと改善提案にも有限予算を割り当てる。** 既存のattempt/deadline内で必要なときだけ行い、未変更のcauseの再採点を止める。入場予算、実行中の中止、終了後の実usageは別の保証として記録する。unknown costを0にしない。
6. **UIは構造・見た目・実操作・既存保持を別に見る。** `/design-reasoning`へ渡すのは原briefと実capture、実操作後の状態。自動gate合格だけで視覚品質まで確認したと主張しない。

実装候補を選ぶときは、1項目だけ既存entry pointへ加え、依頼された実タスクのcompile/buildまたは直接実行で確かめる。成功を重ねるためだけにテスト・fixture・snapshot・benchmark・harnessを新設しない。経験を集める名目の常時LLM、全会話capture、vector DB、GPU訓練、fleet、proxyの追加も今回の調査からは正当化しない。

## 今回の成果と未確認事項

成果はこの案内と分野別5ノート。新規76件のmetadata、採用/保留/見送り、30件の実装と失敗資料、POWで借りる最小境界を残した。内容は原理・評価・source locatorで、OSSコードや巨大な資料本文を転載したものではない。

候補repoの動作、論文結果、Windows移植、長期的な自己改善、実provider費用、全依存のlicense/securityは再現・監査していない。POWの品質・速度・token消費が改善したという実証値はない。runtime、Skills、hook設定、既存のREADMEや未追跡作業は変更せず、調査文書だけを追加した。

今後の読む順は、まずMuscleMemory/SEPM/MemFlowで**証拠を失効可能な経験へ変える**部分、次にRRSI/AgentDescentで**候補の採否**、Herdsman/CarryCtxで**終了とcleanup**、必要時にAgentRx/Gandalfで**judgeの限界**。Hyperagentsはより広い自己改変研究を理解する対照として読む。

## 後続でPOWへ実装した差分

上記は調査時点の記録。利用者の実装依頼を受け、以下を既存の入口へ加えた。OSSコードの転載や外部依存の追加ではなく、調査した境界をPOWの既存stateと実行器で実装したもの。

- [`/update`の経験ライフサイクル](../../commands/update/references/workflow.md#experience-lifecycle): 実行前後のsource一致と実exit zeroからのみ有効な経験を作り、最大3件の適用可能な観測を返す。失効は観測日時から判定し、再scanで延命しない。revoke/restore、削除・再追加後の撤回維持、v1読込とv2保存で旧CLIによる記録消失を防ぐ。
- [`/hatarake review-package`](../../commands/hatarake/references/contract.md): 原要求、固定contract、実行結果、現在のwatched candidate、失敗・未観測coverageを中立な証拠packageにする。過去reviewの結論を持ち込まず、exportではコマンドやLLMを起動しない。既存approvalと同じevidence/hash確認を使う。
- [`pow-reference`](../../commands/pow-reference/references/evidence.md)・[`pow-first-loop`](../../commands/pow-first-loop/references/clean-brief.md): 適用条件を検索順位より先に確認し、圧縮・handoff後に現在の原文を再取得する。撤回理由・不明・失敗を維持し、親の望む結論をbriefへ含めない。
- [`design-reasoning`](../../commands/design-reasoning/references/runtime.md): 構造・画面・実操作・既存保持の証拠を既存review欄で区別し、必須coverageが未観測ならblockedにする。新しい採点器・撮影round・テストは増やしていない。

直接実行では、実変換プログラムの成功からcandidate→active、revoke後の削除/再追加での非復活、restore時の旧証拠消去、実行中に入力を書き換えたexit zeroの非昇格を確認した。実行は2回で、経験取得・撤回・復帰による追加実行はない。さらに旧v1で作成されたstateをv2へ移行し、旧CLIが新形式を拒否して撤回済みstateを変更しないことを確認した。

POW自身の`node scripts/pow.mjs /update run`から既存package:validateを一度実行し、exit zero・前後入力一致と経験の有効化を確認した。hatarakeは実入力不足による失敗/skip、修正後の実行成功、旧形式reviewの受理、変更後candidateの承認拒否、文字列false判定の拒否を有限の直接実行で確認した。これらは今回の機構が動いた証拠で、長期的な能力向上や速度改善率の測定ではない。
