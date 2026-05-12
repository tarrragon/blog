---
title: "6.2 tool use 與 MCP server 的權限模型"
date: 2026-05-12
description: "個人 dev 場景下 tool use / MCP server 的副作用權限：檔案系統 / shell / 網路存取邊界、第三方 MCP 信任、副作用的可逆性"
tags: ["llm", "security", "tool-use", "mcp", "permission", "agent"]
weight: 3
---

[Tool use](/llm/knowledge-cards/tool-use/) 跟 [MCP](/llm/knowledge-cards/mcp/) server 是本地 LLM 對主機資源最大的副作用面。本章把「這個 tool 能做什麼」「MCP server 跑了會碰到什麼檔案」「能不能 rollback」整理成可操作的權限判讀。原理層的副作用範圍 spectrum、可逆性分級見 [4.1 Tool use 原理](/llm/04-applications/tool-use-principles/)、agent 跟人類審查的協作模型見 [4.2](/llm/04-applications/agent-architecture/)；hands-on 驗證「LLM 自己沒 FS / shell 權限、wrapper 才有」見 [Ollama 改檔案的權限邊界](/llm/01-local-llm-services/hands-on/permission-boundary/)。隔離技術見 [sandbox](/llm/knowledge-cards/sandbox/) 卡、權限白名單見 backend [allowlist](/backend/knowledge-cards/allowlist/) 跟 [least-privilege](/backend/knowledge-cards/least-privilege/) 卡。本章 framing 是個人 dev 視角；production agent 場景下 tool use 引發的 prompt injection 後果見 [backend/07 LLM agent prompt injection](/backend/07-security-data-protection/llm-prompt-injection-in-agent/)。

讀完本章後、你應該能對自己用的 tool / MCP server 回答：能讀寫哪些路徑、能跑哪些 shell command、能連哪些網路位址、副作用有沒有 dry-run / preview、出錯時怎麼回退。

## 本章目標

1. 認識 tool use 跟 MCP server 在三層架構中的位置。
2. 區分「讀取類 tool」跟「副作用類 tool」的權限判讀差異。
3. 知道個人 dev 場景下、第三方 MCP server 的信任邊界跟驗證流程。
4. 用「沙箱 / 白名單 / 副作用可逆性」三個維度評估具體 tool / MCP 的風險。
5. 認識常見的 tool use 副作用洩漏路徑跟對應的最低防護。

## tool use 跟 MCP server 在哪一層

tool use 跟 MCP server 同時跨[三層架構](/llm/00-foundations/three-layer-architecture/) 的兩層、但跟模型本身的權限模型分離：

```text
介面層（VS Code / Continue.dev / CLI）
  ↓
推論伺服器（Ollama / llama-server / LM Studio）
  ↓
模型（GGUF 權重）

旁邊另一條：
  ↓
MCP server（獨立 process、自己的權限）
  └── 對檔案 / shell / 網路的具體 API
```

關鍵特性：

1. **模型本身不執行 tool**：模型只生成 tool call JSON、實際執行由「LLM client」（如 Continue.dev、Claude Desktop）跟 MCP server 完成。
2. **MCP server 是獨立程式**：可以是 Node / Python script、可以呼叫任何系統 API、權限上限是「跑該 server 的 user 的權限」。
3. **權限不是模型給的、是 OS / user 給的**：模型再怎麼「同意」執行 `rm -rf /`、實際上能不能跑取決於 OS 的權限模型跟 MCP server 自己的 sandbox。

> **事實查核註**：[Model Context Protocol（MCP）](https://modelcontextprotocol.io) 是 Anthropic 在 2024 年底發布的開放協議、各家 LLM client 跟 MCP server 實作的成熟度、權限粒度依版本演進。本章描述以 2026 年 5 月主流實作為基準、引用前以 MCP 官方規格跟各 client / server 的 README 為準。

## 「讀取類」跟「副作用類」tool 的權限差異

tool 可以粗分成兩類、權限判讀完全不同：

| 類別     | 例子                                                           | 主要風險                                   | 個人 dev 場景的接受程度                |
| -------- | -------------------------------------------------------------- | ------------------------------------------ | -------------------------------------- |
| 讀取類   | read file、grep、search code、查 git log                       | 把私密內容讀進 prompt、prompt 被洩漏出去   | 較高、但要注意 prompt 傳到哪個 LLM     |
| 副作用類 | write file、run shell、git commit、發 HTTP request、操作資料庫 | 不可逆改變、損毀檔案、發送請求、洩漏到外部 | 較低、需要 preview / confirm / sandbox |

讀取類的判讀重點是「**讀到的內容會被傳到哪**」：

1. 讀到的 code 變 prompt 的一部分、prompt 送到本地模型→沒外洩
2. 同樣 prompt 送到雲端 LLM→傳到雲端、跟雲端 LLM 的資料政策走（見 [6.4 跨雲端 / 本地資料邊界](/llm/06-security/cross-cloud-local-data-boundary/)）
3. 讀取會被 log→log 累積、需要管理

副作用類的判讀重點是「**可逆性**」：

1. write file 蓋掉原內容→可能無法回復（沒備份的話）
2. run shell `rm` / `git push`→不可逆或需要 force pull 才能還原
3. 發 HTTP request、轉帳、call API→送出去就回不來
4. 操作 production 資料庫→可能影響其他人

## 三個維度評估具體 tool / MCP 的風險

對任何 tool / MCP server、可以用三個維度做初步評估：

```text
┌────────────────────────────────────────────────────┐
│ 維度一：沙箱                                       │
│   能做什麼 = 跑該 server 的 user 能做什麼          │
│   有沒有 chroot / Docker / namespace 隔離？        │
│                                                    │
│ 維度二：白名單                                     │
│   能讀寫的路徑、能跑的指令、能連的網址有沒有限定？  │
│   還是 "all paths" / "any shell" / "any URL"？     │
│                                                    │
│ 維度三：副作用可逆性                               │
│   出錯能不能 rollback？                            │
│   有沒有 dry-run / preview / confirm？             │
└────────────────────────────────────────────────────┘
```

對應的判讀範例：

| Tool / MCP                       | 沙箱          | 白名單                 | 副作用可逆性                       | 個人 dev 評估            |
| -------------------------------- | ------------- | ---------------------- | ---------------------------------- | ------------------------ |
| `read_file`（讀任意路徑）        | 無、user 權限 | 無、可讀 user 所有檔案 | N/A（讀取無副作用）                | 注意 prompt 走向         |
| `read_file` 限定 workspace       | 無            | 有、只讀 workspace     | N/A                                | 較安全                   |
| `run_shell`（任意指令）          | 無            | 無                     | 視指令、`rm` / `git push` 不可逆   | 高風險                   |
| `apply_patch`（套 diff 到 file） | 無            | 限定 workspace         | git stash 可逆、未 stash 不可逆    | 中風險、值得用 git track |
| `fetch_url`（任意 URL）          | 無            | 無                     | 一般 GET 可逆、POST 不可逆         | 看具體請求               |
| `mcp-server-postgres`（直連 DB） | 無            | 視 DB user 權限        | 改 row 通常可逆、DROP TABLE 不可逆 | DB user 權限要設好       |

實務上、社群常見的 MCP server 多半屬於「白名單較弱」「副作用直接套用」的設計、需要使用者自己加防護。

## 第三方 MCP server 的供應鏈信任

MCP server 是可執行程式碼、信任邊界比 GGUF 模型權重高一個層級。常見的 MCP server 來源：

1. **官方 reference server**（如 Anthropic 維護的 `@modelcontextprotocol/server-*`）：相對較高信任、有官方 maintain。
2. **知名專案的 MCP server**（如 GitHub、Notion、Slack 等公司自己出的）：跟該公司的軟體分發信任度一致。
3. **社群 MCP server**：個人或小團隊維護、信任度視 maintainer 與 download 量、看 code 是基本動作。

裝任何 MCP server 前的最低判讀：

1. **看 source repo**：是不是知名作者、stars 數、最後 commit 時間、issues 是否活躍。
2. **看實際做什麼**：MCP server 的 README 通常列出提供的 tools、跑起來會碰到的權限。
3. **跑在最小權限環境**：能用 Docker / chroot / `nice -n 19` 之類就用、不要直接用 root / admin。
4. **不要用 `curl | sh` 安裝**：用 `npm install` / `pip install` / `go install` 等有 package manager 介入的方式、留下 install log。

> **事實查核註**：MCP server registry、套件管理工具的供應鏈安全機制依版本演進、Anthropic 跟其他主要 client 廠商可能引入官方 marketplace 或簽章機制、建議引用前以當前 MCP 官方狀態為準。

## 個人 dev 場景的最低防護建議

對「我想用 tool use 但又怕 LLM 把檔案搞壞」的工作流、最低防護建議：

1. **codebase 用 git track**：所有寫入操作前確認 working tree clean、出問題能 `git checkout` 還原。`git stash` 是更輕的選擇。
2. **重要檔案 backup**：dotfile、SSH key、雲端 API key 等不在 git track 範圍的、用 Time Machine / rsync / cloud sync 之類做日常 backup。
3. **跑 LLM agent 時用獨立 user / 容器**：對「想試 agent 但怕」的場景、開個專用 macOS user 或 Docker container、user 沒 sudo、檔案存取限定 workspace。
4. **MCP server 的 config 加白名單**：能設 allowed paths / allowed commands / allowed URLs 的 server 都先設、預設拒絕、按需開放。
5. **看不懂的 tool call 不要 confirm**：Continue.dev / Claude Desktop 等 client 通常會 prompt 使用者確認 tool 執行、看不懂的 JSON 先別按。

## tool use 副作用洩漏的常見路徑

個人 dev 場景常見的 tool use 副作用洩漏路徑：

1. **LLM 誤把 secret 寫進 commit**：tool use 帶 `git commit`、LLM 從 `.env` 讀到 API key 又寫進 commit message。對應防護：MCP server 加 `.env` 黑名單、commit hook 掃 secret。
2. **LLM 套用 broken patch 蓋掉檔案**：`apply_patch` 失敗 / 部分套用、留下無法 compile 的狀態。對應防護：套 patch 前 `git stash` 或 `git add -p` 先存 working tree。
3. **LLM 從 issue / PR 內容引發指令**：讀進 issue 的 prompt 內容包含 prompt injection、誘導跑非預期指令。對應防護：tool 跑前明確讓使用者確認（見 [6.3 prompt injection](/llm/06-security/prompt-injection-in-ide/)）。
4. **LLM 觸發 production 操作**：MCP server 連到 production DB、LLM 跑 `DROP TABLE`。對應防護：production credential 絕對不放在 tool use 可達的環境。

## 給讀者的 tool / MCP 評估清單

每次裝新 MCP server / 啟用新 tool 之前、跑一次評估：

```text
[ ] 來源是知名作者 / 官方專案 / 我能 audit 的開源 repo
[ ] README 列出的 tool 列表、跟我的使用情境匹配
[ ] 該 server 跑在最小權限環境（user / sandbox / container）
[ ] 副作用類 tool 有 confirm / preview 機制
[ ] workspace 內容受 git track、能 rollback
[ ] 不放 production credential / SSH key 在該 server 可達的環境
[ ] 啟用後跑簡單測試、確認 tool call 行為符合預期
```

## 小結

tool use 跟 MCP server 對主機資源的副作用面、是個人 dev 場景下安全議題的最大來源。風險不在「LLM 變壞」、而在「tool 本身的權限沒設好」+「LLM 容易被 prompt injection 操縱」。個人 dev 場景的合理防護是「讀取類 tool 注意 prompt 走向、副作用類 tool 用 git track + sandbox + confirm」、不需要 enterprise-grade 沙箱、但 git working tree 跟最小權限是底線。

下一章：[6.3 IDE 場景的 prompt injection](/llm/06-security/prompt-injection-in-ide/)、處理 tool use 副作用最常見的觸發來源。
