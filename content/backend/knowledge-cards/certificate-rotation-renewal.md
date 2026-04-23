---
title: "Certificate Rotation and Renewal"
date: 2026-04-23
description: "說明網站憑證如何安全續期與輪替以避免停機"
weight: 148
---

Certificate rotation and renewal 的核心概念是「在不中斷服務的前提下更新憑證與私鑰」。續期關注到期前更新，輪替關注主動替換既有憑證與金鑰材料。

## 概念位置

續期與輪替是 [website certificate lifecycle](../website-certificate-lifecycle/) 的穩定性核心，並與 [downtime](../downtime/) 風險直接相關。流程設計不完整時，憑證到期會直接造成服務中斷。

## 可觀察訊號與例子

系統需要續期與輪替設計的訊號是憑證有效期縮短或多環境併行部署。支付入口在到期日前未完成灰度更新，可能在流量尖峰觸發連線失敗。

## 設計責任

設計要定義到期門檻 [alert](../alert/)、灰度部署、回滾條件、私鑰輪替、兼容測試與驗證清單。變更後應以 [dashboard](../dashboard/) 追蹤握手錯誤率與憑證剩餘天數。
