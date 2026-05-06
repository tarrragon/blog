---
title: "Migration"
date: 2026-05-06
description: "說明資料或結構變更如何在服務不中斷前提下受控推進"
tags: ["CI", "CD", "migration", "knowledge-card"]
weight: 10
---

Migration 的核心概念是「把舊狀態受控推進到新狀態」。它不只涉及資料庫 schema，也包含資料回填、相容窗口與發布順序。

## 概念位置

Migration 位在 build 之後、deploy 與 rollout 之前後的關鍵路徑，常與 release gate、rollback strategy 一起設計。

## 可觀察訊號

- 新舊版本需要共存一段時間。
- 發布步驟包含 schema 或資料形狀變更。
- 部署失敗時要判斷是否可回退或需要 forward fix。

## 接近真實服務的例子

後端服務先擴充 schema，再讓新版本寫入新欄位，最後收斂舊欄位讀取；整個過程需要 migration gate 與回退方案。

## 設計責任

Migration 要定義相容策略、執行順序、觀測指標與異常回復路由，避免部署成功但資料邏輯失效。
