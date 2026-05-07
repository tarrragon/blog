---
title: "Deployment Dry Run"
date: 2026-05-06
description: "說明發布前如何用預演檢查部署條件與風險"
tags: ["CD", "deployment", "knowledge-card"]
weight: 9
---

Deployment Dry Run 的核心概念是「在正式部署前預演關鍵步驟」。它讓流程在低風險條件下先驗證 artifact、權限與目標環境配置。

## 概念位置

Deployment Dry Run 位在 build / test 完成後、production deploy 之前，通常以 preflight check、模擬發布或目標環境校驗實作。

## 可觀察訊號

- 正式部署常失敗於權限、路徑或配置差異。
- 團隊需要在不影響使用者前提下驗證部署條件。
- 發布流程包含高成本動作或不可逆步驟。

## 接近真實服務的例子

部署腳本先驗證 artifact 存在、環境密鑰可讀、目標 bucket 或 registry 可寫，再進入正式 deploy。

## 設計責任

Deployment Dry Run 要定義檢查範圍、成功條件、失敗回饋與執行時機，並和正式部署命令保持一致語意。
