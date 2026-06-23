---
title: "6.5 失敗模式預判（Pre-mortem 與 FMEA）"
date: 2026-04-24
description: "用 pre-mortem 反向推導失敗路徑、用 FMEA 分類軸評估驗證缺口，把可靠性盲區變成可排序的改善輸入"
weight: 5
tags: ["backend", "reliability"]
---

## 概念定位

失敗模式預判是在變更上線前，主動尋找驗證覆蓋的缺口。責任是把「我們漏掉了什麼」從事後驚訝變成事前盤點。

這一頁處理的是驗證邊界。當某個環節一旦失效就會放大事故，pre-mortem 與 FMEA 的工作是提前把那個環節標出來，讓團隊能在上線前決定是補驗證、收窄範圍還是延後變更。

## 核心判讀

驗證缺口的核心問題是變更是否被差異化控制、回復路徑是否經過驗證。

重點訊號包括：

- 高風險變更是否有獨立 gate
- 負載模型是否包含失敗流量特徵
- 故障演練是否覆蓋 partial failure 與連鎖失效
- rollback 與 runbook 是否有時限驗證

## Pre-mortem 流程

Pre-mortem 的核心假設是「這個變更已經在 production 造成事故」，然後反向推導可能的失敗路徑。這個方法的價值在於成本極低（只需要一次結構化討論）但能暴露驗證盲區。

流程分四步：

**列出依賴與資料路徑**：把變更涉及的服務依賴、資料寫入路徑與外部呼叫畫出來。重點是找出「變更直接或間接觸及的系統邊界」，包括 schema、config、依賴服務版本與流量路由。

**對每條路徑問失敗影響**：對每條路徑假設失敗，判斷影響範圍。問的是「如果這條路徑斷了 / 慢了 / 回傳錯誤，影響會擴散到哪裡」。影響範圍包含直接依賴方、上游呼叫者、使用者可見行為與資料一致性。

**判斷現有驗證覆蓋**：對每條失敗路徑，檢查現有 CI、load test、chaos experiment、contract test 是否能攔住這個失敗。重點是找出「我們認為有覆蓋但實際沒覆蓋」的路徑 — 例如 CI 有 unit test 但沒有 integration test 覆蓋跨服務呼叫，或 load test 有 throughput 驗證但沒有 retry storm 場景。

**識別驗證缺口並路由**：未覆蓋的失敗路徑進入兩條路由。上線前能補的缺口回寫到 [6.19 reliability readiness review](/backend/06-reliability/reliability-readiness-review/)，作為上線前檢查項目。上線前補不了的缺口回寫到 [6.21 reliability debt backlog](/backend/06-reliability/reliability-debt-backlog/)，作為可排序的改善項目。

Pre-mortem 的常見失效是流程走了但結論沒路由。當缺口被列出但沒有 owner、沒有 deadline、沒有連到 readiness review 或 debt backlog，pre-mortem 就只是會議紀錄。

## FMEA 分類軸

Failure Mode and Effects Analysis 按失效模式分類驗證缺口。按模式分類的好處是讓團隊能判斷「缺口屬於哪一類」，然後沿對應章節的路由去補。

### Gate failure

Release gate 缺少高風險變更的差異化控制。當所有變更走同一條 CI pipeline、同一套 gate 門檻，高風險變更（schema migration、payment path、config rollout）的驗證強度跟日常小改動相同，gate 實質上對高風險變更無效。

判讀條件：高風險變更是否有獨立的 gate 流程；gate 門檻是否隨變更風險等級調整。[Microsoft 的變更治理實踐](/backend/06-reliability/cases/microsoft/change-management-and-reliability-governance/)把變更按風險分層，高風險變更需要更嚴的放行條件與更完整的驗證路徑。回到 [6.8 release gate](/backend/06-reliability/release-gate/) 補差異化門檻。

### Load failure

Workload model 沒覆蓋失敗流量特徵。壓測模型通常反映正常流量，但事故時的流量形狀完全不同：retry storm 放大請求量、cascade [timeout](/backend/knowledge-cards/timeout/) 佔住連線、queue backlog 堆積改變消費節奏。當壓測模型只包含正常流量，通過壓測不代表系統能承受失敗流量。

判讀條件：workload model 是否包含 retry 放大、timeout cascade 與 queue 堆積場景。回到 [6.2 load test](/backend/06-reliability/load-testing/) 補失敗流量模型。

### Recovery failure

Rollback 或 DR 路徑在事故前沒被驗證過。團隊假設 rollback 可用，但 schema 已經不向下相容；團隊假設 failover 可用，但 failover config 跟 production 已經漂移。recovery failure 的特徵是「有計畫但沒跑過」。

判讀條件：rollback 是否在過去 90 天被 rehearsal 驗證過；DR failover config 是否跟 production 同步。回到 [6.7 DR / rollback rehearsal](/backend/06-reliability/dr-rollback-rehearsal/) 建立定期驗證節奏。

### Detection failure

告警延遲或缺失，問題被使用者先發現。當 SLO alert 覆蓋不足、dashboard 缺少關鍵路徑的訊號、或告警門檻設定過寬，團隊的 MTTD（mean time to detect）會拉長到使用者回報之後。detection failure 讓所有下游反應（止血、升級、溝通）都延遲。

判讀條件：關鍵路徑的 MTTD 是否在可接受範圍；SLO alert 是否覆蓋使用者可見的服務承諾。[Netflix 的 chaos 實踐](/backend/06-reliability/cases/netflix/steady-state-chaos-and-fit/)把 [steady state](/backend/knowledge-cards/steady-state/) 定義放在驗證的第一步 — 沒有穩態定義，告警就無法判斷系統是否偏離正常，detection 變成盲目。回到 [04 可觀測性](/backend/04-observability/) 補訊號覆蓋。

## 失敗模式嚴重度評估

FMEA 傳統用 severity × probability × detectability 三軸評估風險優先序。在可靠性驗證的語境中，這三軸可以簡化為可操作判讀：

| 軸            | 判讀問題                                                             | 量測方式                                 |
| ------------- | -------------------------------------------------------------------- | ---------------------------------------- |
| Severity      | 失效的 [blast radius](/backend/knowledge-cards/blast-radius/) 有多大 | 單服務 / 跨服務 / 跨區 / 跨租戶          |
| Probability   | 這個失效路徑多常被觸及                                               | 變更頻率、歷史事故率、依賴穩定度         |
| Detectability | 問題被發現需要多久                                                   | MTTD、alert 覆蓋率、synthetic probe 頻率 |

三軸的交叉決定驗證投資順序：high severity + high probability + low detectability 的缺口最先處理。反過來，low severity + low probability 的缺口可以先記錄在 [6.21 reliability debt](/backend/06-reliability/reliability-debt-backlog/)，不需要立即補驗證。

嚴重度評估的陷阱是把評分當目標。三軸的責任是排序驗證投資，讓團隊在有限時間內先補最危險的缺口。當評分本身變成需要維護的文件，評估的維護成本會超過它帶來的判讀價值。

## 服務環節問題地圖

| 環節         | 失效分類 | 主要問題                           | 案例                                                                                                                                             |
| ------------ | -------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Release Gate | Gate     | 高風險變更缺少差異化 gate          | [TeamCity 2023](/backend/07-security-data-protection/red-team/cases/supply-chain/teamcity-cve-2023-42793-ci-entrypoint/)                         |
| 負載驗證模型 | Load     | 測試流量與實際失敗節奏脫鉤         | [WS_FTP 2023](/backend/07-security-data-protection/red-team/cases/data-exfiltration/progress-wsftp-2023-file-service-breach/)                    |
| 失敗模式演練 | Recovery | partial failure 與連鎖失效覆蓋不足 | [Change Healthcare 2024](/backend/07-security-data-protection/red-team/cases/data-exfiltration/change-healthcare-2024-ops-impact/)               |
| 回復路徑驗證 | Recovery | rollback 與 runbook 缺少時限驗證   | [VMware ESXiArgs 2023](/backend/07-security-data-protection/red-team/cases/data-exfiltration/vmware-esxiargs-2023-ransomware-recovery-pressure/) |

TeamCity 案例暴露的是 gate failure：CI 入口本身被繞過時，後續所有 gate 都失效。判讀條件是 CI pipeline 的存取控制是否被納入驗證範圍，而不只是 pipeline 內容。

Change Healthcare 案例暴露的是 recovery failure：事故影響擴散到營運層面時，技術回復完成不代表服務恢復。判讀條件是 DR plan 是否涵蓋跨系統依賴的恢復順序，而不只是單一服務的 rollback。

## 案例對照

| 情境                       | 失效分類  | 判讀                         | 路由章節                                                           |
| -------------------------- | --------- | ---------------------------- | ------------------------------------------------------------------ |
| CI 綠燈但線上回滾率上升    | Gate      | gate 覆蓋與實際風險未對齊    | [6.8 release gate](/backend/06-reliability/release-gate/)          |
| 壓測通過但事故時連鎖降速   | Load      | 負載模型缺少失敗流量特徵     | [6.2 load test](/backend/06-reliability/load-testing/)             |
| 演練記錄完整但回復時間偏長 | Recovery  | 演練內容與實戰決策節奏不一致 | [6.7 DR rehearsal](/backend/06-reliability/dr-rollback-rehearsal/) |
| 使用者先於告警發現問題     | Detection | 訊號覆蓋不足或門檻過寬       | [04 可觀測性](/backend/04-observability/)                          |

[Google 的 error budget 政策](/backend/06-reliability/cases/google/error-budget-policy-and-release-gating/)把 gate 門檻跟 budget 消耗綁在一起：budget 健康時走正常 gate，budget 快速消耗時提高門檻。這種做法讓 gate failure 的偵測從「事後觀察回滾率」轉成「事前看 budget 消耗趨勢」。

[Shopify 的 resiliency matrix](/backend/06-reliability/cases/shopify/pod-architecture-and-resiliency-matrix/) 是 FMEA 的制度化形式：service × failure mode 的矩陣，每格填入防護狀態（covered / gap / in-progress），gap 欄直接成為 game day 的演練題目。這種做法讓 FMEA 從一次性盤點變成持續維護的驗證清單。

## 跟其他章節的整合

Pre-mortem 與 FMEA 的產出需要路由到三個下游：

- [6.19 reliability readiness review](/backend/06-reliability/reliability-readiness-review/)：上線前能補的缺口進入 readiness checklist
- [6.20 experiment safety boundary](/backend/06-reliability/experiment-safety-boundary/)：需要驗證的失敗假設轉成 chaos / load test 的實驗設計
- [6.21 reliability debt backlog](/backend/06-reliability/reliability-debt-backlog/)：上線前補不了的缺口進入可排序的改善 backlog

路由清晰度決定 pre-mortem 的實際價值。當缺口被識別但沒有路由到具體章節的具體動作，pre-mortem 就只是風險清單。

## 判讀訊號

| 訊號                                       | 判讀條件                                                  |
| ------------------------------------------ | --------------------------------------------------------- |
| 高風險變更走一般 gate、無差異化控制        | gate failure — 回到 6.8 確認是否有風險分層                |
| 壓測通過但 production 事故來自 retry/queue | load failure — workload model 是否涵蓋失敗流量            |
| rollback 路徑上次驗證超過 90 天            | recovery failure — 回到 6.7 確認 rehearsal 節奏           |
| 事故 MTTD 超過 SLO window                  | detection failure — 回到 04 確認 alert 覆蓋與門檻         |
| pre-mortem 有做但缺口無 owner              | 流程失效 — 結論沒路由到 6.19 或 6.21                      |
| FMEA 評分定期更新但驗證沒跟著動            | 評估與行動脫鉤 — 評分的責任是排序投資，改完要回寫驗證狀態 |

## 交接路由

- [6.2 load test](/backend/06-reliability/load-testing/)：補失敗流量模型（retry / timeout / queue）
- [6.7 DR / rollback rehearsal](/backend/06-reliability/dr-rollback-rehearsal/)：補回復路徑驗證
- [6.8 release gate](/backend/06-reliability/release-gate/)：補高風險變更的差異化 gate
- [6.19 reliability readiness review](/backend/06-reliability/reliability-readiness-review/)：pre-mortem 缺口轉成上線前檢查
- [6.20 experiment safety boundary](/backend/06-reliability/experiment-safety-boundary/)：失敗假設轉成實驗設計
- [6.21 reliability debt backlog](/backend/06-reliability/reliability-debt-backlog/)：未修缺口進入可排序 backlog
- [04 可觀測性](/backend/04-observability/)：detection failure 回到訊號覆蓋
- [6.23 verification evidence handoff](/backend/06-reliability/verification-evidence-handoff/)：FMEA 結論作為 readiness 證據
- [08 事故處理](/backend/08-incident-response/)：pre-mortem 假設在事故中被驗證時回寫
