# 用假的 chrome API 渲染 popup 的各個狀態

本 reference 給「不靠真實網站與背景服務，把 popup 切到每一個狀態並截圖」的做法：以 `file://` 開啟建置輸出的 popup HTML，在頁面載入前注入假的 `chrome` 物件，再呼叫 popup 程式掛在 `window` 上的函式切狀態。用途是改版前後的畫面比對、元素清單比對與版面檢查；它驗的是畫面，不驗 popup 與背景、content script 之間的真實通訊。

## 假的 chrome 物件

用 `page.addInitScript(stubSource)` 在 popup 程式執行之前注入。只放 popup 實際用到的 API，形狀要跟 MV3 一致：

- **不傳 callback 時回傳 Promise**：MV3 的 `chrome.tabs.query`、`chrome.storage.local.get`、`chrome.runtime.sendMessage` 不傳 callback 時回傳 Promise。假物件只支援 callback 時，`await chrome.storage.local.get(...)` 會丟錯或永遠等待；單元測試的 mock 也是同一回事。
- **初始化握手要回應**：popup 初始化時常先向 service worker 要狀態。假的 `runtime.sendMessage` 永遠不回應，popup 會停在初始化、走不到判斷分頁的那一步，所有狀態看起來都一樣。讓它回應一個成功的狀態物件（例如 `{ success: true }`）。
- **分頁網址可設定**：`tabs.query` 回傳的分頁網址決定 popup 判斷「在哪個網站、哪一頁」，每個狀態給一個網址。
- **content script 的回應可設定**：`tabs.sendMessage` 依狀態設成成功回應、拒絕（`Promise.reject(new Error('Could not establish connection'))`，模擬 content script 還沒注入），或永遠不回應。模擬「連線中」要用拒絕，因為 popup 的連線中處理通常寫在 catch 裡，永遠不回應走不到那條路。
- **導覽與關閉不真的發生**：`tabs.create`、`tabs.update` 記到 `window.__navigations`，`window.close` 改成設旗標，測試可以讀出 popup 要去哪裡。

## 切到每一個狀態

1. 每個狀態開一個新分頁：`browser.newPage({ viewport: { width: <popup 寬>, height: 600 }, deviceScaleFactor: 2 })`。600 是 Chrome popup 的最大高度，高度超過時截圖看得出要捲動。
2. 注入假物件、`page.goto('file://<建置輸出>/<popup 路徑>')`，等初始化跑完（約 1 秒）。
3. 需要時呼叫 popup 程式掛在 `window` 上的函式切狀態（例如更新狀態、顯示錯誤）。popup 程式沒有把要用的函式掛到 `window` 時，在它既有的「供測試使用」區塊補上，不另開一條測試專用的路徑。
4. 截圖，並記錄可見元素的 id 清單與 `document.documentElement.scrollWidth`、`scrollHeight`：id 清單用來比對改版前後有沒有元素消失，`scrollWidth` 大於視窗寬度代表水平溢出。
5. 收集 `pageerror` 事件；任何一個狀態有 page error，截圖不算數。

## 檢查截圖

- 截完先確認每個狀態的情境判斷對了（例如讀 `document.body.dataset` 上的情境屬性），再看畫面。情境全部相同時，通常是假物件沒有回應初始化握手。
- 多張截圖拼成一張檢視時，先把拼圖用的 HTML 寫成檔案再用 `page.goto('file://…')` 開啟；用 `page.setContent` 載入的頁面讀不到 `file://` 圖片。
- 改版前後各跑一次同一支腳本，比對 id 清單：改版前有、改版後沒有的 id，要確認程式裡沒有地方再找它。
