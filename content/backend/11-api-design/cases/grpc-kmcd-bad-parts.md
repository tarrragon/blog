---
title: "11.C32 gRPC: The Bad Parts：cURL 測試不過的 API（反例）"
date: 2026-07-03
description: "反例：獨立實踐者的 gRPC 批評清單、debug 可及性判準、含生態已修補的平衡敘述"
weight: 32
tags: ["backend", "api-design", "case-study", "grpc"]
---

這個案例的核心責任是提供非 vendor 立場的 gRPC 獨立批評、跟 C30 互證。

## 觀察

批評點：非標準術語（unary RPC）墊高學習曲線、通不過「傳一個 cURL 範例給朋友」測試、瀏覽器無法處理 HTTP trailers 需 gRPC-Web 加 proxy、HTTP/3 採用遲緩、protobuf 要求完整解析整個訊息使大檔處理容易出錯、依賴管理長期無標準。文章同時承認 Buf CLI / ConnectRPC / Postman 支援已改善部分問題。

## 判讀

「批評 + 承認生態已修補」的平衡結構適合直接當教材敘事骨架。cURL 測試是「debug 可及性」這個選型維度的好判準 — 協議效率表不會告訴你 on-call 時能不能徒手戳一個 endpoint。

## 對應大綱

styles/grpc/「內部 RPC 的選型位置」（gRPC 邊界與代價段）。反例 / 邊緣。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [gRPC: The Bad Parts（Kevin McDonald）](https://kmcd.dev/posts/grpc-the-bad-parts/)
