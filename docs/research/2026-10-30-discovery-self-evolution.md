# 新発見の自己進化AI repository — POW向け調査

調査日: 2026-10-30。GitHub API観測日も2026-10-30 UTC。**23件をscreeningし、過去調査済みのGEPAを除く新規22件を発見。うち新規6件＋既知比較1件を、固定commitのREADME・root license・計25実装ファイルまで確認した。** 新規22件中18件は2026年作成、9件は100★未満。ここで「新規」は今回のライブ探索で過去POW調査と重複しない候補という意味で、公開直後・急成長を意味しない。

POWに最も近いのは、**RRSIの編集量・費用・欠測の扱い、AgentDescentの候補と証拠の統合、PromptPotterの比較不能を0点と分ける表現**。研究上の自己改変を知るならHyperagents、低starの実装を批判的に読むならgo-go-gepaとgemini-evolveがよい。いずれも丸ごとの導入を勧める結論ではない。

## 探索方法と証拠の強さ

- ライブ検索 `site:github.com "self-evolving" "agent" "2026"`、`"self-improving" "agent" "evolution"`、GEPA/AlphaEvolve関連語から開始。[GitHub self-evolving-agents topic](https://github.com/topics/self-evolving-agents)・[GEPA topic](https://github.com/topics/gepa)も当日確認し、RSIHub/cap-evolve/hone/KADATH等を追加した。
- [sukojiの最新map](https://github.com/sukoji/awesome-self-evolving-agents)と[vicfeiのcoding-agent map](https://github.com/vicfei/awesome-self-improving-coding-agents)は発見入口だけに使用。分類・採否は対象repo自身のREADME、API、固定source、issueへ戻した。
- GitHub connectorの`fetch`はpublic repo metadata・directory・fileを取得できた。グローバルrepository search URLはconnectorが拒否したため、その部分はweb検索で補った。GitHub Topicsは表示時点の一覧であり、Trendingの日次順位・新規star数の証拠ではない。
- **screen**はAPIとREADMEを確認した段階。**深掘り**だけが固定sourceまで確認した候補。論文の数値、作者の成功率、READMEの性能比較はPOWで再現していない。外部code実行・依存導入・API課金・git操作・テスト追加はしていない。

## 観測metadata — 全23件

全件APIの `archived=false`。表の日時はAPIの `created_at` / `pushed_at` そのもの、UTC。`pushed_at` はrepo全体のpushであり保守保証ではない。starは観測時点の総数で、増加率や品質順位ではない。`null` はAPIがlicenseを返さなかったこと、`NOASSERTION` は標準SPDXを断定できなかったことを示す。深掘り候補は本文でも確認し、その差を後述する。

| Repository / metadata出典 | ★ | created_at UTC | pushed_at UTC | API license SPDX | 段階 |
| --- | ---: | --- | --- | --- | --- |
| [gepa-ai/gepa](https://github.com/gepa-ai/gepa) / [API](https://api.github.com/repos/gepa-ai/gepa) | 7,204 | `2025-08-05T09:26:27Z` | `2026-10-29T22:59:51Z` | MIT | 既知比較・深掘り |
| [LichAmnesia/gemini-evolve](https://github.com/LichAmnesia/gemini-evolve) / [API](https://api.github.com/repos/LichAmnesia/gemini-evolve) | 7 | `2026-04-16T04:38:08Z` | `2026-04-18T22:44:13Z` | MIT | 新規・深掘り |
| [PromptPotter/prompt-potter-optimizer](https://github.com/PromptPotter/prompt-potter-optimizer) / [API](https://api.github.com/repos/PromptPotter/prompt-potter-optimizer) | 8 | `2025-11-16T13:49:23Z` | `2026-10-30T05:09:52Z` | NOASSERTION | 新規・深掘り |
| [Birfy/agentdescent](https://github.com/Birfy/agentdescent) / [API](https://api.github.com/repos/Birfy/agentdescent) | 203 | `2026-07-24T13:48:05Z` | `2026-10-30T06:36:28Z` | MIT | 新規・深掘り |
| [go-go-golems/go-go-gepa](https://github.com/go-go-golems/go-go-gepa) / [API](https://api.github.com/repos/go-go-golems/go-go-gepa) | 0 | `2026-02-23T02:29:18Z` | `2026-07-03T20:34:51Z` | MIT | 新規・深掘り |
| [facebookresearch/Hyperagents](https://github.com/facebookresearch/Hyperagents) / [API](https://api.github.com/repos/facebookresearch/Hyperagents) | 2,850 | `2026-03-19T17:24:07Z` | `2026-07-31T16:56:22Z` | NOASSERTION | 新規・深掘り |
| [DaizeDong/self-evolve](https://github.com/DaizeDong/self-evolve) / [API](https://api.github.com/repos/DaizeDong/self-evolve) | 26 | `2026-06-23T17:04:37Z` | `2026-10-16T21:18:16Z` | MIT | 新規・screen |
| [FrontisAI/OpenRSI](https://github.com/FrontisAI/OpenRSI) / [API](https://api.github.com/repos/FrontisAI/OpenRSI) | 864 | `2026-07-30T17:19:53Z` | `2026-09-17T14:17:36Z` | NOASSERTION | 新規・screen |
| [metauto-ai/HGM](https://github.com/metauto-ai/HGM) / [API](https://api.github.com/repos/metauto-ai/HGM) | 446 | `2025-10-24T12:34:21Z` | `2026-02-07T21:30:42Z` | Apache-2.0 | 新規・screen |
| [google-research/rrsi](https://github.com/google-research/rrsi) / [API](https://api.github.com/repos/google-research/rrsi) | 1,679 | `2026-09-16T04:50:49Z` | `2026-09-23T22:16:25Z` | Apache-2.0 | 新規・深掘り |
| [NVlabs/SoL-Pi](https://github.com/NVlabs/SoL-Pi) / [API](https://api.github.com/repos/NVlabs/SoL-Pi) | 3,611 | `2026-09-02T14:48:47Z` | `2026-10-30T06:33:24Z` | MIT | 新規・screen |
| [QuantaAlpha/EvoControl](https://github.com/QuantaAlpha/EvoControl) / [API](https://api.github.com/repos/QuantaAlpha/EvoControl) | 134 | `2026-01-08T13:42:49Z` | `2026-01-25T14:07:36Z` | Apache-2.0 | 新規・screen |
| [SalesforceAIResearch/Beagle](https://github.com/SalesforceAIResearch/Beagle) / [API](https://api.github.com/repos/SalesforceAIResearch/Beagle) | 103 | `2026-08-20T22:15:18Z` | `2026-10-23T00:12:21Z` | Apache-2.0 | 新規・screen |
| [RealLcz/MGM](https://github.com/RealLcz/MGM) / [API](https://api.github.com/repos/RealLcz/MGM) | 36 | `2026-04-09T12:53:13Z` | `2026-09-22T13:03:51Z` | Apache-2.0 | 新規・screen |
| [IQuestLab/ModularRSI](https://github.com/IQuestLab/ModularRSI) / [API](https://api.github.com/repos/IQuestLab/ModularRSI) | 91 | `2026-08-28T06:45:35Z` | `2026-10-19T04:44:36Z` | Apache-2.0 | 新規・screen |
| [shreydesai/self-improving-agent](https://github.com/shreydesai/self-improving-agent) / [API](https://api.github.com/repos/shreydesai/self-improving-agent) | 1 | `2026-05-26T00:45:48Z` | `2026-05-26T03:12:00Z` | null | 新規・screen |
| [modelscope/AgentEvolver](https://github.com/modelscope/AgentEvolver) / [API](https://api.github.com/repos/modelscope/AgentEvolver) | 1,585 | `2025-11-13T08:09:51Z` | `2026-04-01T08:47:19Z` | Apache-2.0 | 新規・screen |
| [jennyzzt/dgm](https://github.com/jennyzzt/dgm) / [API](https://api.github.com/repos/jennyzzt/dgm) | 2,470 | `2025-05-23T14:25:57Z` | `2025-08-13T10:40:14Z` | Apache-2.0 | 新規・screen |
| [simple-agent-lab/RSIHub](https://github.com/simple-agent-lab/RSIHub) / [API](https://api.github.com/repos/simple-agent-lab/RSIHub) | 303 | `2026-07-03T09:54:48Z` | `2026-10-27T21:37:05Z` | Apache-2.0 | 新規・screen |
| [skillberry-ai/cap-evolve](https://github.com/skillberry-ai/cap-evolve) / [API](https://api.github.com/repos/skillberry-ai/cap-evolve) | 66 | `2026-06-15T07:46:31Z` | `2026-10-30T06:44:00Z` | Apache-2.0 | 新規・screen |
| [twaldin/hone](https://github.com/twaldin/hone) / [API](https://api.github.com/repos/twaldin/hone) | 47 | `2026-04-18T03:21:16Z` | `2026-10-07T12:06:21Z` | MIT | 新規・screen |
| [i3T4AN/KADATH](https://github.com/i3T4AN/KADATH) / [API](https://api.github.com/repos/i3T4AN/KADATH) | 253 | `2026-08-08T15:49:55Z` | `2026-10-24T14:19:27Z` | Apache-2.0 | 新規・screen |
| [NousResearch/hermes-agent-self-evolution](https://github.com/NousResearch/hermes-agent-self-evolution) / [API](https://api.github.com/repos/NousResearch/hermes-agent-self-evolution) | 5,606 | `2026-03-09T10:42:48Z` | `2026-06-17T11:53:04Z` | null | 新規・screen |

人気側の入口はHermes companion 5,606★、SoL-Pi 3,611★、Hyperagents 2,850★。低star側にはgo-go-gepa 0★、self-improving-agent 1★、gemini-evolve 7★、PromptPotter 8★、self-evolve 26★、MGM 36★、hone 47★、cap-evolve 66★、ModularRSI 91★がある。大小で分けて見つけたもので、人気から正しさは推定しない。

## 自己進化という語を分解する

| 変更されるもの | 今回の例 | 読み違えない境界 |
| --- | --- | --- |
| 自身のsource / 改善器 | Hyperagents、DGM、HGM、MGM | ベンチマークと有限予算に束縛された研究。任意業務での無制限RSIの証拠ではない |
| prompt / skills / 可変harness | gemini-evolve、AgentDescent、RRSI、cap-evolve | 基盤modelの重みは変えない。採用したartifactが後の実行へ戻る仕組みが必要 |
| 目的関数つきオフライン探索 | PromptPotter、go-go-gepa、EvoControl、hone | 最適化後の通常実行と、探索に要した追加費用は別 |
| training / policy更新 | AgentEvolver、OpenRSI | GPU・学習・環境・データが必要。POWの指示文更新へそのまま置換できない |
| 自動研究の成果物の配布 | SoL-Pi | 配布された固定extensionを動かすこと自体は、改善器が自己更新することではない |

この分類は下記source/READMEからの本調査の整理であり、各作者が同じ用語を採っているという意味ではない。

## 深掘り — 新規6件、既知比較1件

各行はルートREADMEとlicense本文を読み、2本以上の実装を確認した。以下の段落で述べる挙動の出典はこの固定commitである。

| 区分 / Repository | 調査commit | README / license | 確認した実装 |
| --- | --- | --- | --- |
| 新規 [google-research/rrsi](https://github.com/google-research/rrsi) | [`be50316e1db05914068a973f322770ef08ed7ba1`](https://github.com/google-research/rrsi/commit/be50316e1db05914068a973f322770ef08ed7ba1) | [README](https://github.com/google-research/rrsi/blob/be50316e1db05914068a973f322770ef08ed7ba1/README.md)・[root license](https://github.com/google-research/rrsi/blob/be50316e1db05914068a973f322770ef08ed7ba1/LICENSE) | [1: rrsi/selection.py](https://github.com/google-research/rrsi/blob/be50316e1db05914068a973f322770ef08ed7ba1/rrsi/selection.py)<br>[2: rrsi/critic.py](https://github.com/google-research/rrsi/blob/be50316e1db05914068a973f322770ef08ed7ba1/rrsi/critic.py)<br>[3: rrsi/evaluate.py](https://github.com/google-research/rrsi/blob/be50316e1db05914068a973f322770ef08ed7ba1/rrsi/evaluate.py) |
| 新規 [Birfy/agentdescent](https://github.com/Birfy/agentdescent) | [`d0c580ab1d3d90d0bd9414fbdd3455fc292696df`](https://github.com/Birfy/agentdescent/commit/d0c580ab1d3d90d0bd9414fbdd3455fc292696df) | [README](https://github.com/Birfy/agentdescent/blob/d0c580ab1d3d90d0bd9414fbdd3455fc292696df/README.md)・[root license](https://github.com/Birfy/agentdescent/blob/d0c580ab1d3d90d0bd9414fbdd3455fc292696df/LICENSE) | [1: agentdescent/aggregator.py](https://github.com/Birfy/agentdescent/blob/d0c580ab1d3d90d0bd9414fbdd3455fc292696df/agentdescent/aggregator.py)<br>[2: agentdescent/goodhart.py](https://github.com/Birfy/agentdescent/blob/d0c580ab1d3d90d0bd9414fbdd3455fc292696df/agentdescent/goodhart.py) |
| 新規 [PromptPotter/prompt-potter-optimizer](https://github.com/PromptPotter/prompt-potter-optimizer) | [`373199f83e4c43d6a299d32c33e1751e4abcb7bb`](https://github.com/PromptPotter/prompt-potter-optimizer/commit/373199f83e4c43d6a299d32c33e1751e4abcb7bb) | [README](https://github.com/PromptPotter/prompt-potter-optimizer/blob/373199f83e4c43d6a299d32c33e1751e4abcb7bb/README.md)・[root license](https://github.com/PromptPotter/prompt-potter-optimizer/blob/373199f83e4c43d6a299d32c33e1751e4abcb7bb/LICENSE) | [1: promptpotter/application/scoring/selection.py](https://github.com/PromptPotter/prompt-potter-optimizer/blob/373199f83e4c43d6a299d32c33e1751e4abcb7bb/promptpotter/application/scoring/selection.py)<br>[2: promptpotter/domain/paired_reading.py](https://github.com/PromptPotter/prompt-potter-optimizer/blob/373199f83e4c43d6a299d32c33e1751e4abcb7bb/promptpotter/domain/paired_reading.py)<br>[3: promptpotter/application/runner/termination.py](https://github.com/PromptPotter/prompt-potter-optimizer/blob/373199f83e4c43d6a299d32c33e1751e4abcb7bb/promptpotter/application/runner/termination.py)<br>[4: promptpotter/application/runner/arm_gate.py](https://github.com/PromptPotter/prompt-potter-optimizer/blob/373199f83e4c43d6a299d32c33e1751e4abcb7bb/promptpotter/application/runner/arm_gate.py) |
| 新規 [facebookresearch/Hyperagents](https://github.com/facebookresearch/Hyperagents) | [`59a68f672dfb92c74aeb7e61535d776fb36e172d`](https://github.com/facebookresearch/Hyperagents/commit/59a68f672dfb92c74aeb7e61535d776fb36e172d) | [README](https://github.com/facebookresearch/Hyperagents/blob/59a68f672dfb92c74aeb7e61535d776fb36e172d/README.md)・[root license](https://github.com/facebookresearch/Hyperagents/blob/59a68f672dfb92c74aeb7e61535d776fb36e172d/LICENSE.md) | [1: meta_agent.py](https://github.com/facebookresearch/Hyperagents/blob/59a68f672dfb92c74aeb7e61535d776fb36e172d/meta_agent.py)<br>[2: generate_loop.py](https://github.com/facebookresearch/Hyperagents/blob/59a68f672dfb92c74aeb7e61535d776fb36e172d/generate_loop.py)<br>[3: select_next_parent.py](https://github.com/facebookresearch/Hyperagents/blob/59a68f672dfb92c74aeb7e61535d776fb36e172d/select_next_parent.py)<br>[4: utils/gl_utils.py](https://github.com/facebookresearch/Hyperagents/blob/59a68f672dfb92c74aeb7e61535d776fb36e172d/utils/gl_utils.py) |
| 新規 [go-go-golems/go-go-gepa](https://github.com/go-go-golems/go-go-gepa) | [`408467c6e9cd18a533bb88405882d782174077d4`](https://github.com/go-go-golems/go-go-gepa/commit/408467c6e9cd18a533bb88405882d782174077d4) | [README](https://github.com/go-go-golems/go-go-gepa/blob/408467c6e9cd18a533bb88405882d782174077d4/README.md)・[root license](https://github.com/go-go-golems/go-go-gepa/blob/408467c6e9cd18a533bb88405882d782174077d4/LICENSE) | [1: pkg/optimizer/gepa/optimizer.go](https://github.com/go-go-golems/go-go-gepa/blob/408467c6e9cd18a533bb88405882d782174077d4/pkg/optimizer/gepa/optimizer.go)<br>[2: pkg/optimizer/gepa/pareto.go](https://github.com/go-go-golems/go-go-gepa/blob/408467c6e9cd18a533bb88405882d782174077d4/pkg/optimizer/gepa/pareto.go)<br>[3: pkg/optimizer/gepa/reflector.go](https://github.com/go-go-golems/go-go-gepa/blob/408467c6e9cd18a533bb88405882d782174077d4/pkg/optimizer/gepa/reflector.go) |
| 新規 [LichAmnesia/gemini-evolve](https://github.com/LichAmnesia/gemini-evolve) | [`3f6c04446505bfad1b2b6ab5e5ab62ac4dd17872`](https://github.com/LichAmnesia/gemini-evolve/commit/3f6c04446505bfad1b2b6ab5e5ab62ac4dd17872) | [README](https://github.com/LichAmnesia/gemini-evolve/blob/3f6c04446505bfad1b2b6ab5e5ab62ac4dd17872/README.md)・[root license](https://github.com/LichAmnesia/gemini-evolve/blob/3f6c04446505bfad1b2b6ab5e5ab62ac4dd17872/LICENSE) | [1: gemini_evolve/evolve.py](https://github.com/LichAmnesia/gemini-evolve/blob/3f6c04446505bfad1b2b6ab5e5ab62ac4dd17872/gemini_evolve/evolve.py)<br>[2: gemini_evolve/constraints.py](https://github.com/LichAmnesia/gemini-evolve/blob/3f6c04446505bfad1b2b6ab5e5ab62ac4dd17872/gemini_evolve/constraints.py)<br>[3: gemini_evolve/fitness.py](https://github.com/LichAmnesia/gemini-evolve/blob/3f6c04446505bfad1b2b6ab5e5ab62ac4dd17872/gemini_evolve/fitness.py)<br>[4: gemini_evolve/gepa_evolve.py](https://github.com/LichAmnesia/gemini-evolve/blob/3f6c04446505bfad1b2b6ab5e5ab62ac4dd17872/gemini_evolve/gepa_evolve.py)<br>[5: gemini_evolve/dspy_adapter.py](https://github.com/LichAmnesia/gemini-evolve/blob/3f6c04446505bfad1b2b6ab5e5ab62ac4dd17872/gemini_evolve/dspy_adapter.py) |
| 既知比較 [gepa-ai/gepa](https://github.com/gepa-ai/gepa) | [`80a62c879ecdeb8741faac72a844dceb1c18691f`](https://github.com/gepa-ai/gepa/commit/80a62c879ecdeb8741faac72a844dceb1c18691f) | [README](https://github.com/gepa-ai/gepa/blob/80a62c879ecdeb8741faac72a844dceb1c18691f/README.md)・[root license](https://github.com/gepa-ai/gepa/blob/80a62c879ecdeb8741faac72a844dceb1c18691f/LICENSE) | [1: src/gepa/core/engine.py](https://github.com/gepa-ai/gepa/blob/80a62c879ecdeb8741faac72a844dceb1c18691f/src/gepa/core/engine.py)<br>[2: src/gepa/api.py](https://github.com/gepa-ai/gepa/blob/80a62c879ecdeb8741faac72a844dceb1c18691f/src/gepa/api.py)<br>[3: src/gepa/strategies/acceptance.py](https://github.com/gepa-ai/gepa/blob/80a62c879ecdeb8741faac72a844dceb1c18691f/src/gepa/strategies/acceptance.py)<br>[4: src/gepa/proposer/merge.py](https://github.com/gepa-ai/gepa/blob/80a62c879ecdeb8741faac72a844dceb1c18691f/src/gepa/proposer/merge.py) |

### 1. RRSI — 編集を小さくし、雑音や費用で勝たせない

**実装。** `selection.py` は最高観測scoreから雑音幅を引いたfloor、score増に応じたcost rule、構造的novelty、domain guardを組み合わせる。`critic.py` は評価を消費する前にdiffを調べ、task ID・grader・答え・無効な仕掛け等を決定的patternとLLMで検査する。`evaluate.py` はcrash/timeout/欠測試行を分母から消さず0報酬として扱う。成功例だけ残してscoreが上がる経路を閉じる設計である。[selection][rrsi-selection]・[critic][rrsi-critic]・[aggregate][rrsi-evaluate]。

**限界。** README上、proposer/analyst/critic/対象policyは同じClaude Opus 4.8であり、別roleだから独立した価値判断になったとはいえない。さらに同じ調査HEADを対象とした[issue #10](https://github.com/google-research/rrsi/issues/10)は、`gate_failure` があってもcached evaluationがあれば候補が採用され得ると報告する。実際に`judge`の拒否は`ev is None`内だけにあり、読解と報告は整合する。10-05作成、観測時open。独立実行はしていない。

costの欠測も慎重に扱う必要がある。[issue #6](https://github.com/google-research/rrsi/issues/6)は観測済み0tokenを欠測扱いする問題を報告し、sourceも`if not C_cand or not C_inc: return 0.0`。未知costと実測0を分ける発想は採るが、この実装の式を無条件に移植しない。10-04作成、open。[README][rrsi-readme]。

**POWへの最小境界。** hatarakeの既存attempt記録に「評価前の拒否理由」を残し、以後cacheや再reviewがあってもその拒否を優先する。変更提案は一度に1つの具体的な失敗仮説へ限定する。独自critic serviceや新しい評価suiteは作らない。

### 2. AgentDescent — 並列diffは足し算できない

**実装。** `aggregator.py` はstaleness検査・rebase・競合解消・融合・事前audit・統計的accept・CAS/2PC commit・devからstableへのpromotionを扱う。候補ごとの根拠を統合し、古いsource向け提案を現在のsourceへ無条件で混ぜない発想が参考になる。`goodhart.py` は同じ候補のproxy gainとoracle gainを対にし、inflation、順位相関、shortcut率を算出する。[aggregator][ad-aggregator]・[Goodhart診断][ad-goodhart]。

**限界。** `aggregator.py`自身が、全holdoutを同じscorerで再評価する`full_eval`は「偏ったscorer」を検出できず、`oracle-rejected`という名前も過大だと明記する。別の採点根拠がなければ、同じagentの判定を何回重ねても独立した裏付けにならない。早期打切り`bounded_gate`は比較の勝敗が同じでもdeltaの大きさを変えて後続posteriorへ影響するため既定off。この区別は特に有用である。

[issue #617](https://github.com/Birfy/agentdescent/issues/617)は、GEPA等のnamed algorithmで実際は採用されたのに診断が「採用なし」と表示する報告。10-30作成、**観測時closed**なので現行欠陥とは扱わない。採用ledgerと案内文を同じ状態語彙から生成する必要性の実例として読む。性能の「40% fewer calls」「6.8×」は作者の限定実験で、POWへの効果推定には用いない。[固定README][ad-readme]。

**POWへの最小境界。** 並列研究者/実装者の提案にparent/source hash、変更対象、失敗仮説、実行証拠を付け、統合時に既存hatarakeのwatched bytesと照合する。全framework・Git ledger・posterior engineを追加せず、現在の単一writerへ戻す。

### 3. PromptPotter — 比較不能を「改善0」と書かない

**実装。** `selection.py`は共通に採点されたcellで勝敗を読み、親が勝者になった時のcellを再利用して親の幸運を再演しないよう除外する。Rasch能力推定に加えてpaired wins/lossesの裏付けを要求する。`paired_reading.py`は`pending`、`absent`、`refused`、同一candidate、dataset/scorer/cell set不一致等を型で分ける。`termination.py`は停止・pause・入力拒否・timeout・crashを分類し、単なる高得点が一度出たことを停止根拠にしない。[selection][pp-selection]・[comparison state][pp-paired]・[termination][pp-termination]。

**限界。** READMEはlabel付きdatasetが必須、重みや神経architectureを変える実装ではない、in-campaign scoreはwinner選択に使ったrow上の値でdeployment性能ではないと明記する。同じmodel/budget/heldoutでの公開比較数値は未発表。L4自己最適化の入口があることと、再帰で未知taskへ転移する実証は分ける。[固定README][pp-readme]。

[issue #25](https://github.com/PromptPotter/prompt-potter-optimizer/issues/25)はweb UIから候補をVerifyできずCLI説明しかない、異なるcell setのraw前後値がpaired verdictになっていない等の不足を列挙する。09-02作成、10-27更新、open。広いcontrol planeをPOWへ移植するより、少数の状態語彙を借りるのが妥当。

root licenseは**MIT-RG**。著作者が一定の害の懸念を文書化したentityについて書面通知でlicenseを撤回できる独自条項と、Swiss governing lawがある。APIの`NOASSERTION`をMITと読み替えない。設計着想とsource転載を分ける。[license本文][pp-license]。

**POWへの最小境界。** 既存attempt/resultへ`measured`と`unavailable`と`incomparable`を分ける説明を置く。stdoutが出たが本来のartifactを比較できない場合、差0や改善とせずreviewへ送る。新しいscoring基盤は作らない。

### 4. Hyperagents — 改善器自身まで可変にする実例

**実装。** seedの`MetaAgent.forward`はrepoの任意部分の変更をtool付きagentへ依頼する。`generate_loop.py`はlineage diffをcontainerへ適用し、candidateを評価しarchiveを更新する。`utils/gl_utils.py`はmeta/task agentの差分をresetするablationや、任意の親選択logicの編集を扱う。`select_next_parent.py`のseedは`valid_parent`と全domainのscore存在を確認後、許可candidateからランダムに選ぶ。高score一本だけのgreedy探索とは違う。[meta-agent][ha-meta]・[loop][ha-loop]・[差分処理][ha-utils]・[parent selector][ha-select]。

**限界。** seedの`eval_path`と`iterations_left`は引数にあっても本文で使われない。[issue #30](https://github.com/facebookresearch/Hyperagents/issues/30)も同じ点を報告する。remaining iterationがモデルへ渡るというdocstringだけを信じない。05-03作成、open。また[issue #39](https://github.com/facebookresearch/Hyperagents/issues/39)はpaper-review実験のtest sample/labelをmeta-agentが読めたとの報告。08-19作成、open、今回再現していない。READMEも未信頼model生成codeの破壊的挙動を注意対象とする。[固定README][ha-readme]。

root本文はCC BY-NC-SA 4.0で、APIは`NOASSERTION`。商用用途への転載候補としてMIT/Apacheと同列には扱わない。[license本文][ha-license]。

**POWへの最小境界。** 有用なのは「何を可変にするかを明示する」こと。POWではglobal AGENTS、承認・権限・採点契約を可変domainへ入れず、対象Skillの提案差分に限定する。Hyperagentsのcontainer実験一式や親選択の自己改変を直ちに追加する根拠はない。

### 5. go-go-gepa — 0★でも読む価値がある小さな探索core

**実装。** `optimizer.go`は親子を同じminibatchで比較し、残evaluation budgetからmutationなら2倍・mergeなら3倍の最悪必要数を見積もる。cacheはcandidate hash×example index、parent ID/updated key/採否eventを保存する。全評価がcacheで候補も採用されない時に停止する。`pareto.go`は欠けたobjectiveを負の無限大とする小さなPareto実装。[optimizer][gg-optimizer]・[Pareto][gg-pareto]。

**限界。** 作者がGEPAの1:1 portではなくGEPA-inspiredと明記。`acceptChild`は多目的dominanceに失敗してもscalar score改善で採用するため、「保護objectiveは一切後退しない」保証ではない。`Optimize`への入力は単一examples配列で、別holdoutのfinal selectionはこのcoreのAPIが強制しない。`callsUsed`は成功したevaluator呼出で増え、reflection/merge model呼出の費用上限ではない。0★は発見しにくさを示すだけで、6月/7月以降の運用継続は未確認。[source][gg-optimizer]・[README][gg-readme]。

**POWへの最小境界。** 親/子の比較条件・採否理由・変更keyを小さく記録する形を参考にする。POWはNode/Pythonの既存実行経路があるため、Go・Geppetto・JS plugin runtimeを増設する必要は薄い。

### 6. gemini-evolve — hard gateがあっても候補を評価しているかを読む

**実装。** 非空・UTF-8 byte上限・元artifactからの成長率を`ConstraintValidator`で確認し、`_apply_result`は改善閾値・内容変更を確認してbackup後に書く。GEPA pathは一時directoryへ候補の`GEMINI.md`を置き、reflectorは別directoryで動かす。共有trace状態のため`num_threads=1`。この限定は誠実である。[constraints][ge-constraints]・[evolve/apply][ge-evolve]・[GEPA path][ge-gepa]。

**重要な読解結果。** GA pathの`_simulate_agent(instructions, task_input, model,...)`は受け取った`instructions`を使用せず、`run_gemini_cli`には`task_input`を渡す。候補をtargetへ仮配置する処理もこの関数にない。そのためGAでmutationした候補を実際に測っているというREADME説明を、当該sourceからは支持できない。**GEPA既定pathは候補を別途配置するため、この指摘を全engineへ広げない。** 実行再現はしていない。[GA source][ge-evolve]・[GEPA source][ge-gepa]。

さらにGAとGEPAのholdout評価は失敗・空応答をskipし、成功した例だけの平均にする。難しい例が落ちた時のscore上昇を防げない。`fast_heuristic_score`はexpected語のrecallで、非空なら基礎点0.3、余計な誤答への減点がなく、keyword盛込みと意味的正しさを区別しない。同系列modelをpropose/judgeへ分けても独立性の証明にはならない。[fitness][ge-fitness]・[holdout][ge-gepa]。READMEはWindows未検証とも明記する。[固定README][ge-readme]。

**POWへの最小境界。** size/growth cap・backup・候補実体のhashを残す発想を採る。自動文面進化の導入は、このcandidate適用と採点の穴を閉じてから。POW既存のartifact hash/direct executionを使い、synthetic taskや新しいtest harnessは増やさない。

### 既知比較: GEPA — 最適化coreとdeployment自己改善を区別する

既知のため新発見件数には含めない。`api.py`は停止条件を要求し、metric call budgetとreflection cost budgetを区別する。一方、`valset=None`ならtrain loaderをそのままvalidationにも使う。`StrictImprovementAcceptance`の既定はminibatch scoreの合計の改善で、各例の非回帰ではない。[API][gp-api]・[acceptance][gp-acceptance]。

[issue #532](https://github.com/gepa-ai/gepa/issues/532)は`[1,0,0]→[0,1,1]`を採用する問題に対しprotected objective wrapperを提案。10-28作成、open。[issue #535](https://github.com/gepa-ai/gepa/issues/535)は深い候補lineageで祖先探索がPython再帰上限を超える報告。10-29作成、openで、調査HEADの`get_ancestors`は再帰実装だった。独立実行なし。[merge][gp-merge]。POWへの学びは「合計改善」「各必須条件維持」「別holdout」「費用」を別欄として扱うことで、GEPAそのものの再紹介ではない。

## Screeningのみ — 残り16件

ここはREADME主張と制約の確認まで。実装済みの網羅性・課金実績・未知taskへの転移を検証済みと扱わない。

| 候補 / first-party README | 機構と、確認して残った境界 |
| --- | --- |
| [DaizeDong/self-evolve README](https://github.com/DaizeDong/self-evolve/blob/main/README.md) | 固定contractとpaired evidence、archive/review。Cの測定生成、A+B併用等に未実装・拒否範囲 |
| [FrontisAI/OpenRSI README](https://github.com/FrontisAI/OpenRSI/blob/main/README.md) | OpenMLEのSFT/RL＋program探索。READMEは一般RSIを解決したと主張せず。README licenseはCC BY-NC 4.0 |
| [metauto-ai/HGM README](https://github.com/metauto-ai/HGM/blob/main/README.md) | 自己改変coding agentのclade探索。DGM派生、Docker等を伴う研究系 |
| [NVlabs/SoL-Pi README](https://github.com/NVlabs/SoL-Pi/blob/main/README.md) | auto-researchが発見した4機構を配布するPi extension。公開物自体の継続自己進化とは分ける |
| [QuantaAlpha/EvoControl README](https://github.com/QuantaAlpha/EvoControl/blob/main/README.md) | 多様な初期計画＋mutation/crossover＋経験再利用。対象はalgorithm code最適化 |
| [SalesforceAIResearch/Beagle README](https://github.com/SalesforceAIResearch/Beagle/blob/main/README.md) | DarwinX実装を含むharness evolution基盤。Python 3.12+、既存benchmark運用依存 |
| [RealLcz/MGM README](https://github.com/RealLcz/MGM/blob/main/README.md) | 自己失敗/別task/別lineageからの3種mutation。Linux・Slurm/Apptainer系の重い実験環境 |
| [IQuestLab/ModularRSI README](https://github.com/IQuestLab/ModularRSI/blob/main/README.md) | 5個のharness moduleを別々に改変・統合。before/afterとcross-batchはREADME roadmap未完 |
| [shreydesai/self-improving-agent README](https://github.com/shreydesai/self-improving-agent/blob/main/README.md) | CSV分析agentのtool解放・動的tool提案。5taskの例、API license=null、一般化未検証 |
| [modelscope/AgentEvolver README](https://github.com/modelscope/AgentEvolver/blob/main/README.md) | self-questioning/navigation/credit attributionのRL training。運用中prompt書換えとは異なる |
| [jennyzzt/dgm README](https://github.com/jennyzzt/dgm/blob/main/README.md) | coding agent自身のcodeを変えarchiveを探索する基礎研究。最終pushは2025-08 |
| [simple-agent-lab/RSIHub README](https://github.com/simple-agent-lab/RSIHub/blob/main/README.md) | recipe/operatorを差し替え、framework-owned評価と実diffのmutable-surface検査を分離 |
| [skillberry-ai/cap-evolve README](https://github.com/skillberry-ai/cap-evolve/blob/main/README.md) | 既存agent/evalを利用。READMEではval有意差gate＋最後に1回のsealed test。beta |
| [twaldin/hone README](https://github.com/twaldin/hone/blob/main/README.md) | 不変evaluator/brokerと可変optimizerの分離。再帰optimizerの未知taskへの転移は未確立と明記 |
| [i3T4AN/KADATH README](https://github.com/i3T4AN/KADATH/blob/main/README.md) | 不変kernelと可変genomeを分離。epoch中genome読取専用、採点後mutation |
| [NousResearch/hermes-agent-self-evolution README](https://github.com/NousResearch/hermes-agent-self-evolution/blob/main/README.md) | GEPAでskill改変。tool/system/code/continuous loopはREADME上planned、API license=null |

特に次の4件は次回のcode読解候補として残す。

- **RSIHub**: recipeに評価を乗っ取らせず、frameworkが実際のtree diffを検査しclean checkoutを測定する役割分担。POWの「planは命令源ではない」という境界に近い。[README](https://github.com/simple-agent-lab/RSIHub/blob/main/README.md)。
- **cap-evolve**: 既存agent/evalを持ち込む方針と、sealed testを最後に1回だけ測る主張が有用。ただし今回source未確認なので「絶対漏れない」とは書かない。[README](https://github.com/skillberry-ai/cap-evolve/blob/main/README.md)。
- **hone**: proposerとtrusted brokerを分ける。再帰実験を動かしたことと未知taskへ一般化したことを分け、「まだ転移を立証していない」と公表している。固定computeの失敗例も載る。[README](https://github.com/twaldin/hone/blob/main/README.md)。
- **KADATH**: genomeは変えてもscore/goal/scheduler/lineage/isolation ruleを持つkernelは固定。epoch中のgenomeは読取専用。POWでは大規模populationではなく、この可変/不変の分割だけを持ち帰る。[README](https://github.com/i3T4AN/KADATH/blob/main/README.md)。

self-evolveはCの自動scenario生成と測定producerがなく、A+B併用もloopが拒否すると明記する。ModularRSIはbefore/after評価・cross-batch進化がroadmap未完。Hermes companionはSkillだけimplementedで、tool説明・system prompt・tool code・continuous loopはplanned。これらを完成した万能自己進化systemとして勧めない。[self-evolveの限界](https://github.com/DaizeDong/self-evolve/blob/main/README.md#current-limits)・[ModularRSI roadmap](https://github.com/IQuestLab/ModularRSI/blob/main/README.md#roadmap)・[Hermes段階表](https://github.com/NousResearch/hermes-agent-self-evolution/blob/main/README.md#what-it-optimizes)。

## POWへの優先順位 — 既存経路だけに接続する

POWの[hatarake Skill](../../commands/hatarake/SKILL.md)と[engine contract](../../commands/hatarake/references/contract.md)、[実装](../../commands/hatarake/scripts/hatarake.mjs)を照合した。既にimmutable contract hash、watched source/artifact hash、有限attempt/time/circuit、`review_required`、evidence-bound独立review、`tokens:null/cost:null`がある。`cxd`の[hooks.py](../../commands/optimize-latency/scripts/cxd/hooks.py)にもinput snapshot・bounded concurrency・失敗方針がある。重複基盤を作る理由はない。

| 優先 | 最小案 | 既存接続先 | 今回から導ける価値 / 留意点 |
| --- | --- | --- | --- |
| 1 | proposalに親のsource hash・対象path・1つの失敗仮説・実行証拠を結ぶ | hatarakeのwatch/fingerprint/evidenceHash | AgentDescentのstalenessとRRSIのedit budget。proposalが古ければ再採用せず再読する |
| 2 | 比較不能・未計測・拒否を成功/差0から分離する | attempt outcomeとreview package | PromptPotterの状態表現。必須実行のcrashは失敗、cost不明はnull、意味的判定不能はreviewに残す |
| 3 | 変更可能な対象と固定の採点契約を明示する | 既存contract・review対象範囲 | Hyperagents/KADATH/RSIHubとの比較。global指示や権限・採点契約を候補に書換えさせない |
| 4 | 停止理由・採否理由を1つの記録から出す | state.reason / attempt evidence / cxd failure | issueのように採用ledgerと診断文を食い違わせない。新しいdashboardは不要 |
| 5 | 必要な場合だけpromptのsize/growthと用途保持をreviewする | 既存Skill更新・独立review | gemini-evolveの量的gateは採るがkeyword scoreを品質の代用にしない |

この表は提案で、runtime変更はしていない。将来実装する際も、利用者が既に求めた実taskの成果物を既存compile/build/direct executionで確認し、テスト・fixture・benchmark・別harnessを増設しない。新たな有料model呼出やtraining費用は、今回の読解だけでは正当化できない。hatarakeのhashは同じ権限を持つ悪意あるprocessへのsandboxではない、という既存contractの限界も維持する。

## 確認範囲・残る不確実性

- **件数**: screen 23 = 新規22＋既知1。深掘り7 = 新規6＋既知1。新規2026作成18、100★未満9。深掘りは全件固定commit・root license・README・2本以上の実装、実装合計25本。
- issue本文を8件確認（GEPA 2、RRSI 2、AgentDescent 1、Hyperagents 2、PromptPotter 1）。Hyperagents #39とAgentDescent #617のcomment照会は0件。issueは一次の障害報告であり、独立再現や発生率の証拠ではない。open/closedは観測時点。
- 深掘り6件の新規候補で、部署横断・長期運用・未知課題へ安定して改善し続けることは立証していない。「自身を変更できる」と「変更が長期に有益」は別。
- screenedのみのlicenseはAPI/README値まで。shreydesaiとHermes companionのAPI license=nullは、別依存GEPAのMITをrepo全体へ伝播させる根拠にならない。
- 本調査では実行・導入・Windows動作確認・費用計測をしていない。star増加率、GitHub Trending順位、論文tableの再現、外部実験logの全監査もしていない。

[rrsi-selection]: https://github.com/google-research/rrsi/blob/be50316e1db05914068a973f322770ef08ed7ba1/rrsi/selection.py
[rrsi-critic]: https://github.com/google-research/rrsi/blob/be50316e1db05914068a973f322770ef08ed7ba1/rrsi/critic.py
[rrsi-evaluate]: https://github.com/google-research/rrsi/blob/be50316e1db05914068a973f322770ef08ed7ba1/rrsi/evaluate.py
[rrsi-readme]: https://github.com/google-research/rrsi/blob/be50316e1db05914068a973f322770ef08ed7ba1/README.md
[ad-aggregator]: https://github.com/Birfy/agentdescent/blob/d0c580ab1d3d90d0bd9414fbdd3455fc292696df/agentdescent/aggregator.py
[ad-goodhart]: https://github.com/Birfy/agentdescent/blob/d0c580ab1d3d90d0bd9414fbdd3455fc292696df/agentdescent/goodhart.py
[ad-readme]: https://github.com/Birfy/agentdescent/blob/d0c580ab1d3d90d0bd9414fbdd3455fc292696df/README.md
[pp-selection]: https://github.com/PromptPotter/prompt-potter-optimizer/blob/373199f83e4c43d6a299d32c33e1751e4abcb7bb/promptpotter/application/scoring/selection.py
[pp-paired]: https://github.com/PromptPotter/prompt-potter-optimizer/blob/373199f83e4c43d6a299d32c33e1751e4abcb7bb/promptpotter/domain/paired_reading.py
[pp-termination]: https://github.com/PromptPotter/prompt-potter-optimizer/blob/373199f83e4c43d6a299d32c33e1751e4abcb7bb/promptpotter/application/runner/termination.py
[pp-readme]: https://github.com/PromptPotter/prompt-potter-optimizer/blob/373199f83e4c43d6a299d32c33e1751e4abcb7bb/README.md
[pp-license]: https://github.com/PromptPotter/prompt-potter-optimizer/blob/373199f83e4c43d6a299d32c33e1751e4abcb7bb/LICENSE
[ha-meta]: https://github.com/facebookresearch/Hyperagents/blob/59a68f672dfb92c74aeb7e61535d776fb36e172d/meta_agent.py
[ha-loop]: https://github.com/facebookresearch/Hyperagents/blob/59a68f672dfb92c74aeb7e61535d776fb36e172d/generate_loop.py
[ha-select]: https://github.com/facebookresearch/Hyperagents/blob/59a68f672dfb92c74aeb7e61535d776fb36e172d/select_next_parent.py
[ha-utils]: https://github.com/facebookresearch/Hyperagents/blob/59a68f672dfb92c74aeb7e61535d776fb36e172d/utils/gl_utils.py
[ha-readme]: https://github.com/facebookresearch/Hyperagents/blob/59a68f672dfb92c74aeb7e61535d776fb36e172d/README.md
[ha-license]: https://github.com/facebookresearch/Hyperagents/blob/59a68f672dfb92c74aeb7e61535d776fb36e172d/LICENSE.md
[gg-optimizer]: https://github.com/go-go-golems/go-go-gepa/blob/408467c6e9cd18a533bb88405882d782174077d4/pkg/optimizer/gepa/optimizer.go
[gg-pareto]: https://github.com/go-go-golems/go-go-gepa/blob/408467c6e9cd18a533bb88405882d782174077d4/pkg/optimizer/gepa/pareto.go
[gg-readme]: https://github.com/go-go-golems/go-go-gepa/blob/408467c6e9cd18a533bb88405882d782174077d4/README.md
[ge-evolve]: https://github.com/LichAmnesia/gemini-evolve/blob/3f6c04446505bfad1b2b6ab5e5ab62ac4dd17872/gemini_evolve/evolve.py
[ge-constraints]: https://github.com/LichAmnesia/gemini-evolve/blob/3f6c04446505bfad1b2b6ab5e5ab62ac4dd17872/gemini_evolve/constraints.py
[ge-fitness]: https://github.com/LichAmnesia/gemini-evolve/blob/3f6c04446505bfad1b2b6ab5e5ab62ac4dd17872/gemini_evolve/fitness.py
[ge-gepa]: https://github.com/LichAmnesia/gemini-evolve/blob/3f6c04446505bfad1b2b6ab5e5ab62ac4dd17872/gemini_evolve/gepa_evolve.py
[ge-readme]: https://github.com/LichAmnesia/gemini-evolve/blob/3f6c04446505bfad1b2b6ab5e5ab62ac4dd17872/README.md
[gp-api]: https://github.com/gepa-ai/gepa/blob/80a62c879ecdeb8741faac72a844dceb1c18691f/src/gepa/api.py
[gp-acceptance]: https://github.com/gepa-ai/gepa/blob/80a62c879ecdeb8741faac72a844dceb1c18691f/src/gepa/strategies/acceptance.py
[gp-merge]: https://github.com/gepa-ai/gepa/blob/80a62c879ecdeb8741faac72a844dceb1c18691f/src/gepa/proposer/merge.py
