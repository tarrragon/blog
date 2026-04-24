---
title: "模組六：可靠性驗證流程"
date: 2026-04-22
description: "整理 CI、load test、fuzz、chaos testing 與系統級回歸驗證"
weight: 6
---

可靠性驗證模組的核心目標是說明測試如何從單一函式擴展到整個後端系統。語言教材會處理 unit test、table-driven / parameterized test、race / async test 與 integration test；本模組負責 [CI pipeline](../knowledge-cards/ci-pipeline)、壓力測試、fuzz campaign 與 chaos testing。

## 暫定分類

| 分類             | 內容方向                                              |
| ---------------- | ----------------------------------------------------- |
| CI pipeline      | test 分層、快慢測試、artifact、環境變數               |
| [Load test](../knowledge-cards/load-test)        | workload model、[throughput](../knowledge-cards/throughput/)、latency、容量瓶頸         |
| Fuzz campaign    | input boundary、corpus、crash reproduction            |
| Chaos testing    | [broker](../knowledge-cards/broker) 斷線、資料庫延遲、節點重啟、網路抖動           |
| Test environment | ephemeral [database](../knowledge-cards/database)、[container](../knowledge-cards/container/) service、seed data      |
| [Release Gate](../knowledge-cards/release-gate/)     | regression suite、[migration](../knowledge-cards/migration) check、[rollback rehearsal](../knowledge-cards/rollback-rehearsal/) |

## 選型入口

可靠性驗證選型的核心判斷是團隊要提前驗證哪一種失敗風險。CI pipeline 驗證每次變更的基本正確性；load test 驗證容量、延遲、[backpressure](../knowledge-cards/backpressure/)、[rate limit](../knowledge-cards/rate-limit/) 與 [load shedding](../knowledge-cards/load-shedding/)；fuzz campaign 驗證輸入邊界；chaos testing 驗證外部依賴、[partial failure](../knowledge-cards/partial-failure/)、[cascading failure](../knowledge-cards/cascading-failure/) 或 [failover](../knowledge-cards/failover/)；test environment 與 [Release Gate](../knowledge-cards/release-gate/) 則支撐穩定、可重現的驗證流程。

CI pipeline 適合保護回歸；load test 適合高流量活動、容量規劃與瓶頸定位；fuzz campaign 適合 parser、[Request/Response Protocol](../knowledge-cards/request-response-protocol/)、payload validation 與安全邊界；chaos testing 適合 broker、database、network、node failure、[timeout](../knowledge-cards/timeout/)、[retry storm](../knowledge-cards/retry-storm/)、[circuit breaker](../knowledge-cards/circuit-breaker/) 與系統級風險；[Release Gate](../knowledge-cards/release-gate/) 適合 migration、[Rollback Rehearsal](../knowledge-cards/rollback-rehearsal/) 與跨服務相容性。

接近真實網路服務的例子包括活動前驗證 checkout 容量、發版前驗證 migration、對 [Webhook Protocol](../knowledge-cards/webhook-protocol/) 做 fuzz、在預備環境演練 broker 暫時中斷。這些場景的共同問題是事故前驗證，因此本模組會先處理測試分層、工作負載模型與失敗模式。

## 與語言教材的分工

語言教材處理測試程式如何寫得可讀、可重現、可定位。Backend reliability 模組處理測試如何在 CI、環境、資料庫、broker、網路與部署流程中被執行。

## 跨語言適配評估

可靠性驗證使用方式會受語言的測試框架、fixture 生態、並發測試能力、型別系統、fuzz 支援與容器化工具影響。同步 runtime 要測 thread pool、[connection pool](../knowledge-cards/connection-pool) 與 [timeout](../knowledge-cards/timeout)；async runtime 要測 event loop blocking、task cancellation 與 [backpressure](../knowledge-cards/backpressure)；動態語言要用 [contract](../knowledge-cards/contract/) test 與 runtime validation 補足 schema 風險；強型別語言要把型別安全延伸到外部 payload 與 migration 相容性。

## 章節列表

| 章節                  | 主題          | 關鍵收穫                                   |
| --------------------- | ------------- | ------------------------------------------ |
| [6.1](ci-pipeline/)   | CI pipeline   | 分層測試、快慢測試與 artifact 管理         |
| [6.2](load-testing/)  | load test     | 定義 workload、吞吐與延遲基準              |
| [6.3](fuzz-campaign/) | fuzz campaign | 建立輸入邊界、corpus 與 crash reproduction |
| [6.4](chaos-testing/) | chaos testing | 模擬 broker、DB、network 與節點故障        |
| [6.5](attacker-view-validation-risks/) | 攻擊者視角（紅隊）：驗證缺口弱點判讀 | 用驗證盲區、演練缺口與門檻失真檢查 release 風險 |
