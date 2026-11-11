---
title: "Certificate Rotation and Renewal"
date: 2026-04-23
description: "說明網站憑證如何安全續期與輪替以避免停機"
weight: 149
---

Certificate rotation and renewal 的核心概念是「在不中斷服務的前提下更新憑證與私鑰」。續期關注到期前更新，輪替關注主動替換既有憑證與金鑰材料。 可先對照 [Website Certificate Lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/)。

## 跟其他概念的關係

續期與輪替是 [website certificate lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/) 的穩定性核心，並與 [downtime](/backend/knowledge-cards/downtime/) 風險直接相關。流程設計不完整時，憑證到期會直接造成服務中斷。

## 可觀察訊號與例子

系統需要續期與輪替設計的訊號是憑證有效期縮短或多環境併行部署。支付入口在到期日前未完成灰度更新，可能在流量尖峰觸發連線失敗。

## 判斷條件與後果

續期與輪替流程缺了哪一個環節，決定憑證在哪個時間點造成中斷。沒有到期門檻的 [alert](/backend/knowledge-cards/alert/) 時，到期日要等握手開始失敗才被發現，那一刻服務已經中斷。新憑證一次換上全部節點、沒有灰度部署與回滾條件時，新憑證或新私鑰跟某一類 client 不相容，連線同時失敗，而且沒有退回舊憑證的路徑；兼容測試與驗證清單把這類不相容提前到換證之前發現。只續期而沒有輪替私鑰時，新憑證仍綁著原本那把私鑰，私鑰若已外洩，續期不會讓外洩失效。換證之後，[dashboard](/backend/knowledge-cards/dashboard/) 上的握手錯誤率與憑證剩餘天數，是確認新憑證在每個節點都生效的依據。
