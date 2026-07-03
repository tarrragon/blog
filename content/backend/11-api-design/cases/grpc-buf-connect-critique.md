---
title: "11.C30 Buf Connect 發布文：對 grpc-go 的系統性批評"
date: 2026-07-03
description: "gRPC 部署邊界（trailers、瀏覽器、proxy）最完整的一手批評；發布方是競品、立場需標明"
weight: 30
tags: ["backend", "api-design", "case-study", "grpc"]
---

這個案例的核心責任是提供 gRPC 部署邊界的完整批評清單。Buf 是利益相關方、引用時標明；但 trailers 與瀏覽器不相容是可獨立驗證的協議事實。

## 觀察

發布文指 grpc-go 有 13 萬行手寫程式碼、近百個設定選項、不用 Go 標準庫而自帶 HTTP/2 實作、導致無法與其他 HTTP 流量共存；gRPC 協議要求端到端 HTTP/2 加 trailers、瀏覽器支援需要翻譯 proxy；不遵守 semver、debug 時連 `curl | jq` 都不可行。Connect 的對案：建在 net/http 上、同時支援 gRPC / gRPC-Web / Connect 三協議。

## 判讀

gRPC 的部署邊界（瀏覽器、proxy、trailers）是風格選型時常被忽略的維度 — 協議能力表不會列「你的 LB 過不過 trailers」。與 C32 的獨立批評互證後、批評點的可信度不依賴 Buf 的立場。

## 對應大綱

styles/grpc/「streaming 語意與部署邊界」（anchor）、11.2 風格選型（操作可及性軸、已引用）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Connect: a better gRPC（Buf blog）](https://buf.build/blog/connect-a-better-grpc)
