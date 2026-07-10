---
title: "溢出 714px、22 個測試同時紅 — 單點修復與規範化的分界"
date: 2026-07-10
draft: false
description: "Row 裡未受 Flexible 包裹的固定尺寸元件在窄約束下溢出；同型失敗一次爆 22 個時，正確的產出不是 22 個修復、是一份 overflow 預防規範（反模式清單 + 決策樹 + 測試檢查項）。含測試環境小尺寸是 feature、以及 stale ticket 先考古再執行的教訓。"
tags: ["flutter", "dart", "renderflex", "layout", "widget-test", "spec", "refactoring"]
---

> **觸發場景**：Flutter 書籍管理 App 的 UC-04 區塊測試，widget 測試 9/31 通過——22 個失敗全是同一種錯：`RenderFlex overflowed by N pixels`。最大的一筆溢出 714px，來源是 `advanced_search_widget.dart:106` 一個 Row 裡未受 `Flexible` 包裹的 `SegmentedButton`
> **疑問來源**：22 個同型失敗，是修 22 次、還是做一件別的事？
> **整理目的**：記下 overflow 的約束機制、測試環境尺寸的角色、以及「單點修復 vs 抽規範」的判準；附 stale ticket 接手的考古教訓
> **本文邊界**：素材是該專案 v0.31.1 的 W1-011 系列記錄（從發現、拆票、規範建立到修復完成、橫跨兩個多月）

---

## 機制：Row 不會替固定尺寸的子元件求情

`RenderFlex overflowed` 的成因用一句話講完：**flex 容器裡的子元件宣告了固定尺寸需求、而容器的約束裝不下**。Row 對子元件的預設處理是「你要多寬給多寬」，`SegmentedButton` 這類內容驅動寬度的元件在窄約束下要求超過可用寬度時，Row 不會自動壓縮它——溢出、畫黃黑條、測試紅。

修法的方向有三個位階：包 `Flexible` / `Expanded`（讓子元件接受壓縮）、換可捲動容器（內容本來就可能超過一屏）、重設計版面（內容密度本身不合理）。這次選的是第一種的變體——Wrap 方案，因為測試對 `SegmentedButton` 的行為契約有明確要求、元件本身不能換。溢出量還有一個可判讀的性質：它是**內容需求與可用空間的差**，714px 的溢出說明這不是差幾個 padding 的微調問題、是整段版面對窄螢幕沒有任何彈性策略。

## 測試環境的小尺寸是 feature

22 個失敗集中在測試環境（800x600、以及另一批 375x812）現形，實機大螢幕上未必看得到——這容易被誤讀成「測試環境太苛刻」。方向要反過來：**測試環境的小尺寸是免費的窄螢幕模擬**。真實使用者裡有小手機、有分割畫面、有字體放大（同專案另一批 [Dialog 溢位隨狀態增長](/work-log/flutter_test_failure_triage_root_cause_roi/)的數據就是這樣量出來的），widget 測試的固定小尺寸把這些情境提前到 CI 裡。把測試尺寸調大讓紅燈消失，是把免費的檢查關掉。

## 判準：同型失敗的數量決定產出的形態

這次事件最值得記的是處置的形態。22 個同型失敗沒有變成 22 張修復票，而是先拆出一張分析票、產出一份 396 行的規範文件（`ui-layout-overflow-prevention.md`）：六大 overflow 反模式、修法決策樹、Widget 測試檢查清單、既有元件與間距常數的對照表——然後修復票**依規範**執行。

判準跟 [#42 兩次門檻](/report/two-occurrence-threshold/)同源、但這裡數量直接跳過了門檻爭論：同型失敗兩位數，說明這是**團隊寫版面的系統性慣性**、不是某一行的手滑。單點修復對慣性無效——修完這 22 個、下一批新 widget 還會照舊寫。規範化的產出讓三件事變可能：修復者有決策樹可依（不用每處重新發明修法）、新程式碼有檢查清單可對、review 有反模式清單可引。成本結構跟[測試分診](/work-log/flutter_test_failure_triage_root_cause_roi/)的 ROI 排序一致：一次規範的固定成本、攤提給之後每一個版面。

## 附帶教訓：stale ticket 先考古、再執行

這張票還留了一筆流程教訓。W1-011 停滯 58 天後被接手，執行前的考古驗證發現多處漂移：記錄裡的程式碼路徑寫反（`search/widgets` 實際是 `widgets/search`）、失敗測試數寫 22 實際 23、5W1H 欄位不完整。**陳舊 ticket 的內文是它建立當下的快照**，兩個月的 codebase 演化足以讓路徑、數量、甚至問題本身漂移——照著舊內文直接動手，會修錯位置或漏修新增的失敗。接手的正確順序是先重驗每一個事實聲明（重跑測試、重 grep 路徑）、更新票面、再執行——跟[read-path 分析](/work-log/flutter_migration_read_path_gap_fake_green/)的「獨立重驗、勿盲信」是同一條紀律在時間軸上的版本。

## 判讀徵兆

- widget 測試出現 `RenderFlex overflowed`——先看 flex 容器裡哪個子元件沒有彈性策略（`Flexible` / `Expanded` / 可捲動），不是先調測試螢幕尺寸
- 溢出量大（數百 px）——版面對窄約束沒有任何策略、需要結構性修法；溢出量小（個位數）——邊距層級的微調
- 同型失敗兩位數——停止逐個修，先抽反模式與決策樹、讓修復與未來的新程式碼有同一份依據
- 接手停滯超過數週的 ticket——內文的每個事實聲明（路徑、數量、現象）先重驗再引用

## 相關閱讀

- 同族數據：[16 個失敗只有 2 個是缺口](/work-log/flutter_test_failure_triage_root_cause_roi/)——那批的溢位類（idle 81px → error 167px 隨狀態增長）與本文合成 overflow 的兩個現場
- 「單次修復 vs 制度化」的原則層：[#221 檢查規則的作用域要顯式列舉](/report/lint-scope-must-be-explicit-fact/)引用的教訓同構——單張 ticket 裡的觀察不升格、下一個執行者不會讀到；本文的規範文件就是升格的形態
- 概念地基：Flutter 的約束傳遞模型——[HitTestBehavior 三種模式](/work-log/flutter_hit_test_behavior/)同屬「框架的隱式規則要顯式理解」家族
