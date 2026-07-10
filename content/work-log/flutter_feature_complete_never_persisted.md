---
title: "功能「完成」、測試全過、資料從未落地 — 持久化迴圈是驗收的盲區"
date: 2026-07-10
draft: false
description: "domain 功能的測試可以全綠、而它的資料從未被序列化、資料庫沒有對應的表——單元測試都在記憶體內驗證行為、沒有一條測試走「存進去、重建、讀出來」的迴圈。驗收定義要含 roundtrip；entity 欄位與 schema 欄位的差集是靜默資料失真的清單。"
tags: ["flutter", "dart", "ddd", "persistence", "sqlite", "testing", "serialization"]
---

> **觸發場景**：Flutter 書籍管理 App 的借閱功能（UC-06）開發完成——value object、業務方法、狀態屬性、測試全過、宣告完成。兩個 use case 之後、準備跨裝置同步（UC-07）時的架構盤點才發現：借閱資料從未被持久化，App 重啟借閱狀態就消失
> **疑問來源**：測試全綠的功能怎麼會漏掉整個持久層？而且漏了兩個 use case 都沒人發現？
> **整理目的**：記下持久化缺口躲過驗收的機制、以及把它攔在完成宣告之前的檢查點
> **本文邊界**：素材是該專案 v0.18（借閱持久化補齊）與 v0.32（tag 遷移盤點）兩份記錄；兩個 case 是同一個盲區的兩種形態

---

## Case 1：整個持久層缺席、功能照樣「完成」

UC-06 交付時的狀態：`BookLoan` value object 完整（借閱類型、日期、歸還、逾期判斷）、`Book` entity 有整組借閱管理業務方法、狀態屬性齊全、測試全過。但三個持久化環節全部缺席：

- `Book.toJson()` 沒有序列化 `activeLoan`
- `Book.fromJson()` 沒有解析 `activeLoan`
- 資料庫沒有 `book_loans` 表

後果是功能在單次執行內完全正常、App 重啟即失憶。這個洞存活了兩個 use case，直到 UC-07（跨裝置同步）的前置盤點把各層完成度攤開——Schema 層 95%、Domain 層 80%、**Book Entity 40%（缺借閱序列化）**——才現形。發現它的不是測試、是「同步需要資料在裝置之間移動、而借閱資料根本出不了記憶體」這個下游需求。

## 躲過驗收的機制：測試的邊界就是持久化的盲區

測試全綠跟資料沒落地並不矛盾——所有測試都在記憶體內驗證業務行為：借書之後 `isActive` 為真、歸還之後 `isReturned` 為真、逾期計算正確。**沒有任何一條測試走過「序列化、重建、比對」的迴圈**，於是「這個物件能不能離開記憶體」從來不在任何斷言的守備範圍內。

單元測試的這個邊界是結構性的：domain 測試本來就不該碰資料庫。問題出在完成定義——「domain 測試全過」被當成了「功能完成」，而持久化迴圈不在任何 use case 的驗收條件裡。修正時補上的測試正好說明缺的是哪一類：序列化測試（DM-35 到 DM-38、SER-01 到 SER-11）裡最關鍵的是**循環一致性**——`toJson` 再 `fromJson` 回來的物件要跟原物件相等。roundtrip 測試不碰資料庫、成本跟單元測試相同，但它守住「這個物件的完整狀態能離開又回來」。

修正本身是機械的：補 `BookLoan.toJson/fromJson`、`Book` 的 activeLoan 序列化、建 `book_loans` 表加索引、資料庫版本 v4 升 v5 附遷移腳本。機械修正花一個 Phase 0 就完成——貴的從來不是修、是晚了兩個 use case 才發現。

## Case 2：更陰險的形態——欄位存在、寫入層靜默丟棄

同一個專案後期（v0.32）的 tag 系統遷移盤點，抓到同一個盲區的第二形態。`Book` entity 有 `genre`、`source`、`importance` 欄位，遷移設計假設七類資料都有來源；實際掃描 schema 與 repository 後發現：

> books 實體表僅持久化 4 個欄位……source 無實體欄位、`_mapToBook` 恆回傳 `BookSource.physical()`、未持久化；genre 無實體欄位、`_bookToMap` 無 genre key。

這比 Case 1 陰險：Case 1 是欄位不見（重啟後 `activeLoan` 是 null、至少看得出來空了），Case 2 是**預設值冒充資料**——每本書讀出來 source 都是 `physical`，欄位「有值」、值是假的。統計、篩選照著假值運作，沒有任何一層會報錯。這次盤點的價值在於把落差變成顯式決策：遷移行為契約以實際有資料的 4 欄為準、對另外三類明確標記 no-op，而不是讓 Phase 2 測試對不存在的資料設斷言。

## 檢查點：把持久化迴圈寫進完成定義

兩個 case 收斂成三個可操作的檢查：

- **roundtrip 測試是每個可持久化 entity 的標配**：`fromJson(toJson(x)) == x`，含每個 optional 欄位有值與無值的變體。它抓 Case 1 的整段缺席，也抓「加了欄位忘了序列化」的增量缺口
- **entity 欄位對 schema 欄位做差集**：差集裡的每個欄位，要嘛有明確的「不持久化」決策記錄、要嘛就是一筆靜默失真。Case 2 的三個欄位在差集裡躺了很久、沒有人決策過
- **mapper 裡的常數是警訊**：`_mapToBook` 恆回 `BookSource.physical()` 這種寫死的預設值，語意是「這個欄位的讀取路徑沒有來源」——它該是一個顯式的 TODO 或決策，不該長得跟正常映射一樣

「功能完成」的定義問題在這兩個 case 裡是同一個：完成度被「行為測試通過率」代表，而行為測試的守備範圍不含資料的出入境。驗收條件補一句「重啟後狀態仍在」，兩個洞都會在第一天現形。

## 相關閱讀

- 同族的增量版：[新增欄位忘記同步 reset](/work-log/reset_state_leak_cross_test/)——entity 加欄位時的同步點清單（constructor / copyWith / toJson / fromJson / schema / mapper），本文的 Case 2 就是清單裡 schema 與 mapper 兩項長期缺席的結果
- 同構原則：[#221 檢查規則的作用域要顯式列舉](/report/lint-scope-must-be-explicit-fact/)——「測試存在」與「測試涵蓋持久化迴圈」是兩個獨立的 fact，全綠只證明前者
- 概念地基：[DDD 領域驅動設計指南](/ddd/)——entity 的完整性包含它跨越持久化邊界的能力
