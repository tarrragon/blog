---
title: "模組六：可靠性驗證流程"
date: 2026-04-22
description: "整理 CI、load test、fuzz、chaos testing 與系統級回歸驗證"
weight: 6
---

可靠性驗證模組的核心目標是說明測試如何從單一函式擴展到整個後端系統。語言教材會處理 unit test、table-driven / parameterized test、race / async test 與 integration test；本模組負責 CI pipeline、壓力測試、fuzz campaign 與 chaos testing。

## 暫定分類

| 分類             | 內容方向                                              |
| ---------------- | ----------------------------------------------------- |
| CI pipeline      | test 分層、快慢測試、artifact、環境變數               |
| Load test        | workload model、throughput、latency、容量瓶頸         |
| Fuzz campaign    | input boundary、corpus、crash reproduction            |
| Chaos testing    | broker 斷線、資料庫延遲、節點重啟、網路抖動           |
| Test environment | ephemeral database、container service、seed data      |
| Release gate     | regression suite、migration check、rollback rehearsal |

## 與語言教材的分工

語言教材處理測試程式如何寫得可讀、可重現、可定位。Backend reliability 模組處理測試如何在 CI、環境、資料庫、broker、網路與部署流程中被執行。

## 相關語言章節

- [Go：table-driven test](../../go/05-error-testing/table-driven-test/)
- [Go：並發行為測試](../../go/05-error-testing/concurrency-test/)
- [Go 進階：race condition 檢查](../../go-advanced/05-testing-reliability/race-check/)
- [Go 進階：CI、fuzz、load test 與 chaos testing](../../go-advanced/07-distributed-operations/reliability-pipeline/)

## 章節列表

| 章節                    | 主題                   | 關鍵收穫                                                     |
| ----------------------- | ---------------------- | ------------------------------------------------------------ |
| [6.1](ci-pipeline/)     | CI pipeline             | 分層測試、快慢測試與 artifact 管理                            |
| [6.2](load-testing/)    | load test               | 定義 workload、吞吐與延遲基準                                |
| [6.3](fuzz-campaign/)    | fuzz campaign           | 建立輸入邊界、corpus 與 crash reproduction                  |
| [6.4](chaos-testing/)    | chaos testing           | 模擬 broker、DB、network 與節點故障                         |
