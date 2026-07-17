---
title: "Flaky test 根因分類"
date: 2026-06-19
description: "計時依賴 / 環境差異 / 資源競爭 / 非確定性輸出 — 四類 flaky test 根因的辨識和處理策略"
weight: 4
tags: ["testing", "flaky", "root-cause", "ci", "reliability"]
---

Flaky test 是指在程式碼沒有改變的情況下，test 的結果在通過和失敗之間隨機切換。Flaky test 侵蝕團隊對 test suite 的信任 — 如果 test 經常「隨便」失敗，開發者會習慣性地 re-run 而非調查失敗原因，真正的 bug 可能在 re-run 中被忽略。

## 四類根因

### 計時依賴

Test 依賴特定的時間條件 — timeout、delay、animation duration。系統負載不同時，時間條件可能滿足也可能不滿足。

常見模式：

- `await Future.delayed(Duration(seconds: 2))` + assertion — 如果操作在 2 秒內完成，test 通過；如果 CI 機器負載高導致操作超過 2 秒，test 失敗
- `expect(stopwatch.elapsed, lessThan(Duration(seconds: 1)))` — 效能斷言在不同機器上結果不同

處理策略：用事件驅動代替 timeout。等待 `stream.first` 代替 `delay(2s) + check`；用 completion signal 代替固定等待時間。如果必須用 timeout，設定寬裕的上限（10x 預期時間）而非精確的預期值。[T.C8 fire-and-forget 編排的測試競態](/testing/cases/fire-and-forget-test-race/) 是「單跑綠、合跑紅」的實例——被測編排未等待背景收尾，斷言與它賽跑。

### 環境差異

Test 在不同環境下行為不同 — 作業系統、檔案系統、時區、locale、DNS 解析。

常見模式：

- 檔案路徑分隔符（`/` vs `\`）在不同 OS 下不同
- 時間格式化結果依時區而定（UTC vs local）
- 浮點數比較因 CPU 架構不同有微小差異

處理策略：用 `path.join` 代替硬編碼路徑；時間操作用 UTC；浮點比較用 `closeTo` 代替精確比較。在 CI 中固定環境變數（`TZ=UTC`、`LANG=en_US.UTF-8`）。

### 資源競爭

Test 依賴共享資源（port、暫存檔、資料庫行）— 平行執行時多個 test 同時存取同一資源，結果依賴執行順序。

常見模式：

- 多個 test 監聽同一個 port — 第二個綁定失敗
- 多個 test 寫入同一個暫存檔 — 內容被覆蓋
- 多個 test 操作同一個資料庫 table — 資料互相干擾

處理策略：每個 test 使用獨立的資源（隨機 port、唯一檔名、隔離的資料庫 schema）。如果資源無法隔離，sequential 執行相關 test（`@sequential` 標註）。

### 非確定性輸出

程式碼的輸出本身不確定 — `Set` 的迭代順序、`Map` 的 key 順序、非同步操作的完成順序。

常見模式：

- 斷言 `Set` 的 `toString()` 結果等於特定字串 — `Set` 的迭代順序不保證
- 斷言 `Future.wait([a, b]).then((results) => results[0])` — `a` 和 `b` 的完成順序不固定
- 斷言 JSON 序列化的 key 順序 — `Map` 的 key 順序在不同實作中不同

處理策略：不斷言順序（用 `containsAll` 代替 `equals` 比較集合）；不斷言序列化格式（反序列化後比較值）；用 `completion` matcher 代替順序假設。

## 診斷步驟

發現疑似 flaky test 時的診斷步驟：

1. **確認 flaky**：在乾淨環境連續跑 20 次，確認失敗是隨機的（如果每次都失敗，是 bug 不是 flaky）
2. **收集失敗訊息**：記錄每次失敗的 assertion 訊息、stack trace、環境資訊（OS 版本、CI 機器 ID）
3. **分類**：失敗訊息指向時間（timeout）→ 計時依賴；指向值不同 → 非確定性或環境差異；指向連接失敗 → 資源競爭
4. **修復**：根據分類使用對應的處理策略

分類和修復之外，flaky test 的根因有時來自 assertion 本身的設計 — [Assertion 品質三問](/testing/05-test-design-judgment/assertion-quality/)提供判斷 assertion 是否有效的框架。如果 flaky 的根因是 mock 和真實服務的行為差異，回到 [Mock 邊界判斷決策表](/testing/05-test-design-judgment/mock-boundary-decision/)判斷 mock 是否還適用。Protocol integration test 在 CI 中的[服務 fixture 管理](/testing/03-protocol-integration-test/service-fixture-management/)也是 flaky 的常見來源 — 服務啟動不完全就開始跑 test。
