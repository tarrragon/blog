---
title: "4.24 MCP 工具數量多時工具定義怎麼交給模型：全部常駐的成本、延遲載入、靜態篩選、合併工具、拆給 subagent 與程式碼執行"
date: 2026-11-21
slug: "mcp-tool-surface-design"
description: "MCP server 工具數量多時，工具定義全部常駐的 context 佔用、選錯工具與 client 工具數上限；延遲載入（deferred loading、tool search）對往返、搜尋落空與 prompt cache 的影響，做在 server 端與做在 client 和模型 API 端的差別，以及搜尋的對象與一次載入的粒度；靜態篩選、client 預選、以任務為單位合併工具、拆給 subagent 與程式碼執行（Code Mode）這些不由模型搜尋工具定義的做法；寫 server 的人與設定 agent 的人依工具定義總量、任務範圍與呼叫串連選做法的條件，附 Stripe、Atlassian、Cloudflare、GitHub、Sentry 與 Anthropic 的做法對照"
tags: ["llm", "applications", "mcp", "tool-use", "context-budget"]
weight: 25
---

這篇整理 [MCP](/llm/knowledge-cards/mcp/) server 暴露的工具數量變多之後，工具定義怎麼交給模型：工具定義放進每一次呼叫的方式、全部放進 context 的成本（佔用 [context 預算（context budget）](/llm/knowledge-cards/context-budget/)、模型在名稱與 description 相近的工具之間選錯，以及 client 對工具數量的上限）、[延遲載入（deferred loading）](/llm/knowledge-cards/deferred-tool-loading/)（也有人稱 tool search 或 dynamic tool selection）的機制與它帶來的往返、搜尋落空以及對 prompt cache 的影響、延遲載入做在 MCP server 端與做在 client 和模型 API 端的差別、延遲載入搜尋的對象與一次載入的粒度、不由模型在呼叫途中搜尋工具定義的幾種做法（啟動時靜態篩選、client 在送出之前預選、以任務為單位合併工具、拆給 subagent、讓模型寫程式碼呼叫 API），以及寫 MCP server 的人與設定 agent 的人依哪些條件選做法。MCP 屬於架構協議層，function calling 屬於模型能力層，structured output 屬於 sampling 約束，三者的分層在 [4.6 應用層協議](/llm/04-applications/application-protocols/)；context 預算在 agent 各元件之間怎麼分配在 [4.17 Coding agent harness](/llm/04-applications/coding-agent-harness/) 的〈Context Budget 工程實務〉；prompt cache 怎麼比對前綴在 [4.18 Prompt caching 工程實務](/llm/04-applications/prompt-caching-engineering/)。工具在執行前的核准規則以什麼為單位、工具收進分派工具或程式碼執行工具時規則分得出哪些操作，以及 server 端確認與唯讀模式，在 [4.25 MCP 工具的核准規則與執行風險](/llm/04-applications/mcp-tool-approval-and-risk/)。

本篇引用的各家做法查證於 2026 年 11 月。工具名、數字、上限與預設值屬於產品功能，改版頻率比協議高，引用時以各家文件的現行版本為準。下文寫「從機制推論」的地方都沒有實測。

## 工具定義在每一次模型呼叫裡的位置與本篇用的名稱

MCP client 啟動時對每個 server 發出 `tools/list` 請求，取得那個 server 的工具清單。清單裡每一支工具帶著名稱、description 與 input schema（描述參數的 JSON Schema）。client 把這些定義放進送給模型 API 的 request，模型讀過定義才知道有哪些工具、每支工具的參數怎麼填，再產生呼叫。

工具定義因此佔 context window 的一段，而且每一次呼叫都要重送。模型在兩次呼叫之間不保留狀態，上一輪讀過的工具定義下一輪不在 context 裡，模型就呼叫不了那支工具。對話進行了幾十輪，同一份工具定義就被送了幾十次。

下文用三個名稱：

- **常駐工具**（Anthropic 文件寫作 non-deferred tools）：定義在一次呼叫裡進了模型 context 的工具。
- **延遲載入的工具**：定義不在這一次的 context 裡、要先經過一次搜尋才放進 context 的工具。放進來的是 server 決定格式的完整定義，或分派工具背後某個 API method 的參數說明。它的定義可能完全不在 request 裡，也可能在 request 裡而被標記成不放進 context，取決於延遲載入做在哪一端（〈延遲載入做在 MCP server 端或 client 與模型 API 端〉）。
- **分派工具**（dispatcher tool）：接受另一支工具的名稱或一個 API method 與參數、代為執行的工具，例如 Stripe 的 `stripe_api_read` 與 `stripe_api_write`、Atlassian 的 `executeRead`、`executeWrite` 與 `executeDestructive`。dispatcher 是軟體裡依名稱把呼叫轉給對應處理者的做法，[4.6](/llm/04-applications/application-protocols/) 寫的「function calling + 簡單 dispatcher」是同一個做法放在應用程式裡。接受一段程式碼、代為執行的工具（Cloudflare 的 `execute`）下文另稱程式碼執行工具。

## 工具定義全部常駐的成本：context 佔用、選錯工具與 client 的工具數上限

每一次呼叫都把全部工具定義放進 context，也就是工具全部常駐時，有三種成本，成因不同，分開算。

**context 佔用**是工具定義的 token 數。一支工具的大小取決於它的 description 與 schema 有多長，乘上 server 的工具數之後，工具定義合計的 token 數可能超過 system prompt 與對話歷史。Cloudflare 估算過，它的 API 有兩千五百多個 endpoint，假如把每個 endpoint 各包成一支 MCP 工具，用 tiktoken 量出的定義合計約 117 萬 token，Cloudflare 寫的是比當時最先進模型的整個 context window 還大（Cloudflare〈Code Mode: give agents an entire API in 1,000 tokens〉，2026-02-20）。Anthropic 在〈Introducing advanced tool use on the Claude Developer Platform〉（2025-11-24）舉的例子是一個載入五十多支 MCP 工具的 agent，工具定義約 7.2 萬 token，開始工作之前 context 合計用掉約 7.7 萬；改成只載入搜尋到的工具之後，合計約 8,700 token。

[4.17 Coding agent harness](/llm/04-applications/coding-agent-harness/) 在 context 預算那一節把 system prompt、工具定義與對話歷史合稱 [scaffold](/llm/knowledge-cards/scaffold-vs-harness/)，建議三者合計不超過 context 的四分之一；同一節的配額表裡，system prompt 加工具定義的配額是 5% 到 15%。以 200K token 的 context window 計，Anthropic 例子裡的 7.2 萬 token 工具定義約佔 36%，單是工具定義就超過整個 scaffold 的上限。工具定義佔用的 token 越多，留給讀進來的檔案內容與工具回傳結果的 token 越少。

[Prompt cache](/llm/knowledge-cards/prompt-cache/) 讓重複送出的工具定義計費較低、首字延遲（[TTFT](/llm/knowledge-cards/ttft/)）較短，作用在費用與延遲上；被快取的 token 仍然在 context window 裡、仍然參與 attention，佔用的空間不變。

**選錯工具**是模型挑工具時的錯誤率。模型依工具名稱與 description 決定呼叫哪一支。接了好幾個 server 時，每個 server 都可能有一支 `search`、一支 `list`；Claude Code 在 MCP 工具名稱前面加上 server 前綴（`mcp__<server>__<tool>`），名稱並不完全相同，但動詞部分相同，模型要靠前綴與 description 分辨作用對象。同一個 server 裡也可能有 `get_user`、`get_user_profile`、`get_account` 這類動詞與受詞都相近的工具。從這個挑選機制推論，候選越多、名稱與 description 越相近，挑錯的機會越高；選錯之後呼叫多半照常成功，回傳的是另一個對象的結果（另一個 server 的空結果、結構相似而屬於別的帳號的資料），沒有錯誤訊號，模型就照著錯的結果回報「沒有資料」或改錯對象（[tool result misread](/llm/knowledge-cards/tool-result-misread/)）。

Anthropic 用內部的 MCP 評測量過工具數量多的情境：Anthropic 替 Opus 4 開啟 Tool Search Tool（只讓搜尋到的工具定義進 context）之後，評測的準確率從 49% 升到 74%；Opus 4.5 從 79.5% 升到 88.1%（同一篇〈Introducing advanced tool use〉）。這組數字來自 Anthropic 的內部評測，題目與工具組合沒有公開，外部無從重現；文章沒有說明這個準確率量的是選對工具，還是整個任務做對；開啟 Tool Search Tool 同時減少了 context 佔用與候選數量，兩種成本在這組數字裡沒有分開量。另外，Anthropic 的 API 文件〈Tool search tool〉寫 Opus 4.1 與更早的模型不支援 Tool Search Tool，Opus 4 那組數字是內部測試的結果。

兩個模型開啟之前的準確率差了約 30 個百分點（Opus 4 的 49% 對 Opus 4.5 的 79.5%），準確率跟模型有關。開啟之後的改善幅度，用百分點算，Opus 4 升了 25 個百分點，Opus 4.5 升了約 9 個百分點；改用錯誤率（100% 減掉準確率）的相對降幅算，Opus 4 的錯誤率從 51% 降到 26%，約少一半，Opus 4.5 的錯誤率從 20.5% 降到 11.9%，約少四成，兩個模型的相對降幅相近。所以從這組數字分不出能力較弱的模型是否受工具數量的影響更大。[4.3〈為什麼本地小模型 Tool use 失敗率高〉](/llm/04-applications/tool-use-principles/) 已經把可選工具超過五個列為本地小模型的失敗成因之一，並建議把可用工具控制在三到五個；本篇處理的是工具數量遠超過這個範圍、而事先不知道任務會用到其中哪幾支的情境。

**client 的工具數上限**跟 token 數無關：有些 client 對一次 request 裡所有 server 合計的工具支數設了上限，超過時截掉多出的工具或直接報錯。VS Code 的 Copilot Chat 對不支援 tool search 的模型限制一次 request 最多 128 支工具，超過時報錯（VS Code〈Use tools with agents〉的排錯段），實驗性的 virtual tools 設定可以把工具分組、讓模型需要時再展開；支援 tool search 的模型改用延遲載入，不受這個上限影響（Sentry 的 client 相容性文件 `docs/mcp/harnesses.md`，2026-11-03 整理）。Cursor 早期文件寫過約四十支的上限，現行文件已經拿掉，IDE 從 2.4 版起只把工具名稱放進 context、需要時才讀 schema，各模型供應商自己的上限仍在（同一份 Sentry 文件的整理）。被截掉的工具，失敗的外觀跟搜尋落空一樣，模型不知道它存在。

## 延遲載入的機制與它的代價

延遲載入把工具定義從「每次都放進 context」改成「用到才放進 context」。常駐的只剩少數高頻工具加上一支搜尋工具；模型要做常駐工具做不到的事時，先呼叫搜尋工具，取得相關工具的定義之後再呼叫那支工具。取得定義這一步，有的實作併在搜尋的回傳裡（Atlassian 的 `discover` 回傳工具與它們的 schema，Anthropic API 把搜尋命中的工具自動展開成完整定義），有的另外要一次呼叫（Stripe 的 MCP server 先讓模型用 `stripe_api_search` 找 API method，再用 `stripe_api_details` 取參數說明）。有的實作另外把延遲載入工具的名稱放進 context、只把完整 schema 留到搜尋之後（Claude Code），名稱佔的 token 比完整定義少得多，但不是零。

這個機制換到的是 context 佔用與候選數量同時下降：一次呼叫裡只有常駐工具與搜尋到的那幾支。付出的是下面幾項：

- **多出來的模型生成與往返**：每用到一支延遲載入的工具，模型就多生成一段搜尋呼叫。Anthropic API 的 Tool Search Tool 在 API 端執行，搜尋在同一個回應裡完成，多出來的是那一段生成的 token 與時間；搜尋工具由 client 或 MCP server 執行時（Claude Code 的 `ToolSearch`、Atlassian 的 `discover`），多一次模型呼叫的來回；Stripe 搜尋之後再取參數說明，多兩次。
- **搜尋落空**：搜尋沒有回傳某支工具時，模型不知道那支工具存在。Anthropic API 文件寫明，沒有命中時搜尋回傳空的結果，不是錯誤；這類失敗的外觀是模型回報做不到、或改用一支相近但不對的工具（[tool result misread](/llm/knowledge-cards/tool-result-misread/)）。Anthropic 的 Tool Search Tool 比對的是工具名稱、description、參數名與參數說明，內建的 regex 與 BM25（依詞頻排序的關鍵字搜尋）兩種都比對字詞，API 另外接受自訂的搜尋（例如 embedding）；Claude Code 文件寫明，比對 description 時只讀開頭有長度上限的一段。搜尋字詞由模型產生，從機制推論，模型多半沿用使用者描述任務的用語，所以被比對的欄位裡沒有這些字詞時，搜尋就比對不到；使用者用中文描述任務、server 的 description 是英文時，比對字詞的搜尋要靠模型自己把搜尋字詞換成英文，換不到就落空。寫 server 的人在 description 開頭放雙語關鍵詞，或改用 embedding 搜尋，可以降低這種落空。
- **常駐集合要另外決定**：寫 server 或設定 agent 的人決定哪幾支工具常駐，這決定了最常見的任務是否多一次往返。Anthropic 的 API 文件建議把最常用的三到五支工具留在常駐（〈Tool search tool〉）。從往返的成本推論，常駐集合依使用頻率選；上線前沒有呼叫紀錄時，從要服務的任務清單推估最常見的那幾種，上線後再用呼叫紀錄修正。

**延遲載入對 prompt cache 的影響取決於實作。** prompt cache 照 `tools`、`system`、`messages` 的順序比對前綴，前面那一層一改，後面全部重算，所以改了工具定義的 request 整個快取失效（Anthropic〈Prompt caching〉的〈What invalidates the cache〉）。Anthropic API 的延遲載入不改前綴：延遲載入的工具不放進 system 前綴，搜尋命中的定義以 `tool_reference` 區塊加在對話歷史的尾端，所以既有的快取保留（〈Tool use with prompt caching〉）。Claude Code 的文件寫的是同樣的結果：延遲載入時，Claude Code 在整個對話裡沿用第一次 request 的工具清單，中途接上或斷開 MCP server 都不影響已經快取的內容；關掉延遲載入、工具全部常駐時，中途加一支工具就讓快取失效（Claude Code〈How Claude Code uses prompt caching〉）。GitHub 已移除的 `enable_toolset` 讓模型在對話中途打開整組工具（寫在〈延遲載入的搜尋對象與一次載入的粒度〉）；從前綴比對的規則推論，在工具全部常駐的 client 上，它每打開一次，整個快取就失效一次。

工具定義總量本來就小的時候，延遲載入省下的 context 與候選數量都很少，多出來的往返與搜尋落空卻照樣存在。Claude Code 用環境變數 `ENABLE_TOOL_SEARCH` 決定總量小時是否全部常駐：設成 `auto` 時，MCP 工具定義合計不到 context window 的 10% 就全部常駐，到 10% 以上才改成延遲載入（Claude Code 文件〈Connect Claude Code to tools via MCP〉）。10% 是 Claude Code 文件給的門檻，`auto:N` 可以改，文件沒有寫出這個值的依據。沒有設定這個變數時，Claude Code 的預設是全部延遲載入：session 開始時只載入工具名稱與 server 說明，模型要先呼叫 `ToolSearch` 才拿得到完整的 schema；文件列了 MCP 工具全部常駐的例外：用的是不支援的較舊模型、經由部分雲端平台部署（例如 Azure 上的 Microsoft Foundry）、設了 `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`，或權限規則拒絕了 `ToolSearch`；設了 `alwaysLoad: true` 的 server，只有那個 server 的工具常駐。文件沒有說明這個預設值服務的情境。

## 延遲載入做在 MCP server 端或 client 與模型 API 端

延遲載入可以做在協議的兩端，做在哪一端決定了它對哪些 client 有效、搜尋涵蓋哪些工具。

**MCP server 端執行**時，server 的 `tools/list` 只回傳少數工具與一支搜尋工具，其餘的工具藏在搜尋工具背後。Atlassian 的 Rovo MCP server（v2 endpoint）是這一種：Atlassian 稱為 primary tools 的那一組直接出現在 `tools/list`，在不做延遲載入的 client 上它們就是常駐工具；其餘的 deferred tools 要先用 `discover` 以自然語言搜尋，再經由 `executeRead`、`executeWrite`、`executeDestructive` 這三支分派工具帶著工具名與參數執行（Atlassian Developer〈Supported tools〉，2026-11-02 更新）。MCP 規格本身沒有工具搜尋的欄位：`tools/list` 有分頁、快取期限與清單變動的通知，沒有搜尋或數量上限的欄位（MCP 規格 2026-07-28 版）。server 端的延遲載入是用普通的工具做出來的，搜尋工具對 client 來說就是一支工具，所以它對任何 MCP client 都有效；代價是每個 server 各做一套搜尋，搜尋範圍只涵蓋那個 server 自己的工具。

**client 與模型 API 端執行**時，server 照常回傳完整清單，由 client 或模型 API 決定哪些定義進 context。Anthropic API 的 `defer_loading` 是這一種：client 送出的 request 照樣帶著全部工具定義，client 標了 `defer_loading: true` 的工具不放進 context，模型呼叫搜尋工具之後，API 把命中的工具展開成完整定義（〈Tool search tool〉）。Claude Code 對 MCP 工具預設由 client 自己做這件事，搜尋工具是 `ToolSearch`。這一端的好處是一套搜尋涵蓋所有 server，server 不必另外實作搜尋；代價是只在支援延遲載入的 client 與模型上有效，request 仍然帶著完整清單，省下的是 context 佔用，不是 request 的大小。所有 server 的工具在同一套搜尋裡競爭排名，另有一個代價：不受信任的 server 可以在 description 塞進搜尋常用的字詞或「最佳」這類用語，把搜尋結果與模型的選擇導向自己的工具。MPMA（arXiv 2505.11154）量的是名稱與 description 裡的操縱用語對模型選擇的影響；從機制推論，比對字詞的 regex 與 BM25 搜尋同樣受影響。第三方 server 的信任判斷在 [6.2 tool use 與 MCP server 的權限模型](/llm/06-security/tool-use-permission-model/) 的〈第三方 MCP server 的供應鏈信任〉。

兩端可以同時存在。從機制推論，Claude Code 以預設設定接上 Atlassian v2 時，Claude Code 把 Atlassian 的 primary tools 也延遲載入，`discover` 本身也要先被 `ToolSearch` 搜到，模型要找一支 Atlassian 的 deferred tool 得先後經過兩次搜尋。兩層搜尋可以換成一層，三種換法由不同的人做，各有代價：

- **設定 agent 的人加 `alwaysLoad: true`**：在 Claude Code 的 MCP 設定裡替這個 server 加上這個設定，primary tools 與 `discover` 就常駐，只剩 Atlassian 自己那一次搜尋。代價是這些定義回到每一次呼叫的 context 裡。
- **寫 server 的人標記單一工具常駐**：Claude Code 讀工具的 `_meta` 裡的 `"anthropic/alwaysLoad"`，標了的那一支常駐（Claude Code〈Connect Claude Code to tools via MCP〉）。寫 server 的人可以只讓自己的搜尋工具或最常用的那幾支常駐；Sentry 的 client 相容性文件舉的例子是讓 `get_sentry_resource` 常駐，使用者貼上的 Sentry 網址就不必先經過搜尋（`docs/mcp/harnesses.md`）。代價是這個鍵只有 Claude Code 讀，其他 client 照常處理；設定這個 server 的人仍然可以把它的工具全部延遲載入（Claude Code〈Connect Claude Code to tools via MCP〉）。
- **設定 agent 的人改用完整清單**：把 Atlassian server 的 URL 加上 `?tools=all`，讓 `tools/list` 分頁回傳全部工具（Atlassian Support〈Supported tools〉寫的是給需要完整清單的 gateway 用），由 Claude Code 一層搜尋涵蓋全部工具。從機制推論，代價是 deferred tools 改以各自的名稱出現，Atlassian 依風險分開的三支分派工具不再是核准的單位，client 的核准規則要對每支 deferred tool 逐支設定（[4.25〈分派工具的切分〉](/llm/04-applications/mcp-tool-approval-and-risk/)）；而且這個換法要 client 讀完分頁，Sentry 的 client 相容性文件記錄過 Cursor IDE 只讀 `tools/list` 的第一頁、忽略 `nextCursor`，Cursor 員工 2026-09-15 確認過，那份文件寫成時還沒確認修好（引自 Cursor 論壇的回報，本篇沒有查證原帖）。

## 延遲載入的搜尋對象與一次載入的粒度

延遲載入的各家實作，差在搜尋找的是什麼、找到之後一次放進 context 多少。下面依一次載入的單位由細到粗排。

**以 API method 為單位（Stripe）。** 模型呼叫 Stripe MCP server 的 `stripe_api_search`，以關鍵字找 API method，再呼叫 `stripe_api_details` 取得那個 method 的參數說明，最後呼叫 `stripe_api_read`（對應 `GET`）或 `stripe_api_write`（對應 `POST`、`PATCH`、`PUT`、`DELETE`），帶著 method 與參數執行（Stripe〈Model Context Protocol (MCP)〉）。延遲載入的單位是單一 API method，這些 method 是兩支分派工具的參數，各自沒有 MCP 工具定義。Stripe 文件寫明，這個設計讓大部分 API 經由 MCP 可用，又不讓 context window 的佔用無謂地增加。同一個 server 另外常駐幾支不經分派的工具，例如取得帳號資訊的 `get_stripe_account_info` 與搜尋 Stripe 文件的 `search_stripe_documentation`。

**以單一工具為單位（Atlassian、Anthropic API、Claude Code）。** Atlassian 的 `discover` 回傳可能相關的幾支工具與它們的 schema；Anthropic 的 Tool Search Tool 一次回傳幾個命中的工具（預設最多五個）；Claude Code 的 `ToolSearch` 也是以工具為單位載入。

**以整組工具為單位（GitHub，已移除）。** GitHub MCP server 把工具分成 issues、pull_requests、actions 這類 toolset；本機版本曾經提供 dynamic toolsets 模式，啟動時只有 `list_available_toolsets`、`get_toolset_tools` 與 `enable_toolset` 三支工具，模型決定要用哪一組時呼叫 `enable_toolset`，server 把整組工具加進工具清單。這個模式在 2026 年 5 月移除（github/github-mcp-server PR #2512），GitHub 現行的做法寫在〈延遲載入以外控制工具定義的做法〉的靜態篩選。

一次載入的單位越細，載入的定義越接近這次要用的那幾支。單位相同時，差別在搜尋一次回傳幾項：只回傳一項時（Stripe 的 `stripe_api_details` 一次取一個 method），任務要用幾項就多幾次往返；回傳多項時（Atlassian 的 `discover`、Anthropic 的 Tool Search Tool），往返次數不隨項數增加，但回傳的候選裡可能有這次用不到的定義，成敗看候選是否涵蓋任務要用的全部工具。單位粗到整組時，一次就拿到整組，用不到的定義也一起進 context。

## 延遲載入以外控制工具定義的做法：靜態篩選、client 預選、合併工具、拆給 subagent 與程式碼執行

延遲載入由模型在呼叫途中搜尋工具定義。下面幾種做法控制同一件事，但都不讓模型在呼叫途中搜尋定義；各自由不同的人做，換到與付出的也不同。

**靜態篩選**由設定 agent 的人在 server 啟動或連線時決定開哪些工具，模型在整個對話裡看到的是同一份較短的清單。GitHub MCP server 現在採用這一種：本機版用 `--toolsets`、`--tools`、`--read-only` 參數，遠端版用 `X-MCP-Tools` 這類 header；README 的理由是只開需要的 toolset 讓模型比較容易選對工具，也讓 context 變小。移除 dynamic toolsets 的那個 PR 只寫了這個模式僅限本機版，沒有比較 dynamic toolsets 與靜態篩選的效果。server 沒有提供篩選參數時，篩選要做在 client 端：例如 Claude Code 的權限規則可以拒絕整支工具，關掉延遲載入時，Claude Code 會把被拒絕的工具定義從 request 拿掉（Claude Code〈How Claude Code uses prompt caching〉）。server 與 client 兩端都沒有篩選的位置時，只有寫 server 的人改 server 才做得到。靜態篩選讓設定的人代替模型挑選工具：模型呼叫時沒有搜尋往返，也沒有搜尋落空；代價是設定的人要事先知道這個 agent 會做哪些事，任務範圍改變時要改設定。設定的人事先猜錯時，失敗的外觀跟搜尋落空一樣，模型找不到那支工具。

**client 預選**由 client 在送出 request 之前，拿使用者的訊息跟工具的 description 比對，只把相關的工具定義放進這一次的 request，模型不必先呼叫搜尋工具。GitHub Copilot 在 VS Code 裡曾經這樣做：把預設工具從約四十支減到十三支，把相近的工具群集成 virtual tools，並在展開之前用 embedding 預選；GitHub 量到需要的工具出現在清單裡的比例，embedding 預選 94.5%、讓模型分類 87.5%、固定清單 69.0%（GitHub Blog〈How we're making GitHub Copilot smarter with fewer tools〉，2025-11-19）。2026 年 6 月起，VS Code 對支援 tool search 的模型（較新的 Claude 與 GPT-5.4 以後的模型）改用延遲載入：MCP 工具標 `defer_loading`，模型呼叫搜尋工具，由 VS Code 在本地用 embedding 搜尋、回傳最相關的幾支（VS Code Blog〈Improving token efficiency in GitHub Copilot〉，2026-06-17）；預選與 virtual tools 只留給其他模型。VS Code 用的仍是 embedding，用途從決定送出哪些工具變成替模型的搜尋排序。client 預選換到的是沒有多出來的往返；代價是預選漏掉的工具，模型同樣不知道它存在；從 prompt cache 的前綴規則推論，每一輪的工具清單可能不同，清單一變快取就失效。

**以任務為單位合併工具**由寫 server 的人把常一起用的幾個 endpoint 合成一支工具。Anthropic〈Writing effective tools for agents〉（2025-09-11）寫工具多不一定結果好，重疊的工具會讓 agent 分心，舉的例子是用一支 `schedule_event` 取代 `list_users`、`list_events`、`create_event` 三支，並建議不要把 endpoint 逐一包成工具。Sentry 的 MCP server 的搜尋類工具接受自然語言，由 server 內嵌的模型翻成 Sentry 的查詢語法，一支工具收掉一整組查詢參數。合併同時減少工具定義的總量與相近的名稱，核准的單位仍然是一支有意義的工具（`schedule_event` 是寫入）；代價是寫 server 的人要猜對任務的形狀，猜錯時 agent 要拆開來做的事沒有對應的工具；server 內嵌模型的那一種，另外要負擔模型的費用，而且翻譯錯了，回傳的就是另一個查詢的結果；Sentry 的 `search_issues` 可以用 `includeExplanation` 要求回傳翻譯後的查詢，不要求時模型看不到翻譯成了什麼。

**拆給 subagent** 由設定 agent 的人把一個 MCP server 只交給一個 subagent，主對話的 context 不含那組工具定義，需要那組工具的任務委派給 subagent。Claude Code 的 subagent 可以在自己的設定裡 inline 定義 MCP server，文件寫明這樣做時 subagent 拿到工具，主對話沒有（Claude Code〈Subagents〉）。同一份文件也寫明 plugin 提供的 subagent 不讀 `mcpServers` 欄位，plugin 的 MCP server 在 plugin 啟用時主對話也拿得到；所以 Sentry 的 Claude Code plugin 雖然附了一個 `sentry-mcp` subagent，Sentry 的工具定義仍然在主對話裡，要把它們擋在主對話之外，得在自己的 subagent 設定裡 inline 定義 server。換到的是主對話的 context 與候選數量都不含那組工具；代價是一次委派的來回，以及 subagent 只回傳摘要、主對話看不到中間結果。subagent 預設沿用主對話的權限模式，settings 裡的 deny 規則也作用在 subagent 上（〈Subagents〉）。

**程式碼執行**讓模型寫程式碼呼叫 API，不替每個操作載入工具定義，Cloudflare 稱為 Code Mode。它有兩種做在不同位置的實作。

- **server 端（Cloudflare）**：Cloudflare 的 MCP server 只有 `search` 與 `execute` 兩支工具，定義合計約一千 token，不隨 endpoint 數量增加。`search` 也是搜尋，但跟延遲載入的搜尋不同：模型寫一段 JavaScript 在 Cloudflare 的 OpenAPI spec 裡找 endpoint，回到 context 的是模型自己寫的程式碼篩出的結果，不是 server 給的完整定義，所以不算延遲載入；`execute` 讓模型寫一段 JavaScript 呼叫 Cloudflare API。對照之下，Stripe 的 `stripe_api_details` 把 server 寫好的參數說明放進 context，這是延遲載入。Cloudflare 兩支工具產生的程式碼都在 Dynamic Worker isolate 裡執行，這是一個 V8 沙盒（[sandbox](/llm/knowledge-cards/sandbox/)），沒有檔案系統、沒有可以被 [prompt injection](/llm/knowledge-cards/prompt-injection/) 讀走的環境變數，預設不能對外連線（〈Code Mode〉）。
- **client 端（Anthropic〈Code execution with MCP〉，2025-11-04）**：client 把任意 MCP server 的每支工具呈現成檔案樹上的程式碼檔，模型列目錄、只讀需要的那幾個檔，再寫程式碼呼叫；Anthropic 舉的例子從約 15 萬 token 降到約 2,000 token。這一種不需要 server 改動，設定 agent 的人可以對任何 server 採用；client 依工具名稱的核准規則是否管得到程式碼裡的每一次呼叫，依 client 而定，寫在 [4.25〈client 的核准規則以什麼為單位〉](/llm/04-applications/mcp-tool-approval-and-risk/)。

兩種實作都讓呼叫之間的中間結果留在沙盒裡、不進 context。舉一個例子：一段程式碼可以先列出所有 zone，在沙盒裡篩出暫停的那幾個，只把篩完的結果回傳給模型；用個別工具做同一件事時，列出全部 zone 的結果要整份回到 context，模型讀完才下得了下一個呼叫。代價是要有一個能安全執行模型產生的程式碼的沙盒；模型寫錯的程式碼在執行時拋出例外，例外訊息回到模型；server 端只有一支 `execute` 時，client 依工具名稱設定的核准規則分不出讀取與刪除，這對核准的影響在 [4.25〈分派工具的切分〉](/llm/04-applications/mcp-tool-approval-and-risk/)。

## 各家做法並排：常駐的工具、搜尋對象、載入單位與執行方式

下表並排本篇提到、各家實際提供的延遲載入、靜態篩選、client 預選與 server 端程式碼執行；合併工具與拆給 subagent 不改變工具定義的載入方式，client 端程式碼執行不屬於任何一家 server，都不列入。「常駐的工具」一欄指那一家的做法一開始就放進 context 的那一組：server 端的做法以不做延遲載入的 client 為準，Anthropic API 與 Claude Code 那一列以它們自己的延遲載入為準。

| 做法                                               | 常駐的工具                                   | 搜尋的對象                                                     | 一次載入的單位       | 執行的方式                                                      |
| -------------------------------------------------- | -------------------------------------------- | -------------------------------------------------------------- | -------------------- | --------------------------------------------------------------- |
| Stripe                                             | 搜尋、參數說明、讀、寫四支與帳號、文件類工具 | API method                                                     | 單一 method          | 讀、寫兩支分派工具                                              |
| Atlassian（v2）                                    | primary tools 加 `discover`                  | deferred tool 目錄                                             | 單一工具（一次多支） | primary tools 各自；deferred tools 經讀、寫、破壞性三支分派工具 |
| Anthropic API、Claude Code                         | 未標延遲的工具與搜尋工具                     | request 裡標了延遲的工具                                       | 單一工具（一次多支） | 各工具本身                                                      |
| GitHub（dynamic，已移除）                          | 三支 toolset 管理工具                        | toolset 清單                                                   | 整組工具             | 各工具本身                                                      |
| GitHub（現行）                                     | 設定時選定的 toolset                         | 不搜尋                                                         | 不適用               | 各工具本身                                                      |
| GitHub Copilot（VS Code，2025 年的做法）           | client 依使用者訊息預選的工具                | client 在送出前比對                                            | 單一工具或工具群集   | 各工具本身                                                      |
| VS Code（2026 年 6 月起，支援 tool search 的模型） | 約三十支核心工具與搜尋工具                   | 標了 `defer_loading` 的工具（VS Code 在本地用 embedding 搜尋） | 單一工具（一次多支） | 各工具本身                                                      |
| Cloudflare                                         | `search`、`execute`                          | OpenAPI spec（由模型寫程式碼查）                               | 不載入 endpoint 定義 | 單一 `execute`，在沙盒裡執行程式碼                              |

## 工具定義總量、任務範圍與呼叫串連對應的做法

做法由兩種人選，兩者看的是工具定義的總量、事先是否知道任務會用到哪些工具，以及任務是否要串連多次呼叫。工具定義的 token 數，寫 server 或設定 agent 的人可以把 `tools/list` 的回傳交給模型的 tokenizer 量出來；名稱是否相近，看工具（不論是否來自同一個 server）的動詞與受詞是否相同或相近、只靠 description 分辨。核准需求對做法的影響在 [4.25](/llm/04-applications/mcp-tool-approval-and-risk/)。

### 寫 MCP server 的人決定的事

**每個操作包成個別工具、以任務為單位合併，還是收進分派工具**，是寫 server 的人最先做的決定。endpoint 多到連搜尋回傳的定義都要控制、而且操作的參數已經有一份可以查的 API 文件時，把 method 當成分派工具的參數（Stripe），延遲載入的單位是 method，參數說明只在 `stripe_api_details` 這類呼叫時才進 context；代價是 client 依名稱設定的核准只剩那幾支分派工具（[4.25〈分派工具的切分〉](/llm/04-applications/mcp-tool-approval-and-risk/)）。常一起用的幾個 endpoint 對應一件使用者會描述的任務時，合併成一支以任務為單位的工具，同時減少總量與相近的名稱，代價是要猜對任務的形狀。每個操作都要讓 client 能個別放行或拒絕時，保留個別工具，延遲載入的單位是工具（交給 client 或 Anthropic API 的 Tool Search Tool 搜尋）；代價是工具定義較多，每支都要寫 description 與 schema，而且 description 的開頭要有使用者描述任務的字詞，搜尋才比對得到。

**server 端是否做延遲載入**，看這個 server 要服務的 client。

目標 client 都已經做延遲載入（Claude Code、使用 Anthropic API 的 agent）時，從機制推論，server 端再做一層預設會讓模型多搜尋一次，可以不做，或用 `_meta` 的 `"anthropic/alwaysLoad"` 讓搜尋工具常駐。

目標 client 不支援延遲載入時，context 佔用只能在 server 端控制，做法依任務而定：

- 任務範圍事先知道時，提供靜態篩選的參數。
- 要串連多次呼叫時，提供程式碼執行。
- 任務既無法預測、也不需要串連時，做 server 端延遲載入，代價是這個 server 自己做一套搜尋。

兩種 client 都要服務時，寫 server 的人依主要的那一種 client 決定，替另一種保留退路：Sentry 的 MCP server 依支援的優先程度把 client 分成兩級，改動要在第一級的每一個 client 上都能用；第一級（Codex、Claude Code、Cursor）都已經在 client 端延遲載入，Sentry 的程式碼註解寫的是自己那一層搜尋在這些 client 上「多餘」，所以它把全部工具直接列在 `tools/list`，拿掉了自己的搜尋與分派工具（`search_sentry_tools`、`execute_sentry_tool`），並把那一組介面留在程式碼裡當暫時的退路（getsentry/sentry-mcp 的 `docs/mcp/harnesses.md` 與 `packages/mcp-core/src/tools/exposure.ts`）。client 的工具數上限是所有 server 合計，工具多的 server 對有上限的 client 只能靠靜態篩選、合併或少數分派工具，把支數壓在上限之內。

### 設定 agent 的人決定的事

**全部常駐還是延遲載入**：工具定義合計只佔 context window 的一小部分、名稱彼此不相近、而且合計支數在 client 的上限之內時，全部常駐的 context 佔用與選錯工具的機會都小；改成延遲載入省不了多少，仍要付多出來的往返與搜尋落空，所以全部常駐的總成本較低。Claude Code 的 `auto` 模式拿 10% 當這個分界，文件沒有寫出依據；4.17 給 system prompt 加工具定義的配額是 5% 到 15%，可以拿來對照自己的 scaffold 還剩多少。從機制推論，`auto` 的 10% 門檻要往哪個方向調，看 transcript 裡的兩種現象：最常見的任務幾乎每次都先呼叫 `ToolSearch` 時，多出來的往返在增加延遲，提高門檻或把那幾支設成常駐；模型在名稱相近的工具之間呼叫錯的那一支時，降低門檻或篩掉一部分工具。總量小而工具名稱相近時，context 佔用很小，選錯工具的成本仍在；延遲載入在這裡減少的是同時出現的候選數，代價同樣是往返與搜尋落空；靜態篩選掉用不到的工具或 server 則不必付這兩項；同一個 server 裡的相近名稱，要靠寫 server 的人改名稱或 description 的開頭來分辨。

**事先知道任務範圍時**：工具多、而設定 agent 的人事先知道任務只會用到其中一部分時，靜態篩選沒有往返也沒有搜尋落空，context 與候選數量由設定的人在設定時就決定了。任務範圍常常變動時，這個做法的代價是反覆改設定，或者設定得太寬而又付出工具全部常駐的成本。某一組工具只在少數幾類任務用到時，拆給 subagent 讓主對話不必帶著那組定義，代價是委派的來回與主對話看不到中間結果。

**任務無法預測時**：工具多、而任務事先無法預測時，延遲載入讓模型自己找工具，延遲載入的成本取決於搜尋品質：被比對的欄位（Claude Code 比對 description 時只讀開頭一段，Anthropic API 比對名稱、description 與參數）沒有使用者描述任務的字詞時，搜尋落空，模型回報做不到；常駐集合沒放最常用的那幾支時，最常見的任務每次都多一次往返。接上的 server 自己也做延遲載入時，兩層搜尋的三種換法寫在〈延遲載入做在 MCP server 端或 client 與模型 API 端〉。

**要串連多次呼叫時**：任務要串連多次 API 呼叫、中間結果很大時，程式碼執行讓中間結果留在沙盒裡，context 只收到最後的結果。server 沒有提供程式碼執行時，client 端的程式碼執行（Anthropic〈Code execution with MCP〉的做法）對任何 server 都可用。代價是要有沙盒、模型要寫得出正確的程式碼；server 端只有一支 `execute` 時，依工具名稱的核准分不出讀取與刪除，風險改靠 token 的權限範圍控制（[4.25〈分派工具的切分〉](/llm/04-applications/mcp-tool-approval-and-risk/)）。任務範圍事先知道、又要串連多次呼叫時，兩種做法可以並用：設定的人先篩掉用不到的 API 範圍，再讓模型在範圍內寫程式碼串連呼叫，代價是兩套設定要一起維護。

## 延伸閱讀：核准與執行風險、context 預算、快取斷點、MCP 的協議層與最小 server 實作

- client 的核准規則以工具名稱、參數還是 hook 為單位，工具收進分派工具或程式碼執行工具時規則分得出哪些操作，server 端確認的兩種做法、設定時拿掉寫入能力，以及標註與名稱是否可信，在 [4.25 MCP 工具的核准規則與執行風險](/llm/04-applications/mcp-tool-approval-and-risk/)。
- 除了工具定義，system prompt、對話歷史與工具回傳結果各佔多少 context、超標時看到什麼現象，在 [4.17 Coding agent harness](/llm/04-applications/coding-agent-harness/) 的〈Context Budget 工程實務〉。
- 工具定義留在 context、只降低重複送出的費用與延遲時，快取斷點放在哪裡、什麼改動會讓快取失效，在 [4.18 Prompt caching 工程實務](/llm/04-applications/prompt-caching-engineering/) 的〈Cache breakpoint 設計〉。
- 從 API 提供者這一側看 agent 這種呼叫方：有副作用的 GET 讓依 method 分讀寫的入口失效、錯誤訊息給模型讀、idempotency key 由誰產生、OpenAPI spec 的說明被當成搜尋資料，以及 MCP 工具的切法與 endpoint 的切法各自依什麼決定，在 backend 模組的 [11.17 LLM agent 作為 API 的呼叫方](/backend/11-api-design/llm-agent-as-api-caller/)。
- MCP 跟 function calling、structured output 各屬哪一層，以及什麼規模的應用才需要 MCP，在 [4.6 應用層協議](/llm/04-applications/application-protocols/)；自己寫一個最小的 MCP server、看 `tools/list` 回傳什麼，在 [Hands-on：用 blog content 寫一個最小 MCP server](/llm/01-local-llm-services/hands-on/mcp-demo/)。
