---
title: "層級隔離：讓每張 Ticket 只做一件層級的事"
date: 2026-03-04
draft: false
description: "我們在實際開發中整理出一套方法論，讓 Clean Architecture 五層架構與 Ticket 拆分真正結合——每張 Ticket 只修改一個架構層，不多也不少。"
tags: ["AI協作心得", "Ticket", "方法論", "Clean Architecture"]
---

架構圖貼出來，層級畫得漂漂亮亮，但 PR 送進來還是一次動了 UI、Controller、UseCase 和 Entity 四層。

<!--more-->

## 問題不在架構，在派工

Clean Architecture 告訴你「怎麼組織程式碼」，但沒告訴你「怎麼拆 Ticket」。每次 Code Review 都像翻地層，從 Widget 翻到 Entity，不知道從哪開始看；Domain 沒穩定，UI 那層就沒辦法測，整個流程互相等待。

這個銜接點，需要一套專門處理 Ticket 拆法的方法論。

## 核心原則：一張 Ticket，一個層級

> 一個 Ticket 只應該修改單一架構層級的程式碼，變更的原因單一且明確。

SRP 說一個類別只有一個改變的原因，我們把它升一層：一張 Ticket 也只有一個改變的原因。

聽起來嚴苛，但實際跑起來好處很直接：Code Review 只需要理解一層的邏輯、測試不需要拉起整個系統、PR 影響範圍可預測，壞掉的時候更容易定位。

## 我們怎麼定義「五層」

傳統 Clean Architecture 四層中，Interface Adapters 同時處理「事件邏輯」和「資料轉換」，職責太雜，我們把它細分成五層：

**Layer 1 — UI/Presentation**：純視覺呈現，Widget 長什麼樣。變更原因只有一個：設計稿改了。

**Layer 2 — Application/Behavior**：事件處理和 UI 邏輯。按鈕點擊怎麼處理、Loading 狀態怎麼切換、Domain Entity 怎麼轉成 ViewModel。Flutter 對應 Controller 和 ViewModel。

**Layer 3 — UseCase**：業務流程編排。協調多個 Repository 和 Domain Service，把業務步驟串起來。不管 UI 怎麼顯示，也不管資料庫怎麼存。

**Layer 4 — Domain Events/Interfaces**：定義契約。Repository 抽象介面、Domain Event 結構、跨層 DTO。只定義，不實作。

**Layer 5 — Domain Implementation**：核心業務邏輯。Entity、Value Object、Domain Service、業務規則驗證。整個系統最穩定的部分。

Infrastructure 層（資料庫、外部 API、EventBus）不納入層級隔離，它的變更驅動是技術決策，不是業務需求，Ticket 設計上本來就獨立對待。

## 從外而內，而不是從內而外

許多教材說「先設計 Domain 再往外做」，但實際開發時，我們發現從外而內更能控制風險。

原因很簡單：Layer 1 UI 壞掉只影響視覺，Layer 5 Domain 邏輯壞掉影響整個系統的業務規則。從影響最小的地方開始，需求偏差時調整成本低；一開始就動 Domain，到了 UI 才發現需求理解有誤，代價就大得多。

實作順序是 Layer 1 → Layer 2 → Layer 3 → Layer 4 → Layer 5，每層完成後立即驗證。

有幾個例外：架構遷移要先定義 Layer 4 介面契約（Interface-First），讓外層修改有穩定依據；安全性修復從 Layer 5 往外；Bug Fix 從問題根源那層開始。

## Ticket 拆分的量化標準

幾個判斷指標：修改檔案數 1 到 3 個（最多 5 個）、預估開發時間 2 到 8 小時（超過一天就拆）、修改層級嚴格限制 1 層、新增程式碼測試覆蓋率 100%。

數字可以商議，但有標準就不用靠直覺判斷「感覺差不多」。

反面教材：

```
Ticket：實作書籍收藏功能

變更範圍：
- lib/ui/pages/book_detail_page.dart       (Layer 1)
- lib/application/controllers/book_detail_controller.dart  (Layer 2)
- lib/usecases/add_book_to_favorite_usecase.dart  (Layer 3)
- lib/domain/entities/favorite.dart        (Layer 5)
```

這張 Ticket 跨了四層，PR 送出來沒人知道從哪開始審，測試也很難設計。正確做法是拆成四張各自獨立的 Ticket，按依賴順序執行。

## 如何判斷一段程式碼屬於哪一層

最常模糊的是 Layer 2 和 Layer 3 之間的邊界。判斷流程：

1. 在渲染 UI 元素？→ Layer 1
2. 在處理 UI 事件、控制 UI 狀態、或把 Domain 資料轉成 UI 格式？→ Layer 2（把 Domain Exception 轉成 ErrorViewModel 也是這層的事）
3. 在協調多個 Domain Service 或 Repository、編排業務步驟？→ Layer 3
4. 在定義介面契約或事件結構？→ Layer 4
5. 在實作業務規則或定義 Entity？→ Layer 5
6. 以上都不是 → Infrastructure 層

## 這套方法論的定位

這不是要替代 Clean Architecture，而是它的「派工指南」。Clean Architecture 告訴你程式碼怎麼組織，層級隔離告訴你 Ticket 怎麼拆、按什麼順序做。

它和 Atomic Ticket 方法論也不衝突：Atomic Ticket 強調職責維度（一個 Action 加一個 Target），層級隔離強調層級維度（一個 Ticket 只動一層），兩個維度同時符合才是最完整的 Ticket 設計。

緊急 Hotfix、原型開發、一次性腳本不需要強行套用。但在正常功能開發和重構中，跑起來之後的感覺是：每次把一個大需求拆成按層排好的 Ticket 序列，就等於把架構邊界重新確認了一遍。
