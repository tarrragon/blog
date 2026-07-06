---
title: "用 Apps Script 幫這個 blog 做流量統計"
date: 2026-07-06
slug: "apps-script-blog-analytics"
description: "GitHub Pages 靜態 blog 不租伺服器做流量統計時，這個 blog 的 Hugo 版型怎麼接 beacon、參數怎麼開關、以及 script 注入的編碼落差"
tags: ["Hugo", "Bear Cub", "apps-script", "analytics", "blog心得"]
---

## 為什麼這個 blog 需要一段 beacon

這個 blog 架在 GitHub Pages 上，是純靜態託管——瀏覽器把頁面抓下來後所有邏輯都在使用者端跑，GitHub 的伺服器不給 access log、也不能執行我的程式碼。這代表「有人來看過哪一頁」這個事實，預設沒有留在任何我查得到的地方。想知道流量、又不想為此租一台主機，唯一的切入點是頁面裡的 JavaScript：讓它在載入時主動送一則瀏覽事件到一個我掌握的接收端。這種請求叫 beacon，接收端這裡用 Google Apps Script、資料存進 Google Sheet。

這篇記錄的是「這個 blog 實際怎麼接線」，延續先前 Hugo + Bear Cub 主題設定的 blog 紀錄脈絡。beacon → Apps Script → Sheet 這套架構背後的通用方法論、選型理由、Google 端的完整部署步驟，整理在[免伺服器自動化實務指南](/automation/)；這裡只講落在本 blog Hugo 版型上的那一段，以及實作時撞到、官方文件不會告訴你的一個編碼落差。

## 版型注入點：baseof 已備好的 custom_body

Bear Cub 主題的 `baseof.html` 在關閉 `</body>` 前留了一個擴充點：

```go-html-template
{{- partial "custom_body.html" . -}}
```

這正是 beacon 該進的地方——放在 body 結尾、頁面主要內容都載入後才送，不跟關鍵資源搶頻寬。做法是在 `layouts/partials/` 建一個 `custom_body.html`，主題會自動引入。這樣 beacon 邏輯集中在一個 partial 裡，不必動主題檔、不必改每一個版型。

## beacon partial 與開關參數

beacon 的網址不寫死在版型裡，而是讀 `hugo.toml` 的一個站台參數。這樣做有兩個好處：網址換部署時只改 config、不動程式；參數留空時 partial 完全不輸出，等於一個乾淨的開關。

`layouts/partials/custom_body.html`：

```go-html-template
{{- with .Site.Params.analyticsBeacon }}
{{- $host := (urls.Parse $.Site.BaseURL).Host }}
<script>
  (function () {
    // 只在正式站送，本機 hugo server 預覽（localhost）不計入統計
    if (location.hostname !== {{ $host }}) return;
    // 粗粒度分類閱讀裝置，只送 mobile / tablet / desktop，不送完整 userAgent
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
      dev: deviceType()
    });
    var blob = new Blob([payload], { type: "text/plain;charset=UTF-8" });
    navigator.sendBeacon({{ . }}, blob);
  })();
</script>
{{- end }}
```

`hugo.toml` 的 `[params]` 加一行，部署好 Apps Script 後把 `/exec` 網址填進來就啟用，留空字串就停用：

```toml
[params]
  # 免伺服器流量統計 beacon：部署 Apps Script web app 後，把 /exec 網址填進來即啟用。
  # 留空字串代表停用（partial 不會輸出任何 script）。
  analyticsBeacon = ''
```

三個設計決定值得說明。**用 `.Site.Params.analyticsBeacon` 當開關**，讓「啟用統計」變成一個 config 動作而非改程式，也讓公開的版型檔裡不出現部署網址。**hostname guard 從 `.Site.BaseURL` 推導**（`urls.Parse` 取 host），而不是寫死字串，換 domain 時不用改 partial；它的作用是讓本機 `hugo server` 預覽時的瀏覽不混進統計——`localhost` 不等於正式 host，beacon 就不送。**送 `text/plain` 而非 `application/json`**，是為了讓這個跨網域請求成為 CORS simple request、不觸發 preflight；Apps Script 的 web app 無法回應 preflight 的 `OPTIONS`，用 JSON 送會被擋，這條雷的細節在[前端 beacon 與 CORS 障礙](/automation/02-analytics-beacon/frontend-beacon/)。

payload 除了路徑、來源、語言，還送一個粗粒度的閱讀裝置標籤 `dev`（`mobile` / `tablet` / `desktop`），讓我知道讀者用什麼裝置看——這對排版決策有用（例如某篇長表格文章若行動裝置佔比高，就值得檢查手機上的可讀性）。分類刻意只送三選一的標籤、不送完整 `userAgent`，維持不記 PII 的一致立場。實作上有個要補的判斷：iPadOS 的 Safari 會把 `userAgent` 偽裝成 Mac 桌機，單看字串會把 iPad 誤判成 `desktop`，得靠 `navigator.maxTouchPoints > 1` 搭配 `Macintosh` 字樣補抓成 `tablet`。

## 實跑撞到的雷：script context 的雙重編碼

第一版的 partial 我在插值上多加了 `jsonify`，想說手動把值轉成 JSON 字串比較保險：

```go-html-template
if (location.hostname !== {{ $host | jsonify }}) return;
navigator.sendBeacon({{ . | jsonify }}, blob);
```

build 出來的結果是壞的：

```javascript
if (location.hostname !== "\"tarrragon.github.io\"") return;
navigator.sendBeacon("\"https://script.google.com/macros/s/.../exec\"", blob);
```

網址被包成 `"\"...\""`——兩層引號。JS 會把「含引號的整串」當成字串值，`sendBeacon` 打的是一個帶引號的壞網址，beacon 靜默失敗。

根因是 Hugo 底層的 Go `html/template` 是 **context-aware** 的：當插值出現在 `<script>` 區塊裡，它會自動把值當 JS 來輸出，字串會被轉成安全的、帶引號且已跳脫的 JS 字串字面量。也就是說 `{{ $host }}` 在 script context 裡本來就會渲染成 `"tarrragon.github.io"`。我再套一層 `jsonify`，等於編碼兩次。正解是**移除 `jsonify`，直接寫 `{{ $host }}` 和 `{{ . }}`**，讓 template 的 context-aware escaping 自己處理——這同時比手動加引號更安全，因為它會針對 script context 正確跳脫。

這種落差官方文件的 fact-check 抓不到：`jsonify` 和 `sendBeacon` 各自的文件都正確，錯在「兩者疊在 script context」這個組合。只有真的 build 出來、看渲染結果才會發現。

## 啟用與驗證

blog 端接好後，啟用一次走三步：

1. 依[免伺服器自動化實務指南](/automation/02-analytics-beacon/receiver-handler/)部署 Apps Script web app，拿到 `/exec` 網址。
2. 把網址填進 `hugo.toml` 的 `analyticsBeacon`，push 讓 GitHub Pages 重建。
3. 打開線上任一頁，回 Google Sheet 看第二列是否出現一筆瀏覽紀錄。

要在本機先確認 partial 有正確渲染、又不真的送出，可以用環境變數覆蓋參數 build，再 grep 產物：

```bash
HUGO_PARAMS_ANALYTICSBEACON="https://script.google.com/macros/s/TESTID/exec" \
  hugo --destination /tmp/hb
grep -n "sendBeacon" /tmp/hb/automation/index.html
```

看到 `navigator.sendBeacon("https://.../exec", blob)` 這種乾淨的字串字面量、而不是帶跳脫引號的版本，就代表注入正確。hostname guard 也會一起出現在同一段，確認 `location.hostname !== "tarrragon.github.io"` 這條有生效。

## 部署前用 curl 直接驗接收端

blog 的 beacon 只在正式站送，所以「等 push 上線再看 Sheet」的驗證回饋很慢。更快的做法是用 curl 模擬一則 beacon、直接打 `/exec`，把 Google 端（部署、`doPost`、寫入）跟 blog 端拆開驗——Google 端通了再談上線：

```bash
URL='https://script.google.com/macros/s/你的部署ID/exec'
curl -sS -L -H "Content-Type: text/plain;charset=UTF-8" \
  --data '{"path":"/test","ref":"","lang":"zh-TW","dev":"desktop"}' "$URL"
# 預期輸出：{"ok":true}，並在 Sheet 多出一筆 /test 列
```

這段 curl 有兩個容易踩錯、值得記住的點。**用 `--data` 觸發 POST，不要加 `-X POST`。** GAS web app 的 POST 成功後會回一個 302、把 `doPost` 的輸出放在跳轉後的 `googleusercontent.com` echo 端點；curl 遇到 302 預設會轉成 GET 去取那個輸出，這是對的。一旦加了 `-X POST`，curl 會強迫連跳轉後都用 POST，打壞 echo 端點、回一個 Google 雲端硬碟的「很抱歉，目前無法開啟這個檔案」錯誤頁——看起來像部署壞了，其實只是測試指令的方法用錯。瀏覽器的 `sendBeacon` 沒這問題，這是 curl 特有的落差。

**302 是成功、不是錯誤。** GAS web app 的 POST 正常就是回 302，`doPost` 在請求打到 `/exec` 的當下已經執行、資料已經寫進 Sheet，跳轉只是去取回應。所以就算 curl 那端因為方法用錯而讀不到 `{"ok":true}`，那一筆其實也已經寫進去了——診斷時先去 Sheet 看有沒有新列，比盯著 curl 的輸出準。

如果連 GET 打 `/exec` 都回「無法開啟檔案」（而不是 GAS 的 `找不到指令碼函式：doGet`），那才是部署層的問題，優先查「誰可以存取」是不是「所有人」。

## 這個 /exec 網址該公開嗎

這個網址必然是公開的，而且非公開不可——它會被寫進每一頁的 client-side JS，任何人檢視原始碼都看得到。這是 client beacon 架構的本質，不是設定失誤；GA、Cloudflare 那些的收集端點也全是公開的。所以安全的問題不是「怎麼把它藏起來」，而是「限制別人拿它能做什麼」。

別人拿到這網址讀不到你的 Sheet：`doPost` 只做 `appendRow` 然後回 `{"ok":true}`，不回傳任何試算表內容，授權範圍也只綁這一張表。真正的風險是騷擾型的兩種——有人直接 POST 垃圾內容污染統計、或狂打端點吃掉執行配額。對沒沒無聞的個人 blog，攻擊者缺乏動機，這兩者機率都很低。要進一步限制破壞範圍（例如 payload 放一個約定 token、`doPost` 對不上就丟掉），屬於[配額與濫用防護](/automation/05-deploy-quota-security/)的層次——注意 token 也在 client JS 裡看得到，它擋隨手亂打、擋不了鐵了心的人。

## 完整方法論

這篇只涵蓋 Hugo 版型這一段。beacon 該送什麼、Apps Script 接收端怎麼寫、Sheets 當資料庫的並發與容量、觸發器怎麼把原始 log 彙總成日報、以及匿名端點的配額與濫用防護，都在[免伺服器自動化實務指南](/automation/)。想把同一套搬到別的靜態站或別的膠水工具（例如 Cloudflare Workers），也從那裡的模組零選型開始。
