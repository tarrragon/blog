---
title: "監控案例庫"
date: 2026-06-19
description: "監控體系的實作挑戰案例 — 由 monitor repo 實作過程中的撞牆記錄產生"
weight: 90
tags: ["monitoring", "case-study"]
---

本案例庫的來源與 testing / ux-design 不同：案例由 [tarrragon/monitor](https://github.com/tarrragon/monitor) 的實作過程產生，不是事前採集。

每個案例對應 monitor repo 的 `docs/challenges/` 中的一個撞牆記錄，經教學化處理後收錄於此。

## 預期案例（實作後產生）

| 預期主題                  | 觸發時機                    | 對應模組 |
| ------------------------- | --------------------------- | -------- |
| JSONL 查詢效能天花板      | 累積 > 1 萬筆               | 模組四   |
| 高併發寫入 buffer 策略    | 多 SDK 同時 flush           | 模組四   |
| SDK 離線 buffer 丟失      | 網路中斷 + buffer 滿        | 模組三   |
| 跨平台 timestamp 偏移     | JS/Dart/Python 時間精度不同 | 模組五   |
| 錯誤去重 fingerprint 設計 | 同一 exception 重複回報     | 模組三   |
| Redaction false positive  | 正常內容被誤判為 secret     | 模組七   |
| 聚合查詢掃描量爆炸        | 「過去 7 天趨勢」           | 模組四   |

案例庫會隨實作進展持續擴充。
