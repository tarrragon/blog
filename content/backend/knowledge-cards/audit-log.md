---
title: "Audit Log"
tags: ["稽核日誌", "Audit Log"]
date: 2026-04-23
description: "說明高風險操作如何留下可追溯、可稽核的紀錄"
weight: 43
---


Audit log 的核心概念是「記錄誰在何時對哪個資源做了什麼高風險操作」。它支援事故調查、合規稽核、權限濫用追蹤與資料匯出責任判斷。 可先對照 [Log](/backend/knowledge-cards/log/)。

## 概念位置

Audit log 和一般 debug [log](/backend/knowledge-cards/log/) 的責任不同。Debug log 幫助排查程式行為；audit log 保留安全與責任證據，因此需要更穩定的 schema、權限保護與保留策略。

## 可觀察訊號與例子

系統需要 audit log 的訊號是操作會影響權限、金錢、[PII](/backend/knowledge-cards/pii/)、合約或資料匯出。管理員調整角色、客服查看敏感資料、使用者匯出訂單、API key 輪替都應留下 audit record。

## 設計責任

Audit log 要包含 actor、action、resource、result、reason、[request id](/backend/knowledge-cards/request-id/)、來源位置與時間。它也需要防竄改、查詢權限、[retention](/backend/knowledge-cards/retention/) 與 [alert](/backend/knowledge-cards/alert/) 規則。

開啟時機也是設計的一部分：多數雲端平台的資料存取類紀錄預設關閉，例如 GCP 的 Data Access audit log，而 audit log 只記錄開啟之後的事件，事後要調查時，開啟之前的存取查不回來。所以開啟的時點要排在它要記錄的那類存取開始之前，例如切換管理通道的同一天，見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)的〈組織層級的護欄與稽核紀錄〉。開啟之後實際做一次它要記錄的存取、查到那一筆紀錄才算開對：雲端的稽核設定常分成好幾種類型，開錯類型時設定照樣被接受、紀錄一筆都沒有（見[平常不動作的防護機制的部署驗證](/report/protection-proves-itself-by-firing/)）。
