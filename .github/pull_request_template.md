<!--
  PR template — 結構性觸發 Checkpoint 1（#68）+ Test-First（#69）+ 外部觸發（#72）
  不是行政負擔、是補強「沒便利路徑、容易跳過」的工作。
  純文件 / typo / config 改動可刪掉內容、留 summary。
-->

## Summary

<!-- 1-3 句：這個 PR 解決什麼問題、用什麼方法 -->

## Checkpoint 1：使用者意圖完整集合（#68）

<!--
  [#68 verification-timeline-checkpoints] Checkpoint 1 容易跳是因為沒便利路徑。
  這份 PR template 是 L3 工具觸發。
  列「使用者會經歷的 case 完整集合」、不是回顧式而是 prospective。
-->

- [ ] Happy path 列了
- [ ] 邊界 case：空 / 滿 / 一筆 / 大量 / 特殊字元
- [ ] 失敗 case：網路錯 / 權限錯 / 資料錯 / race condition
- [ ] 規模 case：10 vs 1萬 vs 10 萬 行為差異
- [ ] URL state（[#70]）：分享 / reload / back-forward 該保留什麼
- [ ] A11y（[#71]）：tab order / focus / aria-live / 鍵盤導航
- [ ] 跨情境互動：跟既有 feature 的組合行為

詳列：

<!-- 把上面 prompt 出的 case 寫下來、不只是打勾 -->

## Test-First (#69) 自檢

<!--
  測試該 catch 的東西、必須在 buggy / pre-fix code 上看過 RED 才信任。
-->

- [ ] 新測試在「壞掉的版本」上跑過 → RED ✓
- [ ] 修完跑 → GREEN ✓
- [ ] 或：retrospective 用 `make verify-red-green PRE_FIX=<sha>` 驗證
- [ ] 或：純 refactor、不需要 RED（請說明）

## 跟既有 cards 的關係（選填）

<!--
  本 PR 解決的問題、是否對應 content/report/ 既有卡片？
  發現新原則、有沒有新卡需要寫？
-->

## Risks / Known limitations

<!-- 有 silent 限制要明示（[#66]）。不要 ship 之後才補 -->

---

<details>
<summary>Skip checklist（純 docs / typo / config 改動）</summary>

<!--
  Test-First 跟 Checkpoint 1 不適用所有 PR：
  - 純 typo / 文件改動 → skip
  - Config / build 改動沒 testable behavior → skip
  - Pure refactor（沒 behavior 變更）→ Test-First skip RED、其他保留

  其他都該走完整流程。
-->

</details>
