# RTKとHeadroomの導入・使い分け

## 役割を分ける

| 手段 | 主な用途 | 別途確認すること |
| --- | --- | --- |
| RTK | 対応するシェルコマンドの冗長な出力を減らす | 終了コード、失敗ログの回復、対応コマンド |
| Headroom | 大きく反復の多いJSON・ログ等を、原文を保持して圧縮する | 圧縮前後、重要項目、原文復元、処理と起動の費用 |
| cxd | 短い入口、依存関係付きコマンド実行、索引・ワーカー再利用 | 実行とモデル往復の測定境界 |

RTKとHeadroomを全出力へ無条件に二重適用しない。短い出力、既に密なRTK出力、正確なソースや計測JSONをさらに圧縮すると、費用だけ増えたり検証が難しくなったりする。必要な原文は保持する。

モデルが既に読んだ長い出力を、モデルにもう一度ツール引数へ書かせて圧縮しても、入力・生成費用を増やす。効果を出すには、ツール実行側・アプリ側で圧縮し、モデルへ渡すのは圧縮結果だけにする。原文は必要時に取得する。

`functions.exec`等で複数ツールを連携できる環境では、実行結果をランタイムの変数に保持し、そのままHeadroomへ渡して、最後に圧縮結果だけを表示する。実在するツール名・スキーマを確認し、原文を途中でモデルへ出力しない。この連携がない環境では、MCPを登録しただけで全出力が自動圧縮されるわけではない。

## Headroomの固定バージョンと依存関係

2026-10-19の導入確認では公式PyPIの `headroom-ai[mcp]==0.41.0` を使用した。ライセンスはApache-2.0。Python 3.10以降に対応し、検証にはPython 3.12を使った。[公式リリース](https://github.com/headroomlabs-ai/headroom/releases/tag/v0.41.0)にWindows/Linux用wheelがある。

Windows wheel `headroom_ai-0.41.0-cp310-abi3-win_amd64.whl` のSHA-256をPyPIメタデータと照合した:

```text
18b43230c4dbbe9889fdb0863a7943059f4509fdf49ad20b19be394f2725db18
```

`[mcp]` でも今回のWindows環境では推移依存を含め79パッケージになった。軽量な標準ライブラリだけのcxdとは分離する。`[all]`、MLモデル、プロキシ用extrasを一括で入れない。導入時点の実際の解決結果を確認し、専用環境へインストールする。これは依存全体の脆弱性監査済みという意味ではない。

## 明示的なインストール

uvがある環境では、Windows/Linuxとも次の形で独立したツール環境に導入できる。

```sh
uv tool install --python 3.12 "headroom-ai[mcp]==0.41.0"
headroom --help
```

既存uvツールと競合する場合に強制上書きしない。uvがなければ、OSに応じて専用venvを作って、そのPythonのpipから同じ固定パッケージを入れる。Windowsの実行ファイルは通常 `Scripts/headroom.exe`、Linuxは `bin/headroom`。CodexからPATHを解決できない場合は、その絶対パスを登録する。

POW自体はHeadroomを自動ダウンロード・インストールしない。cxdの標準ライブラリのみの構成も維持する。

## Codexにはstdio MCPだけを追加する

CodexのChatGPT認証・モデル・API接続先を保つ方式。次はPATH上にheadroomがある場合の例。サーバー名が既にある場合は、先に既存設定を確認し、別実装を上書きしない。

```sh
codex mcp add headroom \
  --env HEADROOM_OFFLINE=1 \
  --env HEADROOM_BEACON=off \
  --env HEADROOM_TELEMETRY=off \
  --env DO_NOT_TRACK=1 \
  --env HF_HUB_OFFLINE=1 \
  --env TRANSFORMERS_OFFLINE=1 \
  --env HEADROOM_MCP_READ=off \
  --env HEADROOM_OUTPUT_SHAPER=0 \
  --env LITELLM_LOCAL_MODEL_COST_MAP=True \
  --env LITELLM_TELEMETRY=False \
  -- headroom mcp serve
```

上記はsh系シェル用。PowerShellでは1行で実行するか、バックスラッシュではなくPowerShellの行継続を使う。`HEADROOM_WORKSPACE_DIR` を専用の状態保存先へ設定すれば、原文キャッシュ等の配置も分離できる。

登録前に設定をバックアップし、登録後は新しいHeadroom表以外の意味が変わっていないか比較する。CLIのバージョン差による他のMCP設定の正規化も、無関係な変更として検出する。新しいチャットやMCP再読み込み後に、次のツールの接続を確認する。

- `headroom_compress`: 受け取った内容をローカルで圧縮し、原文取得用hashを返す。
- `headroom_retrieve`: hashから元の内容を取得する。
- `headroom_stats`: 統計を確認する。

0.41.0のMCP原文キャッシュは既定1時間。hashだけを長期保存すれば永久に復元できるわけではない。長期的に必要なログや検証原文は別途保持する。

`headroom_read` は既定で無効のままにする。この版にはワークスペース境界・サイズ上限等の設定がなく、初回は原文を返すため、任意ファイルの読み取りを追加する理由にはならない。

`headroom wrap codex` はモデル接続経路をプロキシへ変更する別方式。現在のDesktop通信を自動圧縮するための単なるMCP登録と混同しない。モデルのeffort等を変更するoutput shaperも、速度だけを目的に有効化しない。

## オフライン動作とトークナイザーの初回費用

Headroomの匿名beaconは明示的にoffにする。上記オフライン設定では圧縮のために本文を外部へ送らず、MLモデルの自動取得も行わない。ローカルの原文キャッシュは機密データになりうるため、Gitや公開ログへ追加しない。

初回、tiktokenの辞書がないと取得待ち・推定へのフォールバックが起こりうる。必要ならインストール段階で公式辞書を取得し、tiktokenが期待するハッシュを照合した専用 `TIKTOKEN_CACHE_DIR` を設定する。辞書はLLMのモデル重みとは別。

取得できない環境では `HEADROOM_TIKTOKEN_LOAD_TIMEOUT_SECONDS` を短い上限に設定できるが、その場合の計数は推定となりうる。タイムアウトを短くした結果を、正確なプロバイダー請求トークンと説明しない。MCPはローカルプロキシの稼働確認も行うため、プロキシなしの圧縮・取得にはその確認費用も含まれうる。

## ローカルライブラリでモデルへ渡す前に圧縮する

Pythonアプリ側で連携する場合は、例えば次のようにモデル呼び出しの直前で結果を置き換える。自分のアプリが取得したデータを直接渡し、モデルに原文を再生成させない。

```python
from headroom import compress

def compress_tool_output(content):
    result = compress(
        [{"role": "tool", "content": content}],
        model="gpt-4o",
        mode="agent",
        protect_recent=0,
        kompress_model="disabled",
    )
    return result.messages[0]["content"]
```

`model` はここでは計数等に使う識別子で、LLMへの要求ではない。agentモードは構造的な圧縮とlossless検証を選び、ML圧縮を無効にする。MCPの既定モードとは別の設定であり、同じ出力や圧縮率になるとは限らない。原文の保持・回復や、圧縮結果の形式をアプリ側でも扱う。

## 0.41.0での検証結果

Windowsの独立環境で、同じサービスの正常レコード500件中1件だけを固有のエラーに変えた合成JSONを使った。公式 `headroom.exe mcp serve` に実際のstdio MCPクライアントから接続し、圧縮・原文取得を実行した。

| 項目 | 観測値 |
| --- | --- |
| 圧縮前のHeadroom計数 | 16,512トークン |
| 圧縮後のHeadroom計数 | 6,526トークン |
| 内容部分の削減率 | 60.5% |
| 圧縮と原文取得の合計 | 3.414秒 |
| 固有エラーの保持 | 確認済み |
| 取得原文と入力の完全一致 | 確認済み |

これは辞書キャッシュ後の1例で、MCP初期化は時間に含めていない。MCP応答全体のJSON包絡、入力側に既にある原文、API請求、回答品質、タスク全体の高速化率を測った値ではない。異なる内容・モードの結果を混ぜない。

HeadroomのLinux向けwheelと導入手順は公式配布に基づく。今回のHeadroom実行確認はWindowsのみであり、cxdのWindows/Linux両方のCI成功と混同しない。短いタスクでも常に必須とするのではなく、起動・圧縮・取得を含めて得になる場面で使う。

## 解除

Codex側の登録だけを外す場合は `codex mcp remove headroom`。uvツール方式なら `uv tool uninstall headroom-ai`。専用venv方式なら、その環境を対象とした削除を行う。状態ディレクトリの原文キャッシュは別なので、必要なログ・データを確認した上で明示的に扱う。RTKや他のMCP設定を巻き込まない。

一次資料: [Headroom v0.41.0](https://github.com/headroomlabs-ai/headroom/tree/v0.41.0)、[PyPI](https://pypi.org/project/headroom-ai/0.41.0/)、[RTK](https://github.com/rtk-ai/rtk)。配布バイナリや依存パッケージ自体はPOWへ再配布しない。
