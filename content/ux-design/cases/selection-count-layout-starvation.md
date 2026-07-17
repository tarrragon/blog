---
title: "U.C19 「已選擇」計數被版面擠壓成省略號 — 回饋死在 layout"
date: 2026-07-17
description: "狀態文字顯示成「...」、資料層查起來卻一切正常時使用。回饋鏈的最後一哩是版面 — Flexible + Spacer 的寬度競爭把關鍵計數整串壓成省略號，state 正確、使用者拿到零資訊"
weight: 19
tags: ["ux-design", "case-study", "interaction-feedback", "layout", "ellipsis", "flutter", "mobile"]
---

這個案例的核心責任是說明回饋鏈的最後一哩：狀態存在、綁定正確、文字建構無誤，回饋仍可能死在版面 — 寬度競爭之下被 ellipsis 壓縮成「...」，對使用者等於零回饋。

## 觀察

書庫管理 app 管理模式的工具列右側有「已選擇: {count}/{total}」文字（`library_display_extensions.dart:134-147`）。驗收看到的永遠是「...」— 第一假設是計數沒接上。

程式碼事實推翻這個假設：計數來源 `selectedBookIds.length / books.length` 是同步、reactive 的，勾選即時更新 — **資料層完全正常**。「...」的成因在版面：同一個 Row 裡，模式切換按鈕佔 `Flexible(flex: 2)`、中間一個 `Spacer()` 把剩餘寬度全部吃掉，「已選擇」的 `Flexible` 分到的寬度趨近於零，`TextOverflow.ellipsis` 把整串文字壓縮成「...」。

## 判讀

1. **回饋鏈的驗證要驗到像素層**。「state 有值、widget 有綁」不等於使用者看得到 — 版面是回饋鏈的最後一環，layout starvation（flex 優先權競爭把某個元件的空間擠到零）讓正確的資料以「...」呈現。診斷時「資料壞了」和「版面壓掉了」是兩條完全不同的修法，先分清楚再動手。

2. **ellipsis 對短關鍵資訊是錯誤的降級策略**。ellipsis 的適用場景是「長文字截尾仍保留頭部資訊」（書名、路徑）；「已選擇: 3/45」這種短計數被截、剩下的「...」不保留任何資訊。關鍵狀態文字的降級策略應該是縮短格式（「3/45」）、換行、或保障最小寬度 — 不是 ellipsis。

3. **Spacer 與 Flexible 同列是寬度競爭的常見形態**。Spacer（等同 Expanded）會拿走所有剩餘空間，排在後面的 Flexible 只能分到擠壓後的殘餘 — 在寬幕開發機上可能剛好夠、窄幕上歸零。這類問題只在特定寬度現形，驗收要在窄幕跑。

4. **等比縮放套件不會攔到這類問題**。專案全程使用 flutter_screenutil，它做的是設計稿座標到裝置座標的數值換算、工作在 layout 之前的常數層；空間分配發生在 layout 協商層（Row 把有限寬度分給 flex 子元件、輸入是動態內容），換算工具不參與。比例正確不等於空間夠用 —「有用響應式套件」不構成版面不會擠壓的保證，完整判讀見 [#228 等比縮放不管空間分配](/report/proportional-scaling-is-not-space-allocation/)。

## 策略

1. **關鍵狀態文字給最小寬度保障或更高的 flex 優先權**，可壓縮的是裝飾性元素、不是回饋。

2. **文字降級策略按資訊密度選**：短計數用縮格式（去掉「已選擇:」前綴、只留「3/45」）、長文字才用 ellipsis。

3. **診斷「顯示不出來」先分層**：state 有值嗎（debug 印）→ 綁定對嗎（widget 讀哪個欄位）→ 版面給了空間嗎（layout inspector 看實際寬度）。這個案例卡在第三層。

## 下一步路由

- 結果通知的完整設計 → [互動回饋三層模型](/ux-design/06-interaction-feedback/feedback-three-layers/)
- 資料正確但 UI 未反映的 sibling → [U.C9 提取成功卻誤報失敗](/ux-design/cases/async-listener-false-failure/)
- 同畫面的其他管理模式問題 → [U.C20 管理模式操作全是佔位](/ux-design/cases/management-actions-placeholder-only/)
