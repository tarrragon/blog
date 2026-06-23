---
title: "6.4 chaos testing"
date: 2026-04-23
description: "把故障注入從工具操作升級成可驗證流程：先定義穩態，再按依賴類型設計注入、控制 blast radius 與收集證據"
weight: 4
tags: ["backend", "reliability"]
---

## 概念定位

[Chaos test](/backend/knowledge-cards/chaos-test/) 是在可控條件下主動注入故障，驗證系統是否能在真實依賴失效時維持 [steady state](/backend/knowledge-cards/steady-state/) 與可接受的 [blast radius](/backend/knowledge-cards/blast-radius/)。

這一頁關心的是失效時系統怎麼退化。chaos 的價值在於判讀系統收到故障後的退化行為是否符合預期。沒有先定義 steady state，chaos 只會變成故障展示，不會變成判讀工具。

## 核心判讀

判讀 chaos 的重點是對控制面、資料面與依賴鏈的回復能力做驗證，而不是單純證明服務死過一次。

重點訊號包括：

- 是否先定義 steady state 與成功條件
- 故障是否真的落在常見依賴與控制點
- [blast radius](/backend/knowledge-cards/blast-radius/) 是否可量測、可縮限
- recovery path 是否能在演練後被重播

## 故障注入的設計流程

一輪有效的 chaos 驗證從穩態定義開始。先知道系統正常時應維持什麼行為，再設計注入去測試這個行為是否可持續。

| 步驟              | 核心問題                   | 產出               |
| ----------------- | -------------------------- | ------------------ |
| 定義穩態          | 服務正常時應維持什麼行為   | 穩態指標與門檻     |
| 設計假設          | 失效發生後系統仍應維持什麼 | 可證偽假設         |
| 限制 blast radius | 實驗範圍怎麼控制           | 服務 / 區域 / 流量 |
| 設定停止條件      | 何時立即停止實驗           | abort trigger      |

穩態定義是整個流程的錨點。Netflix 的 chaos 實踐把 steady state 放在驗證循環的第一步 — 先定義穩態指標（[SLI](/backend/04-observability/sli-slo-signal/)、business KPI、queue lag），再用故障注入去測試這些指標是否能在壓力下維持。沒有穩態定義的故障注入只能產出「系統被打壞了」的結論，無法回答「系統是否按預期退化」。

假設設計決定實驗能學到什麼。好的假設會說明「當 [broker](/backend/knowledge-cards/broker/) 節點離線時，訊息消費延遲應在 30 秒內回線，checkout 成功率應維持在 [SLO](/backend/06-reliability/slo-error-budget/) 門檻內」，而不只是「關掉 broker 看看會怎樣」。假設越具體，實驗結果的判讀價值越高。

Blast radius 需要同時包含技術範圍與客戶範圍。技術範圍是 service、region、cluster、dependency；客戶範圍是 tenant、plan、traffic percentage 或 internal-only cohort。從最小範圍開始，逐步放大，每一步都要確認停止條件仍可執行。

停止條件讓實驗可控。當 SLO [burn rate](/backend/knowledge-cards/burn-rate/) 超門檻、customer impact 出現或 cost 異常上升時，實驗應立即終止。停止條件要連到可觀測訊號，不能靠臨場討論決定是否繼續。

## 注入類型與層次

故障注入按依賴類型分層。不同依賴的失效模式不同，預期退化也不同，實驗設計需要對應調整。

| 注入類型       | 打到的依賴                                                  | 預期退化                                                    | 結果可信條件                                                        |
| -------------- | ----------------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------- |
| Broker outage  | [broker](/backend/knowledge-cards/broker/) 節點或 partition | 消費延遲上升、DLQ 累積                                      | 流量接近 production pattern                                         |
| DB latency     | [database](/backend/knowledge-cards/database/) 連線或查詢   | 請求排隊、[timeout](/backend/knowledge-cards/timeout/) 觸發 | connection pool 配置與 production 一致                              |
| Node restart   | 應用節點                                                    | 短暫不可用、load balancer 切流                              | readiness probe 與 graceful shutdown 配置一致                       |
| Network jitter | 跨服務通訊                                                  | latency 抖動、retry 上升                                    | [jitter](/backend/knowledge-cards/jitter/) 模式接近真實 ISP / cloud |

Broker outage 驗證的是非同步依賴的容錯能力。當 broker 節點或 partition 不可用時，生產端應有 retry 與 fallback，消費端應能在恢復後 drain backlog 而不是 replay storm。測試時需要確認 DLQ 設定正確、消費 lag 有監控、恢復後的 [backpressure](/backend/knowledge-cards/backpressure/) 不會壓垮下游。

DB latency 驗證的是同步依賴在退化時的行為。延遲注入比完全斷線更接近真實故障 — production 常見的是 slow query、connection pool exhaustion 或 replica lag，而不是 database 完全離線。測試時需要確認 timeout 是否會級聯：一個慢查詢拖住連線，其他請求開始排隊，最終 thread pool 或 goroutine 耗盡。

Node restart 驗證的是服務在節點層級的恢復能力。graceful shutdown 是否正確 drain 連線、readiness probe 是否能阻止 load balancer 過早送流量、cold start 是否會因 cache miss 或 JIT warmup 造成短暫效能劣化。

Network jitter 驗證的是跨服務通訊的韌性。jitter 注入需要模擬真實的 latency distribution（長尾、間歇性），而不是固定延遲。測試時需要關注 retry 行為：固定 retry 在 jitter 環境下可能放大流量，需要搭配 [retry budget](/backend/knowledge-cards/retry-budget/) 控制。

### 注入粒度：instance-level vs request-path

故障注入有兩個主要粒度，適用場景不同。

Instance-level injection（如 Chaos Monkey）在節點層注入故障 — 關閉 instance、斷開網路、暫停程序。這個粒度驗證的是基礎設施韌性：load balancer 能否切流、auto-scaling 能否補位、graceful shutdown 能否完成。優點是簡單、接近真實硬體故障；缺點是粒度粗，無法精準驗證特定依賴路徑。

Request-path injection（如 FIT）在請求路徑層注入故障 — 對特定 API call、dependency request 或 service-to-service 通訊植入 timeout、error 或延遲。這個粒度驗證的是應用韌性：fallback 是否生效、circuit breaker 是否觸發、retry 是否安全。優點是精準、blast radius 小；缺點是需要更深的 instrumentation，建置成本較高。

兩者不互斥。instance-level injection 適合驗證基礎設施層的回復能力，request-path injection 適合驗證應用層的容錯邏輯。團隊可以從 instance-level 開始建立 chaos 習慣，再逐步引入 request-path injection 提升驗證精度。第三種粒度是 infrastructure-level injection（AZ failure / region failure），由 cloud provider 的 chaos 工具（如 AWS FIS、Azure Chaos Studio）支援，驗證的是跨 AZ 冗餘與 failover 路由。

## 執行時段與環境

故障注入的執行時段與環境直接影響驗證價值。

### Business hours vs off-peak

在 business hours 執行 chaos 能同時驗證系統韌性與團隊應變能力。人員在線可即時觀測、依賴流量接近真實、通訊鏈條（值班升級、跨團隊協作、內外部狀態更新）被完整測到。off-peak 雖然短期風險低，但測到的多是「工具可執行」，不是「服務在真實壓力下可承受」。

選擇 business hours 執行的前提是 guardrails 到位：時段限制在可支援的工作時間、blast radius 從小範圍開始、abort trigger 連到明確門檻、事後回寫進工程控制面。風險來自 guardrails 的缺失。

### Staging vs production

Staging 適合驗證工具整合與基礎假設：注入能否生效、dashboard 能否呈現訊號、stop condition 能否觸發。但 staging 與 production 之間通常存在環境漂移 — traffic pattern 不同、dependency 配置不同、[connection pool](/backend/knowledge-cards/connection-pool/) 大小不同、cache warmup 狀態不同。在 staging 通過的實驗，不能直接等同於 production 可承受。

Production chaos 的價值在於驗證真實依賴路徑。它需要從最小 cohort 開始（internal traffic、canary region、特定 tenant），搭配完整 stop condition 與 rollback path。Production chaos 需要 stop condition 作為安全網。團隊可以從簡單的 stop condition（如 error rate 超門檻就停止）起步，隨經驗累積逐步精細化。

## 證據結構與回寫

Chaos 實驗的產出是可決策的證據。當實驗結果能直接回答「這個依賴的容錯能力是否足夠」，chaos 才從測試活動升級為可靠性控制面。

| 證據欄位             | 核心問題                       | 決策用途                     |
| -------------------- | ------------------------------ | ---------------------------- |
| Steady-state impact  | 注入後穩態指標是否維持         | 判斷容錯能力是否符合預期     |
| Abort trigger record | 停止條件是否被觸發、何時觸發   | 判斷是否需要凍結或回退       |
| Fallback result      | 降級路徑是否可用、恢復是否收斂 | 判斷事故時能否安全止血       |
| Dependency drift     | 受影響依賴是否落在預期範圍     | 判斷 blast radius 是否可接受 |

Steady-state impact 是最核心的證據欄位。它回答的問題是「系統在故障期間是否維持了服務承諾」。若 [SLI](/backend/04-observability/sli-slo-signal/) 維持在 [SLO](/backend/06-reliability/slo-error-budget/) 門檻內，代表容錯機制有效；若偏離，需要記錄偏離幅度、持續時間與影響範圍。

Abort trigger record 讓團隊知道 stop condition 是否可執行。若停止條件被觸發但執行延遲，代表觀測或通訊鏈條有缺口；若停止條件沒被觸發但影響已擴大，代表門檻設定需要校準。

這四個欄位接到 [6.23 verification evidence handoff](/backend/06-reliability/verification-evidence-handoff/) 後，可直接成為 [6.8 release gate](/backend/06-reliability/release-gate/) 的放行輸入。release decision 從「主觀討論」轉成「政策驅動」：有證據支持容錯能力 → 放行；abort 被觸發 → 凍結並修復；fallback 失敗 → 補 action item 再重驗。

## 規模差異

Chaos 的設計在不同規模下差異顯著。單服務 chaos 與跨區 chaos 打到的系統層不同，blast radius 控制方式也不同。

### 單服務 chaos

單服務 chaos 驗證的是一個服務對其直接依賴的容錯能力。blast radius 限在該服務的 instance、replica 或 traffic cohort 內。適合驗證 circuit breaker、fallback、timeout、retry 與 graceful degradation。

### 跨區 chaos 與 failure localization

跨區 chaos 驗證的是故障在區域或依賴鏈上的擴散行為。Amazon 的 cell-based architecture 把多租戶服務的故障域限制在 cell 內 — 一個 cell 的異常不會擴散到其他 cell，恢復策略從全域搶救轉為分批收斂。Meta 的 region failover 實踐則關注控制面故障的跨區擴散 — 當核心網路或 BGP 配置異常跨越區域邊界，恢復動作本身可能成為新的放大器。

兩者共同的判讀重點是：故障是否被限制在預期邊界內。單服務 chaos 的邊界是 instance 與 dependency；跨區 chaos 的邊界是 region、cell 與 shared dependency。blast radius 越大，stop condition 與 rollback path 的設計要求越高。

## 案例對照

- [Netflix：Steady State、Chaos 與 FIT](/backend/06-reliability/cases/netflix/steady-state-chaos-and-fit/)：把故障注入變成科學化驗證循環，四元素（steady state / hypothesis / blast radius / abort condition）提供 chaos 設計的結構。FIT 把注入粒度推進到 request path，讓測試更接近真實依賴路徑。
- [Netflix：Business-Hours Chaos Guardrails](/backend/06-reliability/cases/netflix/chaos-monkey-business-hours-guardrails/)：business hours 執行的前提是 guardrails 到位（時段限制、範圍限制、abort trigger、事後回寫），驗證的不只是系統韌性，也包含團隊應變能力。
- [Netflix：FIT 證據交接](/backend/06-reliability/cases/netflix/fit-failure-injection-evidence-handoff/)：把 FIT 輸出結構化成四個決策欄位，讓實驗結果直接驅動 release gate。
- [Amazon：Shuffle Sharding 與 Cell 邊界](/backend/06-reliability/cases/amazon/shuffle-sharding-and-cell-boundary/)：cell-based architecture 讓恢復策略從全域搶救轉為分批收斂，是跨區 chaos 設計的前提。
- [Meta：Region Failover 邊界治理](/backend/06-reliability/cases/meta/region-failover-and-reliability-boundaries/)：跨區依賴與控制面故障的回復順序，說明 blast radius 在大規模系統中的擴散治理。
- [Shopify：BFCM 容量治理與 Game Day](/backend/06-reliability/cases/shopify/bfcm-capacity-and-game-day/)：game day 把演練、壓測與隔離單位連成一條線，適合補充高峰型場景的 chaos 設計。

## 判讀訊號

判讀 chaos 的品質不只看實驗是否通過，要看實驗設計是否能產出可信結論。

- **chaos experiment 只測 happy path 的故障**：只關掉不重要的服務、只在低流量時段跑，通過了也無法證明高價值路徑的容錯能力。判讀條件：注入目標是否對應服務的關鍵依賴路徑。行動：把注入目標對齊服務的 top-3 關鍵依賴。
- **broker / DB / network 故障無自動演練、靠真事故學**：沒有定期 chaos 的團隊只能從真實事故中學習，學習成本高且機會不可控。判讀條件：chaos 是否有固定節奏，而非只在事故後才啟動。行動：排入季度 chaos sprint、從最小 blast radius 開始。
- **chaos 暴露問題沒修、紀錄堆積**：實驗發現缺口但 action item 沒有 owner、沒有 deadline，同類問題反覆出現。判讀條件：action item 是否進入 [6.21 reliability debt backlog](/backend/06-reliability/reliability-debt-backlog/) 並被追蹤。行動：每次 chaos 結束後 action item 指定 owner + deadline。
- **production chaos 只在低流量時段跑、訊號失真**：低流量時段的依賴行為、流量模式與團隊狀態都跟 production peak 不同，通過了不代表高峰時可承受。判讀條件：是否有 business-hours 或接近 peak 的驗證補充。行動：至少每季補一次 business-hours chaos 驗證。
- **故障注入工具跟 production 不同 stack、結果不可信**：staging 用不同的 broker、database 或 network 配置做 chaos，結果無法外推到 production。判讀條件：實驗環境與 production 的差異是否被記錄並納入結論限制。行動：在結論中標註環境差異、逐步推進 production chaos。
- **chaos 結果沒進 runbook**：值班人員不知道特定依賴失效後的預期退化行為，事故時仍靠臨場推理。判讀條件：chaos 結論是否已回寫到對應服務的 on-call runbook。行動：每次 chaos 完成後回寫 runbook 的「依賴失效預期行為」段。

## 交接路由

- [6.7 DR / rollback rehearsal](/backend/06-reliability/dr-rollback-rehearsal/)：chaos 暴露的回復路徑問題進入 DR 演練
- [6.12 idempotency / replay](/backend/06-reliability/idempotency-replay/)：注入重複訊息驗證冪等能力
- [6.14 dependency budget](/backend/06-reliability/dependency-reliability-budget/)：對依賴注入故障驗證 reliability budget
- [6.20 experiment safety boundary](/backend/06-reliability/experiment-safety-boundary/)：chaos 的 blast radius、stop condition 與權限約束
- [6.22 steady state definition](/backend/06-reliability/steady-state-definition/)：chaos 開始前的穩態定義
- [6.23 verification evidence handoff](/backend/06-reliability/verification-evidence-handoff/)：chaos 證據接到 release gate
- [8.6 drills / on-call readiness](/backend/08-incident-response/drills-and-oncall-readiness/)：chaos 結果回饋到值班訓練
