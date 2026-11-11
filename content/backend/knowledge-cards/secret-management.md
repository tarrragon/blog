---
title: "Secret Management"
tags: ["機密管理", "Secret Management"]
date: 2026-04-23
description: "說明 token、key、password 等存取憑證如何保存、輪替與撤銷"
weight: 41
---

Secret management 的核心概念是「用受控流程管理可取得系統權限的秘密資料」。Secret 包含 API key、[database](/backend/knowledge-cards/database/) password、JWT signing key、[TLS](/backend/knowledge-cards/tls-mtls/) private key、webhook secret 與第三方 credential。

## 跟其他概念的關係

Secret 是高風險操作能力。它們應集中放在受控系統中，並具備儲存位置、[authorization](/backend/knowledge-cards/authorization/)、使用範圍、輪替週期、撤銷流程與 [audit log](/backend/knowledge-cards/audit-log/)。

## 可觀察訊號與例子

系統需要 secret management 的訊號是服務開始連接 database、[broker](/backend/knowledge-cards/broker/)、雲端 API 或第三方支付。Webhook signing secret 洩漏後，攻擊者可能偽造進站事件；database 密碼洩漏後，資料存取邊界會失效。

## 判斷條件與後果

一把 secret 洩漏時的影響範圍與收斂時間，由它平常怎麼被管理決定。Secret 的權限超過服務實際需要時（沒有照 [least privilege](/backend/knowledge-cards/least-privilege/) 發），洩漏一把 secret 就交出它能做的全部操作；各環境共用同一把 secret 時，staging 的洩漏就是 production 的洩漏；輪替沒有演練過時，寫死舊值的服務要到真正輪替時才出現，在新值生效的那一刻連線失敗；沒有版本管理時，新舊 secret 無法並存一段過渡期，輪替只能讓所有使用方同時切換；secret 寫進 image 或 repo 來部署時，撤銷之後舊值仍留在那些副本裡。疑似洩漏時的停用、輪替、追查與恢復彼此有先後依賴，事件當下才排順序會拉長暴露時間，所以這個順序事先寫進 [Runbook](/backend/knowledge-cards/runbook/)。
