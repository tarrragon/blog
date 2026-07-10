---
title: "核心 entity 重寫、140+ 檔消費端不動 — Deprecated Getter Facade 的過渡設計"
date: 2026-07-10
draft: false
description: "重寫被百餘檔引用的核心 entity 時，直接改會同時打爆全部消費端、長期分支的 merge 成本隨時間暴漲。第三條路是 facade：舊欄位保留為 deprecated getter、內部從新結構回讀，消費端零修改編譯通過、@Deprecated 讓編譯器自動列出遷移清單、再逐波清償。facade 要配退場計畫、否則就是永久相容層。"
tags: ["flutter", "dart", "ddd", "entity", "migration", "refactoring", "facade"]
---

> **觸發場景**：Flutter 書籍管理 App 的 Book entity 要從固定欄位（author、publisher、isbn、genre……）重寫成 tag-based 結構。動手前的 ripple 盤點：`.author` 有 64 個檔在用、`.isbn` 60 個、`.publisher` 45 個——加上測試合計 140+ 檔受影響
> **疑問來源**：核心 entity 是所有 Service / Repository / ViewModel 的上游、必須先改；但 140+ 檔的 ripple 又讓「先改它」等於同時打爆整個專案。怎麼解這個死結？
> **整理目的**：記下大 ripple entity 演化的三個選項、facade 策略的機制與配套、以及它跟「永久相容層」的一線之隔
> **本文邊界**：素材是該專案 v0.32 的 ticket 記錄（含 PM 前置調查與 SA 審查結論）；「認知負擔閾值 > 5 檔必須拆分」是該專案自訂的工作規則

---

## 先量化 ripple、再選策略

這次重寫在動手前做了一件關鍵的事：把「影響很大」量化成數字。逐欄位 grep 消費端：

| 廢除欄位           | lib/ 引用檔數 |
| ------------------ | ------------- |
| `.author`          | 64            |
| `.isbn`            | 60            |
| `.publisher`       | 45            |
| `.source`          | 27            |
| `.importanceLevel` | 17            |
| `.readingStatus`   | 16            |

加上 77 個測試檔、合計 140+ 檔。這張表直接判定了原提案（單一 ticket 重寫 entity）的死刑——PM 調查的結論寫得直白：「多 Wave migration 偽裝成單一 ticket」。數字的價值在這裡：**策略選擇是 ripple 規模的函數**，不先量化就選策略、等於矇著眼選。

## 三個選項、兩個否決理由

SA 審查列了三條路、否決理由都寫進了記錄：

- **直接移除 + 全量遷移**：140+ 檔同時修改，違反該專案的認知負擔閾值（單次修改 > 5 檔必須拆分）、且無法在「測試 100% 通過」的前提下原子完成——改到一半的每個中間狀態都是編譯不過的
- **長期分支開發**：分支與 main 的 merge conflict 成本隨時間指數成長，而且其他 Wave 的 ticket 依賴新 entity——分支隔離了風險、也隔離了下游的進度
- **Deprecated Getter Facade**（勝出）：entity 換新結構、舊介面保留為過渡層

## Facade 機制：舊介面成為新資料的 view

核心手法一段程式碼講完：

```dart
// Book entity 內：新結構是 tag 關聯
// 舊欄位保留為 deprecated getter、從新結構回讀
@Deprecated('Use tagRepository.getTagsForBook(bookId, category: "author") instead')
BookAuthor get author => _legacyAuthorFromTags();
```

entity 持有 repository 注入的 `List<BookTag>`，每個廢除欄位各有一個 deprecated getter、從 tags 過濾對應分類、回傳**舊型別**。效果分三層：

- **消費端 140+ 檔零修改編譯通過**——舊介面的形狀完整保留，只是資料來源換了
- **`@Deprecated` 把遷移清單交給編譯器**——每個舊呼叫點自動變成 warning，「還剩多少沒遷」隨時可查、不靠人工盤點
- **新程式碼從第一天用新 API**（`getTagsByCategory`）——新舊並行、但增量只往新的走

配套的兩個細節同樣值得記：新集合命名 `bookTags` 刻意避開 entity 既有的 `tags` 欄位（遷移期兩者並存、同名會災難）；序列化走雙軌——`toJson` 維持 v1 格式相容既有持久化、新的交換格式獨立成 `toInterchangeJson` v2，讀寫兩個世界互不干擾。

## facade 與永久相容層的一線之隔：退場計畫

這個策略跟同專案早年[VO 擺盪](/work-log/flutter_value_object_encapsulation_oscillation/)裡「加回 `.value` getter 當相容性介面」在機制上是同一件事——差別全在配套。那次的 getter 加回來就沒有然後了、成為永久的一部分；這次的 facade 在 ticket 系統裡直接 spawn 了九張後續票、逐 Wave 遷移各消費端，deprecated getter 的死期寫在 backlog 上。

**facade 的性質由退場計畫決定**：有計畫、它是分期償還的過渡層；沒計畫、它是把重構宣告完成的化妝——新舊兩套 API 永久並存、每個新人都要學「哪個是真的」。判斷一個 codebase 裡的 deprecated 標記是哪一種，看它有沒有對應的遷移工作項、以及 warning 數量的趨勢是降是平。

## 判讀徵兆

- 核心 entity / 介面要重寫、而「先量 ripple」沒做——grep 出消費端檔數再開會，策略討論會短很多
- 單一 ticket 的影響檔數超過團隊的認知閾值——它是偽裝成 ticket 的 migration，拆 wave
- deprecated getter 存在超過 N 個版本、warning 數量不降——facade 已變永久相容層，補退場計畫或誠實移除 @Deprecated
- 遷移期新舊集合 / 方法同名或近名——先改名再並行，同名並存的每一天都在累積誤用

## 相關閱讀

- 對照組：[VO 封裝擺盪](/work-log/flutter_value_object_encapsulation_oscillation/)——同樣的 getter 相容層、沒有退場計畫的版本
- 原則層：[#76 分批 ship：低風險可見價值先行](/report/incremental-shipping-criteria/)——facade + wave 遷移就是分批 ship 在 entity 演化上的形態
- 這次遷移的下游驚險：[read-path 缺口與 fixture 假綠](/work-log/flutter_migration_read_path_gap_fake_green/)——facade 讓編譯過了、但新結構的資料通路要自己驗證
