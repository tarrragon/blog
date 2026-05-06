---
title: "Certificate Chain and Trust Root"
date: 2026-04-23
description: "說明網站憑證鏈與信任根如何影響連線可用性與驗證結果"
weight: 147
---


Certificate chain and trust root 的核心概念是「憑證驗證依賴完整憑證鏈與受信任根」。伺服器端需要提供 leaf certificate 與中繼憑證，客戶端再以信任根驗證整條鏈。 可先對照 [TLS / mTLS](/backend/knowledge-cards/tls-mtls/)。

## 概念位置

憑證鏈與信任根是 [TLS / mTLS](/backend/knowledge-cards/tls-mtls/) 成功握手的基礎。鏈配置錯誤、根憑證不受信任或中繼遺失，都會造成 HTTPS 連線失敗。

## 可觀察訊號與例子

系統需要這個設計的訊號是不同平台連線結果不一致。網站在桌機正常但行動裝置失敗，常見原因是中繼憑證配置不完整或舊裝置信任根差異。

## 設計責任

設計要定義憑證鏈部署方式、兼容策略、檢測腳本與故障 [runbook](/backend/knowledge-cards/runbook/)。運維流程要把憑證鏈檢查納入部署 gate 與例行健康檢查。
