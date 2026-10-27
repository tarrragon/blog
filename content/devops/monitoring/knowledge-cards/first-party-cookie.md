---
title: "First-party Cookie（第一方 cookie）"
date: 2026-10-23
description: "盤點網站寫下的識別碼 cookie、比對追蹤碼的 cookie 期限，或判斷某個 cookie 受不受瀏覽器的第三方 cookie 限制時"
weight: 9
tags: ["monitoring", "tracking", "privacy", "knowledge-card"]
aliases: ["/monitoring/knowledge-cards/first-party-cookie/"]
---

第一方 cookie（first-party cookie）是寫在使用者正在瀏覽的那個網站網域上的 cookie；寫在別的網域上、隨對那個網域的請求送出的，是第三方 cookie（third-party cookie）。歸屬只看 cookie 的網域，不看寫入它的 script 是誰的：Meta Pixel 與 GA4 的 script 從 Meta 與 Google 的網域載入，卻用 JavaScript 把識別碼寫在網站自己的網域上，所以 `_fbp`、`_fbc`、`_ga` 都是第一方 cookie。可先對照 [Headless Browser（無頭瀏覽器）](/devops/monitoring/knowledge-cards/headless-browser/)（同一批追蹤碼在無頭模式下照樣寫 cookie、事件卻可能不送）與 [Autocapture（自動事件收集）](/devops/monitoring/knowledge-cards/autocapture/)（這些識別碼會隨自動事件一起送出）；識別碼與瀏覽器指紋的差別見 [Browser Fingerprint（瀏覽器指紋）](/automation/knowledge-cards/browser-fingerprint/)。

## 概念位置

第一方 cookie 是追蹤碼在第三方 cookie 被瀏覽器限制之後保存識別碼的位置。第三方 cookie 由 vendor 的網域直接讀寫，第一方 cookie 寫在網站網域上，瀏覽器送往 vendor 網域的請求不會在 Cookie 標頭裡帶上網站網域的 cookie，所以追蹤碼在瀏覽器裡讀出它的值，放進事件請求的參數送出：在預設設定下（使用者沒有透過同意機制拒絕、追蹤碼的第一方 cookie 設定沒有關掉），Meta Pixel 的每一筆事件都帶 `fbp` 參數，值就是 `_fbp` 的內容；GA4 的 collect 請求帶 `cid`，與 `_ga` 值以點分隔的最後兩段數字相同。網站自己沒有呼叫的[自動事件](/devops/monitoring/knowledge-cards/autocapture/)也帶著這些參數送出。

## cookie 期限的設定者與瀏覽器上限

cookie 的到期時間由寫入它的 script 設定，再受瀏覽器的規則截斷。Chrome 從 104 版起把任何 cookie 的到期時間上限訂為 400 天，要求更久的 cookie 會被改成 400 天。Safari 的 Intelligent Tracking Prevention（ITP）對追蹤碼常用的寫法另有三條限制，依 WebKit 的追蹤防護說明頁：由 JavaScript 寫入的 cookie 與其他 script 寫得到的儲存資料（例如 localStorage），在使用者 7 天沒有與這個網站互動之後刪除（WebKit 先前的說明以使用 Safari 的天數計，現行說明頁沒有寫單位），重新起算的條件是互動、不是單純的造訪；ITP 偵測到網址帶著點擊 ID 這類參數（link decoration）時，落地頁上由 JavaScript 寫入的 cookie 期限上限是 24 小時（WebKit 先前的說明寫明的條件是：把使用者導過來的網域被分類為追蹤者，而且網址帶查詢字串或片段）；回應來自偽裝成第一方、實際指向第三方的伺服器（CNAME 或第三方 IP 偽裝）時，那個 HTTP 回應寫入的 cookie 期限上限是 7 天。所以同一個追蹤碼在不同瀏覽器上的 cookie 壽命不同：GA4 代碼替 `_ga` 與 `_ga_<評估 ID>` 設的預設期限是兩年，在 Chromium 上實測看到的 400 天是瀏覽器的上限，不是 GA4 的設定；從 Meta 廣告帶著 `fbclid` 點進來的那一次，`_fbc` 與 `_fbp` 正好在落地頁上由 JavaScript 寫入，在 Safari 上可能只留一天。

## 可觀察訊號與例子

在開發者工具的 Application 面板（Chrome）或儲存空間面板（Firefox）查看網站網域底下的 cookie，看名稱、網域、到期時間與 `HttpOnly` 欄位；由 JavaScript 寫入的 cookie 不能設 `HttpOnly`，所以頁面上任何 script 都讀得到它。一次在 Chromium 上的實測裡，`_fbp` 與 `_fbc` 的到期時間是寫入起算 90 天，`_ga` 與 `_ga_<評估 ID>` 是 400 天，四個都不是 `HttpOnly`、`SameSite` 都是 `Lax`；`_fbc` 只有網址帶了廣告的[點擊 ID](/devops/monitoring/08-business-analytics/attribution/)（`fbclid`）時才寫入。各 cookie 的值怎麼對應到事件參數，以 [用 Playwright 擷取追蹤碼請求](/devops/monitoring/vendors/tracking-request-capture/) 的結果檔為準。

## 判讀方式

一個 cookie 受哪些限制，取決於兩個屬性：它寫在哪個網域，以及它由 JavaScript 寫入還是由伺服器回應的 `Set-Cookie` 標頭寫入。寫入方式可以在 Network 面板分辨：某個回應的 `Set-Cookie` 標頭帶著這個名稱，就是伺服器寫的；所有回應都沒有、而它在 script 執行之後出現，就是 JavaScript 寫的。網域決定瀏覽器的第三方 cookie 封鎖管不管得到它，封鎖第三方 cookie 不影響第一方 cookie；寫入方式（連同回應來自誰的伺服器）決定 ITP 的哪一條限制管得到它，JavaScript 寫入的第一方 cookie 仍然受 ITP 限制，所以同一個人隔一週以上沒有互動、或從廣告點進來隔天才回來時，可能被追蹤碼當成另一個瀏覽器。用 Network 面板分辨寫入方式時，要用無痕視窗或先清掉這個網站的 cookie、在載入頁面之前就打開面板，否則前一次造訪留下的 cookie 會被誤判成 JavaScript 寫的。在歐盟 ePrivacy 指令下（第 5(3) 條，本站的解讀見[配額、濫用防護、隱私與遷移訊號](/automation/05-deploy-quota-security/quota-abuse-privacy/)的〈隱私與 PII 邊界〉），判斷是否要取得使用者同意時，看的是「在使用者的裝置上儲存或讀取資訊」這個動作，第一方或第三方都在範圍內；把識別碼寫成第一方 cookie 改變的是瀏覽器的限制，改變不了這條同意的要求。

## 完整章節

追蹤碼寫下哪些 cookie、值怎麼對應到事件參數 → [用 Playwright 擷取追蹤碼請求](/devops/monitoring/vendors/tracking-request-capture/)。`_fbp`、`_fbc` 在伺服器端事件裡的用途與 ITP 造成的損失 → [Meta Pixel 與 Conversions API](/devops/monitoring/vendors/meta-pixel-conversions-api/)。cookie 期限在儲存限制裡的位置 → [GDPR 最小化原則的工程落地](/devops/monitoring/07-security-privacy/gdpr-minimization/)。
