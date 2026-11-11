---
title: "Credential（存取憑證）"
date: 2026-04-23
description: "整理身分驗證與系統存取用秘密資料"
weight: 1
---

Credential 的核心概念是「讓主體能證明自己並取得存取權的秘密資料」。常見 credential 包含 password、API key、token、private key、service account secret 與 database credential。中文資料常把 credential 與 certificate 都寫成「憑證」，本站把 credential 寫成存取憑證；由憑證機構簽章、本身可以公開的數位憑證另見 [Certificate（數位憑證）](/backend/knowledge-cards/certificate/)，與數位憑證配對的私鑰屬於存取憑證。 可先對照 [Cutover / Switchover](/backend/knowledge-cards/cutover-switchover/)。

## 跟其他概念的關係

Credential 位在 authentication、authorization、secret management 與 service-to-service access 的交界。 可先對照 [Cutover / Switchover](/backend/knowledge-cards/cutover-switchover/)。

## 可觀察訊號

系統需要 credential 管理的訊號包括：多個服務共用高權限帳號、需要定期輪替、需要撤銷、或需要在不同環境使用不同存取權。

## 接近真實網路服務的例子

登入用 credential 要有過期與撤銷；database credential 要依服務分離；webhook secret 要能驗證來源；內部服務 credential 要配合 mTLS 或 signed request——這幾種之間怎麼選（秘密送不送得出去、撤銷一次影響誰、要什麼配套）見 [7.34 機器憑證的機制選型](/backend/07-security-data-protection/machine-credential-mechanism-selection/)。

## 判斷條件與後果

Credential 的生命週期從核發、初次交付、保存、輪替、撤銷、稽核到事故回復，缺哪一個階段就留下哪一種暴露。保存在原始碼或設定檔的明文裡時，讀得到那份檔案的人都拿得到它。沒有輪替時，一份外洩而沒被發現的 credential 一直有效；沒有撤銷時，發現外洩之後只能等它過期或整組換掉；沒有稽核時，事故之後查不出誰在什麼時候用它做了什麼；沒有事故回復的流程時，換發要臨時找出所有用到它的服務。權限範圍大於用途時，一份 credential 外洩的影響等於它碰得到的全部資源，多個服務共用一個高權限帳號就是這種情形，所以範圍依 least privilege 收到用途所需。核發與初次交付各只發生一次、也因此不在日常監控的觀測範圍內：這個交付動作能不能免掉、免不掉時核發與交付各要滿足什麼，見 [7.32 機器憑證的配發](/backend/07-security-data-protection/machine-credential-issuance/)。
