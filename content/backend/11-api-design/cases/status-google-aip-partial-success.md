---
title: "11.C65 Google AIP 部分成功立場：同步必原子、非同步才准部分成功且要顯式 opt-in"
date: 2026-07-04
description: "AIP-193 明文「不該支援 partial errors」、批次三部曲給出原子性階梯與 LRO 出口：部分成功要 client 顯式同意"
weight: 65
tags: ["backend", "api-design", "case-study", "error-contract"]
---

這個案例的核心責任是提供部分成功的大廠設計立場：跟 207（C64）相反的路線、以及原子性階梯的具體切分規則。

## 觀察

AIP-193（Errors、Approved）專節明文：「APIs **should not** support partial errors. Partial errors add significant complexity for users, because they usually sidestep the use of error codes, or move those error codes into the response message, where the user must write specialized error handling logic to address the problem.」出口是 long-running operations：「Methods that require partial errors **should** use long-running operations, and the method should put partial failure information in the metadata message.」

批次三部曲同構：AIP-231（Batch Get）「The operation **must** be atomic: it must fail for all resources or succeed for all resources (no partial success)」；AIP-233（Batch Create）與 AIP-234（Batch Update）規定同步批次必須原子、非同步批次才可支援部分成功 —— 且支援時 metadata 必須含 `map<int32, google.rpc.Status> failed_requests`、request 要有 `bool return_partial_success` 欄位讓 client 顯式 opt-in。

## 判讀

這組規則把 status 表達力邊界轉成一條設計階梯：同步呼叫只有一個 status 可回、就把語意收窄到原子（讓單一 status 恆為真）；要部分成功、必須升級到非同步 operation、失敗明細結構化進 metadata、且 client 用 opt-in flag 顯式聲明「我會處理部分失敗」。對照 207 的被動解析（consumer 被迫讀 body）、AIP 把契約變成雙向顯式同意 —— 通知責任的分配寫進了介面形狀。

## 對應大綱

11.11 status 表達力邊界章「部分成功」段（與 C64 對照的反向立場、原子性階梯）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [AIP-193 Errors](https://google.aip.dev/193) — Approved。已 WebFetch 驗證。
- [AIP-231 Batch methods: Get](https://google.aip.dev/231)、[AIP-233 Batch methods: Create](https://google.aip.dev/233)、[AIP-234 Batch methods: Update](https://google.aip.dev/234) — 均 Approved。已 WebFetch 驗證。

## 二手來源與狀態標注

AIP 對 gRPC / protobuf 生態（`google.rpc.Status`）有預設、引到一般 REST 情境要說明可轉譯性。AIP-231 是唯讀批次所以直接禁止部分成功、233/234 是寫入批次才有非同步分支 —— 引用時不可把三者混寫成同一條規則。
