---
title: "Cloudflare 2026 BYOIP BGP Withdrawal"
date: 2026-05-07
description: "2026-02-20 Cloudflare BYOIP prefixes 被非預期撤告的事故解析：Addressing API bug、BGP withdrawal、狀態恢復與控制面回寫。"
weight: 3
tags: ["backend", "incident-response", "case-study", "cloudflare"]
---

2026 年 Cloudflare BYOIP / BGP 事故的核心教訓是：控制面資料一旦同時承擔 customer configuration 與 operational state，錯誤清理流程會直接變成全網路由變更。這類事故的第一責任是停止錯誤狀態傳播，再把 desired state 與 actual state 拆開恢復。

## 事故摘要

Cloudflare 在 2026-02-20 17:48 UTC 發生 BYOIP 相關 outage。部分使用 Bring Your Own IP（BYOIP）的客戶，其 IP prefixes 被 Cloudflare 經由 BGP 非預期撤告，導致相關服務從 Internet 無法到達。官方回顧指出，事故總時長為 6 小時 7 分鐘；在 4,306 個 BYOIP prefixes 中，約 1,100 個 prefixes 曾被撤告，約佔 BYOIP prefixes 的 25%。

事故起因不是攻擊，而是 Cloudflare 在 Addressing API / BYOIP pipeline 中引入的自動化清理流程。該流程原本要移除 pending deletion 的 prefixes，但 API query 的 `pending_delete` 參數沒有值，server 端將它解讀成一般查詢，回傳所有 BYOIP prefixes。下游流程接著把回傳結果當成待刪除集合，開始撤告 prefixes 與移除相關 service bindings。

## 判讀訊號

| 訊號                         | 事故中代表什麼                         | 第一波決策價值                                                |
| ---------------------------- | -------------------------------------- | ------------------------------------------------------------- |
| BYOIP prefixes 數量快速下降  | BGP advertisement 正在被控制面錯誤改寫 | 立即停止最新 Addressing API / cleanup 任務                    |
| 客戶服務從 Internet 無法連線 | prefix withdrawal 已影響資料面可達性   | 優先恢復 prefix advertisement，而非只查應用層錯誤             |
| 部分客戶可自行 re-advertise  | 部分狀態只被撤告，binding 尚未被刪除   | 對外提供 dashboard workaround，降低待處理影響面               |
| 部分客戶無法自助恢復         | service bindings 或 edge 設定也被移除  | 需要工程團隊做資料恢復與 global configuration rollout         |
| 恢復分成多批完成             | 受影響 prefixes 處於不同損壞狀態       | decision log 要分別記錄「可自助」「需手動」「需全域 rollout」 |

## 事故路徑

1. Addressing API 相關程式碼在 2026-02-05 合併，並於 2026-02-20 部署。
2. cleanup sub-task 查詢 `/v1/prefixes?pending_delete`，但 `pending_delete` 沒有值。
3. API server 沒有進入 pending deletion 分支，而是回傳所有 BYOIP prefixes。
4. cleanup sub-task 將回傳的 prefixes 解讀成待移除集合，開始撤告 prefixes 與刪除 dependent objects。
5. Cloudflare 在觀察到 1.1.1.1 相關失敗後回退變更並終止 broken sub-process。
6. 多數 prefixes 透過 re-advertise 或 restore 流程恢復，剩餘約 300 個 prefixes 需要工程師手動恢復 service bindings 與 edge 設定。

這條路徑顯示：BGP withdrawal 是結果，真正的事故起點是控制面資料查詢語意不明確，以及 operational workflow 對查詢結果缺少大範圍變更 circuit breaker。

## 可回寫控制面

| 控制面                            | 這次事故暴露的缺口                                          | 回寫方向                                                               |
| --------------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------- |
| API schema                        | boolean-like query 參數語意不明確                           | 將狀態查詢參數標準化，錯誤或空值直接拒絕，不進入危險預設路徑           |
| Desired / actual state 分離       | customer configuration 與 operational action 混在同一資料面 | 引入 snapshot / staged deployment，讓壞資料可快速回到 known-good state |
| 大範圍 withdrawal circuit breaker | cleanup 任務可一次影響大量 prefixes                         | 對 prefix withdrawal / deletion 設速率、數量與健康訊號閘門             |
| Staging 與 mock data              | 測試資料未覆蓋 task-runner 自主操作情境                     | 補 production-like state mutation 測試，而不只測 customer journey      |
| Incident intake                   | 1.1.1.1 異常成為早期觀察點                                  | 將共享基礎服務異常納入控制面事故快速升級條件                           |
| Evidence write-back               | 恢復分成 dashboard 自助、資料修復、global rollout 多條路    | 回寫 decision log 與 evidence package，保留每種狀態的恢復判準          |

## 下一步路由

- 控制面資料品質： [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)
- 規則推送安全閘門： [6.24 Rule Rollout Safety Gate](/backend/06-reliability/rule-rollout-safety-gate/)
- 變更安全邊界： [6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)
- 驗證證據交接： [6.23 Verification Evidence Handoff](/backend/06-reliability/verification-evidence-handoff/)
- 事故決策紀錄： [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)
- 證據回寫流程： [8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)

## 引用源

- [Cloudflare outage on February 20, 2026](https://blog.cloudflare.com/cloudflare-outage-february-20-2026/)
