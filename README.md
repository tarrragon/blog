# blog

Tarragon 的個人技術部落格。內容涵蓋 Flutter / 後端開發筆記、開發過程的事後檢討、寫作方法論的 skill、以及給 Claude runtime 直接呼叫的 prompt-friendly skill 庫。

**Live**：<https://tarrragon.github.io/blog/>

## Tech Stack

| 元件                                                      | 角色                                                    |
| --------------------------------------------------------- | ------------------------------------------------------- |
| [Hugo](https://gohugo.io/)                                | Static site generator（v0.148.2）                       |
| [hugo-bearcub](https://github.com/janraasch/hugo-bearcub) | Theme                                                   |
| [Pagefind](https://pagefind.app/)                         | 客戶端搜尋（無需後端、index 隨 site 部署）              |
| [mdtools](./scripts/mdtools/)                             | 自家 Go + goldmark AST 寫的 markdown linter / formatter |
| GitHub Pages                                              | 部署目標、`.github/workflows/deploy.yml` 自動發布       |

## 內容組織

`content/` 依主題分區、每區自成一個 Hugo section：

| 區塊                                                                       | 內容                                                                        |
| -------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| [posts/](./content/posts/)                                                 | Blog 規範文件、設計筆記、Hugo / Markdown 操作經驗、AI 協作心得              |
| [posts/markdown-writing-spec.md](./content/posts/markdown-writing-spec.md) | mdtools 檢查規則的單一真實來源                                              |
| [report/](./content/report/)                                               | 開發過程的事後檢討（54 篇、含三層結構：抽象原則 / 情境檢討 / Pattern 卡片） |
| [skills/](./content/skills/)                                               | `.claude/skills/` 的文章版本（Claude runtime + 人類讀者雙重存取）           |
| [record/](./content/record/)                                               | 開發中的 side project 紀錄                                                  |
| [work-log/](./content/work-log/)                                           | 工作上遇到的具體問題與解法                                                  |
| [go/](./content/go/) `go-advanced/`                                        | Go 語言教材（語言精神 + 工程實踐）                                          |
| [python/](./content/python/) `python-advanced/`                            | Python 教材（以 Hook 系統為範例）                                           |
| [backend/](./content/backend/)                                             | 語言無關的後端能力、風險、決策                                              |
| [other/](./content/other/)                                                 | 其他雜項                                                                    |

每個 section 有自己的 `_index.md` 說明該區的範圍與閱讀路徑。

## 本地開發

### 環境需求

- Hugo extended ≥ 0.148.2
- Go ≥ 1.21（編譯 mdtools）
- Node.js（執行 `npx pagefind`）

### 常用指令

```bash
# Hugo 預覽（不含搜尋 index）
hugo server

# 完整 build：Hugo + Pagefind 搜尋 index
make site

# 安裝 git pre-commit hook（mdtools 自動 fmt / lint / cards）
make install-hooks

# 手動跑檢查（CI 跑同樣三項）
make check
```

完整指令見 [`Makefile`](./Makefile)：`make help` 列出所有 target。

## 品質工具

### mdtools

自家寫的 markdown 工具鏈、走 goldmark AST、不靠 regex。三個子命令在 pre-commit 與 CI 同時執行：

| 命令                | 角色                                                               |
| ------------------- | ------------------------------------------------------------------ |
| `mdtools fmt --fix` | 表格對齊（CJK 雙寬）、列表 / code block 前後空行、有序列表編號一致 |
| `mdtools lint`      | 標題層級、URL 反釣魚校驗、frontmatter 完整性                       |
| `mdtools cards`     | 卡片雙向完整性、orphan 偵測、相對連結有效性                        |

設計 rationale 見 [`content/posts/mdtools-design.md`](./content/posts/mdtools-design.md)、規則合約見 [`content/posts/markdown-writing-spec.md`](./content/posts/markdown-writing-spec.md)。

### Pre-commit hook

`.githooks/pre-commit` 對 staged markdown 檔案跑：

1. `fmt --fix` 後 re-stage（自動修排版）
2. `lint` 阻擋格式錯誤
3. `cards` 阻擋連結 / 卡片完整性錯誤

`make install-hooks` 一次設定 — 之後 commit 時自動跑。

### CI

GitHub Actions 在 push 到 `main` 時：

| Workflow                                | 角色                                       |
| --------------------------------------- | ------------------------------------------ |
| `md-check.yml`                          | 跑 mdtools 三項檢查                        |
| `deploy.yml`                            | Hugo build + Pagefind index → GitHub Pages |
| `claude.yml` / `claude-code-review.yml` | Claude AI code review                      |

## Skill vs 文章：兩種 surface

`.claude/skills/` 跟 `content/` 是兩個不同產出、規則互斥。同一份知識可以同時存在於兩處（如 `compositional-writing`）、但寫法不同。

|                     | `.claude/skills/`（skill）                  | `content/`（文章）                           |
| ------------------- | ------------------------------------------- | -------------------------------------------- |
| **讀者**            | Claude runtime 呼叫                         | 人類讀者瀏覽                                 |
| **目標**            | 跨專案 portable（複製整個目錄能移到別專案） | 服務本 blog 的脈絡與累積                     |
| **格式**            | H1 + body、**無 Hugo frontmatter**          | 有 Hugo frontmatter（`title` / `date` 必填） |
| **連結**            | 只能用 skill 內相對路徑                     | 可引用 report / posts / 其他 section         |
| **抽象原則**        | 複製進 `references/principles/`、自包含     | 直接寫在 `content/report/`                   |
| **Pre-commit lint** | 豁免 mdtools lint（fmt 仍跑）               | 跑全套 lint + cards                          |

完整撰寫規範見 [AGENTS.md §9 Skill 撰寫規範](./AGENTS.md#9-skill-撰寫規範區別於文章)。

當前 skill 數量（`.claude/skills/`）：

| Skill                      | 主題                           | 公開於 `content/skills/`？ |
| -------------------------- | ------------------------------ | -------------------------- |
| `requirement-protocol`     | 需求 → 實作對話協議            | ❌ 內部協議                |
| `frontend-with-playwright` | 前端開發協議 + Playwright 驗證 | ❌ 內部協議                |
| `compositional-writing`    | 寫作方法論（Zettelkasten）     | ✅ 對外公開                |

每個 skill 都自帶 `references/principles/`、跨專案複製即用。

## 寫作方法論：compositional-writing

`.claude/skills/compositional-writing/` 是這個專案使用的寫作方法論 skill — 以 Zettelkasten 為核心、把每段文字看成可組合的原子卡片。

| 入口                                                              | 內容                                                                                                               |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| [SKILL.md](./.claude/skills/compositional-writing/SKILL.md)       | 三大支柱 + 五大原則速查 + 觸發路由                                                                                 |
| [references/](./.claude/skills/compositional-writing/references/) | 10 份情境 reference（程式碼註解 / 文件 / log / prompt / 文章 / 欄位 / 多篇 collection / metrics / 規範 / dry-run） |

文章版本（人類讀者直接在 blog 讀）：[content/skills/compositional-writing/](./content/skills/compositional-writing/)

## 結構決策

| 決策                                          | 來由                                                                                                                                                            |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.claude/skills/` 與 `content/skills/` 雙存在 | runtime 呼叫用 `.claude/`、人類讀用 `content/`、同內容兩種 surface（細節見「Skill vs 文章」段）                                                                 |
| `report/` 三層結構（抽象 / 情境 / Pattern）   | 從累積 50+ 篇事後檢討文章中演化、由 [`managing-article-collections.md`](./.claude/skills/compositional-writing/references/managing-article-collections.md) 規範 |
| Pagefind 而非 Algolia / Lunr                  | 純客戶端、無需後端、零維運成本（見 [`content/posts/pagefind-static-site-search.md`](./content/posts/pagefind-static-site-search.md)）                           |
| mdtools 用 Go + goldmark AST 而非 regex       | 規則複雜度與正確性兩者都需要、AST 比 regex 穩定（見 [`content/posts/what-is-ast.md`](./content/posts/what-is-ast.md)）                                          |

## 授權

內容採 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — 可自由轉載 / 改作、需標明 Tarragon 為原作者。

程式碼（`scripts/`、`layouts/`、`assets/`）採 MIT。
