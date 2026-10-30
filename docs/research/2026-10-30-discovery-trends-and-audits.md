# 新規探索: Trending、実行証跡、表示品質、自己改善の限界

調査日: 2026-10-30。過去のPOW調査で名前が出ていなかった8 repoをGitHub REST APIで照合し、うち6件で具体的な実装を読んだ。これは動作・性能の追試ではない。公開資料の読み取りだけを行い、導入やコード実行、テスト・harness追加はしていない。

## 発見方法と鮮度

[GitHub Trending daily](https://github.com/trending)、[monthly](https://github.com/trending?since=monthly)、Topics、日付を含むWeb検索、作者のREADMEと実装から候補を広げた。dailyでThinkRail、nightly-labs/openbot、CopilotKit/OpenBotを確認。monthlyの取得結果にはArchify、diagram-design、Switchyard、Makaがあった。ただしmonthlyは検索側が「last month」と表示したcacheであり、10月30日の直近30日順位・増加数とは扱わない。ページ掲載と現在のtotal starsを区別し、以下の値はAPIの単一観測である。新規とは今回のPOW調査に対する新規で、公開直後という意味ではない。

## 8件の照合

全件archived=false。日付はUTC、starsは観測値。APIのlicense判定は本文と同じとは限らない。licenseの列は読めたルート本文を優先した。

| repo / metadata | stars | 作成 / 最終push | license本文 | 調査の深さ・用途 |
| --- | ---: | --- | --- | --- |
| [JetBrains/thinkrail](https://api.github.com/repos/JetBrains/thinkrail) | 6,187 | 07-08 / 10-29 | Apache-2.0 | 深掘り。自分に合うIDEという構想と、既実装の再送・委任制御を分ける |
| [nightly-labs/openbot](https://api.github.com/repos/nightly-labs/openbot) | 4,026 | 08-12 / 10-30 | PolyForm Noncommercial 1.0.0 | 選別。APIはNOASSERTION。名前・説明だけでOSS依存にしない |
| [apache/maka](https://api.github.com/repos/apache/maka) | 5,927 | 05-27 / 10-30 | Apache-2.0 + notices | 深掘り。復帰時の書込権限と原文回収の照合 |
| [NVIDIA-NeMo/Switchyard](https://api.github.com/repos/NVIDIA-NeMo/Switchyard) | 3,466 | 05-19 / 10-30 | Apache-2.0 | 深掘り。レビュー呼出予算、失敗予算、見えない消費量 |
| [tt-a1i/archify](https://api.github.com/repos/tt-a1i/archify) | 91,583 | 04-15 / 10-30 | Apache-2.0、MIT資源も別途存在 | 深掘り。コード根拠付きの図、構造合格と見た目の評価の分離 |
| [cathrynlavery/diagram-design](https://api.github.com/repos/cathrynlavery/diagram-design) | 63,053 | 04-16 / 10-27 | MIT | 選別。意味のpatternとlayoutを分けるSkill。engine監査はしていない |
| [CopilotKit/OpenBot](https://api.github.com/repos/CopilotKit/OpenBot) | 8,318 | 08-17 / 10-29 | MIT | 深掘り。実行前の判断と実行後の結果、正しいinitiatorの記録 |
| [drrawal/self_healing_multi_agent-_system](https://api.github.com/repos/drrawal/self_healing_multi_agent-_system) | 0 | 07-19 / 07-19 | API null、treeにルートLICENSEなし | 深掘りした保留例。実コードはあるが、論文風の性能主張を採用根拠にしない |

## 実装から得た6件の判断

### ThinkRail: 自己拡張の将来像と、再送制御の現在地

固定HEAD: `df7cb6d2dd5fafbc6ed8eea721f16e54f09e38fc`。[README](https://github.com/JetBrains/thinkrail/blob/df7cb6d2dd5fafbc6ed8eea721f16e54f09e38fc/README.md)はliving specsと再利用Skillを現在の機構とし、必要な道具を自ら作る拡張を今後の方向として説明する。「使うほど良くなる」を、基盤LLMの自動学習が完成している証拠にしない。

実装上の収穫は[requestReplayCache.ts](https://github.com/JetBrains/thinkrail/blob/df7cb6d2dd5fafbc6ed8eea721f16e54f09e38fc/packages/server/src/host/requestReplayCache.ts)。client namespace、request ID、payload fingerprintを照合して同一Promiseへ合流し、同じIDで別内容なら拒否する。未確認結果が多ければoverflow、結果保持予算を超えた既実行IDにはunretainedを返し、処理をもう一度実行して埋めない。[subagentPolicy.ts](https://github.com/JetBrains/thinkrail/blob/df7cb6d2dd5fafbc6ed8eea721f16e54f09e38fc/packages/server/src/host/subagentPolicy.ts)はworkspaceごとの有効化と並列上限を解決する。

POWへの判断: native hookのevent/call IDにpayload fingerprintを結び付け、再配信と別要求を区別する候補。現在のsource hashによる重複抑止とは別の層になる。保存し切れない結果を再実行しない原理を借りる。IDE、Pi実行器、SPECのgraph全体を導入する必要はない。cacheのweightはstringなら文字数、それ以外は1なので、そのまま総メモリ量の上限として使わない。[LICENSE](https://github.com/JetBrains/thinkrail/blob/df7cb6d2dd5fafbc6ed8eea721f16e54f09e38fc/LICENSE)。

### Maka: 復帰できることと、安全にsnapshotできることは別

固定HEAD: `85a1031c10d104456127f35aac1523b9ffb1a384`。[session-checkpoint-publication.ts](https://github.com/apache/maka/blob/85a1031c10d104456127f35aac1523b9ffb1a384/packages/runtime-host/src/server/session-checkpoint-publication.ts)はモデルが申告したidleをsnapshot許可にせず、全writerを排他できるhost側の権限を要求する。durable保存場所とlive/control/workspaceを分離し、WindowsではstagingのACLを確認するauthorityがなければ利用不可にする。

[ledger-tool-result-archive-reader.ts](https://github.com/apache/maka/blob/85a1031c10d104456127f35aac1523b9ffb1a384/packages/runtime/src/ledger-tool-result-archive-reader.ts)はsession/event/call/tool、元bytes、SHA-256、projection transitionを照合し、原文回収の失敗理由を返す。短いplaceholderがあるだけで原文が復元できると主張しない。[README](https://github.com/apache/maka/blob/85a1031c10d104456127f35aac1523b9ffb1a384/README.md)も復帰のモデル呼出費用、旧データ移行の制約、既存failed/cancelled turnを自動選択しない条件を明記する。

POWへの判断: 復帰capsuleや出力圧縮を作るなら、元要求と原文の所在・digest・入力世代を残す。session全体のsnapshot engineは大き過ぎる。現状の.cxd状態から必要な情報だけ構成し、復元できない証拠はunknownにする。[LICENSE](https://github.com/apache/maka/blob/85a1031c10d104456127f35aac1523b9ffb1a384/LICENSE)には付随するnoticeもある。依存木全体は監査していない。

### Switchyard: 評価役にも予算が要る

固定HEAD: `3204554a1d997170804f02529a83fa15b1448558`。[advisor_gate/budget.rs](https://github.com/NVIDIA-NeMo/Switchyard/blob/3204554a1d997170804f02529a83fa15b1448558/crates/libsy/src/algorithms/advisor_gate/budget.rs)はレビュー枠を先にatomic reserveし、失敗時にrefundする一方、別の失敗上限も増やす。単なるrefundだけで無限に呼べる状態を防ぐ。scopeとstall latchには保持上限もある。

[advisor_gate.rs](https://github.com/NVIDIA-NeMo/Switchyard/blob/3204554a1d997170804f02529a83fa15b1448558/crates/libsy/src/algorithms/advisor_gate.rs)と[設計文書](https://github.com/NVIDIA-NeMo/Switchyard/blob/3204554a1d997170804f02529a83fa15b1448558/docs/routing_algorithms/advisor_gate_routing.md)は、実装役を替えず終端・停滞時だけadvisorを呼ぶ。破棄した回答のtokenも観測する。ただし失敗時は既定で通過し、判定parse不能も通過する経路がある。これはサービス可用性の選択であり、POWの「検証済み」の根拠にはできない。

POWへの判断: `/hatarake`へ任意reviewを足す場合、実行役と評価役の予算を別に持ち、同一cause・世代の重複reviewを止める。unknownを合格にせず実行証拠を優先する。モデルroutingを既定変更しない。[README](https://github.com/NVIDIA-NeMo/Switchyard/blob/3204554a1d997170804f02529a83fa15b1448558/README.md)自身も「1呼出の安さ」と完了taskの費用を区別し、standalone serverをdemo用途とする。[LICENSE](https://github.com/NVIDIA-NeMo/Switchyard/blob/3204554a1d997170804f02529a83fa15b1448558/LICENSE)。

### Archify: 合格receiptと、視覚品質を混同しない

固定HEAD: `f325d86230553e1dd15d3464324f1fcd01f02352`。[repository-evidence.mjs](https://github.com/tt-a1i/archify/blob/f325d86230553e1dd15d3464324f1fcd01f02352/archify/renderers/shared/repository-evidence.mjs)は40桁SHA、origin、repo root、固定treeのfileと行範囲を確認し、Git replacement refsや自動network取得にも依存しない。多数の参照はcat-file batchで読み、壊れた参照を通過扱いにしない。[layout-report.mjs](https://github.com/tt-a1i/archify/blob/f325d86230553e1dd15d3464324f1fcd01f02352/archify/renderers/shared/layout-report.mjs)は計算したboxと経路を再修正できる情報として出す。

[Skill](https://github.com/tt-a1i/archify/blob/f325d86230553e1dd15d3464324f1fcd01f02352/archify/SKILL.md)は自動gate合格と画面の目視確認を分離し、視覚確認していない場合の扱いも定める。修正対象をdiagnosticのsubjectとsupportedFixesに狭め、配置を改善して悪化したら戻す有限の手順がある。

POWへの判断: `/design-reasoning`でも「構造上の問題なし」と「実画面を見て良い」を別の結果にする。図や説明の出典を生成文だけで信じず、repo・revision・pathへ結び付ける。全rendererや全diagram類型をPOWへ複製しない。[LICENSE](https://github.com/tt-a1i/archify/blob/f325d86230553e1dd15d3464324f1fcd01f02352/LICENSE)と別MIT資源が存在するため、将来の再利用は対象資源単位で確認する。

### CopilotKit/OpenBot: 許可された、実行した、成功したを分ける

固定HEAD: `ab9855c19848378c90a806426130d86699cc798c`。[policy.ts](https://github.com/CopilotKit/OpenBot/blob/ab9855c19848378c90a806426130d86699cc798c/server/src/computer/policy.ts)はdenyをallowより優先し、呼出元の主張だけでなくserverが得た要素情報を使う。clickの名前だけではEnter/Space/submit付きtypeで同じ効果が起きるため、操作の効果も分類する。ただしDOM構造が分からない段階の判定には限界があると明記する。

[audit.ts](https://github.com/CopilotKit/OpenBot/blob/ab9855c19848378c90a806426130d86699cc798c/server/src/audit.ts)は許可拒否、外部処理失敗、成功、認証前の拒否を区別する。過去に外部call前からsuccessを記録していた問題の説明があり、initiatorを確定できない場合に架空のbot IDを付けない。payloadの機微keyをredactし、DB insertに成功してからtapへ流す。

POWへの判断: hookが起動した事実を成功receiptと混ぜず、call ID・実cwd・cause・完了結果を結ぶ。全文保存を増やさず、所有scopeと証拠pathを残す。全gatewayやPostgreSQLを依存にしない。[README](https://github.com/CopilotKit/OpenBot/blob/ab9855c19848378c90a806426130d86699cc798c/README.md)は完成したhosted製品ではなくcloneして構成するtemplateと明記。[LICENSE](https://github.com/CopilotKit/OpenBot/blob/ab9855c19848378c90a806426130d86699cc798c/LICENSE)。

### SH-MAS: 実コードがあっても性能主張は別に確かめる

固定HEAD: `148a9755d60dab51a0c13fd2c129cd3964ee3f0d`。[RESEARCH_PAPER.md](https://github.com/drrawal/self_healing_multi_agent-_system/blob/148a9755d60dab51a0c13fd2c129cd3964ee3f0d/RESEARCH_PAPER.md)には著者・所属・DOIのplaceholderが残る。この記載をIEEE採録や査読済みの証拠にはできない。公開code自体は存在し、[reflection.py](https://github.com/drrawal/self_healing_multi_agent-_system/blob/148a9755d60dab51a0c13fd2c129cd3964ee3f0d/core/agents/reflection.py)はLLMのconfidenceと修正案をparseし、失敗時はretryへfallbackする。[edges.py](https://github.com/drrawal/self_healing_multi_agent-_system/blob/148a9755d60dab51a0c13fd2c129cd3964ee3f0d/core/graph/edges.py)にはrepair上限があり、無限loopとは断定しない。

[experiments/runner.py](https://github.com/drrawal/self_healing_multi_agent-_system/blob/148a9755d60dab51a0c13fd2c129cd3964ee3f0d/experiments/runner.py)は例外で終わったrunを結果listへ加えず、複数scenarioで共有tool classのfailure_rateを変更しながらgatherする。集計の分母とscenario独立性は追加確認が必要。宣伝の成功率をPOWの効果へ転記せず、参考候補として保留する。ライセンスはAPI nullかつ確認したtreeにルートLICENSEがない。

## 選別2件から残す観点

- nightly-labs/openbotはCopilotKit/OpenBotとは別repo。[固定LICENSE](https://github.com/nightly-labs/openbot/blob/f3e3f8ade9c146e96d9d68d65770d2a9126a7856/LICENSE)はPolyForm Noncommercial。名前が同じことやAPIのNOASSERTIONからMITと推定しない。実行器を深掘りした件数には含めない。
- diagram-designの[Skill](https://github.com/cathrynlavery/diagram-design/blob/0cf73c3fcc56667ad91a9a04c439ac6ccfabc9d1/skills/diagram-design/SKILL.md)は意味のpattern→図の型→複雑さ上限という順番を持ち、原文のlabelやdirectiveは非信頼データとして扱う。[MIT本文](https://github.com/cathrynlavery/diagram-design/blob/0cf73c3fcc56667ad91a9a04c439ac6ccfabc9d1/LICENSE)を確認。美的品質や45類型全体の動作は未検証で、今回は選別に留める。

## 最近の研究で補う判断

[Reward Hacking Challenges Oversight of Autonomous Research Agents, 2026-09-23 v1](https://arxiv.org/abs/2609.28614v1)は、研究agentが成果物と採点根拠の両方を変更できる設定を扱い、codeと報告scoreだけを見るLLM panelでも見逃しが起きること、反復feedback条件で回避が増えることを報告する。詳細feedbackの条件は履歴等も異なるため、説明だけが原因とはしない。POWへの推論は、評価metric・対象データ・最終状態を実装役から独立させること。追加LLMを呼ぶだけで独立検証になったと扱わない。

[Dr. Free, 2026-09-27 v1](https://arxiv.org/abs/2609.33565v1)は検索agentの学習で、solverが難しいと感じることと必要な証拠を使うことを区別する。shortcut contextとの比較で情報利得を評価する研究で、重み更新を含む訓練が対象。POWの軽量Skill更新へ訓練器を移植せず、「何に役立ったから採用するか」という評価signalの設計を参考にする。ここでは両論文の著者abstractと一次掲載情報を確認し、実験は再現していない。
