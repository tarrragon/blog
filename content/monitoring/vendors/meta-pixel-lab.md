---
title: "Meta Pixel 實測頁：在瀏覽器裡觀察 fbq 呼叫、送出的請求與寫下的 cookie"
date: 2026-10-22
description: "在這一頁按按鈕載入 Meta Pixel、送 PageView、ViewContent 與帶 eventID 的 Purchase，並用頁面上的面板對照每個呼叫送出的請求參數，以及 _fbp 與 fbclid 帶出的 _fbc cookie"
weight: 3
tags: ["monitoring", "vendor", "meta-pixel", "lab", "tracking"]
---

這一頁是 [Meta Pixel 與 Conversions API](/monitoring/vendors/meta-pixel-conversions-api/) 的實測頁，範圍是瀏覽器端的 Pixel：載入 `fbevents.js`、用 `fbq()` 送事件，以及 Pixel 寫在網站網域上的 cookie。Conversions API 是伺服器端的路徑，在瀏覽器裡看不到，不在這一頁。

## 這一頁載入什麼、什麼時候載入

頁面打開時不載入任何 Meta 的 script。按下「載入 Meta Pixel 並送 PageView」之後，面板才把 `fbevents.js` 從 `connect.facebook.net` 注入頁面，並用填在欄位裡的 Pixel ID 初始化；在那之前這一頁沒有任何送往 Meta 的請求，請求清單可以直接驗證這一點。注入的 script 在重新整理或離開這一頁時就消失，而 Pixel 寫下的 cookie 會留在這個網域上，直到按「清除這一頁的追蹤 cookie」或瀏覽器自己刪除。

Pixel ID 欄位填的是 Meta Events Manager 裡某個 Pixel 的 ID。站方設定了測試用 Pixel 時，欄位會預先填好它的 ID；欄位空白時填自己的測試 Pixel ID。用自己的 Pixel 實測時，事件會出現在那個 Pixel 的 Test Events 頁面，可以對照 Meta 那一端實際收到了什麼。

{{< vendor-lab vendor="meta-pixel" >}}

## 對照面板讀出各個呼叫的效果

面板分成三塊。「操作紀錄」列出按鈕實際執行的 `fbq()` 呼叫；「這一頁送出的跨網域請求」來自瀏覽器的 Resource Timing 紀錄，列出這一頁向其他網域發出的每一個請求與它的查詢參數；「追蹤 cookie」列出這個網域上以 `_fbp`、`_fbc` 等前綴開頭的 cookie。操作紀錄、請求與 cookie 並排讀，就能把一個呼叫對到它造成的網路請求與狀態變化。

- **載入 Pixel 之後**：請求清單先出現 `fbevents.js` 這個 script 請求，接著是 Pixel 送出 PageView 的請求。查詢參數裡可以找到 Pixel ID 與事件名稱；其餘參數的名稱與意義由 Meta 決定、會隨版本調整，以這一頁當下列出的為準。cookie 清單在幾秒內出現 `_fbp`。
- **送 Purchase**：操作紀錄裡的 `eventID` 是這次按鈕產生的值，在請求的查詢參數裡找得到同一個值，這就是 Conversions API 去重時要對上的那一個。`value` 與 `currency` 也出現在同一個請求裡。
- **帶 fbclid 參數重新開啟這一頁**：按鈕把一個測試用的 `fbclid` 加進網址再重新載入。重新載入後再按一次「載入 Meta Pixel」，cookie 清單會多出 `_fbc`，值裡包含剛才的 `fbclid`。這是讀者從廣告點進網站時 Pixel 保存點擊來源的方式。
- **載入失敗**：狀態列顯示「載入失敗」時，代表 `fbevents.js` 的請求被擋下，常見來源是廣告攔截器、瀏覽器的追蹤防護或公司網路的政策。這時按其他按鈕，`fbq()` 只會把呼叫排進佇列，請求清單裡不會出現任何送往 Meta 的請求。這正是瀏覽器端事件損失的樣子：網站這一端沒有任何錯誤訊息。

請求清單在頁面打開時就可能已經有幾筆紀錄，那些是本站每一頁都會載入的第三方資源（例如從 `cdn.jsdelivr.net` 載入的 Mermaid）與本站的流量 beacon（送往 `script.google.com`），與 Meta 無關。本站的 beacon 怎麼設計見 [Automation 模組二：流量 beacon 實作](/automation/02-analytics-beacon/)，拿來和 Pixel 的請求並排看，是自製追蹤與第三方追蹤碼在送出內容上的對照。

Resource Timing 只記錄網址，看不到 POST 請求的 body；Pixel 改用 POST 送出的事件在這裡只看得到網址。要看完整的請求內容，打開瀏覽器開發者工具的 Network 面板，篩選 `facebook` 再點開那一筆。
