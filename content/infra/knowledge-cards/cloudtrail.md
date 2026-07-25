---
title: "CloudTrail"
date: 2026-06-26
description: "AWS 的 API 層稽核日誌服務，記錄誰在什麼時候對什麼資源做了什麼操作"
weight: 10
tags: ["infra", "knowledge-cards", "cloudtrail", "audit"]
---

CloudTrail 的核心職責是把 AWS 帳號內每一個 API 呼叫記錄成可查詢的稽核日誌 — 哪個身分、在什麼時間、對哪個資源、呼叫了哪個 API、結果是成功還是拒絕。它是事故排查和合規稽核的事實來源，記錄的「身分」對應 [IAM](/infra/knowledge-cards/iam/) 裡的 identity。

## 概念位置

CloudTrail 在 infra 治理裡的角色是「發生了什麼」的最後防線。人工變更日誌記錄「為什麼改」，CloudTrail 記錄「改了什麼」— 兩者一起才能從事故回推到可回退的操作。

CloudTrail 預設記錄 management event（建立、修改、刪除資源的 API 呼叫）並保留 90 天可查閱。要長期保存或記錄 data event（S3 物件存取、Lambda 呼叫等更細粒度的操作），需要建立 trail 並指定 [S3](/infra/knowledge-cards/s3/) bucket 儲存。

## 可觀察訊號

以下狀況指向 CloudTrail 的使用場景：

- 事故排查需要回答「誰在過去 24 小時改過這個 security group」— CloudTrail 的 `LookupEvents` API 可以按事件名稱、資源類型或使用者名稱查詢
- 安全稽核要求提供「過去 90 天內所有 IAM policy 變更的紀錄」— CloudTrail 是標準的證據來源
- 發現不預期的資源變更（drift），需要確認是人為操作還是自動化觸發 — CloudTrail 的 `userIdentity` 欄位區分人類使用者和 assume-role 的服務

## 設計責任

使用 CloudTrail 時要決定：

- **保留期限**：預設 90 天免費查閱；超過需要建 trail 存到 S3，費用是 S3 儲存成本
- **事件範圍**：management event 預設開啟；data event（S3 物件讀寫、Lambda invoke）要額外設定，且量大時儲存成本可觀
- **跨帳號整合**：多帳號架構下，Organization trail 可以把所有帳號的事件集中到一個 S3 bucket
- **存取控制**：CloudTrail 的 S3 bucket 本身要限制存取 — 能修改稽核日誌等於能掩蓋操作痕跡

## 鄰卡

- [IAM](/infra/knowledge-cards/iam/) — CloudTrail 記錄的是 IAM 身分的 API 呼叫
- [Drift](/infra/knowledge-cards/drift/) — CloudTrail 是追查 drift 來源（誰手動改了什麼）的工具
