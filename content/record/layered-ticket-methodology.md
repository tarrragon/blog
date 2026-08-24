---
title: "層級隔離：讓每張 Ticket 只做一件層級的事"
slug: "layered-ticket-methodology"
date: 2026-03-04
draft: false
description: "PR 一次動了四層、review 無從下手時，用來把 Clean Architecture 的分層轉成 Ticket 的拆法與執行順序"
tags: ["AI協作心得", "Ticket", "方法論", "Clean Architecture"]
---

架構圖上的層級分得清楚，而 PR 一次動了 UI、Controller、UseCase 和 Entity 四層——這代表分層規範了程式碼的組織方式，沒有規範任務的切法。

<!--more-->

## 問題不在架構，在派工

Clean Architecture 規範的是程式碼怎麼組織，它不涉及 Ticket 怎麼拆。這個空缺會在兩個位置顯現：review 要從 Widget 一路讀到 Entity，沒有可以開始的位置；Domain 還沒穩定時 UI 層測不了，兩邊互相等待。

補上這個銜接點的是 Ticket 拆法本身的規則。

## 核心原則：一張 Ticket，一個層級

> 一個 Ticket 只應該修改單一架構層級的程式碼，變更的原因單一且明確。

SRP 說一個類別只有一個改變的原因，這條規則升一層之後就是：一張 Ticket 也只有一個改變的原因。

限制帶來的四個性質是直接的：review 只需要理解一層的邏輯、測試不需要拉起整個系統、PR 的影響範圍可預測、失敗時的定位範圍限定在一層。

## 五層的定義

傳統 Clean Architecture 四層裡，Interface Adapters 同時處理事件邏輯與資料轉換兩種職責。把它拆開之後得到五層：

**Layer 1 — UI/Presentation**：純視覺呈現，Widget 長什麼樣。變更原因只有一個：設計稿改了。

**Layer 2 — Application/Behavior**：事件處理和 UI 邏輯。按鈕點擊怎麼處理、Loading 狀態怎麼切換、Domain Entity 怎麼轉成 ViewModel。Flutter 對應 Controller 和 ViewModel。

**Layer 3 — UseCase**：業務流程編排。協調多個 Repository 和 Domain Service，把業務步驟串起來。不管 UI 怎麼顯示，也不管資料庫怎麼存。

**Layer 4 — Domain Events/Interfaces**：定義契約。Repository 抽象介面、Domain Event 結構、跨層 DTO。只定義，不實作。

**Layer 5 — Domain Implementation**：核心業務邏輯。Entity、Value Object、Domain Service、業務規則驗證。整個系統最穩定的部分。

Infrastructure 層（資料庫、外部 API、EventBus）不納入層級隔離，它的變更驅動是技術決策，不是業務需求，Ticket 設計上本來就獨立對待。

## 從外而內，而不是從內而外

許多教材的建議是先設計 Domain 再往外做。從風險控制的角度，順序相反更合適。

原因很簡單：Layer 1 UI 壞掉只影響視覺，Layer 5 Domain 邏輯壞掉影響整個系統的業務規則。從影響最小的地方開始，需求偏差時調整成本低；一開始就動 Domain，到了 UI 才發現需求理解有誤，代價就大得多。

實作順序是 Layer 1 → Layer 2 → Layer 3 → Layer 4 → Layer 5，每層完成後立即驗證。

有幾個例外：架構遷移要先定義 Layer 4 介面契約（Interface-First），讓外層修改有穩定依據；安全性修復從 Layer 5 往外；Bug Fix 從問題根源那層開始。

## Ticket 拆分的量化標準

幾個判斷指標：修改檔案數 1 到 3 個（最多 5 個）、預估開發時間 2 到 8 小時（超過一天就拆）、修改層級嚴格限制 1 層、新增程式碼測試覆蓋率 100%。

數字可以商議，但有標準就不用靠直覺判斷「感覺差不多」。

反面教材：

```text
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

它是 Clean Architecture 的派工指南：Clean Architecture 管程式碼怎麼組織，層級隔離管 Ticket 怎麼拆、按什麼順序做。

它和 Atomic Ticket 方法論也不衝突：Atomic Ticket 強調職責維度（一個 Action 加一個 Target），層級隔離強調層級維度（一個 Ticket 只動一層），兩個維度同時符合才是最完整的 Ticket 設計。

緊急 Hotfix、原型開發、一次性腳本不套用這套規則。在常規的功能開發與重構裡，把一個大需求拆成按層排好的 Ticket 序列這個動作本身，就是對架構邊界的一次逐層確認。

架構違規怎麼在 commit 階段被自動擋下，走 [架構合規交給機制](../layered-architecture-quality-checking/)。
