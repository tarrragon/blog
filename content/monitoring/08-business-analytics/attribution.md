---
title: "Attribution"
date: 2026-06-19
description: "使用者從哪來、哪個渠道帶來轉換 — last-touch / first-touch / multi-touch 歸因模型的差異和選擇"
weight: 4
tags: ["monitoring", "analytics", "attribution", "marketing", "conversion"]
---

Attribution（歸因）回答「使用者的轉換應該歸功於哪個渠道或觸點」。使用者可能先看到 Facebook 廣告、再 Google 搜尋、最後直接輸入網址完成購買 — 三個渠道都接觸了使用者，轉換功勞歸誰決定了行銷預算的分配。

## 歸因模型

### Last-touch attribution

把轉換功勞全部歸給使用者轉換前最後接觸的渠道。上例中功勞歸「直接輸入網址」。

優點：實作最簡單 — 只需要記錄轉換事件的 referrer 或 UTM 參數。

缺點：忽略了前面渠道的貢獻。Facebook 廣告讓使用者第一次知道產品，但在 last-touch 模型中功勞為零。長期使用 last-touch 會導致行銷預算過度集中在「最後一步」渠道（品牌搜尋、直接訪問），低估「認知階段」渠道（展示廣告、社群媒體）。

### First-touch attribution

把轉換功勞全部歸給使用者第一次接觸的渠道。上例中功勞歸 Facebook 廣告。

優點：強調「獲客」渠道的貢獻，適合評估品牌認知和獲客效率。

缺點：忽略了後續渠道的推進作用。使用者第一次看到廣告但沒行動，可能是後續的 Google 搜尋才促成轉換。

### Multi-touch attribution

把轉換功勞分配給使用者轉換路徑上的所有渠道。分配方式有多種：

- **線性歸因**：每個渠道平均分配。三個渠道各得 33.3%。
- **時間衰減**：離轉換越近的渠道得到越多功勞。
- **Position-based（U 型）**：第一個和最後一個渠道各得 40%，中間渠道分 20%。
- **資料驅動（data-driven）**：用機器學習模型從歷史資料學習每個渠道的貢獻。需要大量資料。

## 技術實作

Attribution 的技術實作需要解決兩個問題：跨 session 的使用者識別，和觸點的記錄。

### 跨 session 識別

同一個使用者在不同 session、不同裝置、不同瀏覽器上的行為需要關聯到同一個人。

Web 端用 cookie（first-party）或 login ID 關聯。Mobile 端用 device ID 或 login ID。跨裝置關聯需要使用者登入 — 未登入的使用者在不同裝置上是不同的匿名 ID。

### 觸點記錄

每次使用者接觸產品的渠道需要記錄。Web 端記錄 referrer、UTM 參數（`utm_source`、`utm_medium`、`utm_campaign`）。Mobile 端記錄 deep link 參數、app store 來源（需要 attribution SDK 如 AppsFlyer、Adjust）。

## 自架方案的歸因能力

自架 collector 能做基礎的 last-touch attribution — 在轉換事件的屬性中記錄 referrer 和 UTM 參數。

Multi-touch attribution 需要跨 session 的使用者行為歷史，實作複雜度顯著上升。如果 multi-touch 是核心需求，商業方案（GA4、Mixpanel、AppsFlyer）通常比自架更實用。

## 下一步路由

- A/B test 驗證渠道效果 → [A/B test 的統計基礎](/monitoring/08-business-analytics/ab-test-statistics/)
- 使用者分群 → [Cohort analysis](/monitoring/08-business-analytics/cohort-analysis/)
- 行為事件設計 → [行為事件設計](/monitoring/08-business-analytics/behavior-event-design/)
- 客戶取得成本 → [CAC](/business/knowledge-cards/cac/)
