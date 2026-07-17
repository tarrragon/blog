---
title: "輸入機制決策表"
date: 2026-06-19
description: "Keyboard type / submit model / IME policy / special keys 四個維度的決策框架 — 每個維度都是設計決策，影響 UI layout 和 protocol"
weight: 1
tags: ["ux-design", "input", "keyboard", "mobile", "decision"]
---

輸入機制是設計產物，在功能規格階段決定，和 API schema、畫面狀態矩陣同級。手機鍵盤的行為由多個參數控制，每個參數都是一個設計決策，影響使用者體驗、UI layout 和通訊協議。

## 四個決策維度

### Keyboard type：顯示哪種鍵盤

Keyboard type 決定使用者按下輸入框時出現什麼鍵盤。數字鍵盤、email 鍵盤、URL 鍵盤、一般文字鍵盤 — 每種鍵盤的按鍵配置和自動行為不同。

選擇判斷依據是「使用者要輸入什麼內容」。email 地址用 email 鍵盤（有 `@` 鍵），電話號碼用數字鍵盤，密碼或 CLI 指令用 `visiblePassword` 型別（避免自動校正和建議）。

一個遠端終端機 app 的輸入框用 `TextInputType.visiblePassword` — 因為 CLI 指令包含路徑分隔符、flag 縮寫等非自然語言內容，一般文字鍵盤會嘗試自動校正 `ls -la` 或 `/usr/bin/` 成其他東西（[U.C3](/ux-design/cases/terminal-input-mechanism-absent/)）。

### Submit model：怎麼送出輸入

Submit model 決定使用者輸入的內容何時傳送給系統。兩個基本選項：整行送出（使用者按 Enter/Send 後一次傳送整行）和逐字元送出（每個按鍵即時傳送）。

這個決策直接影響通訊協議設計（本章合成，UF-8 Derive）。整行送出代表每次傳送一個完整指令字串（`ls -la\n`），server 端按行處理。逐字元送出代表每個按鍵產生一個 WebSocket frame（`l`、`s`、` `、`-`、`l`、`a`），server 端需要處理單字元輸入，包括 Tab 補全和 Ctrl+C 這類立即回應的操作。

該終端機 app 選擇整行送出（`onSubmitted`），代表 Tab 補全在 client 端無法觸發（因為 Tab 不會單獨送出），但實作成本較低且協議設計較簡單。逐字元送出支援 Tab 補全和命令編輯，但 protocol 複雜度顯著提高。

### IME policy：輸入法的行為控制

IME（Input Method Editor）policy 控制手機輸入法的自動行為：自動校正、建議列、個人化學習。每個行為在某些輸入場景是幫助，在另一些場景是干擾或安全風險。

三個控制項各自有獨立的影響：

- `autocorrect`：自動校正把輸入替換成字典中的詞。CLI 指令和路徑不是自然語言，自動校正會破壞輸入內容。
- `enableSuggestions`：建議列在鍵盤上方顯示候選詞。在 terminal 場景中建議列遮擋畫面底部的終端機輸出。
- `enableIMEPersonalizedLearning`：IME 從使用者輸入中學習新詞，跨 app 適用。CLI 輸入可能包含密碼和路徑 — 這是安全問題，見 [安全敏感輸入框的 IME 控制 checklist](/ux-design/03-input-mechanism/ime-security-checklist/)。

### Special keys：特殊按鍵的處理

手機鍵盤沒有桌面鍵盤的 Esc、Tab、Ctrl、方向鍵。如果應用需要這些按鍵，必須自建 UI 元件提供。

該終端機 app 用底部工具列提供 Esc/Tab/Ctrl/方向鍵。這個工具列的設計（按鈕大小、排列、長按行為）是 UX 決策，不是實作細節。

## 決策表作為設計產物

四個維度的決策應該在功能規格中以表格形式記錄，讓 code review 時可以逐項對照實作是否符合規格。

| 維度         | 選項            | 理由                         |
| ------------ | --------------- | ---------------------------- |
| Keyboard     | visiblePassword | CLI 指令不適用自動校正       |
| Submit       | 整行送出        | protocol 簡單，犧牲 Tab 補全 |
| IME          | 全關            | 安全考量 + 非自然語言輸入    |
| Special keys | 底部工具列      | 手機無實體 Esc/Tab/Ctrl      |

該終端機 app 的六個 TextField 參數全是實機測試後 hotfix 補上的，沒有一個是事前規劃。每個參數都有 gotcha — 漏掉 `enableIMEPersonalizedLearning: false` 就是安全漏洞，漏掉 `autocorrect: false` 就是 UX 問題。事先決策並記錄在規格中，code review 時逐項勾選，比事後逐一發現問題的成本低。

四個維度在不同場景下的具體決策各有不同。CLI 場景的特殊需求見 [Terminal app 輸入設計](/ux-design/03-input-mechanism/terminal-input-design/)，安全敏感欄位的 IME 控制逐項列在 [IME 安全 checklist](/ux-design/03-input-mechanism/ime-security-checklist/)。Submit model 的選擇（整行 vs 逐字元）直接影響通訊協議的設計 — 這個交叉影響在 [testing 模組三 協議整合測試](/testing/03-protocol-integration-test/)中從 test 的角度分析。
