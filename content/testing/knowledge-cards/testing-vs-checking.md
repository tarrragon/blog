---
title: "Testing vs Checking（探究與檢查）"
date: 2026-08-24
description: "斷言可以被整批產生之後，用來區分哪些驗證工作交得出去給機器、哪些需要人的判斷才成立"
weight: 19
tags: ["testing", "checking", "exploratory-testing", "rapid-software-testing"]
---

Checking 是對一個已經被決定的事實作二元評估：判斷標準事先寫下、執行過程不需要判斷、原則上可以交給機器。Testing 是對產品的探究——設計判斷標準本身、發現沒有人想到要問的問題、判斷觀察到的現象算不算問題。這組區分由 Rapid Software Testing 一派提出，用意是把「自動化測試」這個詞裡混在一起的兩件事拆開：能自動化的是 checking，而 checking 的品質取決於當初設計它的那次 testing。這個分界跟 [test oracle](/testing/knowledge-cards/test-oracle/) 是同一個問題的兩端——oracle 寫得下來的部分是 checking，寫不下來的部分留在 testing。

## 概念位置

站內的測試三層（unit / [protocol integration](/testing/knowledge-cards/protocol-integration-test/) / [screen state](/testing/knowledge-cards/screen-state-test/)）全部落在 checking 這一側：它們都是事先寫好判斷標準、之後重複執行。Testing 在這個結構裡是產生前三層的那個活動，而不是它們之外的第四層——決定哪些協議差異值得驗、哪些畫面狀態需要覆蓋、[mock 的邊界](/testing/05-test-design-judgment/mock-boundary-decision/)畫在哪，都是判斷標準設計而非判斷標準執行。

這個分界在斷言的生產成本趨近於零時才變得可操作。過去 checking 的數量受限於有人願意寫多少，於是「寫了多少測試」跟「想清楚多少事」大致同步成長；斷言可以被整批產生之後兩者脫鉤，套件規模不再是思考量的代理指標。

## 可觀察訊號與例子

判別一項驗證工作屬於哪一側，問它的判斷標準在執行之前存不存在。「登入失敗三次後帳號鎖定」的判斷標準事先寫得下來，是 checking。「這個錯誤訊息會不會讓使用者以為是自己打錯」需要在看到畫面的當下判斷，是 testing。同一個功能通常兩側都有：鎖定次數是 checking，鎖定之後的求助路徑通不通則要有人走一次。

一個常見的錯位是把 testing 的產出誤當成 checking 的產出來衡量。套件從 200 個斷言長到 2000 個，如果新增的都是同一批判斷標準的變體，探究的覆蓋面沒有變化——[mutation testing](/testing/knowledge-cards/mutation-testing/) 生出來的測試就屬於這一類，它補的是運算子層的漏洞，不會提出新的問題。

## 設計責任

Checking 交給機器之後，人的時間要移到 checking 產生不了的地方：判斷標準本身的設計、[出處獨立](/testing/knowledge-cards/test-provenance/)的驗收條件、以及那些沒有被任何斷言涵蓋的問題。把省下來的時間拿去讀機器寫的斷言，等於把人放回機器已經做得比較好的那一側。

這個分界也給了自動化程度一個誠實的說法。宣稱「測試全自動化」時實際成立的是「checking 全自動化」，而 checking 的完整性由當初那次 testing 決定——沒有人問過的問題不會因為套件變大而被回答。
