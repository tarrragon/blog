---
title: "Stage 1 Findings：UX 設計案例 audit"
date: 2026-06-19
weight: 90
draft: true
description: "Case-first Stage 1 產物 — 從 U.C1~C4 四個 rich case 抽取 10 個 findings，標明 fact vs derive 分層和對應章節"
tags: ["ux-design", "case-first", "stage-1"]
---

## Findings 表

| #     | Finding                                                                      | Case | 對應模組 | Fact / Derive        |
| ----- | ---------------------------------------------------------------------------- | ---- | -------- | -------------------- |
| UF-1  | 5 個 enum 狀態 0 個退出路徑——退出路徑空白 = UX 死胡同                        | U.C1 | 模組一   | Fact                 |
| UF-2  | 操作盤點「前端引導」只描述顯示不描述操作和退出——BDD 到 UI 缺展開步驟         | U.C1 | 模組一   | Fact                 |
| UF-3  | 畫面狀態矩陣（顯示/操作/進入/退出 四欄）能快速暴露導航缺口                   | U.C1 | 模組一   | Derive（效率主張）   |
| UF-4  | biometricOnly 安全收益 vs 可用性代價——自用工具場景可用性優先                 | U.C2 | 模組二   | Fact                 |
| UF-5  | 開發環境遮蔽 gate 問題：模擬器行為讓認證被跳過                               | U.C2 | 模組二   | Fact                 |
| UF-6  | 6 個 TextField 參數都是設計決策但全是事後 hotfix——影響 UI layout 和 protocol | U.C3 | 模組三   | Fact                 |
| UF-7  | enableIMEPersonalizedLearning 有安全意涵（secret 洩漏到 IME 詞庫）           | U.C3 | 模組三   | Fact                 |
| UF-8  | 整行送出 vs 逐字元影響 protocol 設計——輸入設計必須跟 protocol spec 同步      | U.C3 | 模組三   | Derive（方法論主張） |
| UF-9  | 路由存在但 UI 不可達 = 死程式碼的 UX 版本                                    | U.C4 | 模組一   | Fact                 |
| UF-10 | go vs push 語意差異影響 UX（push 保留返回堆疊，go 替換）                     | U.C4 | 模組五   | Fact                 |

## SSoT 對應

| Frame                 | 主寫章節         | 其他章節 link      |
| --------------------- | ---------------- | ------------------ |
| 輸入機制影響 protocol | ux-design 模組三 | testing 模組三引用 |
| 畫面狀態矩陣          | ux-design 模組一 | testing 模組四引用 |
