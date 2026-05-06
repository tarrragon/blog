---
title: "WAF"
date: 2026-04-23
description: "說明 Web Application Firewall 如何在入口層過濾常見攻擊與濫用"
weight: 121
---


WAF 的核心概念是「在流量進入 application 之前，先用規則擋掉明顯惡意或高風險的 request」。它通常部署在 edge、load balancer、reverse proxy 或 CDN 前後，用來保護公開入口與高暴露面功能。 可先對照 [Admin Endpoint](/backend/knowledge-cards/admin-endpoint/)。

## 概念位置

WAF 位在流量入口與 application 之間。它適合處理 SQL injection、XSS、惡意 bot、異常 payload、重放型濫用與明顯不符合路徑語意的 request。 可先對照 [Admin Endpoint](/backend/knowledge-cards/admin-endpoint/)。

## 可觀察訊號與例子

系統需要 WAF 的訊號是攻擊流量、濫用流量或掃描流量開始增加。公開 API、[Admin Endpoint](/backend/knowledge-cards/admin-endpoint/)、file upload 與 webhook 入口如果暴露在網際網路上，通常需要額外的 WAF 規則與例外管理。

## 設計責任

WAF 設計要定義規則更新、誤殺處理、觀測指標、例外放行與回應流程。它不應取代 application 層的輸入驗證、授權或速率限制，而是作為第一層防護與風險降噪。
