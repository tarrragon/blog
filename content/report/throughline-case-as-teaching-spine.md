---
title: "貫穿式案例是服務教材的教學骨架"
date: 2026-05-19
weight: 132
description: "服務型教材需要一條可重播的貫穿式案例，把資料庫、快取、queue、觀測、部署、可靠性、資安、事故與容量串成同一個服務演進路徑。沒有貫穿式案例時，章節會各自正確但讀者難以理解能力之間如何交接。"
tags: ["report", "事後檢討", "工程方法論", "寫作", "教材設計", "case-driven"]
---

## 核心原則

服務型教材需要貫穿式案例作為教學骨架。資料庫、快取、queue、觀測、部署、可靠性、資安、事故與容量都可以獨立成章，但讀者真正需要學會的是這些能力如何在同一個服務裡交接、互相約束並共同演進。

貫穿式案例是一條可重播的服務演進路徑，而非單一大型專案手冊。它用同一個中性服務情境反覆穿過多個模組，讓讀者看到每個模組處理的是同一個系統在不同壓力下的責任切面。

## WARP 分析摘要

| 面向         | 內容                                                                                                            |
| ------------ | --------------------------------------------------------------------------------------------------------------- |
| Anchor       | Backend 教材要教的是後端服務如何共同支撐 production system，單章正確不足以證明整體教學成立。                    |
| Step 0       | 現有 Backend 已有多個服務路徑示範與 artifact backbone，但還缺系列入口層明示的貫穿式案例。                       |
| Widen        | 可選方式有能力分類、讀者旅程、貫穿式案例。三者可疊加：能力分類是目錄，讀者旅程是路線，貫穿式案例是演練骨架。    |
| Reality Test | Go 用簡化通知服務承接語法到實戰，LLM 用本地 LLM 工作流承接心智模型到工具；Backend 也需要同類骨架。              |
| Prepare      | 若後續章節各自引用不同情境，讀者仍難以看出 DB / cache / queue / observability / incident 如何在同一服務內交接。 |

反向驗證：貫穿式案例要維持中性、簡化、可替換，並明示它是教學載體；讀者理解案例所需的背景要由文章提供，而非內部專案知識。

## 情境

Backend 已有多篇服務路徑示範，例如 schema migration evidence、cache migration rollback、queue retry replay、checkout API evidence package、release gate、credential rotation 與 incident decision log。這些文章各自能說明一段能力，但它們在入口層還沒有被明確收斂成一條「讀者可以跟著走」的服務演進路線。

對照 Go 與 LLM：

| 教材        | 貫穿骨架                                                             |
| ----------- | -------------------------------------------------------------------- |
| Go          | 從小程式走到簡化即時通知服務                                         |
| Go advanced | 用長時間運行服務、WebSocket、event-driven service 當重複情境         |
| LLM         | 用本地 LLM 寫 code 工作流，把硬體、推論伺服器、模型、IDE、安全串起來 |
| Backend     | 目前多個 artifact 示範分散存在，尚未在入口層組成一條主案例           |

Backend 的內容特性更需要貫穿式案例，因為它處理的是多個外部服務的協作教材，範圍大於單一語言或單一工具。

## 理想做法

### 第一步：選一個中性服務作為載體

貫穿式案例應該選讀者容易理解、又能自然觸發多個 Backend 模組的服務。較穩定的候選是 `checkout / order / payment / notification` 類流程。

這條服務路徑可承接：

| 模組             | 在案例中的責任                                              |
| ---------------- | ----------------------------------------------------------- |
| 01 Database      | order / payment 狀態、schema migration、reconciliation      |
| 02 Cache         | 商品、價格或 entitlement 的 freshness 與 origin protection  |
| 03 Queue         | order_created / payment_confirmed 的 retry、DLQ、replay     |
| 04 Observability | checkout evidence package、trace、dashboard、query link     |
| 05 Deployment    | checkout service rollout、drain、rollback                   |
| 06 Reliability   | provider dependency release gate、load / chaos / regression |
| 07 Security      | webhook secret rotation、PII masking、audit evidence        |
| 08 Incident      | payment incident decision log、write-back、action item      |
| 09 Performance   | peak checkout capacity、saturation、cost per request        |

### 第二步：把案例拆成多個可重播 episode

貫穿式案例要避免寫成一篇巨文。較穩定的做法是拆成 episode，每個 episode 對應一個模組責任。

| Episode | 問題                            | 主要模組          |
| ------- | ------------------------------- | ----------------- |
| E1      | 新增付款狀態欄位                | 01 + 04 + 08      |
| E2      | 商品價格快取失效與回源保護      | 02 + 04 + 06      |
| E3      | 訂單事件 consumer 失敗與 replay | 03 + 06 + 08      |
| E4      | Checkout service rollout        | 05 + 04 + 08      |
| E5      | Payment provider timeout 變更   | 06 + 04 + 09      |
| E6      | Webhook secret rotation         | 07 + 04 + 08      |
| E7      | Flash-sale peak readiness       | 09 + 02 + 03 + 06 |

Episode 讓讀者看到「同一服務在不同壓力下需要不同模組」，同時保留單篇文章的原子性。

### 第三步：讓每章都回到同一條服務路徑

每篇主章不需要都重述整個案例，但要能指出它在貫穿案例中的位置。這樣讀者可從任一章回到主線，也可按主線依序讀。

最小寫法：

```markdown
本章在貫穿式 checkout 案例中處理 E3：訂單事件 consumer 失敗後，如何判斷投遞、處理與恢復語意。
```

這句話把章節放回教學骨架，避免單章漂成孤立知識點。

## 沒這樣做的麻煩

### 章節各自正確，但整體難學

資料庫、快取、queue、觀測與事故章節都可以各自寫得正確。讀者看過它們如何在同一條服務路徑交接後，平行知識才會組成 production system 的整體模型。

### 案例庫會停在素材層

大量 case 能支撐反向驗證，但 case 本身不會自動形成學習路線。貫穿式案例的責任是把素材庫轉成讀者可重播的主情境。

### Vendor / migration 內容會太早成為主角

讀者在還沒理解服務交接前讀 vendor 或 migration，容易把具體工具當成主線。貫穿式案例能先建立「問題如何跨模組流動」，再讓 vendor / migration 成為進階專題。

## 跟其他抽象層原則的關係

| 原則                                                                                          | 關係                                                                                |
| --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| [#98 素材庫比例要支撐主情境的反向驗證](../source-library-ratio-supports-scenario-validation/) | #98 說素材庫要支撐主情境；本卡定義服務教材的主情境應有一條貫穿式案例。              |
| [#120 案例引用三段式段落結構](../case-citation-three-part-structure/)                         | 貫穿式案例在單段引用時仍要遵守概念定義 → case 引用 → 通用展開，不讓 case 取代概念。 |
| [#119 章節已有 routing skeleton 走補強段](../routing-layer-chapter-recognition/)              | 貫穿式案例是系列級 routing skeleton。後續擴章要補 episode 與路由，保留既有主線。    |
| [#130 教材目標先於決策框架](../teaching-goal-before-decision-frame/)                          | #130 定義教材目標，本卡提供讓目標落地的案例骨架。                                   |
| [#131 教材完整性要用讀者旅程驗證](../teaching-completeness-by-learner-journey/)               | 讀者旅程回答「怎麼讀」，貫穿式案例回答「沿著什麼服務情境練」。                      |

## 判讀徵兆

| 訊號                                           | 該做的事                       |
| ---------------------------------------------- | ------------------------------ |
| 模組章節很多，但讀者不知道它們怎麼串成一個服務 | 補貫穿式案例                   |
| 每篇文章都用不同業務情境，跨章記憶成本高       | 收斂到 1 條主案例 + 少量變體   |
| 案例庫豐富但主文章仍像概念清單                 | 把案例轉成可重播 episode       |
| Vendor / migration 內容比服務主線更顯眼        | 用貫穿案例重新定義進階專題入口 |
| 跨模組 link 多，但沒有共同 user journey        | 補 episode map 與主線導讀      |

**核心原則**：服務型教材要有貫穿式案例。能力分類讓作者整理內容，讀者旅程讓讀者知道怎麼讀，貫穿式案例讓讀者看到多個能力如何在同一個 production service 中交接與演進。
