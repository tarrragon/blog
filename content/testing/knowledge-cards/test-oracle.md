---
title: "Test Oracle（測試判準來源）"
date: 2026-08-24
description: "一個測試憑什麼判定通過或失敗說不清楚、或被測對象沒有可逐例算出的正確答案時，用來定位判準的來源，以及每一種來源的射程"
weight: 17
tags: ["testing", "test-oracle", "assertion", "verification"]
---

Test oracle 是測試判定「這次執行算通過還是算失敗」所依據的判準來源。斷言只是 oracle 的表達形式，真正的問題是那個預期值從哪裡取得——取得的路徑決定這個測試能發現什麼。規格給的 oracle 抓得出實作偏離需求；[characterization test](/testing/knowledge-cards/characterization-test/) 用現狀當 oracle，只抓得出行為改變；而 [stub](/testing/knowledge-cards/stub/) 餵進去的資料若同時也是斷言的依據，這個測試沒有 oracle 可言，它驗證的是自己寫下的假設。

## 概念位置

測試三層（unit / [protocol integration](/testing/knowledge-cards/protocol-integration-test/) / [screen state](/testing/knowledge-cards/screen-state-test/)）回答的是驗證發生在哪一層，oracle 回答的是憑什麼判定，兩者正交：同一層的兩個測試可以有完全不同的判準來源，而判準來源決定了紅燈的意義。

判準來源分兩層。第一層問**預期值從哪裡取得**，有四種取法；取不到答案時進第二層，改問**預期值必須滿足什麼**（不變量）或**輸入變了輸出該怎麼變**（變形關係）——那兩種是判準的替代形態而不是取得預期值的來源，退階的完整判準在[判準寫不下來的時候](/testing/06-agent-authored-code/oracle-beyond-examples/)。

第一層四種來源各自的覆蓋範圍：

| 來源     | 預期值從哪來           | 抓得到什麼                 | 抓不到什麼                                                                                       |
| -------- | ---------------------- | -------------------------- | ------------------------------------------------------------------------------------------------ |
| 規格     | 人寫下的需求           | 實作與需求之間的偏離       | 需求本身寫錯了（那一層走 [BDD 測行為不測實作](/record/bdd-testing-methodology/)）                |
| 參照實作 | 另一份被信任的實作     | 兩份實作的輸出不一致       | 兩份實作在同一處同時錯（同一份參照在第二層會以「對照」的形態再出現一次——那裡它是性質、不是來源） |
| 人的判斷 | 有人看著產出當場決定   | 判準寫不下來的那些問題     | 無法重複執行、不同人可能給出不同判定                                                             |
| 現狀     | 被測程式當下的實際輸出 | 行為相對於錄下那一刻改變了 | 錄下那一刻的行為本來就是錯的                                                                     |

## 可觀察訊號與例子

Oracle problem 指的是被測對象沒有可直接取得的預期輸出這個處境。典型場合是最佳化演算法（知道解合不合法、算不出最佳解該長什麼樣）、編譯器與轉譯器（輸出是另一份程式）、繪圖與版面計算（正確與否是視覺判斷），以及規格只存在於人腦裡而從未被寫下的功能。這些場合逐例斷言寫不出來，判準要換成[不變量](/testing/knowledge-cards/property-based-testing/)或[變形關係](/testing/knowledge-cards/metamorphic-testing/)。

另一種訊號來自紅燈的歧義：一個測試變紅時如果分不出「這代表行為改了」還是「這代表行為不對」，通常是同一個檔案裡混用了規格 oracle 與現狀 oracle。

## 設計責任

每個測試的作者要能指出預期值是從哪裡取得的。指不出來時最常見的實情是預期值取自實作的執行結果——先跑一次、把印出來的值貼進斷言，那是用實作驗證實作，不是驗證。這個退化在測試與實作由同一次生成產出時是預設會發生的事，判定方式見 [test provenance](/testing/knowledge-cards/test-provenance/)。

Oracle 的可信度是測試套件的上限：斷言寫得再細密，也不會超過判準來源本身的正確性。這條上限也劃出了自動化的邊界——判準無法事先寫下的驗證工作屬於[探究而非檢查](/testing/knowledge-cards/testing-vs-checking/)。
