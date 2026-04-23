---
title: "Credential"
date: 2026-04-23
description: "整理身分驗證與系統存取用秘密資料"
weight: 0
---

Credential 的核心概念是「讓主體能證明自己並取得存取權的秘密資料」。常見 credential 包含 password、API key、token、private key、service account secret 與 database credential。

## 概念位置

Credential 位在 authentication、authorization、secret management 與 service-to-service access 的交界。

## 可觀察訊號

系統需要 credential 管理的訊號包括：多個服務共用高權限帳號、需要定期輪替、需要撤銷、或需要在不同環境使用不同存取權。

## 接近真實網路服務的例子

登入用 credential 要有過期與撤銷；database credential 要依服務分離；webhook secret 要能驗證來源；內部服務 credential 要配合 mTLS 或 signed request。

## 設計責任

Credential 設計要包含保存方式、權限範圍、輪替、撤銷、稽核與事故回復。原則上應遵守 least privilege，避免單一 credential 擁有過大權限。
