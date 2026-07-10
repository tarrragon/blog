---
title: "同一個品項、四個 model — value object 什麼時候該升級成 entity"
date: 2026-07-10
draft: false
description: "同一個業務概念要不要拆成多個 model、value object 什麼時候該升級成 entity——判準是操作需不需要 identity-based 回寫。以 POS 品項從點選、掛單、結算到歷史訂單的四階段模型為例，含 snapshot 與 live reference 的凍結時機。"
tags: ["dart", "flutter", "ddd", "entity", "value-object", "domain-model", "pos"]
---

> **觸發場景**：整理 POS 專案的購物車模型時，發現「一個商品品項」這個概念在 codebase 裡有四個 model：`CartItem`、`ShoppingCartDetail`、`OrderedCartItem`、`OrderItem`。乍看是重複建模
> **疑問來源**：四個 model 是過度設計、還是各有不可合併的職責？如果是後者，拆分的判準是什麼？
> **整理目的**：把「同一個業務概念何時該拆 model、value object 何時升級成 entity」的判斷邊界記下來
> **本文邊界**：素材是一個 Flutter POS App 的現行實作；「四個」是這個 domain 的結果、不是通用配方——判準才是可遷移的部分

---

## 四個 model 各在哪個生命週期

一個商品從「使用者點選」到「進了歷史訂單」，這個專案用四個 model 接力表達：

| Model                | 生命週期階段             | 同一性的依據                         |
| -------------------- | ------------------------ | ------------------------------------ |
| `CartItem`           | 點餐輸入、還沒送出       | 內容比對（spec + 折扣 + 口味集合）   |
| `ShoppingCartDetail` | 掛單系統接受後的後端實體 | 後端 `detail.id`                     |
| `OrderedCartItem`    | 結帳畫面上的一筆訂單行   | `sourceDetailIds`（摺疊多筆 detail） |
| `OrderItem`          | 結完帳的歷史訂單明細     | `detailId` + 全欄位 snapshot         |

每一次交棒都對應一個身份狀態的變化，這是四個 model 不可合併的原因。

## 階段一：CartItem 是純需求描述、沒有 id

`CartItem` 表達「使用者想要什麼」：商品、規格、數量、折扣、口味。它沒有任何 id 欄位——兩個 `CartItem` 是不是同一項，靠 `isSameItem()` 做內容比對：

```dart
bool isSameItem(CartItem other) {
  if (specification.id != other.specification.id) return false;
  if (discount != other.discount) return false;   // 手動改價過的品項視為獨立行
  // 口味集合比對（不考慮順序）
  ...
}
```

這是 value object 的語意：**內容相等就是同一個**。合併購物車（`mergeItems`）靠這個判定把相同品項的數量累加。值得留意折扣也參與同一性判定——改過價的品項是不同的訂單行，這是業務規則直接寫進相等性定義的例子。

## 階段二：掛單接受的那一刻、identity 誕生

需求被掛單系統接受、寫進 `ShoppingCart.details` 之後，每筆明細獲得了後端身份 `detail.id`。model 的原始註解把這個轉折講得很清楚：

> 一旦這個需求被掛單系統接受、寫進 details，它就獲得了後端身份（detail.id），從這刻起在前端應以 OrderedCartItem 表達——客人加點同一項三次，邏輯上是一筆訂單行（一個 OrderedCartItem），實體上是三筆 detail。

`OrderedCartItem` 的結構只有兩個欄位：`cartItem`（內容）加 `sourceDetailIds`（身份）。它存在的理由是**操作需要精確回寫**：改數量、單品取消、單品改價，都必須映射回後端要修改的那幾筆 detail。內容比對在這裡不夠用——同商品同口味的三筆 detail 內容完全相同，取消其中一筆時內容比對無法指定是哪一筆。

購物車 model 上有一段對應的契約註解：UI 顯示的列表經過合併與過濾，「UI 列表的 index 跟 details 的 index 不是同一個東西」，任何 UI 到後端 detail 的操作都要透過 `sourceDetailIds` 做 id-based 比對。用 index 對應兩個列表是這個結構下最容易踩的錯誤路徑，契約直接把它寫死在文件裡。

## 階段三：結完帳、參照凍結成 snapshot

`OrderItem` 是結帳完成後的歷史事實。它跟 `CartItem` 的關鍵差異是參照的凍結：

- `CartItem` 持有 live 的 `Product` 參照，價格即時查當前規格（會員身分變了、價格跟著變）
- `OrderItem` 保存 `OrderDetailProduct` / `OrderDetailProductSpecification` 的 snapshot，註解明說「即使後續商品改名/下架，訂單仍顯示當時購買的內容」；`unitPrice` 也在 `fromResponse` 時依當時的會員身分擇一凍結

`detailId` 在這個階段承擔新職責：退貨與取消 API 的鍵、以及同訂單中區分「同商品不同口味」的唯一鍵。

## 判準：操作需不需要 identity-based 回寫

把三次交棒放在一起看，「value object 什麼時候該升級成 entity」的答案就浮出來了。判準是**對這個物件的操作，需不需要精確指到某一個實體**——概念重不重要、有沒有 id 欄位可以填，都不參與這個判斷。

- 需求描述階段：操作是「加一份」「換口味」，內容相等就是同一個，value object 的內容比對足夠
- 進入外部系統之後：操作是「取消那一筆」「改那一筆的量」，必須 identity-based 回寫，此時需要 entity（或至少像 `OrderedCartItem` 這樣持有身份參照的包裝）
- 成為歷史事實之後：操作只剩查閱與退貨，連 live 參照都要凍結成 snapshot——歷史不隨現在的資料變動

反過來看單一 model 通吃的代價：改量操作靠內容比對會誤中同內容的其他筆；歷史訂單持 live 參照會跟著商品改名漂移。四個 model 不是重複，是身份語意在三個轉折點上真的變了。

## 相關閱讀

- 概念地基：[entity 與 value object 的判準](/ddd/entity-vs-value-object/)（本文是該判準的實機案例）、[狀態轉換與稽核軌跡](/ddd/state-transition-and-audit-trail/)（凍結作為稽核端點的教學層展開）
- 同專案的 snapshot 對照組：entity 稽核軌跡的洞（[copyWith 是逃生口，不是設計](/work-log/dart_copywith_entity_escape_hatch/)）——那篇談變更路徑的完整性，本文談身份與參照的凍結時機，兩者合起來是「歷史事實怎麼被保護」的兩個面
