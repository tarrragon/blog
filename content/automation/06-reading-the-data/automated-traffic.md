---
title: "辨識自動化流量"
date: 2026-08-03
description: "接收端讀不到 HTTP 標頭、無從得知請求來自誰時，在前端蒐集訊號分辨機器抓取與真人閱讀"
weight: 3
tags: ["automation", "beacon", "bot-detection", "user-agent", "apps-script", "data-quality"]
---

辨識自動化流量的責任是在統計裡把機器抓取與真人閱讀分開。這件事的必要性隨著內容累積而上升——搜尋引擎的渲染爬蟲、AI 檢索爬蟲、社群平台的連結預覽、監控服務都會執行頁面上的 JavaScript，因此都會觸發 beacon。它們與真人在資料上完全混在一起，而未分離的統計會系統性高估閱讀量。

這一章的作法受到一個結構限制的支配，先講清楚那個限制，因為它決定了所有訊號只能從哪裡來。

## 接收端讀不到請求標頭

Apps Script 的 `doPost(e)` 事件物件提供 `parameter`、`parameters`、`queryString`、`contentLength`、`postData`、`pathInfo` 這幾個欄位，**不提供任何 HTTP 標頭**。這代表接收端拿不到 `User-Agent`，也拿不到來源 IP。

傳統的伺服器端 bot 過濾（比對 UA 字串、查 IP 反解、比對已知爬蟲的 IP 區段）在這個架構下全部不可用。所有判斷素材必須由前端蒐集之後放進 payload 送出——這既是限制，也界定了設計空間：**能用的訊號只有瀏覽器環境暴露給 JavaScript 的那些**。

這個限制連帶產生一個必須守住的界線。前端能取得完整的 `userAgent`、螢幕尺寸、時區、字型清單，把它們全部送出確實能提高辨識率，但那正好構成[瀏覽器指紋](/automation/knowledge-cards/browser-fingerprint/)——為了分辨機器而蒐集足以識別個人的資料，取捨方向是錯的。後面的每個訊號都在「有判別力」與「不構成指紋」之間取值。

## 訊號分層與信心度

四個訊號的可靠度不同，分開記錄而不是合併成單一結論。

| 訊號        | 來源                            | 信心 | 誤判方向                      |
| ----------- | ------------------------------- | ---- | ----------------------------- |
| `webdriver` | `navigator.webdriver === true`  | 高   | 幾乎不會誤判真人              |
| `ua`        | UA 字串比對自我申報的機器人名稱 | 高   | 抓不到偽裝者，但不誤判真人    |
| `lang`      | `navigator.languages` 為空      | 中   | 隱私擴充功能的真人可能命中    |
| `size`      | `window.outerWidth` 為 0        | 中   | 部分嵌入式 webview 的真人是 0 |

**`navigator.webdriver` 是自動化框架的預設標記。** Playwright、Puppeteer、Selenium 啟動的瀏覽器這個值都是 `true`，一般瀏覽器是 `false`。它的判別力很強而誤判極少，代價是刻意規避偵測的工具第一件事就是把它蓋掉——因此它抓得到的是「沒有隱藏身分意圖」的自動化訪客。

**UA 比對抓的是自我申報。** 搜尋引擎與正派的 AI 檢索爬蟲會在 `User-Agent` 裡寫明自己是誰，這是它們與網站經營者之間的慣例。比對這個字樣不會誤判真人，因為真人的瀏覽器不會自稱是爬蟲。

**空語言清單與零視窗尺寸是環境特徵而非身分宣告。** 無頭瀏覽器沒有實際的視窗外框，語言偏好也常常是空的。這兩個訊號的價值在於它們抓得到隱藏了前兩項的工具，代價是真人也可能命中——裝了隱私擴充功能的瀏覽器會回報空語言清單，嵌在 app 裡的 webview 可能沒有視窗尺寸。

因為誤判方向不同，**記錄下來的是命中了哪些訊號、而不是一個布林結論**：

```javascript
function botSignal() {
  var hits = [];
  try {
    if (navigator.webdriver === true) hits.push("webdriver");
    // UA 比對見下一節
    if (!navigator.languages || navigator.languages.length === 0) hits.push("lang");
    if (!window.outerWidth || !window.outerHeight) hits.push("size");
  } catch (err) {
    // 偵測本身出錯不該影響統計，當作沒有訊號
  }
  return hits.join(",");
}
```

這個設計讓**判定閾值留在彙總端**。日後發現某條訊號誤判太多，在試算表改公式就好，不必改前端重新部署——而前端一旦部署出去，快取的頁面還會用舊版跑一段時間。

## 具名比對與通用退回

UA 比對要回答的問題有兩層：「這是不是機器」以及「是哪一隻機器」。後者的價值在於處置方向不同——搜尋引擎索引與 AI 檢索是內容被看見的證據，社群平台的連結預覽代表有人分享了連結，而不具名的抓取工具才是需要留意的那一類。

直覺的作法是列一份已知爬蟲的名單做精確比對。這個作法單獨使用時有一個不會顯現的失效模式：**名單一定會過時，而過時的表現是新出現的爬蟲完全不被標記**——統計上呈現為自動化流量比例逐漸下降，而這個下降與「內容吸引到更多真人」在數字上不可區分。

因此比對分成兩層，讓過時的代價落在精度而非覆蓋：

```javascript
// 已知爬蟲的自我申報名稱，命中時送出具體名稱
var KNOWN_BOTS = /claudebot|gptbot|oai-searchbot|chatgpt-user|perplexitybot|googlebot|google-extended|bingbot|applebot|duckduckbot|yandexbot|bytespider|amazonbot|ccbot|meta-externalagent|facebookexternalhit|semrushbot|ahrefsbot|dotbot|petalbot/i;
// 通用字樣，接住誠實申報但不在具名清單裡的自動化訪客
var GENERIC_BOT = /bot\b|crawler|spider|headless|slurp|bingpreview|python-requests|curl\//i;

var ua = navigator.userAgent || "";
var named = ua.match(KNOWN_BOTS);
var generic = named ? null : ua.match(GENERIC_BOT);
if (named) hits.push("ua:" + named[0].toLowerCase());
else if (generic) hits.push("ua:" + generic[0].toLowerCase().replace(/[^a-z]+$/, ""));
```

兩層的比對來源不同是關鍵：具名層比對的是身分（清單裡的名字），通用層匹配的是類別詞（`bot`、`crawler`、`spider`），後者不需要知道任何一隻爬蟲的名字就能運作。清單過時時，新爬蟲仍然被通用層接住、標記成 `ua:bot` 之類——失去的是「知道是誰」，不是「知道有」。

這個結構還帶來一個可觀測性：**退回層的命中比例上升，代表清單該更新了**。這把「清單過時」從一件不可見的事變成一個可以看的數字，而且不需要有人事先知道漏了哪些新爬蟲。抽象層的原則見 [#251 清單過時的代價要落在精度、不落在覆蓋](/report/stale-list-costs-precision-not-coverage/)。

只送出命中的關鍵字、不送完整 `userAgent`，是前面那條界線的具體落實——那個關鍵字本來就是爬蟲主動公開申報的身分，不構成指紋特徵。

## 行為訊號比宣告訊號難偽裝

前面四個訊號都是環境屬性，而環境屬性可以被修改。真正難以規避的是行為留下的痕跡，因為改變行為會犧牲抓取工具自己的效率。

**離開事件缺席是其中最強的一個。** 抓取工具取得頁面內容後直接終止瀏覽器環境，不會經歷「頁面轉為不可見」這個狀態轉換，因此不產生離開事件。真人的離開幾乎必定觸發它——切換分頁、關閉頁面、切換 app 都會。

實務上還會遇到相反的形態：**只有離開事件、沒有進入事件**。這來自抓取工具的網路攔截設定——許多框架只放行文件與必要資源，把頁面載入期間的其他請求擋掉；等內容抓完、進入關閉流程時攔截器已經解除，離開事件就送得出去。這種「孤兒離開事件」在真人流量裡不會出現。

**停留時間的分佈也會洩漏排程。** 抓取工具的頁面存活時間由設定決定，因此高度一致——相隔數小時、來自不同識別碼的多列，停留秒數卻精確相同，這個整齊度在真人流量裡不會出現。搭配互動旗標為 0，判定就相當確定。

## 標記而非丟棄

偵測到疑似自動化流量時有兩種處置：前端直接不送，或照常記錄並加上標記欄位。

**照常記錄的理由是判定規則需要可校正。** 前端直接不送的資料完全消失，無從得知誤判率、也無從回頭調整規則；標記則讓判定與使用分離，彙總時決定要不要排除，而規則寫錯了可以回頭校正。代價是試算表多存一些列，以及彙總時必須記得過濾。

對免費配額敏感、或流量大到列數成為問題時，取捨會反過來——那時應該只丟棄高信心訊號（`webdriver` 與具名 UA）命中的部分，中信心訊號仍然照常記錄。

彙總端的分類邏輯把訊號與行為組合起來：

```text
=IFS(
  AND(事件="leave", 同session同路徑的view筆數=0), "爬蟲-孤兒離開事件",
  事件<>"view", "",
  REGEXMATCH(訊號欄, "webdriver|ua"), "爬蟲-高信心",
  同session的leave筆數=0, "爬蟲-疑似",
  訊號欄<>"", "訊號弱-待觀察",
  同session的view筆數=1, "單頁即走",
  TRUE, "真人")
```

條件的順序承載語意。**孤兒離開事件必須排在最前面**，否則第二條會把所有離開事件留白，那一整類流量就在統計裡消失了。**非進入事件留白**避免同一次瀏覽被計數兩次。**弱訊號要搭配行為才升級**——`lang` 或 `size` 單獨命中時歸為待觀察而非判定為爬蟲，因為它們的誤判方向指向真人。

最後那條 `TRUE` 分支不只是語法要求。它讓沒有被任何條件接住的列顯示成具體標籤而非留白——留白與「不適用」在視覺上不可區分，而一個會被看見的標籤才有機會促使人去查為什麼。

## 下一步

訊號齊備之後，統計的可信度取決於整條收集鏈是否健康。判定規則寫對了但公式算錯、程式改了但端點沒生效、錯誤訊息指向的位置不是問題的位置——這些情況的診斷見[假故障與靜默失效的診斷](/automation/06-reading-the-data/diagnosing-silent-failures/)。防濫用與配額的完整討論在[模組五](/automation/05-deploy-quota-security/quota-abuse-privacy/)。
