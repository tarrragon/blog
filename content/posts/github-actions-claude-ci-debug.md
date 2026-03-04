---
title: "用 Claude Code GitHub Actions 自動除錯 CI 建置失敗"
date: 2026-03-04
description: "在 GitHub Actions 中整合 Claude Code，讓 Claude 參與 CI 修復和 Code Review"
tags: ["GitHub Actions", "CI/CD", "Claude Code", "Hugo", "AI協作心得"]
---

## 這是什麼

[Claude Code GitHub Actions](https://github.com/anthropics/claude-code-action) 讓 Claude 直接參與你的 GitHub 工作流程，主要功能：

- **互動式助手** — 在 PR/Issue 留言 `@claude`，Claude 會分析程式碼並回覆
- **自動 Code Review** — PR 開啟時自動審查變更
- **CI 除錯修復** — build 失敗時自動分析錯誤並修復

<!--more-->

完整功能說明參考 [官方文件](https://code.claude.com/docs/en/github-actions)。

## 設定方式

### `/install-github-app`（推薦）

在 Claude Code 終端執行 `/install-github-app`，它會引導你完成所有設定。

流程中的關鍵步驟：

1. **選擇 repo** — 指定要安裝的 GitHub repository
2. **安裝 Claude GitHub App** — 自動安裝到指定 repo，授予 Contents、Issues、Pull requests 的 Read & Write 權限
3. **選擇認證方式** — 選擇 **long-life token** 會產生 OAuth token，自動寫入 GitHub Secrets 為 `CLAUDE_CODE_OAUTH_TOKEN`
4. **建立 workflow 檔案** — 自動建立並 push 兩個 workflow：
   - `claude.yml` — `@claude` 互動回覆
   - `claude-code-review.yml` — PR 自動 code review

完成後不需要額外設定。

### 手動設定（使用 Anthropic API Key）

如果不想用 `/install-github-app`，可以手動操作：

1. 前往 [github.com/apps/claude](https://github.com/apps/claude) 安裝 App 到你的 repo
2. 到 repo 的 **Settings → Secrets and variables → Actions**，新增 `ANTHROPIC_API_KEY`
3. 手動建立 workflow 檔案到 `.github/workflows/`

兩種認證方式的差異：

| 認證方式 | Secret 名稱 | 適用對象 |
|---------|------------|---------|
| OAuth Token | `CLAUDE_CODE_OAUTH_TOKEN` | Pro/Max 用戶，`/install-github-app` 自動設定 |
| API Key | `ANTHROPIC_API_KEY` | 直接使用 Anthropic API，需手動到 [console.anthropic.com](https://console.anthropic.com) 取得 |

## 加入 CI 自動除錯

`/install-github-app` 建立的 workflow 只處理 `@claude` 互動和 code review。如果你想在 **build 失敗時自動觸發 Claude 修復**，需要修改既有的 deploy workflow。

首先，補上 Claude 需要的權限（原本可能只有 `contents: read`）：

```yaml
permissions:
  contents: write        # Claude 需要寫入修復後的檔案
  pull-requests: write   # Claude 可能需要建立 PR
  issues: write          # Claude 回報結果
  pages: write           # 原本的 deploy 權限
  id-token: write        # 原本的 deploy 權限
```

然後在 build 步驟加入 Claude 除錯邏輯：

```yaml
# 在原本的 build step 加上 continue-on-error 和 id
- name: Build
  id: hugo-build
  run: hugo --minify 2>&1 | tee hugo-build-output.txt
  continue-on-error: true

# Build 失敗時觸發 Claude 除錯
- name: Claude Debug on Build Failure
  if: steps.hugo-build.outcome == 'failure'
  uses: anthropics/claude-code-action@v1
  with:
    # 依你的認證方式擇一
    claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
    # anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    prompt: |
      Hugo build failed. Here is the error output:

      $(cat hugo-build-output.txt)

      Please analyze the error, find the problematic file(s),
      fix the YAML front matter or content issue, and commit the fix.
    claude_args: "--max-turns 10"

# 修復後重新 build 驗證
- name: Retry build after fix
  if: steps.hugo-build.outcome == 'failure'
  run: hugo --minify
```

核心設計：

1. `continue-on-error: true` — build 失敗不中斷流程，讓後續 Claude 步驟有機會執行
2. `if: steps.hugo-build.outcome == 'failure'` — 只在失敗時觸發，正常 build 不消耗 API 額度
3. 修復後重新 `hugo --minify` 驗證是否成功

## 計費方式

計費取決於你使用哪種認證方式：

| 認證方式 | 計費來源 | 說明 |
|---------|---------|------|
| OAuth Token | **訂閱額度**（Pro/Max） | 跟 claude.ai 網頁、Claude Code CLI、Claude Desktop **共用同一個額度池** |
| API Key | **獨立 API 計費** | 按 token 用量付費，與訂閱額度完全分開 |

OAuth token 的額度是共用的，GitHub Actions 跑多了會擠壓你日常在 claude.ai 和 CLI 的使用額度。如果 CI 觸發頻繁，建議改用 API Key 避免互相影響。

詳細的費率可參考 [Claude 定價頁面](https://www.anthropic.com/pricing)。

### 降低成本的設定

| 設定 | 說明 |
|------|------|
| `--max-turns 10` | 限制迭代次數，避免無限循環 |
| 只在 `failure` 時觸發 | 正常 build 不消耗 API 額度 |
| `@claude` 觸發詞 | 互動模式只在明確呼叫時才啟動 |

## 搭配 CLAUDE.md

在 repo 根目錄建立 `CLAUDE.md`，Claude 會自動讀取作為上下文，提升修復準確度。

## 參考資料

- [Claude Code GitHub Actions 官方文件](https://code.claude.com/docs/en/github-actions)
- [claude-code-action GitHub Repo](https://github.com/anthropics/claude-code-action)
- [Setup Guide](https://github.com/anthropics/claude-code-action/blob/main/docs/setup.md)
