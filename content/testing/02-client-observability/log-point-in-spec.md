---
title: "功能規格中的 log 點定義方法"
date: 2026-06-19
description: "把 log 點設計從 debug 階段前移到功能規格階段 — 每個功能的規格文件新增可觀測性欄位，列出啟動 / 步驟 / 錯誤 / 完成四類 log 點"
weight: 2
tags: ["testing", "observability", "logging", "specification", "design"]
---

Log 點定義是功能規格的一部分，和 API schema 同級。功能規格描述「這個功能做什麼」，log 點規格描述「這個功能執行時留下什麼可觀察的紀錄」。把 log 點設計前移到規格階段，讓 log 成為功能的設計產物，而非事後的 debug 工具（本章合成，TF-9 Derive）。

## 四類 log 點

每個功能的 log 點按執行時機分成四類。

### 啟動 log

功能開始執行時記錄。回答「這個功能是否被觸發了」。

啟動 log 包含觸發來源（使用者操作、系統排程、外部事件）和初始參數（連線目標、操作類型）。如果一個功能從未被觸發，啟動 log 的缺席就是線索。

### 步驟 log

功能執行過程中的每個關鍵步驟完成時記錄。回答「流程走到哪裡了」。

步驟 log 的粒度依功能複雜度而定。三步驟的功能每步記一條；十步驟的功能可以只記關鍵的三到五步。判斷標準是：如果這一步失敗，開發者是否需要知道失敗點在哪。

### 錯誤 log

步驟失敗、例外捕獲、非預期狀態出現時記錄。回答「出了什麼問題」。

錯誤 log 必須包含足夠的 context 讓開發者不需要重現問題就能判斷原因。至少包含：哪一步失敗、失敗原因（error message）、當時的關鍵狀態值。

### 完成 log

功能正常結束時記錄。回答「功能是否成功完成、花了多久」。

完成 log 包含執行結果和耗時。和啟動 log 配對使用 — 有啟動但沒有完成代表功能中途異常退出。

## 在功能規格中加可觀測性欄位

以 app_tunnel 的「連線到 ttyd 終端機」功能為例，傳統規格只寫：

- 輸入：使用者選擇的伺服器
- 處理：建立 WebSocket 連線、發送 auth token、開始接收 terminal output
- 輸出：終端機畫面顯示 terminal output

加上可觀測性欄位後：

| 類型 | log 點                    | 內容                                        |
| ---- | ------------------------- | ------------------------------------------- |
| 啟動 | connect.start             | 目標 URL、觸發來源（使用者操作 / 自動重連） |
| 步驟 | connect.biometric.done    | 認證結果、耗時                              |
| 步驟 | connect.credential.loaded | 使用者名稱（密碼 redact）                   |
| 步驟 | connect.ws.connected      | 連線 URL、耗時                              |
| 步驟 | connect.auth.sent         | token 長度（內容 redact）                   |
| 步驟 | connect.stream.subscribed | stream 狀態                                 |
| 錯誤 | connect.{step}.failed     | 失敗步驟、error message、retry count        |
| 完成 | connect.done              | 總耗時、最終狀態                            |

這張表在功能規格階段就能寫出來，因為它只依賴功能的流程設計，不依賴實作細節。功能流程確定後，每一步在哪裡需要 log 點就確定了。

## log 點命名規則

統一的命名規則讓 log 可以被 grep、過濾和統計。

**階層式命名**：`{功能}.{步驟}.{事件}`。例如 `connect.ws.connected`、`connect.auth.failed`。

**事件後綴統一**：`start`（啟動）、`done`（步驟完成）、`failed`（失敗）、`complete`（功能完成）。

**和程式碼結構對應**：log 點名稱對應到程式碼中的函式或模組。`connect.biometric.done` 對應 `BiometricService.authenticate()` 的成功路徑。這讓開發者看到 log 名稱就知道去哪裡找程式碼。

## log 點規格的 review 檢查

功能規格 review 時，可觀測性欄位的檢查要點：

**每步都有 log**：流程中的每個步驟在成功和失敗時都有對應的 log 點。遺漏的步驟意味著該步驟出問題時無法從 log 判斷。

**錯誤 log 有足夠 context**：error log 只寫「連線失敗」不夠；需要寫「連線失敗」加上 error code、目標 URL、已完成的步驟。

**敏感欄位有 redaction 標記**：密碼、token、個人資料在 log 規格中標記為 redact，實作時用 redaction 機制處理。

**啟動和完成配對**：每個功能有啟動 log 就應該有完成 log，形成完整的生命週期。

## 下一步路由

- 三層 log 的詳細設計 → [三層 log 設計](/testing/02-client-observability/three-layer-log-design/)
- 事後補 log 和設計產物 log 的差異 → [「事後補 log」vs「設計產物 log」的品質差異](/testing/02-client-observability/hotfix-log-vs-designed-log/)
- Log 中的敏感資訊處理 → [monitoring 模組七 資安](/monitoring/07-security-privacy/)
