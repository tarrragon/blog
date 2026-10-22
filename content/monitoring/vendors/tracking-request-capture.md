---
title: "用 Playwright 擷取追蹤碼請求：擷取方式、記錄欄位與各次結果"
date: 2026-10-22
draft: true
description: "以 Playwright 操作 Meta Pixel 與 GTM 實測頁、記錄各家 script 實際送出的請求與 cookie 的方式，結果檔記錄的欄位與它們的用途，以及每一次擷取的時間、瀏覽器與 script 版本"
weight: 5
tags: ["monitoring", "vendor", "playwright", "meta-pixel", "google-tag-manager", "lab"]
---

這篇記錄用 Playwright 在本機操作 [Meta Pixel 實測頁](/monitoring/vendors/meta-pixel-lab/) 與 [Google Tag Manager 實測頁](/monitoring/vendors/google-tag-manager-lab/)、擷取各家追蹤碼實際送出內容的方式與結果。各家 script 由 vendor 自己的伺服器提供、隨時改版，所以本篇的每一份結果都只代表擷取當下的行為，引用時要連同擷取時間與版本資訊一起看。

## 擷取方式：讓瀏覽器自動化操作實測頁

擷取腳本 `scripts/vendor-capture/capture.mjs` 不直接把 vendor 的 script 載入一個空白頁，而是開啟實測頁、照讀者的操作順序按按鈕。這樣擷取到的請求和讀者在實測頁上看到的是同一條路徑：同樣的 `fbq()` 呼叫、同樣的資料層內容，結果可以直接拿來對照實測頁的面板。

腳本在 Meta Pixel 實測頁上依序做的動作是：載入 Pixel 並送 PageView、送 ViewContent、送帶 `eventID` 的 Purchase，再用帶 `fbclid` 參數的網址重新開啟頁面並再載入一次，觀察 `_fbc` 的產生。在 GTM 實測頁上是載入容器、往資料層推 `purchase` 事件。每個動作之後等三秒，讓第三方 script 送完請求、寫完 cookie。

和實測頁面板相比，Playwright 從瀏覽器的網路層記錄請求，所以拿得到面板拿不到的三樣資訊：POST 請求的 body、回應的狀態碼與標頭、以及帶 `HttpOnly` 旗標而 `document.cookie` 讀不到的 cookie。

## 結果檔記錄的欄位

每次擷取寫出一份 JSON，檔名是 vendor 名稱加上 UTC 擷取時間（例如 `meta-pixel-20261022T0445Z.json`），放在 `scripts/vendor-capture/results/`。欄位分成三組：

- **重現條件**：`capturedAt`（UTC）與 `capturedAtTaipei`、`browser`（Chromium 版本）、`userAgent`、`labUrl`、使用的 Pixel 或容器 ID。結果和這些條件綁在一起才有意義，換一個瀏覽器版本或 vendor 改版之後，同一個動作可能送出不同的參數。
- **vendor 版本線索**：`requests` 裡 `fbevents.js`、`gtm.js` 那幾筆的回應標頭（`last-modified`、`etag`、`date`），以及 `vendorRuntime.fbqVersion`。`fbqVersion` 在 Meta 基本碼裡先被設成 `2.0`，`fbevents.js` 載入後是否覆寫成實際版本由 Meta 決定，所以判斷 script 有沒有改版以回應標頭為主。
- **觀察對象**：`steps`（每個動作之後實測頁狀態列的文字）、`requests`（每一筆跨網域請求的方法、網址、查詢參數、POST body、狀態碼）、`cookies`（追蹤 cookie 的名稱、值、網域、到期時間與旗標）、`vendorRuntime.dataLayer`（GTM 實測時資料層的完整內容）。

## 執行擷取的指令

```bash
# 擷取 Meta Pixel：--id 填測試用 Pixel 的 ID
node scripts/vendor-capture/capture.mjs --vendor meta-pixel --id <Pixel ID>

# 擷取 GTM：--id 填測試用容器的 ID（GTM- 開頭）
node scripts/vendor-capture/capture.mjs --vendor gtm --id <GTM-容器ID>

# 改測本機 build：先 make site 並啟動測試用的靜態伺服器，再把 --url 指到本機的實測頁
node scripts/vendor-capture/capture.mjs --vendor meta-pixel --id <Pixel ID> \
  --url http://localhost:4173/blog/monitoring/vendors/meta-pixel-lab/
```

`--vendor` 決定開哪一個實測頁、照哪一組動作操作。`--id` 是要填進實測頁欄位的 ID，用測試專用的 Pixel 與容器，擷取送出的事件才不會混進正式的廣告報表。`--url` 省略時開正式站的實測頁；`--out` 可以把結果檔寫到別的目錄。本機安裝的 Chromium 版本與 `@playwright/test` 要求的不符時，用環境變數 `PW_CHROMIUM_PATH` 指定瀏覽器執行檔的路徑。

執行環境要能連到 `connect.facebook.net`、`www.facebook.com`、`www.googletagmanager.com` 與各家代碼用到的網域。連不到的時候腳本照樣跑完並寫出結果檔，`steps` 會顯示 script 載入失敗、`requests` 裡那幾筆帶 `failure` 欄位，這份結果記錄的是「在這個網路環境下被擋下」，不是 vendor 的行為，不收進〈各次擷取的結果〉一節。

## 各次擷取的結果

（尚未擷取。第一次擷取完成後依時間由新到舊列在這裡，每一次寫明擷取時間、瀏覽器版本、vendor script 的版本線索，以及和實測頁、兩篇機制文對照之後的觀察。）
