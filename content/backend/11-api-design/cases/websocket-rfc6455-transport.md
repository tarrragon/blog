---
title: "11.C56 RFC 6455：WebSocket 是雙向 transport、不內建投遞保證"
date: 2026-07-04
description: "WebSocket 給雙向管線、不給保證：協議層對投遞保證、ack、重連、斷點續傳全部沉默、留給應用層"
weight: 56
tags: ["backend", "api-design", "case-study", "realtime"]
---

這個案例的核心責任是提供 WebSocket 對外承諾的規範錨點：協議只給雙向 transport、可靠性語意外包給應用層。

## 觀察

RFC 6455 定義 WebSocket 為「two-way communication channel where each side can, independently from the other, send data at will」、由 opening handshake 加 basic message framing 構成、layered over 單一 TCP connection。協議對投遞保證、自動 ack、重連機制完全沉默 —— 只定義 framing 與 handshake 層、設計原則是 minimal framing、framing 之上不加額外語意。

## 判讀

WebSocket 給雙向管線、不給保證：投遞保證、ack、重連、斷點續傳全都是應用層自己要蓋的。這跟 SSE 把重連寫進協議（見 C55）是兩種相反的承諾形狀 —— SSE 內建重連、換來單向；WebSocket 給雙向、換來零內建可靠性。協議層的「沉默」是論點本身：引用時陳述為「協議未定義、留給應用層」、而非「明文禁止」。

## 對應大綱

styles/realtime/「持久連線推送機制」（承諾差異表 WebSocket 欄、投遞保證「不保證」出處）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [The WebSocket Protocol（RFC 6455）](https://www.rfc-editor.org/rfc/rfc6455) — 一手 IETF spec、Proposed Standard（Standards Track）。
- [The WebSocket API（MDN）](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API) — 開發者視角佐證（雙向、未提重連/投遞、基礎介面不支援 backpressure），缺席證據較弱、作佐證非主錨。
