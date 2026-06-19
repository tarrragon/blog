---
title: "模組二：客戶端可觀測性"
date: 2026-06-19
description: "連線生命週期 log、protocol 訊息 log、使用者行為 log — log 設計是功能規格的一部分"
weight: 2
tags: ["testing", "observability", "logging", "client-side"]
---

回答「使用者的裝置上發生了什麼事」。log 設計應在功能規格階段完成，跟 API schema 同級。

## 對應 findings

| Finding | 來源                                                 | 內容                                          |
| ------- | ---------------------------------------------------- | --------------------------------------------- |
| TF-6    | [T.C4](/testing/cases/client-log-absent-debug-cost/) | 6 元件中 4 個零 log，2 個全是 W2 hotfix       |
| TF-7    | [T.C4](/testing/cases/client-log-absent-debug-cost/) | 事後補的 developer.log 格式不統一             |
| TF-9    | [T.C4](/testing/cases/client-log-absent-debug-cost/) | log 設計應在功能規格階段完成 — **本模組主寫** |

## 待寫章節

- [ ] 三層 log 設計（連線生命週期 / protocol 訊息 / 使用者行為）
- [ ] 功能規格中的 log 點定義方法
- [ ] 自架 log endpoint vs 商業方案的取捨判斷
- [ ] 「事後補 log」vs「設計產物 log」的品質差異

## 跨分類引用

- → [monitoring 模組二 Log Schema](/monitoring/02-log-schema/)：本模組教「設計 log 點」，monitoring 教「log 收集到之後怎麼處理」
- → [monitoring 模組七 資安](/monitoring/07-security-privacy/)：log 內容可能含 secret，SDK redaction 在這裡介入
- ← [ux-design 模組一](/ux-design/01-screen-state-machine/)：狀態矩陣可加「可觀測性」欄位
