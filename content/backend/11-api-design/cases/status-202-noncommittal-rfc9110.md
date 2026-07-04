---
title: "11.C66 RFC 9110 202 Accepted：接受不等於承諾、HTTP 沒有回傳非同步結果的機制"
date: 2026-07-04
description: "202 是規範明文的 intentionally noncommittal：一旦回了 202、協定層不再有管道通知最終失敗、通知責任移轉到應用層"
weight: 66
tags: ["backend", "api-design", "case-study", "error-contract"]
---

這個案例的核心責任是提供「先接受、後失敗」模式的規範根據：202 的責任移轉是 HTTP 明文設計。

## 觀察

RFC 9110 §15.3.3（Internet Standard）原文：「The request might or might not eventually be acted upon, as it might be disallowed when processing actually takes place. There is no facility in HTTP for re-sending a status code from an asynchronous operation.」以及「The 202 response is intentionally noncommittal.」規範同時建議 202 的回應內容「ought to describe the request's current status and point to (or embed) a status monitor」。

## 判讀

「intentionally noncommittal」加「no facility for re-sending a status code」合起來是規範層的責任移轉聲明：一旦回了 202、HTTP 協定本身不再提供任何管道通知最終失敗 —— 通知責任落到應用層（status monitor、polling endpoint、callback）、且規範只用「ought to」要求 provider 提供、consumer 得主動來查。consumer 把 202 當終局成功、最終失敗就靜默消失。這是 status 表達力的時間軸邊界：status 只描述「收到當下」、描述不了「之後會不會成」。

## 對應大綱

11.11 status 表達力邊界章「非同步 / 延遲失敗」段（與 C65 的 LRO 出口、C44 AIP-151 Operation 相互印證）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [HTTP Semantics §15.3.3（RFC 9110）](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.3.3) — 一手 IETF spec、Internet Standard（STD 97）。

## 二手來源與狀態標注

RFC 9110 全文超出 WebFetch 摘要視窗、逐字原文以 rfc-editor 官方 .txt 直接取回抽段核對 —— 同源同權威、驗證工具為 curl 非 WebFetch。
