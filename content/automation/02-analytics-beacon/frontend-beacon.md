---
title: "前端 beacon 與 CORS 障礙"
date: 2026-07-06
description: "靜態站用瀏覽器送瀏覽事件到 Apps Script 時，為什麼要用 sendBeacon 送 text/plain 才不會被 CORS preflight 擋下"
weight: 1
tags: ["automation", "beacon", "sendbeacon", "cors", "hugo", "javascript"]
---

前端 beacon 的責任是：在頁面載入時偵測「這一頁被看了」，把一則最小事件送到 Apps Script 的接收端，而且不能拖慢頁面、不能因為送失敗而影響閱讀。做對這件事的關鍵，是選一種**不會觸發 CORS preflight** 的送出方式——這是靜態站打 Apps Script 最容易卡住的地方，先講清楚為什麼。

## CORS preflight 為什麼會擋住 beacon

瀏覽器對跨網域的請求有一套安全機制。當網頁（你的 blog，網域 A）要送一個請求到另一個網域（Apps Script，網域 B），而這個請求「不夠單純」時，瀏覽器會先偷偷送一個 `OPTIONS` 請求去問網域 B：「我等一下要送這種請求，你允許嗎？」這個預先詢問叫 **preflight**。要等網域 B 回答允許，真正的請求才會送出。

Apps Script 在這裡有一個結構性的問題：它的 web app **無法回應 `OPTIONS` 請求**。原因是 Apps Script 只有 `doGet` 和 `doPost` 兩個進入點，沒有 `doOptions`；preflight 送來的 `OPTIONS` 打不到你的程式，Apps Script 平台直接用預設方式回應，而那個回應不帶「我允許」的 CORS 標頭。於是 preflight 失敗、真正的請求根本沒送出。這就是「我照 API 教學寫了 `fetch` 打 Apps Script，瀏覽器 console 一片 CORS 紅字」的根本原因——問題不在你的程式，在於 preflight 發生在你的程式被執行**之前**，你沒有機會處理它。

避開的方法是讓請求「夠單純」，單純到瀏覽器判定不需要 preflight。這種請求叫 **simple request**，條件之一是 `Content-Type` 必須是 `text/plain`、`application/x-www-form-urlencoded` 或 `multipart/form-data` 其中之一。關鍵就在這：**只要用 `text/plain` 送，就不會有 preflight**，請求直接送達，Apps Script 的 `doPost` 正常收到。用 `application/json` 送則會觸發 preflight、然後失敗。

## 用 sendBeacon 送 text/plain

`navigator.sendBeacon` 是瀏覽器為「送出後就不管」這種場景設計的 API，正好適合流量 beacon。它有三個特性剛好對上需求：送出後不阻塞頁面、即使使用者馬上關頁面也保證在背景送完、而且它送出的 `Content-Type` 預設就是 `text/plain`（當你傳字串或 text 型別的 Blob 時）——自動滿足 simple request 條件，不觸發 preflight。

最小可用的 beacon 長這樣：

```javascript
(function () {
  var ENDPOINT = "https://script.google.com/macros/s/你的部署ID/exec";

  var payload = JSON.stringify({
    path: location.pathname,        // 哪一頁
    ref: document.referrer || "",   // 從哪裡連來的
    lang: navigator.language || "", // 瀏覽器語言
  });

  // 用 Blob 明確指定 text/plain，確保是 simple request
  var blob = new Blob([payload], { type: "text/plain;charset=UTF-8" });
  navigator.sendBeacon(ENDPOINT, blob);
})();
```

送出的是一個 JSON **字串**，但外層 `Content-Type` 是 `text/plain`——接收端再自己 `JSON.parse` 把字串還原成物件（模組二的接收端那半會做）。這是「內容是 JSON、但傳輸標成純文字」的常見手法，專門用來繞過 preflight。

payload 刻意只放不涉及個人身分的欄位：看了哪一頁、從哪連來、瀏覽器語言。不送任何能識別個人的資訊。附帶一提，Apps Script 的 web app 收不到訪客的 IP 位址，所以就算你想記 IP 也記不到——這反而讓這套統計在隱私上乾淨很多，時間戳記交給接收端用伺服器時間補（模組二接收端那半處理）。

## 加上閱讀裝置

閱讀裝置（讀者用手機、平板還是桌機看）是一個對排版決策有用的欄位：某篇長表格文章若行動裝置佔比高，就值得回頭檢查它在窄螢幕的可讀性。要在 payload 加這個欄位，關鍵是**只送粗粒度的分類標籤、不送完整 `userAgent`**——`mobile` / `tablet` / `desktop` 這種三選一的標籤足以回答「讀者用什麼裝置」，而完整 `userAgent` 帶著版本、系統等可組成指紋的細節，送它就破壞了前面刻意維持的不記 PII 立場。

分類邏輯在前端從 `navigator.userAgent` 判斷：

```javascript
function deviceType() {
  var ua = navigator.userAgent;
  // iPadOS 的 Safari 會把 userAgent 偽裝成 Mac，靠觸控點數補抓
  var iPadAsMac = /Macintosh/.test(ua) && navigator.maxTouchPoints > 1;
  if (/iPad|Tablet|PlayBook|Silk/.test(ua) || iPadAsMac || (/Android/.test(ua) && !/Mobile/.test(ua))) return "tablet";
  if (/Mobi|iPhone|iPod|Android|BlackBerry|IEMobile|Opera Mini/.test(ua)) return "mobile";
  return "desktop";
}
```

有兩個判斷值得說明，因為它們是「照一般 `userAgent` 教學寫會分錯」的地方。**Android 手機與平板的區分靠 `Mobile` 這個 token**：Android 手機的 `userAgent` 含 `Mobile`、Android 平板不含，所以「有 `Android` 但沒有 `Mobile`」判為平板。**iPad 會偽裝成 Mac**：新版 iPadOS 的 Safari 為了要到桌面版網頁，把 `userAgent` 報成 `Macintosh`，單看字串會把 iPad 誤判成 `desktop`；靠 `navigator.maxTouchPoints > 1`（Mac 桌機沒有觸控）搭配 `Macintosh` 字樣才抓得回來。這類分類規則會隨瀏覽器演進而過時，所以只做粗分類、不追求精確到型號——粗分類容錯高，型號級的判斷維護成本高又容易錯。

把 `dev` 加進 payload：

```javascript
var payload = JSON.stringify({
  path: location.pathname,
  ref: document.referrer || "",
  lang: navigator.language || "",
  dev: deviceType(),   // mobile / tablet / desktop
});
```

接收端多寫一欄就好（模組二接收端那半會補上 `裝置` 欄）。

## 放進 Hugo 的哪裡

這段 JS 要在每一頁都執行，所以放進網站的共用版型、而不是單篇文章。Hugo 的慣例是做一個 partial，在關閉 `</body>` 前引入：

```html
<!-- layouts/partials/beacon.html -->
<script>
  (function () {
    var ENDPOINT = "https://script.google.com/macros/s/你的部署ID/exec";
    function deviceType() {
      var ua = navigator.userAgent;
      var iPadAsMac = /Macintosh/.test(ua) && navigator.maxTouchPoints > 1;
      if (/iPad|Tablet|PlayBook|Silk/.test(ua) || iPadAsMac || (/Android/.test(ua) && !/Mobile/.test(ua))) return "tablet";
      if (/Mobi|iPhone|iPod|Android|BlackBerry|IEMobile|Opera Mini/.test(ua)) return "mobile";
      return "desktop";
    }
    var payload = JSON.stringify({
      path: location.pathname,
      ref: document.referrer || "",
      lang: navigator.language || "",
      dev: deviceType(),
    });
    var blob = new Blob([payload], { type: "text/plain;charset=UTF-8" });
    navigator.sendBeacon(ENDPOINT, blob);
  })();
</script>
```

然後在 baseof 版型的結尾引入它：

```html
<!-- layouts/_default/baseof.html，在 </body> 前 -->
{{ partial "beacon.html" . }}
```

放在 `</body>` 前、而不是 `<head>` 裡，是為了讓 beacon 在頁面主要內容都載入後才送，不跟關鍵資源搶頻寬。`sendBeacon` 本身就不阻塞，這個位置只是讓它更晚一點、更不影響體驗。

一個上線前要注意的邊界：本機 `hugo server` 預覽時 beacon 也會照送，會把你自己開發時的瀏覽混進統計。實務上會加一個判斷，只在正式網域才送——例如檢查 `location.hostname` 是不是你的正式網域，是才執行。這個過濾放哪、怎麼寫，模組五談防濫用與資料乾淨度時一起處理。

## 下一步

前端會送了，但現在 beacon 送出去還沒有人接。接收端要怎麼解析這個 `text/plain` 的 JSON、怎麼安全寫進 Sheet、部署後怎麼確認收到第一筆——見[接收端 handler：寫進第一筆](/automation/02-analytics-beacon/receiver-handler/)。想先補齊 `doPost` 跟部署模型的背景，回[模組一：Apps Script 地基](/automation/01-apps-script-basics/)。
