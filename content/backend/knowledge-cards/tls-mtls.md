---
title: "TLS / mTLS"
date: 2026-04-23
description: "說明傳輸加密與雙向數位憑證驗證如何保護跨邊界資料流"
weight: 42
tags: ["backend", "security", "tls", "knowledge-card"]
---

TLS / mTLS 的核心概念是「保護資料在網路傳輸中的機密性、完整性與身份驗證」。TLS 通常驗證 server 並加密連線；mTLS 讓 client 與 server 彼此驗證憑證。 可先對照 [Authentication](/backend/knowledge-cards/authentication/)。

## 跟其他概念的關係

TLS 是公開網路服務的基本傳輸保護。mTLS 常用在 service-to-service、內部 API、金融或高敏感資料傳輸場景，讓服務身份以憑證、[authentication](/backend/knowledge-cards/authentication/) 與網路邊界共同判斷。什麼時候該選 mTLS 而不是共享密鑰簽章或 API key，以及選它要先具備哪些配套（CA、簽發與續期、撤銷清單或線上查詢），見 [7.34 機器憑證的機制選型](/backend/07-security-data-protection/machine-credential-mechanism-selection/)。每建一條新連線要做一次 TLS 握手，它在延遲與終結 TLS 那一層的 CPU 上的成本，以及連線重用攤平多少，見 [TLS Handshake（TLS 握手）的成本與連線重用](/backend/knowledge-cards/tls-handshake-cost/)。

## 可觀察訊號與例子

系統需要 mTLS 的訊號是內部服務會傳遞付款、[PII](/backend/knowledge-cards/pii/)、企業資料或高權限操作。服務身份與數位憑證輪替納入設計後，橫向移動風險可以被更早偵測與限制。

## 判斷條件與後果

TLS / mTLS 的故障多半出在憑證的管理，加密演算法本身很少是原因。沒有 [website certificate lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/) 與 [ACME automation](/backend/knowledge-cards/acme-automation/) 時，續期靠人記得，憑證過期的那一刻所有用戶端的連線都驗證失敗；沒有過期 [alert](/backend/knowledge-cards/alert/) 時，第一個訊號是使用者回報連不上。[certificate chain and trust root](/backend/knowledge-cards/certificate-chain-trust/) 設定不完整（伺服器沒有送出中繼憑證）時，本機沒有那張中繼憑證的用戶端驗證失敗，其他用戶端正常，症狀只出現在特定的用戶端上。[certificate rotation and renewal](/backend/knowledge-cards/certificate-rotation-renewal/) 沒有在測試環境演練過時，mTLS 兩端在換憑證的那一刻可能信任設定對不上，服務之間的呼叫中斷，而沒有故障排查的工具時，錯誤訊息只寫握手失敗。沒有 [certificate revocation](/backend/knowledge-cards/certificate-revocation/) 時，私鑰外洩之後那張憑證在到期之前都還能用來冒充身份。憑證、private key 與相關 credential 沒有納入 [secret management](/backend/knowledge-cards/secret-management/) 時，private key 散在設定檔與機器上，外洩之後查不出誰拿過。
