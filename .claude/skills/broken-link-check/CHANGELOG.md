# broken-link-check 版本紀錄

新到舊。版號規則與兩個住址（本檔與 `SKILL.md` frontmatter 的 `metadata.version`）見專案的 skill 同步規範。

**Version**: 2.4.0 — 排除清單與同步工具對齊，新增 `SYNC_EXCLUDED_DIRS`（`hook-logs/`、`project-integration/`）。`project-integration/` 是同步工具整個排除傳遞的目錄，也是 Layer 2 內容該住的地方（消費端專案自備自己的一份），所以裡面的消費端專屬路徑是刻意的、不是缺陷。先前只排除 `hook-logs/`，於是照規範把 Layer 2 內容放進 `project-integration/` 反而被報違規——唯一合法的住址變成每行都要標記的地方，等於取消這個目錄的用途。代價是該目錄內真正的失連不再被本掃描抓到，與同步工具的作用域一致。附測試（含突變驗證：把該目錄從清單拿掉後同一份輸入從 0 broken 變 1 broken）。

**Version**: 2.3.0
**Last Updated**: 2026-08-23
**Source**: broken links 後置預防機制；改路由至 scan_links.py 確定性 CLI 作權威 gate，手動流程降級為非權威 fallback；新增 documented-error 豁免 marker（excluded_documented 類別 + `--include-documented` 旋鈕），case-study 內刻意記錄的不存在路徑顯式 opt-in 豁免；新增 `--scan-root` 可疊加額外掃描子樹（如 `docs`），預設行為不變（向後相容）；新增 `--fence-audit` opt-in 稽核模式，`include_code_block` 預設維持 `False` 判定的配套承擔機制，恆 exit 0 非 gate，只輸出機器可靠分組訊號不做語意分類

**Version**: 2.2.1 — 版本紀錄搬到同目錄的 `CHANGELOG.md`。skill 是 runtime 整份載入的檔案，而沒有任何規則要求任何人讀版本紀錄，留在 SKILL.md 等於每次叫用都付一次無效讀取。SKILL.md 末尾留一行指過去，版號的兩個住址改成「CHANGELOG.md 最上面那一條 + frontmatter 的 metadata.version」。skill 的指令內容一個字都沒改。

**Version**: 2.2.0
**Last Updated**: 2026-08-18
