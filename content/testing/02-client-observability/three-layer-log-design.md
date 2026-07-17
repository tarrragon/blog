---
title: "三層 log 設計"
date: 2026-06-19
description: "連線生命週期 log、protocol 訊息 log、使用者行為 log — 三層各自的職責、詳細程度和啟停控制"
weight: 1
tags: ["testing", "observability", "logging", "client-side", "design"]
---

客戶端 log 分成三層，每層記錄不同粒度的資訊，服務不同的 debug 場景。三層的區別在於回答的問題不同：連線生命週期回答「整體流程走到哪一步」，protocol 訊息回答「通訊細節是什麼」，使用者行為回答「使用者做了什麼操作」。

## 連線生命週期 log

連線生命週期 log 記錄的是「流程走到第幾步、每步成功或失敗」。這一層的 log 粒度是步驟級 — 不記錄每一個封包或每一次函式呼叫，只記錄流程中的關鍵節點。

以一個遠端終端機 app 的連線流程為例，連線生命週期包含五步：biometric 認證 → credential 讀取 → WebSocket 連線 → auth token 發送 → stream 訂閱。每步完成時記一條 log，失敗時記一條包含原因的 log。

```text
[conn] Step 1/5: biometric auth completed (duration: 320ms)
[conn] Step 2/5: credential loaded (user: admin)
[conn] Step 3/5: WebSocket connected (url: wss://...)
[conn] Step 4/5: auth token sent
[conn] Step 5/5: stream subscribed, ready
```

該 app 在實機測試前六個核心元件中只有兩個有 log，且全是實機修復時事後補上的（[T.C4](/testing/cases/client-log-absent-debug-cost/)）。auth token 缺失問題的 debug 過程中，開發者無法從任何 log 判斷失敗發生在五步中的哪一步。如果有連線生命週期 log，第一次連線就能看到「Step 3 完成，Step 4 未執行」— 直接定位到 auth token 缺失。

連線生命週期 log 在所有模式（debug 和 release）都應該啟用。這層 log 量小（每次連線 5-10 條），不影響效能，但在 production 問題回報時是第一手資訊來源。

## Protocol 訊息 log

Protocol 訊息 log 記錄的是通訊協議層面的細節：發送和接收的 frame type、payload 前綴、handshake 參數、逾時值。這一層的粒度比連線生命週期更細 — 每一次 send/receive 都記錄。

```text
[proto] TX: text frame, payload: {"AuthToken":"base64..."} (42 bytes)
[proto] RX: text frame, payload prefix: "0" (output data, 128 bytes)
[proto] TX: binary frame, payload: [72, 101, 108, 108, 111] (5 bytes)
```

Protocol log 在 debug 時幫助確認「程式碼發送了什麼、收到了什麼」。該 app 的 text/binary frame 問題（[T.C1](/testing/cases/ws-text-binary-frame-mock-blindspot/)）如果有 protocol log，開發者會在 log 中看到 `TX: binary frame` 而非預期的 `TX: text frame` — 直接指向 frame type 問題。

Protocol log 在 release mode 應該能關閉。這層 log 量大（每次鍵盤輸入一條），且 payload 可能包含敏感資訊。Debug mode 預設啟用，release mode 提供開關（例如隱藏設定頁的 toggle）讓進階使用者在回報問題時開啟。

## 使用者行為 log

使用者行為 log 記錄的是使用者在 UI 上的操作：按鈕點擊、畫面切換、設定變更。這層 log 的粒度是操作級 — 使用者做了一個有意義的動作記一條。

```text
[ui] screen: HomeScreen, action: tap Connect Terminal
[ui] screen: TerminalScreen, state: connecting → connected
[ui] screen: TerminalScreen, action: tap back button
[ui] screen: HomeScreen, state: returned from terminal
```

使用者行為 log 在兩個場景有價值：第一，debug 時還原使用者操作路徑 — 「使用者做了什麼導致問題出現」；第二，結合狀態矩陣（[ux-design 模組一](/ux-design/01-screen-state-machine/)）做狀態轉換的實際覆蓋率分析 — 哪些狀態轉換在真實使用中經常發生，哪些從未發生。

使用者行為 log 在 release mode 啟用時需要注意隱私。記錄「使用者切換了畫面」是合理的；記錄「使用者輸入了密碼 abc123」需要 redaction 機制（[monitoring 模組七 資安](/monitoring/07-security-privacy/)）。

## 三層的關係

三層 log 各自獨立運作，debug 時通常按照從粗到細的順序使用。

**粗篩**：先看連線生命週期 log，確認流程走到哪一步。如果 Step 3 失敗，問題在 WebSocket 連線層。

**細查**：切到 protocol 訊息 log，看 Step 3 的連線嘗試中發送和接收了什麼。如果看到 binary frame 發送但沒有回應，問題可能在 frame type。

**還原**：如果問題和使用者操作有關（例如只在特定操作順序下觸發），看使用者行為 log，還原操作路徑。

三層 log 用同一個時間戳和 correlation ID（例如連線 session ID），讓跨層比對可行。

## 下一步路由

- 在功能規格中定義 log 點 → [功能規格中的 log 點定義方法](/testing/02-client-observability/log-point-in-spec/)
- 事後補 log 和設計產物 log 的品質差異 → [「事後補 log」vs「設計產物 log」的品質差異](/testing/02-client-observability/hotfix-log-vs-designed-log/)
- Log 收集方案選擇 → [自架 log endpoint vs 商業方案](/testing/02-client-observability/log-endpoint-tradeoff/)
- 事件分類與收集策略 → [monitoring 模組一 監控心智模型](/monitoring/01-mental-model/)
