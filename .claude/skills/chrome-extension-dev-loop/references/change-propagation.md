# 改動何時生效：未封裝擴充功能的三個執行位置

本 reference 給「判斷改了某個檔案之後要做什麼才會跑到新程式」與「在新的瀏覽器版本上重新確認這張表」兩件事。SKILL.md 的對照表是結論，這裡是它的依據與重驗方法。

## 對照表的依據

未封裝（unpacked）的擴充功能由瀏覽器直接讀建置輸出的資料夾，不經安裝程序。但瀏覽器讀檔的時機依程式跑在哪裡而不同：

| 執行位置 | 典型檔案 | 讀檔時機 | 改檔並重新建置之後 |
|---------|---------|---------|------------------|
| 擴充功能自己的頁面 | popup、options、overview 這類 `chrome-extension://<id>/…` 頁面 | 每次開啟頁面時讀資料夾裡當下的檔案 | 重新開啟該頁面就跑新程式 |
| content script | manifest `content_scripts` 宣告的檔案 | 載入擴充功能時讀進來，之後注入頁面都用這一份 | 要重新載入擴充功能，再重新整理被注入的頁面 |
| service worker | manifest `background.service_worker` | 載入擴充功能時登記；閒置被停掉再喚醒，跑的仍是登記時的程式 | 要重新載入擴充功能 |
| manifest | `manifest.json` | 載入擴充功能時讀 | 要重新載入擴充功能 |

一次改動同時碰到多個位置時，取最嚴的那一個：改了共用模組，而它被打包進 content script 與 popup，就照 content script 的處置。

## 實驗紀錄（Playwright 附的 Chromium）

做法：把建置輸出複製一份，用 Playwright 以 `--load-extension` 載入副本；載入後改副本裡的檔案、不重新載入擴充功能，觀察跑的是哪一版。標記的寫法：

- content script：檔案尾端加 `document.documentElement.setAttribute('data-cs-marker', 'CS-2')`。content script 與頁面共用 DOM，頁面端讀得到這個屬性。
- service worker：檔案尾端加 `self.__swMarker = 'SW-2'`，用 Playwright 的 `worker.evaluate(() => self.__swMarker)` 讀。
- 擴充功能頁：檔案尾端加 `window.__popupMarker = 'POPUP-2'`，重新開啟頁面後 `page.evaluate` 讀。

結果：

| 情境 | 讀到 |
|------|------|
| popup 改檔後重新開啟 | 新版 |
| content script 改檔後，同一分頁重新整理 | 舊版 |
| content script 改檔後，開新分頁 | 舊版 |
| service worker 改檔後，worker 仍在執行 | 舊版 |
| service worker 改檔後，用 CDP 停掉再由擴充功能頁喚醒 | 舊版 |
| 正對照：同一份改過的檔案全新載入擴充功能 | content script 與 service worker 都是新版 |

**正對照不能省**：沒有它，「讀到舊版」分不出是瀏覽器沒讀新檔，還是標記根本沒寫進去或讀法錯了。正對照讀到新版，前面的「舊版」才算數。

**確認 service worker 真的停過再下結論**：停掉的指令送出後，Playwright 手上的 worker 物件可能還是同一個，只看物件判不出它停過沒有。訂閱 CDP 的 `ServiceWorker.workerVersionUpdated`，看到 `running → stopping → stopped → starting → running` 的序列，才算「停掉再喚醒」這個情境成立。做法見 `chrome-extension-playwright-testing` skill 的 `references/loading-and-markers.md`〈停掉 service worker 並確認它停過〉。

## 在新環境重驗

瀏覽器版本更新、換用 Google Chrome 或 Edge、或擴充功能改成 manifest 以外的方式注入程式（例如 `chrome.scripting.executeScript`）時，這張表可能不再成立。重驗照上面的實驗做，結果寫進專案的開發文件，附上瀏覽器與版本。用 `chrome.scripting.executeScript` 注入的檔案沒有測過，處置不能直接沿用 content script 那一列。

## 實務處置

- 只改擴充功能頁：重新建置後重新開啟頁面。
- 改到 content script 或 service worker：重新載入擴充功能（或用 `dev-auto-reload.md` 的自動重新載入），content script 還要重新整理被注入的頁面。
- 改到 manifest：手動重新載入擴充功能；自動重新載入的機制本身也靠 manifest 宣告權限，manifest 的改動它處理不了。
