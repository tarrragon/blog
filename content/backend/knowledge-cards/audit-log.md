---
title: "Audit Log"
date: 2026-04-23
description: "說明高風險操作如何留下可追溯、可稽核的紀錄"
weight: 42
---

Audit log 的核心概念是「記錄誰在何時對哪個資源做了什麼高風險操作」。它支援事故調查、合規稽核、權限濫用追蹤與資料匯出責任判斷。

## 概念位置

Audit log 和一般 debug [log](../log/) 的責任不同。Debug log 幫助排查程式行為；audit log 保留安全與責任證據，因此需要更穩定的 schema、權限保護與保留策略。

## 可觀察訊號與例子

系統需要 audit log 的訊號是操作會影響權限、金錢、[PII](../pii/)、合約或資料匯出。管理員調整角色、客服查看敏感資料、使用者匯出訂單、API key 輪替都應留下 audit record。

## 設計責任

Audit log 要包含 actor、action、resource、result、reason、[request id](../request-id/)、來源位置與時間。它也需要防竄改、查詢權限、[retention](../retention/) 與 [alert](../alert/) 規則。
