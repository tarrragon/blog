---
title: "文件裡的扁平 Product、程式碼裡的雙層聚合 — 宣稱型文件的半衰期"
date: 2026-07-10
draft: false
description: "refactor 總結文件記的是決策時刻的快照：扁平 Product（一商品一價一庫存）在真實 POS 業務下演化成 Product + ProductSpecification 雙層、價格三種下沉到規格。欄位放聚合根還是子層的判準是「兩個規格會不會不同」；文件預言的需求全中、預言的結構全錯——這正是先蓋結構會蓋錯的實證。"
tags: ["dart", "flutter", "ddd", "aggregate", "documentation", "pos", "model-evolution"]
---

> **觸發場景**：整理 POS 專案時對照 `doc/PRODUCT_MODEL_REFACTOR.md` 跟 `lib/data/models/product/product.dart`——文件描述的 Product 是扁平結構（barcode、price、stockCount 直接掛在商品上），現行程式碼是 Product + ProductSpecification 雙層、幾乎沒有一個欄位還在文件說的位置
> **疑問來源**：這份文件錯了嗎？還是它只是過期了？兩者的差異本身能教什麼？
> **整理目的**：記下扁平商品模型被真實業務打破的具體壓力、欄位歸屬的判準、以及宣稱型文件的正確用法
> **本文邊界**：素材是該專案的 refactor 總結文件（早期）與現行 model；「落差」是十個月演化的累積、不是單次重構的 before/after

---

## 文件的版本：一商品、一價、一庫存

refactor 總結文件裡的 Product 是教科書式的扁平 model：

```dart
const factory Product({
  required String barcode,
  required double price,
  @Default(0.0) double discount,
  required double currentPrice,
  @Default(0) int stockCount,
  @Default('') String category,
  ...
});
```

搭配 `updateStock` / `reduceStock` / `applyDiscount` 業務方法、跟一張「未來擴展」清單：商品分類管理、庫存管理、折扣策略、商品圖片。文件當時的重構是成立的（把散裝參數收成 model、UI 從六個參數變一個物件）——問題不在那次重構、在這個結構隱含的假設：**一個商品有一個條碼、一個價格、一份庫存**。

## 業務打破它的方式：規格

真實 POS 的第一批客戶就帶著飲料店跟零售的需求：中杯與大杯是同一個商品的兩個**規格**，各自有條碼、售價、會員價、進價、庫存、甚至各自的圖片。現行的 model 把這個現實建成雙層：

```dart
abstract class ProductSpecification {   // 會被規格分化的一切
  required String id, name, barcode;
  required Money sellingPrice, purchasePrice, memberPrice;
  Money? cost, rebate;
  @Default(0) int inventory;
  bool enableIgnoreInventory;
  Cover? cover;
}

abstract class Product {                // 跨規格共用的資訊
  required String id, name;
  ProductCategory? productCategory;
  Brand? brand;  Supplier? supplier;
  List<Tag> tags;
  List<CustomizationOption>? customizationOptions;
  List<ProductSpecification> specifications;
  Device? kitchenDevice;                // 廚房出單機路由
}
```

欄位歸屬的判準收成一句：**問「兩個規格會不會不同」**。條碼會（中杯大杯各一個店內碼）、價格會（三種價都會）、庫存會——下沉到 spec；名稱、品牌、供應商、分類、客製化選項、廚房路由不會——留在聚合根。price 的取得也跟著變成規格層的方法（`spec.getPrice(isMember)`），「商品的價格」這個問法在新結構裡根本不成立——只有「某規格對某身分的價格」。

型別也在同一段演化裡逐級升級：`double` 價格換成 `Money`（[三段遷移](/work-log/dart_money_extension_type_migration/)）、`String category` 換成 `ProductCategory` model、裸 URL 換成 `Cover` model。扁平版留下的痕跡只剩一個向後兼容 getter（`productName => name`）。

## 預言全中、路徑全錯

值得玩味的是文件的「未來擴展」清單——商品分類、庫存、折扣、圖片——**每一項都發生了**，但沒有一項是「在扁平模型上加欄位」實現的：分類變成獨立 model、庫存變成 per-spec 欄位加 `enableIgnoreInventory` 開關、折扣走進 `CartItem.discount` 與會員價機制、圖片變成 spec 與商品兩層的 `Cover`。

這是 YAGNI 最好的論據形式：**預測「會有什麼需求」不難、預測「結構會怎麼長」幾乎不可能**。如果當年順著清單先把欄位蓋起來（`String category`、`double discount`），每一個都會變成後來要遷移的錯誤結構——事實上 `double price` 跟 `String category` 正是這樣被遷移掉的。需求清單可以先列（它是雷達）、結構要等需求真的到場才定形。

## 宣稱型文件的正確用法：考古、不是導覽

這份文件沒有錯、它只是停在了自己的時刻。專案裡真正跟著程式碼走的知識在 **model 的註解**——`kitchenDevice` 欄位旁邊寫著業務規則與 fallback 行為、`ShoppingCart` 的契約註解、`unsettledCartView` 的擴充規劃——它們跟被註解的程式碼同檔、同 commit、同生死。

分工可以講明白：**宣稱型文件（design doc、refactor 總結）記決策時刻的理由，讀法是考古**——「當時為什麼這樣想」；**貼身註解記現行契約，讀法是導覽**——「現在它怎麼運作」。把宣稱型文件當導覽讀是事故來源（照著文件的欄位名寫程式碼、發現一個都不存在）；反過來要求宣稱型文件永遠同步則是不可能的維護承諾——它的價值本來就是快照。

## 判讀徵兆

- doc 目錄的文件描述的 API / 欄位在 codebase 裡 grep 不到——文件已進入考古態，讀它時切換心態、別照著寫程式碼
- 商品 / 資源類 model 出現「同一概念、多個變體」的需求（規格、方案、版本）——扁平模型的死期，先做歸屬判準（哪些欄位會被變體分化）再拆層
- 「未來擴展」清單裡的項目被預先建成欄位——每一個都是將來的遷移債，清單留著、欄位等需求
- 業務規則寫在文件而不是欄位旁——文件會漂移、貼身註解不會；規則跟著它約束的程式碼放

## 相關閱讀

- 同專案的型別演化：[Money 三段遷移](/work-log/dart_money_extension_type_migration/)——`double price` 的下場
- 「先蓋結構會蓋錯」的另一個現場：[異步查詢系統的過度設計震盪](/work-log/flutter_async_query_overdesign_oscillation/)——設計期想像的結構被砍、真結構從操作長出來
- 原則層：[#206 預測性索引要有寫後回填輪](/report/predictive-index-needs-backfill-pass/)——寫作領域的同構：寫前的預測性宣告、完成後不回填就雙向失真
- 概念地基：[DDD 領域驅動設計指南](/ddd/)——聚合根與其組成的邊界
