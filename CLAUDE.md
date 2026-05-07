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

## 跟 Codex / 其他 agent 的差異

本 repo 同時支援 Claude Code 跟 Codex。差異點：

- **規範**：CLAUDE.md 跟 AGENTS.md 共用內容（透過 `@AGENTS.md`）、Codex 直接讀 AGENTS.md
- **Skill**：路徑不同（Claude Code 用 `.claude/skills/`、Codex 用 `.agents/skills/`）— 本 repo 用 directory symlink 共用（`.agents/skills` → `../.claude/skills`）、改 `.claude/skills/<name>/` 兩工具同步生效
- 詳見 AGENTS.md §11
