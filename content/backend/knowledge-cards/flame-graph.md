---
title: "Flame Graph（火焰圖）"
date: 2026-07-20
description: "把 CPU 或記憶體 profile 的呼叫堆疊視覺化、用寬度找出哪段程式碼佔用資源最多"
weight: 412
---

Flame graph 是 profiling 結果的標準視覺化形式——每一層代表呼叫堆疊的一層函式，寬度代表該函式（含其子呼叫）佔用的取樣比例。它是 [Continuous Profiling](/backend/knowledge-cards/continuous-profiling/) 持續取樣機制最終被人眼讀懂的呈現形式，寬度而非高度是判讀重點：一段程式碼佔的寬度越大，代表它在取樣期間消耗的 CPU 或記憶體比例越高，跟它在堆疊中的深淺無關。

## 概念位置

Flame graph 是單次 profile 的呈現方式，[Profile Diff](/backend/knowledge-cards/profile-diff/) 是把兩次 flame graph 疊起來比較，找出 release 前後或 baseline 與 candidate 之間的相對變化。它是持續取樣機制的呈現終端——沒有持續取樣，flame graph 只能反映單次手動抓取的一瞬間，看不出趨勢或退化。

## 可觀察訊號與例子

Pyroscope、Datadog Continuous Profiler、Parca 這類 continuous profiling 工具都以 flame graph 為主要呈現介面，差異在於是否自動跟 deployment marker 或 trace span 關聯。Differential flame graph（比較兩個時間段的堆疊差異）是退化定位的常見手法——Brendan Gregg 的開源實作需要手動產生，商業工具通常直接整合進 deployment 事件，選版本前後兩個時間窗就能看到差異。

## 判讀方式

看 flame graph 找退化原因時，先鎖定寬度變化最大的那幾層函式，而不是從頂層一路往下逐層檢查——寬度變化直接對應資源消耗的相對變化，是最快的線索。單張 flame graph 只能告訴系統目前哪裡忙，要回答這次 release 是不是變慢了，需要跟 baseline 做 [Profile Diff](/backend/knowledge-cards/profile-diff/)，只看絕對數字容易誤判。
