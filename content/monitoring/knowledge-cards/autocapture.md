---
title: "Autocapture（自動事件收集）"
date: 2026-10-23
description: "盤點網站實際送出哪些事件與內容、報表裡出現網站沒有呼叫過的事件，或在手動埋點與自動收集之間取捨時"
weight: 11
tags: ["monitoring", "event", "sdk", "vendor", "privacy", "knowledge-card"]
---

自動事件收集（autocapture）是由追蹤碼自己決定送出哪些事件、網站不必逐一呼叫的做法：script 在頁面上監聽點擊、捲動、表單這類互動，或在頁面載入、工作階段開始這類時點，依 vendor 的規則產生事件並送出。涵蓋哪些互動由 vendor 的規則決定，不是頁面上的每一個互動都會送。相對的做法是手動埋點：開發者在要追蹤的元素或事件處自己寫追蹤程式（標上屬性或呼叫追蹤函式），只有這些互動才會送出。可先對照 [First-party Cookie（第一方 cookie）](/monitoring/knowledge-cards/first-party-cookie/)（自動事件同樣帶著識別碼 cookie 的值送出）與 [Headless Browser（無頭瀏覽器）](/monitoring/knowledge-cards/headless-browser/)（瀏覽器裡的機器人過濾對自動事件一樣生效）。自建 SDK 在事件送出前遮蔽欄位的做法見 [Redaction](/monitoring/knowledge-cards/redaction/)；商業追蹤碼的自動事件由 vendor 的 script 直接送出、不經過網站的遮蔽步驟，網站能控制的是開或關那一項自動收集。

## 概念位置

自動事件收集決定的是「事件從哪裡來」，位置在事件產生的那一端，比管線上的[取樣](/monitoring/knowledge-cards/sampling/)與[遮蔽](/monitoring/knowledge-cards/redaction/)都早：事件的欄位由 vendor 的規則決定，網站要等它送出之後才看得到內容。名稱各家不同：Meta 把這類事件叫自動事件（automatic events），GA4 叫自動收集的事件（automatically collected events），本站把兩者統稱為自動事件。兩家的範圍與開關也不同。

**Meta Pixel** 的自動事件由 Pixel 的設定檔指定的模組產生：`fbevents.js` 載入後會向 Meta 取得這個 Pixel 的設定檔，設定檔決定要載入哪些模組（plugin，見 [Meta Pixel 與 Conversions API](/monitoring/vendors/meta-pixel-conversions-api/) 的〈Meta Pixel 在瀏覽器裡做的事〉）。實測時每按一次頁面上的按鈕，`fbevents.js` 都在網站呼叫的事件之外多送一筆 `SubscribedButtonClick`，內容包含按鈕文字（`cd[buttonText]`）、按鈕的 DOM 特徵與頁面特徵；設定檔來自 Meta 的伺服器，所以送出哪些自動事件由 Meta 那一端的設定決定，網站的原始碼裡看不到。

**GA4** 的自動收集事件分成只要裝了 Google 代碼就會送的基本事件，例如 `first_visit`、`session_start`、`user_engagement`，以及由加強型評估（enhanced measurement）控制的事件。加強型評估是網頁資料串流（GA4 資源裡代表一個網站資料來源的設定單位）上的一組開關，涵蓋捲動、外連點擊、站內搜尋、影片互動、檔案下載與表單互動，其中檔案下載會帶連結文字（`link_text`）、表單送出會帶送出按鈕的文字。`page_view` 也列在加強型評估底下，而它是其中唯一關不掉的一項。這組開關在 GA4 管理介面的資料串流設定裡，需要編輯者以上的權限。

## 可觀察訊號與例子

自動事件在請求裡的樣子與網站自己呼叫的事件相同，差別只在網站的程式碼裡找不到對應的呼叫。Meta 的事件請求送到 `www.facebook.com/tr/`，事件名稱在 `ev` 參數；GA4 的事件請求送到 Google Analytics 網域下的 `g/collect`（在開發者工具的 Network 面板以 `collect` 篩選），事件名稱在 `en` 參數。一次 Meta Pixel 的實測裡，網站呼叫了 ViewContent 與 Purchase 各一次，擷取結果裡多出兩筆 `SubscribedButtonClick`，各自緊跟在一次按鈕點擊之後。

## 判讀方式

網站原始碼只列得出手動埋點的那一部分，網站實際送出的資料要從送出的請求裡數；按鈕文字、連結文字這類欄位也在送出範圍內，按鈕或連結上顯示了使用者的個人資料時，那段文字會一起送到 vendor。兩種埋點方式的取捨方向相反：手動埋點會漏掉沒有寫追蹤程式的互動，換到的是送出的欄位全部由開發者決定；自動收集不需要逐一標記，而涵蓋哪些互動、送出哪些欄位由 vendor 的規則決定、會隨 vendor 改版變動。vendor 改版不會通知網站，所以送出資料的盤點要定期重做；Meta Pixel 的版本可以在頁面的開發者工具 Console 輸入 `fbq.version` 讀出，與上次盤點記下的值比對。

## 完整章節

Meta Pixel 自動加送的事件與它的欄位 → [用 Playwright 擷取追蹤碼請求](/monitoring/vendors/tracking-request-capture/)的〈各次擷取的結果〉。以 `data-track` 屬性手動埋點的感測器設計，與它和自動收集的對照 → [前端感測器設計](/monitoring/03-sdk-design/frontend-sensor-design/)。設定檔指定的模組怎麼在網站沒呼叫時自己送事件 → [Meta Pixel 與 Conversions API](/monitoring/vendors/meta-pixel-conversions-api/) 的〈Meta Pixel 在瀏覽器裡做的事〉；同一類模組依 User-Agent 攔下事件的機制 → [用 Playwright 擷取追蹤碼請求](/monitoring/vendors/tracking-request-capture/)的〈擷取方式〉。
