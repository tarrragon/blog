# golden-path-validation 版本紀錄

新到舊。版號規則與兩個住址（本檔與 `SKILL.md` frontmatter 的 `metadata.version`）見專案的 skill 同步規範。

**Version**: 1.3.1 — 術語校正：判準全數改為判斷標準（動作修飾語縮為「X 標準」、狀態義改為「X 條件」）。判準的語域在哲學與教育評量、工程讀者解析不了——五份低階模型探針一致回報非通用

**Version**: 1.3.0 — 多輪審查：frontmatter `metadata.version` 補同步（原漏、卡在 1.0.0）；關係段點名並連結 sibling skill（verification-driven-cli / multi-round-review，對齊 repo 慣例）；階段 3 補「階段 1 稽核缺口寫進 agent prompt」的資料流交棒；cold-read-agent-protocol 邊界補兩條方法缺口（需人工填的憑證步驟、依賴外部時序的長等待步驟怎麼在冷讀 cadence 下處理）
**Version**: 1.2.0 — disposable-environment reference 補第二個公開範例 `scripts/validate.sh`（執行核心 orchestrator：每目標 bare 容器 → git archive HEAD 放入 → install + verify → assert；那個 repo 把自己當本 skill 的 reference implementation）
**Version**: 1.1.0 — 新增 `references/disposable-environment.md`:怎麼起可拋棄乾淨環境（bare 給 cold-read vs provisioned 給操作者、原生非模擬、命名清理、容器專屬坑）+ 公開 reference implementation（`tarrragon/dotfiles` 的 `scripts/scratch.sh`，一鍵起可拋棄容器、可選 provision）；階段 3 指向它
**Version**: 1.0.0 — 初版:五階段(完整性稽核 → 自動化 verify → 冷讀代理人實機執行 → 乾淨環境 re-verify → 發現回收)+ 冷讀 agent 協定 + 三張原則卡(執行勝過審讀 / 原生非模擬 / verifier 也要被驗)。從一次個人尺度 paved road 的冷讀實測(Debian + 原生 arm64 Arch 容器、抓到硬編 sudo / 套件漂移 / verifier 假陰性 / 模擬架構假結果)萃取。
