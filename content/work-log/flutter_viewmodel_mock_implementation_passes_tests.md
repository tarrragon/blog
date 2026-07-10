---
title: "產品碼自己是 mock — ViewModel 假實作通過了 15 個測試"
date: 2026-07-10
draft: false
description: "ViewModel 用 Future.delayed 加硬編碼資料交付、狀態轉換測試全綠，因為測試耦合的是狀態機、不是業務效果。假實作被當成完成的基礎，直到 63 個測試「寫不出來」才現形——測試的可寫性是實作真實性的探針。"
tags: ["flutter", "dart", "testing", "viewmodel", "tdd", "mock"]
---

> **觸發場景**：Flutter 書籍管理 App 的搜尋功能（UC-04），ViewModel 在前一張 ticket 交付、狀態轉換測試全過。下一張 ticket 要補齊設計時規劃的 102 個測試，卡在 39 個——剩下 63 個怎麼樣都寫不出來
> **疑問來源**：測試寫不出來，是測試設計的問題、還是別的？
> **整理目的**：記下「產品碼自己是 mock」這種假綠形態的機制與判讀訊號——它跟「mock 遮蔽真實」是鏡像關係
> **本文邊界**：素材是該專案 v0.15.12 到 v0.15.14 三張 ticket 的記錄；「假實作要不要存在」跟「假實作有沒有被標記」是兩個問題、本文主張只針對後者

---

## 現場：交付的 ViewModel 是假的

前一張 ticket 交付的 `SearchBookViewModel`，所有業務邏輯長這樣：

```dart
// 「搜尋會話初始化」
await Future.delayed(const Duration(milliseconds: 100));

// 「搜尋 API 呼叫」
await Future.delayed(const Duration(milliseconds: 300));
final mockCandidates = <SearchCandidateWithScore>[
  SearchCandidateWithScore(
    candidate: SearchCandidate(id: 'mock1', title: '搜尋結果 1', ...),
  ),
];
```

沒有整合任何真實 UseCase——`Future.delayed` 模擬耗時、硬編碼清單模擬結果。而它通過了交付時的全部狀態轉換測試，品質評估甚至給了高分（程式碼品質 8.8/10），只在測試品質欄位留了一句「缺少 ViewModel 邏輯測試」。

## 為什麼假實作能過測試

測試斷言的對象是**狀態機**：`initiateSearch()` 之後狀態進 loading、結果回來之後進 loaded、錯誤時進 error。假實作忠實地走完了這整套狀態轉換——`Future.delayed` 提供了「非同步等待」的形狀、`mockCandidates` 提供了「有結果」的形狀。狀態轉換是真的發生了，只是驅動它的內容是假的。

**測試耦合到什麼、就只能守住什麼。** 狀態轉換測試守住「狀態會照圖走」，守不住「走的過程做了真的事」。這是「192 個測試全過、實機全壞」的鏡像：那篇的 mock 在測試側（test double 遮蔽真實行為）、本文的 mock 在**產品側**——測試裡沒有半個 test double，被測物自己就是替身。

## 現形機制：寫不出來的測試是探針

假實作的暴露不是靠 review、是靠下一張 ticket 的實際卡點：設計時規劃的 102 個測試只能完成 39 個（38%），剩下 63 個被標記「簡化版跳過」——每一類都寫不出來、而且寫不出來的原因各自指向假實作缺的那塊：

- UseCase 協調邏輯測試——沒有 UseCase 可協調
- EventBus 事件驗證——沒有事件被發送
- 暫停 / 恢復測試——「簡化版處理速度太快，無法測試中途暫停」（假實作連時序都是假的）

這給出一個反直覺的判讀：**測試「寫不出來」是關於產品碼的資訊、不是關於測試的**。斷言想抓的行為在實作裡不存在時，測試自然無處下手——63 個寫不出來的測試就是 63 條「這段邏輯是假的」的證言。修正（下一張 ticket 重做真實實作：注入五個 UseCase 與 EventBus、移除全部四處 `Future.delayed`、發送八個 domain event）之後，這批測試才有東西可測。

## 問題不在骨架、在骨架沒有標記

「先建簡化版、後補真實整合」本身是合理的分批策略——問題出在簡化版**沒有任何機器可見的標記**。它不 throw `UnimplementedError`、方法名沒有 stub 字樣、沒有 TODO 註解在交付清單裡追蹤，於是下一張 ticket 把它當成已完成的基礎往上蓋，直到蓋不動。

假實作要存在，就讓它誠實：

- 沒實作的路徑 `throw UnimplementedError('UC-04 Ticket 9')`——測試會紅、紅得有座標
- 或者硬編碼路徑用命名標記（`_mockSearchResults`）加交付文件裡的顯式缺口清單
- 完成度的宣告跟著「真實整合」走、不跟著「測試通過率」走——本 case 的通過率量的是狀態機的完成度、不是功能的

同專案更早有一個同族 case：整批測試用 `fail('功能尚未實作')` 佔位，讓完成度被反向低估。兩個方向合起來是同一課：**測試通過率只有在「測試斷言真實效果、實作沒有替身」時才代表完成度**，兩個前提壞掉任何一個，這個數字就開始說謊。

## 相關閱讀

- 鏡像篇：[192 個測試全過、實機全壞](/work-log/testing_three_layer_strategy/)——mock 在測試側 vs mock 在產品側，同一個「綠燈失義」的兩個方向
- 同構原則：[#221 檢查規則的作用域要顯式列舉](/report/lint-scope-must-be-explicit-fact/)——「測試全綠」的訊號跟「沒被測到」的訊號長一樣；本文的 63 個寫不出來的測試就是把「沒被測到」變成可見訊號的機制
- 概念地基：[DDD 領域驅動設計指南](/ddd/)——ViewModel 作為 UseCase 與 UI 的膠水層、它的「真實性」就是有沒有真的在協調 UseCase
