---
title: "Secret Management"
date: 2026-04-23
description: "說明 token、key、password 與憑證如何保存、輪替與撤銷"
weight: 40
---

Secret management 的核心概念是「用受控流程管理可取得系統權限的秘密資料」。Secret 包含 API key、database password、JWT signing key、TLS private key、webhook secret 與第三方 credential。

## 概念位置

Secret 是高風險操作能力。它們應集中放在受控系統中，並具備儲存位置、存取權限、使用範圍、輪替週期、撤銷流程與 audit。

## 可觀察訊號與例子

系統需要 secret management 的訊號是服務開始連接資料庫、broker、雲端 API 或第三方支付。Webhook signing secret 洩漏後，攻擊者可能偽造進站事件；資料庫密碼洩漏後，資料存取邊界會失效。

## 設計責任

Secret 管理要包含最小權限、環境隔離、輪替演練、撤銷、版本管理與部署注入方式。Runbook 應說明疑似洩漏時如何停用、輪替、追查與恢復。
