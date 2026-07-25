---
title: "freezed"
tags: ["freezed", "程式碼生成"]
date: 2026-07-10
description: "Dart 的 immutable data class 程式碼生成器。freezed 自動產生 copyWith、equals、toString、sealed union——它是 Dart 生態把 copyWith 推成預設路徑的主要推力。"
weight: 2
---

freezed 是 Dart 生態中最廣泛使用的 immutable data class 程式碼生成器。標記 `@freezed` 後，它自動產生 [copyWith](/flutter/knowledge-cards/copywith/)、`==` / `hashCode`、`toString()`、以及 sealed union（多態分支的 exhaustive switch）。它把「寫一個 immutable class 需要的 boilerplate」壓到接近零。

## 概念位置

freezed 的預設路徑對所有型別一視同仁——它不區分[資料袋](/ddd/knowledge-cards/data-bag/)和有領域方法的 [entity](/ddd/knowledge-cards/entity/)。每個被 `@freezed` 標記的 class 都會得到全欄位的 public [copyWith](/flutter/knowledge-cards/copywith/)、包含狀態欄位與稽核欄位。這是生態推力：規範說「請走領域方法」、工具預設給全欄位 copyWith——規範和預設衝突時、預設會贏。

## 設計責任

在 entity 上使用 freezed 時、需要額外措施收窄 copyWith 的開放程度：把 copyWith 改 private、或從參數列移除受約束的欄位。freezed 的 sealed union 在枚舉分層上有正面價值——exhaustive switch 讓「忘記決定新成員歸哪類」在編譯期就走不通。結構細節見 [Freezed 三層結構解剖](/work-log/dart_freezed_anatomy/)。
