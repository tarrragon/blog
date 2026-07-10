---
title: "Exception 型別綁 ErrorCategory 的建構不變式 — 以及合法需求撞上不變式的時刻"
date: 2026-07-10
draft: false
description: "把「錯誤代碼必須屬於對應分類」做成建構期不變式，錯誤分類錯亂會變成測試失敗而不是靜默混亂；同一批修復出現三種形態——換對值、換精確值、以及改繼承逃離約束。第三種是分類學本身的訊號：一個 domain 的錯誤天生橫跨技術分類時，分類軸跟階層軸不正交。"
tags: ["flutter", "dart", "ddd", "exception", "error-handling", "invariant"]
---

> **觸發場景**：Flutter 書籍管理 App 的測試修復盤點，六個失敗指向同一個結構：exception 型別對錯誤代碼的分類有建構期要求、而實作塞了跨分類的 code——`BusinessException` 家族用了 network 分類的 `serverError`、`StorageException` 用了 platform 分類的 `permissionDenied`
> **疑問來源**：錯誤代碼分錯類、為什麼會讓測試失敗？以及修法裡出現「改繼承」這種大動作、合理嗎？
> **整理目的**：記下「錯誤分類當領域建模」的不變式設計、以及不變式被合法需求撞上時的三種處置與各自的訊號
> **本文邊界**：素材是該專案 v0.11.15 的測試修復計畫；錯誤分類軸（business / network / storage / platform / validation）是該專案的切法、不是通用標準

---

## 設計：錯誤代碼的分類是建構不變式

這個專案把錯誤處理建成兩層結構：`ErrorCode` 枚舉、每個 code 隸屬一個 `ErrorCategory`（business / network / storage / platform / validation）；exception 型別各自綁定分類——`BusinessException` 的建構要求 code 屬於 business 分類、`StorageException` 要求 storage 分類。

這是把「錯誤要分對類」從文件約定升到執行層的做法。沒有這層不變式時，分類錯亂是靜默的：`ImportException` 帶著 network 的 code 一樣能拋能接，錯亂只在某天有人按分類統計錯誤、或按分類決定重試策略時才以錯誤行為浮現。有不變式，錯亂在建構的當下就炸——這批測試失敗全是不變式在工作的證據，六個失敗六個都指向真實的分類錯誤。

## 同一批修復的三種形態

值得記的是修法不只一種，三種形態對應三種不同的病因：

**形態一：值選錯了、換對的。** `StorageException.permissionDenied` 用了 platform 分類的 `permissionDenied`，而 storage 分類裡有語意等價的 `fileAccessDenied`——換過去、不變式滿足、語意不變。病因是選 code 時沒查分類表，最便宜的修法。

**形態二：值太泛、換精確的。** 掃描服務把 ISBN 格式錯誤拋成 `validationFailed`、把離線與網路錯誤都拋成 `serverError`，測試期待的是 `invalidIsbn`、`networkError`、`offlineError`。泛化 code 不違反分類不變式、但淹沒語意——下游想對「離線」跟「伺服器壞了」做不同處置時，兩者在錯誤碼層已經不可區分。這是不變式管不到的精度問題，靠測試斷言把精確度釘住。

**形態三：約束本身擋住合法需求、改繼承逃離。** `ImportException` 原本繼承 `BusinessException`，但匯入流程的錯誤天生橫跨分類——JSON 解析壞（validation）、來源伺服器錯（network）、寫檔失敗（storage）。business 分類裡根本沒有它需要的 code。修法是把父類從 `BusinessException` 改成 `AppException`（不綁分類的基類），逃離約束。

## 形態三是分類學的訊號、不是不變式的失敗

改繼承逃離約束、跟[copyWith 逃生口](/work-log/dart_copywith_entity_escape_hatch/)那種「繞過不變式」是不同的事——這裡的需求是**合法的**：匯入錯誤真的橫跨技術分類。撞牆暴露的是兩條分類軸不正交：

- `ErrorCategory` 的軸是**技術來源**（網路、儲存、平台）
- exception 階層的軸是**業務流程**（匯入、掃描、搜尋）

一個業務流程天生會遭遇多種技術來源的錯誤，把業務流程的 exception 綁死在單一技術分類上，約束跟現實的形狀不合。`ImportException` 改繼承是對這個不合的誠實回應；更徹底的修法是承認兩軸各自獨立——exception 型別按業務流程分、`ErrorCategory` 作為錯誤的一個屬性自由取值——但那是更大的重構，當下的繼承調整是合比例的處置。

可操作的判準：**不變式被撞的時候，先分「需求違規」還是「約束錯形」**。前者的訊號是繞過方在找便利（copyWith 改狀態、省掉領域方法）；後者的訊號是繞過方有無法被現有約束表達的正當語意（匯入錯誤需要 network code）。前者修繞過方、後者修約束。

## 判讀徵兆

- exception 建構失敗、訊息指向分類不匹配——先查分類表有沒有語意等價的正確 code（形態一）、再問這個 exception 是不是真的只屬於一個分類（形態三）
- 多種不同情境拋同一個泛化 code（`serverError` 當萬用垃圾桶）——語意精度在流失、下游的分支處置已經寫不出來
- 「改繼承來讓建構通過」的修法出現——停下來判定是逃生還是約束錯形；是後者就把分類學的不合寫成決策記錄，否則下一個橫跨分類的 exception 會重演一次
- 錯誤分類只存在於命名慣例（`NetworkXxxError`）而沒有建構驗證——分類錯亂正在靜默累積、第一個按分類做統計或重試的功能會揭開它

## 相關閱讀

- 不變式強制層次的原則層：[#222 約束要讓違反路徑走不通](/report/design-intent-needs-enforcement-layer/)——本文是「約束做進執行層之後」的下一章：約束會工作、也會被合法需求撞
- 決策表矛盾的同構：[#158 決策表兩列同時命中且結論相反：缺的是上游區分維度](/report/decision-table-conflict-reveals-missing-dimension/)——分類軸不正交跟決策表缺維度是同一個病：單一分類軸承載不了多維的現實
- 概念地基：[DDD 領域驅動設計指南](/ddd/)——錯誤即領域概念、分類學也是建模
