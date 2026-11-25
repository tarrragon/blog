---
name: chrome-extension-playwright-testing
description: 不經使用者瀏覽器，用 Playwright 驗證 Chrome 擴充功能（MV3）：全新載入建置、讓 content script 注入本機頁、讀與停 service worker、用假 chrome API 渲染 popup 各狀態、標記與正對照。觸發：測擴充功能、popup 截圖、content script 驗證。
metadata:
  version: 1.0.0
  portable: true
---

# Chrome Extension Playwright Testing

改了擴充功能之後，用 Playwright 驗證，不必請使用者手動重新載入、也不必碰使用者正在用的瀏覽器設定。兩種做法驗的東西不同，先選對：

| 要驗的 | 做法 | 讀哪一份 |
|--------|------|---------|
| content script 有沒有注入、訊息有沒有往返、service worker 的行為、哪一版程式在跑 | 以 `--load-extension` 全新載入一份建置的副本 | `references/loading-and-markers.md` |
| popup 在每個狀態長什麼樣、改版前後元素有沒有少、版面有沒有溢出 | `file://` 開啟 popup，注入假的 `chrome` 物件切狀態 | `references/popup-state-rendering.md` |

## 共通規則

- **載入副本，不載入使用者瀏覽器在用的資料夾**：測試要改 manifest（加本機網址）或加標記，改在原資料夾會影響使用者的瀏覽器。
- **每次全新載入**：content script 與 service worker 只在載入擴充功能時讀檔，全新載入才保證跑的是當下的建置。
- **結論是「沒變」或「沒反應」時加正對照**：用同一份改過的檔案全新載入，確認讀得到新的標記，否則分不出是程式沒換還是測試沒讀到。
- **假物件的 API 形狀要跟 MV3 一致**：不傳 callback 時回傳 Promise；初始化握手要回應。不一致時看到的錯誤或停滯是測試造成的，不是程式的問題。

## 限制

- **看不到 `chrome.runtime.reload()` 之後的結果**：以 `--load-extension` 載入的擴充功能，一呼叫 `chrome.runtime.reload()` 就整個消失，service worker 不再出現、content script 不再注入。要驗重新載入之後的行為（例如開發版自動重新載入），只能驗到「觸發了重新載入」，之後的部分在使用者的瀏覽器上驗。
- **登入狀態與真實網站的 DOM 拿不到**：依賴網站登入或網站 DOM 結構的流程（從真實頁面提取資料），本機測試頁替代不了，在使用者的瀏覽器上驗。
- **只在 Playwright 附的 Chromium 上做過**：換 Google Chrome、Edge 或大版本更新時，先重跑 `references/loading-and-markers.md` 的正對照，確認載入方式仍然可用。

改動生效時機與開發版自動重新載入在 `chrome-extension-dev-loop` skill。

版本紀錄在同目錄的 `CHANGELOG.md`。
