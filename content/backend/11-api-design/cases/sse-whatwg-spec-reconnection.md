---
title: "11.C55 WHATWG SSE spec：內建自動重連與 Last-Event-ID 補送"
date: 2026-07-04
description: "SSE 把重連與斷點續傳的協商鉤子寫進協議：自動重連、Last-Event-ID 補送、retry 欄位；補送實際保證仍看 server replay"
weight: 55
tags: ["backend", "api-design", "case-study", "realtime"]
---

這個案例的核心責任是提供 SSE 對外承諾的規範錨點：重連語意寫進協議本身。

## 觀察

WHATWG HTML Living Standard 的 Server-Sent Events 章節定義 `text/event-stream` 格式的四個欄位 `data` / `event` / `id` / `retry`。連線斷掉時 user agent 自動 reestablish（`readyState` 轉 `CONNECTING`、fire `error`、等 reconnection time 後重試）；重連時瀏覽器把最後收到的 event id 放進 `Last-Event-ID` HTTP request header 送給 server、server 據此可從該點往後補送。`retry` 欄位讓 server 動態設定重連間隔（整數毫秒）。邊界：一旦 user agent 主動 fail 掉連線、就不再嘗試重連。

## 判讀

SSE 把「重連 + 斷點續傳的協商鉤子」寫進協議層 —— 消費者拿到的承諾是自動重連加一個可用來補送的 id 契約。但補送的實際保證仍取決於 server 有沒有實作 replay：spec 只保證瀏覽器會送 `Last-Event-ID`、不強制 server 保存或重放事件。這是 SSE 跟 WebSocket（協議層對重連沉默、見 C56）最核心的承諾差異。

## 對應大綱

styles/realtime/「持久連線推送機制」（承諾差異表 SSE 欄、重連語意權威來源）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Server-sent events（WHATWG HTML Living Standard）](https://html.spec.whatwg.org/multipage/server-sent-events.html) — 一手 spec、Living Standard。
- [Using server-sent events（MDN）](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) — 開發者視角佐證（重連內建、單向），非規範層、作可讀性對照。
