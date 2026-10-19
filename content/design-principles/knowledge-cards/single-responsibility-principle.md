---
title: "Single Responsibility Principle（單一職責原則）"
date: 2026-10-19
description: "要判斷一個模組、類別或文件該不該拆，或讀到「一個類別只做一件事」這種說法時：單一職責的定義是改變的理由，而理由對到提出變更的人"
weight: 1
tags: ["design-principles", "knowledge-card", "srp", "solid"]
---

單一職責原則（Single Responsibility Principle，SRP）的定義是：一個模組應該只有一個改變的理由。Robert C. Martin 把「理由」對到提出變更的人——一個模組的變更應該只來自一群緊密合作、代表單一業務職能的人，這樣一群人算一個理由。違反這條原則的模組，在修改紀錄上呈現成 [Divergent Change（發散式變更）](/design-principles/knowledge-cards/divergent-change/)：同一個模組因為不同的理由、以不同的方式反覆被修改；把同一個理由的程式碼拆散到好幾個模組，則是與 Divergent Change 成對的 [Shotgun Surgery（散彈式修改）](/design-principles/knowledge-cards/shotgun-surgery/)。

## 概念位置

SRP 是 SOLID 五原則的第一條。Martin 在《Agile Software Development: Principles, Patterns, and Practices》（2002）把它寫成「一個類別應該只有一個改變的理由」；2014 年他在〈The Single Responsibility Principle〉一文說明「理由」指的是人，並把原則改寫成兩句方向相反的指示：

> Gather together the things that change for the same reasons. Separate those things that change for different reasons.

前一句要求把因同一個理由改變的程式碼放在一起，後一句要求把因不同理由改變的程式碼分開。切分的人只執行後一句，會把同一個理由的程式碼拆散到很多檔案，於是那群人每次提出變更，修改的人都要同時改好幾處，這就是 [Shotgun Surgery](/design-principles/knowledge-cards/shotgun-surgery/)；只執行前一句的極端是把所有程式碼都放在一起，於是不同理由的變更擠在同一個模組，這就是 [Divergent Change](/design-principles/knowledge-cards/divergent-change/)。SRP 要求兩句同時滿足：因同一個理由改變的程式碼在同一個模組，因不同理由改變的程式碼在不同模組。在《Clean Architecture》（2017）裡，Martin 把定義收斂成「A module should be responsible to one, and only one, actor」，actor 指的是要求同一類變更的一群人。

**理由的計數單位是改動的種類，提出的人用來辨認種類。** 一個 actor 要求的是同一類改動，所以理由可以從兩邊辨認：從提出變更的人，或從他們要求的改動種類。兩邊對得上時（財務部門要求的都是薪資規則的改動）看哪一邊結果都一樣；對不上時以改動種類為準——同一個人轉達好幾個職能的需求時，他提出的改動屬於不同理由；不同的人提出同一類改動時，仍是同一個理由。

Martin 在 2014 年那篇文章裡說明這條原則的源頭是 David Parnas 1972 年的論文〈On the Criteria To Be Used in Decomposing Systems into Modules〉與 Edsger Dijkstra 提出的 separation of concerns：模組的切法要依「什麼會一起變」決定，不依程式執行的步驟決定。他在《Agile Software Development》的單一職責那一章也寫明，這條原則就是 Tom DeMarco 與 Meilir Page-Jones 所說的 [Cohesion（內聚）](/design-principles/knowledge-cards/cohesion/)，只是把判斷依據從功能上的相關換成讓模組改變的力量。

**「只做一件事」是另一條原則。** SRP 最常見的誤讀是「一個類別只做一件事」。Martin 在《Clean Architecture》第七章說確實有一條原則是這樣講的，那條原則的對象是函式：一個函式只做一件事，用在把大函式拆小的重構裡。那一條管的是函式內部的步驟，判斷依據是程式碼在做什麼；SRP 管的是模組的邊界，判斷依據是誰會要求它改變。兩條原則的單位與依據都不同，所以一個只做一件事的類別仍然可能有兩個改變的理由，一個做了好幾件事的類別也可能只有一個。

## 可觀察訊號與例子

Martin 的例子是一個 `Employee` 類別，裡面有三個方法：`calculatePay` 依財務部門的規則計算薪資，`reportHours` 依營運部門的需要產生工時報表，`save` 依技術團隊選定的方式寫進資料庫。三個方法服務三群人——財務長、營運長、技術長各自管轄的部門——所以這個類別有三個改變的理由。三個方法放在同一個類別，損害出現在它們共用程式碼的時候：Martin 在《Clean Architecture》裡舉的是 `calculatePay` 與 `reportHours` 共用一個計算正常工時的 `regularHours` 方法：財務部門要求調整加班時數的算法，負責這次修改的工程師改了那段共用計算，營運部門的工時報表跟著變，而營運部門沒有提出任何變更。

判斷一個模組有幾個理由，要看它的變更要求的是哪幾種改動、各由哪一個職能決定，不看它有幾個方法：

- **修改紀錄裡有好幾個不相干的需求改同一個檔案**（不相干指要求的改動屬於不同種類）：這是改變理由不只一個的間接量測。不同理由的修改由不同的人同時進行時，它們會在這個檔案上合併衝突，Martin 把合併列為違反單一職責的另一個症狀。用 git 歷史統計每個檔案被幾個不相干的需求修改，再逐個 commit 歸類，做法在[從修改競爭判斷拆檔](/design-principles/module-boundary-from-change-history/)。
- **一個需求的修改改壞了另一個需求在乎的行為**：上面 `Employee` 的情形。兩個需求互不相干，卻因為住在同一個模組而互相影響。
- **bug 修正與重構不另算一個理由**。Martin 的說法是 bug 修正與重構是程式設計師的責任，不是程式的；歸類時，一個 bug 修正併進它所修的那段程式碼原本屬於的那一類。
- **所有需求都由同一個人提出時**（例如所有票都由同一位 PM 開），看提出的人分不出理由，要看每個需求要求的是哪一種改動。以一個擋下跨工作目錄 commit 的守衛腳本為例：解析 git 命令語法的改動跟著 git 的寫法變，判斷其他代理人是否正在工作的改動跟著團隊的並行流程變，擋下時印給使用者的訊息措辭跟著使用者回饋變，這三種改動各是一個理由。

依改動種類計數理由的判斷也適用於文件：一份文件被好幾個不相干的主題修改，就有好幾個改變它的理由，做法在[依職責拆分文字文件](/record/document-split-by-responsibility/)。

## 設計責任

套用 SRP 的設計責任是讓每一群提出變更的人，各自只需要改一個地方，而且改的時候不會動到別人在乎的行為。執行的判斷問句是：列出一段時間內改過這個模組的需求（範圍要涵蓋幾輪需求，選法見[從修改競爭判斷拆檔](/design-principles/module-boundary-from-change-history/)），逐一寫出要求的是哪一種改動、由哪一個職能決定；改動種類有兩種以上，就有兩個以上的理由，可以考慮依理由切開。

依技術層次切（驗證器、資料存取、寄信服務各一個類別）常常與依理由切重合，因為驗證規則、資料庫結構與信件內容通常由不同的人決定；兩種切法分岔時，以每個類別會被哪一個職能要求改變為準。切開之後反過來檢查：同一個理由的變更是否需要同時改好幾個新模組，是的話就切過頭了，要把那幾個新模組併回來。

SRP 與 [開放封閉原則](/design-principles/knowledge-cards/open-closed-principle/)常一起使用：SRP 決定模組的邊界畫在哪裡，開放封閉原則決定模組裡哪些部分對外公開、讓其他模組不必修改它就能擴充，哪些留在內部。開放封閉原則在 Python 的寫法與例子在[開放封閉原則](/python/00-philosophy/open-closed-principle/)。
