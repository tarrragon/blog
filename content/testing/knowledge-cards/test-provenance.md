---
title: "Test Provenance（測試出處）"
date: 2026-08-24
description: "測試與被測實作由同一來源產出時（同一次生成、同一輪對話、同一個人同時寫），用來判斷這組測試還剩下多少驗證力"
weight: 18
tags: ["testing", "test-provenance", "ai-generated-code", "test-oracle"]
---

測試出處指的是測試與被測實作各自由誰、在什麼順序下產出。它是一項特定驗證力的**代理指標**——抓出需求被誤讀的能力，真正取決於[判斷標準是不是由實作推導](/testing/06-agent-authored-code/test-provenance-independence/)出來的，而出處是這件事最好查的線索：同一次產出的兩者幾乎一定共用同一份對需求的理解，於是斷言編碼的是實作以為自己該做什麼，[oracle](/testing/knowledge-cards/test-oracle/) 退化成實作自身的回音。

代理會在兩個位置失準，記住它們就知道什麼時候不能只看出處：同源產出而判斷標準是一條從需求來的不變量時，驗證力仍在；獨立產出而寫測試那一方被餵了 API schema 時，判斷標準仍有一部分是推導來的。這跟 [stub](/testing/knowledge-cards/stub/) 那張卡描述的失效是同一個機制在不同層級的形態——stub 是餵資料的人同時寫斷言，出處問題是寫實作的人同時寫斷言。

## 概念位置

出處是 [oracle 來源](/testing/knowledge-cards/test-oracle/)之外的第二個維度。同一個 oracle 類型可以有不同的出處：規格 oracle 由人寫規格、機器寫實作時獨立，由機器同時產出規格與實作時不獨立。測試三層（unit / [protocol integration](/testing/knowledge-cards/protocol-integration-test/) / [screen state](/testing/knowledge-cards/screen-state-test/)）對這個維度不作區分——分層決定驗證發生在哪，出處決定驗證是不是在照鏡子。

判斷標準被污染的程度是連續的，不是有無：判斷標準完全從實作推導時抓不到任何需求誤讀，判斷標準有一部分從實作推導（例如生成器的參數、性質的前置條件抄自實作的守衛條件）時抓得到一部分。形態的分類、各自的射程、以及可動的四個變數在[判斷標準的推導來源](/testing/06-agent-authored-code/test-provenance-independence/)那一章，卡片這裡不重複一套鍵不同的分類。

## 可觀察訊號與例子

最直接的訊號是順序：測試在實作之後由同一個來源補上時，它多半是照著實作的分支寫出來的，覆蓋率數字會很高而斷言貼著實作結構。另一個訊號是斷言的寫法——斷言重述實作的計算式（實作寫 `a * 0.8`、斷言也算 `a * 0.8`）：預期值是從實作推導來的，需求文件裡的那個數字從頭到尾沒被引用。

規格層的錯誤是這類測試的系統性盲區。危險處理順序寫反、狀態機少一個轉換、幣別換算方向顛倒——這些在實作與測試共用同一個誤解時全部通過，因為兩邊錯得一致。[mutation testing](/testing/knowledge-cards/mutation-testing/) 也發現不了它們，理由與突變的產生方式有關、在那張卡上。

## 設計責任

出處是可以被設計的，不是給定的：需求的來源、產出的順序、產出的主體、以及兩者之間的時間間隔，四者各自可動。四個變數的取捨、成本與操作方式在[判斷標準的推導來源](/testing/06-agent-authored-code/test-provenance-independence/)那一章展開。

卡片層要記住的判斷標準只有一條：四者都動不了時，這組測試的定位要降級成回歸網，並且在別處補上獨立的判斷標準。
