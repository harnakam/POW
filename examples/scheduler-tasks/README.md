# 実Tool計測用の3プロジェクト

ジャンケン8件、迷路7件、永続化するTODO4件の実テストを同梱する。2026-10-27のTool計測に使った6ファイルと内容ハッシュが一致する。測定データと範囲は `commands/optimize-latency/references/measurements-2026-10-27.md` を参照。

POWルートから実行する（Linuxは `python3`）。

```sh
python -B commands/optimize-latency/scripts/cxd/dispatch.py --workspace examples/scheduler-tasks plan verify-all
python -B commands/optimize-latency/scripts/cxd/dispatch.py --workspace examples/scheduler-tasks verify-all --concurrency 3
```

19件の成功を毎回実行して確認する。テスト結果はキャッシュしない。`estimated_s` は優先順位の例で、実際の実行時間の予測や保証ではない。
