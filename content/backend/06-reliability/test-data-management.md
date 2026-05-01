---
title: "6.16 Test Data Management"
date: 2026-05-01
description: "把 fixture / seed / production-like data 作為跨模組共用 artifact"
weight: 16
---

## 大綱

- test data 是驗證的隱形依賴：fixture 過期、seed 不一致、PII 外洩風險都從這裡來
- 資料層次：unit fixture、integration seed、staging dataset、production sample
- production data 進測試環境的風險：PII、合規、洩漏
- 遮罩 / 合成策略：tokenization、format-preserving encryption、synthetic generation
- 可重現性：seed 版本化、跟 schema 演進對齊
- fixture 跟 [6.10 contract](/backend/06-reliability/contract-testing/) 的整合：契約定義 fixture shape
- 跟 [6.15 environment parity](/backend/06-reliability/environment-parity/) 的整合：production-like data 是 parity 的一部分
- 跟 [07 資料保護](/backend/07-security-data-protection/) 的交接：PII 在測試環境的處理
- 反模式：拷 production DB 進 staging；fixture 寫死 production 帳號；synthetic data 跟真實分佈差太遠

## 判讀訊號

- 工程師為 debug 把 production data 拷到 local
- staging DB 含真實用戶 PII
- fixture 跟 schema 漂移、測試常壞但無 owner
- 新測試靠拷貼舊 fixture、變動範圍模糊
- production bug 重現不出、因為 staging 資料分佈不同

## 交接路由

- 06.10 contract testing：fixture shape 契約
- 06.15 environment parity：production-like data 來源
- 07 資料保護：PII 遮罩與最小揭露
