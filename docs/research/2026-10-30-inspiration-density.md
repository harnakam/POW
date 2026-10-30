# 情報密度・コード探索・安全な整理の調査 — 2026-10-30

優先候補は**入口を説明する証拠、失効境界、原文へ戻れる圧縮**。POWには保護・hash検証・隔離/restore、cxdのhash付きAST索引・常駐worker・hook/joinがある。以下は残る差分を扱う。[既存調査](2026-10-30-compressor.md)、[resident.py](../../commands/optimize-latency/scripts/cxd/resident.py)、[hooks.py](../../commands/optimize-latency/scripts/cxd/hooks.py)

## 対象と確認範囲

GitHub connectorで正規名・HEAD・license本文を確認。stars/pushは2026-10-30のAPI観測値。旧facebook/watchman、sourcegraph/scip、webpro/knipの移動先は下表の正規repo。starsは品質保証ではない。

| 正規repo | stars | 最終push | 状態・固定license |
|---|---:|---|---|
| [Watchman](https://github.com/meta/watchman) | 13,757 | 10-30 | active・[MIT](https://github.com/meta/watchman/blob/879494ce12ce0efecbff3dcb1f67feb635e2ea9e/LICENSE) |
| [Knip](https://github.com/webpro-nl/knip) | 12,552 | 10-30 | active・[ISC](https://github.com/webpro-nl/knip/blob/16fee14f4ec1bcd3244a1b4cb2ac15343a4e0999/LICENSE) |
| [Tree-sitter](https://github.com/tree-sitter/tree-sitter) | 27,330 | 10-30 | active・[MIT](https://github.com/tree-sitter/tree-sitter/blob/ad067fddf76a32c3071f8f3a31e8719d348e2737/LICENSE) |
| [SCIP](https://github.com/scip-code/scip) | 852 | 10-28 | active・[Apache-2.0](https://github.com/scip-code/scip/blob/bbec5345bfae602b31286a9ec74e2c2042713f50/LICENSE) |
| [ast-grep](https://github.com/ast-grep/ast-grep) | 16,399 | 10-29 | active・[MIT](https://github.com/ast-grep/ast-grep/blob/72f150994f2f5ffe52fd6d1e72f18a93c3998e0e/LICENSE) |
| [Pyright](https://github.com/microsoft/pyright) | 15,719 | 10-29 | active・[MIT本文](https://github.com/microsoft/pyright/blob/74743ab17950a6bd205935e21808102a610d40a1/LICENSE.txt) |
| [Unimport](https://github.com/unjs/unimport) | 681 | 10-12 | active・[MIT](https://github.com/unjs/unimport/blob/bbd07768ddb4919205bcb5a3cbc06c3a2791981a/LICENSE) |
| [RTK](https://github.com/rtk-ai/rtk) | 85,012 | 10-30 | active・[Apache-2.0](https://github.com/rtk-ai/rtk/blob/0dfe17b1873d6a2d1ee046f7b3a89aa6a262ae78/LICENSE) |
| [Headroom](https://github.com/headroomlabs-ai/headroom) | 78,286 | 10-30 | active・[Apache-2.0](https://github.com/headroomlabs-ai/headroom/blob/1fe8549f9ca77a2bc1280e4319980e0b9b31f5b9/LICENSE) |
| [depcheck](https://github.com/depcheck/depcheck) | 4,907 | 2025-02-27 | archived・[MIT](https://github.com/depcheck/depcheck/blob/9ff7081fe01fb2890c1ab73e79128e62b7cc7088/LICENSE) |

activeはarchived=false。SCIP/Unimportは専門枠、depcheckは比較対照。本人の[固定README](https://github.com/depcheck/depcheck/blob/9ff7081fe01fb2890c1ab73e79128e62b7cc7088/README.md)が保守停止・Knip移行を案内。PyrightのAPI判定NOASSERTIONよりlicense本文を優先。転載・導入・ベンチマークは未実施。

## 固定ソースから得た20の設計判断

機構の説明は確認事項、番号はPOWへの提案。

**入口と確信度。** Knipの[is-referenced.ts](https://github.com/webpro-nl/knip/blob/16fee14f4ec1bcd3244a1b4cb2ac15343a4e0999/packages/knip/src/graph-explorer/operations/is-referenced.ts)は入口からalias/namespace/star再exportを辿り、循環を止め、opaque/loader参照を区別する。Unimportの[scan-dirs.ts](https://github.com/unjs/unimport/blob/bbd07768ddb4919205bcb5a3cbc06c3a2791981a/src/node/scan-dirs.ts)は設定globと再exportを走査。import検索だけでは自動import対象を捉えない。

1. 候補に入口からの参照経路と入口の設定元を付ける。
2. alias・再export・循環を区別。未解決辺は「参照なし」にしない。
3. route/glob/自動import/plugin/scriptの入口adapterを用意し、未対応なら削除判断を保留。
4. 確信度はbyte一致/静的未到達/動的入口未確認と根拠別にし、未校正の確率を出さない。

**ASTと索引の境界。** Tree-sitterの[api.h](https://github.com/tree-sitter/tree-sitter/blob/ad067fddf76a32c3071f8f3a31e8719d348e2737/lib/include/tree_sitter/api.h#L282)は旧tree再利用前に実際の編集に一致するts_tree_editを要求し、changed_ranges・構文error・grammar ABIを公開する。Pyrightの[importResolver.ts](https://github.com/microsoft/pyright/blob/74743ab17950a6bd205935e21808102a610d40a1/packages/pyright-internal/src/analyzer/importResolver.ts#L141)はconfig変更で解決cacheを失効させる。一方、stdlib集合を環境別にkey化しない限界も同ファイルに明記している。

5. 既存hash cacheへparser/runtime版・設定・source rootの索引世代を加える。
6. 部分parseは実編集差分がある場合だけ。hash変更しか分からなければファイルを再parse。
7. 構文errorは正常な空索引にせず、失敗範囲と失効を返す。
8. 意味解析cacheにはvenv/search path/language版を含め、環境間共有は実測で判断。

**イベントと検索結果。** Watchmanの[since.cpp](https://github.com/meta/watchman/blob/879494ce12ce0efecbff3dcb1f67feb635e2ea9e/watchman/query/since.cpp#L44)は粗いtimestamp境界をinclusiveに扱い、fresh instanceでは存在するファイルを返す。SCIPの[scip.proto](https://github.com/scip-code/scip/blob/bbec5345bfae602b31286a9ec74e2c2042713f50/scip.proto#L41)はindexer版・引数・root・相対path・位置encodingを分離し、本文は通常重複保存しない。

9. watcher導入時はevent watermarkと索引世代を分ける。欠落・再起動では全体照合し、通知件数を完全性の証明にしない。
10. 同時刻更新・rename/delete・再走査を受入例にする。連続再走査には上限・backoff・不健全状態を設ける。
11. path/symbol/定義・参照/範囲/hash/生成元を返し、本文を追加取得。SCIP全体より先に共通形を試す。
12. 日本語・emojiを含む位置はbyte/UTF-16/code pointを宣言する。行列だけの曖昧な引用を避ける。

**重複と所有者。** ast-grepの[relational_rule.rs](https://github.com/ast-grep/ast-grep/blob/72f150994f2f5ffe52fd6d1e72f18a93c3998e0e/crates/config/src/rule/relational_rule.rs)はinside/has関係をfieldとstopByで限定する。Unimportの同名export整理も型・値・宣言元を区別する。どちらも「似た文字列なら意味が等しい」という仕組みではない。

13. 小抽象・重複コードの候補は構文と利用箇所を添える。単なる短さや同じ関数名を整理理由にしない。
14. Markdown類似度は候補検索に限定。目的・読者・期限・所有者・独自制約を比較し、固有の運用例/復旧条件を残す。
15. 既存隔離planへowner/consumerと存続先を追加する。テスト・契約・リンクの役割が移る先を示せないものはretainとする。

**回収可能な圧縮。** RTKの[tee.rs](https://github.com/rtk-ai/rtk/blob/0dfe17b1873d6a2d1ee046f7b3a89aa6a262ae78/src/core/tee.rs#L118)はposthookでfilter前のrawを保存し、同時書込み識別子と専用rotation枠を持つ。Headroomの[mcp_server.py](https://github.com/headroomlabs-ai/headroom/blob/1fe8549f9ca77a2bc1280e4319980e0b9b31f5b9/headroom/ccr/mcp_server.py#L462)は原文保存に失敗すると原文を返し、保存できた場合だけhashで回収可能にする。

16. 圧縮結果に原文hash・回収方法・省略範囲・保持期限を付ける。保存不能時はrawを返す。
17. 原文取得経路を再圧縮しない。期限切れと未保存を区別し、再取得すべき元コマンドを示す。
18. JSON/JSONL/SARIF/JUnitの機械向け出力は構造を保持する。未知形式の文字数切捨てを成功扱いしない。
19. 先頭の推測よりcommand/toolの形式情報を優先。不明・例外・deadline超過はrawへ戻す。
20. 圧縮時間・回収回数・総入力・誤判断も測る。小出力や短い索引は圧縮を省略。

## 失敗例からの受入条件

- **誤った未使用判定:** [Knip #1771](https://github.com/webpro-nl/knip/issues/1771)はHTML内module importの見落とし。[PR #1772](https://github.com/webpro-nl/knip/pull/1772)はinline import抽出と有効/未使用双方のfixtureを追加し修正済み。入口adapterには必ず両側の例を置く。[修正ソース](https://github.com/webpro-nl/knip/blob/51f4eddc9e1b2fed1ba25e81fc596e9fb514ce01/packages/knip/src/plugins/vite/helpers.ts#L37)
- **再走査の暴走:** [Watchman #1354](https://github.com/meta/watchman/issues/1354)はイベント欠落後14,459回のrecrawlと初期走査未完を報告しopen。利用者報告で再現・頻度は未確認。完全再走査に復旧上限も必要。
- **構造と失敗信号の消失:** openの[RTK #4655](https://github.com/rtk-ai/rtk/issues/4655)は構造化出力の切断、[RTK #4692](https://github.com/rtk-ai/rtk/issues/4692)はGo testの誤分類でFAIL行を失う報告。圧縮率が高くても検証証拠としては失格。
- **圧縮自身の遅延:** openの[Headroom #600](https://github.com/headroomlabs-ai/headroom/issues/600)はWindowsの大きなJSON/MCP呼出し停止を報告。POWでの再現は未実施。Windows受入、timeout、raw fallbackを導入判断に含める。

## POWでの優先順と依存費用

| 優先 | 小さく追加する差分 | 導入判断・費用 |
|---|---|---|
| 1 | compressor候補へ入口coverage・未解決辺・根拠別確信度 | まず標準機能と既存索引。自動削除権限を増やさない |
| 2 | cxd/圧縮表示へ原文参照とraw回収の契約 | RTK等の既存回収機構を確認し再利用。別の保存系を増やさない |
| 3 | index世代へruntime/config、失敗状態、証拠の位置encoding | hash cacheを拡張。常駐化やhookを作り直さない |
| 4 | owner/consumer/存続先に基づく文書統合plan | embedding不要。少数候補を人が比較し、隔離/restoreを再利用 |
| 5 | 実測で必要な言語だけAST adapter・event差分 | Tree-sitter/ast-grepは任意。grammar配布・native build・版管理費が生じる |

Knipは既存JS/TS開発依存なら任意診断に使う。PyrightはPython意味解析、SCIPは複数indexer交換が必要な段階で検討。Headroom一式やwatcher daemonは、短い証拠で解けない課題を測ってから採用する。

確認範囲は10 repoのmetadata/license、10固定実装ソース、depcheck README、4系統の障害資料。実行再現・性能精度比較・buildは未実施。導入時はlicense/NOTICEとgrammar同梱条件を再確認。本変更は調査文書のみ。
