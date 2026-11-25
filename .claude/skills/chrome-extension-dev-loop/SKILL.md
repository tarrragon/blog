---
name: chrome-extension-dev-loop
description: 未封裝 Chrome 擴充功能（MV3）的開發迴圈：改哪類檔案之後要重新載入、為什麼 content script 與 service worker 改了不生效、開發版自動重新載入的設計與接入。觸發：擴充功能改了沒生效、要不要重新載入、自動重新載入、hot reload。
metadata:
  version: 1.0.0
  portable: true
---

# Chrome Extension Dev Loop

未封裝的擴充功能由瀏覽器直接讀建置輸出的資料夾，不必重新安裝；但改了程式之後要不要到擴充功能管理頁重新載入，取決於那段程式跑在哪裡。判錯的代價是拿舊程式的行為當成新程式的結果：改了 content script 卻在沒重新載入的頁面上測，看到的「沒修好」其實是舊版。

## 改動何時生效

| 改到哪裡 | 程式跑在哪裡 | 重新建置之後要做的事 |
|---------|------------|------------------|
| popup、options 等擴充功能自己的頁面（`chrome-extension://<id>/…`） | 擴充功能頁 | 重新開啟該頁面 |
| manifest `content_scripts` 宣告的檔案 | 被注入的網頁 | 重新載入擴充功能，再重新整理那個網頁 |
| manifest `background.service_worker` | service worker | 重新載入擴充功能 |
| `manifest.json` | — | 手動重新載入擴充功能 |

- 一次改動同時碰到多個位置時（共用模組被打包進 content script 與 popup），照最嚴的那一列做。
- service worker 閒置被停掉、再被喚醒，跑的仍是載入時的舊程式，等它自己重啟不會換成新版。
- 這張表是在 Playwright 附的 Chromium 上實驗得到的；換瀏覽器、換大版本，或程式改用 `chrome.scripting.executeScript` 注入時，照 `references/change-propagation.md`〈在新環境重驗〉重驗。

## 開發版自動重新載入

要讓 content script 與 service worker 的改動在重新建置後自己生效，用 `scripts/dev-auto-reload.js`：開發建置的最後一步把建置戳記寫死在 service worker 尾端的程式裡，再寫出戳記檔；service worker 每 3 秒比對一次，不同就 `chrome.runtime.reload()`。

接入前要知道的事：

- 只在開發建置呼叫，正式版不附加程式、不加 `alarms` 權限。
- 接入後第一次要手動重新載入一次（manifest 加了權限）。
- content script 的改動仍要重新整理被注入的頁面。
- 長時間作業進行中重新建置會中斷它。
- 重新載入之後的結果只能在使用者的瀏覽器裡驗證，Playwright 以 `--load-extension` 載入的擴充功能一重新載入就消失。

設計理由、接入步驟、驗證方法在 `references/dev-auto-reload.md`。

## 按需讀取

| 何時讀 | 檔案 |
|--------|------|
| 要知道對照表的依據、或在新的瀏覽器版本上重驗 | `references/change-propagation.md` |
| 要把自動重新載入接進一個專案、或它沒有運作要排查 | `references/dev-auto-reload.md` |
| 要在不碰使用者瀏覽器的情況下驗證擴充功能的改動 | `chrome-extension-playwright-testing` skill |

版本紀錄在同目錄的 `CHANGELOG.md`。
