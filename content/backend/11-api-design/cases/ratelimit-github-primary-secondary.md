---
title: "11.C43 GitHub 雙層限流：primary / secondary 與 x-ratelimit 契約"
date: 2026-07-03
description: "單一維度配額擋不住真實濫用、前標準時代 x- header 與 IETF 命名並存的遷移期現實"
weight: 43
tags: ["backend", "api-design", "case-study", "rate-limit"]
---

這個案例的核心責任是提供大平台限流對外契約的實作切片、跟 IETF draft（C42）對照。

## 觀察

GitHub REST API 提供四個 header：`x-ratelimit-limit` / `-remaining` / `-used` / `-reset`（UTC epoch 秒）；超限回 403 或 429（文件未明確劃分兩者使用時機）；secondary limit 命中且有 `retry-after` 時要求等滿秒數；primary（每小時額度）與 secondary（並發、單端點吞吐、CPU、內容建立速率）分層；持續打限流請求可能導致 integration 被 ban。

## 判讀

secondary limit 的存在說明單一維度配額擋不住真實濫用模式。GitHub 是前標準時代 x- 前綴 header 的代表、與 IETF 命名並存 — 遷移期的現實是新 API 該出標準 header、client 仍要能讀 x- 系。「403 / 429 混用未明確化」是文件可指出的語意瑕疵（fact：文件確實未區分）。

## 對應大綱

11.9 對外流量語意（anchor）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Rate limits for the REST API（GitHub docs）](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
