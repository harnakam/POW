# 2026-10-30 新規発掘: 経験を記憶・手順へ変える実装

調査日: 2026-10-30。GitHub の現在の検索結果から候補を得て、公開 GitHub API、固定 commit のソース、作者の説明・issue を読んだ。一般的な vector DB 一覧ではなく、経験の抽出、手順化、失敗からの修正、失効、削除、必要な文脈だけの再読込を対象にした。

**新規候補15件を選別し、そのうち6件を実装まで深読した。既調査の cass_memory_system 1件は再確認枠で、15件にも新規深読6件にも含めない。** 選別は README と repository metadata、深読はそれに加えて root LICENSE、固定 commit の実装ファイル2件以上、作者の限界説明または実際の issue/thread を読んだことを指す。実行、再現、インストール、外部変更はしていない。stars は一点観測で、成長率・流行の証明ではない。

## 発見経路と採否

最初から名前を並べず、GitHub repository search の `"procedural memory" agent created:>2025-01-01`、`"skill" "self-evolving" pushed:>2026-09-01`、`"memory" "agent" created:>2026-09-01 stars:3..500` を検索した。後者の低 star・作成日条件から Octop Memory、Cairn、Agent Memory Integrity 等が出た。加えて現在の Web 検索 `github agent experience skill memory "2026" "self-evolving"` と `github "procedural memory" agents "2026"` を使い、[scriptflow の作者投稿](https://www.reddit.com/r/LLMDevs/comments/1xd7cmt/i_built_a_procedural_memory_system_for_ai_agents/)と [SEPM の原論文](https://arxiv.org/abs/2610.14515)から公式 repository を辿った。検索結果や survey は発見用で、実装上の根拠は下記の一次資料に置いた。

表の created / pushed は API の `created_at` / `pushed_at` の UTC 日付。全件で API の license / archived を取得した。`false` は archive されていない意味で、品質や保守継続の保証ではない。各 repository 名のリンクが metadata の取得先、説明中の README リンクが選別内容の根拠。

| 新規 repository / API | stars | created UTC | pushed UTC | API license / archived | 選別結果・今回の判断 |
|---|---:|---|---|---|---|
| [GrappinoRoot/scriptflow](https://api.github.com/repos/GrappinoRoot/scriptflow) | 1 | 2026-10-20 | 2026-10-20 | MIT / false | **深読**。成功 trace の parameter 化と失敗時 fallback が小さい。[README][sf-readme] |
| [ViktorAxelsen/MemSkill](https://api.github.com/repos/ViktorAxelsen/MemSkill) | 589 | 2026-01-30 | 2026-10-01 | Apache-2.0 / false | **深読**。記憶する方法そのものを更新する。作業手順学習とは区別する。[README][ms-readme] |
| [cookieApril/SEPM](https://api.github.com/repos/cookieApril/SEPM) | 3 | 2026-08-03 | 2026-10-26 | MIT / false | **深読**。SOP の提案・検証・昇格・版管理・引退を分ける。[README][se-readme] |
| [thebasedcapital/brainbox](https://api.github.com/repos/thebasedcapital/brainbox) | 14 | 2026-02-16 | 2026-10-09 | MIT / false | **深読**。失敗→修正→成功からの procedure 抽出と、効果主張の撤回が参考になる。[README][bb-readme] |
| [skhynix/MemFlow](https://api.github.com/repos/skhynix/MemFlow) | 10 | 2026-03-31 | 2026-10-28 | Apache-2.0 / false | **深読**。生成学習ではなく、trust を保持する skill 検索・注入・圧縮後の再読込。[README][mf-readme] |
| [TheWariend/MuscleMemory](https://api.github.com/repos/TheWariend/MuscleMemory) | 40 | 2026-07-21 | 2026-10-25 | Apache-2.0 / false | **深読**。成功証拠、承認、独立 check、現在ファイル照合、削除済み skill の復活防止。[README][mm-readme] |
| [zjunlp/MemP](https://api.github.com/repos/zjunlp/MemP) | 41 | 2026-01-10 | 2026-01-30 | MIT / false | 保留。trajectory から細粒度 instruction と上位 script を抽出。今回の軽量移植候補は、最近の変更と撤回条件が見える上の6件を優先。[README](https://github.com/zjunlp/MemP/blob/main/README.md) |
| [TheWariend/CleanSlate](https://api.github.com/repos/TheWariend/CleanSlate) | 15 | 2026-07-27 | 2026-10-28 | MIT / false | 見送り。VS Code ベースの workspace、SDK、CLI 全体を導入するのは広い。同作者の学習機構 MuscleMemory を別に読んだ。[README](https://github.com/TheWariend/CleanSlate/blob/main/README.md) |
| [vbcherepanov/total-agent-memory](https://api.github.com/repos/vbcherepanov/total-agent-memory) | 73 | 2026-02-16 | 2026-10-29 | MIT / false | 見送り。knowledge graph、code ingest、MCP 等を含む永続 memory platform。今回必要な小さい手順学習に対して導入面が広い。性能値は再現していない。[README](https://github.com/vbcherepanov/total-agent-memory/blob/main/README.md) |
| [qingshanyuluo/exogram](https://api.github.com/repos/qingshanyuluo/exogram) | 9 | 2026-02-03 | 2026-02-25 | MIT / false | 保留。browser demonstration→distillation→rule injection は関連するが、対象が browser-use 系で、今回の POW の local workflow とずれる。[README](https://github.com/qingshanyuluo/exogram/blob/main/README.md) |
| [TencentCloud/octop-memory](https://api.github.com/repos/TencentCloud/octop-memory) | 86 | 2026-09-24 | 2026-10-28 | MIT / false | 追跡。owner 文書優先、synthetic runtime error の自動記憶除外、provenance による retirement が興味深い。手順獲得より fact/context 維持寄り。README は実 Chroma/Qdrant 統合未検証を明記する。[README](https://github.com/TencentCloud/octop-memory/blob/main/README.md) |
| [memodb-io/Acontext](https://api.github.com/repos/memodb-io/Acontext) | 3,698 | 2025-07-16 | 2026-10-24 | Apache-2.0 / **true** | 導入見送り。作者 README 冒頭が保守終了と alook.ai への注力を明記。star 数より保守状態を重視する。[README](https://github.com/memodb-io/Acontext/blob/main/README.md) |
| [Cairn-ink/cairn-memory](https://api.github.com/repos/Cairn-ink/cairn-memory) | 33 | 2026-09-04 | 2026-10-30 | Apache-2.0 / false | 追跡。source receipt と preference の変更・削除を人が点検できる。作者は preview、既定 extraction が source-support の基準を満たさないと明記。receipt は真実の証明ではない。[README](https://github.com/Cairn-ink/cairn-memory/blob/main/README.md) |
| [tech4biz-yasha/agent-memory-integrity](https://api.github.com/repos/tech4biz-yasha/agent-memory-integrity) | 3 | 2026-09-14 | 2026-10-27 | MIT / false | 参照のみ。改ざん、rollback、削除後の復活を分ける観点が有用。実体は conformance suite で、今回 POW に harness を足す根拠にはしない。作者は自分の過去の no-op 測定も訂正している。[README](https://github.com/tech4biz-yasha/agent-memory-integrity/blob/main/README.md) |
| [Seeing-Maintaining-Learning/multimodal-agent-memory-evolution](https://api.github.com/repos/Seeing-Maintaining-Learning/multimodal-agent-memory-evolution) | 42 | 2026-09-29 | 2026-10-26 | MIT / false | 発見 index として保留。memory state 更新と learning policy 更新の分類は有用だが、survey であり移植する runtime ではない。深読実装数に含めない。[README](https://github.com/Seeing-Maintaining-Learning/multimodal-agent-memory-evolution/blob/main/README.md) |

## 「学習」の中身を混同しない

| 実装 | 変化するもの | 今回確認できたこと / できないこと |
|---|---|---|
| MemFlow | 既存 skill の索引、snapshot、検索順、読込履歴 | 検索・文脈配送であり、新しい能力や手順の獲得ではない。[README][mf-readme] |
| brainbox | file/tool/error 間の関連 weight、procedure、注入量 policy | local 数値と外部記憶を更新する。LLM parameter の更新ではない。[procedures][bb-procedures]・[policy][bb-policy] |
| scriptflow / MuscleMemory / SEPM | 経験から得た手順、適用条件、証拠、状態、版 | 外部 procedural memory。将来の別 task での再利用は可能だが、一般的能力向上の証明は別途必要。[compiler][sf-compiler]・[MuscleMemory learning][mm-how]・[SEPM service][se-service] |
| MemSkill | 何を抽出するかという memory skill の文章 + skill 選択 controller の parameter | README は meta-memory と明記。`trainer.py` は controller に `backward` / optimizer step を行う。base LLM 全体が自動で更新されるという意味ではない。[README][ms-readme]・[controller][ms-controller]・[trainer][ms-trainer] |

保存量増加、summary の更新、検索成功、file を開いた頻度、手順の再利用、未知 task への能力転移はそれぞれ違う結果である。以下の採用判断は source inspection に基づく提案で、POW の速度や成功率が上がったという測定ではない。

## 新規の深読6件

### 1. MuscleMemory: 何をもって「前回うまくいった」とするか

固定 commit `e7f869dbe3bc2a8dd9721cb1a9684f9972bd674a`。root [LICENSE][mm-license] は Apache-2.0。読みどころは「記憶する」機能より、成功を偽らない admission と stale detection にある。

`client_hooks.py` の `_final_test` は capture に欠落があれば成功証拠を返さず、最後のコード変更で先行する test の証拠を捨て、その後の最後の test の既知結果だけを使う。browser interaction は local test では検証できないため別扱い。`service.py` の `evaluate` は同じ run の評価書換えを拒み、失敗した revision を flagged にする。`delete_memory` / `bury` は削除した各版の skill fingerprint を tombstone に残し、同じ経験を再抽出して復活させることを防ぐ。[client_hooks.py#L954][mm-hooks]・[service.py#L79][mm-service]・[service.py#L1260][mm-evaluate]・[service.py#L1679][mm-delete]

`hook_files.py` の current-file check は最大32ファイル・各1MiB、project 外と symlink を拒み、保存された before/after text が現在のファイルに少なくとも1つ合うことを要求する。全不一致なら配送しない。部分一致なら不一致を残す。この check は file text の照合であり、動作保証ではない。`os.O_DIRECTORY` / `os.O_NOFOLLOW` と `dir_fd` を使うので、この実装を Windows の POW にそのまま写すのも適切でない。[hook_files.py][mm-files]

作者自身の [issue #2](https://github.com/TheWariend/MuscleMemory/issues/2) は、無関係な passing test が skill を trusted に近づけていた問題を記録し、正規化した**skill 自身の test command**が最後の変更後の最後の test であるよう修正したと説明する。[issue #3](https://github.com/TheWariend/MuscleMemory/issues/3) は file check が hooks だけで、server/MCP は current file を見られない限界を明記。[issue #4](https://github.com/TheWariend/MuscleMemory/issues/4) は既定 namespace が project 間で共通で、cross-repository recall は未検証と明記する。

README と設計説明は、承認、少なくとも2回の独立 passing check、reliability、90日以内の validation、tool/permission 適合を列挙する。一方 trace は既定30日で期限切れとなり、skill/evaluation が残っても元の raw event が消える場合がある。根拠の長期保存と skill の寿命は別設計が要る。作者も評価は少数の制御 codebase と小さい Claude run と限定する。[README][mm-readme]・[how-it-works][mm-how]

**POW に借りるなら:** 既存の検証を追加実行するのではなく、既に行った最終変更後の実行結果だけを learning evidence に紐付ける。source hash / 適用条件が変わったら以前の成功を持ち越さず、撤回した fact の ID/hash を残す。新しい test suite、常時 hook、server、embedding 導入は不要。

### 2. SEPM: procedure の提案と採用を分ける

固定 commit `fbbed150d1520dc527d42a6415876a944efe83a4`。root [LICENSE][se-license] は MIT。`SOPCandidate` は unpublished proposal で、source workspace、base version/fingerprint、state verification、causal confidence を別 field とする。条件限定の変化は親を上書きする代わりに variant とする。[models.py#L323][se-models]

`promote_candidate` は safety / state_verified / causal_attribution / reproduction / net_benefit の5 gate を再計算する。net benefit は成功例だけでなく**失敗を含む全 trial**の `candidate_reward - baseline_reward - cost_weight * cost` の平均。削除も version/fingerprint を通して行う。[service.py#L439][se-service]・[models.py#L391][se-trials]

ただし既定閾値は1で、最初の qualified trial が publication を起こし得る。`state_verified` / `causal_supported` は入力する側が与える値であり、この class が環境の真偽や因果を自動的に立証するわけではない。`SafetyValidator` は確認・backup・不可逆操作の明示 flag と英中 keyword を使う deterministic gate。mandatory step の削除や弱化を防ぐ一方、未知の言い回しまで意味理解する保証ではない。[service.py#L421][se-reproduction]・[models.py#L391][se-trials]・[safety.py][se-safety]

`SOPRetriever.rank` は active な SOP のうち、context_conditions が verified context facts の subset で、exclusions に当たらないものだけを ranking する。条件は単なる keyword 加点ではない。この applicability gate が POW には特に小さく移せる。[retrieval.py#L67][se-retrieval]

作者 README の Evaluation 節は、公開 selected-case workflow と ignored local result だけでは掲載された full benchmark score を再生成できないと明記する。性能表を POW への効果保証として使わない。[README][se-readme]

**POW に借りるなら:** 新規 fact を候補のまま提示し、source / current applicability / observed outcome / negative evidence が揃うかを短い欄で判定する。SOP graph、multi-agent blackboard、学習 loop 全体は導入しない。特に入力された `verified: true` を実証と取り違えない。

### 3. scriptflow: trace の一般化に失敗したら覚えない

固定 commit `cfa3b8bbf19b43a5a055865a27cec04a96f78701`。root [LICENSE][sf-license] は MIT。`compile_procedure` は request parameter と先行 step の出力参照を tool 引数へ埋め込む。由来不明の opaque ID、未使用 parameter、部分文字列に落ちた parameter などは拒否する。保存形式は tool/args の JSON で、生成 Python を eval/import する設計ではない。[compiler.py][sf-compiler]・[runtime.py][sf-runtime]

とはいえ JSON の再生も host の `call_tool` を再実行する。外部変更、冪等性、認可は host の責任である。`recorder.py` の既定成功は最低1 tool 成功、blocked/skipped なし、final answer ありという構造条件。任意の `mutation_verifier` は「作成要求なのに検索だけした」を弾けるが、書込み結果の意味的正しさまでは保証しない。[recorder.py][sf-recorder]・[verify.py][sf-verify]

Skill 型は learned_from、created_at、runs/failures/last_run_at を持つが、確認した型に source commit/tool schema hash/expiry/revocation reason はない。`FileStore.delete` は削除を提供するが、tombstone 付き再学習防止とは別。全 skill の intent/parameters/description を classifier prompt に並べるため、catalog が膨らめば検索前の context cost も増える。[types.py#L88][sf-types]・[store.py#L114][sf-store]・[intent.py][sf-intent]

[作者の Reddit thread](https://www.reddit.com/r/LLMDevs/comments/1xd7cmt/i_built_a_procedural_memory_system_for_ai_agents/)は early-stage とし、exact intent match、linear replay のみ、branch なし、tool signature 未追跡、多数 skill 時の cost 未測定を回答している。少数 run の体感時間は一般的な speedup として採用しない。投稿の relative time は検索 index と open で揺れるため、投稿日の厳密値にも依存しない。[固定 README][sf-readme]

**POW に借りるなら:** 成功ログから「どの値は parameter か」「どの値は前 step の出力か」を示す手順候補を作り、一般化できなければ保存しない。自動再生は移さず、source/tool schema と失効条件を添えて読める候補を返す。

### 4. brainbox: 関連の予測と、生産性向上を分ける

固定 commit `2585acb73ad2140dc4f57e5a726b45675f508015`。root [LICENSE][bb-license] は MIT。`compileProcedures` は失敗した Bash→Edit/Write→似た command の passing rerun から error-fix を抽出し、workflow には3–6 step、3 session 以上の裏付けを要求する。session/seq/ts の provenance と incremental high-water mark を持つ。[procedures.ts#L249][bb-procedures]

同 trigger の上限、検索候補数、表示数を絞り、過去の観測として support と helpful/harmful を budget 内で表示する。harmful が helpful+2 を超えると deprecate するが、これは物理削除ではない。policy は注入量を学習し、後で file を開いた/編集したことを reward に、注入量を cost にする。token 数は `ceil(chars/4)` という推計で provider の実測 token ではない。[procedures.ts#L180][bb-feedback]・[procedures.ts#L424][bb-format]・[policy.ts][bb-policy]

作者の [WHITEPAPER §6.2/§7][bb-whitepaper] は、予測の成功と生産性が違うこと、open/edit が helpful の不完全な proxy、poisoned repository でも association/procedure ができること、quoted observation でも真正性は保証できないこと、現 version の長期 DB 成長・latency が未測定であることを記す。旧版の token savings、他 memory への優位、5ms 等の主張も撤回している。README は local edited-file 順位で単純 frequency baseline に負ける結果を隠していない。[README Results][bb-readme]

**POW に借りるなら:** useful/contradicted の根拠 locator と候補数・文字数上限を既存 fact に添える程度。UCB、全 session capture、SQLite graph、embedding は採用しない。file を開いた事実だけで「学習成功」とせず、反証が出た fact は手で差し替える。

### 5. MemFlow: 検索することと指示として信頼することを分ける

固定 commit `b073265df202bdb224e42c5a478dfb6251085e50`。root [LICENSE][mf-license] は Apache-2.0。README 自身が skill retrieval/injection layer と呼び、生成 LLM を既定では必要としない。Qdrant と embedding service を使うが、POW にそれらを導入する必要はない。[README][mf-readme]

`skills.py` は source path、SHA-256、mtime、補助ファイル manifest と governance を記録し、unknown を data、trusted を instruction、blocked を blocked にする。`read_skill_from_store` は exact ID を要求し、blocked を拒否し、完全な stored body と trust_mode を返す。検索に当たっただけで body 全体を有効な命令にしない境界が実装されている。[skills.py#L217][mf-skills]・[mcp_server.py#L43][mf-mcp]

圧縮後は以前読んだ skill の本文を再注入せず ID を newest-first で並べる reminder を作り、8,000 UTF-16 code unit 以内に絞る。current stored skill を読み、instruction/data の区別、完了済み作業の非再実行を維持する。README は reminder を出すことと実際に再読込したことは別、と明記する。[claude_compaction.py][mf-compaction]・[README][mf-readme]

失効については注意が要る。登録は snapshot で source を編集しても sync まで本文は変わらない。`sync_skill` は source hash が変わった時に再読込する一方、**以前の trust_state を新本文へ持ち越す**。source hash は真正性の証明でも、新本文の承認でもない。POW では内容が変わったら evidence/承認を stale にする方が適合する。[manager.py#L245][mf-sync]

作者は SKILL.md 本文だけを保存・提供し付属 scripts/reference の実体は配送しないこと、embedding API 失敗時の hash vector fallback が semantic search でないこと、hook failure は追加文脈なしで続行することを明記する。既存 skill を引く仕組みとして評価すべきで、経験からの能力獲得と呼ばない。[README][mf-readme]

**POW に借りるなら:** task に必要な既読 source/fact の ID と hash を、圧縮・handoff 後に上限付きで再確認する。任意の外部 SKILL.md を instruction に自動昇格しない。source 更新は信頼の継承ではなく再確認の trigger にする。

### 6. MemSkill: 「何を覚えるか」を学ぶ meta-memory

固定 commit `f65b797338033f4f9c34822f1810f9c2747e6022`。root [LICENSE][ms-license] は Apache-2.0。作者は memory skill は経験や task procedure 自体ではなく、何を抽出し、どこに注目し、何を保存・忘却するかという **meta-memory** と明記する。[README][ms-readme]

`PPOController` は state と operation を別の MLP に通し、連結した特徴を actor head で scoring する。`trainer.py` はこの controller の loss を backpropagation し optimizer を更新する。作者は [issue #2 の回答](https://github.com/ViktorAxelsen/MemSkill/issues/2#issuecomment-4075980810)で論文の dot product は説明用に簡略化し、公開実装は concatenation+MLP と説明する。論文の式だけで実装方式を断定しない。[controller.py#L218][ms-controller]・[trainer.py#L994][ms-trainer]

`Designer` は失敗 case を rolling window / 最大数で絞り、既存 skill refinement と新規追加を提案する。適用側は変更数、必要 field、insert/update の種別、空 template 等を確認する。これは型と形式の gate であり、外部由来の間違った内容を意味的に排除する証明ではない。memory item の DELETE と skill bank の evolution は別の操作である。[designer.py#L137][ms-failures]・[designer.py#L1483][ms-designer]・[executor.py#L510][ms-executor]

作者は [issue #3 の回答](https://github.com/ViktorAxelsen/MemSkill/issues/3#issuecomment-4088939432)で dense retrieval は通常の RAG を用い、主眼は retrieval 自体ではないと説明。README は dataset/environment に応じて retraining/tuning が必要になり得ること、within-sample 並列 extraction が quality を悪化させ得ること、主な training cost が downstream query evaluation にあることを明記する。[README][ms-readme]

**POW に借りるなら:** 保存対象の選択規則を分離し、失敗の種類に応じて「何を残すべきか」を一度だけ見直す発想まで。PPO/GPU/training pipeline を POW に入れるのは不適合。継続的な自動呼出しや base-model self-training と混同しない。

## 既調査枠の再確認: cass_memory_system

新規件数に含めない。2026-10-30 API は stars 457、created 2025-12-07、pushed 2026-10-29、archived false、license `NOASSERTION`。固定 commit は `fa4561b06d5cfacb745f72b1aa9e179de13f1ba3`。[API](https://api.github.com/repos/Dicklesworthstone/cass_memory_system)

root [LICENSE][ca-license] は通常の MIT ではなく **MIT with OpenAI/Anthropic Rider**。OpenAI/Anthropic と関連する Restricted Parties の権利を除き、analysis/indexing/benchmark 等も use に含める文言がある。plain MIT と記載せず、コードの採用候補から外す。以下は公開資料の再確認記録で、転載や再実装を行ったものではない。

`scoring.ts` は時間減衰、harmful の重み、少数 feedback の confidence damping、relevance を覆さない bounded multiplier を分ける。`forget.ts` は reason を必須とし、repo/global の所有 scope を検索時と揃え、重複 ID を lock 下で拒否してから blocked log と deprecation を行う。`curate.ts` は deprecated/retired rule を類似候補から強化して復活させない。[scoring.ts][ca-scoring]・[forget.ts][ca-forget]・[curate.ts#L1030][ca-curate]

[issue #89](https://github.com/Dicklesworthstone/cass_memory_system/issues/89)のユーザーは private な31問の factual recall で 0.4.0 が以前の0.2.13を上回らなかったと報告する。小標本・private・procedural guidance とは違う課題である限界も本人が記す。作者は [回答](https://github.com/Dicklesworthstone/cass_memory_system/issues/89#issuecomment-6191982589)で v0.5.0 の context 上限、token budget、feedback を relevance の tie-break に留める変更を説明した。件数増加を品質上昇と取り違えないための実例になる。

長い session の中間に失敗・訂正が埋もれていた [issue #88](https://github.com/Dicklesworthstone/cass_memory_system/issues/88)は、作者が fixed window 由来と認め、[回答](https://github.com/Dicklesworthstone/cass_memory_system/issues/88#issuecomment-5915415469)で予算内 middle error/correction scan と incremental extraction を説明する。後続回答は user-turn header 認識も修正したと記す。未修正の現行 bug として扱わず、負の経験を削る圧縮が学習を歪める設計上の教訓として読む。

## POW に対する小さい独立案

既存 [pow-reference evidence protocol](../../commands/pow-reference/references/evidence.md) は、claim、source/version/locator、適用条件、inspected/compiled/executed、失効 trigger を既に持つ。[update](../../commands/update/SKILL.md) も source hash / HEAD / runtime / platform を freshness に用い、失敗と interrupted を保持し、自動再試行しない。新しい memory platform を別に作る必要はない。

1. **経験→候補を1回で終える。** 依頼された作業の完了時、再利用価値がある fact だけ既存 entry の更新候補にする。観測された最終変更後の成功/失敗、適用範囲、locator を必須にする。自分の final answer は成功証拠にしない。新しい外部推論は既定0回、必要があって明示的に使う場合も1回まで。
2. **反証と撤回を消さない。** active / candidate / stale / revoked を分け、撤回理由と対象 hash を短く残す。単に検索から消すだけでは、再抽出による復活を防げない。root や namespace を混ぜない。一般化できない trace は無理に skill にしない。
3. **使用時に条件を先に確認する。** source/API/schema/関連 file hash、platform、tool capability を見て applicable でなければ出さない。古い成功回数で relevancy や applicability を上書きしない。文字数/token 推計と provider 実測は区別する。
4. **文脈を小さく保つ。** 全 library を prompt に入れず、最大3候補、必要な根拠、失敗・失効警告と locator だけを読む。圧縮や handoff 後は ID/hash の再確認を促す。古い依頼や skill body を新しいユーザー命令として復活させない。

この案はまだ未実装。既存実行結果を使う設計であり、追加 test/fixture/snapshot/benchmark、常駐 service、vector DB、全会話 capture、untrusted skill 自動実行は提案しない。新しい検証を実施する場合も、ユーザーが依頼した実装の既存 entry point を有限 timeout で一度確かめ、成功したら止める。

## 確認範囲

新規15件: metadata と README 選別。新規6件: 上記固定 commit の root LICENSE、README、実装2ファイル以上、作者の issue/thread または限界説明まで確認。既調査1件: metadata/license/変更・issue の再確認。未確認は runtime 再現、長期品質、実 provider token/cost、横断的 benchmark、Windows の実動作。調査で得た候補は採用済み機能ではない。

[sf-readme]: https://github.com/GrappinoRoot/scriptflow/blob/cfa3b8bbf19b43a5a055865a27cec04a96f78701/README.md
[sf-license]: https://github.com/GrappinoRoot/scriptflow/blob/cfa3b8bbf19b43a5a055865a27cec04a96f78701/LICENSE
[sf-compiler]: https://github.com/GrappinoRoot/scriptflow/blob/cfa3b8bbf19b43a5a055865a27cec04a96f78701/src/procedural_memory/compiler.py
[sf-runtime]: https://github.com/GrappinoRoot/scriptflow/blob/cfa3b8bbf19b43a5a055865a27cec04a96f78701/src/procedural_memory/runtime.py
[sf-recorder]: https://github.com/GrappinoRoot/scriptflow/blob/cfa3b8bbf19b43a5a055865a27cec04a96f78701/src/procedural_memory/recorder.py#L43
[sf-verify]: https://github.com/GrappinoRoot/scriptflow/blob/cfa3b8bbf19b43a5a055865a27cec04a96f78701/src/procedural_memory/verify.py
[sf-types]: https://github.com/GrappinoRoot/scriptflow/blob/cfa3b8bbf19b43a5a055865a27cec04a96f78701/src/procedural_memory/types.py#L88
[sf-store]: https://github.com/GrappinoRoot/scriptflow/blob/cfa3b8bbf19b43a5a055865a27cec04a96f78701/src/procedural_memory/store.py#L114
[sf-intent]: https://github.com/GrappinoRoot/scriptflow/blob/cfa3b8bbf19b43a5a055865a27cec04a96f78701/src/procedural_memory/intent.py
[bb-readme]: https://github.com/thebasedcapital/brainbox/blob/2585acb73ad2140dc4f57e5a726b45675f508015/README.md
[bb-license]: https://github.com/thebasedcapital/brainbox/blob/2585acb73ad2140dc4f57e5a726b45675f508015/LICENSE
[bb-procedures]: https://github.com/thebasedcapital/brainbox/blob/2585acb73ad2140dc4f57e5a726b45675f508015/src/procedures.ts#L249
[bb-feedback]: https://github.com/thebasedcapital/brainbox/blob/2585acb73ad2140dc4f57e5a726b45675f508015/src/procedures.ts#L180
[bb-format]: https://github.com/thebasedcapital/brainbox/blob/2585acb73ad2140dc4f57e5a726b45675f508015/src/procedures.ts#L424
[bb-policy]: https://github.com/thebasedcapital/brainbox/blob/2585acb73ad2140dc4f57e5a726b45675f508015/src/policy.ts
[bb-whitepaper]: https://github.com/thebasedcapital/brainbox/blob/2585acb73ad2140dc4f57e5a726b45675f508015/WHITEPAPER.md
[mm-readme]: https://github.com/TheWariend/MuscleMemory/blob/e7f869dbe3bc2a8dd9721cb1a9684f9972bd674a/README.md
[mm-license]: https://github.com/TheWariend/MuscleMemory/blob/e7f869dbe3bc2a8dd9721cb1a9684f9972bd674a/LICENSE
[mm-how]: https://github.com/TheWariend/MuscleMemory/blob/e7f869dbe3bc2a8dd9721cb1a9684f9972bd674a/docs/how-it-works.md
[mm-hooks]: https://github.com/TheWariend/MuscleMemory/blob/e7f869dbe3bc2a8dd9721cb1a9684f9972bd674a/packages/musclememory/client_hooks.py#L954
[mm-files]: https://github.com/TheWariend/MuscleMemory/blob/e7f869dbe3bc2a8dd9721cb1a9684f9972bd674a/packages/musclememory/hook_files.py
[mm-service]: https://github.com/TheWariend/MuscleMemory/blob/e7f869dbe3bc2a8dd9721cb1a9684f9972bd674a/packages/musclememory/service.py#L79
[mm-evaluate]: https://github.com/TheWariend/MuscleMemory/blob/e7f869dbe3bc2a8dd9721cb1a9684f9972bd674a/packages/musclememory/service.py#L1260
[mm-delete]: https://github.com/TheWariend/MuscleMemory/blob/e7f869dbe3bc2a8dd9721cb1a9684f9972bd674a/packages/musclememory/service.py#L1679
[se-readme]: https://github.com/cookieApril/SEPM/blob/fbbed150d1520dc527d42a6415876a944efe83a4/README.md
[se-license]: https://github.com/cookieApril/SEPM/blob/fbbed150d1520dc527d42a6415876a944efe83a4/LICENSE
[se-models]: https://github.com/cookieApril/SEPM/blob/fbbed150d1520dc527d42a6415876a944efe83a4/src/sepm/models.py#L323
[se-trials]: https://github.com/cookieApril/SEPM/blob/fbbed150d1520dc527d42a6415876a944efe83a4/src/sepm/models.py#L391
[se-service]: https://github.com/cookieApril/SEPM/blob/fbbed150d1520dc527d42a6415876a944efe83a4/src/sepm/service.py#L439
[se-reproduction]: https://github.com/cookieApril/SEPM/blob/fbbed150d1520dc527d42a6415876a944efe83a4/src/sepm/service.py#L421
[se-safety]: https://github.com/cookieApril/SEPM/blob/fbbed150d1520dc527d42a6415876a944efe83a4/src/sepm/safety.py
[se-retrieval]: https://github.com/cookieApril/SEPM/blob/fbbed150d1520dc527d42a6415876a944efe83a4/src/sepm/retrieval.py#L67
[mf-readme]: https://github.com/skhynix/MemFlow/blob/b073265df202bdb224e42c5a478dfb6251085e50/README.md
[mf-license]: https://github.com/skhynix/MemFlow/blob/b073265df202bdb224e42c5a478dfb6251085e50/LICENSE
[mf-skills]: https://github.com/skhynix/MemFlow/blob/b073265df202bdb224e42c5a478dfb6251085e50/memflow/skills.py#L217
[mf-mcp]: https://github.com/skhynix/MemFlow/blob/b073265df202bdb224e42c5a478dfb6251085e50/memflow/mcp_server.py#L43
[mf-compaction]: https://github.com/skhynix/MemFlow/blob/b073265df202bdb224e42c5a478dfb6251085e50/memflow/claude_compaction.py
[mf-sync]: https://github.com/skhynix/MemFlow/blob/b073265df202bdb224e42c5a478dfb6251085e50/memflow/manager.py#L245
[ms-readme]: https://github.com/ViktorAxelsen/MemSkill/blob/f65b797338033f4f9c34822f1810f9c2747e6022/README.md
[ms-license]: https://github.com/ViktorAxelsen/MemSkill/blob/f65b797338033f4f9c34822f1810f9c2747e6022/LICENSE
[ms-controller]: https://github.com/ViktorAxelsen/MemSkill/blob/f65b797338033f4f9c34822f1810f9c2747e6022/src/controller.py#L218
[ms-trainer]: https://github.com/ViktorAxelsen/MemSkill/blob/f65b797338033f4f9c34822f1810f9c2747e6022/src/trainer.py#L994
[ms-failures]: https://github.com/ViktorAxelsen/MemSkill/blob/f65b797338033f4f9c34822f1810f9c2747e6022/src/designer.py#L137
[ms-designer]: https://github.com/ViktorAxelsen/MemSkill/blob/f65b797338033f4f9c34822f1810f9c2747e6022/src/designer.py#L1483
[ms-executor]: https://github.com/ViktorAxelsen/MemSkill/blob/f65b797338033f4f9c34822f1810f9c2747e6022/src/executor.py#L510
[ca-license]: https://github.com/Dicklesworthstone/cass_memory_system/blob/fa4561b06d5cfacb745f72b1aa9e179de13f1ba3/LICENSE
[ca-scoring]: https://github.com/Dicklesworthstone/cass_memory_system/blob/fa4561b06d5cfacb745f72b1aa9e179de13f1ba3/src/scoring.ts
[ca-forget]: https://github.com/Dicklesworthstone/cass_memory_system/blob/fa4561b06d5cfacb745f72b1aa9e179de13f1ba3/src/commands/forget.ts
[ca-curate]: https://github.com/Dicklesworthstone/cass_memory_system/blob/fa4561b06d5cfacb745f72b1aa9e179de13f1ba3/src/curate.ts#L1030
