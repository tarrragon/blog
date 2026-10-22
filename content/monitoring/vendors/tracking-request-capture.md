---
title: "用 Playwright 擷取追蹤碼請求：擷取方式、記錄欄位與各次結果"
date: 2026-10-22
description: "以 Playwright 操作 Meta Pixel 與 GTM 實測頁、記錄各家 script 實際送出的請求與 cookie 的方式，結果檔記錄的欄位與它們的用途，以及每一次擷取的時間、瀏覽器與 script 版本"
weight: 5
tags: ["monitoring", "vendor", "playwright", "meta-pixel", "google-tag-manager", "lab"]
---

這篇記錄用 Playwright 在本機操作 [Meta Pixel 實測頁](/monitoring/vendors/meta-pixel-lab/) 與 [Google Tag Manager 實測頁](/monitoring/vendors/google-tag-manager-lab/)、擷取各家追蹤碼實際送出內容的方式與結果。各家 script 由 vendor 自己的伺服器提供、隨時改版，所以本篇的每一份結果都只代表擷取當下的行為，引用時要連同擷取時間與版本資訊一起看。

## 擷取方式：讓瀏覽器自動化操作實測頁

擷取腳本 `scripts/vendor-capture/capture.mjs` 不直接把 vendor 的 script 載入一個空白頁，而是開啟實測頁、照讀者的操作順序按按鈕。這樣擷取到的請求和讀者在實測頁上看到的是同一條路徑：同樣的 `fbq()` 呼叫、同樣的資料層內容，結果可以直接拿來對照實測頁的面板。

腳本在 Meta Pixel 實測頁上依序做的動作是：載入 Pixel 並送 PageView、送 ViewContent、送帶 `eventID` 的 Purchase，再用帶 `fbclid` 參數的網址重新開啟頁面並再載入一次，觀察 `_fbc` 的產生。在 GTM 實測頁上是載入容器、往資料層推 `purchase` 事件。每個動作之後等三秒，讓第三方 script 送完請求、寫完 cookie。

和實測頁面板相比，Playwright 從瀏覽器的網路層記錄請求，所以拿得到面板拿不到的三樣資訊：POST 請求的 body、回應的狀態碼與標頭、以及帶 `HttpOnly` 旗標而 `document.cookie` 讀不到的 cookie。

腳本預設以無頭模式（headless）啟動 Chromium，這時瀏覽器的 User-Agent 帶 `HeadlessChrome` 字樣。實測時 Meta Pixel 的 `fbevents.js` 在無頭模式下照樣載入、照樣寫 cookie，事件請求卻一筆都不送出；同一個無頭瀏覽器只把 User-Agent 換成一般 Chrome 的字串，事件就送出了，所以 `fbevents.js` 依 User-Agent 判斷要不要送。Pixel 設定檔裡出現一個名為 `botblocking` 的外掛，名稱與這個行為相符，但沒有直接證據顯示過濾是它做的。GA4 在無頭模式下照常送出。所以擷取 Meta Pixel 要加 `--headed`，讓 Playwright 開一個有視窗的瀏覽器操作實測頁。腳本不改寫 User-Agent，有視窗的瀏覽器仍然是自動化控制的瀏覽器，Meta 之後若加入其他偵測條件，同一個指令的結果可能改變，這也是每份結果要記下擷取模式的理由。

## 結果檔記錄的欄位

每次擷取寫出一份 JSON，檔名是 vendor 名稱加上 UTC 擷取時間（例如 `meta-pixel-20261022T0445Z.json`），放在 `scripts/vendor-capture/results/`。欄位分成三組：

- **重現條件**：`capturedAt`（UTC）與 `capturedAtTaipei`、`browser`（Chromium 版本）、`userAgent`、`headless`（這次是否以無頭模式執行）、`labUrl`、使用的 Pixel 或容器 ID。結果和這些條件綁在一起才有意義，換一個瀏覽器版本或 vendor 改版之後，同一個動作可能送出不同的參數。
- **vendor 版本線索**：`requests` 裡 `fbevents.js`、`gtm.js` 那幾筆的回應標頭（`last-modified`、`etag`、`date`）與 `body` 欄位（script 本體的位元組數與 SHA-256），以及 `vendorRuntime.fbqVersion`。`fbqVersion` 在 Meta 基本碼裡先被設成 `2.0`，`fbevents.js` 載入後是否覆寫成實際版本由 Meta 決定，所以判斷 script 有沒有改版以回應標頭與本體雜湊為主。`gtm.js` 的回應實測不帶 `last-modified` 與 `etag`，比對 GTM 只能靠本體雜湊；而 `gtm.js` 的內容由容器設定與 Google 的執行環境一起產生，雜湊變了之後要再到 GTM 後台的版本紀錄查容器那段期間有沒有發布，才分得出是哪一邊改的。
- **觀察對象**：`steps`（每個動作之後實測頁狀態列的文字）、`requests`（每一筆跨網域請求的方法、網址、查詢參數、POST body、狀態碼）、`cookies`（追蹤 cookie 的名稱、值、網域、到期時間與旗標）、`vendorRuntime.dataLayer`（GTM 實測時資料層的完整內容）。

`requests` 裡同時有 `status` 與 `failure` 的那一筆，代表瀏覽器已經收到伺服器的回應、之後 Playwright 才把請求記成失敗。GA4 送往 `g/collect` 的請求是這個樣子：另外用 Chrome DevTools Protocol 的網路事件對照同一個操作，瀏覽器在中止之前已收到伺服器的 204，事件有送達。`status` 為 `null` 而帶 `failure` 的才是沒有送出去的請求。

## 執行擷取的指令

```bash
# 擷取 Meta Pixel：--id 填測試用 Pixel 的 ID
node scripts/vendor-capture/capture.mjs --vendor meta-pixel --id <Pixel ID>

# 擷取 GTM：--id 填測試用容器的 ID（GTM- 開頭）
node scripts/vendor-capture/capture.mjs --vendor gtm --id <GTM-容器ID>

# 改測本機 build：先 make site 並啟動測試用的靜態伺服器，再把 --url 指到本機的實測頁
node scripts/vendor-capture/capture.mjs --vendor meta-pixel --id <Pixel ID> \
  --url http://localhost:4173/blog/monitoring/vendors/meta-pixel-lab/

# 以有視窗的瀏覽器擷取：Meta Pixel 在無頭模式下不送事件，要記錄事件請求就加 --headed
node scripts/vendor-capture/capture.mjs --vendor meta-pixel --id <Pixel ID> --headed
```

`--vendor` 決定開哪一個實測頁、照哪一組動作操作。`--id` 是要填進實測頁欄位的 ID，用測試專用的 Pixel 與容器，擷取送出的事件才不會混進正式的廣告報表。`--url` 省略時開正式站的實測頁；`--out` 可以把結果檔寫到別的目錄；`--headed` 不帶值，加上它就以有視窗的瀏覽器執行，執行期間螢幕上會開一個 Chromium 視窗、跑完自動關閉。本機安裝的 Chromium 版本與 `@playwright/test` 要求的不符時，用環境變數 `PW_CHROMIUM_PATH` 指定瀏覽器執行檔的路徑。

Pixel ID 填錯時沒有任何錯誤訊息：`www.facebook.com/tr/` 對任何 ID 都回 200，`signals/config/<ID>` 對不存在的 ID 也回 200，內容是一個只有 `/* empty plugin */` 的設定檔。確認 ID 的方法是看結果檔裡 `signals/config` 那一筆之後有沒有對應的外掛被載入，或直接在事件管理工具的資料集頁面讀 ID。商家設定頁網址裡的 `selected_asset_id` 是設定頁內部的資產編號，與 Pixel ID 不同。

執行環境要能連到 `connect.facebook.net`、`www.facebook.com`、`www.googletagmanager.com` 與各家代碼用到的網域。連不到的時候腳本照樣跑完並寫出結果檔，`steps` 會顯示 script 載入失敗、`requests` 裡那幾筆帶 `failure` 欄位，這份結果記錄的是「在這個網路環境下被擋下」，不是 vendor 的行為，不收進〈各次擷取的結果〉一節。

## 各次擷取的結果

每一次擷取依時間由新到舊列在這裡，寫明擷取時間、瀏覽器版本、vendor script 的版本線索，以及和實測頁、兩篇機制文對照之後的觀察。

### 2026-10-23 01:26（台北）：Meta Pixel，有視窗的瀏覽器

擷取時間是 UTC 2026-10-22 17:26:10，瀏覽器是 Playwright 提供的 Chromium 148.0.7778.96（macOS、arm64）以 `--headed` 執行，User-Agent 不帶 `HeadlessChrome`；實測頁開在本機 build。Pixel 是測試用的資料集，建立時沒有勾選把資料集連到轉換 API 的選項，所以 Meta 那一端沒有另一條伺服器端路徑。結果檔是 `scripts/vendor-capture/results/meta-pixel-20261022T1726Z.json`。

版本線索：`fbevents.js` 本體 435,058 位元組，SHA-256 開頭是 `6f3aa7a0d8d9`；`fbq.version` 是 `2.9.427`，`signals/config` 請求的查詢參數同樣帶 `v=2.9.427`、`r=stable`。這個 Pixel 的設定檔裡出現 26 個外掛名稱，其中與本篇觀察相關的是 `cookie`、`inferredevents` 與 `botblocking`，名稱分別對應寫 cookie、自動事件與機器人流量。不存在的 ID 拿到的設定檔裡一個外掛都沒有。

**事件請求的形式。** 每一筆事件都是向 `www.facebook.com/tr/` 送出的 POST，參數放在表單 body 裡，`rqm=formPOST`；Playwright 把這些請求的資源類型記成 `document`，因為 `fbevents.js` 是在一個隱藏的 iframe 裡提交表單。`ev` 是事件名稱，ViewContent 的 `cd[content_name]`、Purchase 的 `cd[value]` 與 `cd[currency]` 是 `fbq('track', …)` 第二個參數的內容，Purchase 的 `eid` 是第三個參數帶的 `eventID`，[Meta Pixel 與 Conversions API](/monitoring/vendors/meta-pixel-conversions-api/) 的去重一節靠的就是這個值。

**Pixel 自己加送的事件。** 每按一次實測頁的按鈕，`fbevents.js` 都在實測頁呼叫的事件旁邊多送一筆 `SubscribedButtonClick`，兩筆在同一毫秒送出。這筆事件不是實測頁呼叫的，內容是被點的按鈕文字（`cd[buttonText]` 是「送 ViewContent」）、按鈕的 DOM 特徵（`cd[buttonFeatures]`）與頁面特徵（`cd[pageFeatures]`）。網站沒有寫任何程式，按鈕文字就送到了 Meta，盤點一個網站送出哪些資料時要把這一類算進去。

**cookie 與參數的對應。** `_fbp` 的值是 `fb.0.` 接毫秒時間戳與一串隨機數，每一筆事件的 `fbp` 參數都帶著它。帶 `fbclid` 重新開啟頁面之後多了 `_fbc`，值是 `fb.0.` 接毫秒時間戳與 `fbclid` 的原值，那一次的 PageView 同時帶 `fbp` 與 `fbc` 兩個參數。兩個 cookie 都由 JavaScript 寫入（`httpOnly` 為 false）、`SameSite=Lax`，到期時間是擷取時間起算 90 天。

**`o` 參數。** 每一筆事件都帶 `o=4126`。`fbevents.js` 原始碼裡把它定義成一組旗標的位元和，4126 拆開是 `FIRST_PARTY_COOKIES`、`AUTO_CONFIG`、`CONFIG_LOADING`、`SUPPORTS_DEFINE_PROPERTY` 與 `SUPPORTS_SEND_BEACON`。另一個參數 `coo` 在原始碼裡記錄的是免程式碼事件設定（codeless）是否被關閉，與 cookie 無關。

### 2026-10-23 01:23（台北）：Meta Pixel，無頭模式

擷取時間是 UTC 2026-10-22 17:23:23，瀏覽器是 Chromium headless shell 148.0.7778.96，其餘條件與上一則相同，只差在沒有加 `--headed`。結果檔是 `scripts/vendor-capture/results/meta-pixel-20261022T1723Z.json`。

`fbevents.js` 與 `signals/config` 都載入成功，`_fbp` 與 `_fbc` 照樣寫入，向 `www.facebook.com/tr/` 的事件請求一筆都沒有：PageView、ViewContent、Purchase 都停在瀏覽器裡。同樣的實測頁、同樣的 Pixel 改用有視窗的瀏覽器就送得出去，所以差別落在無頭模式本身。實測頁狀態列顯示「fbevents.js 已載入」，從頁面上看不出事件沒送，這是 [Meta Pixel 與 Conversions API](/monitoring/vendors/meta-pixel-conversions-api/) 列的瀏覽器端損失路徑之外的另一種：script 載入成功、cookie 也寫了，事件在送出之前被 script 自己丟掉。

### 2026-10-23 00:45（台北）：GTM 容器只帶一個 GA4 代碼

擷取時間是 UTC 2026-10-22 16:45:30，瀏覽器是 Playwright 提供的 Chromium headless shell 148.0.7778.96（macOS、arm64），實測頁開在本機 build（`http://localhost:4173/blog/monitoring/vendors/google-tag-manager-lab/`）。容器是測試用容器，發布的版本裡只有一個 Google Analytics 代碼，觸發條件是 Initialization - All Pages，沒有任何以 `purchase` 為名的自訂事件觸發條件。結果檔是 `scripts/vendor-capture/results/gtm-20261022T1645Z.json`。

版本線索：`gtm.js` 的回應本體 546,027 位元組，SHA-256 開頭是 `b970456b1ca6`；回應標頭只有 `content-type`、`date` 與 `cache-control: private, max-age=900`。

**載入容器之後送出的請求。** 瀏覽器先向 `www.googletagmanager.com` 取得 `gtm.js?id=<容器 ID>`（200），約 0.1 秒後由容器裡的 GA4 代碼向 `www.google-analytics.com/g/collect` 送出一筆 POST（204）。這一筆的事件資料全部放在網址的查詢參數裡，POST body 是空的：`tid` 是評估 ID，`en=page_view` 是事件名稱，`dl` 與 `dt` 是頁面網址與標題。`dl` 記錄的網址沒有連接埠號，實測頁實際開在 4173 埠。

**GA4 代碼寫下的 cookie。** 一筆 `page_view` 之後，這個網域多出兩個 cookie。`_ga` 的值是 `GA1.1.` 接兩段數字，這兩段數字與 collect 請求的 `cid` 參數相同，GA4 用它辨識同一個瀏覽器。第二個 cookie 的名稱是 `_ga_` 接上評估 ID 去掉 `G-` 的部分，值記錄這個瀏覽器在這個資源下的工作階段，`s` 之後的時間戳與 collect 請求的 `sid` 參數相同。兩個 cookie 都由 JavaScript 寫入（`httpOnly` 為 false）、`SameSite=Lax`，到期時間是擷取時間起算 400 天。

**往資料層推 purchase 事件之後。** `window.dataLayer` 依序是實測頁推的 `gtm.js`、容器自己推的 `gtm.dom` 與 `gtm.load`，以及按鈕推的 `purchase`（帶 `order_id`、`value`、`currency`）。推入 `purchase` 之後沒有新的請求：這個容器裡沒有以 `purchase` 觸發的代碼，那一筆只留在陣列裡。這是 [Google Tag Manager](/monitoring/vendors/google-tag-manager/) 的資料層一節描述的分工在網路層的樣子，網站推什麼事件由前端決定，事件會不會變成送往某一家的請求由容器的設定決定。要讓購買事件送到 GA4，容器要另加一個 GA4 事件代碼，以名稱為 `purchase` 的自訂事件觸發條件啟動它。

**Playwright 對 collect 請求的記錄。** Playwright 把 `g/collect` 那一筆記成 `requestfailed`（`net::ERR_ABORTED`），而 Chrome DevTools Protocol 的網路事件顯示瀏覽器在中止之前已收到 204；這一筆是 script 以 fetch 送出的請求。結果檔因此同時帶 `status: 204` 與 `failure`，判讀方式見〈結果檔記錄的欄位〉。請求清單裡另有一筆 `cdn.jsdelivr.net` 的 Mermaid script，那是本站每一頁都會載入的資源，與 GTM 無關。
