---
title: "3.C53 FINRA：S3 → SQS notification 大檔上傳"
date: 2026-05-18
description: "FINRA 金融監管、broker 上傳大檔、S3 → SQS notification → LFS、KMS + bucket policy + queue policy 三層稽核。"
weight: 53
tags: ["backend", "message-queue", "case-study", "aws-sqs"]
---

這個案例的核心責任是說明 S3 event notification 是 SQS 最經典 trigger、合規場景的 IAM 多層設定。

## 觀察

FINRA 金融監管機構、處理 broker-dealer 上傳大檔。Large File Service 用 S3 → SQS 通知模式：使用者上傳完 loading dock bucket、S3 推 SQS message 給 LFS、移檔後再推 "file available" SQS message 給下游。

## 判讀

S3 通知是 SQS 最經典 trigger、KMS + bucket policy + queue 權限的合規場景（金融業要保留稽核軌跡）。揭露金融場景的 IAM 設計不是一道權限、是多層稽核軌跡。

## 對應大綱

SQS 進階主題：SQS + Lambda event source / IAM + Cross-account。

## 下一步路由

回 [SQS vendor 頁](/backend/03-message-queue/vendors/aws-sqs/) 與 [7 security 模組](/backend/07-security-data-protection/)。

## 引用源

- [FINRA Large File Service](https://www.finra.org/about/how-we-operate/technology/blog/large-file-service-securely-uploading-large-files-to-s3)
