# Self-aware limitation 模式

> **角色**：本卡是 `migration-playbook-methodology` 的支撐型原則、被 [SKILL.md](../../SKILL.md) Self-aware limitation 段引用。
>
> **何時讀**：第 2-3 輪 4-reviewer audit 後、Reviewer D 揭露 *結構性質疑*（不只是 typo / 規範違規）時。

## 核心原則

Reviewer D 通常揭露 *結構性質疑*（分類不窮盡 / 框架邊界含糊 / 互斥失效）。處理選 *meta-acknowledgment*（記錄）而非 *substantive restructure*（重寫）；除非已累積足夠 sample 支撐重寫。

兩個對立路徑：

| 路徑                         | 內容                                          | 適用                                       |
| ---------------------------- | --------------------------------------------- | ------------------------------------------ |
| Phase 3a meta-acknowledgment | 在卡內加 Self-aware limitation 段、列 limitation + tripwire | sample 不足以重寫、保留 framework 用、誠實標 limitation |
| Phase 3b substantive restructure | 跑既有內容 retroactive audit、重審 type / axis、改寫 framework | sample 充足（≥ 10 同類）、重寫成本 < 修補成本 |

## 為什麼 default 選 Phase 3a

30 篇 migration playbook 過 4 輪 4-reviewer audit、Reviewer D 每輪都揭露 *結構性質疑*：

| 輪次   | Reviewer D 揭露                                             | 選擇路徑                          |
| ------ | ----------------------------------------------------------- | --------------------------------- |
| 第 1 輪 | N=5 sample over-fit 5 type / 5 type 互斥失效                 | Phase 3a                          |
| 第 2 輪 | 6 維仍漏類 / Type F 跟 Type B 重疊 / 拒絕理由依賴 narrow 定義 | Phase 3a                          |
| 第 3 輪 | 工作量 % 是 post-hoc / 3 軸 overlap / Type F 應拆 3 sub-type | Phase 3a                          |
| 第 4 輪 (meta-audit on skill) | Multi-element collapse skill 自陷 / limitation 30+ 條 / 跟 case-first 重疊 / Phase 3a/3b binary 太嚴 | Phase 3a (partial)、含 multi-element 補卡 |

4 輪都 *主要* 選 Phase 3a 的理由：

1. **Reviewer D 揭露的結構性質疑深度 ≥ 當前 sample 重寫的依據**：第 1 輪 N=5 樣本不足以 commit 重寫 5 type、第 3 輪 N=15 仍不足以 commit 重寫 6 type
2. **重寫成本 > 修補成本**：每輪 audit 後重寫 framework 會 invalidate 既有 dogfood、循環往復
3. **Phase 3a 是 documentation 不是 capitulation**：在卡內承認 limitation 比 *假裝完美* 更接近真實狀態、未來新 reader 看到 limitation 段就知道風險邊界
4. **跟「Stage 0 variant 規劃」spirit 一致**：方法論本身也是 batch 寫作、需要 self-aware

## Phase 3a 範本

加在卡末「Self-aware limitation」段：

```markdown
## Self-aware limitation：本卡的 N 個未解結構性質疑

第 X 輪 4-reviewer audit 揭露 N 項結構性 issue、本卡選擇 *meta-acknowledgment* 而非 *substantive restructure*：

1. **<Issue 1 標題>**：<reviewer 揭露的問題、保留原意、不修飾> — 本卡 *<保留現狀 / 加註例外 / 待累積樣本 / 改寫修法>*；理由：<樣本不足 / 邊界模糊 / 影響面廣>
2. **<Issue 2 標題>**：<同上>
...

下一輪 batch trigger：

- 寫 X-Y 篇 <type / axis> dogfood 驗證 <claim>
- 若浮現 <條件>、考慮 <restructure 動作>
- 若浮現 <條件>、再 <擴 axis / 拆 type / 增 layer>
- 既有 N 篇 retroactive audit 在累積到 M+ <unit> 後做、單獨成 retrospective report
```

## 何時切到 Phase 3b

下列訊號累積時、考慮 Phase 3b：

| 訊號                                                       | 累積 trigger                            |
| ---------------------------------------------------------- | --------------------------------------- |
| 同 limitation 在連續 N 輪 audit 都揭露、未隨 dogfood 解決  | 3 輪以上                                |
| Reader 端 feedback 指出 framework 結構錯位                  | 多次（外部 + 內部）                     |
| 既有 dogfood 樣本累積到足以重寫 framework                   | ≥ 10 同類樣本 / axis                    |
| Reviewer D 從「結構性質疑」升到「結構性錯誤」              | 質疑措辭從「可能」「考慮」變「應該」「必須」|

## 反模式

| 反模式                                       | 後果                                                                 |
| -------------------------------------------- | -------------------------------------------------------------------- |
| Reviewer D 揭露結構性質疑、選擇隱藏不寫進卡   | 後續 reader 不知 limitation、繼續用框架踩同樣坑                      |
| Phase 3a 變成 disclaimer 大全、卡末塞 20+ 限制 | 反而被讀者跳過、limitation 失去 anchor 作用                          |
| Phase 3b 在 sample 不足時做                  | Framework 在 N=2-5 樣本上重寫、新框架仍 over-fit、循環往復          |
| 把 Phase 3a 寫成「未解決議題清單」、無 trigger | 沒 trigger 等於永遠不動、limitation 變空話                          |
| Self-aware limitation 段過長、沒先寫核心結論  | Reader 看到 limitation 就棄讀、核心 framework 沒被讀懂              |

## 跟其他原則的關係

| 原則                                                                  | 關係                                                          |
| --------------------------------------------------------------------- | ------------------------------------------------------------- |
| [six-dimension-audit-framework](./six-dimension-audit-framework.md)   | Audit framework 本身的演化機制 — 6 維 / 6 type / 主導維度優先序都需要 limitation 段保留誠實 |
| [stage-0-variant-discipline](./stage-0-variant-discipline.md)         | 寫作流程紀律 — 寫作前主動規劃、寫作後 reviewer audit、揭露 limitation 後 meta-acknowledgment 三段一體 |
| [axis-candidate-evaluation](./axis-candidate-evaluation.md)            | 演化 trigger — limitation 段列的 trigger 對應 axis candidate 評估流程 |

## 自查清單

寫 Phase 3a meta-acknowledgment 段時：

1. **每個 limitation 都有 *為什麼保留現狀* 理由嗎**？沒理由就是該 Phase 3b、不是 Phase 3a
2. **每個 limitation 都有 *trigger* 觸發 Phase 3b 嗎**？沒 trigger 就是「永遠不動」
3. **總 limitation 數 ≤ 8 條**？超過 8 條表示 framework 結構不穩、考慮 retroactive audit
4. **Limitation 段在卡末、不擋核心結論**？放卡末是 default、避免阻擋 first-time reader
5. **「擴張不是重構」這類 disclaimer 詞慎用**？通常是 silent grandfathering、應該誠實寫
