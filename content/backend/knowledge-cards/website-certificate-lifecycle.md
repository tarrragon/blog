---
title: "Website Certificate Lifecycle"
date: 2026-04-23
description: "說明網站 TLS 憑證從簽發到續期與撤銷的全流程責任"
weight: 146
---

Website certificate lifecycle 的核心概念是「把網站憑證視為持續運作流程，而非一次性設定」。流程包含簽發、部署、驗證、監控、續期、輪替、撤銷與事故處理。 可先對照 [TLS / mTLS](/backend/knowledge-cards/tls-mtls/)。

## 跟其他概念的關係

網站憑證生命週期位在 [TLS / mTLS](/backend/knowledge-cards/tls-mtls/) 與 [secret management](/backend/knowledge-cards/secret-management/) 的交界。它同時影響可用性、資安與操作成本，因為憑證過期、鏈錯誤或私鑰洩漏都會直接影響服務可用性。

## 可觀察訊號與例子

系統需要網站憑證生命週期設計的訊號是服務會公開提供 HTTPS。電商網站在促銷高峰若遇到憑證過期，使用者會直接遇到瀏覽器安全警示並中斷交易。

## 判斷條件與後果

憑證生命週期的每一個環節缺席，對應一種中斷或風險。過期門檻沒有 [alert](/backend/knowledge-cards/alert/) 時，自動續期失敗不會通知任何人，到期當下使用者看到瀏覽器安全警示，交易中斷；續期沒有演練時，續期流程壞掉要到過期那天才發現；沒有撤銷流程時，私鑰洩漏後舊憑證仍被信任到原定的到期日；簽發與部署權限沒有分離時，一個帳號外洩同時交出部署與簽發兩種能力；沒有 [runbook](/backend/knowledge-cards/runbook/) 時，鏈錯誤或過期的處置要在事故當下重新摸索。流量越高，每分鐘中斷的損失越大，所以高流量站點把憑證健康放進 [dashboard](/backend/knowledge-cards/dashboard/) 與停機演練。
