# 載入擴充功能、注入本機頁、用標記判斷跑的是哪一版

本 reference 給以 Playwright 實際載入擴充功能來驗證的做法：全新載入一份建置、讓 content script 注入本機測試頁、開啟擴充功能頁、讀 service worker、停掉 service worker，以及判斷跑的是哪一版程式的標記與正對照。

## 全新載入一份建置

每次測試都全新載入，content script 與 service worker 就一定是當下的建置（它們只在載入時讀檔，見 `chrome-extension-dev-loop` skill）。

1. 把建置輸出複製到暫存目錄，不直接載入使用者瀏覽器正在用的那個資料夾：測試期間改的檔案、加的 manifest 設定會影響使用者的瀏覽器。
2. 以持久 context 載入副本：

   ```js
   const { chromium } = require('playwright')
   const ctx = await chromium.launchPersistentContext('', {
     channel: 'chromium',
     headless: true,
     args: [`--disable-extensions-except=${extDir}`, `--load-extension=${extDir}`]
   })
   const sw = ctx.serviceWorkers()[0] || await ctx.waitForEvent('serviceworker', { timeout: 15000 })
   const extId = new URL(sw.url()).host
   ```

   `extDir` 是副本的絕對路徑。`channel: 'chromium'` 用 Playwright 附的 Chromium，它的新版 headless 模式可以載入擴充功能；`launchPersistentContext` 的第一個引數給空字串，代表用暫存的使用者資料目錄。
3. 測完 `await ctx.close()`。

## 讓 content script 注入本機測試頁

content script 只注入 manifest `content_scripts[].matches` 列出的網址。要在不連外、不登入的情況下驗證注入與訊息往返：

1. 在副本的 `manifest.json` 的 `content_scripts[0].matches` 加上 `http://127.0.0.1/*`。這個改動在載入之前做，不是要測的變因。
2. 用 Node 的 `http.createServer` 在 `127.0.0.1` 的隨機埠開一個回傳簡單 HTML 的伺服器。
3. `page.goto('http://127.0.0.1:<port>/')`，等一兩秒讓 content script 注入。

真實網站才有的 DOM 結構（例如書城的書籍清單）在本機頁上沒有，依賴那些結構的流程照樣要在使用者的瀏覽器上驗證。

## 開啟擴充功能頁

`page.goto(\`chrome-extension://${extId}/<頁面路徑>\`)`，例如 popup 的 HTML 路徑。這是真的擴充功能頁，`chrome.*` API 都是真的；要控制 API 的回應（例如模擬「在某個網站上」），改用 `popup-state-rendering.md` 的假 API 渲染。

## 用標記判斷跑的是哪一版

要知道某段程式是新版還是舊版，在檔案尾端加一行標記，再從外面讀：

| 位置 | 加在檔案尾端 | 讀法 |
|------|------------|------|
| content script | `document.documentElement.setAttribute('data-cs-marker', 'v2')` | `page.evaluate(() => document.documentElement.getAttribute('data-cs-marker'))`；content script 與頁面共用 DOM |
| service worker | `self.__swMarker = 'v2'` | `worker.evaluate(() => self.__swMarker)` |
| 擴充功能頁 | `window.__pageMarker = 'v2'` | 開啟頁面後 `page.evaluate(() => window.__pageMarker)` |

## 停掉 service worker 並確認它停過

```js
const cdp = await ctx.newCDPSession(page)
const statuses = []
cdp.on('ServiceWorker.workerVersionUpdated', (e) => {
  for (const v of e.versions) if (v.scriptURL.includes(extId)) statuses.push(v.runningStatus)
})
await cdp.send('ServiceWorker.enable')
await cdp.send('ServiceWorker.stopAllWorkers')
```

`page` 是任一個已開啟的分頁。之後開啟一個擴充功能頁、呼叫 `chrome.runtime.sendMessage` 就會喚醒 worker。只看 Playwright 的 worker 物件判不出它停過：停掉再喚醒後拿到的可能還是同一個物件。`statuses` 出現 `stopped` 再出現 `starting`、`running`，才算真的停過再喚醒。

## 正對照

結論是「讀到舊版」或「沒有反應」時，加一組正對照：用同一份改過的檔案全新載入擴充功能，確認讀得到新標記。正對照讀不到新標記，代表標記沒寫進去或讀法錯了，前面的結果不能用。正對照不能用 `chrome.runtime.reload()` 做，理由見 SKILL.md〈限制〉。
