---
title: "ACME Automation"
date: 2026-04-23
description: "說明網站憑證如何透過 ACME 自動簽發與續期"
weight: 147
---

ACME automation 的核心概念是「用標準化協議自動化網站憑證簽發與續期」。它透過 HTTP-01、DNS-01 或 TLS-ALPN-01 驗證網域控制權，減少手動更新憑證的風險。 可先對照 [Website Certificate Lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/)。

## 跟其他概念的關係

ACME 自動化是 [website certificate lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/) 的簽發與續期機制。它通常和 ingress、CDN、load balancer 或 [API Gateway](/backend/knowledge-cards/api-gateway/) 整合，確保多節點部署時維持一致憑證狀態。

## 可觀察訊號與例子

系統需要 ACME 自動化的訊號是站點數量增加、環境增加或憑證更新頻率提高。多網域 SaaS 服務若使用手動續期，憑證遺漏更新的風險會快速上升。

## 判斷條件與後果

ACME 自動化把續期交給機器之後，人只在流程失敗時介入，所以判斷看每一段失敗時是否有人收到通知、是否還有時間補救。challenge 類型決定自動化需要哪種權限：HTTP-01 要從外部連得到驗證路徑，DNS-01 要能寫入 DNS 紀錄，DNS-01 用的 DNS 憑證權限沒有收斂到 [least privilege](/backend/knowledge-cards/least-privilege/) 時，持有它的機器能改動驗證以外的紀錄。續期窗口與失敗重試留得太短時，簽發端暫時失敗、重試還沒成功憑證就已過期，使用者的瀏覽器顯示憑證錯誤。憑證簽到了而沒有分發到每一個 ingress、CDN 或 load balancer 時，部分節點仍送出舊憑證，到期那天只有那幾個節點出錯。這幾種失敗在憑證到期之前都看不見，所以續期失敗要接 [alert](/backend/knowledge-cards/alert/)，並有回復用的 [runbook](/backend/knowledge-cards/runbook/)。

這裡的網域驗證挑戰與多租戶身分接入要求租戶證明網域控制權是同型機制，判讀見 [7.40 B2B 多租戶的身分接入](/backend/07-security-data-protection/multi-tenant-identity-onboarding/)。
