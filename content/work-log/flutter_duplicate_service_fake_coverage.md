---
title: "兩個 domain 各自實作同一個 API service — 100% 覆蓋率的假象"
date: 2026-07-10
draft: false
description: "同名 service 在多個 domain 各自實作時，覆蓋率數字會失去意義：每份實作各測各的、mock 各有介面，統一的行為從未被測過。重複實作是上游訊號——規劃文件沒抽出跨 domain 的共同技術需求；單檔品質審查看不到跨檔重複。"
tags: ["flutter", "dart", "ddd", "clean-architecture", "testing", "infrastructure"]
---

> **觸發場景**：Flutter 書籍管理 App 開發到 v0.4，發現 Search 跟 Scanner 兩個 domain 各有一份 `GoogleBooksApiService`。一句反問觸發了完整稽核：「如果有重複的 service，那是不是表示我們的規劃文件跟 domain test 也都有問題？」
> **疑問來源**：重複實作看起來只是 DRY 違反、抽出來就好——為什麼值得往規劃文件跟測試架構追？
> **整理目的**：記下「重複 service」作為上游訊號的判讀方式、以及它對覆蓋率數字的破壞機制
> **本文邊界**：素材是該專案 v0.4.0 的架構債分析記錄；當時的修正計畫（統一 Infrastructure 層）在後續版本執行

---

## 重複的現場：兩份實作、三套 mock

稽核盤出來的重複不只一層。實作層，Search domain 有一份完整的 `GoogleBooksApiService`（含 API client 與回應解析器），Scanner domain 有另一份不同的實作（帶自己的模擬回應機制）。測試層更碎：兩套 `MockGoogleBooksApiService` 散在不同的 helper 檔、**介面彼此不同**；而 Search 跟 Scanner 的 domain 測試裡，效能相關的測試直接 `GoogleBooksApiService()` 用真實服務打網路。

每一份單獨看都寫得不差——這正是它能存活到 v0.4 的原因。前一輪重構（v0.3.x）專注單檔程式碼品質，跨 domain 的架構審查不在範圍內，稽核記錄裡的那句話說中了機制：**重複實作被各自的高品質掩蓋**。品質工具的作用域是單檔，重複是跨檔性質，作用域不含它、它就不會被回報。

## 覆蓋率數字的破壞機制

「測試覆蓋率 100%」在這個結構下是個精確但無意義的數字。分母綁著實作：Search domain 的測試覆蓋 Search 的實作、Scanner 的測試覆蓋 Scanner 的實作、mock 服務又測著第三種介面——三個 100% 加起來，**「這個 App 查詢 Google Books 的行為」這件事沒有任何一份統一的測試在守**。

兩份實作對同一個 API 的邊界行為（rate limit、空結果、格式變化）可以各自演化出不同的處理，而測試不會抓到分歧——因為每份測試只知道自己那份實作。單元測試裡混用的真實 API 呼叫則往反方向破壞：測試結果隨網路狀態擺盪，綠燈紅燈都不再指向程式碼。

## 往上游追：重複是規劃缺陷的下游症狀

那句反問的價值在於方向——它問的是「重複從哪來」而不是「重複怎麼修」。往上游追的結果：需求規格書在三個 use case（匯入、掃描、搜尋）各自描述了 Google Books API 整合，規劃階段沒有識別出「這是同一個技術能力被三個流程共用」；事件驅動架構的設計文件裡甚至直接寫著各 domain 自行呼叫 API 的範例。

也就是說，兩份實作是忠實執行了規劃——**規劃本身就是重複的**。只修程式碼層（把兩份合成一份）而不修規劃文件，下一個新 use case 照著文件開發時會長出第三份。這是把修法對準病因而不是症狀的又一個實例。

## 修法：歸位到 Infrastructure、單一抽象 + 單一 mock

修正方向把 API 服務歸位到它該在的層：

- Google Books API 是**基礎設施能力**、不是任何單一 domain 的知識——建立 `lib/infrastructure/api/` 收統一實作
- domain 依賴抽象介面 `BookInfoApiService`（`queryByIsbn` / `searchByTitle`），透過注入取得
- mock 收斂成一份、實作同一個抽象介面——mock 的介面從此跟真實服務的介面由同一個 abstract class 保證一致

分層的判準在這個 case 裡很乾淨：**會被多個 domain 用同一種方式消費的技術能力，屬於 Infrastructure**；domain 層持有的是「用查到的資料做什麼」的業務知識，不是「怎麼查」的技術知識。

## 判讀徵兆

- 同名（或近義名）的 service class 出現在多個 domain 目錄
- 同一個外部依賴有多套 mock、且介面不一致——mock 介面的分歧就是實作分歧的投影
- 單元測試裡 `new` 出真實的網路 / IO 服務
- 覆蓋率高但「某個跨 domain 行為壞掉沒有測試會紅」的直覺不安

第一項成本最低：`grep -r "class.*ApiService" lib/domains/` 一次列出所有候選。第二項是最早的訊號——寫第二套 mock 的那一刻，通常就是重複實作誕生的時刻，只是當下感覺是在「補測試」。

## 相關閱讀

- 概念地基：[DDD 領域驅動設計指南](/ddd/) 的分工表——domain 與 Infrastructure 的邊界
- 覆蓋率假象的姊妹篇：[192 個測試全過、實機全壞](/work-log/testing_three_layer_strategy/)——那篇是 mock 遮蔽真實行為、本文是重複實作讓覆蓋率分母失義，兩種機制都產出「綠燈但沒有保障」
- 作用域原則：[#221 檢查規則的作用域要顯式列舉](/report/lint-scope-must-be-explicit-fact/)——「重複被各自的高品質掩蓋」是同一件事的 review 版本：單檔品質審查的作用域不含跨檔性質
