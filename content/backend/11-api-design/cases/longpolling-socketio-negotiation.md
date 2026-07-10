---
title: "11.C59 Socket.IO：先 long-polling 再 upgrade WebSocket 的 transport negotiation"
date: 2026-07-04
description: "WebSocket 不保證能建立（proxy/防火牆會擋）、所以先用 long-polling 建連再 upgrade：fallback 的價值是相容性下限、不是效能"
weight: 59
tags: ["backend", "api-design", "case-study", "realtime"]
---

這個案例的核心責任是說明 long-polling 作為相容性 fallback 的選型定位。

## 觀察

Socket.IO 官方 docs 說明三種 transport（HTTP long-polling / WebSocket / WebTransport）。預設 client 先用 HTTP long-polling 建連、再嘗試 upgrade 到更好的 transport。退回 long-polling 的理由明確：「experience has shown that it is not always possible to establish a WebSocket connection、due to corporate proxies、personal firewall、antivirus software...」。效能對照：WebSocket 支援「great」但可能被 proxy 擋；HTTP long-polling 支援「best」但效能只「acceptable」、因為每個 packet 都要一個新的帶 headers 的 HTTP request。設計原則把 reliability 與 user experience 排在效能之前。

## 判讀

推送機制選型是「相容性 vs 效能」的權衡，純技術優劣決定不了結果。當消費者形狀含不可控網路環境（企業 proxy / 防火牆）時、系統要能 negotiate、退回 long-polling 保證可用性 —— long-polling 的價值正是它的相容性下限、不是效能。

## 對應大綱

styles/realtime/「持久連線推送機制」（transport fallback / negotiation、long-polling 的 fallback 定位）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [How it works（Socket.IO v4 官方 docs）](https://socket.io/docs/v4/how-it-works/) — 一手 vendor 官方 docs。

## 二手來源與狀態標注

Socket.IO 特定的 negotiation 策略（先 long-poll 再 upgrade）、不是通則 —— 有些 vendor 先試 WebSocket 再退回。引用時說清楚這是 Socket.IO 的策略。
