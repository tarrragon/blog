---
name: chrome-extension-dev-loop
description: 未封裝 Chrome 擴充功能（MV3）的開發迴圈：改哪類檔案之後要重新載入、為什麼 content script 與 service worker 改了不生效、開發版自動重新載入、在使用者瀏覽器上讀 log 與 storage 診斷。觸發：擴充功能改了沒生效、要不要重新載入、自動重新載入、資料沒更新、讀 storage。
metadata:
  version: 1.1.0
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

## 在使用者的瀏覽器上診斷

錯誤只在使用者的瀏覽器重現時（要登入的網站、使用者累積的 storage 資料），請使用者跑指令、貼回輸出，照下面幾項做：

- **寫明是哪一個 Console**：content script、service worker、popup、擴充功能頁的 log 各在各的 DevTools；請使用者用 Filter 篩關鍵字，只貼那幾行。
- **讀 storage 用唯讀片段**：service worker 的 Console 直接呼叫得到 `chrome.storage.local.get`；先用 `get(null)` 列出全部 key 與筆數，再印計數與少量樣本，輸出純文字。會修改或刪除資料的片段先列出要動的紀錄，由使用者決定要不要跑。
- **沿著資料流逐段計數**：來源宣稱的總數、載入到 DOM 的數量、解析數、寫入時的數量與 key、storage 裡讀取端那個 key 的數量、畫面上的數量；缺陷在第一次對不上的那兩段之間，前一段的輸出或後一段的輸入。
- **請使用者做會寫入資料的操作之前，先確認建置裡有修正**：開發版從目前 checkout 的分支建置，修正還在別的分支時，使用者用舊程式操作會寫下錯的資料，修正上線之後那些資料仍然留著。
- **修好程式之後，舊程式寫下的資料另外判斷**：哪些會被下一次操作補上、哪些在讀取端推導顯示、哪些是不在來源上的使用者資料要保留、哪些只能清掉。

片段的寫法、各 Console 的打開方式與殘留資料的判斷在 `references/diagnosing-in-user-browser.md`。

## 按需讀取

| 何時讀 | 檔案 |
|--------|------|
| 要知道對照表的依據、或在新的瀏覽器版本上重驗 | `references/change-propagation.md` |
| 要把自動重新載入接進一個專案、或它沒有運作要排查 | `references/dev-auto-reload.md` |
| 錯誤只在使用者的瀏覽器重現、要請使用者跑指令或讀 storage、資料抓到了畫面沒更新 | `references/diagnosing-in-user-browser.md` |
| 要在不碰使用者瀏覽器的情況下驗證擴充功能的改動 | `chrome-extension-playwright-testing` skill |

版本紀錄在同目錄的 `CHANGELOG.md`。
