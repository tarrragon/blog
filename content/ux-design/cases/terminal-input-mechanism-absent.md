---
title: "U.C3 終端機文字輸入機制未設計、事後 hotfix 補 TextField"
date: 2026-06-19
description: "Flutter 終端機 app 的鍵盤輸入完全未設計 — 沒有 TextField、沒有 keyboard type 選擇、沒有 IME 控制。W2 修復時才補上 TextField + 6 個參數（enableSuggestions/autocorrect/enableIMEPersonalizedLearning/keyboardType/textInputAction/onSubmitted），全是散落 hotfix"
weight: 3
tags: ["ux-design", "case-study", "input", "keyboard", "mobile", "terminal", "flutter"]
---

這個案例的核心責任是說明輸入機制是設計產物（在企劃階段決定），不是實作細節（在寫 code 時順便加）。

## 觀察

app_tunnel 的 Terminal 畫面在 W2 修復前沒有任何文字輸入元件。使用者只能透過底部工具列的特殊鍵（Esc/Tab/Ctrl/方向鍵）操作終端機，無法打字。

W2-001 修復時加入的 `TextField` 及其參數：

```dart
TextField(
  keyboardType: TextInputType.visiblePassword,   // 避免自動校正
  enableSuggestions: false,                       // 關閉建議列
  autocorrect: false,                             // 關閉自動校正
  enableIMEPersonalizedLearning: false,           // 關閉 IME 個人化學習
  onSubmitted: _submitInput,                      // Enter 送出整行
  textInputAction: TextInputAction.send,          // 鍵盤顯示「傳送」
)
```

每個參數都是一個設計決策，但沒有一個是事前規劃的 — 全部是寫 code 時臨時判斷。

| 設計決策                               | 事前規劃 | 事後 hotfix 的風險                                             |
| -------------------------------------- | -------- | -------------------------------------------------------------- |
| `visiblePassword`                      | 沒有     | 如果用預設 `text`，iOS 會自動校正 `ls -la` 成其他東西          |
| `enableSuggestions: false`             | 沒有     | 建議列遮擋終端機畫面下方                                       |
| `autocorrect: false`                   | 沒有     | 路徑 `/usr/bin/` 可能被校正                                    |
| `enableIMEPersonalizedLearning: false` | 沒有     | CLI 輸入含密碼和路徑，IME 學習是安全風險                       |
| `onSubmitted`（整行送出）              | 沒有     | 如果逐字元送出，Tab 補全和命令編輯需要完全不同的 protocol 設計 |
| `TextInputAction.send`                 | 沒有     | 如果用 `newline`，使用者按 Enter 會換行不送出                  |

## 判讀

1. **輸入設計影響 UI layout 和 protocol**。`onSubmitted`（整行送出）vs 逐字元即時送出不只是 UI 問題 — 整行送出代表 protocol 層送的是 `command\n`，逐字元送出代表每個按鍵都是一個 WS frame。這個決策應該在 protocol spec 階段就做，因為它影響 server 端的行為預期。

2. **IME 控制有安全意涵**。`enableIMEPersonalizedLearning: false` 不只是 UX 偏好 — CLI 輸入可能包含資料庫密碼、API key、伺服器路徑。IME 學習這些內容等於把 secret 存到了 IME 的詞庫裡，跨 app 可用。這是安全問題，不是 UX 問題。

3. **事後 hotfix 的六個參數每個都有 gotcha**。如果這些決策在企劃階段做，可以寫成決策表並在 code review 時對照。事後 hotfix 時開發者可能漏掉其中一兩個（例如只加 `autocorrect: false` 但忘了 `enableIMEPersonalizedLearning: false`），漏掉的那個就成為安全漏洞。

## 策略

1. **功能規格新增「輸入機制決策表」**：keyboard type / submit model / IME policy / special keys 四個維度，每個列出選項和取捨理由。
2. **輸入機制跟 protocol 一起設計**：「整行送出」還是「逐字元」決定了 WS 訊框的設計，必須在 protocol spec 階段決定。
3. **安全敏感參數強制列入 review checklist**：`enableIMEPersonalizedLearning`、`autocorrect` 在處理 secret 的輸入框中是安全要求，不是可選項。

## 下一步路由

- 想設計 mobile 輸入機制 → [模組三：輸入機制設計](/ux-design/)
- 想看 protocol 跟輸入的關聯 → [T.C1 WS frame type](/testing/cases/ws-text-binary-frame-mock-blindspot/)（sendData 的型別決策）
- 想做安全審查 → 待補：CLI 輸入安全 checklist
