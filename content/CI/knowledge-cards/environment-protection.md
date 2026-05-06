---
title: "Environment Protection"
date: 2026-05-06
description: "說明目標環境的審核、權限與放行條件如何保護發布"
tags: ["CD", "environment", "knowledge-card"]
weight: 5
---

Environment Protection 的核心概念是「用環境層 gate 控制正式發布」。它把環境風險從 workflow 腳本外顯成可檢查規則。

## 概念位置

Environment Protection 位在部署 job 與目標環境之間，包含 reviewer、wait timer、branch policy 與 secret scope。

## 可觀察訊號

- 測試綠燈後仍需要人工批准才能進 production。
- 不同環境需要不同發布權限與審核規則。
- 發布失誤常來自權限配置或保護規則缺失。

## 接近真實服務的例子

GitHub Actions deploy job 指向 `production` environment，需指定 reviewer 批准後才可部署。staging 則採自動放行。

## 設計責任

Environment Protection 要定義環境分層、審核責任、發布時窗與例外流程，讓高風險發布有明確控制面。
