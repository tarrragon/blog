---
title: "BookImported 不能寫成 ImportBook — 事件命名的過去式是語意類別、不是風格"
date: 2026-07-10
draft: false
description: "domain event 用過去式命名（BookImported）因為事件是已發生的事實；動詞開頭（ImportBook）是命令的形狀、訂閱者會誤讀成指令。字尾清單的自動檢查抓不住不規則動詞——偵測可機械化、判定要看語意。附一次版本終止：工作日誌宣稱的命名問題實際早已不存在、執行前驗前提省下整輪流程。"
tags: ["ddd", "domain-event", "naming", "event-driven", "dart", "flutter"]
---

> **觸發場景**：Flutter 書籍管理 App 的事件驅動架構修正系列排了一張票：統一 use case 流程圖裡的事件命名——記錄顯示 UC-02 用了 `book_imported`、UC-04 用了 `data_exported`，違反 PascalCase + 過去式規範
> **疑問來源**：事件命名規範裡「過去式」這條，是風格偏好還是有語意依據？以及這張票最後的結局為什麼是「終止」？
> **整理目的**：記下事件 vs 命令的命名分界、過去式自動檢查的脆弱性、以及「執行前驗前提」的止損實錄
> **本文邊界**：素材是該專案 v0.12-C.4 的設計與終止記錄；這張票停在設計階段、命名規範本身是它留下的產物

---

## 過去式不是風格：它標記「這是事實、不是指令」

規範的反例清單值得逐個讀，因為四個反例的病因不同：

```dart
class BookImported extends DomainEvent { }   // 正確：已發生的事實
class book_imported extends DomainEvent { }  // 錯：風格（snake_case）
class BookImport extends DomainEvent { }     // 錯：現在式、看不出已發生
class ImportBook extends DomainEvent { }     // 錯：動詞開頭——這是命令的形狀
class book extends DomainEvent { }           // 錯：沒有業務語意
```

第一個反例是純風格問題、lint 就能管。真正的語意分界在第三個：**`ImportBook` 是命令（command）的命名形狀**——「去匯入這本書」，接收者要對它做事、可以拒絕、可以失敗；`BookImported` 是事件（event）——「這本書已經被匯入了」，它是不可否認的歷史事實，訂閱者只能對事實做反應、沒有拒絕的位置。

兩種訊息的責任結構完全不同（命令有唯一的處理者與成敗、事件有任意多的訂閱者且無所謂失敗），而讀者第一眼接觸的就是名字。動詞開頭的「事件」會讓訂閱者用命令的心智模型寫處理邏輯——以為自己能影響流程、以為失敗會被重試。過去式把類別烙在名字上：**看到 `Imported` 就知道木已成舟**。

## 字尾清單抓不住語意：偵測與判定的老分界

規劃中的自動檢查用字尾清單判定過去式：

```dart
final pastTenseEndings = ['ed', 'ted', 'ned', 'ched', 'ded'];
```

這個啟發式的兩面漏洞都很典型：不規則動詞全部漏接（`Sent`、`Built`、`Run` 的過去式形態沒有 ed 字尾）、而碰巧以 ed 結尾的非過去式會被誤放。它能當**候選過濾器**（抓出 `BookImport` 這類明顯缺字尾的）、當不了**判決**——「這個名字是不是過去式的事實陳述」終究是語意判斷。這跟寫作 lint 的 [keyword bank 命中是候選不是判決](/report/keyword-bank-hit-is-candidate-not-verdict/)、跟[函式長度規則是觸發器](/work-log/flutter_function_decomposition_split_vs_keep/)是同一條分界的第三個現場：**可機械化的是偵測、不可機械化的是判定**，把前者當後者用就會又漏又誤。

## 版本的結局：前提不存在、0.3 小時止損

這張票最後沒有修任何檔案——Phase 1 的設計審查去核對「待修正」的流程圖時發現：UC-02 的流程圖實際寫的是 `BookImportedEvent`、UC-04 是 `ExportCompletedEvent`，**早就符合規範**。票面宣稱的 snake_case 問題來自過時的工作日誌記錄，實際問題不存在。決策是終止版本、總耗時 0.3 小時。

這是「執行前驗前提」最便宜的一次勝利：如果跳過核對直接進 TDD 四階段，會為一個不存在的問題走完測試設計與實作流程。它跟 [stale ticket 考古](/work-log/flutter_renderflex_overflow_prevention_spec/)（58 天票、路徑與數量全漂移）是同一條紀律的兩次實證——**工作項的內文是建立當下的快照、執行前重驗每一個事實聲明**。而終止決策記錄本身也做對了一件事：把「為什麼不做」跟兩個選項的否決理由寫下來（改成 Event 後綴標準化的提案被否決：後綴是風格、不符架構修正系列的定位），下一個看到這張票的人不會重開一輪。

附帶的懸念也誠實地留著：實際文件用了 `Event` 後綴（`BookImportedEvent`）、規範範例沒有（`BookImported`）——這個不一致被看見、被評估為風格層、被明確地不處理。跟靜默的不一致相比，「已知、已評估、不處理」是完全不同的狀態。

## 判讀徵兆

- 事件類別的名字以動詞開頭——它長成了命令，訂閱者會用錯誤的心智模型消費它
- 事件與命令在同一個 bus / 同一個目錄裡混居且命名無法區分——先立命名分界、再談架構
- 命名檢查用字尾 / 前綴清單且被當成判決——降級為候選過濾器、命中後人工判定
- 修正類工作項的「問題描述」超過幾週沒被重驗——執行前先花十分鐘核對問題還在不在

## 相關閱讀

- 同紀律的另一現場：[溢出 714px 的 stale ticket 考古](/work-log/flutter_renderflex_overflow_prevention_spec/)——票面快照 vs 現實的漂移
- 偵測 / 判定分界的原則層：[#149 keyword bank 命中是候選、不是判決](/report/keyword-bank-hit-is-candidate-not-verdict/)
- 概念地基：[DDD 領域驅動設計指南](/ddd/)——事件建模章節；事件與命令的責任結構差異是「從操作推導領域」的一部分
