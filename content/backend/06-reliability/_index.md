---
title: "模組六：可靠性驗證流程"
date: 2026-04-22
description: "整理 CI、load test、fuzz、chaos testing 與系統級回歸驗證"
weight: 6
---

可靠性驗證模組的核心目標是說明測試如何從單一函式擴展到整個後端系統。語言教材會處理 unit test、table-driven / parameterized test、race / async test 與 integration test；本模組負責 [CI pipeline](/backend/knowledge-cards/ci-pipeline)、壓力測試、fuzz campaign 與 chaos testing。

## 暫定分類

| 分類                                                   | 內容方向                                                                                                                                    |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| CI pipeline                                            | test 分層、快慢測試、artifact、環境變數                                                                                                     |
| [Load test](/backend/knowledge-cards/load-test)        | workload model、[throughput](/backend/knowledge-cards/throughput/)、latency、容量瓶頸                                                       |
| Fuzz campaign                                          | input boundary、corpus、crash reproduction                                                                                                  |
| Chaos testing                                          | [broker](/backend/knowledge-cards/broker) 斷線、資料庫延遲、節點重啟、網路抖動                                                              |
| Test environment                                       | ephemeral [database](/backend/knowledge-cards/database)、[container](/backend/knowledge-cards/container/) service、seed data                |
| [Release Gate](/backend/knowledge-cards/release-gate/) | regression suite、[migration](/backend/knowledge-cards/migration) check、[rollback rehearsal](/backend/knowledge-cards/rollback-rehearsal/) |

## 選型入口

可靠性驗證選型的核心判斷是團隊要提前驗證哪一種失敗風險。CI pipeline 驗證每次變更的基本正確性；load test 驗證容量、延遲、[backpressure](/backend/knowledge-cards/backpressure/)、[rate limit](/backend/knowledge-cards/rate-limit/) 與 [load shedding](/backend/knowledge-cards/load-shedding/)；fuzz campaign 驗證輸入邊界；chaos testing 驗證外部依賴、[partial failure](/backend/knowledge-cards/partial-failure/)、[cascading failure](/backend/knowledge-cards/cascading-failure/) 或 [failover](/backend/knowledge-cards/failover/)；test environment 與 [Release Gate](/backend/knowledge-cards/release-gate/) 則支撐穩定、可重現的驗證流程。

CI pipeline 適合保護回歸；load test 適合高流量活動、容量規劃與瓶頸定位；fuzz campaign 適合 parser、[Request/Response Protocol](/backend/knowledge-cards/request-response-protocol/)、payload validation 與安全邊界；chaos testing 適合 broker、database、network、node failure、[timeout](/backend/knowledge-cards/timeout/)、[retry storm](/backend/knowledge-cards/retry-storm/)、[circuit breaker](/backend/knowledge-cards/circuit-breaker/) 與系統級風險；[Release Gate](/backend/knowledge-cards/release-gate/) 適合 migration、[Rollback Rehearsal](/backend/knowledge-cards/rollback-rehearsal/) 與跨服務相容性。

接近真實網路服務的例子包括活動前驗證 checkout 容量、發版前驗證 migration、對 [Webhook Protocol](/backend/knowledge-cards/webhook-protocol/) 做 fuzz、在預備環境演練 broker 暫時中斷。這些場景的共同問題是事故前驗證，因此本模組會先處理測試分層、工作負載模型與失敗模式。

## 與語言教材的分工

語言教材處理測試程式如何寫得可讀、可重現、可定位。Backend reliability 模組處理測試如何在 CI、環境、資料庫、broker、網路與部署流程中被執行。

## 與資安概念層的交接

本模組承接 07 模組的概念判讀，並在驗證層落地。交接基線如下：

- 來自 [7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)：承接資料外送與回復排序的驗證場景。
- 來自 [7.7 稽核追蹤與責任邊界](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)：承接事件證據完整性與回查演練。
- 來自紅隊 [7.R4 資源濫用與可用性破壞](/backend/07-security-data-protection/red-team/resource-abuse/)：承接壓力放大路徑與降級回復驗證。

這個交接讓可靠性模組聚焦驗證方法與演練節奏，同時保持與資安問題模型一致。

## 跨語言適配評估

可靠性驗證使用方式會受語言的測試框架、fixture 生態、並發測試能力、型別系統、fuzz 支援與容器化工具影響。同步 runtime 要測 thread pool、[connection pool](/backend/knowledge-cards/connection-pool) 與 [timeout](/backend/knowledge-cards/timeout)；async runtime 要測 event loop blocking、task cancellation 與 [backpressure](/backend/knowledge-cards/backpressure)；動態語言要用 [contract](/backend/knowledge-cards/contract/) test 與 runtime validation 補足 schema 風險；強型別語言要把型別安全延伸到外部 payload 與 migration 相容性。

## 章節列表

| 章節                                   | 主題                                 | 關鍵收穫                                        |
| -------------------------------------- | ------------------------------------ | ----------------------------------------------- |
| [6.1](ci-pipeline/)                    | CI pipeline                          | 分層測試、快慢測試與 artifact 管理              |
| [6.2](load-testing/)                   | load test                            | 定義 workload、吞吐與延遲基準                   |
| [6.3](fuzz-campaign/)                  | fuzz campaign                        | 建立輸入邊界、corpus 與 crash reproduction      |
| [6.4](chaos-testing/)                  | chaos testing                        | 模擬 broker、DB、network 與節點故障             |
| [6.5](attacker-view-validation-risks/) | 攻擊者視角（紅隊）：驗證缺口弱點判讀 | 用驗證盲區、演練缺口與門檻失真檢查 release 風險 |
