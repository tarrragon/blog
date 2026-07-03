---
title: "11.C29 Buf breaking detection：四級規則對應消費者依賴"
date: 2026-07-03
description: "把 proto 相容紀律從人的自律升級成 CI gate、檢查粒度是產品決策不是工具預設"
weight: 29
tags: ["backend", "api-design", "case-study", "grpc"]
---

這個案例的核心責任是說明相容性檢查如何工具化進 CI、以及檢查粒度的選擇邏輯。

## 觀察

`buf breaking` 對比歷史版本 schema、在 merge 前擋下如「Field 1 type int32 改 string」這類變更；規則分四級（FILE、PACKAGE、WIRE_JSON、WIRE、嚴格包含寬鬆）。文件明言「Catching this before merge is the point」、並指出破壞發生在多層 — 改名破壞 generated code、改 type 破壞 wire format — 人工 review 抓不全。

## 判讀

這是 C28 紀律從「人的自律」升級成 CI gate 的論證。四級規則的核心主張：「選符合消費者實際依賴的等級」— 只走 wire 的消費者用 WIRE、有外部 Go import 的要 PACKAGE。教學重點是「相容性檢查粒度是產品決策、不是工具預設」。

## 對應大綱

11.6 向後相容的變更紀律（工具層 anchor、已引用）、styles/grpc/「proto 演進紀律」、11.10 API 規範治理（linting 進 CI）交叉。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Breaking change detection（Buf 官方文件）](https://buf.build/docs/breaking/)
