---
title: "Secret Management"
tags: ["機密管理", "Secret Management"]
date: 2026-04-23
description: "說明 token、key、password 與憑證如何保存、輪替與撤銷"
weight: 40
---


Secret management 的核心概念是「用受控流程管理可取得系統權限的秘密資料」。Secret 包含 API key、[database](/backend/knowledge-cards/database/) password、JWT signing key、[TLS](/backend/knowledge-cards/tls-mtls/) private key、webhook secret 與第三方 credential。

## 概念位置

Secret 是高風險操作能力。它們應集中放在受控系統中，並具備儲存位置、[authorization](/backend/knowledge-cards/authorization/)、使用範圍、輪替週期、撤銷流程與 [audit log](/backend/knowledge-cards/audit-log/)。

## 可觀察訊號與例子

系統需要 secret management 的訊號是服務開始連接 database、[broker](/backend/knowledge-cards/broker/)、雲端 API 或第三方支付。Webhook signing secret 洩漏後，攻擊者可能偽造進站事件；database 密碼洩漏後，資料存取邊界會失效。

## 設計責任

Secret 管理要包含 [least privilege](/backend/knowledge-cards/least-privilege/)、環境隔離、輪替演練、撤銷、版本管理與部署注入方式。[Runbook](/backend/knowledge-cards/runbook/) 應說明疑似洩漏時如何停用、輪替、追查與恢復。
