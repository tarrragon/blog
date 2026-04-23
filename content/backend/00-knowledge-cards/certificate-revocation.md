---
title: "Certificate Revocation"
date: 2026-04-23
description: "說明憑證洩漏或誤發時如何撤銷並控制影響範圍"
weight: 149
---

Certificate revocation 的核心概念是「在憑證不再可信時快速宣布失效」。常見觸發情境是私鑰洩漏、錯誤簽發、身份資訊不再有效或資安事件需要立即切斷信任。

## 概念位置

憑證撤銷是 [website certificate lifecycle](../website-certificate-lifecycle/) 的事故處理能力，與 [secret management](../secret-management/) 與 [audit log](../audit-log/) 一起構成憑證風險控制邊界。

## 可觀察訊號與例子

系統需要撤銷流程的訊號是金鑰材料疑似外洩或錯誤部署到不該公開的環境。若缺少撤銷與替換流程，攻擊者可能持續利用舊憑證偽裝服務端點。

## 設計責任

設計要定義撤銷觸發條件、責任人、替換時序、客戶端影響評估、溝通流程與回復 [runbook](../runbook/)。事故後要以 [post-incident](../runbook/) 更新偵測與輪替策略。
