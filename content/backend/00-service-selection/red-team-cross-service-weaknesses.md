---
title: "0.11 攻擊者視角（紅隊）：跨服務弱點判讀總表"
date: 2026-04-24
description: "用攻擊面、可觀察訊號與失敗代價，建立 backend 選型前的弱點盤點框架"
weight: 11
---

跨服務紅隊判讀的核心目標是把「哪裡最容易被打穿」先標出來，再決定服務能力的補強順序。這裡的紅隊是「攻擊者視角的風險檢查方法」：用攻擊者可能採取的路徑反向驗證系統設計。這份總表維持純概念層，不進入實作細節，重點是先回答四件事：暴露面在哪裡、弱點訊號長什麼樣、失敗代價是什麼、最低控制面要先有哪些。

## 【總表】服務類型與弱點判讀

| 服務類型 | 常見弱點 | 可觀察訊號 | 失敗代價 | 最低控制面 |
| --- | --- | --- | --- | --- |
| [database](../knowledge-cards/database/) | 越權查詢、交易邊界混亂、schema 變更風險 | 權限模型複雜、跨租戶查詢、migration 頻繁 | 資料錯誤、資料洩漏、長時間修復 | [authorization](../knowledge-cards/authorization/)、[transaction boundary](../knowledge-cards/transaction-boundary/)、[audit log](../knowledge-cards/audit-log/) |
| cache / [read model](../knowledge-cards/read-model/) | 資料陳舊、快取污染、索引暴露 | hit rate 波動、回源突增、欄位暴露不一致 | 錯誤決策、客訴、壓力擴散到主存 | [cache invalidation](../knowledge-cards/cache-invalidation/)、[data classification](../knowledge-cards/data-classification/)、[fallback](../knowledge-cards/fallback/) |
| message [queue](../knowledge-cards/queue/) / stream | 重複投遞、重放濫用、毒訊息擴散 | [consumer lag](../knowledge-cards/consumer-lag/)、[DLQ](../knowledge-cards/dead-letter-queue/)、重試風暴 | 重複執行、狀態偏移、恢復時間拉長 | [idempotency](../knowledge-cards/idempotency/)、[retry budget](../knowledge-cards/retry-budget/)、[replay runbook](../knowledge-cards/replay-runbook/) |
| observability | 盲區告警、敏感資料進 log、追蹤斷點 | 告警無法定位、trace 斷鏈、log 欄位失衡 | 修復延遲、誤判、資安風險提升 | [metrics](../knowledge-cards/metrics/)、[trace](../knowledge-cards/trace/)、[log schema](../knowledge-cards/log-schema/)、[runbook](../knowledge-cards/runbook/) |
| deployment / network entry | 隱藏入口、錯誤設定、切換窗口失控 | readiness 不穩、error rate 突增、unknown endpoint 被命中 | 擴散式故障、服務中斷、恢復成本升高 | [readiness](../knowledge-cards/readiness/)、[graceful shutdown](../knowledge-cards/graceful-shutdown/)、[WAF](../knowledge-cards/waf/)、[release gate](../knowledge-cards/release-gate/) |

## 【判讀】攻擊者視角總表在選型流程的位置

攻擊者視角總表放在產品需求與服務實體之間。流程上先做需求分類，再用這份總表檢查弱點與代價，最後才進入產品比較。這個順序能讓選型討論同步納入攻擊面與操作成本，避免把風險留到上線後才處理。

## 【判讀】弱點討論要對齊成本模型

弱點判讀的核心價值是提早看見操作成本。若只看開發速度，常見結果是上線後才補 [runbook](../knowledge-cards/runbook/)、權限分級、告警路由與備援切換。把弱點表納入選型初期，可以同時估算人力成本、容量成本與事故成本，讓服務能力與團隊負擔一起被評估。

## 【下一步】對應模組

- 資料層弱點路徑：模組一 database
- 訊息層弱點路徑：模組三 message queue
- 平台與入口弱點路徑：模組五 deployment platform
- 可觀測性弱點路徑：模組四 observability
- 資安與紅隊弱點路徑：模組七 security / red-team
