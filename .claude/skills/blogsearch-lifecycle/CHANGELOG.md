# blogsearch-lifecycle 版本紀錄

新到舊。版號規則與兩個住址（本檔與 `SKILL.md` frontmatter 的 `metadata.version`）見專案的 skill 同步規範。

**Version**: 1.5.0 — 偵測觸發表補一列「刪除、搬移或改名 content 的檔案」（偵測直接比對 `meta.json` 的 `metas[].source` 在工作樹裡存不存在。審查時先後試過 `git log --since=<meta.json 的修改時間> --diff-filter=DR`：`--name-only` 對改名印新路徑，2026-10-27 實跑 405 行裡 369 行是還存在的路徑；改取舊路徑之後仍有反例，分支上較早提交的搬移在 ingest 之後才 fast-forward 進 main 時查不到，ingest 進行中提交的也查不到，還沒提交的改動也看不到。比對 index 自己記的路徑沒有這些反例，同一天在 3828 個路徑的 index 上列出 315 個已經不存在），提醒表補同一個情境並附耗時，「說出耗時」從單篇文章的提示擴大到每一種提示，description 補觸發詞「content 搬移」（同時刪掉「適用於有 blogsearch 語意搜尋工具的專案」以免超過 250 字元）。來源：2026-10-27 把五個資料夾收進 content/devops/ 之後，index 裡 399 頁的路徑都過時，而原本的觸發表只列「寫完新文章」與「git pull」，搬移對不到任何一列

**Version**: 1.4.3 — 失敗處理表補一列：Linux procps 的 `pgrep -f` 會匹配等待迴圈自己的 shell，迴圈在 ingest 結束後停不下來；macOS 的 BSD pgrep 預設排除祖先行程不受影響（debian procps-ng 4.0.4 與 macOS 各實測一次，方括號 pattern 在 Linux 上正常結束）

**Version**: 1.4.2 — 耗時實測補 2026-09-29 一筆（3830 檔 / 33092 chunks / 2182 秒）；兩次速度差到每秒 1.1 與 1.8 檔，推估改成開跑後讀進度換算當次速度

**Version**: 1.4.1 — 術語校正：判準全數改為判斷標準（動作修飾語縮為「X 標準」、狀態義改為「X 條件」）。判準的語域在哲學與教育評量、工程讀者解析不了——五份低階模型探針一致回報非通用

**Version**: 1.4.0 — 全量 rebuild 的真實成本進 SOP：耗時改為按當前規模推估（2026-08 實測 3510 檔 / 29863 chunks / 3296 秒，取代過時的「約 4 分鐘」）、明寫無增量模式與它對 rebuild 時機的影響、補雙重 fork 的脫離跑法（掛在 agent 背景工作下會連同 ollama 一起被回收、經管線的輸出會被緩衝到看不見進度）；失敗處理表加這兩種形態；提示規則補「說出耗時量級再問要不要跑」

**Version**: 1.3.0 — SOP 改用 Makefile target（install / ingest / verify）、description 補 ingest 觸發詞
