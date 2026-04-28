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

## 跟 Codex / 其他 agent 的差異

本 repo 同時支援 Claude Code 跟 Codex。差異點：

- **規範**：CLAUDE.md 跟 AGENTS.md 共用內容（透過 `@AGENTS.md`）、Codex 直接讀 AGENTS.md
- **Skill**：路徑不同（Claude Code 用 `.claude/skills/`、Codex 用 `.agents/skills/`）— 目前 repo 只維護 `.claude/skills/`、Codex 用戶要用需手動同步
- 詳見 AGENTS.md §11
