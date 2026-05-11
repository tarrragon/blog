---
title: "Fail-forward"
date: 2026-05-11
description: "說明無法回到舊狀態時如何用受控前進完成修復"
weight: 157
tags: ["backend", "knowledge-card", "reliability", "incident-response"]
---

Fail-forward 的核心概念是「當回退代價高於前進修復時，用受控方式往新狀態完成修復」。它連接 [rollback strategy](/backend/knowledge-cards/rollback-strategy/)、[fallback plan](/backend/knowledge-cards/fallback-plan/) 與 [incident decision log](/backend/knowledge-cards/incident-decision-log/)，不是忽略失敗繼續推進。

## 概念位置

Fail-forward 位在 [rollback window](/backend/knowledge-cards/rollback-window/)、[containment](/backend/knowledge-cards/containment/) 與 [post-incident review](/backend/knowledge-cards/post-incident-review/) 之間。Rollback window 關閉後，團隊仍需要一條能限制影響、補資料、完成相容收斂的前進路線。

## 可觀察訊號

系統需要 fail-forward 的訊號是：

- 舊資料語意已被 contract 或不可逆寫入移除
- 回退會造成更大的資料不一致或客戶影響
- 新路徑有明確修補方案、停損條件與 owner
- 事故 decision log 需要記錄為何不回滾

## 接近真實網路服務的例子

資料庫 migration 已完成 contract 後，舊欄位被移除，回到舊版本會讓讀取路徑失效。此時比較可控的做法可能是暫停部分寫入、修補 mismatch、補 validation query，再讓新路徑收斂到可用狀態。

## 設計責任

Fail-forward 要定義 containment、修補步驟、預期效果、停止條件與回寫項目。它要搭配 [evidence package](/backend/knowledge-cards/evidence-package/) 與 [action item closure](/backend/knowledge-cards/action-item-closure/)，避免「不能回滾」被誤用成沒有證據的硬推。
