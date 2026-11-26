---
title: "Content Script（內容腳本）"
date: 2026-11-26
description: "Chrome 擴充功能要讀或改網頁上的內容，content script 沒有注入、改了程式卻還是舊行為、拿不到網頁自己的變數，或 popup 送訊息到分頁時出現 Receiving end does not exist 時"
weight: 22
tags: ["ux-design", "knowledge-card", "chrome-extension", "manifest-v3", "content-script"]
---

Chrome 擴充功能讀網頁上的資料、在網頁上加按鈕，都由 Content Script（內容腳本）執行：擴充功能注入網頁、在那個網頁裡執行的腳本，也是擴充功能裡唯一碰得到網頁 DOM 的部分。manifest 的 `content_scripts` 寫明要注入哪些網址（`matches`），符合的網頁一載入就注入；擴充功能也可以呼叫 `chrome.scripting.executeScript` 在需要時注入。它讀到或做完的結果交給 [Extension Service Worker（擴充功能的背景程式）](/ux-design/knowledge-cards/extension-service-worker/) 處理或保存。

## 跟其他概念的關係

content script 跟網頁共用同一份 DOM，但不共用 JavaScript 的執行環境：Chrome 讓它跑在一個獨立的環境（isolated world），網頁自己的全域變數與函式它讀不到，它定義的變數網頁也讀不到。所以網頁上看得到的內容，content script 讀得到；只存在網頁程式記憶體裡的狀態（框架的 store、網頁自己的變數），它讀不到，要從 DOM 或網頁發出的請求間接取得。

它能用的 `chrome.*` API 只有少數幾組（`chrome.runtime` 的訊息與 `chrome.storage` 這類），其餘的工作交給 [Extension Service Worker（擴充功能的背景程式）](/ux-design/knowledge-cards/extension-service-worker/)：它用 `chrome.runtime.sendMessage` 把資料送過去，service worker 或 popup 用 `chrome.tabs.sendMessage` 把指令送進分頁。這條訊息鏈路上任何一段沒接好，畫面上的結果就跟實際發生的事對不上，例如 [U.C9 提取成功卻誤報失敗 — 結果通知鏈路被搶通道](/ux-design/cases/async-listener-false-failure/)。

## 可觀察訊號與例子

它的 log 出現在那個網頁的 DevTools（網頁按 F12）；Console 頂端的執行環境選單可以切到擴充功能的那一個，要在 content script 的環境裡執行程式時才需要切。service worker 的 log 不在這裡。

popup 呼叫 `chrome.tabs.sendMessage` 送到一個沒有 content script 的分頁時，會得到 `Could not establish connection. Receiving end does not exist` 這個錯誤。成因之一是這個分頁在擴充功能安裝或重新載入之前就開著：宣告式注入只發生在網頁載入時，不會補進已經開著的網頁。

2026 年一個電子書擴充功能由 content script 在書城的書櫃頁捲動、載入並解析書目，它回報給 popup 的本數是當下 DOM 裡的元素數，而書櫃是捲動才載入的清單，剛進頁面只有第一批；細節見 [Chrome 擴充功能提取書目之後書庫頁停在舊資料的排查：逐段計數、頁首總數的解析、轉送層覆蓋欄位寫錯 storage key、舊識別碼對不上而新增重複、修好之後的殘留資料](/work-log/chrome-extension-library-stale-after-extraction/)。

## 判斷條件與後果

修改了 content script 的程式之後，未封裝的擴充功能重新載入，已經開著的網頁裡跑的仍然是注入時的那一份；那個網頁要重新整理，新的程式才會注入。只重新載入擴充功能就測試，看到的是舊行為，容易被誤判成修法無效。

網頁是捲動或分頁才載入內容時，content script 在某一刻讀到的 DOM 只是已經載入的那一部分；把這個數字當成總數，預告與實際處理的數量就對不上，總數要從網頁宣告的總數或 API 回應取得。

content script 跑在網頁裡，網頁的結構改版時它的選擇器可能全部失效，而它不會報錯，只是讀到零筆或讀錯欄位；所以解析結果的筆數要跟網頁宣告的總數對照，對不上時要看得見，不能安靜地當成零。

同一份 DOM 也被網頁自己的程式操作：網頁在 content script 讀完之後重繪了那一區（單頁應用換頁、無限捲動回收元素），content script 手上的元素參照就指到已經被移除的節點，需要在網頁變動時重新讀取（`MutationObserver` 這類）。
