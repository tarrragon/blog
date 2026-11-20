---
title: "Deferred Tool Loading（延遲載入）"
date: 2026-11-21
description: "agent 接了很多 MCP server、工具定義佔掉大半 context，或在 transcript 看到模型先呼叫 ToolSearch、tool search 才呼叫真正的工具時，延遲載入在做什麼、換到什麼、付出什麼"
weight: 1
tags: ["llm", "knowledge-cards", "coding-agent", "mcp", "context-window"]
---

Deferred tool loading（延遲載入，也有人稱 tool search）的核心概念是「**工具定義平常不放進模型的 context，模型要用到時先呼叫一支搜尋工具，命中的那幾支定義才放進 context**」。[Tool use](/llm/knowledge-cards/tool-use/) 的模型在兩次呼叫之間不保留狀態，工具定義原本每一次呼叫都要整份重送；延遲載入讓 context 裡只剩少數常駐的工具與一支搜尋工具，用它控制工具定義佔掉的 [context budget](/llm/knowledge-cards/context-budget/)。

## 跟其他概念的關係

延遲載入改變的是哪些工具定義進到這一次的 context，決定權在 runtime，所以它屬於 [harness](/llm/knowledge-cards/scaffold-vs-harness/) 那一層：工具仍然在建構時註冊，進不進 context 由 harness 或模型 API 在每一輪決定。

- **常駐工具**指定義在一次呼叫裡進了 context 的工具；**延遲載入的工具**指定義要先經過一次搜尋才放進 context 的工具。兩者是同一份工具清單依載入方式分成的兩組。
- **跟 [prompt cache](/llm/knowledge-cards/prompt-cache/) 的分工**：prompt cache 讓重送的工具定義計費較低、首字延遲較短，被快取的 token 仍然佔 context；延遲載入讓用不到的工具定義不佔 context。Anthropic API 的延遲載入把搜尋命中的定義加在對話歷史的尾端，不動快取前綴；工具全部常駐時，中途加一支工具就讓整段快取失效。
- **跟靜態篩選的分界**：靜態篩選由設定 agent 的人在啟動時決定開哪些工具，整個對話裡清單不變；延遲載入由模型在呼叫途中依任務搜尋。
- **跟 [MCP](/llm/knowledge-cards/mcp/) 的關係**：MCP 規格沒有工具搜尋的欄位。延遲載入可以做在 MCP server 端（`tools/list` 只回少數工具加一支搜尋工具），也可以做在 client 與模型 API 端（server 回完整清單，client 或 API 決定哪些進 context）。

## 可觀察訊號與例子

- **Claude Code**（2026 年 11 月的文件）：MCP 工具預設延遲載入，session 開始時只放工具名稱，模型先呼叫 `ToolSearch` 才拿到完整 schema；transcript 裡會看到 `ToolSearch` 出現在真正的工具呼叫之前。環境變數 `ENABLE_TOOL_SEARCH=auto` 時，MCP 工具定義合計不到 context window 的 10% 就全部常駐。
- **Anthropic API**：client 在工具上標 `defer_loading: true`，那些工具不放進 context，模型呼叫 Tool Search Tool 之後，API 把命中的工具展開成完整定義。
- **Atlassian 的 Rovo MCP server（v2 endpoint）**：一組 primary tools 直接列在 `tools/list`，其餘工具要先用 `discover` 搜尋，再經由讀、寫、破壞性三支以參數指定操作的工具執行。
- Anthropic 舉過一個載入五十多支 MCP 工具的 agent：工具定義約 7.2 萬 token，改成只載入搜尋到的工具之後，開始工作前的 context 合計約 8,700 token（〈Introducing advanced tool use on the Claude Developer Platform〉，2025-11-24）。

## 判斷條件與後果

1. **工具定義合計佔掉 context 的一大段、或名稱相近的工具很多時**，延遲載入同時減少 context 佔用與模型挑工具時的候選數；代價是每用到一支延遲載入的工具，模型就多生成一段搜尋呼叫，搜尋工具由 client 或 server 執行時還多一次來回。
2. **搜尋沒有回傳某支工具時**，模型不知道那支工具存在，外觀是回報做不到或改用相近而不對的工具，不會出現錯誤訊息；搜尋比對的是 description 這類欄位裡的字詞，description 開頭沒有使用者描述任務的用語時最容易落空。
3. **最常見的任務每次都要先搜尋時**，最常走的那條路徑每次都多一次往返；那幾支工具設成常駐（Anthropic 的 API 文件建議三到五支）就省掉這一段。
4. **工具定義合計本來就小時**，延遲載入省下的 context 很少，往返與搜尋落空照樣存在，全部常駐的總成本較低。

延遲載入做在哪一端、搜尋的單位、跟靜態篩選與程式碼執行的取捨，以及兩端都做時兩層搜尋的換法，在 [4.24 MCP 工具數量多時工具定義怎麼交給模型](/llm/04-applications/mcp-tool-surface-design/)。
