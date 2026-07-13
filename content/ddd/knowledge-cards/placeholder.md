---
title: "Placeholder"
tags: ["佔位", "placeholder"]
date: 2026-07-13
description: "「開發中」頁、空 callback、拋出例外的注入項該怎麼管理時使用。佔位是先立介面後補實作的合法中間態——它的失效讓測試綠燈、比文件層約束更靜默。"
weight: 13
---

佔位（placeholder）是「先立介面、實作後補」的合法開發中間態：指向「開發中」頁的路由、空的事件 callback、拋出「requires override」的 [注入項](/ddd/knowledge-cards/dependency-injection/)、回傳 hardcoded 假資料的 stub。節奏本身沒有問題、問題在佔位的失效形態：漏網的佔位通過所有以 mock 為基礎的驗收、終點站是使用者的回報。與它相鄰的組裝概念見 [composition root](/ddd/knowledge-cards/composition-root/)。

## 概念位置

失效的靜默程度比文件層約束（層次判準見 [invariant](/ddd/knowledge-cards/invariant/)）再深一級：文件層失效至少留下「規則寫在那裡、沒人遵守」的對照證據；佔位讓測試綠燈——型別層看它是合法構件、行為測試的 override 讓它永遠沒被觸發（override 的機制見 [test seam](/ddd/knowledge-cards/test-seam/)）。

## 可觀察訊號

佔位頁的型別名、「requires override」的拋出語句、空函式體都是靜態可掃描的形態。回傳假值的佔位在掃描與 [接線測試](/ddd/knowledge-cards/wiring-test/) 眼中都是正常構件——注入項解析得了、導航也會發生。

## 設計責任

佔位需要一個獨立的攔截點：靜態可掃描的形態進發版前置檢查、掃到即警告、由人判斷是刻意中間態還是漏網；回傳假值的那一類靠行為斷言或實機冒煙走查。攔截點怎麼落進發版流程、[組裝層的可達性](/ddd/composition-root-reachability/) 有完整處置。
