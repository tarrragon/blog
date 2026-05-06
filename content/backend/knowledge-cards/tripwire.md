---
title: "Tripwire"
tags: ["重評估觸發器", "Tripwire"]
date: 2026-04-30
description: "說明風險決策在條件變化時如何自動回到評估流程"
weight: 254
---


Tripwire 的核心概念是「用可量測訊號讓風險決策在條件變化時回到評估流程」。它把治理決策從一次性同意，轉成可持續更新的閉環。 可先對照 [Security Exception](/backend/knowledge-cards/security-exception/)。

## 概念位置

Tripwire 位在 [Security Exception](/backend/knowledge-cards/security-exception/)、[Release Freeze](/backend/knowledge-cards/release-freeze/) 與 [Escalation Policy](/backend/knowledge-cards/escalation-policy/) 之間。它把監控與流程訊號轉成「何時重新決策」的共通語言。

## 可觀察訊號

系統需要 tripwire 的訊號是：

- 例外決策存在到期與重評估需求
- 風險條件會隨版本、漏洞、外部公告持續變化
- 團隊需要在訊號達門檻時自動升級處理
- 治理決策需要可追蹤的觸發紀錄

## 接近真實網路服務的例子

供應鏈治理中，artifact 驗證失敗率連續超過門檻，tripwire 會觸發 release freeze 重評估；身分治理中，特權操作異常增長，tripwire 會觸發 exception 審查與權限收斂。

## 設計責任

Tripwire 要定義 trigger signal、threshold、escalation owner、decision route 與關閉條件。設計重點是訊號可量測、門檻可稽核、觸發後流程可執行。
