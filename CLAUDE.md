# Claude Code 入口

本專案的寫作規範、工程協議、agent 行為準則統一在 [`AGENTS.md`](./AGENTS.md)。

CLAUDE.md（本檔）只是 redirect — Claude Code 預設讀此檔、AGENTS.md 才是 SSoT。修改時改 AGENTS.md、本檔不重複。

## 快速路徑

依任務類型直接讀對應段落：

| 任務          | 讀                                                         |
| ------------- | ---------------------------------------------------------- |
| 寫文章        | AGENTS.md §1 寫作核心原則 + §5 產出流程 + §10 內容分類流程 |
| 寫卡片        | AGENTS.md §3 知識卡片規範 + §10 寫作前 due-diligence       |
| 寫 skill      | AGENTS.md §9 Skill 撰寫規範                                |
| 改 markdown   | `content/posts/markdown-writing-spec.md`（含 §6.5 slug）   |
| 跑分析 / 決策 | AGENTS.md §4 WARP 方法                                     |
| 提交 / commit | 不可繞過 pre-commit（`--no-verify` 禁用）— AGENTS.md §8    |

## 兩個 surface 不要混淆

|          | `.claude/skills/`                             | `content/`                 |
| -------- | --------------------------------------------- | -------------------------- |
| 讀者     | Claude runtime                                | 人類讀者透過 Hugo          |
| 規則     | 自包含、不引用 blog 卡片                      | 可自由 cross-link          |
| 規範文件 | `references/reference-authoring-standards.md` | `markdown-writing-spec.md` |

跨 surface 的引用會違反規範 — 寫 skill 時複製 principle 卡進 `references/principles/`、不寫外部連結（AGENTS.md §9.2-3）。
