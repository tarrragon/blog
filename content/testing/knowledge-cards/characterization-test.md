---
title: "Characterization Test"
date: 2026-07-17
description: "斷言「行為不變」而非「行為正確」的測試形態；與正確性測試的語意分界，決定紅燈能不能歸因"
weight: 10
tags: ["testing", "characterization-test", "legacy", "refactoring"]
---

Characterization test 的斷言對象是現狀本身：預期值取自被測程式碼當下的實際輸出，而非規格說它該輸出什麼。這個語意讓它的紅燈只有一種意義——行為改了。正確性測試的紅燈則有兩種意義（行為改了、或行為本來就不對），兩者混在同一個測試檔裡，紅燈就失去歸因能力。與測試三層（unit / [protocol integration](/testing/knowledge-cards/protocol-integration-test/) / [screen state](/testing/knowledge-cards/screen-state-test/)）的關係是正交：三層各自驗證正確性，characterization test 守護現狀。

## 概念位置

當依賴纏結到必須先拆解才能寫正確性測試、而拆解本身就可能改壞行為時，characterization test 補上這段真空期的回饋——這是它唯一的存在理由。依賴纏結的典型樣貌是[mock 遮蔽](/testing/knowledge-cards/mock-masking/)描述的那種處境：程式碼直接呼叫外部服務、沒有可注入的介面。這個處境在 [legacy 專案的起步順序](/testing/01-test-strategy-layers/legacy-test-bootstrap/)的「遷移安全網」段有完整的操作判準——包含三種起步路徑各自何時需要它。

## 可觀察訊號與例子

改動範圍不可知時——沒有測試、依賴纏結、沒人記得它該回傳什麼——先鎖行為再動手；範圍可知時（規格明確、依賴已可注入）直接寫正確性測試更划算。判斷落點就在這條分岔上：它的價值來自不確定性，不確定性消失，它就失去存在理由。

## 設計責任

這類測試自帶退場條件，維護者要負責執行它：正確性測試覆蓋同一段行為後，characterization test 的使命結束、應該移除。留著不移除的代價是雙份維護，且兩份測試對同一行為的斷言可能分岔。與 [mock 遮蔽](/testing/knowledge-cards/mock-masking/)的關係值得留意——characterization test 記錄的是含既有 bug 的行為，它保證的是「沒改壞」，不保證「是對的」。
