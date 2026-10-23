---
title: "Certificate（數位憑證）"
date: 2026-10-23
description: "文件裡的「憑證」要分辨指的是數位憑證還是存取憑證，或要判斷 TLS、mTLS、程式碼簽章用的憑證外洩之後要撤銷什麼時，查數位憑證由哪些部分組成、哪一部分是秘密"
weight: 494
tags: ["backend", "security", "pki"]
---

Certificate（數位憑證）是由憑證機構（CA）簽章、把一把公鑰綁定到一個身分（網域、服務或人）的資料，常見格式是 X.509，TLS、mTLS 與程式碼簽章都用它。數位憑證本身是公開的，任何人都可以讀；要保密的是與憑證中公鑰配對的私鑰。中文資料常把 credential 與 certificate 都寫成「憑證」，本站把前者寫成存取憑證（[Credential](/backend/knowledge-cards/credential/)），後者寫成數位憑證。

## 概念位置

數位憑證是信任鏈的一環：驗證方從對方送來的憑證一路檢查到自己信任的根憑證，見 [Certificate Chain and Trust Root](/backend/knowledge-cards/certificate-chain-trust/)。它的處置與存取憑證不同：存取憑證外洩時，撤銷那一份秘密它就失效；數位憑證外洩的若只是憑證本身，不需要處置，外洩的是私鑰時，要撤銷那張憑證，並換一把新的金鑰重新簽發，見 [Certificate Revocation](/backend/knowledge-cards/certificate-revocation/)。

## 可觀察訊號與例子

「平台保存所有連線的憑證」這句話有兩種讀法：平台保存連到各系統的帳號密碼與 API 金鑰（存取憑證），或平台保存各網域的 TLS 憑證與私鑰（數位憑證）。兩者外洩之後的處置不同，所以文件寫到「憑證」時要寫明是哪一種。憑證到期而服務沒有自動續期，是網站中斷的常見原因，續期的做法見 [Certificate Rotation and Renewal](/backend/knowledge-cards/certificate-rotation-renewal/)。

## 設計責任

數位憑證要列進清單管理：每一張憑證的用途、到期日、私鑰存放的位置與負責續期的人。私鑰與存取憑證一樣屬於秘密管理的範圍，憑證本身則可以公開。網站憑證的簽發、續期與撤銷流程見 [Website Certificate Lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/) 與 [7.5 傳輸信任與憑證生命週期](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/)。
