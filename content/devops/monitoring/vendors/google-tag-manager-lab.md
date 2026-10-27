---
title: "Google Tag Manager 實測頁：在瀏覽器裡觀察容器載入、資料層事件與代碼送出的請求"
date: 2026-10-22
description: "在這一頁按按鈕載入 GTM 容器、往資料層推 purchase 事件，並用頁面上的面板對照 window.dataLayer 的內容、容器載入的代碼與它們送出的請求"
weight: 4
tags: ["monitoring", "vendor", "google-tag-manager", "gtm", "lab", "tracking"]
aliases: ["/monitoring/vendors/google-tag-manager-lab/"]
---

這一頁是 [Google Tag Manager](/devops/monitoring/vendors/google-tag-manager/) 的實測頁，範圍是網頁容器：載入 `gtm.js`、往資料層推事件，以及容器依設定載入的代碼。伺服器端代碼管理的伺服器容器在瀏覽器裡看不到，不在這一頁。

## 這一頁載入什麼、什麼時候載入

頁面打開時不載入 GTM。按下「載入 GTM 容器」之後，面板才先往 `window.dataLayer` 推一筆 `gtm.js` 事件，再從 `googletagmanager.com` 注入填在欄位裡的那個容器；在那之前這一頁沒有任何送往 Google 的請求。注入的容器在重新整理或離開這一頁時消失，容器裡的代碼寫下的 cookie 會留在這個網域上，直到按「清除這一頁的追蹤 cookie」。

容器 ID 欄位填的是 GTM 後台裡某個容器的 ID（`GTM-` 開頭）；欄位預設空白，填自己的測試容器 ID。容器裡有哪些代碼、它們在什麼觸發條件下執行，由那個容器目前發布的版本決定，所以同一個按鈕在不同容器上會送出完全不同的請求。用自己的測試容器實測時，在 GTM 後台開啟預覽模式再回到這一頁，就能在 Tag Assistant 裡看到每一筆資料層事件觸發了哪些代碼。

{{< vendor-lab vendor="gtm" >}}

## 對照面板讀出容器的行為

面板分成四塊：「操作紀錄」列出按鈕實際執行的 `dataLayer.push()`；「這一頁送出的跨網域請求」列出這一頁向其他網域發出的每一個請求；「追蹤 cookie」列出 `_ga`、`_gcl` 等前綴開頭的[第一方 cookie](/devops/monitoring/knowledge-cards/first-party-cookie/)；「window.dataLayer 目前的內容」是資料層這個陣列的完整內容。

- **載入容器之後**：資料層除了按鈕推的 `gtm.js`，還會多出容器自己推入的事件（頁面的 DOM 就緒、視窗載入完成這類），它們是 GTM 內建觸發條件比對的對象。請求清單先出現 `gtm.js`，再出現容器裡各個代碼載入的 script 與送出的請求——容器設了 GA4 就會看到送往 Google Analytics 的請求，設了 Meta Pixel 就會看到 `fbevents.js`。
- **往資料層推 purchase 事件**：資料層多一筆帶 `order_id`、`value`、`currency` 的物件。容器裡有以 `purchase` 為名的自訂事件觸發條件時，以它為觸發條件的代碼會在這時執行並送出請求；沒有的話這一筆只會留在陣列裡，請求清單不會變。資料層是約定、容器決定要不要讀它，從這裡可以直接看到兩者的分工。
- 推了事件而容器沒有對應觸發條件時網路請求的實際樣子，擷取紀錄見 [用 Playwright 擷取追蹤碼請求](/devops/monitoring/vendors/tracking-request-capture/) 的 GTM 那一則。
- **沒有載入容器就推事件**：先按「往資料層推 purchase 事件」再載入容器，容器載入後會從陣列開頭依序處理已經在裡面的事件，所以先推的那一筆仍然觸發得到代碼。網站在容器載入完成之前就推事件，靠的是這個行為。
- **載入失敗**：狀態列顯示「載入失敗」時，代表 `gtm.js` 的請求被擋下（廣告攔截器、瀏覽器追蹤防護或網路政策），容器裡的每一個代碼都不會執行。

請求清單在頁面打開時就可能已經有幾筆紀錄，那些是本站每一頁都會載入的第三方資源（例如從 `cdn.jsdelivr.net` 載入的 Mermaid）與本站的流量 beacon（送往 `script.google.com`），與 GTM 無關。Resource Timing 只記錄網址、看不到 POST 請求的 body，要看完整內容改用瀏覽器開發者工具的 Network 面板。
