---
title: "Federation"
date: 2026-05-13
description: "跨系統信任與授權交換的聯邦機制"
weight: 255
---

Federation 的核心概念是「不同身份或資源系統之間建立可驗證信任關係，讓授權資訊可被交換使用」。它的責任是縮短跨域整合成本，同時維持邊界可追蹤。可對照 [workload-identity](/backend/knowledge-cards/workload-identity/) 與 [trust-boundary](/backend/knowledge-cards/trust-boundary/)。

## 跟其他概念的關係

Federation 常出現在 SSO、跨雲工作負載授權與第三方服務整合。它把外部事件導入內部授權鏈，因此要和 [token-revocation](/backend/knowledge-cards/token-revocation/) 與 [audit-log](/backend/knowledge-cards/audit-log/) 共同設計。

## 可觀察訊號與例子

需要 federation 判讀的訊號是「外部身份事件發生後，內部權限收斂速度慢且回查困難」。例如供應商事件後，聯邦 token 仍在非預期服務活躍。

## 判斷條件與後果

聯邦信任建立之後，外部身分系統的事件會直接改變內部的授權狀態。信任的授權範圍大於整合所需時，一個外部身分被盜用，影響擴及所有接受聯邦 token 的服務；撤銷沒有分域時，撤銷的最小單位是整組聯邦信任，處理一個外部來源的事件要連同其他來源一起停掉。信任建立之後沒有定期重評估時，供應商出事之後聯邦 token 仍在非預期的服務裡活躍，內部權限收斂得慢，事後也難以回查，原因是信任關係建好之後不會自己失效。

主體是人的那一側，判讀走 [7.38 外部身分與本地紀錄](/backend/07-security-data-protection/external-identity-local-record-lifecycle/)（接上之後兩條生命週期怎麼走）與 [7.40 B2B 多租戶的身分接入](/backend/07-security-data-protection/multi-tenant-identity-onboarding/)（每個客戶各帶一組時要做成幾組設定）。
