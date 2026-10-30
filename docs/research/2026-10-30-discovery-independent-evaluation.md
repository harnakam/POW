# 新規探索: 独立評価・失敗帰属・judge自身の信頼性

調査日: 2026-10-30。GitHub連携のrepository searchから候補を探し、個別の公開REST API、README、固定revisionの実装、著者論文・issueへ戻って確認した。**15件をscreen、うち6件をソース深掘り**した。既出の主要coding agent、runtime、UI component libraryは再集計していない。以下の★は取得時点の累計であり、増加履歴を取っていないため「急上昇」の証拠ではない。2026年作成の小規模repoと、以前からあるが今回未掲載の専門repoを区別する。

POWに合うのは評価platformの導入より、**原要求と実成果を別の読み手が照合し、不明・失敗・費用を残す小さな契約**である。`hatarake`の実行後review、`pow-first-loop`の履歴を継承しない相談、`design-reasoning`の実画面批評、`pow-reference`の一次資料へのlocatorに接続できる。新しいtest、fixture、benchmark、harnessを増やす提案ではない。現状のcompile/build・直接実行を判断の土台にする。

## 深掘り6件の現況

日付はUTC、Cはrepository作成、Pは最終push。全件`archived:false`。Pはdefault branchの実装更新と同義ではないため、本文の実装判断は下記commitに固定した。APIのlicense分類とroot license本文を両方読んだ。

| repo / メタデータ出典 | ★ | C / P | root license / 確認commit |
|---|---:|---|---|
| [agentscope-ai/OpenJudge](https://api.github.com/repos/agentscope-ai/OpenJudge) | 989 | 2025-07-08 / 2026-10-20 | [Apache-2.0](https://github.com/agentscope-ai/OpenJudge/blob/c2fdc38314cd971b03d4d9333cd2c9f24d85c27f/LICENSE) / `c2fdc38314cd971b03d4d9333cd2c9f24d85c27f` |
| [microsoft/AgentRx](https://api.github.com/repos/microsoft/AgentRx) | 163 | 2026-03-11 / 2026-09-14 | [MIT](https://github.com/microsoft/AgentRx/blob/7a18c79708e7671be15124460f4f7296107c2a55/LICENSE.txt) / `7a18c79708e7671be15124460f4f7296107c2a55` |
| [ulab-uiuc/AgentDebug](https://api.github.com/repos/ulab-uiuc/AgentDebug) | 108 | 2025-09-26 / 2026-03-30 | [MIT](https://github.com/ulab-uiuc/AgentDebug/blob/7740fe3a5c4822b2143cbde78ecfffeace0bb166/LICENSE) / `7740fe3a5c4822b2143cbde78ecfffeace0bb166` |
| [metauto-ai/agent-as-a-judge](https://api.github.com/repos/metauto-ai/agent-as-a-judge) | 842 | 2024-10-16 / 2026-03-28 | [MIT](https://github.com/metauto-ai/agent-as-a-judge/blob/43c2fa7b84ef0c1522e8250576e6798bace29dd0/LICENSE) / `43c2fa7b84ef0c1522e8250576e6798bace29dd0` |
| [apple-aiml-research/ml-agent-evaluator](https://api.github.com/repos/apple-aiml-research/ml-agent-evaluator) | 13 | 2025-07-31 / 2026-09-11 | APIは`NOASSERTION`。[Apple独自本文](https://github.com/apple-aiml-research/ml-agent-evaluator/blob/1550273c6c7e6e872fc92738b80174e4be7d3450/LICENSE)、dataは別の[CC BY-NC-ND 4.0](https://github.com/apple-aiml-research/ml-agent-evaluator/blob/1550273c6c7e6e872fc92738b80174e4be7d3450/LICENSE_DATA) / `1550273c6c7e6e872fc92738b80174e4be7d3450` |
| [Handshake-AI-Research/gandalf-the-grader](https://api.github.com/repos/Handshake-AI-Research/gandalf-the-grader) | 58 | 2026-02-24 / 2026-10-19 | [Apache-2.0](https://github.com/Handshake-AI-Research/gandalf-the-grader/blob/c087e67ab334574aabde25312bdd864c3923c16c/LICENSE.txt) / `c087e67ab334574aabde25312bdd864c3923c16c` |

## 1. OpenJudge: 再採点の多数決と独立した証拠を分ける

[`TrajectoryErrorRecoveryGrader`](https://github.com/agentscope-ai/OpenJudge/blob/c2fdc38314cd971b03d4d9333cd2c9f24d85c27f/openjudge/graders/agent/trajectory/trajectory_error_recovery.py#L25)は、error認識、原因診断、戦略変更、同じ失敗の反復、最終的な回復を軌跡から採点する。これはtrajectoryを渡したLLM評価であり、コードを再実行して回復を証明するものではない。[`VotingEvaluationStrategy.execute`](https://github.com/agentscope-ai/OpenJudge/blob/c2fdc38314cd971b03d4d9333cd2c9f24d85c27f/openjudge/evaluation_strategy/voting_evaluation_strategy.py#L94)は同じ`call_fn(**kwargs)`を`num_votes`回並行実行しscoreの最頻値を返す。**回数を増やしても新しい観測源や異なる失敗仮説は自動では増えない**。費用も採点call数に応じて増え、共有した誤解は多数決に残る。

良い失敗例は[#195](https://github.com/agentscope-ai/OpenJudge/issues/195)。失敗・欠損した採点を除外すると、1/3件しか採点できていなくても正解率100%に見えるという報告で、10-20にclosed/completed。**現在の固定版**の[`AccuracyAnalyzer`](https://github.com/agentscope-ai/OpenJudge/blob/c2fdc38314cd971b03d4d9333cd2c9f24d85c27f/openjudge/analyzer/validation/accuracy_analyzer.py#L129)にはalignment checkとcoverage metadataがあるため、未修正バグとして扱わない。一方、空のreferenceが各種文字列判定で満点になる[#199](https://github.com/agentscope-ai/OpenJudge/issues/199)はopenの利用者報告で、今回は実行再現していない。

POW案: `hatarake`のreview理由に「対象N件 / 実際に観測したN件 / 不明な項目」を併記する。失敗retryは変更点と新証拠を必須にし、「judgeの再投票で通った」を達成にしない。既存receiptに観測範囲を加える程度でよく、50種grader、学習pipeline、外部dashboardは不要。Skillの宣言と実コードを比較する[`SkillDeclarationAlignmentGrader`](https://github.com/agentscope-ai/OpenJudge/blob/c2fdc38314cd971b03d4d9333cd2c9f24d85c27f/openjudge/graders/skills/declaration_alignment.py)も追加の読書候補だが、これも静的LLM分析であり実行証明ではない。

## 2. AgentRx: 最初のエラーより「回復不能になった箇所」

[`checker.py`](https://github.com/microsoft/AgentRx/blob/7a18c79708e7671be15124460f4f7296107c2a55/agentrx/invariants/checker.py#L405)は適用条件に合うinvariantだけを確認し、違反、skip、telemetryを残す。[`judge.py`のroot-cause手順](https://github.com/microsoft/AgentRx/blob/7a18c79708e7671be15124460f4f7296107c2a55/agentrx/judge/judge.py#L511)は各失敗が後続で解消されたかを確認してから原因へ帰属する。ツール出力を根拠として使う部分は自己申告より強いが、constraint生成・自然言語check・最終帰属にはLLMが残る。生成したcheckerを「独立したground truth」と呼ばない。

[論文v2](https://arxiv.org/html/2602.02475v2#S4.SS7)自身が、endpoint障害をinvocation違反へ誤帰属した例と、PDF取得の幻覚より後のguardrail症状を原因とした例を示す。validation logを増やすと、かえってjudgeを誤誘導し得る。[比較結果](https://arxiv.org/html/2602.02475v2#S4.SS2)は人手注釈した失敗軌跡の位置・分類精度であり、agentのタスク成功率を直接高めた実験ではない。v2は170 trajectories・11設定、初期release記事の115件とは版が違う。

現行コード上の具体的な制約もある。openの[#50](https://github.com/microsoft/AgentRx/issues/50)が指摘する通り、[`checker.py:915–926`](https://github.com/microsoft/AgentRx/blob/7a18c79708e7671be15124460f4f7296107c2a55/agentrx/invariants/checker.py#L915)は非JSONへのfallbackを作った直後に再び`json.loads(raw)`する。これは固定ソースとの照合で確認したもので、実行再現はしていない。

POW案: 既存attemptの失敗を「call/step、期待した効果、観測、後で回復したか、残る仮説」に絞ってreviewへ渡す。全stepへのLLM採点は増設せず、既存直接実行で失敗した箇所だけ調べる。checker自身の例外・skipを成功へ丸めない。複数生成・semantic check・最終judgeの費用があるため、全tool callを常時採点するhook化は見送る。[`get_metrics_summary`](https://github.com/microsoft/AgentRx/blob/7a18c79708e7671be15124460f4f7296107c2a55/agentrx/invariants/checker.py#L1117)はchecker tokensやskip件数を持つが、それだけを全pipeline費用とは扱えない。

## 3. AgentDebug: targeted feedbackは有望、反実仮想の説明は再実行と別

[`fine_grained_analysis.py`](https://github.com/ulab-uiuc/AgentDebug/blob/7740fe3a5c4822b2143cbde78ecfffeace0bb166/detector/fine_grained_analysis.py#L247)はmemory/reflection/planning/actionの前後関係とenvironment responseを使い、根拠付きerrorを列挙する。[`critical_error_detection.py`](https://github.com/ulab-uiuc/AgentDebug/blob/7740fe3a5c4822b2143cbde78ecfffeace0bb166/detector/critical_error_detection.py#L222)は、その一箇所だけ直せば成功へ向かうか、という反実仮想をLLM promptで問う。**この関数は実際に過去へ戻って再実行していない**。因果仮説として読む。

[論文](https://arxiv.org/abs/2509.25370)はALFWorld/GAIA/WebShopで最大26%の**相対的な**task success改善を報告しており、単なる自己採点上昇とは違う。ただし対象はその3環境で、[limitations](https://arxiv.org/html/2509.25370v1#A1.SS1)も規模・領域の狭さを明記する。公開issueにはfeedback付き再実行コードを求める[#2](https://github.com/ulab-uiuc/AgentDebug/issues/2)、環境setup不足の[#4](https://github.com/ulab-uiuc/AgentDebug/issues/4)がopenで残る。現READMEは後に更新されているため、古いsetup指摘が全て現状でも再現するとは断定しない。

移植を避けたい細部は、[`fine_grained_analysis.py:498`](https://github.com/ulab-uiuc/AgentDebug/blob/7740fe3a5c4822b2143cbde78ecfffeace0bb166/detector/fine_grained_analysis.py#L498)のparse失敗を`error_detected=False`にするfallbackと、同file:349の30step固定判定。POWの未解析は`unknown`、停止上限は実際のcontractから取るべきである。step×moduleの複数LLM callと最終原因推定も費用になる。

POW案: `hatarake`の失敗後、reviewerは最大1つの主要仮説と修正理由を返し、hostが既存entry pointを一度実行して結果を確認する。「記憶が悪かった」のような人格評を避け、誤読したtool出力・破った条件をlocator付きで示す。vendored環境、taxonomy全体、専用debugger serviceは持ち込まない。

## 4. metauto Agent-as-a-Judge: 「成果物を読ませる」利益と、評価記憶の汚染

[`JudgeAgent.judge_anything/check_requirement`](https://github.com/metauto-ai/agent-as-a-judge/blob/43c2fa7b84ef0c1522e8250576e6798bace29dd0/agent_as_a_judge/agent.py#L158)はrequirementごとにworkspace、関連file、内容、trajectory等の証拠を集める。black-boxではtrajectoryをworkflowから除く。[`llm/cost.py`](https://github.com/metauto-ai/agent-as-a-judge/blob/43c2fa7b84ef0c1522e8250576e6798bace29dd0/agent_as_a_judge/llm/cost.py#L5)は各call費用と累計を区別する。実装者の最終メッセージだけを読むjudgeより証拠への到達手段が多いが、独立した実行結果の代用にはしない。

重要なのは成功談より[ablationと失敗分析](https://arxiv.org/html/2410.10934v2#S4.SS1)。著者はplanningが不安定で、過去の判定をmemoryへ入れると誤りが連鎖して性能を損ねたと述べる。read/locateの追加は有効だったが、全moduleを追加するほど良いわけではない。openの[#32](https://github.com/metauto-ai/agent-as-a-judge/issues/32)も、DevAIのような事前定義requirementsのない実タスクで誰が基準を作るのかを問う。

[費用分析](https://arxiv.org/html/2410.10934v2#S4.SS4)ではDevAIの全評価がAPI $30.58・118.43分、LLM-as-a-Judgeは$29.63・10.99分。人間比較の大幅削減だけを見ると、単純judgeより遅い点を落とす。これらは2024年の特定モデル・55task/365requirementsに対する著者値で、現在の価格やPOWの測定値ではない。人間との一致を測った研究で、自律改変を繰り返したPOWの品質向上実験ではない。

POW案: `pow-first-loop`・`hatarake`の別読み手へ、原要求、直接実行の出力、必要なfile内容、未確定点だけ渡す。前judgeの「良いはず」「失敗原因はX」という結論を評価memoryとして継承させない。sourceへのlocatorを再取得し、変更済み候補を過去の合格で保証しない。graph/embedding検索基盤やDevAIを新設しなくても実現できる。

## 5. Apple ml-agent-evaluator: 外部toolは採点を改善も悪化もさせる

[`PairwiseEvaluatorAgent.evaluate`](https://github.com/apple-aiml-research/ml-agent-evaluator/blob/1550273c6c7e6e872fc92738b80174e4be7d3450/src/ageval/evaluators/agent/core.py#L184)は候補A/Bの初期評価から必要toolを選び、tool出力と例外を含めて最終判断する。[`NoHarmAgentEvaluator`](https://github.com/apple-aiml-research/ml-agent-evaluator/blob/1550273c6c7e6e872fc92738b80174e4be7d3450/src/ageval/evaluators/agent/no_harm.py#L61)はweb検索が有効そうかを別LLM callで推定し、threshold以上ならagent、それ以外はbaselineへ分岐する。「NoHarm」は名前であって無退行の保証ではない。分岐の推定自身にも費用と誤りがある。

[ACL 2025論文](https://arxiv.org/html/2507.17015v1#S4.SS4)は長文事実確認等の改善に加え、単純なcode領域で最大9%のannotation performance低下を報告する。[limitations](https://arxiv.org/html/2507.17015v1#S7)は分布外退行、promptへの感度、AI judgeへの過適合を明記する。外部情報によるgroundingと「より多く考えたjudge」を同一視しない。ここでの独立性はtool由来の観測にあり、gateや最終採点はなおLLMである。

POW案: 明確なcompile/run結果がある箇所はそれを使い、文献事実なら必要な引用元、画面なら実captureを取得する。機械的に判定できる項目へLLM採点を上乗せしない。新しいcheckerを作る代わりに、既存tool一回で不明点が解けるかを先に決める。Apple独自licenseとdata用CC BY-NC-NDは別物なので、コード・datasetをまとめてMIT資産のように扱わず、原理の参考を優先する。

## 6. Gandalf: 同じ成果環境を見せる。ただしparserがrewardを壊せる

[`judge.run_agent_session`](https://github.com/Handshake-AI-Research/gandalf-the-grader/blob/c087e67ab334574aabde25312bdd864c3923c16c/src/gandalf/judge.py#L417)はagent型judgeを走らせ、LLM usageを取得する。[`orchestrator.run_judge`](https://github.com/Handshake-AI-Research/gandalf-the-grader/blob/c087e67ab334574aabde25312bdd864c3923c16c/src/gandalf/orchestrator.py#L249)はworkspaceをcloneし、期限付きsubprocessを実行し、失敗を`met=None`へする。結果が全て揃うまで[`reward.json`を書かない](https://github.com/Handshake-AI-Research/gandalf-the-grader/blob/c087e67ab334574aabde25312bdd864c3923c16c/src/gandalf/orchestrator.py#L784)。最終文章だけではなく、実artifactやtool stateを調べるのが核である。

[著者のmeta-evaluation](https://joinhandshake.com/research/ai/gandalf-the-grader/)は既に完了した21 banking taskの3,204人手判定に対するF1を比較し、最安設定で約$42・F1 0.633を報告する。これは採点architectureの比較であり、task実行者自身の成功率向上ではない。同記事時点でmeta-eval datasetは後日公開予定、別領域の一部はinternal benchmarkなので、第三者が同じ範囲を再検証できるとは限らない。F1が1ではない点も残す。

見逃せないのはopenの[#47](https://github.com/Handshake-AI-Research/gandalf-the-grader/issues/47)。固定版の[`Verdict.from_raw`](https://github.com/Handshake-AI-Research/gandalf-the-grader/blob/c087e67ab334574aabde25312bdd864c3923c16c/src/gandalf/models.py#L195)が`bool(raw_met)`を使うため、JSONのbooleanではなく文字列`"false"`を受けるとTrueになる。**実装ソースで確認した推論上の誤りで、今回はコードを実行していない**。環境を見に行く強いjudgeでも、結果parserだけでrewardを逆転させ得る。

POW案: `hatarake`と`design-reasoning`のreviewerが候補の実file・実screenを直接確認し、証拠にアクセス不能なら不明として止める。型の不正、judge timeout、未解析は不合格とは別の未評価として明示する。同時に、criticに実行者の書込権限や外部mutation能力まで渡す必要はない。Gandalf全体はPython、OpenHands SDK、tmux、API costを伴い、Windowsの依存なしNode CLIへそのまま導入する候補ではない。成果物clone・read-only review・有限期限という原理だけ取る。

## 追加screen 9件: 深掘りとは別集計

この9件も個別APIとREADMEを取得した。全件`archived:false`。root license本文・固定ソース2fileの確認は行っていないため、以下のlicense列は**API検出値**であり流用許可の最終判断ではない。低品質・不明候補も除外理由込みで数えた。新規発見15件の全てを採用推奨する意図ではない。

| repo / API出典 | ★ | C / P（UTC） | API license | 今回確認した仕組み / 判断 |
|---|---:|---|---|---|
| [microsoft/AgentAsJudge](https://api.github.com/repos/microsoft/AgentAsJudge) | 23 | 2025-06-11 / 2026-02-11 | MIT | [README](https://github.com/microsoft/AgentAsJudge/blob/main/README.md): reviewer→critic→ranker。複数役の文章採点で、実artifactの独立検証とは別。冒頭1–5点とfeatureの1–10点が不一致。役数の増加だけを品質保証にしない比較対照。 |
| [showlab/AUI](https://api.github.com/repos/showlab/AUI) | 45 | 2025-10-29 / 2025-11-27 | MIT | [README](https://github.com/showlab/AUI/blob/main/README.md)・[論文](https://arxiv.org/abs/2511.15567): coder/CUA/verifierを分け、実navigationの失敗軌跡から改修する。`design-reasoning`の実操作critic候補。ただし目的はagent向け操作容易性で、destylizationを人間向け美しさと混同しない。 |
| [OSU-NLP-Group/Mind2Web-2](https://api.github.com/repos/OSU-NLP-Group/Mind2Web-2) | 114 | 2025-06-08 / 2026-09-25 | MIT | [README](https://github.com/OSU-NLP-Group/Mind2Web-2/blob/main/README.md): web回答の引用先と取得時page cache。CAPTCHA/login等の取得障害を不正確と分ける。`pow-reference`で取得時証拠を残す着眼点。benchmark全体を導入しない。 |
| [YufeiXIA/AgentLocate](https://api.github.com/repos/YufeiXIA/AgentLocate) | 2 | 2026-08-19 / 2026-08-20 | null | [README](https://github.com/YufeiXIA/AgentLocate/blob/main/README.md): initial judge→evaluator→SFT/LoRA→judge、evidence-first prompt、3票。評価者の学習と独立評価を混同しない比較候補。READMEはCOLM 2026 submissionとする。採択済みとは書かない。license未確認でコード流用は保留。 |
| [agiresearch/AgentDebugger](https://api.github.com/repos/agiresearch/AgentDebugger) | 8 | 2025-05-06 / 2025-05-16 | null | [README](https://github.com/agiresearch/AgentDebugger/blob/main/README.md)がtitleのみ。**除外**。名前・所属だけでdebuggerの完成や能力を推定しない。 |
| [ag2ai/Agents_Failure_Attribution](https://api.github.com/repos/ag2ai/Agents_Failure_Attribution) | 397 | 2025-04-29 / 2026-02-11 | MIT | [README](https://github.com/ag2ai/Agents_Failure_Attribution/blob/main/README.md)・[論文](https://arxiv.org/abs/2505.00212): 184 failure tasksで誰・どのstepを分離しall-at-once/step-by-step/binary-search比較。reviewを総合点から原因箇所へ分ける参考。原因位置を当てる値をPOW成功率に一般化しない。 |
| [mala-lab/VerifyMAS](https://api.github.com/repos/mala-lab/VerifyMAS) | 15 | 2026-05-08 / 2026-10-25 | null | [README](https://github.com/mala-lab/VerifyMAS/blob/main/README.md)・[論文](https://arxiv.org/abs/2605.17467): full trajectoryで失敗仮説を先に検証してからagentへ帰属するerror-first方式。否定可能な仮説から始める点が有望。MIT badgeはあるが[取得したroot](https://api.github.com/repos/mala-lab/VerifyMAS/contents)にLICENSEなし。専門verifierの汎化・費用は今回未精査。 |
| [RANDCorporation/judge-reliability-harness](https://api.github.com/repos/RANDCorporation/judge-reliability-harness) | 22 | 2025-12-11 / 2026-02-23 | MIT | [README](https://github.com/RANDCorporation/judge-reliability-harness/blob/main/README.md): label flip、paraphrase、verbosity、再sampling、ordinal calibration。正しさと安定性を分けるための参考資料。POWへ別suite/harnessを追加する提案にはしない。 |
| [DaBestCode/JudgeGauge](https://api.github.com/repos/DaBestCode/JudgeGauge) | 1 | 2026-09-08 / 2026-09-08 | Apache-2.0 | [README](https://github.com/DaBestCode/JudgeGauge/blob/main/README.md): 9requestのbounded smokeで反復順位・候補順序・invalid readout、exit 0/1/2を区別。未release、[open #1](https://github.com/DaBestCode/JudgeGauge/issues/1)はlive endpoint未検証を明記。動作済みtoolとして勧めず、予算と不明の分離というアイデアだけ残す。 |

## POWで優先する5つの小さな変更案

以下は**未実装の提案**。現在も持つ契約との差分を確認して、重複記述を増やさず必要箇所だけ補う。

| 優先 | 接続先 | 小さな移植 | 採用しない広がり |
|---|---|---|---|
| 1 | `hatarake` review / `pow-first-loop` clean brief | 原要求、候補source/output、実行結果、未観測項目を渡し、親の望む結論を渡さない。fresh contextを独立実測と呼ばない。 | 全agentの恒常的相互採点、新judge service |
| 2 | 既存review JSONと報告文 | approve/rejectとは別に、根拠なし・型不正・timeout・未解析を識別する。対象範囲と観測coverageを明示する。 | parsing失敗をFalse/合格に丸める処理、多数決での救済 |
| 3 | 既存attempt evidence | エラーの後に回復したかを確認し、最初の失敗と回復不能点を分ける。実command出力で主要仮説を一度確認する。 | 全stepへのLLM採点、新trace database、評価用fixture |
| 4 | `design-reasoning` critic | 実capture＋実操作効果＋原briefを同時に見せ、視覚品質、操作成功、preservationを分けて読む。 | agentの操作しやすさだけを人間向けdesign品質とする最適化 |
| 5 | `hatarake`既存time/attempt budget | judge/retrievalの時間・call・provider実usageも総費用へ含める。unknown costはnullのまま。不要な再judgeを止める。 | 自動paid API call、無制限の再採点、未測定の節約率 |

自己進化へつなぐなら、改善案生成者と合否基準を同時に変えない。生成したrubricの得点上昇は独立改善の証拠にならない。元の要求、直接実行の効果、履歴を継承しない読み手の証拠付き判定を固定し、費用を含めて一回の限定比較で判断する。既知の評価例にだけ合わせ込む変更や、checkerを弱めた合格は除外する。これらは上記論文・失敗例から得た設計推論で、POWで改善を測定した結果ではない。

## 確認範囲と残る空白

- 15件は検索hitだけで数えず、個別APIとREADMEを確認。深掘り6件はroot license、commit、2file以上の実装、一次の失敗issueまたは論文limitationsを確認した。screen 9件のsource固定・ライセンス本文精査は未実施。
- GitHub検索は`agent judge evaluator created:>2025-01-01`、`AgentDebug`、`AgentRx`、`agent as a judge`、`agent failure localization`、`agent failure attribution`、`UI visual evaluation`、`LLM judge reliability`等。公開webは論文・著者記事への補助経路に使用した。
- Redditの「toolを呼ばず出力を捏造する」「traceが正常に見えても空結果を無視する」という[議論](https://www.reddit.com/r/aiagents/comments/1r9bjx7/discussion_i_spent_some_time_reading_some_github/)は利用者の関心を探すleadとして読んだ。発生頻度・性能・因果の証明には使っていない。技術判断は上の一次sourceへ戻した。
- install、モデルAPI実行、候補codeの実行、benchmark再現は行っていない。★増加率、judgeの現在の単価、POWへの成功率・速度・token削減効果は不明。メタデータはmutable、実装の引用は固定commitなので更新状態は分けて読む。
- 本調査はMarkdownのみ。POW runtime、README、git履歴・index、global設定は変更していない。
