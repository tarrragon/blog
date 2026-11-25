# 開發版自動重新載入

本 reference 給「讓擴充功能在重新建置後自己重新載入」的設計、接入建置流程的步驟、驗證方法與限制。通用實作在 `scripts/dev-auto-reload.js`，複製到專案的建置腳本目錄即可使用。

## 設計

改了 content script 或 service worker 之後，要重新載入擴充功能才會跑新程式（`change-propagation.md`）。自動重新載入把這一步交給 service worker 自己做：

1. 開發建置在所有檔案寫完之後，於 service worker 檔案尾端附加一段程式，這次的建置戳記寫死在程式裡。
2. 建置最後寫出 `dev-build-stamp.json`（內容是同一個戳記）。
3. service worker 以 `chrome.alarms` 每 3 秒讀一次 `dev-build-stamp.json`；磁碟上的戳記與寫死的戳記不同，就呼叫 `chrome.runtime.reload()`。

三個設計決定與各自的理由：

| 決定 | 理由 | 換成另一種做法的後果 |
|------|------|------------------|
| 戳記寫死在程式裡，不在 service worker 啟動時讀檔 | service worker 閒置被停掉、再被喚醒時，跑的是載入時的舊程式，卻讀得到新的戳記檔 | 舊程式醒來記下新戳記，兩者永遠相同，不會重新載入 |
| 戳記檔最後才寫 | 建置若先清空輸出目錄，中途讀不到戳記檔，`check()` 不動作 | 先寫戳記檔，可能重新載入到只寫了一半的輸出 |
| 用 `chrome.alarms`，不用 `setInterval` | service worker 閒置會被停掉，計時器跟著消失；alarm 會把停掉的 worker 叫醒 | 閒置一段時間後就不再檢查 |

`chrome.alarms` 的 30 秒下限只套用在已封裝的擴充功能；未封裝的擴充功能可以用更短的間隔（實測 3 秒的間隔照常觸發）。

## 接入建置流程

1. 把 `scripts/dev-auto-reload.js` 複製到專案的建置腳本旁邊。
2. 在建置腳本的最後一步（打包、複製、manifest 處理全部完成之後）呼叫：

   ```js
   if (isDevBuild && process.env.DEV_AUTO_RELOAD !== '0') {
     const { applyDevAutoReload } = require('./dev-auto-reload')
     applyDevAutoReload(buildDir)
   }
   ```

   `isDevBuild` 與 `buildDir` 換成專案建置腳本裡區分開發版與輸出目錄的變數。
3. 正式版建置不呼叫它：不附加程式、不加 `alarms` 權限、不寫戳記檔。
4. 補一支單元測試，至少確認三件事：戳記寫進附加的程式、manifest 多了 `alarms`、戳記檔寫出。另外以字串比對確認建置腳本只在開發版呼叫它。

`applyDevAutoReload` 從 `manifest.background.service_worker` 找 service worker 檔，打包工具輸出 IIFE 或 ES module 都可以在尾端附加。

## 使用與注意事項

1. **第一次要手動重新載入一次**：manifest 多了 `alarms` 權限，manifest 的改動只有手動重新載入才生效。之後的建置就自動重新載入。
2. **content script 的改動仍要重新整理頁面**：擴充功能重新載入後，已開著的分頁裡是舊的 content script，重新整理才注入新的。
3. **提取或長時間作業進行中重新建置會中斷它**：重新載入會結束 service worker 與所有擴充功能頁。
4. **建置驗證工具可能多一個權限警告**：開發版多了 `alarms`，正式版沒有。
5. **關閉**：建置時設 `DEV_AUTO_RELOAD=0`。

## 驗證

在使用者的瀏覽器裡驗證，因為重新載入之後的結果在 Playwright 以 `--load-extension` 載入的環境裡看不到（`chrome.runtime.reload()` 會讓這種方式載入的擴充功能消失，見 `chrome-extension-playwright-testing` skill 的〈限制〉）：

1. 使用者手動重新載入一次擴充功能（因為 manifest 加了權限）。
2. 重新建置，記下建置印出的戳記。
3. 使用者開啟擴充功能管理頁上該擴充功能的 service worker 檢查視窗，看 Console：
   - 最新一行 `[dev-auto-reload] 目前建置 <戳記>` 的戳記等於第 2 步的戳記，代表重新載入成功並跑新程式。
   - 同一段 log 裡 `chrome.runtime.onInstalled` 的 `reason` 是 `update`，代表確實重新載入過。
   - 戳記仍是舊值，或幾秒後沒有新訊息，代表沒有運作。

在 Playwright 裡只驗得到「偵測並觸發了重新載入」：訂閱擴充功能 console 的 `[dev-auto-reload] 偵測到新建置` 訊息，以及 CDP `ServiceWorker.workerVersionUpdated` 的 `stopping → stopped`。實測從改戳記到偵測約 1.3 秒（worker 執行中）、約 0.2 秒（worker 已被停掉，由 alarm 喚醒）。
