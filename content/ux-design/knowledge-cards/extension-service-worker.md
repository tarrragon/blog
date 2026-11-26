---
title: "Extension Service Worker（擴充功能的背景程式）"
date: 2026-11-26
description: "Chrome 擴充功能（Manifest V3）的 popup 剛打開就顯示離線、背景程式改了卻沒生效、全域變數莫名其妙歸零，或要分辨擴充功能的 service worker 跟網頁的 service worker 時"
weight: 21
tags: ["ux-design", "knowledge-card", "chrome-extension", "manifest-v3", "service-worker"]
---

Extension Service Worker（擴充功能的背景程式）是 Chrome 擴充功能在 Manifest V3 底下唯一的背景執行環境：manifest 的 `background.service_worker` 指定一支腳本，瀏覽器在有事件要處理時啟動它，閒置一段時間後把它停掉。擴充功能的 popup、設定頁與注入網頁的 [Content Script（內容腳本）](/ux-design/knowledge-cards/content-script/) 都把需要跨分頁、跨頁面保存或協調的工作交給它，例如收訊息、呼叫 `chrome.*` API、寫 `chrome.storage`。Manifest V2 的背景頁（background page）一直開著，Manifest V3 改成這種依事件啟停的形式。

## 跟其他概念的關係

擴充功能的 service worker 與網頁的 service worker 共用同一種執行環境（`ServiceWorkerGlobalScope`），用途不同。網頁的 service worker 由網頁呼叫 `navigator.serviceWorker.register` 登記，管一個網站範圍內的請求攔截與離線快取；擴充功能的 service worker 由 manifest 宣告，管這個擴充功能的事件與 `chrome.*` API，不負責替任何網站做快取。兩者都沒有 DOM，也都不能用 `localStorage`。

它跟 [Content Script（內容腳本）](/ux-design/knowledge-cards/content-script/) 分工的界線是能碰到什麼：content script 碰得到網頁的 DOM、只拿得到少數 `chrome.*` API；service worker 碰不到任何網頁的 DOM、拿得到擴充功能宣告過權限的全部 API。兩邊靠訊息（`chrome.runtime.sendMessage`、`chrome.tabs.sendMessage`）往來，所以 content script 讀到的資料要經過一段訊息轉送，才會被寫進 storage、顯示在畫面上。

它閒置後會被停掉，所以查詢它的畫面多了一個狀態：popup 打開時 service worker 可能還沒醒，要先等它啟動、跑完初始化才回應，這段時間是「還不知道」，不是「離線」。這個狀態要放進 [Screen State Matrix](/ux-design/knowledge-cards/screen-state-matrix/) 的一列。

## 可觀察訊號與例子

它的 log 只出現在它自己的 DevTools：在 `chrome://extensions` 該擴充功能的卡片上按「Service Worker」連結打開，網頁按 F12 開的 Console 看不到。排查時使用者貼回來的 log 屬於哪一個執行環境，是最先要確認的事。

2026 年一個電子書擴充功能的 popup 有時一打開就顯示離線：popup 向 service worker 查狀態，2 秒沒有回應就判成離線，而 service worker 冷啟動偶爾超過 2 秒。成因與設計見 [U.C10 Service Worker 冷啟動期間的假離線 — initializing 狀態未建模](/ux-design/cases/service-worker-cold-start-false-offline/)。同一個擴充功能的 service worker 裡有一層訊息轉送，它替事件加上的附註佔用了下游拿來組 storage key 的欄位名，書目因此寫進錯的 key，排查過程見 [Chrome 擴充功能提取書目之後書庫頁停在舊資料的排查：逐段計數、頁首總數的解析、轉送層覆蓋欄位寫錯 storage key、舊識別碼對不上而新增重複、修好之後的殘留資料](/work-log/chrome-extension-library-stale-after-extraction/)。

## 判斷條件與後果

資料放在 service worker 的全域變數時，它被停掉那一刻資料就沒了，下一次啟動時變數回到初始值；要跨啟動保存的資料放在 `chrome.storage`，啟動時讀回來。依 Chrome 官方文件〈The extension service worker lifecycle〉，閒置約 30 秒會被停掉，收到事件或呼叫擴充功能 API 時重新計時；這個時間依 Chrome 版本調整過，以當下版本的文件為準。

事件監聽器（`chrome.runtime.onMessage.addListener` 這類）寫在腳本最上層、同步登記時，瀏覽器為了某個事件喚醒它之後，監聽器已經在，事件送得到；登記寫在 `await` 或 callback 之後時，喚醒當下監聽器還不存在，那個事件就漏掉了，症狀是「偶爾沒反應、重開擴充功能就好」。

修改了 service worker 的程式之後，未封裝的擴充功能要在 `chrome://extensions` 重新載入才會跑新的程式，停掉再喚醒仍然是舊版；這跟 content script 一樣，跟 popup（重新打開就是新版）不同。

查詢它的畫面（popup、設定頁）在它還沒回應時處在「初始化中」：把這段時間直接判成離線，代價是使用者看到一個不存在的故障；所以初始化中要有自己的顯示，等待逾時才是它的退出路徑。
