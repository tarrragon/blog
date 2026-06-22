---
title: "4.8 訊號治理閉環"
date: 2026-06-22
description: "把 postmortem 揭露的偵測缺口回寫成新訊號、讓觀測能力隨事故學習成長"
weight: 8
tags: ["backend", "observability"]
---

## 大綱

- 為何訊號需要治理閉環：alert / metric / dashboard 是會老化的資產
- 偵測缺口的來源：post-incident review、chaos test、日常 noise
- 訊號生命週期：新增 → 調整 → 淘汰
- Alert 健康度量測
- Dashboard 健康度量測
- 治理節奏與 ownership
- 反模式

## 概念定位

訊號治理閉環是把事故、演練與日常使用經驗回寫到觀測系統的流程，責任是讓 alert、metric 與 dashboard 隨服務變化而更新。

觀測資產會老化：服務拓撲會變、流量型態會變、告警接收者會離職或轉組。設定一次就不再動的 alert rule 會在數月後變成 noise 來源；建立一次就不再看的 dashboard 會累積成系統負擔。訊號治理把觀測系統當成需要持續維護的產品，而非建好就完成的基礎設施。

跟 [4.4 dashboard-alert](/backend/04-observability/dashboard-alert/) 的分工：4.4 處理設計（怎麼設計好的 dashboard 跟 alert），4.8 處理維運與淘汰（設計好之後怎麼讓它們持續有效）。

## 偵測缺口的來源

### Post-incident review

每次事故的 [post-incident review](/backend/knowledge-cards/post-incident-review/) 都可能揭露偵測缺口 — 事故發生到被偵測到的時間太長、alert 觸發了但指向錯誤的方向、或根本沒有 alert 觸發。

偵測缺口的分類：

| 缺口類型               | 典型表現                                  | 回寫方向             |
| ---------------------- | ----------------------------------------- | -------------------- |
| 訊號缺失               | 問題存在但沒有對應的 metric 或 trace      | 新增 metric / span   |
| Alert 太晚             | Alert 在使用者投訴後才觸發                | 調整閾值或加短窗     |
| Alert 指向錯誤         | Alert 觸發了但指向不相關的服務            | 修正 alert rule      |
| Dashboard 沒有對應視圖 | 事故中需要看某個維度但現有 dashboard 沒有 | 新增 panel           |
| 關聯性斷裂             | Log / trace / metric 無法用同一個 ID 串連 | 補 correlation field |

Post-incident review 的 [action items](/backend/knowledge-cards/action-item-closure/) 中標記為「detection gap」的項目，應該指派給觀測系統的 owner，帶明確的 metric / alert / dashboard 變更規格。

### Chaos test 與演練

[Chaos test](/backend/knowledge-cards/chaos-test/) 跟災難恢復演練會在受控條件下暴露觀測盲區。注入 dependency failure 後，觀測系統是否在預期時間內觸發 alert？Alert 是否指向正確的方向？Dashboard 是否有足夠的 panel 支援診斷？

演練揭露的盲區跟事故揭露的盲區性質相同，但成本更低 — 在受控環境發現的缺口不會拉長真實事故的 MTTR。

### 日常 noise 累積

Alert noise 的日常累積是漸進式的退化 — 每個月新增幾個 alert rule 但沒有淘汰舊的，noise rate 從 10% 慢慢升到 30% 再到 50%。退化的訊號是 on-call 工程師開始忽略某些 alert（先 ack 再看、或直接 resolve 不看）。

## 訊號生命週期

### 新增

新訊號的來源：新服務上線時的 [readiness review](/backend/04-observability/observability-readiness-review/) 檢查、post-incident review 的 detection gap、chaos test 暴露的盲區、新功能上線時的 SLI 定義。

新增訊號時要同時定義：metric / alert 的 owner、預期的 noise rate baseline、review 週期、淘汰條件。沒有 owner 跟 review 週期的訊號會在累積後變成治理負擔。

### 調整

調整的觸發條件：alert threshold 跟當前 baseline 偏差過大、dashboard panel 的資料來源（metric name、label）已改變、alert 的 runbook link 過期、noise rate 超過團隊可接受的上限。

調整是訊號治理的主要日常工作。多數訊號不需要刪除，但需要隨服務演進跟著更新。

### 淘汰

淘汰的觸發條件：alert rule 超過 N 天（例如 180 天）沒有觸發、dashboard 超過 N 天沒有人訪問、metric 被 recording rule 取代後原始查詢不再使用、服務已下線但 alert / dashboard 還在。

淘汰需要 owner 確認。自動淘汰（超過 180 天不觸發就自動刪除）風險太高 — 有些 alert 本來就是極低頻但極高價值（年度高峰才觸發的 capacity alert）。安全做法是自動標記候選淘汰，由 owner 在定期審視中決定保留或刪除。

## Alert 健康度量測

Alert 的健康度用四個指標追蹤：

**Noise rate**：不需要行動的 alert / 總 alert。On-call 在 ack 時標記 actionable / noise。月度彙整。目標：< 30%。

**MTTD（Mean Time to Detect）**：事故開始到 alert 觸發的時間。從 incident timeline 回溯。目標：跟 SLO burn rate window 對齊（急性問題 < 5 分鐘）。

**False positive rate**：alert 觸發但事後確認沒有問題 / 總 alert。跟 noise rate 不同 — noise 包含 redundant alert（有問題但重複），false positive 是真的沒問題。

**Coverage**：有 alert 覆蓋的 user journey / 總 user journey。未覆蓋的 user journey 代表潛在的偵測盲區。

## Dashboard 健康度量測

Dashboard 的健康度用三個指標追蹤：

**訪問頻率**：每個 dashboard 的每週 / 每月訪問次數。Grafana 的 usage analytics 或 access log 可以提供。長期零訪問的 dashboard 是候選淘汰。

**Data freshness**：Dashboard panel 是否顯示有效資料。Panel 因 metric name 改變或 label 漂移而回空值時，曲線看起來是平的零線 — 容易被誤讀成「一切正常」。定期掃描所有 panel 的 no-data 狀態。

**Owner coverage**：有 owner 的 dashboard / 總 dashboard。沒有 owner 的 dashboard 沒人負責更新，退化只是時間問題。

## 治理節奏

訊號治理需要固定節奏，避免「只在事故後才補訊號、平時不管」的反應式治理。

**事故驅動（每次事故後）**：Post-incident review 的 detection gap action items 在兩週內 close — 新增 / 調整的 metric、alert、dashboard 已部署並驗證。

**定期審視（每季）**：

- Alert noise rate 報告：noise rate > 30% 的 alert rule 進入調整或淘汰流程
- Dashboard 訪問頻率報告：零訪問 dashboard 進入淘汰審視
- Orphan alert / dashboard（owner 離職或轉組、未交接）指派新 owner

**年度回顧**：

- 觀測覆蓋率（有 instrumentation 的服務 / 總服務）
- SLI / SLO 的量測點跟閾值是否需要調整（業務變化、流量變化）
- 觀測成本 vs 事故成本的 ROI 評估

## 核心判讀

判讀訊號治理時，先看缺口是否有來源，再看改善項是否真的關閉。

重點訊號包括：

- [Post-incident review](/backend/knowledge-cards/post-incident-review/) 是否把偵測缺口轉成具體 metric / alert / dashboard 變更
- [Chaos test](/backend/knowledge-cards/chaos-test/) 或 DR 演練是否暴露新的觀測盲區
- Alert noise、ack time、false positive 是否有趨勢追蹤
- Orphan dashboard 與過期 alert 是否有定期清理節奏

## 判讀訊號

- Alert 數量只增不減、無淘汰流程
- Alert noise rate > 30%、ack 後無實際動作
- Dashboard 半年無人訪問、仍存在於主目錄
- Post-incident review action items 大半 open > 90 天
- 同類事故重複發生、觀測系統無更新
- Alert owner 離職後無人接手、alert 成為孤兒

## 反模式

| 反模式                         | 表面現象                                   | 修正方向                      |
| ------------------------------ | ------------------------------------------ | ----------------------------- |
| Alert 只增不減                 | 數百個 alert rule、多數是 noise            | 定期審視 + 自動標記候選淘汰   |
| Dashboard 全是裝飾             | 事故時沒人打開、只有 demo 時展示           | 追蹤訪問頻率、零訪問的淘汰    |
| Post-incident action 永遠 open | Detection gap 被記錄但半年沒 close         | 兩週 close 期限、逾期自動升級 |
| 治理只在事故後才啟動           | 平時不管、出事才補                         | 建立每季定期審視節奏          |
| Orphan alert 無人負責          | Owner 離職後 alert 持續觸發但沒人處理      | 交接流程 + orphan 掃描        |
| Chaos test 不看觀測面          | 只看服務恢復、不看 alert 跟 dashboard 表現 | Chaos hypothesis 包含觀測預期 |

## 交接路由

- [4.4 dashboard-alert](/backend/04-observability/dashboard-alert/)：alert / dashboard 的設計原則
- [4.5 威脅建模](/backend/04-observability/attacker-view-observability-risks/)：告警失真作為觀測弱點
- [4.7 cardinality](/backend/04-observability/cardinality-cost-governance/)：新訊號的成本邊界
- [4.14 anomaly detection](/backend/04-observability/anomaly-detection/)：anomaly false positive 的淘汰
- [4.16 readiness review](/backend/04-observability/observability-readiness-review/)：上線前的觀測覆蓋檢查
- [4.18 operating model](/backend/04-observability/observability-operating-model/)：ownership 矩陣
- [8.5 post-incident review](/backend/knowledge-cards/post-incident-review/)：action items 回寫機制
- [8.11 閉環](/backend/08-incident-response/observability-reliability-incident-loop/)：跨模組視角的閉環
