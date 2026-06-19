---
title: "模組三：輸入機制設計"
date: 2026-06-19
description: "Keyboard type / submit model / IME policy / special keys — 輸入機制是設計產物，影響 UI layout 和 protocol"
weight: 3
tags: ["ux-design", "input", "keyboard", "mobile", "ime"]
---

回答「使用者怎麼輸入資料」。手機鍵盤和桌面鍵盤的差異比想像的大。

## 對應 findings

| Finding | 來源                                                      | 內容                                                          |
| ------- | --------------------------------------------------------- | ------------------------------------------------------------- |
| UF-6    | [U.C3](/ux-design/cases/terminal-input-mechanism-absent/) | 6 個 TextField 參數全是事後 hotfix — **本模組主寫**           |
| UF-7    | [U.C3](/ux-design/cases/terminal-input-mechanism-absent/) | enableIMEPersonalizedLearning 有安全意涵（secret → IME 詞庫） |
| UF-8    | [U.C3](/ux-design/cases/terminal-input-mechanism-absent/) | 整行送出 vs 逐字元影響 protocol 設計 — **SSoT 主寫**          |

## 待寫章節

- [ ] 輸入機制四維度決策表（keyboard type / submit model / IME policy / special keys）
- [ ] Terminal app 輸入設計（CLI 特殊需求）
- [ ] 表單 UX 模式（validate / auto-fill / error feedback）
- [ ] 搜尋 UX 模式（debounce / instant / suggestion）
- [ ] 安全敏感輸入框的 IME 控制 checklist

## 跨分類引用

- → [testing 模組三 協議整合測試](/testing/03-protocol-integration-test/)：整行 vs 逐字元影響 protocol test 斷言
- → [monitoring 模組七 資安](/monitoring/07-security-privacy/)：IME 個人化學習 = secret 洩漏風險
