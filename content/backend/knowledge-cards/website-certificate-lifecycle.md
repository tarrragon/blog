---
title: "Website Certificate Lifecycle"
date: 2026-04-23
description: "說明網站 TLS 憑證從簽發到續期與撤銷的全流程責任"
weight: 145
---

Website certificate lifecycle 的核心概念是「把網站憑證視為持續運作流程，而非一次性設定」。流程包含簽發、部署、驗證、監控、續期、輪替、撤銷與事故處理。

## 概念位置

網站憑證生命週期位在 [TLS / mTLS](/backend/knowledge-cards/tls-mtls/) 與 [secret management](/backend/knowledge-cards/secret-management/) 的交界。它同時影響可用性、資安與操作成本，因為憑證過期、鏈錯誤或私鑰洩漏都會直接影響服務可用性。

## 可觀察訊號與例子

系統需要網站憑證生命週期設計的訊號是服務會公開提供 HTTPS。電商網站在促銷高峰若遇到憑證過期，使用者會直接遇到瀏覽器安全警示並中斷交易。

## 設計責任

設計要定義簽發方式、部署邊界、過期門檻 [alert](/backend/knowledge-cards/alert/)、續期演練、撤銷流程、權限分離與 [runbook](/backend/knowledge-cards/runbook/)。高流量站點應把憑證健康納入 [dashboard](/backend/knowledge-cards/dashboard/) 與停機演練。
