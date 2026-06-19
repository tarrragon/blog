---
title: "安全敏感輸入框的 IME 控制 checklist"
date: 2026-06-19
description: "處理密碼、API key、伺服器路徑等 secret 的輸入框需要關閉 IME 的個人化學習和自動校正 — 安全要求而非 UX 偏好"
weight: 5
tags: ["ux-design", "input", "security", "ime", "mobile", "checklist"]
---

IME（Input Method Editor）的個人化學習功能會從使用者輸入中學習新詞彙，存入 IME 詞庫，跨 app 適用。在處理 secret 的輸入框中，這個功能把密碼、API key、伺服器路徑等敏感資訊存入了 IME 的持久化儲存 — 其他 app 的使用者在輸入時可能在建議列表中看到這些內容。

## 為什麼是安全問題

`enableIMEPersonalizedLearning` 控制的是 IME 是否從當前輸入框的內容學習新詞彙。預設值是 `true` — IME 會學習使用者輸入的所有內容。

在一般文字輸入場景中（聊天、筆記、email），IME 學習使用者的常用詞彙是合理的 — 提高打字效率，減少重複輸入。

在 CLI 場景中（[U.C3](/ux-design/cases/terminal-input-mechanism-absent/)），使用者可能輸入：

- 資料庫密碼：`mysql -p'MySecret123'`
- API key：`curl -H 'Authorization: Bearer sk-abc123...'`
- 伺服器路徑：`ssh admin@192.168.1.100`
- 環境變數：`export DB_PASSWORD=secret`

IME 學習這些輸入後，使用者在其他 app 打字時，IME 可能在建議列表中顯示 `MySecret123` 或 `sk-abc123` — 任何看到螢幕的人都能看到。

這個風險和密碼外洩的傳統路徑不同。傳統密碼外洩通常是資料庫被入侵或傳輸被攔截；IME 學習造成的洩漏是使用者在日常打字時被動暴露，使用者不會意識到 IME 記住了他們在另一個 app 輸入的密碼。

## Checklist

處理以下任何一類內容的輸入框，應全部通過此 checklist：

- 密碼、PIN 碼
- API key、token、secret
- 伺服器位址、連線字串
- CLI 指令（可能包含上述任何一類）
- 信用卡號碼
- 任何標示為 confidential 的欄位

### 必須關閉的 IME 控制

| 控制項     | 參數                                   | 理由                       |
| ---------- | -------------------------------------- | -------------------------- |
| 個人化學習 | `enableIMEPersonalizedLearning: false` | 防止 secret 進入 IME 詞庫  |
| 自動校正   | `autocorrect: false`                   | 防止 secret 被替換成字典詞 |
| 輸入建議   | `enableSuggestions: false`             | 防止 secret 出現在建議列表 |

### 建議的 keyboard type

| 場景       | Keyboard type   | 理由                        |
| ---------- | --------------- | --------------------------- |
| 密碼       | visiblePassword | 關閉自動校正，可選顯示/隱藏 |
| CLI 指令   | visiblePassword | 需要精確輸入，不要自動校正  |
| 信用卡號碼 | number          | 只需要數字鍵盤              |
| 連線字串   | url             | 有 `.`、`/`、`:` 快捷鍵     |

### Code review 檢查點

Review 安全敏感輸入框的 TextField 實作時，逐項確認：

1. `enableIMEPersonalizedLearning` 是否明確設為 `false`（不依賴預設值）
2. `autocorrect` 是否設為 `false`
3. `enableSuggestions` 是否設為 `false`
4. `keyboardType` 是否選擇了不會觸發自動行為的類型
5. 如果是密碼欄位，`obscureText` 是否按需求設定

## 平台差異

`enableIMEPersonalizedLearning` 是 Flutter 的 API，對應到不同平台的不同機制：

- **iOS**：對應 `UITextField.spellCheckingType = .no` 和相關 attribute。iOS 的 QuickType 學習機制由系統控制，app 只能建議不強制。
- **Android**：對應 `InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS` 等 flag。不同 IME app（Gboard、Samsung Keyboard、搜狗）對 flag 的遵守程度不一。

平台差異意味著 app 端的控制是「盡力而為」— 設定正確的 flag 是必要條件，但不保證所有 IME 都會遵守。安全敏感場景中，除了 IME 控制外，還應考慮 secure text entry（`obscureText: true`）讓畫面上不顯示明文。

## 下一步路由

- 四維度決策表總覽 → [輸入機制決策表](/ux-design/03-input-mechanism/four-dimension-decision/)
- IME 個人化學習在 monitoring 中的安全考量 → [monitoring 模組七 資安](/monitoring/07-security-privacy/)
- Terminal 場景的完整輸入設計 → [Terminal app 輸入設計](/ux-design/03-input-mechanism/terminal-input-design/)
