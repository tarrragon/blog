---
title: "First-party Cookie（第一方 cookie）"
date: 2026-10-23
description: "盤點網站寫下的識別碼 cookie、比對追蹤碼的 cookie 期限，或判斷某個 cookie 受不受瀏覽器的第三方 cookie 限制時"
weight: 9
tags: ["monitoring", "cookie", "privacy", "vendor", "knowledge-card"]
---

第一方 cookie（first-party cookie）是寫在使用者正在瀏覽的那個網站網域上的 cookie；寫在別的網域上、隨對那個網域的請求送出的，是第三方 cookie（third-party cookie）。歸屬只看 cookie 的網域，不看寫入它的 script 是誰的：Meta Pixel 與 GA4 的 script 從 Meta 與 Google 的網域載入，卻用 JavaScript 把識別碼寫在網站自己的網域上，所以 `_fbp`、`_fbc`、`_ga` 都是第一方 cookie。可先對照 [Headless Browser（無頭瀏覽器）](/monitoring/knowledge-cards/headless-browser/)（同一批追蹤碼在無頭模式下照樣寫 cookie、事件卻可能不送）與 [Autocapture（自動事件收集）](/monitoring/knowledge-cards/autocapture/)（這些識別碼會隨自動事件一起送出）；識別碼與瀏覽器指紋的差別見 [Browser Fingerprint（瀏覽器指紋）](/automation/knowledge-cards/browser-fingerprint/)。

## 概念位置

第一方 cookie 是追蹤碼在第三方 cookie 被瀏覽器限制之後保存識別碼的位置。第三方 cookie 由 vendor 的網域直接讀寫，第一方 cookie 寫在網站網域上，vendor 的伺服器收不到它的 Cookie 標頭，所以追蹤碼在瀏覽器裡讀出它的值，放進事件請求的參數送出：Meta Pixel 的每一筆事件都帶 `fbp` 參數，值就是 `_fbp` 的內容；GA4 的 collect 請求帶 `cid`，與 `_ga` 值裡的兩段數字相同。網站自己沒有呼叫的[自動事件](/monitoring/knowledge-cards/autocapture/)也帶著這些參數送出。

## 期限由誰決定

cookie 的到期時間由寫入它的 script 設定，再受瀏覽器的規則截斷。Chrome 從 104 版起把任何 cookie 的到期時間上限訂為 400 天，要求更久的 cookie 會被改成 400 天；Safari 的 Intelligent Tracking Prevention（ITP）另外限制 JavaScript 寫入的儲存資料，Google 的 cookie 說明頁把它寫成使用者沒有再造訪時最長 7 天。所以同一個追蹤碼在不同瀏覽器上的 cookie 壽命不同：GA4 代碼替 `_ga` 與 `_ga_<評估 ID>` 設的預設期限是兩年，在 Chromium 上實測看到的 400 天是瀏覽器的上限，不是 GA4 的設定。由 JavaScript 寫入的 cookie 不能設 `HttpOnly`，頁面上任何 script 都讀得到它。

## 可觀察訊號與例子

在開發者工具的 Application 面板（Chrome）或儲存空間面板（Firefox）查看網站網域底下的 cookie，看名稱、網域、到期時間與 `HttpOnly` 欄位。一次在 Chromium 上的實測裡，`_fbp` 與 `_fbc` 的到期時間是寫入起算 90 天，`_ga` 與 `_ga_<評估 ID>` 是 400 天，四個都不是 `HttpOnly`、`SameSite` 都是 `Lax`；`_fbc` 只有網址帶了廣告的點擊 ID（`fbclid`）時才寫入。各 cookie 的值怎麼對應到事件參數，以 [用 Playwright 擷取追蹤碼請求](/monitoring/vendors/tracking-request-capture/) 的結果檔為準。

## 判讀方式

判斷一個 cookie 的限制條件時，先看它寫在哪個網域、由誰寫入：瀏覽器封鎖第三方 cookie 不影響第一方 cookie，而 ITP 對 JavaScript 寫入的第一方 cookie 仍然生效，所以同一個人隔一週以上才在 Safari 上回來時，可能被追蹤碼當成另一個瀏覽器。判斷要不要取得使用者同意時，看的是「在使用者的裝置上儲存或讀取資訊」這個動作，第一方或第三方都在範圍內；把識別碼寫成第一方 cookie 改變的是瀏覽器的限制，改變不了同意的要求。

## 完整章節

追蹤碼寫下哪些 cookie、值怎麼對應到事件參數 → [用 Playwright 擷取追蹤碼請求](/monitoring/vendors/tracking-request-capture/)。`_fbp`、`_fbc` 在伺服器端事件裡的用途與 ITP 造成的損失 → [Meta Pixel 與 Conversions API](/monitoring/vendors/meta-pixel-conversions-api/)。cookie 期限在儲存限制裡的位置 → [GDPR 最小化原則的工程落地](/monitoring/07-security-privacy/gdpr-minimization/)。
