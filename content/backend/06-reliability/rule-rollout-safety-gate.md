---
title: "6.24 規則推送安全閘門"
date: 2026-05-07
description: "把規則、策略與控制面配置推送從部署步驟升級為可靠性 gate，避免小變更在秒級擴散成全網事故。"
weight: 24
tags: ["backend", "reliability", "release-gate", "control-plane"]
---

## 概念定位

規則推送安全閘門（rule rollout safety gate）的核心責任是防止控制面錯誤快速擴散到資料面。這個閘門是補上「規則與配置類變更」特有風險，跟既有 release gate 互補而非取代：變更體積小、覆蓋範圍大、擴散速度快。

當變更屬於 WAF rule、routing policy、token/policy、或 Addressing API 相關設定時，判讀重點從程式碼正確性轉為擴散控制。這類變更即使 diff 很短，也可能在數十秒內影響跨區域流量與多產品控制面。

## 適用場景

| 場景                         | 典型風險                         | 為何需要獨立 gate                    |
| ---------------------------- | -------------------------------- | ------------------------------------ |
| WAF / regex 規則更新         | 高計算成本規則拖垮 edge runtime  | CI 綠燈無法代表 runtime 成本安全     |
| Routing / BYOIP 相關設定變更 | prefix withdrawal 造成服務不可達 | 單一 API 查詢語意錯誤可全網擴散      |
| Token / policy 控制面變更    | 多產品授權連鎖失效               | shared dependency 失效會誤導排障路徑 |
| 共享控制面批次清理任務       | 批量誤刪或批量撤告               | 需要數量閘門與緊急停機機制           |

## 產業情境：遊戲服務的規則推送安全

遊戲的規則推送（平衡性調整、反作弊規則、賽季設定、經濟系統參數）有特殊的擴散特性：影響面是全體玩家、生效時機即時、且玩家行為會立刻適應規則變更。

規則推送的 blast radius 預設是全體在線玩家。一次平衡性調整會立刻改變所有正在進行的比賽的角色強度、裝備數值或技能效果。跟一般 feature flag 的 percentage rollout 不同，遊戲平衡性需要所有玩家看到相同規則，否則同場比賽的公平性會被破壞。

推送時機需要跟 match lifecycle 對齊。在進行中的比賽套用新規則會造成不公平 — 某隊在舊規則下建立的優勢可能在新規則下消失。安全做法是在 match boundary（比賽開始或結束時）切換，讓新規則只套用到新開始的比賽。這要求規則推送系統能區分「已開始的 match」和「即將開始的 match」。

回退條件需要綁定遊戲特有的 KPI。active player count 下降超過門檻、match completion rate 異常降低（玩家中途離開）、player report rate 上升（玩家回報異常體驗）、in-game economy anomaly（虛擬貨幣或道具流通量異常）都是規則推送出問題的訊號。這些 KPI 的 feedback loop 比一般服務長 — 玩家行為的適應需要數小時到數天才會穩定，短窗觀察可能漏掉延遲暴露的問題。

反作弊規則的推送有額外約束：規則內容本身是機密的，推送失敗後不能在 log 或 alert 中暴露規則細節，回退也必須在不洩漏偵測邏輯的前提下進行。

## Gate 檢查層

| 層級              | Gate 問題                                    | 不通過訊號                              |
| ----------------- | -------------------------------------------- | --------------------------------------- |
| Query / API 語意  | 查詢參數有沒有安全預設與錯誤拒絕策略         | 空參數回傳全量、模糊布林語意            |
| Rule 計算成本     | 規則是否通過代表性 payload 成本檢查          | 單一規則可造成 CPU 熱點                 |
| 推送策略          | 是否採分群 rollout 並設即時回退條件          | 一次推全域、無分區觀測閘門              |
| Withdrawal 限速   | 批次撤告 / 刪除是否有數量與速率限制          | 單次操作可影響大量 prefixes 或 bindings |
| Shared dependency | 是否識別跨產品共享控制點                     | 多產品同時異常卻無 shared root 判讀     |
| Evidence 與回寫   | 事故後是否可回放決策、查證恢復路徑與狀態差異 | 決策只留結論，缺假設與驗證證據          |

## 判讀訊號

- 控制面變更後，多區域同時出現 5xx / timeout / auth 失敗
- 指標在秒級惡化，且與最新規則或 policy 變更高度同時
- 回退後短時間明顯回穩，顯示變更與故障高度關聯
- 部分服務可自助恢復、部分服務需人工修復，代表狀態損壞分層
- 事故中出現「每個產品都在修自己的症狀」，代表 shared dependency 沒被先識別

## 最低可執行 Gate

1. **變更分類**：將規則/配置/控制面 API 變更標為 `high-blast-radius change`。
2. **語意檢查**：對 query 參數、空值與預設行為做拒絕式驗證。
3. **成本檢查**：用代表性 payload 跑 rule-level CPU / latency 測試。
4. **分批推送**：至少分成小流量群組與全量兩階段，且每階段有回退條件。
5. **撤告保護**：對 withdrawal / delete 設速率與數量上限，超限自動中止。
6. **決策紀錄**：事故期間保留假設、證據、回退門檻、owner 與狀態差異。

## 反模式

| 反模式                      | 風險結果                      | 修法                                  |
| --------------------------- | ----------------------------- | ------------------------------------- |
| 把規則推送當一般配置        | 低估擴散速度與影響面          | 強制走高風險變更 gate                 |
| 只看 CI / lint              | 無法捕捉 runtime 計算成本風險 | 補 rule replay 與成本基線             |
| 全域一次推送                | 擴散太快，回退窗口太短        | 改 staged rollout + 即時回退閘門      |
| 事故後只寫事後摘要          | 無法復盤決策與恢復路徑        | 補 decision log + evidence package    |
| 未分離 desired/actual state | 壞狀態難以回到已知穩定點      | 引入 snapshot 與 staged state restore |

## 案例回扣

- [Cloudflare 2019 Regex CPU Outage](/backend/08-incident-response/cases/cloudflare/2019-regex-cpu-outage/)
- [Cloudflare 2023 Control Plane Token Incident](/backend/08-incident-response/cases/cloudflare/2023-control-plane-token-incident/)
- [Cloudflare 2026 BYOIP BGP Withdrawal](/backend/08-incident-response/cases/cloudflare/2026-byoip-bgp-withdrawal/)

這三個案例對應同一個上位問題：控制面小變更如何在短時間擴散成全網事故。不同事故只是擴散路徑不同，gate 核心都是「先限制擴散、再修復功能」。

## 下一步路由

- `04`： [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)
- `06`： [6.8 Release Gate](/backend/06-reliability/release-gate/)
- `06`： [6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)
- `06`： [6.23 Verification Evidence Handoff](/backend/06-reliability/verification-evidence-handoff/)
- `08`： [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)
- `08`： [8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)
