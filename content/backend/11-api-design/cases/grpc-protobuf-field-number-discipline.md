---
title: "11.C28 protobuf 官方規範：field number 紀律"
date: 2026-07-03
description: "編號不可改、刪除必 reserve、重用導致資料損毀；契約相容性是編碼格式的性質、不是 review 慣例"
weight: 28
tags: ["backend", "api-design", "case-study", "grpc"]
---

這個案例的核心責任是提供 proto 演進紀律的規範錨點。

## 觀察

官方語言規範明文：field number 一旦訊息投入使用即不可變更、因為它就是 wire format 的欄位識別；刪欄位後必須 reserve 該編號、重用編號會使 wire 解碼歧義、後果列舉包括 parse / merge error、PII 洩漏、資料損毀。文件把 schema 變更分三類：wire-unsafe、wire-safe（加欄位、加 enum 值、刪欄位皆安全）、conditionally wire-compatible。

## 判讀

契約相容性在 protobuf 是編碼格式的數學性質、不是 code review 慣例 —「加法演進 + 編號永不回收」是 protobuf 相對 JSON schema 的核心工程差異、也是所有 breaking-change 工具（C29）存在的前提。

## 對應大綱

styles/grpc/「proto 演進紀律」（anchor）、11.6 向後相容的變更紀律交叉。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Language Guide (proto 3)（Protocol Buffers 官方文件）](https://protobuf.dev/programming-guides/proto3/)
