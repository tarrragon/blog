---
title: "Federation"
date: 2026-05-13
description: "跨系統信任與授權交換的聯邦機制"
weight: 254
---

Federation 的核心概念是「不同身份或資源系統之間建立可驗證信任關係，讓授權資訊可被交換使用」。它的責任是縮短跨域整合成本，同時維持邊界可追蹤。可對照 [workload-identity](/backend/knowledge-cards/workload-identity/) 與 [trust-boundary](/backend/knowledge-cards/trust-boundary/)。

## 概念位置

Federation 常出現在 SSO、跨雲工作負載授權與第三方服務整合。它把外部事件導入內部授權鏈，因此要和 [token-revocation](/backend/knowledge-cards/token-revocation/) 與 [audit-log](/backend/knowledge-cards/audit-log/) 共同設計。

## 可觀察訊號與例子

需要 federation 判讀的訊號是「外部身份事件發生後，內部權限收斂速度慢且回查困難」。例如供應商事件後，聯邦 token 仍在非預期服務活躍。

## 設計責任

聯邦信任要有定期重評估、分域撤銷與最小授權範圍。若只建立信任不做持續治理，federation 會把整合便利轉成長期風險擴散通道。
