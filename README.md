# blog

Tarragon 的個人技術部落格。內容涵蓋後端工程教學系列、開發過程的事後檢討、寫作方法論的 skill、以及給 Claude runtime 直接呼叫的 prompt-friendly skill 庫。

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

### 教學系列

| 區塊                                                                        | 內容                                                             |
| --------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| [go/](./content/go/) [go-advanced/](./content/go-advanced/)                 | Go 語言教材（語言精神 + 工程實踐 + 並發 / WebSocket / 服務架構） |
| [python/](./content/python/) [python-advanced/](./content/python-advanced/) | Python 教材（Hook 系統 + 內部機制 / 擴展開發）                   |
| [backend/](./content/backend/)                                              | 語言無關的後端能力 — 資料庫、快取、訊息佇列、觀測、部署、可靠性  |
| [ci/](./content/ci/)                                                        | CI/CD 教學 — 驗證、建置、發布 gate 與部署場域流程差異            |
| [cli/](./content/cli/)                                                      | CLI 圖形化工具 — TUI / ASCII 圖表 / 多工器 / 遠端操作選型        |
| [devops/](./content/devops/)                                                | DevOps 實務 — 負載平衡、水平擴展、流量管控、容量規劃             |
| [infra/](./content/infra/)                                                  | 基礎設施建置 — IaC、身分憑證、網路地基、環境分離                 |
| [llm/](./content/llm/)                                                      | 本地 LLM 寫 code 實務 — Apple Silicon + VS Code 整合             |
| [monitoring/](./content/monitoring/)                                        | 監控體系 — 事件分類、SDK 設計、collector 架構、行為資料商業利用  |
| [testing/](./content/testing/)                                              | 測試策略 — 三層分層、mock 遮蔽、protocol integration test        |
| [ux-design/](./content/ux-design/)                                          | 畫面設計 — 狀態矩陣、gate fallback、輸入機制、導航模式           |
| [business/](./content/business/)                                            | 商業概念與策略分析 — 商業模式、單位經濟、WRAP 案例拆解           |

### 筆記與檢討

| 區塊                                                                       | 內容                                                                         |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| [posts/](./content/posts/)                                                 | Blog 規範文件、設計筆記、Hugo / Markdown 操作經驗、AI 協作心得               |
| [posts/markdown-writing-spec.md](./content/posts/markdown-writing-spec.md) | mdtools 檢查規則的單一真實來源                                               |
| [report/](./content/report/)                                               | 開發過程的事後檢討（183 篇、含三層結構：抽象原則 / 情境檢討 / Pattern 卡片） |
| [record/](./content/record/)                                               | 開發中的 side project 紀錄                                                   |
| [work-log/](./content/work-log/)                                           | 工作上遇到的具體問題與解法                                                   |
| [skills/](./content/skills/)                                               | `.claude/skills/` 的公開鏡像（Claude runtime + 人類讀者雙重存取）            |
| [til/](./content/til/)                                                     | TIL 學習筆記 — 單字字源、概念由來、跨領域術語、冷知識                        |
| [other/](./content/other/)                                                 | OS / 工具小技巧等雜項                                                        |

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

# 安裝 git hooks（commit 前守 staged markdown；push 前跑 CI 同款全量檢查）
make install-hooks

# 手動跑檢查（CI 跑同樣三項）
make check
```

完整指令見 [`Makefile`](./Makefile)：`make help` 列出所有 target。

## 品質工具

### mdtools

自家寫的 markdown 工具鏈、走 goldmark AST、不靠 regex。三個子命令在 pre-commit、pre-push 與 CI 同時執行：

| 命令                | 角色                                                               |
| ------------------- | ------------------------------------------------------------------ |
| `mdtools fmt --fix` | 表格對齊（CJK 雙寬）、列表 / code block 前後空行、有序列表編號一致 |
| `mdtools lint`      | 標題層級、URL 反釣魚校驗、frontmatter 完整性                       |
| `mdtools cards`     | 卡片雙向完整性、orphan 偵測、相對連結有效性                        |

設計 rationale 見 [`content/posts/mdtools-design.md`](./content/posts/mdtools-design.md)、規則合約見 [`content/posts/markdown-writing-spec.md`](./content/posts/markdown-writing-spec.md)。

### Git hooks

`.githooks/pre-commit` 對 staged markdown 檔案跑快速檢查：

1. `fmt --fix` 後 re-stage（自動修排版）
2. `lint` 阻擋格式錯誤
3. `cards` 阻擋連結 / 卡片完整性錯誤

`.githooks/pre-push` 跑 `make check`，也就是 CI 的同款全量檢查：

1. `mdtools fmt --check content/`
2. `mdtools lint content/`
3. `mdtools cards content/`

`make install-hooks` 一次設定 — 之後 commit 與 push 時自動跑。用 `make hooks-status` 確認目前 repo 是否已指向 `.githooks`。

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

當前 skill（`.claude/skills/`）：

| Skill                            | 主題                                        | 公開鏡像 |
| -------------------------------- | ------------------------------------------- | -------- |
| `compositional-writing`          | 寫作方法論（Zettelkasten + 原子卡片）       | 有       |
| `multi-round-review`             | 多輪 agent reviewer 審查流程                | 無       |
| `requirement-protocol`           | 需求確認到實作的對話協議                    | 有       |
| `frontend-with-playwright`       | 前端開發協議 + Playwright 驗證              | 有       |
| `wrap-decision`                  | WRAP 決策框架 — 認知偏誤防護與選項擴增      | 有       |
| `case-first-module-workflow`     | Case-first + Agent team review 教學模組流程 | 無       |
| `content-extension-evaluation`   | 核心章節完成後的延伸內容評估                | 無       |
| `migration-playbook-methodology` | 跨 vendor migration playbook 寫作方法論     | 無       |
| `saas-tech-selection`            | SaaS repo 初始化時的設計與選型訪談協議      | 無       |

每個 skill 都自帶 `references/principles/`、跨專案複製即用。Skill 與遠端 skill 庫透過 `skill-sync` CLI 同步。

## 寫作方法論：compositional-writing

`.claude/skills/compositional-writing/` 是這個專案使用的寫作方法論 skill — 以 Zettelkasten 為核心、把每段文字看成可組合的原子卡片。

| 入口                                                              | 內容                                                                                                                      |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| [SKILL.md](./.claude/skills/compositional-writing/SKILL.md)       | 三大支柱 + 五大原則速查 + 觸發路由                                                                                        |
| [references/](./.claude/skills/compositional-writing/references/) | 14 份情境 reference（涵蓋程式碼註解 / 文件 / log / prompt / 文章 / 欄位 / 多篇 collection / metrics / 規範 / dry-run 等） |

文章版本（人類讀者直接在 blog 讀）：[content/skills/compositional-writing/](./content/skills/compositional-writing/)

## 結構決策

| 決策                                          | 來由                                                                                                                                                             |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.claude/skills/` 與 `content/skills/` 雙存在 | runtime 呼叫用 `.claude/`、人類讀用 `content/`、同內容兩種 surface（細節見「Skill vs 文章」段）                                                                  |
| `report/` 三層結構（抽象 / 情境 / Pattern）   | 從累積 180+ 篇事後檢討文章中演化、由 [`managing-article-collections.md`](./.claude/skills/compositional-writing/references/managing-article-collections.md) 規範 |
| Pagefind 而非 Algolia / Lunr                  | 純客戶端、無需後端、零維運成本（見 [`content/posts/pagefind-static-site-search.md`](./content/posts/pagefind-static-site-search.md)）                            |
| mdtools 用 Go + goldmark AST 而非 regex       | 規則複雜度與正確性兩者都需要、AST 比 regex 穩定（見 [`content/posts/what-is-ast.md`](./content/posts/what-is-ast.md)）                                           |

## 授權

內容採 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — 可自由轉載 / 改作、需標明 Tarragon 為原作者。

程式碼（`scripts/`、`layouts/`、`assets/`）採 MIT。
