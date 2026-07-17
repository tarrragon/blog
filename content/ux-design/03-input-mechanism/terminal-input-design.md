---
title: "Terminal app 輸入設計"
date: 2026-06-19
description: "CLI 場景在手機上的特殊需求 — 非自然語言輸入、特殊按鍵需求、整行 vs 逐字元送出對 protocol 的影響"
weight: 2
tags: ["ux-design", "input", "terminal", "cli", "mobile", "protocol"]
---

Terminal app 在手機上的輸入需求和一般文字輸入有根本差異。CLI 指令是結構化語法，路徑分隔符、flag 縮寫、管線符號都有精確語意 — 手機鍵盤為自然語言設計的自動行為（校正、建議、學習）在 CLI 場景中全部變成干擾。

## CLI 輸入的特殊性

桌面終端機的鍵盤直接傳送按鍵事件，沒有中間的輸入法處理層。使用者按 `l` 就是 `l`，按 Tab 就是 Tab，按 Ctrl+C 就是 interrupt signal。

手機鍵盤在使用者和 app 之間插入了 IME 層。使用者按 `l` 時，IME 可能等待後續按鍵組合成完整詞彙再傳送；使用者按的按鍵可能被自動校正替換；使用者的輸入被記錄到 IME 詞庫供跨 app 學習。

Terminal app 需要繞過或控制 IME 層的這些行為。以一個遠端終端機 app 為例，TextField 用 `TextInputType.visiblePassword` + `autocorrect: false` + `enableSuggestions: false` + `enableIMEPersonalizedLearning: false` 四個參數關閉 IME 的自動行為（[U.C3](/ux-design/cases/terminal-input-mechanism-absent/)）。

## 整行送出 vs 逐字元：protocol 層的影響

整行送出和逐字元送出在 UI 層看起來只是「按 Enter 送出整行」和「每個按鍵即時送出」的差別，但在 protocol 層是兩種不同的通訊模式。

### 整行送出

Client 端累積使用者輸入，使用者按 Enter 時傳送完整指令字串加換行符（`ls -la\n`）。Server 端收到完整行後處理。

Protocol 設計簡單：每個 WebSocket frame 是一個完整指令。Server 不需要管理部分輸入的狀態，也不需要即時回應 Tab 或方向鍵。

代價：使用者無法在手機上使用 Tab 補全（Tab 被 IME 攔截或不存在）、無法用方向鍵在指令中移動游標（移動的是 TextField 的游標，不是 server 端的 readline 游標）。

### 逐字元送出

Client 端每個按鍵即時傳送一個 WebSocket frame。Server 端的 shell 即時處理每個字元，包括 Tab 補全（server 回傳補全結果）、Ctrl+C（server 中斷當前程序）、方向鍵（server 端 readline 移動游標）。

Protocol 設計複雜：每個按鍵一個 frame，frame 內容是單一字元或控制序列。Server 端必須維護 readline 狀態。Client 端必須正確編碼控制字元（Ctrl+C = 0x03, Tab = 0x09）。

代價：protocol 複雜度高，每個按鍵都有網路延遲。在高延遲網路上輸入體驗差（打字後要等 round-trip 才看到回顯）。

### 決策在 protocol 層做

該終端機 app 選擇整行送出，犧牲 Tab 補全換取簡單的 protocol 設計。這個決策應該在 protocol spec 階段做 — 因為它影響 server 端（ttyd）的行為預期和 client 端的 frame 格式。在 UI 實作時才臨時決定，可能和 server 端的行為預期不一致。

## 特殊按鍵的 UI 方案

手機沒有 Esc、Tab、Ctrl、方向鍵。Terminal app 需要額外的 UI 元件提供這些按鍵。

### 底部工具列

固定在鍵盤上方的一排按鈕，提供常用特殊鍵。該終端機 app 的工具列包含 Esc、Tab、Ctrl、四個方向鍵。

工具列的設計考量：按鈕大小（手指能精確觸碰的最小尺寸約 44x44 pt）、排列順序（最常用的放中間）、長按行為（長按 Ctrl 是否支援 Ctrl 組合鍵）。

### Ctrl 組合鍵

Ctrl+C（中斷）、Ctrl+D（EOF）、Ctrl+Z（暫停）在 CLI 操作中頻繁使用。手機上的實作方式通常是：按下 Ctrl 按鈕後進入「Ctrl 模式」，下一個按鍵自動加 Ctrl 前綴。

## 下一步路由

- 四維度決策表 → [輸入機制決策表](/ux-design/03-input-mechanism/four-dimension-decision/)
- 安全敏感輸入框的 IME 控制 → [IME 安全 checklist](/ux-design/03-input-mechanism/ime-security-checklist/)
- 表單場景的輸入設計 → [表單 UX 模式](/ux-design/03-input-mechanism/form-ux-pattern/)
