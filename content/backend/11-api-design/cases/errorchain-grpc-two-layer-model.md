---
title: "11.C73 gRPC 兩層錯誤模型：status code 是保證層、richer detail 是選配層"
date: 2026-07-04
description: "標準模型全語言保證、richer error model 走 trailing metadata — proxy 與 logger 看不到、中間節點對錯誤細節是盲的"
weight: 73
tags: ["backend", "api-design", "case-study", "error-contract"]
---

這個案例的核心責任是提供錯誤契約分層的一手根據：保證層與選配層的傳播能力不同。

## 觀察

gRPC 官方 error guide：標準模型是成功回 `OK`、失敗「gRPC returns one of its error status codes instead, with an optional string error message」。richer error model（`google.rpc.Status`）「enables servers to return and clients to consume additional error details expressed as one or more protobuf messages」、提供常見錯誤型別（invalid parameters、quota violations、stack traces）、實作上「as trailing metadata in the response」。官方自列三個風險：跨語言實作不一致（僅 C++/Go/Java/Python/Ruby 支援、「broader support remains uncertain」）、proxies 與 loggers 看不到 trailing metadata 裡的 error detail、payload 過大會撞 header size 上限。

## 判讀

兩端張力在「保證層 vs 選配層」：status code 是所有語言 client 都拿得到的最低契約；richer detail 是選配、而且中間節點（proxy、logger）對它是盲的。中間服務作為 consumer 拿到 richer detail、作為 provider 轉發時不能假設下游也解得開 —— 轉譯責任落在它身上。錯誤契約設計要先分清哪些資訊放保證層（全鏈可見）、哪些放選配層（端到端可見、中間盲）。

## 對應大綱

11.11 錯誤鏈傳播章「錯誤契約的保證層與選配層」開場、「中間件對錯誤細節的可見性」段。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Error handling（gRPC 官方 docs）](https://grpc.io/docs/guides/error/) — 一手、現行版。已 WebFetch 驗證。

## 二手來源與狀態標注

richer model 語言支援「broader support remains uncertain」—— 不可寫成「gRPC 全語言支援 richer errors」。
