---
name: multi-round-review
description: "寫多篇章節後做多輪 agent reviewer audit 的標準操作流程。每輪用不同 frame 切換、跨輪 finding 互不重疊、停止訊號是 frame 涵蓋而非 finding 數遞減。觸發詞：多輪審查、Round 1/2/3、frame 切換、跨輪審查、reviewer 規劃、何時停止 review、cadence 同骨化、enumeration 不窮盡、self-application sweep。Trigger when reviewing multiple writings via successive rounds of agent reviewers."
license: MIT
metadata:
  version: 1.0.0
  category: writing-methodology
---

# Multi-Round Review

寫多篇章節後做多輪 agent reviewer audit 的標準操作流程。每輪用不同 frame、跨輪 finding 互不重疊、停止訊號是 frame 涵蓋而非 finding 數遞減。已在一次 backend 5 章 + 1 report 卡的 review 驗證、3 輪 9 個 reviewer 抓出 38 個零重疊 finding。

## 適用情境

- **多篇相關章節**：3+ 章一起寫完、需要跨稿件 audit
- **品質高於速度**：每輪 30-60 分鐘 reviewer + 30-120 分鐘 fix、3 輪約 4-8 小時
- **章節品質敏感**：教學模組、規範文件、長期累積的內容
- **主 context 容量敏感**：reviewer 平行 background 是節省 context 的關鍵設計

不適用：

- **單篇短文**：固定成本（規劃 frame + 跑 reviewer + 整合 finding）對短文 ROI 低
- **快速迭代原型**：流程偏向「寫一次寫好」、不是「快速修改」
- **低風險文件**：個人筆記、草稿、不需要外部 review

## 三大基本原則

1. **每輪用不同 frame**（per [#114 multi-pass frame 顆粒度盲點](references/principles/multi-pass-frame-granularity.md)）：同 reviewer / 同 frame 跑多輪 catch 高度相同。多輪價值在 frame 切換、不在重複加深。
2. **跨輪 finding 互不重疊**：若新一輪 finding 跟上一輪重疊、代表 frame 沒換、再跑無增益。
3. **停止訊號是 frame 涵蓋、不是 finding 遞減**（per [#148 跨輪 review 停止訊號](references/principles/cross-round-stopping-signal.md)）：多輪 review 通常 finding 不遞減、Round 3 可能比 Round 1 / 2 多。停止判讀看「想不出新 frame」。

## 標準流程

### Round 1：Compliance / 基線 audit

最先用「規範遵循」frame、抓 surface 層問題。常見三個 reviewer 平行 background：

- **A: 寫作規範 audit** — AGENTS.md / markdown-writing-spec / compositional-writing 規範遵循
- **B: 案例 / fact-check audit** — 案例引用準確性、編號 mis-cite、跨章節引用
- **C: 跨章一致性 audit** — 編號、學習路線、模組整合、frontmatter 一致

預期 finding 類型：編號錯、broken link、案例 mis-citation、規範違反、cadence 散點。

### Round 2：Cadence / 讀者旅程 frame

修完 Round 1 後、改用「字句層 + 讀者體驗」frame：

- **A: Cadence + 字句層** — 句型同骨化（per [#122 cadence 同質化](references/principles/cadence-homogenization.md)）、廢話前綴、口語修辭、地區用語
- **B: Reader simulation 旅程審查** — 假裝特定讀者類型（如「剛從入門影片進來的開發者」）、實際走學習路線、看入口判讀 / 內容門檻 / 跳出訊號
- **C: Title commitment + cross-surface** — body 是否對齊 title 承諾、跨 surface（章節 ↔ report 卡 ↔ knowledge card）三角對齊

預期 finding 類型：cadence 同骨化（多篇同位置同句型）、影片詞彙橋斷裂、enumeration 模板化。

### Round 3：Self-application / Steelman / Outbound frame

修完 Round 2 後、改用「meta / 知識淵博讀者 / 跨章影響」frame：

- **A: Self-application sweep** — 用本 batch 寫的 report 卡 / 規範 self-grep 同 batch 稿件、catch 規範化後仍犯的同義變體（per [#147 規範化跟自審](references/principles/rule-codification-self-audit.md)）
- **B: Steelman / Reality test** — 知識淵博讀者視角、檢查判讀訊號 / 取捨表 enumeration 是否窮盡、有無稻草人、數字 / 閾值有無源頭
- **C: Outbound impact audit** — 既有章節應該但沒引用新章節的反向引用、knowledge card 缺口、跨章節整合段缺位

預期 finding 類型：同義變體（grep pattern 漏抓）、enumeration 不窮盡、反向引用斷裂、新概念缺卡。

## Round N 規劃判讀

Round 3 之後是否需要 Round 4？四個停止訊號齊備、停：

1. **新 frame 想不出來**：team 腦力激盪 30 分鐘想不出「能 catch 新東西」的 frame
2. **七軸動完**：per [#126](references/principles/review-seven-axes.md)、frame / instance / surface / scope / cadence / timing / granularity 七軸都用過
3. **Finding 性質退化**：新 frame catch 到的 finding 又退回 surface 層
4. **修法成本反轉**：修一個 finding 成本超過讀者實際感受價值

任二齊備、可以判定「真的夠了」。任一齊備、繼續但要主動規劃 frame 切換。

## Reviewer prompt 結構

每個 reviewer 用 background agent、prompt 結構：

```text
你是 [frame 名稱] 審查員。任務是用 [frame 描述] 對 N 篇稿件做 audit。

# 必讀規範
- [規範檔案清單]

# 審查目標
- [章節 / 報告卡完整路徑清單]

# 審查維度
[3-6 個具體維度、每個帶 grep pattern 或檢查方式]

# 不要做
[排除已被前面 round 覆蓋的維度、避免 finding 重疊]

# 輸出格式
- 嚴重（必修）：違反 [規範]
- 建議（可改）：可優化但非阻塞
最後給「整體評估」分級。
報告 1500 字內、不修檔案。
```

關鍵設計：

- **「不要做」段必填**：排除已被前面 round 覆蓋的 frame、強制 reviewer 進入新維度、避免 finding 重疊
- **平行 background 跑**：3 個 reviewer 同時跑、主 context 節省 ~80% token
- **輸出限長**（1500 字）：避免報告自我膨脹、強制 reviewer 精煉

## 整合 finding 跟 fix 工作流

每輪結束後：

1. **跨 reviewer convergence**：3 個 reviewer 報告中重疊的 finding 優先序最高（per [#138 cross-reviewer convergence](references/principles/cross-reviewer-convergence.md)）
2. **整合 punch list**：列嚴重 / 建議 / 不修三層、估每項修法成本
3. **跟用戶確認修法範圍**：「修必修 + 建議全部修 / 只修必修 / 全部 backlog」用 AskUserQuestion 取得方向
4. **拆 commit**：按 frame 拆 2-3 個 commit（如 commit 1 處理規範 frame finding、commit 2 處理 cadence frame）
5. **驗證 + commit**：mdtools lint / cards / fmt 跑過、各 commit 帶清楚的修法描述

## 跟既有 skill 的關係

- [`case-first-module-workflow`](../case-first-module-workflow/SKILL.md) 的 Stage 4 含「agent team review」但偏 case-driven 單輪。Multi-round-review 補完跨輪 frame 切換維度、可以接在 case-first 的 Stage 5 之後或同時使用。
- [`compositional-writing`](../compositional-writing/SKILL.md) 提供寫作原則（intent-revealing、grep-friendly）、本 skill 不重複、reviewer prompt 直接引用其檢查 pattern。

## 反模式

- **用 finding 數遞減當停止訊號**：上一輪修完、下一輪 finding 變少就停 — 會錯過「更深層 frame 仍有 finding 待 catch」的時機
- **同 reviewer 跑多輪**：per #114、同 frame 多輪 catch 高度重複、無增益
- **跳過 frame 規劃直接派 reviewer**：「再來一輪 audit」沒指定 frame 切換、reviewer 用同方向掃同類問題、是 #114 的具體實例
- **單跑字面 grep 修法**：修完字面層（編號、broken link）就以為到位、漏掉結構層（cadence）跟同義變體（per #147）
