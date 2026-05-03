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

## 概念定位

Environment parity 是把 staging、preprod 與 production 的差異視為一級風險，責任是讓驗證環境能代表真實上線條件。

這一頁不是要求三個環境完全相同，而是要求會影響行為的差異被識別、記錄與管理。沒有 parity，測試結論就會跟真實服務脫鉤。

## 核心判讀

判讀 parity 時，先看差異是否可見，再看差異是否會改變結果。

重點訊號包括：

- config drift 是否有清單與責任人
- data shape 是否接近 production
- infra parity 是否涵蓋 network、storage、identity
- release 前是否知道哪些差異會影響判讀

## 案例對照

- [Heroku](/backend/08-incident-response/cases/heroku/_index.md)：平台抽象高時，更要清楚環境行為差異。
- [GCP](/backend/08-incident-response/cases/gcp/_index.md)：區域、網路與權限設定差異會直接影響驗證結論。
- [GitHub](/backend/08-incident-response/cases/github/_index.md)：大規模部署時，環境差異通常先變成事故放大器。

## 下一步路由

- 6.11 migration safety：環境差異常常在 migration 暴露
- 6.8 release gate：把 parity 當作放行前檢查
- 6.13 perf regression gate：把環境差異排除在效能判讀外

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
- 08.5 [post-incident review](/backend/knowledge-cards/post-incident-review/)：parity 漂移作為事故根因類別
