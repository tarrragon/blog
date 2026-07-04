---
title: "4.C20 獨立 status page：對外狀態源的失效域隔離"
date: 2026-07-04
description: "主站掛時自建 status page 跟著掛；事故溝通通道的可用性不能依賴被溝通的那個系統、要放在獨立 domain 與 infra"
weight: 20
tags: ["backend", "observability", "case-study"]
---

這個案例的核心責任是把失效域隔離用在事故的對外溝通通道。

## 觀察

Atlassian Statuspage 官方問題陳述：「when your website is down, so is your status page」；其託管做法「We host your page so it's available when you need it most – when you're down」；support docs 補充 custom domain 要用獨立 dedicated domain、否則 DNS provider 掛了 status page 也跟著掛。溝通 cadence 五原則：Communicate Early（快速確認、簡述已知影響、承諾後續更新）、Communicate Often（每 30 分更新、即使技術狀態沒變）、Communicate Precisely（誠實、清楚、透明）、跨通道一致、Own the Problem；主動溝通可「Halt the flood of support requests during an incident」。

## 判讀

事故溝通管道的可用性不能依賴被溝通的那個系統。status page 必須放在獨立 domain、獨立 codebase、獨立 infra（甚至獨立 DNS）、才能在主服務全滅時仍可達 —— 這是 out-of-band 用在對外播報通道。cadence 原則是為盲飛設計：沒有新資訊時、「我們仍在處理」本身就是要發布的狀態；主動發布降低湧入的客訴、讓人層訊號通道（客訴聚合、見 [4.C24](/backend/04-observability/cases/pagerduty-customer-liaison/)）不被 noise 淹沒。

## 對應大綱

觀測共命運章「out-of-band 訊號」段（對外狀態源）與「人層應對」段（主動溝通降 noise）。

## 引用源

- [Why you need a status page（Atlassian Statuspage）](https://www.atlassian.com/blog/statuspage/why-you-need-a-status-page) — vendor 一手。已 WebFetch 驗證。
- [Incident communication tips（Atlassian support docs）](https://support.atlassian.com/statuspage/docs/incident-communication-tips/) — vendor 一手。已 WebFetch 驗證。

## 二手來源與狀態標注

Atlassian 是賣 Statuspage 的 vendor、內容帶產品傾向 —— 引用取「失效域隔離 / cadence」工程原理、剝離「所以買我們的」行銷框架。
