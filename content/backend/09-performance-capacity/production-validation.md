---
title: "9.10 Production-Side 驗證"
date: 2026-05-12
description: "shadow traffic、dark launch、canary、production-like load test"
weight: 10
tags: ["backend", "performance", "capacity", "production-validation"]
---

## 概念定位

Production-side 驗證的責任是回答「staging 過了 production 一定過嗎」。多數 staging 環境的硬體 / 流量 / 資料 / 第三方依賴都跟 production 不一樣、staging 通過不代表 production 安全。本章處理「在 production 安全驗證新配置」的工程做法。

跟 [06.20 experiment safety boundary](/backend/06-reliability/experiment-safety-boundary/) 的關係：06.20 走「故障注入」的安全邊界（chaos）、9.10 走「正常負載」的 production 驗證（perf）。兩者方法論類似、目標完全不同。chaos test 是「主動破壞看會不會出事」、production perf validation 是「真實流量看新版本能不能跑」。

本章四個工具（shadow traffic、dark launch、canary、production-like load test）按 *blast radius* 從小到大排列、每個適合不同驗證場景。

## Shadow traffic

[Shadow traffic](/backend/knowledge-cards/shadow-traffic/) 是 blast radius 最小的工具：複製 production traffic 到新版本、但 *不把結果返回用戶*。

**運作機制**：

- 用戶看到的還是舊版本回應、體驗不變
- 新版本只是「並行跑、看會不會崩」
- 新版本的結果可以跟舊版本對比、找出邏輯差異
- 對下游的寫入要 *特別處理*：要麼寫入 sandbox、要麼 dry-run（純驗證 query plan、不真寫）

**工具實作**：

- GoReplay：tcpdump-based 開源、適合 HTTP
- Service mesh shadow（Istio、Linkerd mirror）：mesh 層 mirror、零 application invasion
- AWS VPC Traffic Mirroring：底層網路層、加密 traffic 要另處理
- Diffy（已 deprecated 但概念有效）：dual-write 對比結果

**適合場景**：架構大改、想驗證 *是否能撐 production traffic* 但不能影響用戶。例如「DB 從 PostgreSQL 換 Aurora、想看新 DB 在真實 query pattern 下穩不穩」。

**注意事項**：

- shadow traffic 也消耗 production 下游資源（DB read、API call）— 必須算進容量
- 加密 / PII 資料需要處理
- shadow 通常跑 1-7 天看 long-tail、不是 30 分鐘就下結論

對應案例：[Tixcraft 10K t2.micro 壓測](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — pre-event 壓測但走 staging；real shadow 則是 *production-traffic-driven* 而非合成。

## Dark launch

[Dark launch](/backend/knowledge-cards/dark-launch/) 介於 shadow 跟 canary 之間：程式碼上線、走 production traffic、但 *UI 入口暫不開放*。

**跟 shadow 的差別**：

- Shadow：traffic 複製、新版本 *不寫入真實狀態*
- Dark launch：*真實寫入 production*、但用戶看不到 UI

**運作機制**：

- 後端 code 部署到 production
- 用 feature flag 控制 UI 暴露
- 從內部 API、cron job、employee-only access 觸發新功能
- 真正寫入 production DB / cache / queue
- 用戶看不到 UI 入口、無感

**Exit criteria**：

- 跑足夠時間（通常 1-2 週）
- 內部使用沒有 critical issue
- metric 在預期範圍

**適合場景**：新功能後端風險高、想 production-validate 再開放給用戶。
**不適合**：純 UI 改動（沒有後端風險、直接 canary）。

對應案例：[SeatGeek Virtual Waiting Room](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/) 從第三方換到自建、必然有 dark launch 階段驗證 token 配發機制、再正式 cutover。

## Canary

Canary 是 production-side 驗證最常用工具：小比例流量導到新版本、跟舊版本對比。

**運作機制**：

- 小比例（1% / 5% / 10%）流量導到新版本
- 大部分流量（99% / 95% / 90%）走舊版本
- 比較 perf / error / business metric
- 通過 → 漸進放大；不通過 → 自動 rollback

**漸進放大策略**：1% → 5% → 25% → 50% → 100%、每階段觀察足夠時間（至少 15 分鐘看 long-tail）。

**自動 rollback 條件**：

- error rate canary 比 control 高 X%（例如 50%）
- p99 latency canary 比 control 退化 X%（例如 10%）
- business metric（conversion rate）canary 比 control 低 X%

**Canary perf check 跟一般 canary 的差異**：

- 一般 canary：看 error rate 為主
- [Canary perf check](/backend/knowledge-cards/canary-perf-check/)：看 latency / throughput / cost、退化通常早於 error rate

**比較的對象是 control（同時跑的舊版本）、不是 baseline**：同樣流量同樣時段才能對比、不能拿 canary 跟昨天 baseline 比（外部變數太多）。

對應案例：[Prime Day pre-event 驗證](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) / [FanDuel canary across 20 州](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) — 按 region 漸進放大、控制 blast radius。

## Production-like load test

當需要驗證 *peak 場景* 但 production 平日流量達不到時、在 production 跑額外的 synthetic load。

**為什麼要在 production 跑**：

- staging 環境的硬體 / 網路 / 第三方依賴跟 production 不同
- staging 沒有 production 級資料量、cache hit pattern 不一樣
- 只有 production 才能驗證真實 peak

**風險高、必須有安全邊界**：

- blast radius 限制（用 dedicated test endpoint、限制影響範圍）
- abort condition（什麼訊號觸發停止）
- rollback path（rollback 流程跟時間）
- 通訊（相關 oncall 通知、避免誤判 incident）

**通常用在**：

- Pre-event 壓測（Black Friday、Super Bowl、IPL 決賽 前一週）
- 重大架構變更後驗證
- 容量規劃 review（每年 / 每季）

**跟 [06.20 experiment safety boundary](/backend/06-reliability/experiment-safety-boundary/) 同等嚴格的安全要求**：production 壓測本質是 controlled experiment、必須有 game day-level 的計畫跟人員。

對應案例：[Prime Day FIS 8x chaos](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) — 把 chaos test 跟 load test 結合、production-like 驗證；[Tixcraft 10K t2.micro 壓測](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — pre-event 大規模壓測模擬實際售票場景。

## A/B test 與 perf 對齊

Product A/B test（測試新功能對 conversion 的影響）同時也是 perf A/B test。

**為什麼要對齊**：

- 新 feature 可能帶來 perf 退化（多 query、多 component、額外 logic）
- 純看 conversion lift 會誤判：「conversion 上升、所以 OK」可能掩蓋「但 p99 上升 30%」
- A/B 同時看 conversion 跟 perf 兩個 metric

**Guardrails**：

- 業務 metric 改善 + perf 退化 → 工程判斷是否值得（trade-off review）
- 業務 metric 沒改善 + perf 退化 → 直接 reject
- 業務 metric 改善 + perf 改善 → 直接 ship
- 業務 metric 退化 → 不論 perf 怎樣、reject

對應 [06.20 experiment safety boundary](/backend/06-reliability/experiment-safety-boundary/) 的 experiment guardrails。

## Pre-event readiness check（game day）

大事件前跑「全系統 production-like 壓測」、是 production-side 驗證的整合演練。

跟 [9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/) 直接對接 — game day 是 readiness 流程的一個 stage。

Shopify game day、Stripe game day 是業界範本（[06 cases](/backend/06-reliability/cases/) 有完整案例）。

## 安全邊界設計

任何 production-side 驗證都要有清楚的安全邊界、不能臨機應變。

**Blast radius**：

- 影響哪些用戶（X% 流量、特定 cohort、特定 region）
- 影響哪些 service（受 perf 影響的下游）
- 影響哪些 metric（哪些 business metric 可能變化）

**Abort condition**：

- 什麼訊號觸發停止（error rate > X%、latency > Y ms、特定 alert 觸發）
- 由誰觸發（自動 vs oncall 手動）
- 觸發後多久內必須完成 abort（< 60 秒）

**Rollback path**：

- rollback 流程是什麼（feature flag、deployment rollback、traffic shift）
- rollback 需要多久（target < 5 分鐘）
- rollback 是否需要 data 處理（已寫入的資料怎麼處理）

**通訊**：

- 啟動驗證前 notify 哪些 channel
- 期間 oncall 待命
- 結束後 retro

## 反模式

- **Canary 比例太大**（50% 起跳）：出事影響大、blast radius 失控
- **沒 control group**：不知道 baseline、看絕對數字會誤判
- **Canary 跑太短時間**（< 15 分鐘）：看不到 long-tail、看不到 user pattern shift
- **沒 abort condition**：人工監控失誤就出事、不可預測
- **shadow traffic 寫入真實狀態**：可能造成 double charge、duplicate notification
- **production load test 沒 notify 相關團隊**：被當成 incident、誤觸 escalation

## 案例對照

| 案例                                                                                                            | 教學重點                          |
| --------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| [9.C1 Prime Day FIS 8x](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/)               | pre-event chaos + perf 驗證       |
| [9.C15 Tixcraft 10K t2.micro 壓測](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) | pre-event 大規模壓測              |
| [9.C28 FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/)                    | 跨 20 州 canary 控制 blast radius |
| [9.C16 SeatGeek](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/)                         | 從第三方換到自建的 dark launch    |

## 下一步路由

- 上游：[9.9 Improvement Loop](/backend/09-performance-capacity/improvement-loop/)
- 下游：[9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/)
- 跨模組：[06.20 experiment safety boundary](/backend/06-reliability/experiment-safety-boundary/) / [06.4 chaos testing](/backend/06-reliability/chaos-testing/)

## 既建知識卡片

- [Shadow Traffic](/backend/knowledge-cards/shadow-traffic/)
- [Dark Launch](/backend/knowledge-cards/dark-launch/)
- [Canary Perf Check](/backend/knowledge-cards/canary-perf-check/)
