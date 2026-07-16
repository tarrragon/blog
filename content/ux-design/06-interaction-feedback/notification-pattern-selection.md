---
title: "通知模式選擇：SnackBar、Dialog、Banner 與 Bottom Sheet"
date: 2026-07-16
description: "操作結果該用 SnackBar 閃一下還是彈 Dialog 問使用者 — 干擾程度與是否需要使用者操作的二軸判準，選錯形式的症狀是通知被忽略或流程被打斷"
weight: 4
slug: "notification-pattern-selection"
tags: ["ux-design", "interaction-feedback", "notification", "dialog", "snackbar", "banner", "bottom-sheet"]
---

## 核心觀念

**通知的形式是一個設計決策，判準是干擾程度與使用者是否需要操作。** 判準選錯，輕則通知被忽略（太低調），重則流程被打斷（太侵入）。[三層回饋模型](../feedback-three-layers/)把使用者操作後的回饋拆成點擊確認、等待指示、結果通知三層，本篇聚焦第三層（結果通知）的**形式選擇** — 前篇回答「該通知什麼」，本篇回答「用什麼形式通知」。

六種通知形式從低干擾到高干擾排成一道光譜：inline 狀態更新、SnackBar、Banner、Bottom Sheet、Dialog、全螢幕。每種形式對使用者的注意力佔用不同，選擇依據是兩個軸的交叉判讀。讀完本篇，你可以對每個操作結果選出干擾程度剛好的通知形式，避免「所有通知都用 Dialog」或「重要通知用 SnackBar 閃一下就消失」這兩類鏡像錯誤。

## 二軸判準

### 軸一：是否需要使用者操作

通知分「純告知」和「需要回應」兩類。

**純告知**：使用者只需要知道結果，不需要做任何事。「已複製到剪貼簿」「設定已儲存」「訊息已送出」。這類通知可以自動消失 — 使用者瞄一眼就夠了，停留太久反而擋視線。

**需要回應**：使用者必須做出選擇或確認才能繼續。「確定要刪除嗎？」「匯出完成，檔案在這裡」「批次操作有 3 筆失敗」。這類通知必須持續顯示直到使用者處理，自動消失等於系統擅自幫使用者做了「忽略」這個決定。

邊界情境：帶「復原」選項的刪除通知。使用者不操作也行（刪除生效），操作了也行（復原）。這屬於「可選操作」— SnackBar 加一顆 action button 是標準解法，給使用者反悔窗口但不強制回應。

### 軸二：干擾程度

干擾程度由兩個因素決定：通知是否遮擋當前內容（視覺佔用），以及使用者能否繼續操作其他功能（互動阻斷）。

| 等級 | 視覺佔用       | 互動阻斷 | 代表形式              |
| ---- | -------------- | -------- | --------------------- |
| 零   | 不額外佔用空間 | 否       | Inline 狀態更新       |
| 低   | 小面積 overlay | 否       | SnackBar              |
| 中   | 局部固定區域   | 否       | Banner                |
| 中高 | 螢幕下半       | 部分     | Bottom Sheet（modal） |
| 高   | 居中 overlay   | 是       | Dialog                |
| 最高 | 整個螢幕       | 是       | 全螢幕 / 新畫面       |

干擾程度的選擇原則是「剛好夠用」— 確認已複製到剪貼簿不需要 Dialog，刪除確認不能用 SnackBar。

## 通知形式光譜

### Inline 狀態更新

UI 元素在原位更新，不彈出額外元件。使用者按了按鈕，按鈕本身或旁邊的區域就反映結果。

收藏按鈕填滿、列表項目滑動移除、表單欄位驗證紅字、數量即時更新 — 結果就在使用者視線所在位置，不需要另開通知通道。[三層回饋模型](../feedback-three-layers/)第一層（點擊確認）和第三層（結果通知）在同一個 UI 元素上完成時，inline 是唯一合理的形式。

適用條件：操作結果在觸發元素的 UI context 內就能完整呈現。不適合需要額外資訊（檔案路徑、失敗原因）或離操作位置較遠的結果。

### SnackBar

螢幕底部的短暫訊息條，可選配一顆 action button。出現後自動消失，使用者也可以手動滑掉。同一時間只顯示一個 — 新的 SnackBar 會取代舊的。

Material Design 的 SnackBar 是 Android 平台 Toast 的設計升級 — Toast 只能顯示文字且不可互動，SnackBar 加入了 action button（最多一個）和 swipe-to-dismiss。iOS 沒有官方對等元件，多數跨平台 app 統一使用 SnackBar 行為。

**適用條件**：

- 操作已完成，使用者不需要做進一步決定。「已儲存」「已複製」「已加入購物車」
- 提供可選但不強制的操作。「已刪除」＋「復原」button — 不點也沒關係，刪除照常生效
- 結果資訊量低，一句話能講完的確認訊息

**不適合**：需要使用者確認才能繼續的決策（用 Dialog）、資訊量大到一句話裝不下的結果（用 Dialog 或 Bottom Sheet）、持續性狀態變更通知（用 Banner）。

### Banner

SnackBar 消失後使用者就忘記自己在離線中，30 秒後送出表單才撞上網路錯誤 — 這類持續性狀態需要一種不會自動消失的通知。Banner 固定在內容區頂部（app bar 下方），保持顯示直到使用者主動 dismiss 或觸發條件消失，可以有一到兩顆 action button。

Banner 和 SnackBar 的關鍵差異是**生命週期**：SnackBar 是事件驅動（「這件事剛發生」），Banner 是狀態驅動（「這個條件持續存在」）。「已恢復連線」是事件、用 SnackBar；「目前離線，部分功能不可用」是持續狀態、用 Banner。[Degraded mode](/ux-design/04-error-recovery/degraded-mode-design/)（系統部分功能因外部依賴不可用而暫時無法運作）的進入退出是這個差異的典型場景 — 進入降級是持續狀態，用 Banner 比 SnackBar 合適，因為 SnackBar 消失後使用者會忘記自己在降級中；退出降級是一次性事件，用 SnackBar。

典型使用場景：持續性狀態需要使用者知曉（「離線模式」「版本過舊，部分功能受限」）、非緊急但需要使用者在某個時間點處理（「有新版本可更新」＋「立即更新」「稍後」）、影響整個畫面的使用者操作（「篩選已啟用，顯示的是部分結果」）。一次性事件通知（用 SnackBar）和需要立即決策的重要操作（用 Dialog）不適合 Banner。

### Bottom Sheet

Dialog 佔用焦點但面積有限，需要更大空間展開選項又不想離開當前畫面時，Bottom Sheet 從螢幕底部滑出、覆蓋部分內容。Modal bottom sheet 有半透明遮罩，使用者必須選擇或 dismiss 才能繼續操作下方內容；non-modal bottom sheet 與下方內容並存，使用者可以在不 dismiss 的情況下切換注意力。

分享選單、篩選面板、地圖上的地點詳情、設定快捷面板 — 共通點是操作與當前畫面高度相關，全螢幕導航會破壞 context。列表某一項的詳細資訊、日期選擇器這類需要一定面積但不值得開新畫面的互動也適合用 Bottom Sheet。

iOS 的 Action Sheet 是 Bottom Sheet 的特化形式，專門呈現「針對當前操作的選項列表」（分享、更多操作）。iOS 13+ 的 sheet presentation 把 Bottom Sheet 擴展為通用 UI 容器（可拖曳到不同高度、可滑動 dismiss）。兩個平台的共識是：Bottom Sheet 用在「延伸當前操作」，Dialog 用在「要求使用者做決定」。簡單的操作確認（用 SnackBar 或 Dialog 足夠）和重要決策確認（Dialog 的阻斷性是設計需求，Bottom Sheet 太容易被意外滑掉 dismiss）不適合 Bottom Sheet。

### Dialog

有些操作的後果大到使用者必須被強制暫停 — 刪除不可逆、匯出結果包含使用者必須知道的檔案路徑、付款金額需要最後確認。Dialog 是居中的 modal overlay，半透明遮罩阻斷背景互動，使用者必須回應（選擇按鈕或 dismiss）才能繼續。它同時佔用視覺焦點和阻斷所有其他操作，是最強的注意力攫取手段之一。

三種常見型態：

**Alert Dialog**：告知重要結果或狀態，使用者確認後繼續。例如匯出完成後顯示檔案路徑的 Alert Dialog — 使用者需要看到路徑才能找到匯出結果（完整案例見 [匯出按鈕零回饋](/ux-design/cases/export-button-zero-feedback/)）。

**Confirmation Dialog**：使用者做出會產生後果的決定前確認。「確定刪除這 3 個項目？此操作無法復原」＋「刪除」「取消」。操作不可逆或代價高時，Dialog 的阻斷性是設計需求 — 讓使用者在執行前有一個強制暫停點。

**Selection Dialog**：從多個選項中做一次性選擇。從列表中選一個類別、從月曆中選日期。Material Design 建議選項超過兩三個時考慮用 Bottom Sheet 或全螢幕，因為 Dialog 的面積有限。

Dialog 的保護效果取決於使用頻率。操作不可逆或代價高、操作結果包含關鍵資訊、必須在當前流程中做二選一決定 — 這三類情境是 Dialog 的正確使用場景。但輕量確認（「已儲存」）用 Dialog 是殺雞用牛刀、SnackBar 足夠。頻繁操作每次都彈 Dialog 等於每次都打斷流程，使用者訓練出的反應是「不讀直接按確定」，真正重要的確認也會被跳過。大量內容或複雜互動會超出 Dialog 的有限面積，改用 Bottom Sheet 或全螢幕。

**Dialog vs Bottom Sheet 的決策邊界**：延伸當前操作的選項（分享、篩選、更多操作）用 Bottom Sheet，要求使用者做二選一決定（刪除確認、付款確認）用 Dialog。兩者重疊的地帶是 Selection Dialog — 選項少（二到三個）時 Dialog 的居中面積夠用，選項多時 Material Design 建議升級到 Bottom Sheet 或全螢幕。區分它們的是行為屬性：Dialog 是 [modal](/ux-design/knowledge-cards/modal/)（阻斷背景互動、強制回應），Bottom Sheet 可以是 modal 也可以是 non-modal，且 Bottom Sheet 太容易被滑掉 dismiss，承載重要決策時使用者可能意外關閉。

### 全螢幕

整個畫面被替換為通知或結果內容。在 Material Design 中稱為 full-screen dialog，在 navigation 架構中就是 push 一個新畫面。

批次操作中部分項目成功、部分失敗時（[三層回饋模型](../feedback-three-layers/)稱為「部分成功」），摘要加明細的資訊密度通常高到只有全螢幕才放得下。嚴重錯誤需要完整展示標題、原因說明與行動指引（[錯誤訊息撰寫原則](/ux-design/04-error-recovery/error-message-principles/)的三層結構），這種資訊密度同樣需要全螢幕作為容器。

**適用條件**：

- 結果內容需要完整閱讀和互動。批次操作的詳細結果（87 成功 / 13 失敗 + 每筆失敗的原因與修正操作）
- 流程的終結畫面。付款完成確認頁（金額、訂單編號、預計送達）
- 需要使用者在結果上做進一步操作。匯入結果的逐筆確認修正

## 選擇矩陣

本篇聚焦使用者操作後的結果通知。系統主動發起的通知（背景任務完成、伺服器推播、排程提醒）的形式選擇涉及 OS 層通知中心與 app 內通知的分工，不在本篇範圍。

把二軸交叉後，每個格子對應一到兩種適合的通知形式。矩陣同時涵蓋操作後的結果通知和操作前的預防性確認（第六列），因為兩者都需要在同一組通知形式中做選擇：

| 情境                                     | 需要使用者操作？ | 干擾程度建議 | 推薦形式          |
| ---------------------------------------- | ---------------- | ------------ | ----------------- |
| 操作成功，結果已反映在 UI                | 否               | 零           | Inline 狀態更新   |
| 操作成功，結果不在視線範圍               | 否               | 低           | SnackBar          |
| 操作成功，帶可選的復原                   | 可選             | 低           | SnackBar + action |
| 持續性狀態變更                           | 否/可選          | 中           | Banner            |
| 操作結果需要選後續操作                   | 是               | 中高         | Bottom Sheet      |
| 操作不可逆，需確認（操作前）             | 是               | 高           | Dialog            |
| 操作結果含關鍵資訊                       | 是               | 高           | Dialog            |
| 操作結果內容密度高，需要閱讀和進一步操作 | 是               | 最高         | 全螢幕            |

### 補充判準：操作頻率

矩陣是判讀起點，但二軸無法區分「刪除帳號」和「刪除待辦事項」— 兩者在軸一（需要操作：是）和軸二（干擾程度：高）的讀數相同。區分它們的是操作頻率：低頻高代價的刪除（刪帳號）用 Dialog 確認，高頻低代價的刪除（刪待辦事項）用 SnackBar + 復原。頻率高的操作應該降級通知形式 — 每次加入購物車都彈 Dialog 會讓 Dialog 的保護效果在第三次點擊時歸零。

## 自動消失的時間設計

SnackBar 的自動消失時間取決於使用者閱讀內容和決定是否操作所需的時間。

| 內容類型                | 建議停留時間 | 理由                                                                     |
| ----------------------- | ------------ | ------------------------------------------------------------------------ |
| 純文字確認（無 action） | 4 秒         | 一句話的閱讀時間，足夠瞄一眼（Material Design 短時長慣例值）             |
| 帶 action button        | 8-10 秒      | 使用者需要讀訊息 + 決定是否按 action（Material Design 範圍上端的推導值） |

Material Design 建議 SnackBar 顯示 4-10 秒。帶 action 時取範圍上端（8-10 秒）是基於「使用者需要讀完訊息再決定是否操作」的推導，MD 規範本身未針對帶 action 的情境單獨指定子範圍。下限低於 4 秒的風險是使用者來不及讀完（螢幕閱讀器使用者尤其受影響），上限超過 10 秒則開始干擾後續操作。

**無障礙考量**：帶 action 的 SnackBar 若自動消失且 action 不可復得，對依賴螢幕閱讀器的使用者是可用性問題（WCAG 2.1 SC 2.2.1 要求自動消失的內容可延長或可暫停）。替代策略：action 消失後仍可在別處操作（如復原也能從歷史記錄觸發），或螢幕閱讀器啟用時延長停留時間。

Banner 和 Dialog 不自動消失 — 它們承載的資訊或決策不能被時間限制替代。Banner 在觸發條件消失時自動移除（「離線模式」在恢復連線後消失）；Dialog 在使用者回應後關閉。

## 堆疊與排程

多個通知同時到達或短時間連續到達時，形式本身的堆疊規則決定使用者體驗。

SnackBar、Dialog、Bottom Sheet 都遵循「同一時間只顯示一個」的規則，但衝突時的行為不同。SnackBar 新舊替換 — 新的到達時當前的立即 dismiss；快速連續觸發（批次操作逐筆回饋）只有最後一條存活，這種場景應彙整為一條摘要（「已匯入 12 筆」）或改用全螢幕明細。Dialog 之上再彈 Dialog 是嚴重的 UX 問題 — 使用者的注意力不知道該放哪裡，dismiss 順序混亂；業務流程確實需要連續確認時，改為多步驟的單一 Dialog 或全螢幕流程。

Banner 是例外 — 多條 Banner 垂直堆疊，而非互相替換。超過兩條時畫面可用空間嚴重縮減；如果同時存在多個持續性狀態（離線 + 版本過舊 + 同步衝突），考慮合併為一條摘要 Banner 或改用全域狀態列。

少數可接受的跨形式堆疊：Bottom Sheet 之上彈 Dialog。Bottom Sheet 提供操作 context，Dialog 確認該操作 — 兩者的語意分工清楚，使用者不會混淆。

## 反模式

| 反模式                                | 症狀                                                    | 修正                                                 |
| ------------------------------------- | ------------------------------------------------------- | ---------------------------------------------------- |
| 所有通知都用 Dialog                   | 使用者訓練出「不讀直接按確定」，真正重要的確認被跳過    | 依二軸判準降級：純告知用 SnackBar，持續狀態用 Banner |
| 需要使用者操作的通知用 SnackBar       | SnackBar 自動消失，使用者還沒讀完就不見了               | 改用 Dialog 或延長停留時間 + 保留 action 在別處      |
| 頻繁操作的每次結果都彈 Dialog         | 流程不斷被打斷，操作效率下降                            | 改用 SnackBar 或 inline 狀態更新                     |
| 離線狀態用 SnackBar 通知              | SnackBar 消失後使用者忘記自己在離線，操作失敗時感到困惑 | 改用 Banner，持續顯示直到恢復連線                    |
| Dialog 裡再彈 Dialog                  | 使用者注意力分裂，dismiss 順序混亂                      | 合併為一個 Dialog 或改為多步驟流程                   |
| SnackBar 堆疊成串（逐筆回饋批次操作） | 只看到最後一條，前面的都被蓋掉                          | 彙整為一條摘要或改用全螢幕明細                       |

第一條和第二條是最常見的一對鏡像錯誤 — 前者過度使用 Dialog 稀釋了它的保護效果，後者讓需要操作的通知被時間自動沖掉。兩者的根因相同：沒有用「是否需要使用者操作」這個軸做區分。

第三條（頻繁 Dialog）的典型場景：電商 app 每次加入購物車都彈確認 Dialog，使用者連續加五件商品要按五次「確定」— 第三次開始就不看內容直接按，到真正需要確認的結帳 Dialog 也沿用同一反射動作。第四條（離線 SnackBar）：使用者在地鐵中斷線，SnackBar 閃一下「已離線」然後消失，30 秒後使用者填完表單送出，得到的是毫無脈絡的網路錯誤。第五條（Dialog 堆疊）：刪除按鈕彈確認 Dialog，確認後觸發權限檢查又彈第二個 Dialog，使用者按錯層 dismiss 會取消真正想做的操作。第六條（SnackBar 成串）：批次匯入 50 筆資料，每筆成功都彈 SnackBar，50 條在 4 秒內輪替，使用者只看到最後一條「第 50 筆匯入成功」，不知道前 49 筆的狀態。

## 設計檢查清單

為每個操作的結果通知逐一確認：

- [ ] 這個通知需要使用者操作嗎？（需要 → 不能自動消失）
- [ ] 干擾程度是否匹配通知的重要性？（不可逆操作 → Dialog，常規確認 → SnackBar）
- [ ] 自動消失的時間足夠使用者讀完內容並操作嗎？
- [ ] 多個通知同時到達時的堆疊行為是否合理？
- [ ] 持續性狀態用 Banner 而非 SnackBar？
- [ ] 高頻操作的通知夠低調嗎？（不會每次都打斷流程）
- [ ] 批次操作的結果有彙整，而非逐筆彈 SnackBar？

## 參考來源

- **Material Design 3: Snackbar**（[m3.material.io/components/snackbar](https://m3.material.io/components/snackbar)）— SnackBar 的設計規範與使用時機
- **Material Design 3: Dialogs**（[m3.material.io/components/dialogs](https://m3.material.io/components/dialogs)）— Dialog 的三種型態與使用準則
- **Material Design 3: Bottom Sheets**（[m3.material.io/components/bottom-sheets](https://m3.material.io/components/bottom-sheets)）— Bottom Sheet 的 modal 與 non-modal 使用場景
- **Apple Human Interface Guidelines: Alerts**（Apple Developer Documentation）— iOS Alert 的使用時機：需要使用者注意的重要資訊
- **Apple Human Interface Guidelines: Action Sheets**（Apple Developer Documentation）— iOS Action Sheet 的設計規範
- **Nielsen Norman Group: "Modal & Nonmodal Dialogs"**（nngroup.com, 2017）— Modal 與 nonmodal 的使用時機研究
