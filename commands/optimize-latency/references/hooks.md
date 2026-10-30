# Hookごとの同期・非同期と最適化

既存cxdの実行器、永続ジョブ、待機通知、依存関係、リソース競合の処理を再利用する。Python 3.10+、標準ライブラリのみ。別の実行エンジンや常駐サービスは追加しない。

## 設定

対象の`.codex-dispatch.json`へ確認済みpresetを参照する`hooks`を追加する。既存設定を保持し、ファイル名を対象に合わせる。

```json
{
  "version": 1,
  "source_roots": ["."],
  "hooksConcurrency": 2,
  "presets": {
    "build-local": {"jobs": [{"id":"build","argv":["node","scripts/build.mjs"],"timeout_s":60,"reads":["source"],"writes":["dist"]}]},
    "index-local": {"jobs": [{"id":"index","argv":["{python}","-B","scripts/index.py"],"timeout_s":20,"reads":["source"],"writes":["index"]}]}
  },
  "hooks": [
    {"id":"build","event":"beforeComplete","preset":"build-local","mode":"sync","onFailure":"block","inputs":["scripts/build.mjs"]},
    {"id":"index","event":"afterChange","preset":"index-local","mode":"async","onFailure":"block","requiredAt":["beforeComplete"],"independent":true,"inputs":["scripts/index.py"]}
  ]
}
```

- `mode:sync`は結果と実行器の終了を待つ。`async`は永続ジョブIDを返し、起動成功を処理成功と扱わない。
- `onFailure:block`は失敗で後続を止める。非同期なら`requiredAt`が必須。`record`は失敗を記録して続行する。
- `requiredAt`は結果が必要な後続イベント。`emit beforeComplete`も最初に該当hookを待つ。`join beforeComplete`は待機だけを行う。未実行・古い結果・期限超過は完了を拒否する。起動イベント自身は指定できない。
- `independent:true`は他の作業と重ねられるという利用者の宣言。最適化提案に使うが自動で非同期化しない。
- `inputs`は鮮度を束縛する実在ファイルの相対パス。各8 MiB以下、最大64個。必要なソース・設定・スクリプトを含める。省略した依存や外部データの変更は検知できない。検証成功のキャッシュではない。
- `inputRoots`は追加・削除も監視する相対ディレクトリ、最大8個。Git・依存・生成物・状態を除外し、2000ファイル・総32 MiB・各2 MiBが上限。範囲を超えた場合はエラーにして入力範囲を見直す。
- 同じ`reads`/`writes`キーを共有するpresetは別hook・別cycleでも競合を検出する。意味上のキーであり自動のアクセス検出ではない。preset内依存には`depends_on`を使う。

最大32hook、presetあたり32ジョブ。argvコマンドのみ、各`timeout_s`は300秒以下。preset内はconcurrency 1、hook間は`hooksConcurrency:1..8`で制限する。容量不足・競合はbusyで拒否し、無制限の待ち行列や自動再試行を作らない。

## 呼び出し

```text
cxd hooks plan --workspace <repo>
cxd hooks emit afterChange --workspace <repo> --cycle <task-id>
cxd hooks emit beforeComplete --workspace <repo> --cycle <same-task-id>
cxd hooks join beforeComplete --workspace <repo> --cycle <same-task-id>
cxd hooks status --workspace <repo>
cxd hooks profile --workspace <repo>
```

`cxd --workspace <repo> hooks ...`の順も使える。クローンでは`node scripts/pow.mjs /hooks ...`、Skill単体では`python -B <skill>/scripts/cxd/dispatch.py hooks ...`。Linuxでは`python3`を使う。Node入口はWindowsの`python`、その他の`python3`が既定で、`POW_PYTHON`で実行ファイルを指定できる。

新しい作業には新しいcycle IDを使い、発火から完了判定まで同じIDを渡す。実行中の同じhook・入力・cycleの再発火は既存ジョブへ合流する。終了後の再発火は新規実行になるため成功した検証を反復しない。異なるcycleや入力の同じhookが実行中なら拒否する。設定や宣言した入力の変更で既存cycleは失効し、必須hookを削除して以前のcycleを通過させられない。実行中の結果を調べ、新cycleで必要な処理を実行する。

`--timeout 0..60`は呼び出し側の待機上限。ジョブ自体のtimeoutとは別で、期限超過はexit 2、ジョブは設定済み上限まで継続する。configや入力が壊れても`status`は保存済みジョブを表示する。詳細は`cxd result ID`、待機は`cxd wait ID --timeout 60`。保存したPIDだけを根拠に別プロセスを強制終了する機能は追加しない。

hook内のemitは継承する環境マーカーで拒否する。意図しない再帰の防止でありコードの隔離ではない。明示的なemitに加え、[native統合](native-hooks.md)を登録するとCodexイベントから自動発火できる。Skillを入れるだけで自動登録することはない。native adapterの`--resume`は同じcycle・同じ入力に記録された実行を合流し、ターン内の完了確認で重複実行を避ける。通常のemitは既定で終了済み処理を再利用しない。

## 最適化と保存

`profile`は同じhook設定・argv入口の内容・platform・Python版の記録から、実行器の経過時間p50/p95、呼び出し側の累積待機、失敗、重複起動抑止を表示する。入力内容の異なる件数も表示し、普通の編集で計測を蓄積できる。鮮度は別の入力fingerprintで制御し、過去の成功を新しい入力の検証へ流用しない。異なる入力の費用は同一とは限らない。起動・待機通知もあるため、合計や推定の高速化率にはしない。

通常利用の比較可能な記録が3件未満なら不足を表示する。失敗時は原因調査を優先し、問題がなく`independent:true`の同期hookに非同期化候補を出す。blocking hookに合流点が未指定なら追加の選択が必要と表示する。timeout候補は成功したジョブ別時間が3件以上ある場合だけ、観測最大時間の2倍+1秒を1..300秒に収めた値を出す。preset全体時間は使わない。負荷や未観測条件を保証する値ではない。提案は自動適用せず、合流点・失敗制御・競合を確認して更新する。サンプル数のためだけに検証を繰り返さない。

emit/joinは状態更新を直列化し、同期待機中も最大60秒ロックを保持する。他の書き込み要求はbusyで拒否されるが、statusはatomicな保存済み状態を読み、待機中も参照できる。複数呼び出し元を同時に待機させる仕組みではない。

状態は`.cxd/hooks/`、ログは従来の`.cxd/async/`。最大200cycle・200件の終了記録と全実行中ジョブを保持し、古い非実行cycleのメタデータから失効させる。ログの自動削除は行わない。残ったロックはPIDと子プロセスを調べてから明示的に復旧する。

## 2026-10-30の直接実行

使い捨て作業場所で関数索引を非同期生成し、再発火が同じジョブIDへ合流した。beforeCompleteで待ち合わせ、同期構文確認が成功し、symbols.jsonに実関数名greetingが出た。索引の実行器時間は約3.27秒、合流待機は約2.36秒。構文確認は実行器約0.23秒に対し呼び出し待機約1.83秒で、起動・終了確認の費用も観測できた。exit 7の同期hookは後続を拒否しexit 2を返した。入力の削除中にもstatusが動き、入力変更時の古いcycleと再帰emitは拒否された。6-module版の所有receiptから7-module版への実インストール更新も成功した。機能の実証であり、全体の高速化率を示す比較ではない。3件以上の通常利用を前提とする候補生成は、この単一シナリオで一般的な有効性まで実証したものではない。
