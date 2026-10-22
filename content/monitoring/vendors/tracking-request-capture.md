---
title: "用 Playwright 擷取追蹤碼請求：擷取方式、記錄欄位與各次結果"
date: 2026-10-22
description: "以 Playwright 操作 Meta Pixel 與 GTM 實測頁、記錄各家 script 實際送出的請求與 cookie 的方式，結果檔記錄的欄位與它們的用途，擷取用的測試帳號，以及每一次擷取觀察到的事件請求形式、cookie 與請求參數的對應、無頭瀏覽器下的差異與 script 自動送出的事件"
weight: 5
tags: ["monitoring", "vendor", "playwright", "meta-pixel", "google-tag-manager", "lab"]
---

這篇記錄用 Playwright 在本機操作 [Meta Pixel 實測頁](/monitoring/vendors/meta-pixel-lab/) 與 [Google Tag Manager 實測頁](/monitoring/vendors/google-tag-manager-lab/)、擷取各家追蹤碼實際送出內容的方式與結果。下文的「擷取腳本」指本站寫的 Playwright 程式 `scripts/vendor-capture/capture.mjs`（在本站的公開 repo [tarrragon/blog](https://github.com/tarrragon/blog) 裡），「script」指服務商（vendor）提供、在頁面上執行的 JavaScript（`fbevents.js`、`gtm.js`）。各家 script 由服務商自己的伺服器提供、隨時改版，所以本篇的每一份結果都只代表擷取當下的行為，引用時要連同擷取時間與版本資訊一起看。

## 擷取方式：讓瀏覽器自動化操作實測頁

擷取腳本不直接把服務商的 script 載入一個空白頁，而是開啟實測頁、照讀者的操作順序按按鈕。這樣擷取到的是和讀者在實測頁上觸發的同一組 JavaScript 呼叫：同樣的 `fbq()` 呼叫、同樣的資料層（dataLayer，頁面上供 GTM 讀取事件的全域陣列 `window.dataLayer`，定義見 [Google Tag Manager](/monitoring/vendors/google-tag-manager/) 的資料層一節）內容，結果可以拿來對照實測頁的面板（實測頁上列出操作紀錄、跨網域請求與追蹤 cookie 的區塊）。

擷取腳本在 Meta Pixel 實測頁上依序做的動作是：載入 Pixel 並送 PageView、送 ViewContent、送帶 `eventID` 的 Purchase，再把 `fbclid` 參數加進網址重新開啟頁面並再載入一次 Pixel，觀察 `_fbc` cookie 的產生。在 GTM 實測頁上是載入容器、按實測頁的「往資料層推 purchase 事件」按鈕。每個動作之後等三秒，讓 script 送完請求、寫完 cookie。

實測頁的面板用瀏覽器的 Resource Timing 列出跨網域請求，Playwright 則直接監看瀏覽器送出的每一個請求，所以擷取結果多了面板拿不到的資訊：POST 請求的 body、回應的狀態碼與標頭、帶 `HttpOnly` 旗標而 `document.cookie` 讀不到的 cookie，以及面板根本列不出來的請求。Meta Pixel 的事件請求就是最後一種：`fbevents.js` 以隱藏的表單把事件提交到一個 iframe，這類提交不進父頁面的 Resource Timing，所以實測頁面板上只看得到 `fbevents.js` 與它的設定檔，看不到任何一筆事件；在 Playwright 的紀錄與瀏覽器開發者工具的 Network 面板裡看得到。

擷取腳本預設以無頭模式（headless）啟動 Chromium，這時瀏覽器的 User-Agent 帶 `HeadlessChrome` 字樣。實測時 Meta Pixel 在無頭模式下照樣載入、照樣寫 cookie，事件請求卻一筆都不送出，原因在 Pixel 的設定檔（`signals/config/<Pixel ID>`）帶來的 `botblocking` 外掛（plugin）：依擷取當時那一版設定檔的原始碼，這個外掛拿 `navigator.userAgent` 比對一份機器人規則清單，清單裡有 `HeadlessChrome/`，比對成功時由這個外掛在事件送出之前把它攔下（外掛程式碼裡對應的訊息字串是 `[Meta pixel] Bot traffic detected and blocked`）。`fbevents.js` 本體也偵測 `HeadlessChrome`，但只把結果寫進事件請求的 `o` 參數。

兩組對照支持這個歸因，都沒有存成結果檔。作者在 Playwright 的瀏覽器設定裡只把 User-Agent 換成一般 Chrome 的字串、其餘照舊以無頭模式執行，事件就送出了，這證明結果取決於 User-Agent，但 `fbevents.js` 本體同樣讀 User-Agent，單靠這一組分不出攔截的是外掛還是本體。另一組來自一次填錯 Pixel ID 的擷取：同樣是無頭模式，不存在的 ID 拿到的設定檔一個外掛都沒有，向 `www.facebook.com/tr/` 的事件請求卻照樣送出（那次是 GET，`o` 參數含 `IS_HEADLESS`），所以本體偵測到無頭模式之後並沒有攔截，攔截來自設定檔帶來的外掛。那份結果檔因為 ID 填錯而刪除了。GTM 容器裡的 GA4 代碼在無頭模式下照常送出事件請求。依 User-Agent 辨識自動化流量是通用的做法，本站自己的流量統計怎麼分辨機器流量見 [辨識自動化流量](/automation/06-reading-the-data/automated-traffic/)。

所以擷取 Meta Pixel 要加 `--headed`，讓 Playwright 開一個有視窗的瀏覽器操作實測頁。擷取腳本不改寫 User-Agent，有視窗的瀏覽器仍然是自動化控制的瀏覽器，Meta 之後若加入其他偵測條件，同一個指令的結果可能改變，這也是每份結果要記下擷取模式的理由。

## 擷取結果檔（JSON）的欄位

擷取腳本每次執行寫出一份 JSON，檔名是服務商名稱加上 UTC 擷取時間（例如 `meta-pixel-20261022T1726Z.json`），放在 `scripts/vendor-capture/results/`。欄位分成三組：

- **重現條件**：`capturedAt`（UTC）與 `capturedAtTaipei`、`browser`（Chromium 版本）、`userAgent`、`headless`（這次是否以無頭模式執行）、`labUrl`、使用的 Pixel 或容器 ID。`headless` 欄位從 2026-10-23 01:26 那一次擷取起才有，01:23 與 00:45 兩份結果沒有這個欄位，看 `userAgent` 有沒有 `HeadlessChrome`。結果和這些條件綁在一起才有意義，換一個瀏覽器版本或服務商改版之後，同一個動作可能送出不同的參數。
- **script 的版本線索**：`requests` 裡 `fbevents.js`、`gtm.js` 那幾筆的 `body` 欄位（script 本體的位元組數與 SHA-256）與回應標頭，以及 `vendorRuntime.fbqVersion`（頁面上 `fbq.version` 的值）。實測兩家的回應都不帶 `last-modified` 與 `etag`，所以讀結果的人判斷 script 有沒有改版，以本體雜湊為主。`fbq.version` 在網站安裝的 Pixel 基本碼（base code）裡先被設成 `2.0`，`fbevents.js` 載入後覆寫成實際版本。`gtm.js` 的內容由容器設定與 Google 提供的 GTM 執行時程式碼（runtime）一起產生，雜湊變了之後要再到 GTM 後台的版本紀錄查容器那段期間有沒有發布，才分得出是哪一邊改的。
- **觀察對象**：`steps`（每個動作之後實測頁狀態訊息列的文字）、`requests`（每一筆跨網域請求的方法、網址、查詢參數、POST body、狀態碼）、`cookies`（追蹤 cookie 的名稱、值、網域、到期時間與旗標）、`vendorRuntime.dataLayer`（GTM 實測時資料層的完整內容）。

判讀 `requests` 時，`status` 是主要訊號。瀏覽器收到回應之後才被中止的請求，Playwright 會觸發失敗事件，擷取腳本在失敗事件裡也讀取已收到的回應，所以結果檔同時記下 `status` 與 `failure`，這時以 `status` 為準：請求送達了。本篇的擷取裡只有 GA4 的 `g/collect` 出現這個組合，00:45 那一則記錄了它與作者用 Chrome DevTools Protocol 做的對照。`status` 為 `null` 而帶 `failure` 的，是沒有收到回應的請求。

## 擷取用的測試帳號

擷取用的 Pixel 與 GTM 容器都是測試專用的資產，各自放在只放實測資產的擁有者底下：Meta 另開一個商家資產管理組合，GTM 與 GA4 各另開一個帳戶。這樣安排的理由見 [追蹤資產的歸屬](/monitoring/vendors/tracking-account-ownership/)。建立時三家的檢查與預設值會影響擷取結果，記在這裡：

- **Meta 對組合名稱有檢查**：`vendor-lab-test` 與 `Tarragon` 兩個名稱都被退回，錯誤訊息是組合名稱必須如實反映商家，`Tarragon Tech Notes` 通過。Meta 的說明頁只寫組合名稱要和商家對外使用的名稱一致、不能有特殊字元，沒有列出退件的判斷條件；錯誤訊息附的連結是粉絲專頁的命名守則，其中一條是名稱不能只由一個統稱用詞組成（守則舉的例子是「披薩」），`Tarragon` 是香草的英文名稱，與這一條相符。GTM 與 GA4 這次以 `vendor-lab-test` 當帳戶名稱，都直接建立成功。
- **Meta 的建立流程詢問要不要把既有的粉絲專頁加入新組合**，預設不勾選。Meta 資料集不需要粉絲專頁，這次略過。
- **Meta 資料集的建立表單有一個預設勾選的選項**，表單上的說明是勾選之後，組合裡現有與日後新建的每一個資料集都會連結到 Meta 的 Conversions API（轉換 API），搭配 Pixel 把網站事件也送到 Meta 的伺服器端。這個選項由 Meta 那一端代為處理伺服器端的傳送，與 [Meta Pixel 與 Conversions API](/monitoring/vendors/meta-pixel-conversions-api/) 描述的、由網站自己的伺服器呼叫 Conversions API 是不同的設置方式。擷取要觀察的是瀏覽器端送出的內容，這次取消勾選，所以測試 Pixel 沒有伺服器端的事件來源。
- **GA4 建立帳戶時，四個資料共用選項有三個預設勾選**（「根據輸入內容和業務洞察資料建立模型」「技術支援」「依據您業務性質提供的建議」），這次全部取消；GTM 帳戶的匿名資料共用選項預設不勾選。

Pixel ID 在事件管理工具（Events Manager）的資料集頁面讀，商家設定頁網址裡的 `selected_asset_id` 是設定頁內部的資產編號，與 Pixel ID 不同；GTM 容器 ID（`GTM-` 開頭）顯示在 GTM 後台工作區頁面的上方。

## 執行擷取的指令

指令都在 repo 的根目錄執行。第一次執行前，先裝好 Node.js，安裝 repo 的相依套件（`@playwright/test` 與 `http-server`）與 Playwright 用的 Chromium：

```bash
# 取得擷取腳本與實測頁的原始碼
git clone https://github.com/tarrragon/blog.git && cd blog

# 安裝相依套件與 Playwright 的 Chromium；沒有裝 Chromium 時，第一次執行會出現 Executable doesn't exist
npm ci
npx playwright install chromium
```

擷取指令本身：

```bash
# 擷取 Meta Pixel：--id 填測試用 Pixel 的 ID，--headed 讓事件請求送得出去
node scripts/vendor-capture/capture.mjs --vendor meta-pixel --id <Pixel ID> --headed

# 擷取 GTM：--id 填測試用容器的 ID（GTM- 開頭）
node scripts/vendor-capture/capture.mjs --vendor gtm --id <GTM-容器ID>

# 改測本機建置的網站：先建置網站並啟動靜態伺服器，再把 --url 指到本機的實測頁
make site
mkdir -p .test-www && ln -sfn ../public .test-www/blog
npx http-server .test-www -p 4173 -s &
node scripts/vendor-capture/capture.mjs --vendor meta-pixel --id <Pixel ID> --headed \
  --url http://localhost:4173/blog/monitoring/vendors/meta-pixel-lab/
node scripts/vendor-capture/capture.mjs --vendor gtm --id <GTM-容器ID> \
  --url http://localhost:4173/blog/monitoring/vendors/google-tag-manager-lab/
```

擷取腳本依 `--vendor`（`meta-pixel` 或 `gtm`）決定開哪一個實測頁、照哪一組動作操作。`--id` 是要填進實測頁欄位的 ID，用測試專用的 Pixel 與容器，擷取送出的事件才不會混進正式的廣告報表；兩個 ID 去哪裡讀，見〈擷取用的測試帳號〉一節的最後一段。省略 `--url` 時，擷取腳本開正式站的實測頁；加 `--out <目錄>` 時，擷取腳本把結果檔寫到那個目錄；`--headed` 不帶值，加上它就以有視窗的瀏覽器執行，執行期間螢幕上會開一個 Chromium 視窗、跑完自動關閉。本篇的擷取都在有桌面的 macOS 上執行，沒有顯示器的環境（例如沒有桌面的 Linux 伺服器）開不了有視窗的瀏覽器，本篇沒有驗證那種環境的做法。

擷取腳本啟動的 Chromium 由 `@playwright/test` 的版本決定；沒有跑過 `npx playwright install chromium`、或 Playwright 升級之後，執行時會出現 `Executable doesn't exist at …` 這個錯誤。這時重跑安裝指令，或用環境變數 `PW_CHROMIUM_PATH` 指定本機已有的 Chromium 執行檔，例如 `PW_CHROMIUM_PATH=<Chromium 執行檔路徑> node scripts/vendor-capture/capture.mjs …`。

改測本機那幾行指令裡，`make site` 用 Hugo 把網站建置到 `public/`，接著用 `npx pagefind` 產生站內搜尋的索引（這一步要連網下載 pagefind）；建置前要先裝好 Hugo，並以 `git submodule update --init --recursive` 拉下網站的佈景主題。本站的網址前綴是 `/blog/`，所以把 `public/` 以符號連結掛在 `.test-www/blog` 底下，再用 `http-server` 從 `.test-www` 提供檔案，網址才會和正式站的路徑結構一致。`4173` 是 `http-server` 監聽的連接埠，與 `--url` 裡的埠號要一致，換成其他未被占用的埠號時兩處一起改；網站的網址前綴不是 `/blog/` 時，`.test-www` 底下的資料夾名稱與 `--url` 的路徑一起改。`-s` 讓 `http-server` 不輸出每一筆存取紀錄，結尾的 `&` 讓它在背景執行，擷取完用 `kill %1` 停掉它。

Pixel ID 填錯時沒有任何錯誤訊息：Meta 的伺服器對不存在的 ID 也回應 `signals/config/<ID>` 的請求（狀態碼 200），內容是一個只有 `/* empty plugin */` 的設定檔，`fbevents.js` 照樣送出事件。確認 ID 的方法是看結果檔裡 `signals/config` 那一筆回來的設定檔有沒有外掛，或直接在事件管理工具的資料集頁面讀 ID。

執行環境（跑擷取腳本的那台機器）要能連到 `connect.facebook.net`、`www.facebook.com`、`www.googletagmanager.com` 與各家 script 用到的網域。連不到的時候擷取腳本照樣跑完並寫出結果檔，`steps` 會顯示 script 載入失敗，`requests` 裡向那些網域的請求帶 `failure` 欄位；這時結果檔反映的是網路環境，不是服務商 script 的行為。

## 各次擷取的結果

這一節收錄服務商的 script 實際載入、請求有回應的擷取，依時間由新到舊排列，每一則寫明擷取時間、瀏覽器版本、script 的版本線索，以及和實測頁、[Meta Pixel 與 Conversions API](/monitoring/vendors/meta-pixel-conversions-api/)、[Google Tag Manager](/monitoring/vendors/google-tag-manager/) 兩篇機制文對照之後的觀察。網路被擋下的擷取不收，理由在〈執行擷取的指令〉一節的最後一段。

### 2026-10-23 01:26（台北）：Meta Pixel，有視窗的瀏覽器

擷取時間是 UTC 2026-10-22 17:26:10，瀏覽器是 Playwright 提供的 Chromium 148.0.7778.96，在 macOS 上以 `--headed` 執行，User-Agent 不帶 `HeadlessChrome`；實測頁開在本機建置的網站。Pixel 是〈擷取用的測試帳號〉一節建立的測試 Meta 資料集。結果檔是 `scripts/vendor-capture/results/meta-pixel-20261022T1726Z.json`。

版本線索：`fbevents.js` 本體 435,058 位元組，SHA-256 開頭是 `6f3aa7a0d8d9`；`fbq.version` 是 `2.9.427`，`signals/config` 請求的查詢參數同樣帶 `v=2.9.427`、`r=stable`。這個 Pixel 的設定檔裡出現 26 個外掛名稱，與本篇觀察相關的是 `cookie`（寫 `_fbp` 與 `_fbc`）、`inferredevents`（自動事件）與 `botblocking`（機器人流量）；不存在的 ID 拿到的設定檔裡一個外掛都沒有。

**事件請求的形式。** 每一筆事件都是向 `www.facebook.com/tr/` 送出的 POST，參數放在表單 body 裡，`rqm=formPOST`。`fbevents.js` 建立一個隱藏的表單，把它提交到一個 iframe，所以 Playwright 把這些請求記成 `document` 類型（`resourceType`），實測頁面板也因此列不出它們。`ev` 是事件名稱；`fbevents.js` 把 `fbq('track', …)` 的第三個引數（事件參數物件）轉成 `cd[...]` 參數，例如 ViewContent 的 `cd[content_name]`、Purchase 的 `cd[value]` 與 `cd[currency]`，第四個引數帶的 `eventID` 轉成 `eid`。網站同時從瀏覽器與伺服器送同一筆事件時，Meta 用 `eid` 把兩邊去重，機制見 [Meta Pixel 與 Conversions API](/monitoring/vendors/meta-pixel-conversions-api/) 的去重一節；這次的測試 Pixel 沒有伺服器端的事件來源，`eid` 只出現在瀏覽器端這一路。

**Pixel 自動加送的事件。** Pixel 載入之後，每按一次實測頁的按鈕，`fbevents.js` 都在實測頁呼叫的事件之外多送一筆 `SubscribedButtonClick`，依兩筆請求的 `ts` 參數，相差不到 10 毫秒。這筆事件由 `fbevents.js` 讀取被點的按鈕之後自動產生，內容是按鈕文字（`cd[buttonText]` 是「送 ViewContent」）、按鈕的 DOM 特徵（`cd[buttonFeatures]`）與頁面特徵（`cd[pageFeatures]`）。網站開發者沒有為按鈕寫任何追蹤程式，按鈕文字就由 `fbevents.js` 送到了 Meta；盤點一個網站送出哪些資料時，要把 Pixel 自動加送的事件算進去。載入 Pixel 的那一下按鈕沒有對應的 `SubscribedButtonClick`，那時 `fbevents.js` 還沒載入。

**cookie 與參數的對應。** `_fbp` 的值是 `fb.0.` 接毫秒時間戳與一串隨機數，每一筆事件的 `fbp` 參數都帶著這個值。帶 `fbclid` 重新開啟頁面之後多了 `_fbc`，值是 `fb.0.` 接毫秒時間戳與 `fbclid` 的原值，那一次的 PageView 同時帶 `fbp` 與 `fbc` 兩個參數，另外還有一個 `fbcs` 參數，原始碼裡它與 `fbc` 寫在同一組點擊 ID 的處理裡，本篇沒有進一步確認它記錄的內容。兩個 cookie 都由 `fbevents.js` 以 JavaScript 寫入（`httpOnly` 為 false）、`SameSite=Lax`，到期時間是擷取時間起算 90 天。

**`o` 參數。** 這一次的每一筆事件都帶 `o=4126`。`fbevents.js` 原始碼裡把 `o` 定義成一組旗標的位元和，4126 拆開是 `FIRST_PARTY_COOKIES`、`AUTO_CONFIG`、`CONFIG_LOADING`、`SUPPORTS_DEFINE_PROPERTY` 與 `SUPPORTS_SEND_BEACON`。原始碼裡另有一個 `IS_HEADLESS` 旗標，在無頭模式下加進 `o`；01:23 那次無頭擷取沒有送出任何事件，所以沒有 `o` 值可以對照。另一個參數 `coo` 在原始碼裡記錄的是免程式碼事件設定（codeless）是否被關閉，不是 cookie 的設定。

### 2026-10-23 01:23（台北）：Meta Pixel，無頭模式

擷取時間是 UTC 2026-10-22 17:23:23，瀏覽器是 Chromium 148.0.7778.96 的無頭模式；Pixel、實測頁與操作順序與 01:26 那次以 `--headed` 執行的擷取相同，差別只在沒有加 `--headed`。結果檔是 `scripts/vendor-capture/results/meta-pixel-20261022T1723Z.json`。

版本線索：`fbevents.js` 本體的位元組數與 SHA-256、`fbq.version` 都與 01:26 那一次相同，兩次擷取用的是同一版 script，差別只來自擷取模式。

`fbevents.js` 與 `signals/config` 都載入成功，`_fbp` 與 `_fbc` 照樣寫入，向 `www.facebook.com/tr/` 的事件請求一筆都沒有：PageView、ViewContent、Purchase 都沒有送出。差別來自無頭模式的 User-Agent 帶 `HeadlessChrome`，攔下事件的是 Pixel 設定檔帶來的 `botblocking` 外掛，機制見〈擷取方式〉一節。實測頁狀態訊息列顯示「fbevents.js 已載入」，從頁面上看不出事件沒送。[Meta Pixel 與 Conversions API](/monitoring/vendors/meta-pixel-conversions-api/) 列的瀏覽器端損失路徑裡，script 被廣告攔截器擋下時網站還有機會察覺載入失敗；這一次是 script 載入成功、cookie 也寫了，事件在送出之前被設定檔帶來的外掛攔下。

### 2026-10-23 00:45（台北）：GTM 容器只帶一個 GA4 代碼

擷取時間是 UTC 2026-10-22 16:45:30，瀏覽器是 Playwright 提供的 Chromium 148.0.7778.96 的無頭模式（collect 請求的 `uaa=arm`、`uab=64` 顯示是 macOS arm64），實測頁開在本機建置的網站（`http://localhost:4173/blog/monitoring/vendors/google-tag-manager-lab/`）。GTM 容器是〈擷取用的測試帳號〉一節建立的測試容器，發布的版本裡只有一個 Google Analytics 代碼（tag），觸發條件（trigger）是 Initialization - All Pages，沒有任何以 `purchase` 為名的自訂事件觸發條件。代碼與觸發條件的定義見 [Google Tag Manager](/monitoring/vendors/google-tag-manager/) 講 GTM 責任的那一節。結果檔是 `scripts/vendor-capture/results/gtm-20261022T1645Z.json`。

版本線索：`gtm.js` 的回應本體 546,027 位元組，SHA-256 開頭是 `b970456b1ca6`；回應標頭只有 `content-type`、`date` 與 `cache-control: private, max-age=900`。

**載入容器之後送出的請求。** 瀏覽器先向 `www.googletagmanager.com` 取得 `gtm.js?id=<容器 ID>`（200），約 0.1 秒後由容器裡的 GA4 代碼向 `www.google-analytics.com/g/collect` 送出一筆 POST（204）。這一筆 collect 請求的事件資料全部放在網址的查詢參數裡，POST body 是空的：`tid` 是評估 ID（Measurement ID），`en=page_view` 是事件名稱，`dl` 與 `dt` 是頁面網址與標題。`dl` 記錄的網址沒有連接埠號，實測頁實際開在 4173 埠，所以在本機用不同埠號測試時，GA4 報表上的頁面網址看不出是哪一個埠號的伺服器送來的。

**GA4 代碼寫下的 cookie。** 一筆 `page_view` 之後，實測頁所在的網域（這次是 `localhost`）多出兩個 cookie。`_ga` 的值是 `GA1.1.` 接兩段數字，這兩段數字與 collect 請求的 `cid` 參數相同，GA4 用它辨識同一個瀏覽器。另一個 cookie 的名稱是 `_ga_` 接上評估 ID 去掉 `G-` 的部分，值記錄這個瀏覽器在這個 GA4 資源（property）下的工作階段，`s` 之後的時間戳與 collect 請求的 `sid` 參數相同。兩個 cookie 都由 GA4 代碼以 JavaScript 寫入（`httpOnly` 為 false）、`SameSite=Lax`，到期時間是擷取時間起算 400 天。

**往資料層推 purchase 事件之後。** `window.dataLayer` 依序是實測頁推的 `gtm.js`、容器自己推的 `gtm.dom` 與 `gtm.load`，以及實測頁的「往資料層推 purchase 事件」按鈕推的 `purchase`（帶 `order_id`、`value`、`currency`）。推入 `purchase` 之後沒有新的請求，成因是這個容器裡沒有以名稱為 `purchase` 的自訂事件觸發條件啟動的 GA4 事件代碼，那一筆只留在陣列裡。[Google Tag Manager](/monitoring/vendors/google-tag-manager/) 的資料層一節描述的分工，在網路請求上就是這個樣子：網站推什麼事件由前端決定，事件是否變成送往某一家的請求由容器的設定決定。

**Playwright 對 collect 請求的記錄。** Playwright 把 `g/collect` 那一筆記成 `requestfailed`（`net::ERR_ABORTED`）。作者在這次擷取之後另外用 Chrome DevTools Protocol 的網路事件對照同一個操作，瀏覽器在中止之前已收到 204，事件有送達；那次對照沒有存成結果檔。結果檔因此同時帶 `status: 204` 與 `failure`，判讀以 `status` 為準，見〈擷取結果檔（JSON）的欄位〉。請求清單裡另有一筆 `cdn.jsdelivr.net` 的 Mermaid script，那是本站每一頁都會載入的資源，與 GTM 無關。
