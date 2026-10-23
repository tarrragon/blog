---
title: "Meta Pixel 與 Conversions API：廣告平台轉換追蹤的瀏覽器端與伺服器端"
date: 2026-10-22
description: "Meta Pixel 在頁面上送出的標準事件與它的資料消費者、瀏覽器端事件被攔截的路徑、Conversions API 從伺服器補送同一批事件的必填欄位，以及兩路並送時以 event_id 去重與用 Test Events 驗證的方式"
weight: 1
tags: ["monitoring", "vendor", "meta-pixel", "conversions-api", "attribution", "tracking"]
---

這篇整理 Meta（Facebook / Instagram 廣告）的網站轉換追蹤：瀏覽器端的 Meta Pixel、伺服器端的 Conversions API（常簡稱 CAPI），以及兩條路徑並用時的去重與驗證。範圍是網站事件；App 端的事件走 Meta 的 App SDK，不在這篇。欄位規格以 Meta 開發者文件為準，本篇引用的規則（必填欄位、去重的時間窗、`event_time` 的上限）都會隨 Meta 改版調整，接入時回官方文件核對一次。

## 廣告平台轉換追蹤的資料消費者

Meta Pixel 送出的事件，主要的消費者是 Meta 的廣告投放系統：投放演算法依轉換事件學習該把廣告給誰看，廣告後台依它計算每一檔廣告帶來幾筆轉換。這一點讓它跟 [Mixpanel / Amplitude](/monitoring/06-commercial-comparison/mixpanel-amplitude/) 這類行為分析工具分開——行為分析的消費者是自己的產品團隊，事件怎麼命名、帶什麼屬性由自己決定；廣告平台的事件要讓平台的演算法讀得懂，所以命名照平台的規定。

Meta 定義了一組標準事件（standard events）：`PageView`、`ViewContent`、`AddToCart`、`InitiateCheckout`、`Purchase`、`Lead`、`CompleteRegistration` 等。廣告活動的最佳化目標綁在這些事件名稱上，例如以「購買」為目標的廣告活動讀的是 `Purchase`；`Purchase` 另外要帶 `value` 與 `currency`，平台才算得出廣告投資報酬。自己的事件命名（[事件命名規範](/monitoring/01-mental-model/event-naming-convention/) 的 `namespace.action`）因此需要一層對映：`checkout.complete` 送到自己的 collector，同一筆在送往 Meta 時改名成 `Purchase`。對映表寫在一個地方、由工程維護，比散在各個埋點呼叫裡改名好查。

廣告平台各自用自己看得到的事件做歸因，同一筆訂單可能同時被 Meta 與 Google Ads 算成自己帶來的轉換，兩個後台的轉換數加總會大於實際訂單數。跨渠道的歸因模型見 [Attribution](/monitoring/08-business-analytics/attribution/)。

## Meta Pixel 在瀏覽器裡做的事

Pixel 的基本碼從 `connect.facebook.net` 載入 `fbevents.js`，再用 `fbq()` 這個全域函式初始化並送事件。`fbevents.js` 載入後會再向 Meta 取得這個 Pixel 的設定檔，設定檔帶來的外掛會在網站沒有呼叫 `fbq()` 的情況下自己送事件，例如依按鈕點擊送出的 `SubscribedButtonClick`，內容包含按鈕文字；實測見 [用 Playwright 擷取追蹤碼請求](/monitoring/vendors/tracking-request-capture/) 的 Meta Pixel 有視窗那一次。

```html
<script>
  // Meta 提供的載入片段（略）：定義 fbq 並從 connect.facebook.net 載入 fbevents.js
  fbq('init', 'PIXEL_ID');   // PIXEL_ID 換成 Events Manager 裡那個 Pixel 的 ID
  fbq('track', 'PageView');  // 每一頁載入時送一次
</script>
```

`fbq('init', ...)` 的第二個引數是 Pixel ID，每個 Pixel 在 Meta Events Manager 裡有自己的一串數字，一個網站可以初始化多個 Pixel。`PIXEL_ID` 在這裡是佔位值，要換成自己 Events Manager 裡顯示的那一串。

送轉換事件時，`fbq('track', ...)` 依序接事件名稱、事件參數、以及選填的第四個引數：

```js
// 第二個引數是標準事件名稱，第三個是事件參數，第四個帶這一筆事件的唯一 ID
fbq('track', 'Purchase',
  { value: 1280, currency: 'TWD' },
  { eventID: 'order-20261022-0042' });
```

`value` 與 `currency` 是這一筆購買的金額與幣別，從訂單資料取值。`eventID` 是這一筆事件的識別碼，只送 Pixel 的時候可以省略；同一筆事件還要從伺服器再送一次時就必須帶，原因在〈兩路並送時的去重規則〉一節。

Pixel 也在網站自己的網域上寫 cookie：`_fbp` 記錄這個瀏覽器的識別碼；使用者從廣告點進來時，落地網址會帶 `fbclid` 參數，Pixel 把它存成 `_fbc`。這兩個 cookie 是[第一方 cookie](/monitoring/knowledge-cards/first-party-cookie/)（寫在網站自己的網域上），之後伺服器端送事件時會用到它們的值。

## 瀏覽器端事件的損失路徑

Pixel 的事件從讀者的瀏覽器發出，所以它會在讀者端被擋下，而網站這一端收不到任何錯誤：

- **廣告攔截器擋下 script 本身**：攔截清單收錄 `connect.facebook.net` 這類已知追蹤網域，`fbevents.js` 載不進來，`fbq()` 之後的所有事件都不會送出。
- **瀏覽器的追蹤防護縮短 cookie 壽命**：Safari 的 Intelligent Tracking Prevention（ITP）會限制由 JavaScript 寫入的第一方 cookie 的有效期，`_fbp` 因此比預期更早消失，同一個人隔幾天回來購買時會被當成另一個瀏覽器；部分瀏覽器與 App 內開啟的連結也會移除網址裡的 `fbclid`。
- **同意聲明還沒取得**：在要求事先同意的法域（例如 GDPR 下的歐盟讀者），網站在使用者同意之前不能載入 Pixel，這段期間的事件依規定就不送。
- **自動化與機器人流量過濾**：Pixel 設定檔裡的外掛依 User-Agent 判斷機器人流量，[無頭瀏覽器](/monitoring/knowledge-cards/headless-browser/)（User-Agent 帶 `HeadlessChrome`）送出的事件在瀏覽器裡就被攔下。`fbevents.js` 照常載入、cookie 照常寫入，網站這一端看不出事件沒送；用自動化工具驗證追蹤設定時會撞上這一條，實測見 [用 Playwright 擷取追蹤碼請求](/monitoring/vendors/tracking-request-capture/) 的無頭模式那一次。
- **跳頁中斷**：購買按鈕按下後立刻導向感謝頁，送事件的請求可能還沒送完頁面就被卸載。這是所有前端事件追蹤共通的狀況，機制與 `sendBeacon` 的解法見 [JS/TS 平台適配](/monitoring/05-platform-adaptation/js-ts-platform/)。

每個網站被擋下的比例取決於讀者組成（裝攔截器的比例、iOS 的比例、歐盟流量的比例），網路上流傳的百分比是別人網站的數字。量自己網站的方式是對帳：同一段期間內，訂單資料庫裡的訂單數與 Events Manager 收到的 `Purchase` 數相比，差距就是這個網站的瀏覽器端損失。

## Conversions API：從伺服器送同一批事件

Conversions API 讓網站的伺服器直接把事件 POST 到 Meta 的 Graph API（`/<PIXEL_ID>/events`），請求不經過讀者的瀏覽器，所以廣告攔截器與 cookie 期限都影響不到它。代價是伺服器要自己準備瀏覽器原本會自動附上的資訊：

```json
{
  "data": [{
    "event_name": "Purchase",
    "event_time": 1792656000,
    "event_id": "order-20261022-0042",
    "action_source": "website",
    "event_source_url": "https://shop.example.com/checkout/thanks",
    "user_data": {
      "client_user_agent": "<下單時瀏覽器的 User-Agent>",
      "client_ip_address": "<下單時的來源 IP>",
      "fbp": "<讀自 _fbp cookie>",
      "fbc": "<讀自 _fbc cookie>",
      "em": ["<正規化後的 email 的 SHA-256>"]
    },
    "custom_data": { "value": 1280, "currency": "TWD" }
  }]
}
```

欄位的來源與限制：

- `event_name`、`event_id`、`custom_data` 與 Pixel 那一筆相同，名稱的對映方式見〈廣告平台轉換追蹤的資料消費者〉一節。
- `event_time` 是事件發生的 Unix 時間（秒）。Meta 接受的範圍是送出當下往前七天內；一批資料裡只要有一筆超過七天，整個請求會被拒絕、一筆都不處理，所以用排程補送積壓的事件時要先過濾掉過期的那些。
- `action_source` 標明事件發生在哪裡，網站事件填 `website`。Meta 對網站事件另外要求 `event_source_url`（事件發生的頁面網址，網域要與 Meta 後台驗證過的網域一致）與 `client_user_agent`。
- `user_data` 是 Meta 用來把這筆事件對回某個 Meta 使用者的資料。`fbp`、`fbc` 從請求帶上來的 cookie 讀，`client_ip_address` 與 `client_user_agent` 從下單那一次請求的 header 讀，這四個欄位原樣送出；email、電話這類個人資料要先依 Meta 規定的方式正規化（去空白、轉小寫等），再做 SHA-256 雜湊才送。給的欄位越多，Events Manager 顯示的事件比對品質（Event Match Quality）越高。

請求要帶 Meta 發給這個 Pixel 的 access token，這個 token 只能放在伺服器上：放進前端程式碼等於公開，任何人都能用它往這個 Pixel 灌假事件。前端憑證會被提取的機制見 [Client-side SDK 認證的根本限制](/monitoring/07-security-privacy/client-sdk-authentication/)。`user_data` 裡雜湊過的 email 仍然是可以對回個人的資料，送出前的同意與用途說明照 [GDPR 最小化原則的工程落地](/monitoring/07-security-privacy/gdpr-minimization/) 的原則處理。

## 兩路並送時的去重規則

Meta 建議 Pixel 與 Conversions API 並用：Pixel 送得到的時候帶著完整的瀏覽器資訊，送不到的那些由伺服器補上。兩條路徑都送成功的事件會被 Meta 收到兩次，所以 Meta 用兩個欄位判斷是不是同一筆：Pixel 的 `eventID` 與伺服器的 `event_id` 相同、且兩邊的事件名稱相同。依 Meta 文件，去重只在同一個 `event_id` 第一次送達後的 48 小時內生效；兩筆幾乎同時抵達時 Meta 保留瀏覽器那一筆；48 小時內沒有收到瀏覽器那一筆時，伺服器那一筆照常計入。

這條規則決定了 `event_id` 要在哪裡產生：在事件的源頭產生一次，再同時交給前端與後端。訂單編號符合這個條件，前後端都拿得到同一個值：感謝頁從訂單資料讀出編號放進 `fbq` 的第四個引數，伺服器在建立訂單時用同一個編號送 Conversions API。兩邊各自產生一個隨機 UUID 是常見的錯法，兩個值永遠對不上，每一筆轉換都會被算兩次，廣告後台的轉換數膨脹而沒有任何錯誤訊息。

Meta 另有一種用 `event_name` 加 `fbp` 或 `external_id` 比對的去重方式，文件註明它通常只在瀏覽器那一筆先到、伺服器那一筆後到的順序下有效，所以只當作 `event_id` 的備援。

去重的道理與自架 collector 處理 SDK 重送是同一件事：重送的事件要靠一個在源頭就決定的 ID 才認得出來，見 [端到端資料完整性](/monitoring/04-collector/data-integrity/)。

## 用 Test Events 驗證送出的事件

Events Manager 在每個 Pixel 底下有 Test Events 頁面，它即時列出這個 Pixel 收到的事件、來源是瀏覽器還是伺服器、以及去重的結果。兩條路徑的驗證方式不同：

- **瀏覽器端**：在 Test Events 頁面輸入網站網址開啟，或在瀏覽器裝 Meta Pixel Helper 擴充功能，操作一次購買流程，確認 `Purchase` 出現且帶著 `value`、`currency` 與 `eventID`。
- **伺服器端**：Test Events 頁面會給一組測試代碼，伺服器送 Conversions API 時在請求裡加上 `test_event_code` 欄位，那批事件就會出現在測試視窗裡。正式上線前要把這個欄位拿掉；帶測試代碼的事件會不會計入正式報表，以 Events Manager 當下的說明為準。

驗證去重時兩條路徑一起跑：同一筆測試訂單在 Test Events 裡應該看到瀏覽器與伺服器各一筆，並標示其中一筆被去重。只看到一筆時，先確認另一條路徑確實沒送，還是 `event_id` 對不上而被當成兩筆不同的事件。

## 和自架事件追蹤並存的資料流

接了 Pixel 與 Conversions API 之後，同一個業務事件（一筆購買）會往三個地方送：自己的 collector、Meta 的瀏覽器端、Meta 的伺服器端。業務事件的定義只寫一次，送往各家時各自做名稱與欄位的對映，比在各個埋點位置分別呼叫三家的 API 好維護，改一個欄位不必找遍三種呼叫。這個分流結構與它的保留期、PII 取捨，在 [監控資料的雙重用途](/monitoring/telemetry-data-dual-use/) 有完整的推導。

本篇描述的瀏覽器端行為可以在 [Meta Pixel 實測頁](/monitoring/vendors/meta-pixel-lab/) 按按鈕觸發、對照它實際送出的請求與 cookie。追蹤碼要由誰、用什麼流程放上網站，是另一層的決定。行銷團隊常用 tag manager 自行加 Pixel，那條路徑的約定與治理見 [Google Tag Manager](/monitoring/vendors/google-tag-manager/)。Pixel 的資料集屬於哪一個商家資產管理組合、建立之後能不能轉給另一個組合，以及委託代理商時資料集該建在誰的組合裡，見 [追蹤資產的歸屬](/monitoring/vendors/tracking-account-ownership/)。
