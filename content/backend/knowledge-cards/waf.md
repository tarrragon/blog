---
title: "WAF"
date: 2026-04-23
description: "說明 Web Application Firewall 如何在入口層過濾常見攻擊與濫用"
weight: 122
---

WAF 的核心概念是「在流量進入 application 之前，先用規則擋掉明顯惡意或高風險的 request」。它通常部署在 edge、load balancer、reverse proxy 或 CDN 前後，用來保護公開入口與高暴露面功能。 可先對照 [Admin Endpoint](/backend/knowledge-cards/admin-endpoint/)。

## 跟其他概念的關係

WAF 位在流量入口與 application 之間。它適合處理 SQL injection（外層過濾；根治在資料存取層一律用佔位符，見 [SQL Injection](/backend/knowledge-cards/sql-injection/)）、XSS、惡意 bot、異常 payload、重放型濫用與明顯不符合路徑語意的 request。 可先對照 [Admin Endpoint](/backend/knowledge-cards/admin-endpoint/)。

## 可觀察訊號與例子

系統需要 WAF 的訊號是攻擊流量、濫用流量或掃描流量開始增加。公開 API、[Admin Endpoint](/backend/knowledge-cards/admin-endpoint/)、file upload 與 webhook 入口如果暴露在網際網路上，通常需要額外的 WAF 規則與例外管理。

## 判斷條件與後果

WAF 的維護流程缺哪一段，入口就出現對應的失效。規則不更新時，新的攻擊形態直接穿過；誤殺沒有處理流程時，合法 request 持續被擋，而回報沒有去處；沒有觀測指標時，分不出攔截量上升是攻擊增加還是規則誤殺；例外放行沒有紀錄與期限時，放行範圍只增不減；沒有回應流程時，告警出現了也不會轉成規則調整或來源封鎖。WAF 只看得到 request 的形態，看不到發出請求的是誰、是否有權做這件事，所以 application 層的輸入驗證、授權與速率限制各自保留，WAF 擔任前面一層的防護與降噪。

它擋的 XSS 是入口層的形態過濾，而根本的處置在輸出處理與內容安全政策，見 [cross-site scripting](/backend/knowledge-cards/cross-site-scripting/) 與 [content security policy](/backend/knowledge-cards/content-security-policy/)。
