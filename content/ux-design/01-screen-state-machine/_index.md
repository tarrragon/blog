---
title: "模組一：畫面狀態機設計"
date: 2026-06-19
description: "畫面狀態矩陣（顯示 / 操作 / 進入 / 退出）— 退出路徑為空 = UX 死胡同"
weight: 1
tags: ["ux-design", "state-machine", "navigation"]
---

回答「這個畫面有幾個狀態、每個狀態能做什麼、怎麼離開」。核心工具是畫面狀態矩陣。

## 對應 findings

| Finding | 來源                                                     | 內容                                                            |
| ------- | -------------------------------------------------------- | --------------------------------------------------------------- |
| UF-1    | [U.C1](/ux-design/cases/five-states-zero-exits/)         | 5 enum 狀態 0 退出路徑                                          |
| UF-2    | [U.C1](/ux-design/cases/five-states-zero-exits/)         | 操作盤點「前端引導」只描述顯示不描述操作和退出 — **本模組主寫** |
| UF-3    | [U.C1](/ux-design/cases/five-states-zero-exits/)         | 畫面狀態矩陣能快速暴露導航缺口                                  |
| UF-9    | [U.C4](/ux-design/cases/missing-enrollment-entry-point/) | 路由存在但 UI 不可達 = 死程式碼的 UX 版本                       |

## 待寫章節

- [x] 畫面狀態矩陣的定義與填寫方法
- [x] 從 BDD 操作盤點展開到狀態矩陣的五步驟
- [x] 路由可達性檢查（router 定義的路由 vs UI 可達的路由）
- [x] 反模式：假設使用者只走 happy path

## 跨分類引用

- → [testing 模組四 UI 自動化](/testing/04-ui-automation/)：狀態矩陣轉 widget test case
- → [testing 模組二 客戶端可觀測性](/testing/02-client-observability/)：狀態矩陣可加「可觀測性」欄位
- → [monitoring 模組八 商業利用](/monitoring/08-business-analytics/)：狀態轉換事件是 funnel 分析的原料
- ← [testing 模組一 測試策略](/testing/01-test-strategy-layers/)：三層測試中 screen state test 對應狀態矩陣
- ← work-log：[每個畫面都需要出口](/work-log/ux_screen_state_machine_design/)
