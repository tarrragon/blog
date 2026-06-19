---
title: "反模式：用 mock 數量彌補 mock 盲區"
date: 2026-06-19
description: "為什麼增加 mock test 數量無法跨越 mock 的結構性盲區 — 從 192 個 test 全過的案例拆解數量與覆蓋率的真正關係"
weight: 5
tags: ["testing", "anti-pattern", "mock", "coverage", "strategy"]
---

當 mock test 全過但實機出問題時，常見的第一反應是「test 不夠多」或「覆蓋率不夠高」。這個反應假設 mock test 的問題在數量，而實際上問題在層級 — mock test 驗證的對象和實機暴露的問題不在同一層。增加 mock test 數量擴展的是同一層的覆蓋範圍，不會跨越到另一層。

## 數量與層級的區別

app_tunnel 的 192 個 unit test 覆蓋了 `ConnectionManager`、`AnsiParser`、`TerminalBuffer` 等元件的邏輯分支。如果在 mock test 全過但實機失敗後，反應是「再寫 50 個 test」，新寫的 test 會使用同一個 `FakeWebSocketChannel`，測試更多的邏輯分支 — 更多的輸入組合、更多的邊界條件、更多的錯誤處理路徑。

這 50 個新 test 和原來的 192 個 test 在同一個 mock 環境中執行，受到同一個 `FakeWebSocketChannel` 的行為限制。`FakeWebSocketChannel` 不區分 text frame 和 binary frame — 這個限制在第 1 個 test 和第 242 個 test 中都一樣。數量增加了，遮蔽範圍沒有改變。

用類比說明：用純水測試淨水器的過濾效果，不管測 1 杯還是 1000 杯，結論都是「水很乾淨」。問題在測試材料 — 需要用含有雜質的水測試才能驗證過濾功能。Mock 是純水，真實服務互動是含雜質的水。

## 覆蓋率指標的盲點

Line coverage 和 branch coverage 衡量的是「程式碼中有多少行 / 分支被 test 執行過」。這些指標在同一層 test 內有意義 — 100% branch coverage 的 unit test 確保每個 if/else 都被走過。

但覆蓋率指標不區分 test 的依賴環境。一個使用 `FakeWebSocketChannel` 的 test 和一個使用 `IOWebSocketChannel` 的 test 走過同一行 `sink.add(data)` — 在覆蓋率報告中是同一行被覆蓋，但驗證的語意完全不同。

覆蓋率 100% 意味著「在 mock 環境中，所有程式碼分支都被走過」。這不等於「在真實環境中，所有程式碼分支的行為都是正確的」。app_tunnel 的 `sendData()` 在覆蓋率報告中是「已覆蓋」的，但覆蓋它的 test 用的是不區分 frame type 的 fake。

## 這個反模式如何在團隊中擴散

「test 不夠多」是一個容易執行、容易衡量的回應。寫更多 test 可以提高覆蓋率數字，覆蓋率數字上升給團隊信心。相比之下，「需要一個新的 test 層級」需要建置新的 test 環境、學習不同的 test 技術、接受較慢的執行速度。

這個成本差異讓團隊傾向於在既有的 mock test 層加量，而非引入新的 test 層。每一輪加量後覆蓋率上升，團隊信心增加，但 mock 遮蔽的盲區從未被觸及。問題在下一次實機測試或 production incident 中再次浮現，觸發新一輪的「test 不夠多」反應。

打破這個循環的起點是區分「同層覆蓋率不足」和「層級缺失」。如果問題是同層覆蓋率不足（某個分支沒被 test 走到），加 test 有效。如果問題是層級缺失（mock 結構性地遮蔽了某類行為），加同一層的 test 無效，需要引入新的 test 層級。

## 判讀訊號

以下訊號指向「層級缺失」而非「數量不足」：

**test 全過但實機失敗的 bug 類型集中在外部互動**：連線問題、認證問題、資料格式問題、逾時問題 — 這些問題的共同特徵是發生在程式碼與外部服務的邊界上，不是程式碼內部的邏輯錯誤。

**修復後原有 test 不需要改動**：如果 bug 修復只加了新程式碼（例如新增 auth handshake 步驟）而原有 test 全部不受影響，說明原有 test 從一開始就沒有覆蓋這個行為 — 整個 test 層級不涵蓋這類行為。

**bug 修復是型別轉換或編碼調整**：`if (data is Uint8List) sink.add(String.fromCharCodes(data))` 這類修復改變的是資料在協議層的表現，不是程式邏輯。在 mock 環境中，這個修改前後的行為完全相同 — mock 不區分 frame type。

## 下一步路由

- 從三層職責表理解每層的邊界 → [三層定義與職責表](/testing/01-test-strategy-layers/three-layer-definition/)
- 理解 mock 遮蔽的結構性原因 → [Mock 遮蔽機制分析](/testing/01-test-strategy-layers/mock-masking-mechanism/)
- 判斷是否需要引入 protocol integration test → [判斷原則：什麼時候需要 protocol integration test](/testing/01-test-strategy-layers/when-protocol-integration-test/)
