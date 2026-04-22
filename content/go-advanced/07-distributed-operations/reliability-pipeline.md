---
title: "7.6 CI、fuzz、load test 與 chaos testing"
date: 2026-04-22
description: "把單元測試與整合測試擴展成服務可靠性驗證流程"
weight: 6
---

可靠性驗證流程的核心責任是讓不同層級的測試回答不同風險。Unit test 驗證規則，integration test 驗證協定協作，race test 檢查資料競爭，fuzz test 尋找輸入邊界，load test 驗證容量，chaos test 驗證失敗復原。

## 本章目標

學完本章後，你將能夠：

1. 分辨不同測試層級各自要防的風險
2. 把 race、fuzz、load 與 chaos 放到合適的流程裡
3. 設計能回饋容量規劃的驗證流程
4. 不把端到端測試當成萬能答案
5. 讓測試結果回到 deployment 與 runtime 邊界

## 前置章節

- [Go 入門：testing 基礎](../../go/05-error-testing/testing-basics/)
- [Go 進階：WebSocket integration test](../05-testing-reliability/websocket-integration/)
- [Go 進階：race condition 檢查](../05-testing-reliability/race-check/)
- [Go 進階：table-driven test 的設計邊界](../05-testing-reliability/table-tests/)

## 後續撰寫方向

1. CI 中哪些測試應每次執行，哪些可以排程或合併前執行。
2. Fuzzing 適合驗證 parser、normalizer 與 protocol decoder 的哪些邊界。
3. Load test 如何設定 client 數、message rate、payload size 與觀測指標。
4. Chaos testing 如何模擬 broker 斷線、資料庫延遲、server shutdown 與網路抖動。
5. 測試結果如何回饋到 capacity planning 與 feature gate。

## 【觀察】不同測試層級回答不同問題

可靠性驗證最怕的錯誤，是把所有測試都塞成一種樣子。不同層級應該分工：

- unit test：規則有沒有寫對
- integration test：協定與元件有沒有接對
- race test：並發邊界有沒有資料競爭
- fuzz test：輸入邊界有沒有漏掉
- load test：容量與延遲是否能接受
- chaos test：失敗發生時系統能不能復原

## 【判讀】race test 不是替代設計

`go test -race` 能抓出實際跑到的資料競爭，但它不是正確性保證。真正的重點仍然是：

- state owner 是誰
- 哪些資料需要 lock
- 哪些資料應該只讓單一 goroutine 擁有
- 哪些資料應該複製而不是共享

## 【策略】load test 的輸出要能回到容量判斷

load test 不應只是跑出一個數字，還要能回答：

- 哪個 queue 開始變長
- 哪個 DB connection pool 開始飽和
- 哪種 message rate 會讓 latency 明顯上升
- 哪個 memory curve 表示需要調整 buffer 或 GC 參數

如果沒有這些觀察點，壓測結果就很難轉成實際修正。

## 【執行】chaos test 應該模擬真實失敗

chaos test 的重點不是故意把系統弄壞，而是模擬真實世界常見的失敗：

- broker 暫時不可用
- database 延遲上升
- shutdown 中斷流量
- 網路抖動或 timeout

這些情境應該回到 graceful shutdown、retry、idempotency 與 backpressure 設計。

## 【延伸】測試結果應回饋到 feature gate

如果某個功能在 load test 或 chaos test 下風險太高，最直接的做法不一定是先修完整系統，也可能是先用 feature gate 逐步推出、觀察與回收。

## 本章不處理

本章不會綁定特定 CI 或壓測平台。教材重點會放在測試層級分工，避免把所有風險都塞進端到端測試。

## 和 Go 教材的關係

這一章承接的是 Go 的並發測試與可靠性驗證；如果你要先回看語言教材，可以讀：

- [Go：測試基礎](../../go/05-error-testing/testing-basics/)
- [Go 進階：WebSocket integration test](../05-testing-reliability/websocket-integration/)
- [Go 進階：race condition 檢查](../05-testing-reliability/race-check/)
- [Go 進階：table-driven test 的設計邊界](../05-testing-reliability/table-tests/)
