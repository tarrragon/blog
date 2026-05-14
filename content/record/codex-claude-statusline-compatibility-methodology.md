---
title: "Codex 與 Claude Code Statusline 相容設計方法"
date: 2026-05-13
draft: false
description: "用 case-first 查詢與 WRAP 判讀，整理 Claude Code statusLine 與 Codex tui.status_line 的差異，說明如何讓同一個 statusline 工具保留 Claude 原功能並預留 Codex 相容入口。"
tags: ["Codex", "Claude Code", "statusline", "AI協作心得", "方法論"]
---

## 問題錨點

Statusline 相容設計的核心責任是把「資料輸入契約」和「畫面渲染邏輯」分開。Claude Code 已經提供 command-backed statusline，會把 session JSON 丟進命令的 stdin；Codex 目前公開的設定則是 `tui.status_line` 字串項目陣列，契約停在內建 footer item 的排列與選擇。

這個差異讓「同一個 statusline 工具同時支援兩邊」要從輸入契約對齊開始。真正要做的是先建立一層輸入正規化：Claude JSON、Codex 既有或未來 JSON、手動測試 JSON 都先轉成同一個內部狀態，再交給同一套 renderer。

## Case-first 觀察

Case-first 查詢的目的，是先看社群實際卡在哪裡，再決定要改工具還是改使用方式。本次查詢到的案例集中在 OpenAI Codex repo issue 與官方文件，顯示需求已經存在，但 Codex 的 command-backed statusline 仍屬提案或缺口。

| Case                                                                                  | 觀察                                                                                                   | 判讀                                                                                                        |
| ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| [Claude Code status line 官方文件](https://code.claude.com/docs/en/statusline)        | Claude Code 的 statusline command 會從 stdin 收到 JSON，stdout 的每一行會顯示成 status area。          | Claude 端是穩定可用的 producer，工具可依賴 `model`、`workspace`、`context_window`、`rate_limits` 這類欄位。 |
| [OpenAI Codex config reference](https://developers.openai.com/codex/config-reference) | `tui.status_line` 的型別是 `array<string>` 或 `null`，用途是排列 footer status-line item identifiers。 | Codex 端目前公開契約屬於內建項目清單。                                                                      |
| [openai/codex #17827](https://github.com/openai/codex/issues/17827)                   | 使用者明確要求 Codex 加入類似 Claude Code 的 `statusLine.command`。                                    | 社群已把 Claude Code statusline 當成對照基準，混用痛點是真實需求。                                          |
| [openai/codex #20043](https://github.com/openai/codex/issues/20043)                   | 提案列出 Codex 既有 `status_line` picker，並要求外部 command 模式、ANSI 顏色與 stdin JSON。            | 未來若 Codex 採納此類設計，statusline 工具需要同時支援 Codex 風格 JSON 與 Claude 欄位。                     |
| [openai/codex #20244](https://github.com/openai/codex/issues/20244)                   | 另一個使用者提出 command-backed item 或 persistent banner，並被標為 #17827 的 duplicate。              | 重複 issue 表示需求已經多次出現；相容設計應預留 Codex command input，讓後續定案只需要調整 mapper。          |
| [openai/codex #21324](https://github.com/openai/codex/issues/21324)                   | 使用者在 local branch 實作 context/token usage 狀態項目與進度條。                                      | Codex 社群也在補足使用量可視化，但路徑偏向內建 item，和 Claude 的外部 renderer 是兩種不同擴充模型。         |

## WRAP 判讀

Anchor Check：目標是讓 `cc-statusline` 的核心能力可被兩種工具共用。使用者真正需要的是少維護一套 statusline 邏輯，並在 Codex 具備 command-backed 入口時保留既有 renderer。

Step 0 資料充足度：足以做工具內部改造，尚不足以宣稱 Codex TUI 目前能直接執行 `cc-statusline`。官方文件只保證 `tui.status_line` 是字串陣列；社群 issue 裡的 command JSON 仍是提案階段。

Widen Options：可選方案有三種。

| 選項                                       | 策略                                                        | 適用條件                                                                                |
| ------------------------------------------ | ----------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| A：只用 Codex 內建 `tui.status_line`       | 不改 `cc-statusline`，在 Codex 設定內建項目。               | 只需要模型、目錄、git branch、context 這類內建欄位時可用。                              |
| B：改 `cc-statusline` 成雙 schema renderer | 保留 Claude JSON，新增 Codex / generic JSON normalization。 | 希望同一套 renderer 服務 Claude、未來 Codex command hook、tmux / wrapper 測試時最划算。 |
| C：Fork 兩套工具                           | Claude 一套、Codex 一套，各自用不同資料模型。               | 只有在兩邊 UI 契約長期分歧且需求完全不同時才合理。                                      |

Reality Test：目前 Codex 的公開設定停在內建 item 排列，所以 B 的立即價值是讓工具「具備 Codex 相容輸入能力」。反向驗證是：若未來 Codex 最終採用完全不同的 command JSON，B 的 normalization 層仍只需新增一個 mapper，renderer 可維持同一套。

Attain Distance：B 的長期成本最低，因為 statusline 最容易變動的是輸入欄位名稱，最穩定的是使用者想看的資訊：專案、環境、輸入法、模型、context、rate limit、git worktree。把欄位差異收斂在 normalization 層，能避免每加入一個工具就複製一次畫面邏輯。

Prepare to be Wrong：若 Codex 不採納外部 command statusline，這次改造仍可用於手動測試、tmux status、其他 wrapper，且不影響 Claude Code 原始入口。若 Codex 採納但欄位名稱不同，新增 mapper 即可。

Tripwire：當 OpenAI Codex 文件把 `tui.status_line` 從 `array<string>` 擴充為 command 或 table schema 時，重新檢查 `cc-statusline` 的 Codex mapper。若 Codex issue #17827 關閉並附帶實作 PR，也應重新校準欄位名稱。

## 實作策略

相容設計的正確切點是輸入正規化層。`cc-statusline` 應維持一個內部狀態模型，並接受多種外部 payload：

| 外部 payload             | 正規化規則                                                                                                                              |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| Claude Code              | 直接讀 `model.display_name`、`workspace.project_dir`、`context_window.used_percentage`、`rate_limits`。                                 |
| Codex proposed / generic | 接受 `model` 字串、`cwd` / `project_root`、`context.used_percent` / `context.remaining_percent`、`limits.five_hour` / `limits.weekly`。 |
| 手動測試 payload         | 只要能提供模型與目錄，就輸出可讀 statusline；缺 rate limit 時自動省略。                                                                 |

這個切點保留了 Claude Code 既有功能，因為原本的欄位不需要改名，也不需要改設定檔。新增行為只在非 Claude payload 進來時啟動，屬於向後相容的讀取能力。

## 操作路由

現在可立即使用的路由是 Claude Code 原設定：在 `~/.claude/settings.json` 裡設定 `statusLine.command` 指向 `cc-statusline`。這條路由使用官方支援的 stdin JSON，適合日常使用。

Codex 目前可立即使用的路由是內建 footer item：在 `~/.codex/config.toml` 設定 `tui.status_line = [...]`。這條路由使用 Codex 內建 renderer，能顯示 Codex 已支援的內建狀態。

未來 Codex 若支援 command-backed statusline，路由應該指向同一個 `cc-statusline` binary。工具端已經能接受 Codex / generic JSON 時，設定層只要補 command 指向，不需要重寫 renderer。

## 實測記錄（2026-05-14）

這次排查的核心責任是先確認「工具本身可用」還是「接入路由不對」。先把 binary 行為跟 TUI 設定拆開檢查，才能避免把路由問題誤判成程式 bug。

### 觀察

- `cc-statusline` 程式已支援 generic/Codex-style payload，手動餵 JSON 可正確輸出模型與 context 資訊。
- `~/.claude/settings.json` 使用 `statusLine.command` 指向 `/Users/mac-eric/go/bin/cc-statusline`，Claude Code 路由成立。
- `~/.codex/config.toml` 的 `tui.status_line` 是內建 item 陣列，這條路由不會執行外部 binary。
- Codex 內建 footer 的實際輸出已觀察到：`gpt-5.3-codex medium · Context 100% left · ~/project/blog`。

### 判讀

Codex 端「沒有生效」的主因是契約邊界：`tui.status_line` 只負責排列內建欄位，不負責執行 command。`cc-statusline` 的 renderer 相容能力屬於預留未來入口，不會在現有 Codex 內建 footer 流程自動觸發。

### 操作

為了讓 Codex 內建 footer 至少顯示模型與 context 資訊，已調整：

```toml
[tui]
status_line = ["model-with-reasoning", "context-remaining", "current-dir"]
status_line_use_colors = true
```

這個設定可讓 Codex 使用內建項目顯示 `model-with-reasoning` 與 context remaining；格式由 Codex 內建 renderer 決定，不等同 `cc-statusline` 的自訂輸出字串。

### 驗證指令

```bash
printf '%s\n' '{"model":"gpt-5.3-codex","reasoning_effort":"medium","project_root":"~/project/blog","context":{"remaining_percent":100}}' | /Users/mac-eric/go/bin/cc-statusline
```

預期結果是主行包含 `gpt-5.3-codex medium`，context 顯示為 `Context 100% left`。這一步驗證的是 binary 能力，不是 Codex 內建 footer contract。

## 檢查清單

- Claude Code 原本的 JSON payload 仍能輸出相同欄位。
- Codex / generic payload 不造成 parse error。
- `model` 同時支援 object 與 string。
- `context` 同時支援 used percentage 與 remaining percentage。
- rate limit 缺席時只省略對應 segment，不影響專案、模型、git worktree。
- README 明確標示 Codex 目前限制，避免讀者以為 Codex 已能直接執行外部 statusline command。
