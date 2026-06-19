---
title: "T.C4 Client-side log 缺失導致 debug 只能靠實機盲測"
date: 2026-06-19
description: "Flutter app 六個核心元件中只有兩個有 log（且全是 W2 hotfix 補的），連線失敗時開發者無法從任何 log 判斷失敗發生在哪一步 — 被迫用最昂貴的 debug 方式：插拔裝置反覆測試"
weight: 4
tags: ["testing", "case-study", "observability", "logging", "debug", "flutter"]
---

這個案例的核心責任是說明「客戶端 log 設計」為什麼應該在功能企劃階段完成，而不是 debug 時才補。Log 不是 debug 工具，是可觀測性基礎設施。

## 觀察

app_tunnel 的六個核心元件在實機測試前的 log 覆蓋狀態：

| 元件                 | log 點數 | 備註                                |
| -------------------- | -------- | ----------------------------------- |
| ConnectionManager    | 0 → 10   | W2 修復後補的 `developer.log`       |
| TerminalScreen       | 0 → 5    | W2 修復後補的                       |
| TtydProtocol         | 0        | encode/decode/buildAuth 無 log      |
| BiometricService     | 0        | isAvailable/authenticate 結果無 log |
| CredentialRepository | 0        | load/save/delete 操作無 log         |
| EnrollmentScreen     | 0        | QR 掃描/解析/儲存無 log             |

W2-004（P0：iOS 實機 WS stream 不觸發）的 debug 過程：無法從任何 log 判斷問題發生在 biometric → credential → WS connect → auth token → stream listen 的哪一步。開發者被迫在每個函式手動加 `developer.log`，重新編譯，插拔裝置測試，反覆數次才定位到「stream 訂閱時機」問題。

| 指標                          | 值                                                  |
| ----------------------------- | --------------------------------------------------- |
| debug 成本                    | 每次修改→編譯→部署→測試約 3-5 分鐘                  |
| 定位 W2-002 (auth token) 花費 | 約 30 分鐘反覆測試                                  |
| 若有連線生命週期 log          | 第一次連線就能看到「Step 3 之後無 auth token 發送」 |

## 判讀

1. **Log 缺失把 debug 成本從秒級升到分鐘級**。如果 ConnectionManager 在企劃階段就設計了「Step 1: biometric → Step 2: credential → Step 3: WS connect → Step 4: auth token → Step 5: listen stream」五步 log，W2-002 的 auth token 問題在第一次連線就能從 log 看到「Step 3 完成，Step 4 未執行」。

2. **「事後補 log」的 log 品質較低**。W2 修復時補的 `developer.log` 格式不統一（有的帶 `name:`，有的不帶；有的用 `// i18n-exempt` 標記，有的忘了），沒有統一的 log 層級，沒有結構化欄位。事後補的 log 是救火工具，不是可觀測性設計。

3. **自用工具最適合自架 log 收集**。app_tunnel 的 server 和 client 都在同一台機器上（或同一個 Tailscale tailnet），client 可以直接打 HTTP POST 到本機的 log endpoint，不需要 Sentry 或 Crashlytics。一個 Go 寫的 JSON log receiver（20 行）+ grep 就是完整的 debug 工具鏈。

4. **Log 設計是功能規格的一部分**。「連線到 ttyd 終端機」這個功能的規格不只是「建立 WS 連線」，還包含「每步有 log、失敗有 log、成功有 log」。跟 API 規格需要定義 request/response 一樣，連線功能需要定義 log 點。

## 策略

1. **功能規格階段列出 log 點清單**：每個功能的規格文件新增「可觀測性」欄位，列出啟動/步驟/錯誤/完成四類 log 點。
2. **建立統一 log 層**：封裝 `developer.log` 為 `AppLogger`，統一 name、level、格式。開發期用 `developer.log`，後續可切換到 HTTP log endpoint。
3. **自架 log endpoint 方案**：本機 Go server 開一個 `/log` POST endpoint，接收 JSON log，寫入檔案。Client 端 `AppLogger` 在 debug mode 同時寫 console + POST 到 endpoint。開發期 grep 查詢，不需要 dashboard。
4. **Protocol log 獨立一層**：WebSocket frame type、payload 前綴、auth handshake 結果獨立記錄，跟 business log 分開。這層 log 在 release mode 應該能關閉。

## 下一步路由

- 想設計客戶端 log 方案 → [模組二：客戶端可觀測性](/testing/)
- 想建自架 log endpoint → 待補：自架 log endpoint 實作章節
- 想理解三層 log 設計 → [模組二](/testing/) 的「三層 log 設計」段
