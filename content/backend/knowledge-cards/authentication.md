---
title: "Authentication"
tags: ["身分驗證", "Authentication"]
date: 2026-04-23
description: "說明系統如何確認呼叫者身份"
weight: 112
---

Authentication 的核心概念是「確認呼叫者是誰」。它可以透過 password、session、token、OAuth、certificate、API key 或 workload identity 完成。 可先對照 [Authorization](/backend/knowledge-cards/authorization/)。

## 跟其他概念的關係

Authentication 是 [authorization](/backend/knowledge-cards/authorization/) 的前置條件。系統先確認身份，再判斷該身份能否操作某個資源。身份確認失敗時，後續權限判斷缺少可靠基礎。

## 可觀察訊號與例子

系統需要 authentication 設計的訊號是服務需要區分使用者、管理員、service account 或第三方系統。Webhook 進站可以用 signature 驗證來源；service-to-service 可以用 [mTLS](/backend/knowledge-cards/tls-mtls/) 或 workload identity。

## 判斷條件與後果

Credential 生命週期的每一段，都可能讓身份確認不再代表持有者本人。保存方式讓 credential 能被讀出時，持有者以外的人也能用那個身份登入；沒有過期時，一次外洩永久有效；沒有撤銷時，發現外洩之後它仍然有效到過期；沒有輪替時，同一個 credential 用得越久，被外洩而沒有察覺的期間越長。錯誤回應把「帳號不存在」與「密碼錯誤」分開回時，攻擊者能列舉出有效的帳號；沒有登入風險的判斷時，異常地點或大量失敗之後的登入照常放行。安全事件之後追查是哪個身份與哪個 credential 被使用，依據是 [audit log](/backend/knowledge-cards/audit-log/)；沒有這份紀錄時，影響範圍只能整批假設。

人類身分這一側的方式選型（自建、委派、或裝置持有的金鑰對）走 [7.31 認證方式選型](/backend/07-security-data-protection/authentication-approach-selection/)，其中金鑰對那一種見 [passkey](/backend/knowledge-cards/passkey/)；登入交給外部系統之後的責任分界見 [identity provider](/backend/knowledge-cards/identity-provider/)。
