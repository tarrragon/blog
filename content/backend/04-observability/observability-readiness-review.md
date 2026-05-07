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

Observability readiness review 的價值在於把「事故時才會被問到的問題」提前成上線條件。服務進 production 前，團隊需要先確認訊號能回答三件事：哪裡出問題、影響到誰、下一步由誰處理。

## 概念定位

Observability readiness review 是把「訊號是否足以支援操作」變成上線前檢查的流程，責任是讓服務進入 production 前已具備基本診斷能力。

這一頁處理的是準備度。工具已存在時，仍需要確認訊號是否對應使用者旅程、依賴邊界、事故分級與復盤證據。

readiness review 不等於打勾清單。它是一次跨角色對齊：服務團隊確認事件語意，平台團隊確認採集與查詢路徑，on-call 確認事故前 10 分鐘真的能定位。三者同時成立，才算可操作準備度。

## 適用情境

Observability readiness review 適合放在服務生命週期的高風險節點。這些節點共同特徵是：一旦變更進入 production，第一次異常就會依賴既有訊號做判讀。

| 情境       | 檢查重點                         | 缺口代價                     |
| ---------- | -------------------------------- | ---------------------------- |
| 新服務上線 | 核心旅程、依賴、owner 是否可觀測 | 事故初期只能靠人工猜測       |
| 重大變更   | 新 queue、新依賴、新 flag 的訊號 | 新風險進 production 後才暴露 |
| 架構拆分   | trace、correlation、service name | 事件鏈跨服務後斷裂           |
| 演練前     | chaos、load、DR 行為是否可被看見 | 演練結果缺少可驗證證據       |
| 事故後     | 復盤缺口是否回寫成新訊號         | 同類事故仍以相同盲區重演     |

新服務上線時，readiness review 的責任是確認基本診斷能力已經存在。典型服務至少要能從 request、tenant、region、dependency 與錯誤分類回到同一條事件鏈，讓 on-call 能在前 10 分鐘判斷影響範圍。

重大變更時，readiness review 的責任是確認變更帶來的新風險已有訊號。加入新的外部 API、queue、background job、feature flag 或資料同步流程，都會增加新的失效面；每個失效面都應有對應 log、metric、trace 或 alert。

演練前，readiness review 的責任是確認驗證行為能被觀測。chaos experiment、load test 或 DR drill 需要同時產生故障與判讀證據，讓團隊能確認 [steady state](/backend/knowledge-cards/steady-state/)、blast radius 與回復狀態。

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

## Review 流程

Readiness review 的流程是從使用者旅程走向操作路由。先從服務承諾的體驗開始，再反推工具與訊號清單，才能讓監控資產對應事故時的實際判讀。

1. 定義核心旅程與失敗後果。
2. 對每個旅程列出依賴、async workflow 與資料寫入點。
3. 為每個失效點指定 log、metric、trace 或 dashboard。
4. 驗證 alert 是否連到 owner、runbook 與下一步動作。
5. 標記尚未補齊的訊號缺口，決定是否阻擋上線或納入 follow-up。

核心旅程是 readiness review 的錨點。購物服務的核心旅程可能是 checkout、payment、order confirmation；內容平台可能是 upload、publish、read path；B2B API 可能是 authentication、request processing、webhook delivery。訊號需要優先對到這些旅程，再補 CPU、memory 與 pod restart 等資源層訊號。

依賴圖是 readiness review 的第二層。每個資料庫、cache、broker、third-party API、object storage 與 internal service 都應能被定位為 upstream 或 downstream，並且在 trace、metric 或 log 中留下可查詢欄位。

操作路由是 readiness review 的交付物。當 alert 觸發時，on-call 需要知道先看哪個 dashboard、用哪個 query、找哪個 owner、用哪個 runbook、何時升級到 incident commander。

## 判讀訊號

- 服務上線 checklist 有監控項目，但沒有事故判讀欄位
- 新依賴上線後，dashboard 看不到 upstream / downstream 影響
- alert 觸發後仍需要人工 grep 多個系統拼事件鏈
- chaos 或 DR 演練產生故障，但 04 訊號沒有反映出預期現象
- 事故復盤 action item 反覆要求「補監控」

在真實服務中，最常見的 readiness 缺口是工具已存在，但工具沒有對到決策。例如 alert 可以 page on-call，但查詢第一步就要跨三個系統手動對帳，代表 readiness 還停在可見層，尚未進入可操作層。

## 控制面

Readiness review 的控制面是把檢查結果轉成可執行決策。每個缺口都要被分類為阻擋、降級接受或後續改善，並且留下 owner 與期限。

| 缺口類型 | 判斷方式                        | 處理路由                                 |
| -------- | ------------------------------- | ---------------------------------------- |
| 阻擋     | 影響核心旅程、事故時無替代判讀  | 暫停上線，補 04 訊號或 06 readiness      |
| 降級接受 | 風險可被 runbook 或人工查證承接 | 標記限制，接到 08 intake 與 decision log |
| 後續改善 | 不影響首輪定位，但影響長期治理  | 進入 04.8 signal governance loop         |
| 淘汰整理 | 舊 dashboard 或 alert 干擾判讀  | 進入 4.18 operating model                |

阻擋條件應該以「事故時是否能決策」為核心。核心旅程 SLI、request correlation、upstream / downstream 分辨能力與 alert owner 都是第一次事故能否被接住的基本條件。

降級接受需要明確寫出限制。若某個低流量背景任務暫時缺 trace，但有 log query、DLQ dashboard 與人工 replay 流程可以承接，團隊可以接受短期限制；限制需要進入 [incident decision log](/backend/knowledge-cards/incident-decision-log/)，避免事中被誤讀為完整訊號。

後續改善適合處理長期品質問題。dashboard 可用但查詢成本過高、alert 可行但 noise 偏高、欄位命名需要統一，這些缺口適合進入 signal governance，讓上線決策與長期治理分流。

## 常見反模式

Observability readiness 的反模式通常來自把「有監控」誤當成「可操作」。監控存在只是起點，能支援判讀、路由與回復才是 readiness。

| 反模式                 | 表面現象                           | 修正方向                        |
| ---------------------- | ---------------------------------- | ------------------------------- |
| 事後補 dashboard       | 事故發生後才知道缺哪些面板         | 把核心旅程面板列為上線條件      |
| 告警只有通知           | on-call 收到 page 後仍需重新找證據 | alert 必須帶 owner 與 runbook   |
| trace 需要人工拼 log   | 跨服務路徑靠 request id 手動對回   | 統一 trace context 與 log 欄位  |
| readiness 只看平台工具 | 平台 green，但服務旅程不可判讀     | 從 user journey 反推訊號需求    |
| checklist 無阻擋條件   | 每次都勾選通過，但缺口持續存在     | 定義 block / accept / follow-up |

事後補 dashboard 的風險是把第一次事故變成探索行為。事故期間的主要工作應是止血與決策；如果團隊還在建立第一個查詢、猜欄位語意、找 owner，代表 readiness 沒有完成。

告警只有通知會把壓力丟給 on-call。有效 alert 應該同時提供症狀、範圍、第一個查詢入口與下一步路由，讓值班者能直接進入判讀流程。

## 與 06 和 08 的關係

Observability readiness 是可靠性驗證與事故處理的輸入層。06 需要用它判斷驗證前提是否成立，08 需要用它判斷事故 evidence 是否足以啟動流程。

在 06 中，readiness 缺口會影響 load test、chaos、DR drill 與 release gate。驗證行為需要可觀測訊號支撐，測試結果才足以證明系統維持在可接受狀態內。

在 08 中，readiness 缺口會影響 severity trigger、incident intake 與 decision log。若 evidence 不完整，事故指揮需要先標記資料限制，再決定是否升級、降級或等待更多證據。

## 交接路由

- 04.1 log schema：補事件關聯欄位
- 04.2 metrics：補服務健康與容量指標
- 04.3 tracing：補跨服務與 async context
- 04.4 dashboard / alert：補操作入口與通知條件
- 06.19 reliability readiness：把觀測準備度納入上線前門檻
- 08.18 incident intake：把訊號接進事故 intake 與 evidence triage
