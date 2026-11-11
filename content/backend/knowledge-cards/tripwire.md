---
title: "Tripwire"
tags: ["重評估觸發器", "Tripwire"]
date: 2026-04-30
description: "說明風險決策在條件變化時如何自動回到評估流程"
weight: 255
---

Tripwire 的核心概念是「用可量測訊號讓風險決策在條件變化時回到評估流程」。它把治理決策從一次性同意，轉成可持續更新的閉環。 可先對照 [Security Exception](/backend/knowledge-cards/security-exception/)。

## 跟其他概念的關係

Tripwire 位在 [Security Exception](/backend/knowledge-cards/security-exception/)、[Release Freeze](/backend/knowledge-cards/release-freeze/) 與 [Escalation Policy](/backend/knowledge-cards/escalation-policy/) 之間。它把監控與流程訊號轉成「何時重新決策」的共通語言。

## 可觀察訊號

系統需要 tripwire 的訊號是：

- 例外決策存在到期與重評估需求
- 風險條件會隨版本、漏洞、外部公告持續變化
- 團隊需要在訊號達門檻時自動升級處理
- 治理決策需要可追蹤的觸發紀錄

## 接近真實網路服務的例子

供應鏈治理中，artifact 驗證失敗率連續超過門檻，tripwire 會觸發 release freeze 重評估；身分治理中，特權操作異常增長，tripwire 會觸發 exception 審查與權限收斂。

## 判斷條件與後果

Tripwire 的五個組成各自缺席時，重新決策的閉環斷在不同位置。trigger signal 量不到時，風險條件變了也沒有任何紀錄；threshold 沒有寫下數值時，觸發與否由當下看的人判斷，事後無從稽核；沒有 escalation owner 時，訊號觸發了而沒有人接手重評估；沒有 decision route 時，接手的人不知道該送進哪一個流程（release freeze 重評估或 exception 審查）；沒有關閉條件時，觸發狀態一直掛著，下一次觸發與這一次分不開。五項都在時，一次觸發才成為一筆可追蹤的重新決策。
