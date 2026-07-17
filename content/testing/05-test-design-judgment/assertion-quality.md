---
title: "Assertion 品質三問"
date: 2026-06-19
description: "斷言的是行為嗎？能區分正確和錯誤嗎？會 flaky 嗎？— 三個問題判斷 assertion 是否有效"
weight: 3
tags: ["testing", "assertion", "quality", "test-design"]
---

Assertion 是 test 的結論 — 「我認為程式碼的行為應該是 X」。Assertion 的品質決定了 test 的有效性：無效的 assertion 讓 test 通過但問題仍在，或讓 test 隨機失敗但問題不在程式碼。

## 三個判斷問題

### 斷言的是行為嗎

Assertion 應該斷言程式碼的外部可觀察行為（回傳值、狀態變化、副作用），而非內部實作細節（私有變數的值、呼叫次數、執行順序）。

斷言行為的 test 在重構時不需要改 — 只要行為不變，test 就通過。斷言實作的 test 在任何內部調整時都會壞掉，即使行為完全正確。

例：驗證「parser 正確解析紅色文字」時，斷言 token 的顏色屬性（行為）比斷言 parser 內部的 state machine 走了哪些步驟（實作）更穩定。

### 能區分正確和錯誤嗎

Assertion 應該在程式碼正確時通過、錯誤時失敗。如果 assertion 無論程式碼正確或錯誤都通過，這個 assertion 沒有提供保護。

常見的無效 assertion：

**斷言不為 null**：`expect(result, isNotNull)` 只驗證「有回傳值」，不驗證「回傳值正確」。回傳錯誤的值也會通過。

**斷言型別**：`expect(result, isA<List>())` 只驗證「回傳 List」，不驗證 List 的內容。空 List 和錯誤內容的 List 都會通過。

**斷言包含**：`expect(result, contains('error'))` 驗證字串包含 'error'，但如果回傳 'no error occurred'（正確情境）也包含 'error' — assertion 無法區分正確和錯誤。

T.C3 的 parser test 斷言 `expect(tokens.first, isA<TextToken>())` — 驗證 token 型別是 TextToken。但正確解析和透傳亂碼都可能產生 TextToken，assertion 無法區分（本章合成，TF-5 Derive — 透傳的靜默副作用和 assertion 的區分力有 tension）。

有時序約束的訊息流是區分力的另一個維度：[T.C9 外接螢幕訊息序列斷言](/testing/cases/outbox-sequence-external-display/) 是序列斷言取代存在斷言的實例——只斷言「訊息有送出」無法區分順序顛倒的錯誤。

### 會 flaky 嗎

Assertion 是否依賴非確定性因素 — 時間、隨機數、外部服務狀態、執行順序。如果是，test 可能在程式碼正確時失敗（false negative），降低團隊對 test 的信任。

常見的 flaky assertion 來源：

- 依賴 `DateTime.now()` 或 `stopwatch.elapsed` — 時間精度和系統負載影響結果
- 依賴特定的執行順序 — `Set` 或 `Map` 的迭代順序不保證
- 依賴外部服務的回應時間 — 網路延遲導致 timeout

## Assertion 改善的操作步驟

對既有的 test assertion 逐一問三個問題，標記需要改善的：

1. **行為 check**：assertion 斷言的是 public API 的回傳值或狀態嗎？如果斷言私有變數或呼叫次數，考慮改成行為斷言。
2. **區分 check**：把 assertion 改成反向（`expect(result, 'wrong_value')`），test 會失敗嗎？如果 assertion 太寬鬆（isNotNull、isA），test 可能在錯誤的情況下也通過。
3. **穩定 check**：連續跑 10 次，每次都通過嗎？如果有 flaky，找到依賴的非確定性因素。

## 下一步路由

- Flaky test 的系統性根因分類 → [Flaky test 根因分類](/testing/05-test-design-judgment/flaky-test-root-cause/)
- 斷言失敗訊息該寫什麼（reason 寫失敗後果與處置）→ [測試註解與命名紀律](/testing/05-test-design-judgment/test-comment-and-naming-discipline/)
- 測試資料的代表性 → [Test data 代表性](/testing/05-test-design-judgment/test-data-representativeness/)
- Mock 邊界判斷 → [Mock 邊界判斷決策表](/testing/05-test-design-judgment/mock-boundary-decision/)
