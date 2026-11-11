---
title: "freezed"
tags: ["freezed", "程式碼生成"]
date: 2026-07-10
description: "Dart 的 immutable data class 程式碼生成器。freezed 自動產生 copyWith、equals、toString、sealed union——它是 Dart 生態把 copyWith 推成預設路徑的主要推力。"
weight: 2
aliases: ["/flutter/knowledge-cards/freezed/"]
---

freezed 是 Dart 生態中最廣泛使用的 immutable data class 程式碼生成器。標記 `@freezed` 後，它自動產生 [copyWith](/programming/flutter/knowledge-cards/copywith/)、`==` / `hashCode`、`toString()`、以及 sealed union（多態分支的 exhaustive switch）。它把「寫一個 immutable class 需要的 boilerplate」壓到接近零。

## 跟其他概念的關係

freezed 的預設路徑對所有型別一視同仁——它不區分[資料袋](/software-design/ddd/knowledge-cards/data-bag/)和有領域方法的 [entity](/software-design/ddd/knowledge-cards/entity/)。每個被 `@freezed` 標記的 class 都會得到全欄位的 public [copyWith](/programming/flutter/knowledge-cards/copywith/)、包含狀態欄位與稽核欄位。這是生態推力：規範說「請走領域方法」、工具預設給全欄位 copyWith——規範和預設衝突時、預設會贏。

## 判斷條件與後果

freezed 標在有領域方法的 entity 上時，生成的全欄位 public copyWith 讓狀態欄位與稽核欄位都能不經過領域方法覆寫，不變式只剩規範文件在約束，程式碼裡沒有任何檢查擋得下違規的覆寫；所以 entity 上的 copyWith 要收窄，改成 private，或從參數列移除受約束的欄位。freezed 的 sealed union 用在枚舉分層時，生成的程式碼反過來替規範做檢查：exhaustive switch 要求每個成員都有分支，新增成員而沒決定它歸哪一類時編譯就失敗，遺漏在編譯期現形，不會留到 runtime。結構細節見 [Freezed 三層結構解剖](/work-log/dart_freezed_anatomy/)。
