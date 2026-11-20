---
title: "4.25 MCP 工具的核准規則與執行風險：client 依名稱核准的單位、分派工具的切分、server 端確認的兩種做法、唯讀模式與標註的信任"
date: 2026-11-21
slug: "mcp-tool-approval-and-risk"
description: "MCP 工具在執行前的核准與風險控制：client 的核准規則以工具名稱、參數或 hook 為單位，工具收進分派工具或程式碼執行工具時這個單位分得出哪些操作；讀取、寫入、破壞性三種切法與 4.3 副作用分級的對應；server 端確認的通道外核准與 elicitation 兩種做法，以及 client 不支援時的失效方向；設定時用唯讀模式、權限範圍與鎖定參數拿掉寫入能力；MCP 標註與工具名稱只在信任 server 時有效；依 server 是否管得到 client、操作是否可逆與任務是否要串連選做法的條件，附 Stripe、Atlassian、Cloudflare、Supabase 與 Zapier 的做法"
tags: ["llm", "applications", "mcp", "tool-use", "permission"]
weight: 26
---

這篇整理 MCP 工具在執行時的核准與風險控制：client 的核准規則以什麼為單位（工具名稱、參數與 hook），以及 client 自己做程式碼執行時這個單位怎麼變；分派工具依讀取、寫入與破壞性操作切開的幾種做法，以及這組切法跟 [4.3 Tool use 原理](/llm/04-applications/tool-use-principles/) 的副作用分級怎麼對應；server 端確認的兩種做法（使用者在 agent 的通道以外核准，以及經由 client 顯示表單的 elicitation）與 client 不支援時各自的失效方向；設定時直接拿掉寫入能力的做法（唯讀模式、權限範圍、鎖定參數）；MCP 標註與工具名稱為什麼只在信任 server 時有效；以及寫 server 的人與設定 agent 的人依哪些條件選做法。本篇的**分派工具**指一支以參數指定要做哪一個 API 操作、再由 server 把呼叫轉給對應處理者的 MCP 工具（Stripe 的 `stripe_api_write`、Atlassian 的 `executeWrite`）：許多操作共用同一個工具名稱，所以 client 依名稱核准時，看到的是分派工具的名稱，看不到參數裡的操作。接受一段程式碼、代為執行的工具（Cloudflare 的 `execute`）下文稱程式碼執行工具。常駐工具與延遲載入這兩個名稱，以及工具收進少數幾支的原因（工具定義佔用 context 與模型選錯工具），在 [4.24 MCP 工具數量多時工具定義怎麼交給模型](/llm/04-applications/mcp-tool-surface-design/)；人在 agent 流程的哪一點介入，在 [4.5 人機協作拓樸](/llm/04-applications/human-ai-collaboration/)；第三方 MCP server 的程式碼是否可信、安裝前看什麼，在 [6.2 tool use 與 MCP server 的權限模型](/llm/06-security/tool-use-permission-model/)。

本篇引用的各家做法查證於 2026 年 11 月，工具名、設定名與預設值以各家文件的現行版本為準。下文寫「從機制推論」的地方都沒有實測。

## client 的核准規則以什麼為單位

client 的核准規則決定一次工具呼叫在執行之前自動放行、要使用者確認，還是拒絕。以 Claude Code 為例，allow 規則以工具名稱為單位（`mcp__<server>__<tool>`）；deny 規則經由 `--disallowedTools` 可以比對 MCP 工具某個參數的確切值；PreToolUse hook 讀得到完整的呼叫內容，可以依內容決定（Claude Code 文件〈Configure permissions〉）。依名稱設規則最簡單；依參數或內容設規則，寫規則的人要事先知道危險的呼叫長什麼樣。Stripe 文件也建議在 client 開啟工具核准，由使用者在工具執行前先審。

依名稱核准的前提是 client 把每一支 MCP 工具當成一支工具列給模型。有些 client 自己把 MCP 工具收進程式碼執行：OpenCode 預設把每個 MCP server 放進 code mode，模型改由一支 `execute` 在 JavaScript 裡呼叫那些工具（OpenCode〈MCP servers〉）。這時依名稱的規則是否管得到程式碼裡的每一次呼叫，OpenCode 文件沒有寫；文件給的做法是對那個 server 設 `codemode: false`，或拒絕 `execute`，工具就改回直接列出。從機制推論，假如這類 client 的規則管不到程式碼裡的呼叫，client 看到的只有一支 `execute`；server 依風險切開的分派工具（〈分派工具的切分〉）在名稱上的差別，到了這類 client 上就不再是核准的單位。Anthropic〈Code execution with MCP〉寫的 client 端程式碼執行，程式碼呼叫的仍然是一支支經過 client 的 MCP 工具，從機制推論，client 仍可以逐支套規則，Anthropic 的文章沒有寫核准怎麼做。

## 分派工具的切分：一支、讀寫兩支、讀寫破壞性三支

工具收進分派工具之後，分派工具怎麼切分，決定了 client 依工具名稱設定的核准規則分得出哪些操作。所有寫入都經過同一支分派工具時，client 依名稱只能對那支工具整體放行或確認：設成自動放行，所有寫入都放行；設成每次確認，連風險低的寫入（例如建立客戶）也要確認。

[4.3〈工具的「副作用範圍」設計〉](/llm/04-applications/tool-use-principles/) 把工具依副作用分級，並建議把同一個功能切到不同等級，例如把「query DB」切成 SELECT 與 INSERT、UPDATE 兩支。分派工具的切分是同一個做法套在分派工具上：切得越細，client 依名稱設定的核准層級越多。

兩種切法的分級依據不同。4.3 依寫入的位置（sandbox、本地、共享或 production、真實世界）與是否可逆分級。讀、寫、破壞性的切法，Atlassian 文件只寫依操作的風險分開，沒有寫分級的定義；MCP 規格的 `destructiveHint` 把破壞性定義成會改寫環境既有狀態的更新，相對於只新增的更新。照 MCP 規格的定義對過去，4.3 的純讀對應讀取的分派工具；只新增、但對外不可逆的操作（寄出一封信、送出一筆付款）歸寫入的分派工具，不歸破壞性的那一支。要讓這類操作也套較嚴的核准，得在 client 端另外對它寫參數層的規則或 hook。

- **一支程式碼執行工具**（Cloudflare 的 `execute`）：client 看到的每一次呼叫都是同一支工具，讀取與刪除在工具名稱上沒有差別，負責核准的人要逐次讀程式碼才分得出來；hook 可以檢查程式碼，但從機制推論，要從任意程式碼判斷那段程式碼是否刪除資料，判斷本身就不可靠。Cloudflare 把這層控制放在授權：使用者連線時選擇要授予的權限，[OAuth token 被縮到那些權限](/backend/knowledge-cards/authorization-scope/)，agent 只拿得到使用者明確授予的能力；在 CI 這類自動化情境，使用者改用只帶必要權限（[least privilege](/backend/knowledge-cards/least-privilege/)）的 API token（Cloudflare〈Code Mode: give agents an entire API in 1,000 tokens〉）。
- **讀與寫兩支**（Stripe）：client 可以讓 `stripe_api_read` 自動放行、`stripe_api_write` 每次確認。Stripe 另外在 server 端對特定動作要求人工確認，寫在〈server 端確認的兩種做法〉。
- **讀、寫、破壞性三支**（Atlassian）：`executeRead`、`executeWrite`、`executeDestructive` 依操作的風險分開，Atlassian 文件寫明 agent 端依呼叫的是哪一支 execute 工具套用不同的確認（Atlassian Support〈Supported tools〉）。client 可以替刪除設定比一般寫入更嚴的規則，例如把寫入設成每次確認、把刪除設成一律拒絕。Atlassian 的 Rovo MCP server 把工具分成直接列在 `tools/list` 的 primary tools，以及要先用 `discover` 搜尋、再經這三支執行的 deferred tools（搜尋的機制在 [4.24〈延遲載入做在 MCP server 端或 client 與模型 API 端〉](/llm/04-applications/mcp-tool-surface-design/)）；這三支只用在 deferred tools，primary tools 裡的寫入工具（`createJiraIssue`、`editJiraIssue`）以自己的名稱呼叫，要另外逐支設規則。

## server 端確認的兩種做法：通道外核准與 elicitation

server 端確認是 server 自己對特定動作要求使用者確認，不靠 client 的核准規則。下文把 agent 的通道定義為 agent 與 client 之間傳遞工具呼叫與結果的那一條路徑。server 端的確認可以發生在 agent 的通道以外，也可以經由 agent 的通道、由 client 顯示給使用者；client 不支援或設定了略過時，前一種確認照樣生效，後一種不一定。

**通道外核准（Stripe）**：建立退款這類動作，agent 回傳一個網址，使用者到 Stripe Dashboard 按下核准，Stripe 發給 agent 一個 approval token，使用者再請 agent 重試；使用者 24 小時內沒有核准，這次的核准請求就失效。Stripe 依動作本身決定是否要求確認，不只看工具名稱：Stripe 文件列出需要人工確認的動作，同樣經過 `stripe_api_write` 的建立客戶不在其中，帳號另設的核准規則可以要求更多動作確認；這層確認適用於以使用者身分（OAuth）連線的情形，跟 client 端的工具核准是兩層獨立的設定（Stripe〈Model Context Protocol (MCP)〉）。核准發生在 Dashboard，client 是否支援、設了什麼規則都不影響這道確認。

**elicitation（Supabase）**：MCP 的 elicitation（規格 2025-11-25 版起）讓 server 在完成一次工具呼叫之前，請 client 向使用者顯示一份表單（form mode）或一個外部網址（URL mode）；2026-07-28 版改成 server 對 `tools/call` 回傳 `input_required`，client 收集使用者的輸入之後重送那次呼叫。兩種 mode 都要 client 支援才顯示得出來：URL mode 的互動雖然在 agent 的通道以外完成，網址仍由 client 交給使用者。Supabase 的 MCP server 在 `execute_sql` 與 `apply_migration` 偵測到 destructive SQL 時這樣要求確認。確認經由 client 顯示，所以依賴 client 支援：Supabase 文件寫明，client 不支援 elicitation、或使用者設了略過確認的選項時，destructive SQL 不經額外確認就照常執行；同一個 server 的刪除 notebook 則在 client 不支援表單時直接拒絕刪除（Supabase〈Model context protocol (MCP)〉）。Supabase 同一份文件也寫明這道確認只是防護，偵測不一定涵蓋每一種破壞性 SQL，不是安全保證。destructive SQL 的處理是確認失效時照常執行（fail open），刪除 notebook 的處理是確認失效時拒絕執行（fail closed）。

兩種做法的差別是 client 不配合時的方向：通道外核准不依賴 client；elicitation 依賴 client，失效時照常執行還是拒絕，由寫 server 的人在每個動作上決定。server 要服務設定不受控的 client、而動作不可逆時，寫 server 的人把用 elicitation 確認的那些動作設成失效時拒絕；偵測式的確認可能漏掉某些操作，任務不需要那類操作時，再配上〈設定時拿掉寫入能力〉的唯讀模式或權限範圍。

## 設定時拿掉寫入能力：唯讀模式、權限範圍與鎖定參數

任務根本不需要寫入或破壞性操作時，最直接的做法是在設定時就把這類能力拿掉，限制由資料庫的權限或 token 的權限範圍執行，不靠 server 把操作放進名稱對得上風險的那一支分派工具。

- **唯讀模式**：Supabase 的 `read_only=true` 讓所有查詢以唯讀的 Postgres 使用者執行，`project_ref` 把 server 限定在一個專案；GitHub MCP server 的 `--read-only` 只開讀取類工具。
- **依任務授予權限範圍**：Sentry 的 MCP server 依使用者選的 skills 決定要哪些 OAuth scope，沒選的 skill 對應的工具與權限都不給（getsentry/sentry-mcp 的 `skills.ts`）；Cloudflare 的 OAuth 縮權是同一類（〈分派工具的切分〉）。
- **鎖定參數**：Zapier MCP 的 managed 模式由擁有者逐支選 action，並可以把欄位鎖成固定值，例如把訊息要發到的頻道鎖成固定的一個，agent 只能用這些工具、不能自己加新的（Zapier〈Zapier MCP agentic and managed modes〉）。同一個 server 也有讓 agent 自己找 action 並啟用的 agentic 模式。

這一類換到的是寫入能力在設定時就不存在，核准規則與 server 宣告是否如實都不影響它；代價是任務範圍改變、需要寫入時要改設定，而且設定的人要事先知道任務只需要讀取或只寫哪幾個對象。

## MCP 標註與工具名稱的信任

MCP 規格定義了工具的標註（annotation）：`readOnlyHint`（不修改環境）、`destructiveHint`（可能做破壞性的更新）、`idempotentHint`（同樣的參數重複呼叫不產生額外效果）與 `openWorldHint`（互動對象是開放的外部世界）。server 沒有宣告時，規格的預設是會修改環境、可能有破壞性、對象開放，也就是假設最壞的情形。規格寫明這些都是提示，不保證如實描述工具的行為，client 對不受信任的 server 送來的標註不能據以做出工具使用的決定（MCP 規格 2025-11-25 版與 2026-07-28 版寫法相同）。

分派工具的名稱跟標註一樣是 server 自己宣告的：一個 server 可以把刪除操作放進 `executeRead`，就像它可以在刪除工具上標 `readOnlyHint: true`。所以依風險切分分派工具，讓 client 能替讀取、寫入與破壞性操作各設一條規則；規則要有效，前提是 server 如實把操作放進對應風險的那一支（server 如實照 HTTP method 分類，API 本身卻有會改狀態的 GET 時，那個動作照樣進了讀取那一支，見 backend 模組的 [11.17 LLM agent 作為 API 的呼叫方](/backend/11-api-design/llm-agent-as-api-caller/)），而 client 是否依賴這個前提，取決於設定 client 的人是否信任這個 server。工具的 description 同樣由 server 宣告，不受信任的 server 可以用它把搜尋結果與模型的選擇導向自己的工具，寫在 [4.24〈延遲載入做在 MCP server 端或 client 與模型 API 端〉](/llm/04-applications/mcp-tool-surface-design/)。server 端確認依賴的是 server 確實執行這道確認；用 elicitation 時，另外依賴 client 支援並顯示表單（〈server 端確認的兩種做法〉）。設定時拿掉寫入能力的做法，限制由資料庫或 token 的權限執行，信任的對象是發 token 與管權限的那一方。第三方 MCP server 的程式碼是否可信、安裝前看什麼，在 [6.2 tool use 與 MCP server 的權限模型](/llm/06-security/tool-use-permission-model/) 的〈第三方 MCP server 的供應鏈信任〉。

## server 是否管得到 client、操作是否可逆與任務是否要串連對應的做法

做法由兩種人選：寫 MCP server 的人決定分派工具怎麼依風險切分、哪些動作要在 server 端確認、確認失效時照常執行還是拒絕、提供哪些唯讀與權限範圍的設定；設定 agent 的人決定 client 端的核准規則、是否開唯讀模式與授予哪些權限範圍、以及是否開啟 client 的 code mode。寫 server 的人與設定 agent 的人選做法時看的條件相同：寫 server 的人是否管得到 client 的設定、操作是否可逆或影響真實世界、任務是否需要寫入，以及任務是否要串連多次呼叫。

**任務不需要寫入時**，設定 agent 的人開唯讀模式或只授予讀取的權限範圍，寫入能力在設定時就不存在；核准規則與 server 的宣告都不必依賴。

**寫入與破壞性操作需要不同的核准、而寫 server 的人管得到 client 時**（設定 agent 的人跟寫 server 的人是同一方，或 server 只服務已知的 client），依風險切分分派工具（Atlassian），由 client 替每一支設規則。

**server 要服務設定不受控的 client 時**（client 由別人設定，寫 server 的人看不到也改不了它的核准規則），從機制推論，client 沒有替分派工具另設規則、而它的預設是放行時，依風險切分的分派工具一樣全部放行。動作不可逆或影響真實世界（退款、刪除資料）時，在 server 端對那些動作要求確認：通道外核准（Stripe）不依賴 client；用 elicitation 時，把那些動作設成 client 不支援就拒絕執行。

**任務要串連呼叫、又有不可逆的寫入要個別核准時**，兩個條件指向不同的做法：server 端的程式碼執行把所有操作收進一支 `execute`，核准只能靠 token 的權限範圍：模型寫的程式碼在 server 的隔離執行環境（沙盒）裡跑，同一個 token 授予的刪除權限，那段程式碼一律用得到。從機制推論，串連與個別核准可以分開處理：讀取類的串連交給程式碼執行，發給程式碼執行的 token 只帶讀取權限；寫入與刪除另外經由依風險切分的分派工具或 server 端確認，代價是寫入前後的中間結果回到 context。client 端的程式碼執行若能逐支套規則（〈client 的核准規則以什麼為單位〉），串連與個別核准就不必拆開，但要先確認 client 的規則管得到程式碼裡的呼叫。

依風險分級核准、避免每次都確認而讓核准的人不再細看，在 [4.5 人機協作拓樸](/llm/04-applications/human-ai-collaboration/) 的〈有效 HITL 的四個設計條件〉；Stripe 在動作執行前要求的確認對應同一篇的〈Pre-act：動作執行前確認〉。

## 延伸閱讀：工具定義的載入、副作用分級、人機協作與權限模型

- 工具為什麼會收進少數幾支分派工具或一支程式碼執行工具（工具定義佔用 context、選錯工具、client 的工具數上限），以及延遲載入、靜態篩選、合併工具與拆給 subagent 的取捨，在 [4.24 MCP 工具數量多時工具定義怎麼交給模型](/llm/04-applications/mcp-tool-surface-design/)。
- 工具本身依副作用切分時，從純讀、寫 sandbox、寫本地持久化、寫共享或 production 到操作真實世界的分級，以及各級適合的審查方式，在 [4.3 Tool use 原理](/llm/04-applications/tool-use-principles/) 的〈工具的「副作用範圍」設計〉；讀取類與副作用類工具的權限差異，在 [6.2 tool use 與 MCP server 的權限模型](/llm/06-security/tool-use-permission-model/) 的〈「讀取類」跟「副作用類」tool 的權限差異〉。
- 核准放在動作執行前、執行中還是事後，以及分級的確認怎麼避免流於形式，在 [4.5 人機協作拓樸](/llm/04-applications/human-ai-collaboration/) 的〈HITL 三種觸發時機〉與〈有效 HITL 的四個設計條件〉。
