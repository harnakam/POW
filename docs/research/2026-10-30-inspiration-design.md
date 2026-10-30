# UI設計・視覚検証から design-reasoning へ取り込む案

調査日: 2026-10-30。GitHub connectorで公式9 repoのAPI・固定実装・ライセンスを確認。応用案の効果は未測定。実装・導入・テスト追加なし。

現行契約を確認。CDP撮影・hash結合の独立レビュー・5軸・有限回数は既存機能。先行研究のImpeccable・Taste Skill・Design Harnessは再調査しない。

## 対象と現況

星数は取得時点。pushはUTC、全件未archive。Headless UIは4月以降pushなし。正規APIとルート `LICENSE`（shadcnは `LICENSE.md`）本文を照合。人気・pushは品質の証明ではない。

| 正規repo・一次API | stars | 最終push | license |
| --- | ---: | --- | --- |
| [microsoft/playwright](https://api.github.com/repos/microsoft/playwright) | 98,837 | 2026-10-30 | Apache-2.0 |
| [storybookjs/storybook](https://api.github.com/repos/storybookjs/storybook) | 91,407 | 2026-10-30 | MIT |
| [dequelabs/axe-core](https://api.github.com/repos/dequelabs/axe-core) | 7,730 | 2026-10-29 | MPL-2.0 |
| [radix-ui/primitives](https://api.github.com/repos/radix-ui/primitives) | 19,442 | 2026-10-14 | MIT |
| [adobe/react-spectrum](https://api.github.com/repos/adobe/react-spectrum) | 15,997 | 2026-10-29 | Apache-2.0 |
| [shadcn-ui/ui](https://api.github.com/repos/shadcn-ui/ui) | 126,919 | 2026-10-29 | MIT |
| [tailwindlabs/headlessui](https://api.github.com/repos/tailwindlabs/headlessui) | 28,806 | 2026-04-13 | MIT |
| [floating-ui/floating-ui](https://api.github.com/repos/floating-ui/floating-ui) | 32,783 | 2026-10-27 | MIT |
| [carbon-design-system/carbon](https://api.github.com/repos/carbon-design-system/carbon) | 9,591 | 2026-10-30 | Apache-2.0 |

## 固定ソースの仕組みと20案

次の12実装は40桁SHA固定。各案は既存ブラウザの直接操作・記録へ落とし込み、テストスイートを増やさない。

| 実装で確認した仕組み | POWへの具体案 |
| --- | --- |
| Playwright: [`packages/playwright-core/src/server/screenshotter.ts`][pw]。fonts待機、caret非表示、有限animationのfinish、無限animationのcancel・復元。 | **1. 撮影準備条件**を主領域表示・データ反映・fonts.ready等で指定。固定sleep依存を減らす。**2. 比較条件**にブラウザ版・DPR・フォント・fullPage方式を残す。**3. 正規化範囲**を記録。caret・時刻の除外で意味や動作まで合格にせず、意味を変えるデータ凍結を標準化しない。 |
| Storybook: [`code/core/src/preview-api/modules/preview-web/render/StoryRender.ts`][sb] はload/render/play/completeとAbortSignalを分離。[`animation-utils.ts`][sba] は有限animationを最大5秒待つ。scroll/view timelineは対象外。 | **4. 意味のある状態名**と到達操作を撮影単位にする。例:「保存エラー後・入力保持」。**5. 中断した古い描画**を新候補へ登録しない。**6. motion待機**は完了条件・上限を持ち、打切りは未確認。安定画用停止と通常motionの動作確認を分ける。 |
| axe-core: [`lib/core/constants.js`][ax] は `passes / violations / incomplete / inapplicable` を別群にする。 | **7. 未判定・対象外**をpassへ潰さない。**8. スクロールでの到達**を実操作し、不可視として検査から落ちた可能性を残す。導入済みaxeだけ利用し、導入を必須にしない。 |
| Radix: [`packages/react/focus-scope/src/focus-scope.tsx`][rx] はfocusin/out、DOM除去、Tab周回、遅延unmount autofocus、scope stackを扱う。 | **9. close→focus復元→再起動**まで観測。画像上の消失で終えない。**10. 背面の主操作**を再実行し、透明overlay・pointer制限の残留を検出。 |
| React Aria: [`packages/react-aria/src/focus/FocusScope.tsx`][ra] はcontain/restoreと消えた復元先を扱う。[`useFocusVisible.ts`][ram] はkeyboard/pointer/virtualを区別。 | **11. focus可視性**をクリックとTabで別に観察。**12. 復元先が消える削除・遷移**では次の論理的操作先をbriefに指定し、bodyへの復帰だけを成功にしない。 |
| shadcn: [`apps/v4/registry/new-york-v4/ui/alert-dialog.tsx`][sh] はtitle/description/action/cancelのslot、幅制約、footer逆順・breakpoint配置を持つ。 | **13. 構造制約**を「対象・結果の説明→主操作・取消」の関係で定義。**14. 長文・狭幅**で説明と操作の近さ、DOM順と視覚順、ボタン折返しを確認。 |
| Headless UI: [`dialog.tsx`][hu] はclosing/open、背景inert、scroll lock、Escape、top layer、portalを区別。 | **15. modalと背景**の関係を記録。open中は背景操作不可、close後はscroll・操作復帰。必要な入れ子・Escape・touch条件を選び、幅を入力方式の代用にしない。 |
| Floating UI: [`autoUpdate.ts`][fl] はscroll/resize/layout shiftを監視して解除関数を返す。常時RAFは既定で無効。 | **16. popupと起点の関係**をscroll・折返し・resize後も確認し、主操作の被覆を検出。**17. 一時観測**に限定し、不要な常時RAF・全DOM監視を増やさず、閉鎖後の解除も確認。 |
| Carbon: [`packages/grid/scss/_breakpoint.scss`][cb] はup/down/betweenと境界の丸め対策。[`theme.tokens.json`][ct] はbackground/layer/textを役割・状態で定義。 | **18. responsive境界**は既存CSSの重要な切替幅の直前・直後だけ追加観察。**19. ブランド保持**は色の役割・書体・密度・強調を対応付け、lintと視覚判断を分離。**20. before/after**は内容・scroll・focus・ランドマークを揃え、折返し削減等の改善を説明。意図した移動を画素差だけで退行にしない。 |

## 一次issue/PRに残る失敗条件

過去の実例であり、最新版での再現は今回未検証。

- **フォント待機の限界。** [Playwright #29968](https://github.com/microsoft/playwright/issues/29968) はv1.42.1のfullPage撮影で別フォントになる報告。[maintainer調査](https://github.com/microsoft/playwright/issues/29968#issuecomment-2007893526)は撮影とChromiumのfont updateの干渉を指摘。内部原因は推定を含む。2026-05-12 not_plannedでclosed。案1–3の条件記録が必要。
- **0 violationsの限界。** [axe-core #3883](https://github.com/dequelabs/axe-core/issues/3883) は外側overflow:hidden・中間overflow:autoで画面外要素を不可視とするfalse negative。[maintainer確認済](https://github.com/dequelabs/axe-core/issues/3883#issuecomment-1401154864)、調査時open。案7–8で未評価の可能性を残す。言及された修正PRの取り込みは未確認。
- **close≠unmount。** [Radix #419](https://github.com/radix-ui/primitives/issues/419)・[merged PR #422](https://github.com/radix-ui/primitives/pull/422) は終了animation中のunmount遅延で復元focusをtrapする問題。2021-02-03に `trapped={context.open}` 等へ修正。[#1241](https://github.com/radix-ui/primitives/issues/1241) はmobile emulationでclose後にpointer-events:noneが残る報告。案9・10・15では復旧まで直接確認し、closedを現在版の解決保証にしない。

## 優先する5件と採用しないもの

1. **案4・20: 比較の意味。** 既存HTML比較へ状態・ランドマークの対応と改善理由を足す。
2. **案1・2・6: 撮影条件。** CDPへ待機・環境記録を最小限追加。timeoutは成功にしない。
3. **案9・10・15: dialog復旧。** close後の一操作を足す。native browserのfocus・scroll・pointer lifecycleを画像で代用しない。
4. **案16・18: 関係と境界。** 関係するpopup・breakpointだけ選び、全解像度snapshotにしない。
5. **案7・19: 検査の権限。** DOM事実・未判定とブランド・視覚階層の判断を分け、独立レビューを置換しない。

新規Playwright/Storybook/Chromatic・SaaS・画像diff依存・snapshot・テスト・fixture・harnessは採らない。外観・寸法の移植、コード・素材の転載なし。

確認済: 9 repo・12 SHA固定実装・3失敗群。未確認: 実行効果・各不具合の最新修正状況。将来の実装確認もcompile/buildか直接実行のみ、新規テストコードなし。

[pw]: https://github.com/microsoft/playwright/blob/018adb570c757898e7035f23e29ebb689d1d6ead/packages/playwright-core/src/server/screenshotter.ts
[sb]: https://github.com/storybookjs/storybook/blob/b007bb4cc5da68feba837c2c5956c36ad09339df/code/core/src/preview-api/modules/preview-web/render/StoryRender.ts
[sba]: https://github.com/storybookjs/storybook/blob/b007bb4cc5da68feba837c2c5956c36ad09339df/code/core/src/preview-api/modules/preview-web/render/animation-utils.ts
[ax]: https://github.com/dequelabs/axe-core/blob/6b52b841461bd23345970b91ec75fdaff6bad31a/lib/core/constants.js
[rx]: https://github.com/radix-ui/primitives/blob/eb3a2b7091293e27df8f9ba906632d8daa3d81a3/packages/react/focus-scope/src/focus-scope.tsx
[ra]: https://github.com/adobe/react-spectrum/blob/a562b335e645c172ec5a940b3e47ccdadbeeaa15/packages/react-aria/src/focus/FocusScope.tsx
[ram]: https://github.com/adobe/react-spectrum/blob/a562b335e645c172ec5a940b3e47ccdadbeeaa15/packages/react-aria/src/interactions/useFocusVisible.ts
[sh]: https://github.com/shadcn-ui/ui/blob/96da9cc7f1aa10580a3741664e2a77c721206c00/apps/v4/registry/new-york-v4/ui/alert-dialog.tsx
[hu]: https://github.com/tailwindlabs/headlessui/blob/eea57cf46fd6767ed1059012f7073b88eb159fba/packages/@headlessui-react/src/components/dialog/dialog.tsx
[fl]: https://github.com/floating-ui/floating-ui/blob/93ea014e0344ec0169e9a03db8aee70e90fd5a09/packages/dom/src/autoUpdate.ts
[cb]: https://github.com/carbon-design-system/carbon/blob/03dfc3ae5d933d2d00cd583c175b7b27b3d6dfb0/packages/grid/scss/_breakpoint.scss
[ct]: https://github.com/carbon-design-system/carbon/blob/03dfc3ae5d933d2d00cd583c175b7b27b3d6dfb0/packages/themes/tokens/themes/white/theme.tokens.json
