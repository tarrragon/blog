---
title: "本 blog 專案的 GitHub Actions workflow"
date: 2026-05-06
description: "以本 blog 專案為例，整理 .github/workflows 底下所有 workflow 的觸發條件、責任、失敗處理與維護注意事項"
tags: ["CI", "GitHub Actions", "workflow", "blog維護"]
weight: 1
---

本 blog 的 GitHub Actions workflow 負責把內容檢查、瀏覽器回歸測試、Hugo 發布與 Claude 協作分成不同自動化流程。每條 workflow 都是一個獨立入口；維護時要先分清楚它是在保護內容品質、使用者行為、發布產物，還是協作流程。

## Workflow 總覽

本專案目前有五條 workflow。三條屬於 CI / CD 主流程，兩條屬於 Claude 協作輔助流程。

| Workflow                    | 檔案                                       | 觸發條件                           | 核心責任                          |
| --------------------------- | ------------------------------------------ | ---------------------------------- | --------------------------------- |
| `md-check`                  | `.github/workflows/md-check.yml`           | push / pull request 到 `main`      | 檢查 content Markdown 契約        |
| `Playwright tests`          | `.github/workflows/playwright.yml`         | push / pull request 到 `main`      | 驗證瀏覽器層行為與版面回歸        |
| `Deploy Hugo site to Pages` | `.github/workflows/deploy.yml`             | push 到 `main`                     | 建置 Hugo、產生搜尋索引並部署     |
| `Claude Code`               | `.github/workflows/claude.yml`             | issue / comment / review 叫 Claude | 讓 Claude 讀 issue、PR 與 CI 結果 |
| `Claude Code Review`        | `.github/workflows/claude-code-review.yml` | PR opened / synchronize 等事件     | 對 PR 進行 Claude code review     |

這張表的責任是提供入口。看到 GitHub Actions 紅燈時，先對照 workflow 名稱，把失敗歸到內容檢查、瀏覽器測試、部署或協作流程。

## `md-check`

`md-check` 的責任是讓 `content/` 裡的 Markdown 維持同一套結構契約。它會先用 Go build 出 `scripts/mdtools`，再依序執行 formatter 檢查、lint 與卡片連結檢查。

```yaml
name: md-check
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

這條 workflow 的核心步驟是：

1. `actions/checkout@v6`
2. `actions/setup-go@v6`
3. `go build -o ../../bin/mdtools`
4. `./bin/mdtools fmt --check content/`
5. `./bin/mdtools lint content/`
6. `./bin/mdtools cards content/`

`md-check` 失敗時，下一步是回本機跑同一組命令。`fmt --check` 失敗代表格式可由 `fmt --fix` 修正；`lint` 失敗代表標題、front matter、URL、code block 等結構契約不符；`cards` 失敗代表卡片連結、orphan 或 K4 規則需要修。

```bash
./bin/mdtools fmt --check content/
./bin/mdtools lint content/
./bin/mdtools cards content/
```

維護這條 workflow 時，規則來源要和 [Blog Markdown 寫作規範與 mdtools 檢查](/posts/markdown-writing-spec/) 對齊。改 `scripts/mdtools/internal/rules/` 時，也要同步更新規範文章，避免 CI 行為和文件描述分叉。

## `Playwright tests`

`Playwright tests` 的責任是驗證使用者可見行為。它會先建出完整 Hugo site 與 Pagefind index，再用 Chromium 驗證搜尋、版面與互動。

```yaml
name: Playwright tests
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

這條 workflow 的核心步驟是：

1. checkout，並包含 submodules
2. 安裝 Hugo `0.148.2` extended
3. 安裝 Node `24`
4. `npm ci`
5. `npx playwright install --with-deps chromium`
6. `make site`
7. `npx playwright test`
8. 失敗時上傳 `playwright-report/`

`make site` 是這條 workflow 的關鍵前置條件。它會產生 Hugo 靜態檔與三份 Pagefind index：`pagefind`、`pagefind-title`、`pagefind-content`。如果只跑 `hugo --minify` 就跑 Playwright，搜尋測試會因為缺少 index 而失敗。

Playwright 失敗時，下一步是下載 `playwright-report` 或讀 error context。若失敗發生在搜尋頁，先確認 `make site` 是否完整成功；若失敗發生在版面，先看 screenshot、bounding box 或 computed style；若失敗發生在互動，先看 selector 是否仍對準真實 DOM。

```bash
make site
npm test
```

維護這條 workflow 時，測試要守使用者行為，不應只守 implementation detail。像 TOC RWD 這類版面行為，可以用 viewport 測試固定桌面、筆電與手機三種狀態。

## `Deploy Hugo site to Pages`

`Deploy Hugo site to Pages` 的責任是把 `main` 上的內容建置成 GitHub Pages artifact 並部署。它只在 push 到 `main` 時觸發，不在 pull request 上部署。

```yaml
name: Deploy Hugo site to Pages
on:
  push:
    branches:
      - main
```

這條 workflow 有兩個 job：

| Job      | 責任                                     | 關鍵設定                 |
| -------- | ---------------------------------------- | ------------------------ |
| `build`  | checkout、Hugo build、Pagefind、artifact | `runs-on: ubuntu-latest` |
| `deploy` | 發布 GitHub Pages                        | `needs: build`           |

`build` job 會先跑 `hugo --minify`，並把輸出寫到 `hugo-build-output.txt`。目前它設了 `continue-on-error: true`，所以 Hugo build 失敗時會進入 Claude Debug 步驟，嘗試讓 Claude 分析錯誤並 commit 修復。

`Fail if build was not fixed` 是第二道保護。若原本 Hugo build 失敗，workflow 會重新跑一次 `hugo --minify`；如果 Claude 沒修好，這一步會讓 workflow 停止。

Pagefind index 會在 Hugo build 後產生：

```bash
npx -y pagefind --site public --root-selector main
npx -y pagefind --site public --root-selector "article.article-content > h1" --output-subdir pagefind-title
npx -y pagefind --site public --root-selector ".article-body" --output-subdir pagefind-content
```

Deploy 失敗時，下一步先分層判讀。若 `build` job 失敗，回到 Hugo 或 Pagefind；若 `Upload artifact` 成功但 `deploy` job 失敗，檢查 Pages environment、permission、artifact 與 GitHub Pages 設定。

這條 workflow 目前的注意事項是：deploy workflow 自己沒有直接 `needs` `md-check` 或 `Playwright tests`，因為它們是獨立 workflow。這是本專案目前的實際邊界；gate 設計原理見 [CI gate 與 workflow 邊界](../../ci-gate-workflow-boundary/)。

## `Claude Code`

`Claude Code` 的責任是提供互動式 Claude 協作入口。它不會在每次 push 自動修程式，而是在 issue、comment 或 review 內容包含 `@claude` 時觸發。

```yaml
on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
  issues:
    types: [opened, assigned]
  pull_request_review:
    types: [submitted]
```

這條 workflow 的 gate 寫在 job `if`。只有以下情境會真正執行：

- issue comment 包含 `@claude`
- pull request review comment 包含 `@claude`
- pull request review body 包含 `@claude`
- issue title 或 body 包含 `@claude`

這條 workflow 給 Claude `actions: read` 權限，讓它能讀 PR 上的 CI 結果。這對「請 Claude 看 CI 為什麼失敗」很重要，因為 Claude 需要讀 workflow run、job log 或 check 結果才能判斷。

維護這條 workflow 時，重點是權限最小化。它目前給的是 `contents: read`、`pull-requests: read`、`issues: read`、`id-token: write`、`actions: read`，適合互動分析；若未來要讓 Claude 直接 commit，才需要重新評估寫入權限與保護條件。

## `Claude Code Review`

`Claude Code Review` 的責任是在 PR 事件發生時跑 Claude code review。它和 `Claude Code` 不同，前者是 PR review automation，後者是被 `@claude` 叫起來的互動入口。

```yaml
on:
  pull_request:
    types: [opened, synchronize, ready_for_review, reopened]
```

這條 workflow 使用 `code-review@claude-code-plugins`，prompt 是：

```text
/code-review:code-review ${{ github.repository }}/pull/${{ github.event.pull_request.number }}
```

它的責任是提供 review 視角。Claude review 可以指出風險、邏輯問題或測試缺口；真正阻擋合併與發布的責任仍在 [Required Checks](/ci/knowledge-cards/required-checks/)、測試 workflow 與 deploy gate。

維護這條 workflow 時，可以依 PR 類型決定是否加 path filter。若未來只想在程式碼或 workflow 變更時觸發，可打開 `paths` 設定；若希望文章內容也被 review，就維持目前全 PR 觸發。

## 本專案的發布阻擋邊界

本 blog 的發布阻擋邊界需要同時看 YAML 與 GitHub repository 設定。這一節只記錄本專案目前能從 YAML 判讀出的事實；required checks、environment protection 與 artifact handoff 的原理不在本頁展開。

目前從 YAML 可直接確認的阻擋關係是：

| 關係                      | 是否在 YAML 中明確存在 | 說明                                            |
| ------------------------- | ---------------------- | ----------------------------------------------- |
| `deploy` 等 `build`       | 是                     | `deploy` job 有 `needs: build`                  |
| `deploy` 等 `md-check`    | 否                     | `md-check` 是另一條 workflow                    |
| `deploy` 等 Playwright    | 否                     | `Playwright tests` 是另一條 workflow            |
| PR 需要通過測試才能合併   | 需查 repository 設定   | 需要看 GitHub branch protection 設定            |
| Pages deploy 需要人工審核 | 需查 environment 設定  | 需要看 GitHub Pages environment protection 設定 |

若日後發現測試紅燈但 Pages 仍發布，本頁只負責指出目前 workflow 邊界；具體改法回到 [CI gate 與 workflow 邊界](../../ci-gate-workflow-boundary/) 判斷，並對照 [Required Checks](/ci/knowledge-cards/required-checks/) 與 [Environment Protection](/ci/knowledge-cards/environment-protection/)。

## 失敗時的維護路由

失敗時的維護路由要先定位 workflow，再定位 job，再回到本機重現。這能避免在錯誤層修錯問題。

| 紅燈位置               | 優先看什麼                          | 本機重現命令                        |
| ---------------------- | ----------------------------------- | ----------------------------------- |
| `md-check`             | mdtools 訊息                        | `./bin/mdtools lint content/`       |
| `Playwright tests`     | `playwright-report` / error context | `make site` 後 `npm test`           |
| `Deploy` 的 Hugo build | `hugo-build-output.txt`             | `hugo --minify`                     |
| `Deploy` 的 Pagefind   | Pagefind command output             | `make site`                         |
| `Deploy` 的 Pages step | artifact / permission / environment | GitHub Actions UI + Pages 設定      |
| `Claude Code`          | secret / permission / trigger `if`  | 檢查 `@claude` 觸發文字與 secrets   |
| `Claude Code Review`   | plugin marketplace / token          | 檢查 PR event、secret 與 action log |

這份路由也可以當維護 checklist。新增 workflow 時，至少要補三件事：觸發條件、失敗時看哪個 artifact 或 log、本機要用哪條命令重現。

## 本專案維護注意事項

本專案維護注意事項的責任是記錄和目前 YAML 直接相關的操作提醒。這些提醒隨 workflow 實作改變而更新，不承擔通用 CI 設計原理。

- `Playwright tests` 依賴 `make site` 產生 Pagefind index；搜尋測試失敗時先確認 production build 是否完整。
- `deploy.yml` 的 Hugo build 使用 `continue-on-error: true`，後面用 Claude Debug 與 retry build 接住失敗。
- `Claude Code` 目前是 read-oriented 互動入口；若未來要寫入 repo，需要重新審核 permission。
- `.github/workflows/*.yml` 有實作變更時，要同步更新本頁，讓維護入口維持可信。

## 下一步路由

- CI 紅燈處理流程：讀 [CI 失敗到修復發布流程](../../github-actions-failure-flow/)。
- CI gate 設計原理：讀 [CI gate 與 workflow 邊界](../../ci-gate-workflow-boundary/)。
- CI 在可靠性模組的位置：讀 [6.1 CI pipeline](/backend/06-reliability/ci-pipeline/)。
- 發布 gate 設計：讀 [6.8 Release Gate 與變更節奏](/backend/06-reliability/release-gate/)。
- Markdown 檢查規則：讀 [Blog Markdown 寫作規範與 mdtools 檢查](/posts/markdown-writing-spec/)。
