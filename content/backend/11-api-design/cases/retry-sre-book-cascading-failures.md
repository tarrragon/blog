---
title: "11.C69 Google SRE Book：retry 放大與跨層疊乘、per-request 上限與 retry budget"
date: 2026-07-04
description: "retry 放大讓有效工作遞減；三層各 retry 3 次在底層變 64 次；建議 per-request 上限 + server-wide retry budget、provider 要用不同 code 分開可重試與不可重試"
weight: 69
tags: ["backend", "api-design", "case-study", "error-contract"]
---

這個案例的核心責任是提供接收方重試決策的量化判準、以及「retry 該放哪一層」的架構責任分配。

## 觀察

Google SRE Book「Addressing Cascading Failures」章：retry 放大例 —— 100 QPS 失敗、retry 疊加成 200 QPS、再 300 QPS、「fewer and fewer requests are able to succeed on their first attempt, so less useful work is being performed」。四條逐字建議：「Always use randomized exponential backoff when scheduling retries」；「Limit retries per request. Don't retry a given request indefinitely」；「Consider having a server-wide retry budget. For example, only allow 60 retries per minute in a process」；避免「amplifying retries by issuing retries at multiple levels」—— 三層各 retry 3 次會在最底層產生 64 次嘗試。另要求用不同 response code「separate retriable and nonretriable error conditions」。

## 判讀

這章把責任明確放到兩端：provider 要用 status/error 區分可重試與不可重試（這正是雙向契約的 provider 義務、對應 11.4 的第一刀）；consumer 要有 per-request 上限加全程序 retry budget。跨層疊乘（64 倍）說明 retry 決策必須在架構層指定「哪一層負責 retry」—— 責任沒分配時、每層的局部自保疊成全域攻擊。

## 對應大綱

11.11 接收方重試決策章「retry budget 量化判準」「retry 放哪一層」段、provider 的 retriable/nonretriable 標示義務（回扣 11.4）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Addressing Cascading Failures（Google SRE Book）](https://sre.google/sre-book/addressing-cascading-failures/) — 一手、官方站。已 WebFetch 驗證、正文完整取回。

## 二手來源與狀態標注

本章未討論 circuit breaker（取回內容確認）—— circuit breaker 段以 C71（Slack）承接。
