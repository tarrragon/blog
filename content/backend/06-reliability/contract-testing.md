---
title: "6.10 Contract Testing 與 Schema 演進"
date: 2026-05-01
description: "用契約測試驗證跨服務 / API / event schema 的相容性"
weight: 10
---

## 大綱

- contract testing 的核心：把 producer / consumer 的契約變成可驗證 artifact
- consumer-driven vs provider-driven 的取捨
- 契約驗證的三個層次：schema 結構、語意、向後相容性
- API 契約：OpenAPI / gRPC schema 演進規則
- Event schema 演進：Avro / Protobuf / JSON Schema 的 backward / forward compatibility
- DB schema 演進：欄位新增 / 移除 / 型別變更的 rollout 策略（跟 6.11 銜接）
- 跟 [6.1 CI](/backend/06-reliability/ci-pipeline/) 的整合：contract test 作為 release gate 條件
- vendor 取捨：Pact / Spring Cloud Contract / OpenAPI diff tool / Buf
- 反模式：契約只在 docs、無自動驗證；consumer 改 schema 不通知 producer；breaking change 靠口頭溝通

## 概念定位

Contract testing 是在服務邊界上驗證 producer 與 consumer 的相容性，責任是把跨團隊協作的隱性期待變成可執行的契約。

這一頁不只在驗 schema，而是在驗誰對誰承諾了什麼。當服務彼此頻繁演進，契約測試就是避免變更互相踩踏的最小保護層。

## 核心判讀

好的 contract testing 會明確劃出兼容視窗，並把驗證放進 CI 或 release gate。

判讀時看三件事：

- 契約是否對準真實 consumer，不是抽象假想 client
- schema evolution 是否有明確 compatibility window
- 失敗是否能回到責任邊界，而不是只看到測試紅燈

## 案例對照

- [GitHub](/backend/08-incident-response/cases/github/_index.md)：API 與平台整合面常需要維持可預測的契約。
- [Stripe](/backend/06-reliability/cases/stripe/_index.md)：外部整合的變更要能維持 backward compatibility。
- [Slack](/backend/08-incident-response/cases/slack/_index.md)：跨系統 webhook / event 契約失配會直接放大事故。

## 下一步路由

- 06.8 release gate：把契約驗證放進放行條件
- 06.11 migration safety：把 schema 演進變成可逆流程
- 06.16 test data：把契約案例轉成持久化 seed

## 判讀訊號

- 跨服務 deploy 順序錯誤導致 production 故障
- API 文件跟實作漂移、新接入服務踩坑
- event schema 變更後下游 consumer 解析失敗
- breaking change 靠 release note 標註、無工具強制
- contract 違規只在 staging 才發現、CI 階段無法攔截

## 交接路由

- 06.8 release gate：contract 通過作為放行條件
- 06.11 migration safety：DB schema 演進的契約驗證
- 06.14 dependency budget：依賴契約穩定性
- 06.15 environment parity：契約覆蓋的環境邊界
- 06.16 test data：fixture shape 契約
- 05 部署：跨服務 deploy 順序協調
- 06.17 feature flag：flag 不同分支的契約覆蓋
