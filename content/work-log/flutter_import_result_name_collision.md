---
title: "兩個 ImportResult 各自都合理 — 傘狀名的碰撞與做一半的重命名"
date: 2026-07-10
draft: false
description: "同一個 domain 裡兩個類別都叫 ImportResult：一個是驗證結果、一個是操作結果，各自誕生時都合理。修法是依語意責任命名（ImportValidationResult）；而重命名是一組原子操作——類別名、檔名、import、文件宣稱，做一半留下的不一致比不做更迷惑，且宣稱完成與實際完成的漂移要靠稽核抓。"
tags: ["dart", "flutter", "naming", "refactoring", "ddd", "value-object"]
---

> **觸發場景**：Flutter 書籍管理 App 的 import domain 介面盤點，發現兩個同名類別並存：`value_objects/import_result.dart` 跟 `models/import_result.dart`——都叫 `ImportResult`、欄位完全不同、引用時全憑 import 路徑分辨
> **疑問來源**：兩個類別各自看都命名合理，撞名是怎麼發生的？重命名之後的 Phase 4 稽核又抓到什麼？
> **整理目的**：記下傘狀名的碰撞機制、依職責命名的修法、以及「重命名是原子操作組」的教訓
> **本文邊界**：素材是該專案 v0.12.1 的介面盤點與 Phase 4 重構稽核報告

---

## 碰撞：兩個「匯入結果」、各自誕生都合理

攤開兩個類別的內容，撞名的成因就清楚了：

| 檔案                               | 欄位                                                                              | 它其實是什麼           |
| ---------------------------------- | --------------------------------------------------------------------------------- | ---------------------- |
| `value_objects/import_result.dart` | `isValid`、`books`、`errors`                                                      | **JSON 驗證**的結果    |
| `models/import_result.dart`        | `isSuccess`、`successfulBooks`、`failedItems`、`processingTimeMs`、`peakMemoryMB` | **整個匯入操作**的結果 |

寫驗證邏輯的人需要一個型別裝驗證結果——「這是匯入流程的結果」、叫 `ImportResult`，合理；寫匯入執行的人需要一個型別裝執行結果——同樣的推理、同樣的名字。**「Result」是傘狀詞**：它只說「某個東西的結果」、不說是哪個環節的，同一個 domain 裡任何階段的產出都有資格用它，於是第二個使用者出現時必然碰撞。碰撞的代價由所有讀者付：每次看到 `ImportResult` 都要先看 import 路徑才知道在讀哪一個，而 IDE 自動匯入選錯路徑的錯誤、型別又剛好對不上時的錯誤訊息（「ImportResult 不是 ImportResult」）尤其折磨。

## 修法：名字要能回答「什麼操作的結果」

決策保留 models 版當主要的 `ImportResult`（它代表整個 use case 的產出、消費者最多），value object 版重命名為 `ImportValidationResult`——名字補上了它缺的那一節：**驗證**的結果。判準可以一般化：result / info / data / manager 這類傘狀名，掛上去之前先問「它是**哪個操作**的 result」——答案就是名字該有的樣子。兩個同名類別並存時的診斷同理：先問哪一個的名字說謊了（通常是語意較窄的那個佔了寬名字）、改窄的那個。

這跟[分層 enum](/work-log/dart_payment_dual_layer_enum/) 的粒度判準是同一族：名字的顆粒度要配得上它指涉範圍的顆粒度，佔著寬名字的窄概念是碰撞的定時炸彈。

## 稽核抓到的：做一半的重命名、以及宣稱的漂移

Phase 4 重構稽核在「已完成」的重命名上抓到殘局：類別名確實改成了 `ImportValidationResult`——但**檔名還是 `import_result.dart`**。而且工作日誌宣稱檔案已重命名為 `import_validation_result.dart`、與現實不符。

三層漂移疊在一起：類別名（改了）、檔名（沒改）、文件宣稱（說改了）。做一半的重命名比不做更迷惑——現在檔名對讀者說「這裡是 ImportResult」、打開來是另一個名字，Dart 的「檔名對應主類別名」慣例反過來變成誤導。教訓收成兩條：

- **重命名是一組原子操作**：類別名、檔名、所有 import 路徑、測試引用、文件宣稱——清單上每一項都做完才算完成，IDE 的 rename 重構通常只保證前三項、檔名跟文件是人的責任
- **宣稱完成與實際完成是兩個 fact**：工作日誌寫「已重命名」的當下可能是計畫、可能是部分完成——下游讀者無從分辨。這正是 Phase 4 稽核這類「驗收與執行分離」流程存在的理由，同構於 [read-path 分析](/work-log/flutter_migration_read_path_gap_fake_green/)的獨立重驗紀律

## 判讀徵兆

- 同一個 domain 裡 grep 到兩個同名類別——先判哪個名字說謊（語意窄的佔寬名）、改窄者
- 類別名含 Result / Info / Data / Manager 而前綴不含操作名——傘狀名候選，下一個同 domain 的產出型別就會撞上來
- 檔名與主類別名不一致——半完成重命名的化石，補完或回退、別放著
- 工作記錄宣稱的檔案狀態與 codebase 不符——把「宣稱」降級為線索、以 grep 結果為準

## 相關閱讀

- 命名顆粒度的同族：[16 種支付渠道、4 種行為分類](/work-log/dart_payment_dual_layer_enum/)——名字與指涉範圍的顆粒度要相配
- 原則層：[#157 語意錨用單一字串](/report/semantic-anchor-single-string/)——同語意雙字串與同字串雙語意是一體兩面的引用災難；[#84 Naming 是 iterated artifact](/report/naming-as-iterated-artifact/)——第一版命名幾乎不對、cross-call-site 檢驗才收斂
- 宣稱與實際的分離：[遷移計畫有寫入、有消費、缺讀出](/work-log/flutter_migration_read_path_gap_fake_green/)——獨立重驗的紀律
