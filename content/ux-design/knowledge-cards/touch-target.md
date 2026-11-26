---
title: "Touch Target（觸控目標）"
date: 2026-07-16
description: "實機測試點列表行文字沒有反應、可用性測試中觀察到使用者重複點擊同一行，或替下緣畫了立體厚度的按鈕量可點範圍時使用。觸控目標要求尺寸不小於平台底線，範圍也要涵蓋視覺暗示的可點區域；範圍這一層在列表行展開/收合上容易被漏掉，立體按鈕的厚度則同時影響範圍與尺寸底線的判斷。"
weight: 6
tags: ["ux-design", "knowledge-card", "interaction-feedback", "touch-target", "mobile"]
---

Touch Target 的核心概念是「可點擊區域必須涵蓋視覺上暗示可點的範圍」。視覺設計透過整行反白、箭頭圖示、卡片邊框暗示「這裡可以點」；若實際的 gesture 區域小於視覺暗示的範圍，使用者點了沒反應，體感跟按鈕壞掉相同。它處理的是回饋發生之前的問題 — 點擊沒有落在 gesture 區域內，[三層回饋](/ux-design/06-interaction-feedback/feedback-three-layers/)連第一層都不會啟動。與 [Doherty Threshold](/ux-design/knowledge-cards/doherty-threshold/)（回饋時間門檻）互補：Doherty 管「點擊後多久要有反應」，Touch Target 管「點擊有沒有落在可反應的區域」。

## 跟其他概念的關係

Touch Target 處理的是回饋鏈的第零層——點擊有沒有落在可反應的區域。[三層回饋](/ux-design/06-interaction-feedback/feedback-three-layers/)（點擊確認 / 等待指示 / 結果通知）假設點擊已經落在 gesture 區域內；Touch Target 確保這個前提成立。與 [Doherty Threshold](/ux-design/knowledge-cards/doherty-threshold/) 的關係是空間 vs 時間：Doherty 管回饋的時間門檻、Touch Target 管回饋的空間門檻。與 [Screen State Matrix](/ux-design/knowledge-cards/screen-state-matrix/) 無直接關聯——狀態矩陣管畫面層級的轉換、Touch Target 管元件層級的互動。與 [Affordance（操作暗示）](/ux-design/knowledge-cards/affordance/) 的分工是外觀與範圍：Affordance 管外觀暗示了什麼操作，Touch Target 管暗示可點的範圍是否都在 gesture 區域內。

## 尺寸底線與範圍對齊

兩個層次的要求，缺一都會產生「點了沒反應」：

- **尺寸底線**：Material Design 規定最小觸控目標 48x48dp、iOS HIG 規定 44x44pt。小於底線的目標（如單獨一顆 24dp 圖示）即使精準點擊也容易失手。
- **範圍對齊**：觸控區域要等於視覺暗示的可點範圍。列表行的展開/收合是典型場景 — 整行是一個視覺單元，使用者直覺點行的任何位置；若 gesture 只掛在尾端箭頭 `IconButton` 上，點標籤名稱、點空白處都無反應。

一個書庫管理 App 的標籤管理頁實證了範圍錯位（案例見 [標籤行只有箭頭可點 — 觸控目標小於視覺單元](/ux-design/cases/tag-row-touch-target-scope/)）：二級標籤的展開/收合只有尾端箭頭可點，實機測試使用者直覺點整行、無反應。修復是在包裹整行的 `InkWell` 加上 `onTap`（與箭頭觸發同一個 callback）；內層 `IconButton` 是獨立 gesture 區域，點箭頭時由它自己處理，不會被外層重複觸發 — 整行成為觸控目標，箭頭行為不變。

**按鈕的下緣畫了立體厚度時，厚度不一定在 gesture 區域裡。** 有些按鈕的下緣畫有一條深色的厚度，讓按鈕看起來像按得下去的立體按鈕。厚度在視覺上跟按鈕面是同一個單元，是一種操作暗示（Affordance），使用者會把它當成按鈕的一部分；照範圍對齊，點在厚度上也該有反應。厚度怎麼畫決定它在不在 gesture 區域裡：用陰影畫的厚度（CSS 的 `box-shadow: 0 5px 0`、Flutter 的 `BoxShadow`）不佔版面，用滑鼠點、或在 Flutter App 裡點，至少厚度下緣那一段沒有反應（手機瀏覽器可能把靠近按鈕的觸碰校正到按鈕上，見〈可觀察訊號與例子〉）；用下框線或 padding 畫在按鈕本身裡的厚度，點得到。按下效果把整顆按鈕往下移時（CSS 在 `:active` 時改 `transform` 或 `margin`），按在頂緣的滑鼠點擊會掉：按下之後按鈕移開了，放開的位置已經不在按鈕上；位移只放在內層的按鈕面時不會掉。

Flutter 的 Material 按鈕在行動平台上，會在不到 48dp 的那一軸補上透明的點擊區，厚度畫在外層元件上時，這圈點擊區夾在按鈕面與厚度之間，兩者因此分開。行動平台上 `materialTapTargetSize` 預設是 `padded`，在預設的視覺密度（`VisualDensity`）下，按鈕面不到 48dp 的那一軸會補上透明的點擊區，把 gesture 區域補到 48dp；厚度用下框線畫在把框線算進版面的外層元件上時（例如 `Container` 依框線寬度內縮子元件），這圈透明區落在按鈕面與厚度之間，看起來像兩個元件，點在厚度上仍然沒有反應；外層用 `BoxShadow` 畫厚度時沒有空隙，透明區蓋住厚度的上段，上段點得到、下段點不到。修法同下一段：讓 gesture 區域涵蓋厚度。

量尺寸底線時量的是 gesture 區域，不是加上厚度的視覺高度。一顆按鈕面 44dp、下緣再畫 5dp 陰影厚度、沒有補點擊區（例如用 `GestureDetector` 自製的按鈕、Flutter 在桌面平台上、`materialTapTargetSize` 設成 `shrinkWrap`；CSS 寫的按鈕同理，網頁的底線照專案採用的那一條，WCAG 2.2 的 SC 2.5.8 是 24×24 CSS px、SC 2.5.5 是 44×44）的按鈕，看起來有 49dp 高，gesture 區域只有 44dp，不到 Material 的 48dp 底線。厚度用下框線或 padding 畫在按鈕本身裡時，gesture 區域涵蓋厚度，範圍對齊了，尺寸也變成按鈕面加厚度：44dp 加 5dp 是 49dp，過了底線；40dp 加 5dp 是 45dp，仍然不到。

## 可觀察訊號與例子

範圍錯位的訊號是「使用者點了視覺單元的非 icon 區域而無反應」：實機測試點列表行文字無反應、可用性測試觀察到使用者重複點擊同一行、觸控熱點分析顯示大量落在 gesture 區域外的點擊。程式碼層的訊號是 gesture 只掛在視覺單元的子元件（trailing icon、小圖示）而非整個單元容器。下緣畫了立體厚度的按鈕，訊號是用滑鼠點在厚度上沒有反應，以及 Flutter 的 Material 按鈕在行動平台上按鈕面與厚度之間出現一段空隙（厚度用陰影畫在外層時沒有空隙，要點在厚度最下緣驗）；有按下效果的按鈕，另外在頂緣按下再放開一次；成因寫在〈尺寸底線與範圍對齊〉末尾的立體按鈕那幾段。在手機瀏覽器上用手指驗不準：瀏覽器的觸碰校正（touch adjustment）可能把靠近按鈕的觸碰校正到按鈕上，生效與否依瀏覽器、觸碰的接觸面大小與附近有沒有別的可點目標而定。用滑鼠點量到的是 gesture 區域本身：滑鼠點擊只有一個點，不經過觸碰校正。開發者工具標出的元素盒子只是起點，偽元素擴大的點擊區、`clip-path` 裁掉的區域與超出盒子的子元素，都會讓 gesture 區域跟盒子不同。

## 判斷條件與後果

觸控區域比視覺暗示的範圍小、或小於平台底線時，使用者點在看起來可以點的位置而沒有反應，體感跟按鈕壞掉相同。列表行的主要操作（展開、進入詳情）的 gesture 只綁在尾端圖示上時，點標籤名稱或空白處都沒有反應；整行作為觸控目標時，行內的次要操作（刪除、更多選單）保留成獨立的內層 gesture 區域，點它時由內層自己處理，外層不會重複觸發。按鈕的下緣畫有立體厚度、而厚度不在 gesture 區域裡時，視覺尺寸比 gesture 區域大，用滑鼠的使用者與 Flutter App 的使用者點在厚度上沒有反應；兩顆按鈕上下相鄰、間距小於厚度時，鄰鍵補出來的透明區可能疊到這段厚度上，點下去觸發的是鄰鍵；這時審查的人用整顆按鈕的視覺高度判斷是否達到尺寸底線，視覺高度達到底線而按鈕面不到時，會把只有按鈕面那麼大的 gesture 區域判成合格。設計審查時對每個可互動視覺單元問一句：使用者最直覺點的位置，在 gesture 區域內嗎？按下的過程中仍在嗎？
