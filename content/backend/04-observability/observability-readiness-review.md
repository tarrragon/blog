---
title: "4.16 Observability Readiness Review"
date: 2026-05-02
description: "在服務上線、重大變更與演練前檢查 log / metric / trace / alert 是否可支援事故判讀"
weight: 16
---

## 大綱

- readiness review 的責任：在 production 前確認訊號能支援分級、定位、回復與復盤
- 檢查面向：[log schema](/backend/knowledge-cards/log-schema/)、[metrics](/backend/knowledge-cards/metrics/)、[trace context](/backend/knowledge-cards/trace-context/)、[dashboard](/backend/knowledge-cards/dashboard/)、[alert](/backend/knowledge-cards/alert/)
- 上線前判準：核心 user journey 是否有 SLI、錯誤是否有 correlation key、依賴是否可追蹤
- 變更前判準：新依賴、新 queue、新 feature flag 是否帶出新訊號需求
- 演練前判準：game day / chaos / DR drill 是否能被 04 訊號觀察
- 跟 06 的交接：readiness 缺口進入 reliability readiness / release gate
- 跟 08 的交接：readiness 缺口影響 severity trigger、runbook 與 decision log
- 反模式：服務先上線、事故後才補 dashboard；alert 有通知但缺定位欄位；trace 需要人工對回 log

Observability readiness review 的價值在於把「事故時才會被問到的問題」提前。服務上線後才補訊號，通常代表第一次事故會被用來探索系統而不是處理事故；readiness review 讓團隊先確定至少能回答三件事：哪裡出問題、影響到誰、下一步由誰處理。

## 概念定位

Observability readiness review 是把「訊號是否足以支援操作」變成上線前檢查的流程，責任是讓服務進入 production 前已具備基本診斷能力。

這一頁處理的是準備度。工具已存在時，仍需要確認訊號是否對應使用者旅程、依賴邊界、事故分級與復盤證據。

readiness review 不等於打勾清單。它是一次跨角色對齊：服務團隊確認事件語意，平台團隊確認採集與查詢路徑，on-call 確認事故前 10 分鐘真的能定位。三者同時成立，才算可操作準備度。

## 核心判讀

判讀 observability readiness 時，先看服務的核心旅程是否有訊號，再看事故時能否從症狀走到原因。

重點訊號包括：

- 核心 user journey 是否有 [SLI/SLO](/backend/knowledge-cards/sli-slo/) 與 error rate
- log 是否有 [request id](/backend/knowledge-cards/request-id/)、[trace id](/backend/knowledge-cards/trace-id/) 與 tenant 欄位
- trace 是否覆蓋同步、async、queue 與 background job 邊界
- dashboard 是否能支援 on-call 的前 10 分鐘判讀
- alert 是否能連到 [runbook](/backend/knowledge-cards/runbook/) 與 owner

| 檢查面向 | 最小可用判準                                | 常見失真                           |
| -------- | ------------------------------------------- | ---------------------------------- |
| 事件關聯 | request / trace / tenant 可串成同一條事件鏈 | 欄位命名不一致、跨服務拼接失敗     |
| 服務健康 | SLI 與 error rate 能反映核心旅程            | 指標只反映系統資源、不反映用戶結果 |
| 路徑可視 | trace 能覆蓋 sync + async + queue           | background job 與 queue 邊界斷鏈   |
| 操作入口 | dashboard / alert 能支撐前 10 分鐘          | 告警有通知、沒有定位與下一步       |

## 判讀訊號

- 服務上線 checklist 有監控項目，但沒有事故判讀欄位
- 新依賴上線後，dashboard 看不到 upstream / downstream 影響
- alert 觸發後仍需要人工 grep 多個系統拼事件鏈
- chaos 或 DR 演練產生故障，但 04 訊號沒有反映出預期現象
- 事故復盤 action item 反覆要求「補監控」

在真實服務中，最常見的 readiness 缺口不是「沒有工具」，而是「工具沒有對到決策」。例如 alert 可以 page on-call，但查詢第一步就要跨三個系統手動對帳，代表 readiness 還停在可見而不是可操作。

## 交接路由

- 04.1 log schema：補事件關聯欄位
- 04.2 metrics：補服務健康與容量指標
- 04.3 tracing：補跨服務與 async context
- 04.4 dashboard / alert：補操作入口與通知條件
- 06.19 reliability readiness：把觀測準備度納入上線前門檻
- 08.18 incident intake：把訊號接進事故 intake 與 evidence triage
