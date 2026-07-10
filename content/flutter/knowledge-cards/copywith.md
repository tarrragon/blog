---
title: "copyWith"
tags: ["copyWith"]
date: 2026-07-10
description: "物件的逐欄位覆寫方法在什麼時候是正確工具、什麼時候是逃生口時使用。copyWith 對資料袋語意清晰、對有領域方法的 entity 是繞過不變式的逃生口。"
weight: 1
---

copyWith 是 Dart 生態中逐欄位覆寫物件的慣用方法：呼叫時只傳要改的欄位、其餘保留原值、回傳一個新實例。[freezed](/flutter/knowledge-cards/freezed/) 自動為每個 model 生成 copyWith，IDE 補全第一個跳出來的也是它——它是 Dart 的預設路徑。

## 概念位置

copyWith 對[資料袋](/ddd/knowledge-cards/data-bag/)（DTO、API model、UI state）是正確工具——欄位組合全部合法、逐欄位覆寫語意清晰。但對有領域方法的 [entity](/ddd/knowledge-cards/entity/)、copyWith 是繞過[不變式](/ddd/knowledge-cards/invariant/)的逃生口：領域方法從「唯一路徑」降級成「建議路徑」、稽核軌跡開始出洞。判準是型別有沒有「不允許任意組合的欄位」——有，copyWith 就不該讓那些欄位 public 可寫。

## Nullable 欄位的三態缺口

copyWith 在 nullable 欄位上有一個 Dart 型別系統的缺口：`String? isbn` 只有兩態（有值 / null），而 copyWith 需要三態——「不改這欄」「改成某值」「清空成 null」。前兩態沒問題，第三態表達不出來。通用的補償手法是哨兵物件（sentinel），freezed 生成的 copyWith 內部就是用同樣的技巧。

## 設計責任

收窄的方向分三層：value object / DTO / UI state 保留 copyWith；有領域方法的 entity 把 copyWith 改 private 或從參數列移除受約束欄位；測試建構需求不足時修工廠的表達力、不修每一個拼裝點。完整機制見 [copyWith 是逃生口，不是設計](/work-log/dart_copywith_entity_escape_hatch/)、教學層見 [資料袋與領域模型](/ddd/data-bag-vs-domain-model/)。
