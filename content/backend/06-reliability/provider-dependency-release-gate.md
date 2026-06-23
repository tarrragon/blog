---
title: "6.25 Provider Dependency Release Gate 實作示範"
date: 2026-05-08
description: "以 payment provider 變更示範 release gate 如何結合 evidence、stop condition 與 rollback window。"
weight: 25
tags: ["backend", "reliability", "release-gate", "implementation"]
---

Provider dependency release gate 的核心責任是把第三方依賴風險轉成可驗證放行條件，避免變更在高不確定性下直接擴散。

## 服務路徑與風險模型

示範路徑是 checkout API 切換 payment provider timeout/retry 設定。這類變更看起來只改 config，但會直接影響交易成功率、延遲與重試風暴。

gate 應固定五欄：`Gate decision`、`Checks`、`Stop condition`、`Rollback window`、`Owner`。欄位先成立，再討論工具落地。

以 payment provider timeout 調整為例，五欄的具體內容：

| 欄位            | 範例值                                                                                                         |
| --------------- | -------------------------------------------------------------------------------------------------------------- |
| Gate decision   | proceed / hold / rollback — 每批 canary 結束時做一次判定                                                       |
| Checks          | checkout success rate > 99.5%、provider timeout ratio < 2%、duplicate charge = 0、error budget remaining > 30% |
| Stop condition  | error rate 超門檻、latency p99 超過基線 2 倍、provider timeout ratio > 5%，任一觸發即停止擴批                  |
| Rollback window | 15 min — config-only 變更無 schema 衝突，超過 15 min 後交易資料可能依賴新設定                                  |
| Owner           | checkout team lead，負責每批 go/no-go 與 rollback 決策                                                         |

Checks 欄位的數值來自歷史 baseline，每次變更前從 production 最近 7 天取值。baseline 偏移超過 10% 時，先校準再啟動 canary。

## 實作步驟

1. 定義放行前檢查：checkout 成功率、provider timeout 比率、duplicate charge 監控、[error budget](/backend/knowledge-cards/error-budget/) 餘量。
2. 設定 canary 節奏：1% -> 5% -> 25% -> 100%，每批觀察固定時間窗。
3. 為每批設定 stop condition：error rate、latency、provider timeout 任一超門檻即停止擴大。
4. 設定 rollback window：例如 15 分鐘內可無資料格式衝突地回退設定。
5. 把每批結果寫入 [6.23 Verification Evidence Handoff](/backend/06-reliability/verification-evidence-handoff/) 與 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

### Canary 節奏與觀察窗

| 批次 | 流量比例 | 觀察窗   | Go/no-go 判斷依據                                     |
| ---- | -------- | -------- | ----------------------------------------------------- |
| B1   | 1%       | 30 min   | checks 全過、stop condition 未觸發                    |
| B2   | 5%       | 1 h      | B1 指標持平、無 duplicate charge、無客訴              |
| B3   | 25%      | 2 h      | B2 指標持平、error budget 消耗速度未加快              |
| B4   | 100%     | 持續觀測 | B3 指標持平、跨區結果一致，進入持續觀測而非一次性放行 |

Payment 類變更的觀察窗比一般 config 變更長，原因有兩個。第一，交易確認有延遲 — provider 回傳 settlement 結果可能在數分鐘到數小時後，短觀察窗無法看到完整的交易結果分佈。第二，退款與爭議申請通常在交易後數小時甚至數天才出現，B3 階段需要持續追蹤退款率趨勢，確認新設定沒有引發 provider 層的異常判定。

### 證據留存格式

每批 canary 結束時留存一筆結構化證據，供 [6.23](/backend/06-reliability/verification-evidence-handoff/) 與 [8.19](/backend/08-incident-response/incident-decision-log/) 調用。

| 欄位             | 內容                                                       |
| ---------------- | ---------------------------------------------------------- |
| batch            | B1 / B2 / B3 / B4                                          |
| timestamp        | 批次開始與結束時間                                         |
| traffic %        | 該批實際流量比例                                           |
| metrics snapshot | checkout success rate、latency p99、provider timeout ratio |
| decision         | proceed / hold / rollback                                  |
| decider          | 做出該決策的人與角色                                       |

這個格式讓事故發生時，[8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/) 可以直接調用每批的 metrics 與決策紀錄，不需要回溯 dashboard 截圖。

## 判讀訊號

| 訊號                             | 判讀重點                              | 對應動作                               |
| -------------------------------- | ------------------------------------- | -------------------------------------- |
| canary 成功率正常但 timeout 升高 | 交易完成但成本與延遲風險在累積        | 暫停擴批，先調 provider timeout 策略   |
| error budget 快速消耗            | 變更風險超過目前可承受範圍            | 觸發 freeze，回到上一批設定            |
| rollback 成功但客訴仍上升        | 影響可能來自非同步補償或下游延遲      | 補 replay/對帳證據，再決定是否二次回退 |
| 不同區域結果分歧                 | provider 區域品質差異或路由策略不一致 | 分區 gate，禁止全域同批放行            |
| 告警只反映症狀無法定位變更關聯   | evidence 與 deploy event 沒對位       | 補 deployment event link 與 owner 欄位 |

## 常見誤區

把 gate 當成 CI 綠燈會漏掉依賴風險。依賴類變更需要觀測窗與停損條件，單靠測試通過不足以放行。

把 rollback window 寫成「可回退」但沒有時限也會失效。沒有時間邊界的回退通常意味著資料與行為已經漂移。

## 案例回寫

這條路徑可用 [Stripe Idempotency and Zero-downtime Migration](/backend/06-reliability/cases/stripe/idempotency-and-zero-downtime-migration/) 回寫。先看交易正確性與變更節奏如何綁定，再回到本章對齊 gate 欄位與停損邏輯。

這個案例主要支撐的是「交易依賴變更放行節奏」判讀，不直接支撐 incident 通訊節奏；對外更新要回到 8.4。

## 跨模組路由

1. 與 4.22 的交接：證據來源使用 [Checkout API Evidence Package](/backend/04-observability/checkout-api-evidence-package/)。
2. 與 6.8 的交接：策略與制度回到 [Release Gate 與變更節奏](/backend/06-reliability/release-gate/)。
3. 與 6.23 的交接：每批驗證證據進 [Verification Evidence Handoff](/backend/06-reliability/verification-evidence-handoff/)。
4. 與 8.19 的交接：停損與回退決策同步到 incident decision log。

## 下一步路由

要看控制面事故如何用 decision log 與 write-back 關閉迴圈，接著讀 [8.23 Control Plane Decision Log and Write-back 實作示範](/backend/08-incident-response/control-plane-decision-log-write-back/)。
