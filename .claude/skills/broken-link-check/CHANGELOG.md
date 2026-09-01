# broken-link-check 版本紀錄

新到舊。版號規則與兩個住址（本檔與 `SKILL.md` frontmatter 的 `metadata.version`）見專案的 skill 同步規範。

**Version**: 2.2.0
**Last Updated**: 2026-08-18
**Source**: broken links 後置預防機制；1.0.0-W8-030.1 改路由至 scan_links.py 確定性 CLI 作權威 gate，手動流程降級為非權威 fallback；1.0.0-W8-049 新增 documented-error 豁免 marker（excluded_documented 類別 + `--include-documented` 旋鈕），case-study 內刻意記錄的不存在路徑顯式 opt-in 豁免；新增 `--scan-root` 可疊加額外掃描子樹（如 `docs`），預設行為不變（向後相容）
