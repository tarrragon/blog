# verification-driven-cli 版本紀錄

新到舊。版號規則與兩個住址（本檔與 `SKILL.md` frontmatter 的 `metadata.version`）見專案的 skill 同步規範。

**Version**: 1.2.2 — 版本紀錄搬到同目錄的 `CHANGELOG.md`。skill 是 runtime 整份載入的檔案，而沒有任何規則要求任何人讀版本紀錄，留在 SKILL.md 等於每次叫用都付一次無效讀取。SKILL.md 末尾留一行指過去，版號的兩個住址改成「CHANGELOG.md 最上面那一條 + frontmatter 的 metadata.version」。skill 的指令內容一個字都沒改。

**Version**: 1.2.1 — 術語校正：判準全數改為判斷標準（動作修飾語縮為「X 標準」、狀態義改為「X 條件」）。判準的語域在哲學與教育評量、工程讀者解析不了——五份低階模型探針一致回報非通用

**Version**: 1.2.0 — 關係段補回指 golden-path-validation（雙向可見：本 skill「作者驗單一工具」vs 它「陌生人端到端驗指引」、共享執行勝過審讀/模擬不可信）；frontmatter `metadata.version` 補同步（原漏、卡在 1.0.0）
**Version**: 1.1.0 — 反覆陷阱補兩條方法論：verifier 自己也是待驗的（naive 檢查對上 stow 摺疊等會假陰性、拿已知正確環境先驗 verifier）、模擬架構的 fixture 不可信（qemu 下 sandbox/seccomp/LSM/syscall 行為跟原生不同、架構敏感驗證要原生跑）
**Version**: 1.0.0
