---
title: "Authentication"
tags: ["身分驗證", "Authentication"]
date: 2026-04-23
description: "說明系統如何確認呼叫者身份"
weight: 111
---

Authentication 的核心概念是「確認呼叫者是誰」。它可以透過 password、session、token、OAuth、certificate、API key 或 workload identity 完成。

## 概念位置

Authentication 是 [authorization](/backend/knowledge-cards/authorization/) 的前置條件。系統先確認身份，再判斷該身份能否操作某個資源。身份確認失敗時，後續權限判斷缺少可靠基礎。

## 可觀察訊號與例子

系統需要 authentication 設計的訊號是服務需要區分使用者、管理員、service account 或第三方系統。Webhook 進站可以用 signature 驗證來源；service-to-service 可以用 [mTLS](/backend/knowledge-cards/tls-mtls/) 或 workload identity。

## 設計責任

Authentication 要處理 credential 保存、過期、撤銷、輪替、錯誤回應、登入風險與 [audit log](/backend/knowledge-cards/audit-log/)。安全事件後要能追查是哪個身份與 credential 被使用。
