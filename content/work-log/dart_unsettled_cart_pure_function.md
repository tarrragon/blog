---
title: "「該收多少錢」抽成 pure function — IO 在邊界、領域計算在核心"
date: 2026-07-10
draft: false
description: "多個畫面都要顯示「未結帳的份數與金額」時，把計算抽成無 IO 的 pure function：資料由 caller 從 repository 拿好傳入、函式只做合併 / 扣減 / 折扣運算。含合併鍵要跟同一性定義同維度的陷阱、兩層折扣各自 clamp 的邊界、以及用註解預留擴充點讓未來規則接入不動本體。"
tags: ["dart", "flutter", "ddd", "pure-function", "pos", "testing", "domain-logic"]
---

> **觸發場景**：POS 的提前結帳功能讓一個資料語意浮出來：後端購物車明細的 `quantity` 是總量、包含客人已經先結過帳的份數。桌位詳情、掛單列表、取單頁都要顯示「還要處理 / 還要收」的數字——用總量顯示，員工會誤收已付過的錢
> **疑問來源**：這段「扣掉已結帳份數、算出應付金額」的邏輯，好幾個畫面都要用，該放在哪？
> **整理目的**：記下領域計算抽成 pure function 的做法、以及這個函式裡三個容易寫錯的細節
> **本文邊界**：素材是該專案現行的 `unsettledCartView` 實作與註解；「pure function + caller 餵資料」的形態可遷移、折扣規則是這個 domain 當下的切法

---

## 形態：一個函式、輸入齊備、輸出結構化

整段計算收在一個頂層函式裡，簽名把設計講完了：

```dart
({
  List<OrderedCartItem> items,
  Money originalAmount,   // 折扣前商品總額（含口味加價）
  Money discountAmount,   // 折扣總額（單品 + 整筆）
  Money totalAmount,      // 應付金額（不會為負）
  int totalItemCount,
})
unsettledCartView({
  required ShoppingCart cart,
  required List<RemoteOrderSnapshotItem> snapshotItems,
  Money? manualCartDiscount,
})
```

關鍵的選擇是**它不做任何 IO**。已結帳份數要靠線上點單的 snapshot 判斷，而 snapshot 在 repository 裡——函式不去拿，由 caller 先從 `IOnlineOrderRepository.itemsByCart` 取好傳進來。這一刀切出兩個直接的好處：測試就是「餵資料、斷言輸出」（不用 mock repository）；任何畫面都能重用（桌位詳情、掛單列表、取單頁各自拿自己的資料餵）。金額回三個欄位而不是一個，因為 UI 要顯示折扣明細——輸出的形狀由消費者的需求決定、用 record 一次回齊。

## 細節一：合併鍵要跟「同一品項」的定義同維度

計算的第一步是把同品項的多筆 detail 合併、第二步用已結帳份數扣減。扣減需要一個 key 來對應「snapshot 裡結掉的」跟「cart 裡剩下的」——這個 key 的維度是實作裡最容易寫錯的地方，原始註解直接記了陷阱：

> 只用 spec 當 key 的話，同 spec 不同 customizations 的多筆 cart 項目會被同一筆已結帳數量重複扣減，造成新加的不同口味品項被誤過濾。

正解是 key 用「規格 + 客製化簽章」——跟 `CartItem.isSameItem` 對「同一品項」的判定維度**一致**。原則化：**扣減 / 合併 / 對帳用的 key，維度必須等於這個 domain 對「同一個」的定義**，少一個維度就會把不同的東西誤當同一個。還有一個資料現實的妥協記在註解裡：snapshot 的客製化只有 name 沒有 id，所以簽章用排序後的 name 串接——妥協可以，但要寫明它是妥協。

## 細節二：兩層折扣、clamp 的上限要選對

折扣有兩層：單品折扣（記在每個 `CartItem.discount`、由改價彈窗設定）跟整筆折扣（結帳頁折價按鈕、業務上不分攤回品項）。整筆折扣的 clamp 邊界又是一個註解裡的判讀：

```dart
// 上限用 itemsSubtotal 而非 originalAmount，避免單品折扣 + 整筆折扣
// 加總超過商品總額導致應付為負。
final cartDiscountAmount = rawCartDiscount > itemsSubtotal ? itemsSubtotal : ...;
```

直覺會拿「商品原始總額」當上限，但單品折扣已經先扣了一輪——整筆折扣的真正可用空間是**扣完單品折扣後的餘額**。兩層折扣各自對自己的空間 clamp，「應付金額不會為負」這個輸出契約才成立。多層減項的通用判讀：每一層的邊界要對「前面各層扣剩的餘額」算、不對原始值算。

## 細節三：擴充點先設計、但不先實作

未來的折扣規則（會員等級、促銷、優惠券、滿額減）還沒被後端定義，函式的註解預留了接入方式：規則成形時新增一個並列的 pure function（`cartDiscountView`），規則需要的 IO 資料同樣由 caller 拿好傳入，本函式在算完品項後呼叫它、把結果套進三個金額欄位——**本函式與所有 UI 都不需要改**。

這跟[過度設計震盪](/work-log/flutter_async_query_overdesign_oscillation/)裡「先做起來放」的偽需求處置形成正面對照：擴充點的設計成本是一段註解（接入位置、簽章形式、啟用點），實作成本是零——它把「未來怎麼接」的思考結果留下來、把「現在就寫」的浪費留在門外。同樣的態度也出現在整筆折扣的來源上：「商業邏輯尚未由後端定義，此處先以前端 model 自洽為主；未來後端開接口時 caller 改傳後端值即可」。

## 判讀徵兆

- 同一段「從資料算出畫面要的數字」邏輯散在多個 widget / controller 裡——抽 pure function 的時機，重複第二次就該動手
- 領域計算的測試裡出現 repository mock——計算跟 IO 黏在一起了，把資料取得推給 caller、測試立刻減重
- 合併或對帳結果「偶爾多扣 / 少一筆」——查 key 的維度是否少於 domain 對「同一個」的定義
- 多層折扣 / 費用的邊界檢查全部對原始總額算——疊加後可能穿底，逐層對餘額 clamp

## 相關閱讀

- 同專案的資料語意背景：[桌子跟購物車是兩個聚合](/work-log/pos_table_cart_lifecycle_decoupling/)——提前結帳的生命週期設計是本文「份數扣減」需求的來源；[同一個品項、四個 model](/work-log/dart_pos_item_four_lifecycle_models/)——合併產出的 `OrderedCartItem` 與 `sourceDetailIds` 的身份設計
- 概念地基：[DDD 領域驅動設計指南](/ddd/)——領域計算的歸屬、以及「從操作推導領域」（提前結帳這個操作逼出了整個 view 函式）
