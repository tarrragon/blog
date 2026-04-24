---
title: "7.5 傳輸信任與憑證生命週期"
date: 2026-04-24
description: "整理 TLS/mTLS、簽章請求與憑證治理的大綱與路由"
weight: 75
---

本章的責任是定義傳輸信任模型的觀念邊界。核心輸出是跨邊界信任判讀與憑證生命周期路由，讓服務設計可一致評估風險。

## 大綱

- 傳輸信任模型：client-server、service-to-service、edge-to-origin
- TLS / mTLS 判讀：身份驗證、憑證鏈、錯誤回應策略
- 憑證生命周期：簽發、部署、輪替、撤銷、回查
- 自動化邊界：ACME、證書更新節奏與失效窗口
- 事件映射：會話劫持、憑證外洩、過期中斷
- 路由章節：05 部署、08 incident-response
