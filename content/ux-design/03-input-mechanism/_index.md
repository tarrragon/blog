---
title: "模組三：輸入機制設計"
date: 2026-06-19
description: "Keyboard type / submit model / IME policy / special keys — 輸入機制是設計產物，影響 UI layout 和 protocol"
weight: 3
tags: ["ux-design", "input", "keyboard", "mobile", "ime"]
---

回答「使用者怎麼輸入資料」。手機鍵盤和桌面鍵盤的差異比想像的大。

## 本模組回應的 UX 盲區

| Finding | 來源                                                      | 內容                                                          |
| ------- | --------------------------------------------------------- | ------------------------------------------------------------- |
| UF-6    | [U.C3](/ux-design/cases/terminal-input-mechanism-absent/) | 6 個 TextField 參數全是事後 hotfix — 本模組的核心案例         |
| UF-7    | [U.C3](/ux-design/cases/terminal-input-mechanism-absent/) | enableIMEPersonalizedLearning 有安全意涵（secret → IME 詞庫） |
| UF-8    | [U.C3](/ux-design/cases/terminal-input-mechanism-absent/) | 整行送出 vs 逐字元影響 protocol 設計 — 本模組的核心案例       |

## 章節

- [輸入機制決策表](/ux-design/03-input-mechanism/four-dimension-decision/) — Keyboard type / submit model / IME policy / special keys 四個維度的決策框架
- [Terminal app 輸入設計](/ux-design/03-input-mechanism/terminal-input-design/) — CLI 場景在手機上的特殊需求，整行 vs 逐字元送出對 protocol 的影響
- [表單 UX 模式](/ux-design/03-input-mechanism/form-ux-pattern/) — 表單輸入的驗證時機、auto-fill 支援、錯誤回饋設計
- [搜尋 UX 模式](/ux-design/03-input-mechanism/search-ux-pattern/) — Debounce / instant / suggestion 三種搜尋模式的取捨
- [安全敏感輸入框的 IME 控制 checklist](/ux-design/03-input-mechanism/ime-security-checklist/) — 密碼、API key 等 secret 輸入框需要關閉 IME 個人化學習

## 跨分類引用

- → [testing 模組三 協議整合測試](/testing/03-protocol-integration-test/)：整行 vs 逐字元影響 protocol test 斷言
- → [monitoring 模組七 資安](/monitoring/07-security-privacy/)：IME 個人化學習 = secret 洩漏風險
