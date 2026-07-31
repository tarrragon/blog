---
title: "Identity Provider"
date: 2026-07-31
description: "登入要交給外部系統時，用來定位對方承擔了什麼、沒承擔什麼，以及這邊還剩下哪些責任"
weight: 430
tags: ["backend", "knowledge-card", "security", "authentication"]
---

Identity provider（身分提供者，常縮寫為 IdP）是集中保管帳號並代為驗證使用者的系統，驗證完之後對接入方發出一段可驗證的宣告，說明這是誰。企業內部常用的形態是目錄服務加上單一登入入口，消費端的形態是各家平台的「用某某帳號登入」。接入方（依協定用語稱為信賴方或服務提供者）拿到宣告之後建立自己的會話，對接的協定通常是 SAML 或 OIDC。它解的是 [authentication](/backend/knowledge-cards/authentication/) 這一段，而使用者手上拿什麼向它證明身分是另一個決定，見 [passkey](/backend/knowledge-cards/passkey/) 與 [credential](/backend/knowledge-cards/credential/)。

## 概念位置

它承擔的是[認證](/backend/knowledge-cards/authentication/)這一段——確認人是誰。授權（這個人能做什麼）通常留在接入方，因為權限與各服務自己的資源模型綁定；身分提供者能送過來的是群組或角色這類粗粒度的屬性，細部判斷見 [authorization](/backend/knowledge-cards/authorization/) 與 [authorization scope](/backend/knowledge-cards/authorization-scope/)。

要不要把登入交出去、以及交出去付什麼代價，判讀走 [7.31 認證方式選型](/backend/07-security-data-protection/authentication-approach-selection/)。交出去之後接入方仍然持有一筆本地紀錄，而它與外部身分是兩條各自獨立的生命週期，見 [7.38 外部身分與本地紀錄](/backend/07-security-data-protection/external-identity-local-record-lifecycle/)。每個客戶各帶一個的多租戶形態把它從一次選型變成一項可設定的能力，見 [7.40 B2B 多租戶的身分接入](/backend/07-security-data-protection/multi-tenant-identity-onboarding/)。

機器對機器的那一側用的是不同的機制與判讀軸，見 [workload identity](/backend/knowledge-cards/workload-identity/)。

## 可觀察訊號與例子

導入之後最常被誤判的是責任範圍。對方驗證使用者這件事做完了，而帳號**狀態**的變化預設不會傳過來——對方停用一個帳號時，接入方不會收到任何事件，本地紀錄與既有會話照常有效。要拿到這一類事件需要另接一條反向通道（帳號開通與停用、單一會話結束、安全事件推送各有各的協定），而對方支不支援是導入當下要問的問題。

另一個訊號是登入強度的上限落在對方手上。對方只支援密碼時，接入方就算想要更強的驗證方式也拿不到；對方的密碼政策鬆，實際強度就是那個鬆的水準。

## 設計責任

導入時要把三件事寫進契約而非留給事發當時：帳號狀態怎麼同步過來、使用者離開那個來源之後這邊的資料歸誰、以及對方故障時有沒有替代路徑。第三項最容易被跳過，而它的後果是對方的控制面出事時這邊沒有任何一條路能讓使用者進來。

退出成本要在選型階段就算進去。換一個身分提供者等於全體使用者重新註冊，憑證無法遷移，因此這個決定的可逆性遠低於多數技術選型。長生命週期的產品要把它與「不必自己碰密碼儲存」這項省下的工作放在同一張表上比較。

留給「沒有那個來源帳號的使用者」的備用登入路徑要與主路徑一起治理。它不看外部身分的狀態，於是對方停用帳號之後那條路對同一個人照樣開著——處置是把停用落到本地紀錄本身而不只是撤銷會話。
