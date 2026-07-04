---
title: "11.C58 RFC 6202：long-polling 的機制代價與 fallback 定位"
date: 2026-07-04
description: "long-polling hold 住請求到有事件才回：header 開銷、三段網路延遲、每 client 佔一條連線是機制決定的、不是實作品質"
weight: 58
tags: ["backend", "api-design", "case-study", "realtime"]
---

這個案例的核心責任是提供 long-polling 機制代價的標準組織權威定義。

## 觀察

RFC 6202（Known Issues and Best Practices for the Use of Long Polling and Streaming in Bidirectional HTTP）定義 long polling 為 server「hold open（not immediately reply to）each HTTP request、responding only when there are events to deliver」。列出三項固有代價：header 開銷（每個 request-response pair 都帶完整 HTTP headers、payload 小時 header 佔比高）；延遲（maximal latency 超過三段網路傳輸 —— long poll response、下一個 long poll request、long poll response）；資源佔用（每個 client 同時 hold 住一條 TCP/IP connection 與一個 HTTP request）。相對 HTTP streaming、long polling 提供 canonical framing（每則訊息一個完整 response）、不需 application-level 訊息分隔。

## 判讀

long-polling 落在「消費者是瀏覽器或受限 HTTP 環境、訊息頻率低、可容忍每則一次往返延遲」的形狀。它每則訊息一次完整 request/response cycle、結構上就比持久連線重 —— 這是機制決定的、不是實作品質問題。這也是它作為相容性 fallback 而非首選的根據。

## 對應大綱

styles/realtime/「持久連線推送機制」（四機制承諾差異表 long-polling 欄、為何 long-polling 是 fallback）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Known Issues and Best Practices for the Use of Long Polling and Streaming in Bidirectional HTTP（RFC 6202）](https://datatracker.ietf.org/doc/html/rfc6202) — 一手 IETF spec、Informational RFC。

## 二手來源與狀態標注

RFC 為 2011 年、pre-WebSocket-普及的時代背景；它比較的對象是 HTTP streaming、不是 WebSocket。用來講 long-polling 內在機制代價很穩、「相對 WebSocket 多重」的對照要另配來源（見 C59）。
