# 用假的 chrome API 渲染擴充功能頁的各個狀態

本 reference 給「不靠真實網站與背景服務，把擴充功能自己的頁面切到每一個狀態並截圖」的做法：以 `file://` 開啟建置輸出的頁面 HTML，在頁面載入前注入假的 `chrome` 物件，再呼叫頁面程式掛在 `window` 上的函式，或操作頁面本身，切到要看的狀態。〈假的 chrome 物件〉〈切到每一個狀態〉〈檢查截圖〉以 popup 為例；清單頁、設定頁這類從 storage 讀資料、內容很長的擴充功能頁，另外照〈popup 以外的擴充功能頁〉。用途是改版前後的畫面比對、元素清單比對與版面檢查；這個做法驗證的對象是畫面，不是頁面與背景、content script 之間的真實通訊。

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

## popup 以外的擴充功能頁

清單頁、設定頁這類頁面多半在載入時從 `chrome.storage.local` 讀資料、內容可以很長，跟 popup 的差別在視窗、資料與捲動：

- **視窗尺寸**：這類頁面開在一般分頁裡，〈切到每一個狀態〉第 1 步的 popup 寬度與 600 的高度上限不適用。用桌機的寬高（例如 1280×800）截一次，再用窄寬（例如 390）截一次看響應式版面。
- **資料從假的 storage 給**：假物件的 `storage.local.get` 照 MV3 的語意回傳：字串或陣列回傳測試資料裡那幾個 key；物件回傳物件裡的每一個 key，測試資料沒有的用物件給的預設值；`null` 或不帶引數回傳整份測試資料。同樣在不傳 callback 時回傳 Promise；`onChanged` 給一個不做事的 `addListener`。每個狀態給一份資料：有資料、空的、會觸發特殊顯示的那幾種（缺欄位的舊格式、沒有圖片的項目）。測試資料的形狀取自實際寫進 storage 的資料：用 `chrome-extension-dev-loop` skill 的唯讀片段匯出一份樣本當底稿；舊格式照舊版程式實際寫下的值，空字串與缺欄位分開各給一份，手寫時很容易把兩者寫成同一種。
- **只顯示特定協定圖片的頁面**：頁面為了安全只顯示 http(s) 網址的圖片時，測試資料裡用 `data:` 網址的圖片會全部被當成沒有圖片。測試資料改寫成假的 https 網址（`https://covers.test/<n>.svg`），再用 `page.route('https://covers.test/**', route => route.fulfill({ contentType: 'image/svg+xml', body: <svg> }))` 回應；這樣有圖片與沒有圖片的兩種顯示都看得到。
- **捲動後的狀態只截視窗範圍**：sticky 工具列、「回到頂部」這類只在捲動之後出現的東西，要先 `window.scrollTo(0, <位置>)`（位置取視窗高度的兩到三倍，越過「捲過約一個畫面才出現」這類門檻），等捲動事件與轉場跑完（等目標元素可見，或等一個 `requestAnimationFrame` 加上轉場時間）再截圖，而且截視窗範圍（不加 `fullPage`）。`fullPage` 截圖把整頁畫進一張，`position: fixed` 與 `sticky` 的元素只出現在它們在頁首時的位置，遮罩只蓋到第一個視窗高度，捲動後才有的狀態也重現不了；審查這類截圖時，把「遮罩只蓋一半」「側欄底色停在半途」先歸給截圖方式，再判斷是不是版面缺陷。捲動狀態要有足夠長的資料：把測試資料複製幾份（每份改 id）撐出好幾個畫面。
- **頁面記住的設定**：頁面把檢視方式這類偏好存在 `localStorage` 時，每個狀態用新的 context（`browser.newPage()` 預設就是），才不會讀到上一個狀態留下的值；要測「記住了」時，在同一個 context 裡切換後重新整理。
