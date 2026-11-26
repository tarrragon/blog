---
name: chrome-extension-playwright-testing
description: 不經使用者瀏覽器，用 Playwright 驗證 Chrome 擴充功能（MV3）：全新載入建置、讓 content script 注入本機頁、讀與停 service worker、用假 chrome API 渲染 popup 與擴充功能頁各狀態、瀏覽器的關閉與殘留。觸發：測擴充功能、popup 或擴充功能頁截圖、content script 驗證。
metadata:
  version: 1.1.0
  portable: true
---

# Chrome Extension Playwright Testing

改了擴充功能之後，用 Playwright 驗證，不必請使用者手動重新載入、也不必碰使用者正在用的瀏覽器設定。兩種做法驗的東西不同，先選對：

| 要驗的 | 做法 | 讀哪一份 |
|--------|------|---------|
| content script 有沒有注入、訊息有沒有往返、service worker 的行為、哪一版程式在跑 | 以 `--load-extension` 全新載入一份建置的副本 | `references/loading-and-markers.md` |
| popup 與其他擴充功能頁（清單頁、設定頁）在每個狀態長什麼樣、改版前後元素有沒有少、版面有沒有溢出、捲動後的樣子 | `file://` 開啟頁面，注入假的 `chrome` 物件切狀態 | `references/popup-state-rendering.md` |

## 共通規則

- **載入副本，不載入使用者瀏覽器在用的資料夾**：測試要改 manifest（加本機網址）或加標記，改在原資料夾會影響使用者的瀏覽器。
- **每次全新載入**：content script 與 service worker 只在載入擴充功能時讀檔，全新載入才保證跑的是當下的建置。
- **結論是「沒變」或「沒反應」時加正對照**：用同一份改過的檔案全新載入，確認讀得到新的標記，否則分不出是程式沒換還是測試沒讀到。
- **假物件的 API 形狀要跟 MV3 一致**：不傳 callback 時回傳 Promise；初始化握手要回應。不一致時看到的錯誤或停滯是測試造成的，不是程式的問題。
- **測試輸入取下一層實際收到的形狀**：這一條不論用 Playwright 還是單元測試，只要驗的是資料流（content script 送出的事件經轉送層到 service worker、再寫進 storage）都適用；轉送層指把事件從一個執行環境轉交給下一個的那段程式（例如 service worker 裡接收 content script 訊息、再分派給事件處理器的程式）。測試送進去的事件要長得跟轉送層實際交給下一層的一樣，包括轉送層加上的欄位。寫測試的人手寫一份「理想的」事件（例如明確帶 `source: 'site-a'`），會跳過轉送層覆蓋欄位的那一步，下一層拿那個欄位組 storage key 的錯誤測不到。做法是在轉送層的出口錄一份實際的事件當測試資料，或讓測試經過轉送層。

## 測試開出的瀏覽器：關閉與殘留

測試開出的瀏覽器沒關掉，會一直留在使用者的機器上：有視窗的模式下是一個個只有空白分頁的視窗，headless 的則是背景程序。

- **預設 headless**：照 `references/loading-and-markers.md` 的 `launchPersistentContext` 設定，`headless: true`，不開視窗；Playwright 附的 Chromium 要帶 `channel: 'chromium'` 才能在 headless 下載入擴充功能，預設的 headless shell 載入不了。
- **在 `finally` 關閉**：`context.close()`（或 `browser.close()`）寫在 `finally`，測試失敗或丟錯時也關得到。
- **啟動到一半失敗時瀏覽器可能已經開出來**：瀏覽器程序已經啟動、接下來的連線才失敗時（例如在 jsdom 環境跑 Puppeteer，WebSocket 連不上），`launch()` 丟錯、拿不到 browser 物件，`close()` 無從呼叫，程序留成孤兒（父程序變成 1）。`launch()` 丟錯之後，照下面「測完查一次有沒有殘留」查。
- **跑專案既有的測試套件時，瀏覽器 E2E 只用它指定的設定跑**（node 環境的 jest 設定、專用的 npm script），不用預設設定把整個測試目錄掃進去：預設設定可能是 jsdom 環境，正好造成啟動到一半失敗的孤兒。跑之前列出這條指令實際用的設定檔，以及它的 `testEnvironment` 與 `testMatch`（看 `package.json` 的 scripts 與 jest 設定檔）；會 import puppeteer 或 playwright 的測試檔落在 `testEnvironment` 不是 `node` 的設定裡時，不跑那條指令。`npm test` 不因為是專案的 script 就算指定的設定。找不到 node 環境的設定時，先問使用者。
- **測完查一次有沒有殘留**：用測試的 profile 目錄名找程序（macOS 用 `pgrep -fl`，Linux 用 `pgrep -af`，兩者都印出完整命令列）。pattern 寫成 `'[p]uppeteer_dev_chrome_profile|[p]laywright_chromiumdev_profile'`：方括號讓包住這條指令的那層 shell 的命令列比對不上（Linux 的 `pgrep` 只排除它自己，不排除上層的 shell），專案在設定裡指定了 `userDataDir` 時改成那個目錄名，同樣把第一個字母包進方括號；不用 `ps | grep`。正對照在測試還在跑時做，做法在 `references/loading-and-markers.md` 的〈全新載入一份建置〉。沒有輸出代表沒有殘留；有輸出時，每個瀏覽器有好幾個子程序，命令列含 `--user-data-dir=` 而不含 `--type=` 的那一個是主程序，列出主程序的 PID 與 profile 路徑給使用者，由使用者決定關閉。

## 限制

- **看不到 `chrome.runtime.reload()` 之後的結果**：以 `--load-extension` 載入的擴充功能，一呼叫 `chrome.runtime.reload()` 就整個消失，service worker 不再出現、content script 不再注入。要驗重新載入之後的行為（例如開發版自動重新載入），只能驗到「觸發了重新載入」，之後的部分在使用者的瀏覽器上驗。
- **登入狀態與真實網站的 DOM 拿不到**：依賴網站登入或網站 DOM 結構的流程（從真實頁面提取資料），本機測試頁替代不了，在使用者的瀏覽器上驗。
- **只在 Playwright 附的 Chromium 上做過**：換 Chrome for Testing 或 Chromium 大版本更新時，先重跑 `references/loading-and-markers.md` 的正對照，確認載入方式仍然可用。品牌版 Google Chrome 與 Edge 的新版本不接受 `--load-extension`（Playwright 文件〈Chrome extensions〉寫明這兩者移除了側載參數），不必試。

改動生效時機與開發版自動重新載入在 `chrome-extension-dev-loop` skill。

版本紀錄在同目錄的 `CHANGELOG.md`。
