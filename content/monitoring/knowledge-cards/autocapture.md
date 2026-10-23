---
title: "Autocapture（自動事件收集）"
date: 2026-10-23
description: "盤點網站實際送出哪些事件與內容、報表裡出現網站沒有呼叫過的事件，或在標記式與自動收集式的埋點之間取捨時"
weight: 11
tags: ["monitoring", "event", "sdk", "vendor", "privacy", "knowledge-card"]
---

自動事件收集（autocapture）是追蹤碼不等網站呼叫、自己決定送出哪些使用者互動的做法：script 在頁面上監聽點擊、捲動、表單這類互動，依 vendor 的規則產生事件並送出，網站開發者不必為每個元素寫追蹤程式。相對的做法是標記式埋點，只有被開發者標記或明確呼叫的互動才會送出。可先對照 [First-party Cookie（第一方 cookie）](/monitoring/knowledge-cards/first-party-cookie/)（自動事件同樣帶著識別碼 cookie 的值送出）與 [Headless Browser（無頭瀏覽器）](/monitoring/knowledge-cards/headless-browser/)（送出端的機器人過濾對自動事件一樣生效）；送出前要遮蔽哪些欄位見 [Redaction](/monitoring/knowledge-cards/redaction/)。

## 概念位置

自動事件收集決定的是「事件從哪裡來」，位置在事件產生的那一端，比管線上的[取樣](/monitoring/knowledge-cards/sampling/)與[遮蔽](/monitoring/knowledge-cards/redaction/)都早：事件的欄位由 vendor 的規則決定，網站要等它送出之後才看得到內容。Meta 與 GA4 各有一套，範圍與開關不同。

**Meta Pixel** 的自動事件由 Pixel 的設定檔帶來的外掛產生。實測時每按一次頁面上的按鈕，`fbevents.js` 都在網站呼叫的事件之外多送一筆 `SubscribedButtonClick`，內容包含按鈕文字（`cd[buttonText]`）、按鈕的 DOM 特徵與頁面特徵；設定檔來自 Meta 的伺服器，所以送出哪些自動事件由 Meta 那一端的設定決定，網站的原始碼裡看不到。

**GA4** 把不需要額外程式就會收集的事件稱為自動收集的事件（automatically collected events），分成兩組。一組只要裝了 Google 代碼就會送，例如 `first_visit`、`session_start`、`user_engagement`；另一組由網頁資料串流的加強型評估（enhanced measurement）控制，包括捲動、外連點擊、站內搜尋、影片互動、檔案下載與表單互動，其中檔案下載會帶連結文字（`link_text`）、表單送出會帶送出按鈕的文字。`page_view` 也列在加強型評估底下，而且關不掉。加強型評估的開關在 GA4 管理介面的資料串流設定裡，需要編輯者以上的權限。

## 可觀察訊號與例子

在開發者工具的 Network 面板篩選 vendor 的網域，比對事件請求與網站自己呼叫的次數：Meta 的事件請求送到 `www.facebook.com/tr/`，事件名稱在 `ev` 參數；GA4 送到 `g/collect`，事件名稱在 `en` 參數。一次 Meta Pixel 的實測裡，網站呼叫了 ViewContent 與 Purchase 各一次，Network 面板上多出兩筆 `SubscribedButtonClick`，各自緊跟在一次按鈕點擊之後。

## 判讀方式

盤點網站送出哪些資料時，網站原始碼只列得出標記式的那一部分，自動事件要從實際送出的請求裡數；按鈕文字、連結文字這類欄位也在送出範圍內，按鈕或連結上顯示了使用者的個人資料時，那段文字會一起送到 vendor。兩種埋點方式的取捨方向相反：標記式會漏掉沒被標記的互動，換到的是送出的欄位全部由開發者決定；自動收集不漏互動，而送出的內容由 vendor 的規則決定、會隨 vendor 改版變動，所以盤點要在 vendor 改版之後重做一次。

## 完整章節

Meta Pixel 自動加送的事件與它的欄位 → [用 Playwright 擷取追蹤碼請求](/monitoring/vendors/tracking-request-capture/)。標記式感測器的設計與它和自動收集的對照 → [前端感測器設計](/monitoring/03-sdk-design/frontend-sensor-design/)。Pixel 設定檔帶來的外掛在瀏覽器端與伺服器端事件裡的位置 → [Meta Pixel 與 Conversions API](/monitoring/vendors/meta-pixel-conversions-api/)。
