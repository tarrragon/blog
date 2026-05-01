---
title: "6.15 Environment Parity 與漂移控制"
date: 2026-05-01
description: "把 staging / preprod / prod 之間的差異作為一級風險"
weight: 15
---

## 大綱

- environment parity 的核心：staging 通過不代表 prod 安全、parity 越低 release 風險越高
- 漂移來源：配置、scale、資料量、流量模式、依賴版本、infra 拓撲
- 12-factor 的 dev/prod parity 原則延伸到 staging 層
- shadow traffic / dark launch：用 prod 流量驗證 staging
- production-like data：PII-safe synthetic data vs production sample
- canary 環境的定位：staging 跟 prod 之間的緩衝
- 跟 [6.10 contract testing](/backend/06-reliability/contract-testing/) 的整合：契約 + parity 才覆蓋變更風險
- 跟 [6.16 test data](/backend/06-reliability/test-data-management/) 的整合：parity 需要可控的 production-like data
- 反模式：staging 用單機、prod 多區；staging 流量是合成的小量；staging 無真實依賴版本

## 判讀訊號

- staging 通過、prod 上線失敗、根因是配置 / scale / 資料量差異
- staging 跟 prod 用不同 DB engine 版本 / cache 配置
- shadow traffic 從未啟用、staging 流量靠手動測試
- prod-only bug 反覆出現、staging 永遠重現不出
- 環境差異無 owner、漂移無 review

## 交接路由

- 05 部署：環境拓撲一致性
- 06.10 contract testing：契約覆蓋環境邊界
- 06.16 test data：production-like data 來源
- 08.5 postmortem：parity 漂移作為事故根因類別
