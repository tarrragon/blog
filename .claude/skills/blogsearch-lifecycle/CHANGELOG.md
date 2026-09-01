# blogsearch-lifecycle 版本紀錄

新到舊。版號規則與兩個住址（本檔與 `SKILL.md` frontmatter 的 `metadata.version`）見專案的 skill 同步規範。

**Version**: 1.4.1 — 術語校正：判準全數改為判斷標準（動作修飾語縮為「X 標準」、狀態義改為「X 條件」）。判準的語域在哲學與教育評量、工程讀者解析不了——五份低階模型探針一致回報非通用

**Version**: 1.4.0 — 全量 rebuild 的真實成本進 SOP：耗時改為按當前規模推估（2026-08 實測 3510 檔 / 29863 chunks / 3296 秒，取代過時的「約 4 分鐘」）、明寫無增量模式與它對 rebuild 時機的影響、補雙重 fork 的脫離跑法（掛在 agent 背景工作下會連同 ollama 一起被回收、經管線的輸出會被緩衝到看不見進度）；失敗處理表加這兩種形態；提示規則補「說出耗時量級再問要不要跑」

**Version**: 1.3.0 — SOP 改用 Makefile target（install / ingest / verify）、description 補 ingest 觸發詞
