---
title: "模組一：畫面狀態機設計"
date: 2026-06-19
description: "畫面狀態矩陣（顯示 / 操作 / 進入 / 退出）— 退出路徑為空 = UX 死胡同"
weight: 1
tags: ["ux-design", "state-machine", "navigation"]
---

回答「這個畫面有幾個狀態、每個狀態能做什麼、怎麼離開」。核心工具是畫面狀態矩陣。

## 本模組回應的 UX 盲區

| Finding | 來源                                                     | 內容                                                              |
| ------- | -------------------------------------------------------- | ----------------------------------------------------------------- |
| UF-1    | [U.C1](/ux-design/cases/five-states-zero-exits/)         | 5 enum 狀態 0 退出路徑                                            |
| UF-2    | [U.C1](/ux-design/cases/five-states-zero-exits/)         | 操作盤點「前端引導」只描述顯示不描述操作和退出 — 本模組的核心案例 |
| UF-3    | [U.C1](/ux-design/cases/five-states-zero-exits/)         | 畫面狀態矩陣能快速暴露導航缺口                                    |
| UF-9    | [U.C4](/ux-design/cases/missing-enrollment-entry-point/) | 路由存在但 UI 不可達 = 死程式碼的 UX 版本                         |

## 章節

- [畫面狀態矩陣的定義與填寫方法](/ux-design/01-screen-state-machine/state-matrix-definition/) — 四欄矩陣（顯示 / 可用操作 / 進入條件 / 退出路徑）的定義與填寫步驟
- [從 BDD 操作盤點展開到狀態矩陣](/ux-design/01-screen-state-machine/bdd-to-state-matrix/) — 五步驟把「前端引導」展開成完整矩陣，補上操作和退出兩個容易遺漏的面向
- [路由可達性檢查](/ux-design/01-screen-state-machine/route-reachability/) — Router 定義的路由 vs UI 實際可達的路由，不可達路由 = 死程式碼的 UX 版本
- [反模式：假設使用者只走 happy path](/ux-design/01-screen-state-machine/anti-pattern-happy-path-only/) — 開發者容易只設計 happy path UI 的機制分析，用狀態矩陣系統性防止

## 跨分類引用

- → [testing 模組四 UI 自動化](/testing/04-ui-automation/)：狀態矩陣轉 widget test case
- → [testing 模組二 客戶端可觀測性](/testing/02-client-observability/)：狀態矩陣可加「可觀測性」欄位
- → [monitoring 模組八 商業利用](/monitoring/08-business-analytics/)：狀態轉換事件是 funnel 分析的原料
- ← [testing 模組一 測試策略](/testing/01-test-strategy-layers/)：三層測試中 screen state test 對應狀態矩陣
- ← work-log：[每個畫面都需要出口](/work-log/ux_screen_state_machine_design/)
