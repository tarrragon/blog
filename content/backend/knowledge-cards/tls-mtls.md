---
title: "TLS / mTLS"
date: 2026-04-23
description: "說明傳輸加密與雙向憑證驗證如何保護跨邊界資料流"
weight: 41
---


TLS / mTLS 的核心概念是「保護資料在網路傳輸中的機密性、完整性與身份驗證」。TLS 通常驗證 server 並加密連線；mTLS 讓 client 與 server 彼此驗證憑證。 可先對照 [Authentication](/backend/knowledge-cards/authentication/)。

## 概念位置

TLS 是公開網路服務的基本傳輸保護。mTLS 常用在 service-to-service、內部 API、金融或高敏感資料傳輸場景，讓服務身份以憑證、[authentication](/backend/knowledge-cards/authentication/) 與網路邊界共同判斷。

## 可觀察訊號與例子

系統需要 mTLS 的訊號是內部服務會傳遞付款、[PII](/backend/knowledge-cards/pii/)、企業資料或高權限操作。服務身份與憑證輪替納入設計後，橫向移動風險可以被更早偵測與限制。

## 設計責任

TLS / mTLS 設計要包含 [website certificate lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/)、[ACME automation](/backend/knowledge-cards/acme-automation/)、[certificate chain and trust root](/backend/knowledge-cards/certificate-chain-trust/)、[certificate rotation and renewal](/backend/knowledge-cards/certificate-rotation-renewal/)、[certificate revocation](/backend/knowledge-cards/certificate-revocation/)、過期 [alert](/backend/knowledge-cards/alert/)、測試環境與故障排查。憑證、private key 與相關 credential 應納入 [secret management](/backend/knowledge-cards/secret-management/)。
