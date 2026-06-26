@AGENTS.md

---

# Claude Code 專屬補充

上方 `@AGENTS.md` 由 Claude Code 自動內嵌、AGENTS.md 是寫作 / 工程規範的 SSoT。本檔只放 **Claude Code 專屬行為**、不重複 AGENTS.md 內容。

## Skill 自動觸發

Claude Code 會根據對話內容自動觸發 `.claude/skills/` 內的 skill — 看 `SKILL.md` 開頭的 `description` / `trigger` 字串匹配當前任務。常用觸發詞：

| Skill                      | 觸發情境                                                   |
| -------------------------- | ---------------------------------------------------------- |
| `compositional-writing`    | 寫文章 / 卡片 / 註解 / 文件 / prompt 時                    |
| `requirement-protocol`     | 模糊指令、反覆失敗、覆寫成本、確認嗎 / OK 嗎 / yes-no 二選 |
| `frontend-with-playwright` | 前端 CSS / DOM / framework 共處 / Playwright 驗證 / a11y   |
| `wrap-decision`            | 分析 / 決策 / 比較 / 提案、被困住、根因分析、個人化建議    |

手動調用：對話中打 `/<skill-name>` 強制啟動。

skill 內容看 `.claude/skills/<name>/SKILL.md`。

## Skill ↔ Content 互斥

寫作時要清楚目前在哪個 surface：

| Surface           | 規則檔                                                                       | 自包含？          |
| ----------------- | ---------------------------------------------------------------------------- | ----------------- |
| `.claude/skills/` | `compositional-writing/references/reference-authoring-standards.md`          | 是、不引用 blog   |
| `content/`        | `content/posts/markdown-writing-spec.md`（Hugo 規範）+ AGENTS.md（內容規範） | 否、可 cross-link |

跨 surface 的引用會違反規範 — 寫 skill 時複製 principle 卡進 `references/principles/`、不寫外部連結（AGENTS.md §9.2-3）。

## 文章寫作避免模板化

Claude Code 寫 `content/` 文章時，不要為了整齊而把案例、反例、規模對照或 tripwire 抽成共通模板。不同情境的業務壓力、資料形狀、流量型態、失敗條件與回退路徑若不同，必須用該情境自己的敘事說明與判讀條件。

表格只能輔助整理，不可取代情境判讀。若欄位化後讓內容變得僵硬、抽象或遺失細節，應改回段落式說明。

## 教學模組寫作流程

寫跨多章節的教學模組時（例：backend/01 資料庫模組 12 章）、走 [Case-First + Agent Team Review 標準流程](/posts/case-first-agent-team-review-workflow/)、不要直接用 LLM 自生內容塞章節。

完整方法論看該文章、Claude Code 執行重點：

1. **完整讀 case 庫抽 findings**：用 Read tool 完整讀目標 case（不只 frontmatter）、邊讀邊抽 findings 跟章節對應、邊際遞減訊號出現就停止 audit
2. **內容生成**：寫稿時案例引用要回 case 原文驗證、避免把通用 best practice 包裝成「[case] 揭露」
3. **Agent team review**：用 Agent tool spawn 3 個 `general-purpose` reviewer、各自指定不同維度（寫作規範 / 案例準確性 / 跨章一致性）、`run_in_background: true` 平行跑、主 context 只看彙整報告

**為什麼 background**：reviewer 要讀完整 commit + 案例 + 章節、自身 context 會被佔滿；用 background 把 reviewer context 跟主 context 分開、主 context 只接收精煉摘要、節省 ~80% context。

**何時用**：跨 5+ 章節模組 + 有 case 庫 + 品質高於速度。詳細適用 / 不適用條件見 AGENTS.md §5「教學模組級流程」段。

## Content 路徑大小寫

`content/` 的資料夾與對外 route 一律使用小寫（例如 `content/ci` ↔ `/ci/`）。在 macOS 本機大小寫錯誤可能不會浮現，但 Linux CI 會把 `content/CI` 與 `/ci/` 視為不同路徑，造成 `mdtools cards` 大量 broken link。

提交前最少做一次：

```bash
./bin/mdtools cards content/
```

若要快速掃描 repo 是否殘留大寫內容路徑：

```bash
git ls-tree -r --name-only HEAD | rg '^content/[A-Z]'
```

### Portable pass

Claude Code 修改 `.claude/skills/` 時要把 skill 當成「可搬到空白專案的獨立目錄」。允許依賴同 skill 內的相對檔案；需要 report / posts 的抽象原則時，先抽成 `references/principles/<slug>.md`，再用相對連結引用。

提交前掃描 portable 風險：

```bash
rg -n "\\]\\((/|content/|\\.\\./\\.\\./)|(/report/|/posts/|/skills/|content/report|content/posts|content/skills|_index\\.md)" .claude/skills/<name>
```

掃到 blog route、`content/` path、`/report/`、`/posts/`、`/skills/`、Hugo-only `_index.md` 時，改成 skill 內部 principle、相對連結或中性名詞（collection index / MOC / article / reference）。

## Skill 庫同步

本專案的 `.claude/skills/` 與遠端 skill 庫 `https://github.com/tarrragon/claude-skills.git` 共用同一組 skill。使用 `skill-sync` CLI 工具同步（透過 `uv tool` 安裝在 `~/.local/bin/skill-sync`）。

### skill-sync 指令

```bash
# 列出遠端所有 skill
skill-sync list

# 批次更新已安裝的 skill（比對 versions.json，只更新有差異者）
skill-sync pull

# 拉取指定 skill（新安裝或強制更新）
skill-sync pull <skill-name>

# 本地 → 遠端（修改 skill 後推送，自動更新 versions.json）
skill-sync push <skill-name> -m "commit message"
```

### 版號規則（強制）

修改 skill 內容後必須更新 SKILL.md 末尾的版本號，格式為 `**Version**: X.Y.Z — 變更摘要`。版號遵循 semver：

- **patch**（0.1.0 → 0.1.1）：修錯字、補連結、格式調整
- **minor**（0.1.0 → 0.2.0）：新增 reference / principle 卡、擴充段落、加觸發詞
- **major**（0.X → 1.0.0）：結構重組、支柱變動、破壞既有行為

未標版號的 skill 首次補標用 `1.0.0`。變更摘要簡述改了什麼，參考 compositional-writing 的版本紀錄格式。

### 標準操作流程

流程從 report 卡開始，不從 skill 修改開始。report 是原則的 SSoT（有情境、根因、理想做法），skill 是 report 的操作化引用。先有 report 才有 skill 引用的依據。

1. **建 report 卡**：在 `content/report/` 建卡，更新 `_index.md` 篇目索引
2. **評估是否進 skill**：判斷這個原則該進哪個 skill（compositional-writing / multi-round-review / 其他）、進哪個段落
3. **修改 skill**：在 `.claude/skills/<name>/` 修改 SKILL.md，引用 report 卡的路徑（`.claude/` 用 `references/principles/` 相對連結、`content/` 鏡像會自動轉成 `/report/` 路徑）
4. **如果新增 principle 卡**：在 `references/principles/` 建卡，並在 `bin/skill-mirror` 的 mapping table 加上 principle slug → report slug 的對應
5. **更新版本號**：SKILL.md 末尾加版本號（見上方版號規則）
6. **commit 到 blog repo**
7. **推送到 skill repo**：`skill-sync push <name> -m "描述" --force`
8. **同步鏡像**：`bin/skill-mirror <name>`（自動處理 Hugo frontmatter、H1→H2、連結轉換、fmt）
9. **commit 鏡像**：`git add content/skills/<name>/skill.md && git commit --no-verify`
10. **push**

簡化版（步驟 6-10）：

```bash
git add .claude/skills/<name>/ content/report/ && git commit
skill-sync push <name> -m "vX.Y.Z: 描述" --force
bin/skill-mirror <name>
git add content/skills/<name>/skill.md && git commit --no-verify
git push --no-verify
```

批量推送多個 skill 時逐一執行 `skill-sync push`，不要嘗試手動 clone 遠端 repo 操作。

### 同步判斷原則

- 版本號相同但檔案有差異 → 本地是客製版，以本地為準推回遠端。
- 遠端版本較新 → diff 審查後決定是否合併（`skill-sync pull` + 本地比對）。
- 本地版本較高 → 不覆蓋，本地為準。
- 遠端有新增檔案（原則卡、hooks）→ `skill-sync pull` 取用到本地，再推合併版回遠端。
- `compositional-writing` 的 `hooks/` 目錄只存在遠端、本地不使用 — 推回時工具會保留。

### 注意事項

- 本專案 AGENTS.md 禁 emoji（§8），遠端若加了 emoji 是倒退、要修正推回。
- Skill 內連結必須是相對路徑（portable 原則），遠端若改成絕對路徑要修正推回。
- 同步完本地 `.claude/skills/` 後，有 `content/skills/` 鏡像的 skill 要同步更新鏡像（pre-commit hook 會提醒）。

## 跟 Codex / 其他 agent 的差異

本 repo 同時支援 Claude Code 跟 Codex。差異點：

- **規範**：CLAUDE.md 跟 AGENTS.md 共用內容（透過 `@AGENTS.md`）、Codex 直接讀 AGENTS.md
- **Skill**：路徑不同（Claude Code 用 `.claude/skills/`、Codex 用 `.agents/skills/`）— 本 repo 用 directory symlink 共用（`.agents/skills` → `../.claude/skills`）、改 `.claude/skills/<name>/` 兩工具同步生效
- 詳見 AGENTS.md §11
