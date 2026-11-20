---
title: "11.17 LLM agent 作為 API 的呼叫方：執行時讀說明的消費者、method 語意與讀寫入口、錯誤回應的可重試與終態、寫入的冪等、規格當搜尋資料、agent 流量的識別，以及 MCP 工具與 endpoint 的切法"
date: 2026-11-21
slug: "llm-agent-as-api-caller"
description: "LLM agent 呼叫 API 時跟其他消費者不同的行為（執行時才讀 description 與 schema、契約被改壞時不回報、看到錯誤會自己重試），以及這些行為讓既有契約的哪幾處變成承重：HTTP method 的安全語意決定讀寫入口能不能自動放行、錯誤回應的可重試與終態分類與給模型讀的訊息、寫入的 idempotency key 由誰產生、OpenAPI spec 的說明被當成搜尋資料、用量觀測怎麼分出 agent 流量，以及 MCP 工具的切法與 endpoint 的切法各自依什麼決定；附 Stripe 與 Cloudflare 的做法、Anthropic 對工具說明與錯誤回應的建議"
weight: 17
tags: ["backend", "api-design", "llm-agent", "ai-agent", "mcp", "contract"]
---

這一篇整理 LLM agent（常稱 AI agent）呼叫 API 時，API 的契約要承擔哪些事：agent 這種呼叫方跟其他消費者不同的三種行為（執行時才讀 description 與 schema、契約被改壞時不回報、看到錯誤會自己重試）；HTTP method 的安全語意怎麼決定讀寫入口與 MCP 標註能不能據以自動放行，以及授權範圍照讀與寫切開；錯誤回應的可重試與終態分類、給模型讀的錯誤訊息、長時操作的 202、請求端的未知欄位，以及回應內容帶進來的 prompt injection；agent 自己重試時，寫入的 idempotency key 由誰產生；OpenAPI spec 與 endpoint 的說明在 agent 找 endpoint 時被當成搜尋資料，回應欄位的多寡怎麼佔 agent 的 context，以及分頁接續標記交給模型轉抄的風險；用量觀測怎麼把 agent 的流量與配額分出來；以及 MCP 工具的切法與 endpoint 的切法各自依什麼決定。

這些都是本模組既有章節的判斷標準，套到一種新的呼叫方上：method 與 status 的承諾在 [11.3 資源建模與操作語意](/backend/11-api-design/resource-modeling-operation-semantics/)，錯誤分類在 [11.4 錯誤模型設計](/backend/11-api-design/error-model-design/)，冪等在 [11.8 API 層冪等設計](/backend/11-api-design/api-idempotency-design/)，消費者身分在 [11.12 API 消費者用量觀測](/backend/11-api-design/consumer-usage-observability/)，本篇寫的是這幾處的條件在 agent 身上變得承重。下文說一個條件「承重」，指的是：同一個條件出錯，別的消費者那邊有寫程式的工程師或中介層的行為補救，換成 agent 呼叫時，出錯會直接變成 agent 的錯誤動作，例如繞過核准、重複寫入或找不到 endpoint。MCP server 端怎麼把大量 API 交給模型（延遲載入、分派工具、程式碼執行）、client 端的核准規則怎麼設，在 LLM 模組的 [4.24 MCP 工具數量多時工具定義怎麼交給模型](/llm/04-applications/mcp-tool-surface-design/) 與 [4.25 MCP 工具的核准規則與執行風險](/llm/04-applications/mcp-tool-approval-and-risk/)。

本篇引用的各家做法查證於 2026 年 11 月，以各家文件的現行版本為準。下文寫「從機制推論」的地方都沒有實測。

## LLM agent 跟其他消費者不同的行為：執行時讀說明、不回報、自己重試

[LLM agent](/llm/knowledge-cards/agent/) 是把控制流交給模型、由模型跨多步決定呼叫哪些[工具](/llm/knowledge-cards/tool-use/)的應用。它呼叫 API 時，發出請求的程式碼不是工程師事先寫好的：模型在執行時讀工具的名稱、description 與參數的 schema，決定呼叫哪一支、參數怎麼填，再由 agent 的程式送出請求。這裡的 agent 框架是包住模型、執行模型產生的呼叫的程式；[MCP](/llm/knowledge-cards/mcp/)（Model Context Protocol）是框架與工具提供方之間的協議，框架這一端稱為 MCP client，工具提供方那一端稱為 MCP server。API 跟模型之間常隔著一層 MCP server，把 endpoint 包成工具；也可能由模型寫程式碼，經由 server 提供的 client 呼叫 HTTP API（Cloudflare 的 MCP server 讓模型寫 JavaScript，在沙盒裡用 `cloudflare.request()` 呼叫 Cloudflare API）。不論哪一種，呼叫的形狀在執行時才決定，這帶出三種跟其他消費者不同的行為。

**執行時才讀 description 與 schema。** 整合團隊的工程師讀過文件、寫好程式碼，之後每一次呼叫都照那份程式碼走；agent 每一次對話都重新讀一次工具的說明，再依說明產生呼叫。所以 description 與 schema 對 agent 來說是即時生效的契約條款：說明寫錯、或改了說明，下一次對話的呼叫就跟著變，中間沒有工程師審查的那一步。Anthropic〈Writing effective tools for agents — with agents〉（2025-09-11，下文簡稱〈Writing effective tools for agents〉）寫工具的說明會一起引導 agent 的呼叫行為，建議像對團隊新人描述工具那樣寫。[11.14 契約條款的送達](/backend/11-api-design/contract-clause-delivery/) 把送達手段分成機制層、型別與 schema、執行期回饋與文件幾層，文件層送得到的消費者最少，因為消費者要主動去讀才知道；對 agent，工具的 description（文件層）與參數的 schema（型別與 schema 層）每一次對話都會被讀到，文件層從要消費者主動去讀、最常沒被讀到的一層，變成每一次呼叫前都被讀到的一層。所以對 agent，改 description 等於一次不升版的契約變更：改之前要照 [11.6 向後相容的變更紀律](/backend/11-api-design/backward-compatibility-discipline/) 判斷它會不會改變既有的呼叫；退場通知也不能只放在 Deprecation 這類 header，header 不一定到得了模型（從機制推論；退場的工具在 [11.5 版本策略與 deprecation](/backend/11-api-design/versioning-and-deprecation/)）。

**契約被改壞時不回報。** 整合團隊在契約被改壞的隔天會開票；agent 拿到不符預期的回應時，模型把工具結果當成事實讀進 context，照著那份回應往下做，可能回報使用者「查無資料」、或改用另一支工具，不會有人寫信給 API 提供者（從機制推論；回應被模型讀錯的形態見 LLM 模組的 [tool result misread](/llm/knowledge-cards/tool-result-misread/) 卡）。這一點跟非人格中介（proxy、快取層、泛型 HTTP client 這類依 status 自動做決定、不讀文件的程式，見 [API Consumer Shape](/backend/knowledge-cards/api-consumer-shape/)）相同：做錯決定時沒有任何訊號回到提供者。差別在 agent 背後有一個設定它的人，那個人可能是整合團隊、也可能是終端使用者自己；agent 把錯誤原文轉給那個人時，錯誤有機會經由他回報，而設定 agent 的是終端使用者時，他手上沒有 API 提供者的聯絡管道，也不一定知道錯誤出在哪一個 API（從機制推論）。

**看到錯誤會自己重試。** MCP 規格規定工具的執行錯誤應該（SHOULD）放在工具結果裡、標 `isError: true`，不要當成協議層的錯誤回傳，理由是這樣模型才看得到錯誤並自我修正（MCP 規格的 `CallToolResult`，2025-11-25 版與 2026-07-28 版寫法相同）。模型讀到錯誤之後，可能改參數再呼叫一次、可能原樣再呼叫一次，也可能放棄；它依據的是錯誤回應裡寫了什麼。agent 框架寫死的 retry 邏輯只處理它認得的 status；其餘的錯誤要不要重試、怎麼改參數，改由模型讀錯誤訊息決定。

這幾種行為合起來，讓 agent 成為一種新的消費者形態：它跟整合團隊一樣讀文件（只是在執行時讀），跟非人格中介一樣不回報，重試的方式又由每一次的錯誤訊息決定。呼叫的形狀在執行時才決定、中間沒有工程師審查，核准規則代替了審查，而核准規則常常依 method 分讀寫，所以 method 的讀寫語意變得承重；模型在執行時讀說明，所以 spec 的說明變得承重；自己重試，讓錯誤回應的分類與寫入的冪等變得承重；不回報，讓 agent 流量的觀測變得承重。

## HTTP method 的安全語意與讀寫入口

[11.3 資源建模與操作語意](/backend/11-api-design/resource-modeling-operation-semantics/) 把 HTTP method 定為對中介層與消費者的承諾：GET 承諾沒有副作用，所以 proxy 與瀏覽器會據此重試與預取。MCP server 把 API 包成工具時，常常直接拿 method 分讀寫：Stripe 的 MCP server 用 `stripe_api_read` 執行 GET，用 `stripe_api_write` 執行 POST、PATCH、PUT 與 DELETE（Stripe〈Model Context Protocol (MCP)〉）。這兩支把許多 endpoint 收進一支、依讀寫分開的工具，就是本篇說的讀寫入口；4.25 把這種以參數指定操作的工具稱為分派工具。MCP client 執行一支工具之前，可以先停下來請使用者同意；這組依工具決定要不要停下來的設定稱為核准規則，由使用者或部署 agent 的人設定。Stripe 文件只建議開啟 client 的工具核准；依這兩支工具的名稱設，讀取那一支不經同意直接執行（自動放行）、寫入那一支要使用者確認，是 client 依名稱核准時的一種設法（[4.25 MCP 工具的核准規則與執行風險](/llm/04-applications/mcp-tool-approval-and-risk/) 的〈分派工具的切分〉）。

這個分法成立的前提是 API 的每一個 GET 都沒有副作用。API 裡只要有一個會改狀態的 GET（`GET /orders/123/cancel`、讀取時順便標成已讀、讀取時扣額度），依 method 分讀寫的 MCP server 就會把這個動作放進讀取那一支，而讀取那一支被設成自動放行，agent 改狀態時沒有人確認（從機制推論）。對瀏覽器與 proxy，有副作用的 GET 會被預取或重試；對 agent，同一個缺陷的後果是核准規則失效。所以 method 語意在 agent 這種呼叫方上，從「中介層的行為」延伸到「核准的分界」。

反方向的錯放同樣存在：API 用 POST 做查詢或試算時（`POST /search`、GraphQL 的 query、Stripe 的建立預覽發票 `POST /v1/invoices/create_preview` 只試算、不建立發票，依 method 歸進 `stripe_api_write`），依 method 分讀寫會把這些查詢放進寫入那一支。讀取也要等使用者確認，確認的次數多了，使用者可能乾脆把寫入那一支設成自動放行；開了唯讀模式的 agent 則用不到這些查詢（從機制推論）。GraphQL 這類只有一個 endpoint 的 API，method 分不出讀寫，讀寫的分界是 operation type：GraphQL-over-HTTP 規格草案寫明 mutation 不能用 GET 執行，理由是要符合 HTTP 安全 method 的語意；Apollo MCP Server 解析 operation type 來分，mutation 是否開放由設定檔的 `mutation_mode` 決定（Apollo〈Apollo MCP Server〉的設定文件）。

MCP server 從 API 描述產生工具時，也常照 method 填工具的 MCP 標註：rmcp-openapi 依每個 OpenAPI 操作的 HTTP method 自動產生標註，GET 標 `readOnlyHint`（不修改環境），PUT 與 DELETE 標 `idempotentHint`（同樣的參數重複呼叫不產生額外效果）；Apollo MCP Server 對 GraphQL query 預設標唯讀（rmcp-openapi 的 README、Apollo〈Define tools〉）。會改狀態的 GET 因此拿到唯讀標註，實作上不冪等的 PUT 拿到冪等標註，client 依標註放行或重試時，錯在 API 的 method 語意（後果從機制推論；標註只是提示、client 什麼條件下不能信任它，在 [4.25〈MCP 標註與工具名稱的信任〉](/llm/04-applications/mcp-tool-approval-and-risk/)）。

核准規則依賴 MCP server 如實分類，也依賴 client 照規則停下來；API 提供者自己做得到的一道，是把授權範圍照讀與寫切開（必要時再照資源切），讓 agent 的憑證只拿到任務要用的權限。agent 用唯讀的憑證送出寫入請求時，API 直接回權限不足，不經過 method 分類，也不靠核准規則。這要求 API 的 scope 在設計時就分得出讀與寫（[Authorization Scope](/backend/knowledge-cards/authorization-scope/)；依任務授予權限範圍的做法在 [4.25〈設定時拿掉寫入能力〉](/llm/04-applications/mcp-tool-approval-and-risk/)）。

寫入那一支涵蓋的動作，風險各不相同：建立客戶與建立退款都是 POST，退款送出就是錢離開帳戶，建立錯的客戶刪掉就好。Stripe 在 server 端依動作本身決定是否要求人工確認，文件寫「確認取決於動作，不只看工具名稱」：建立退款要，建立客戶不用（同一份 Stripe 文件；確認的流程在 [4.25〈server 端確認的兩種做法〉](/llm/04-applications/mcp-tool-approval-and-risk/)）。server 端要做到這種依動作的確認，API 得讓 method 加路徑就辨認得出是哪一個動作；同一個 endpoint 依 body 的某個欄位做幾種不同風險的事時，依動作確認就要解析 body（從機制推論）。

## 錯誤回應：可重試與終態的分類，以及給模型讀的訊息

[11.4 錯誤模型設計](/backend/11-api-design/error-model-design/) 把錯誤分類的第一刀定為可重試與終態：可重試指示消費者退避後重送，終態指示停止重試、走修正或人工路徑。消費者是工程師寫的程式時，可重試與終態的分類由 status 與錯誤碼表達，程式依它們走寫好的分支；消費者是 agent 時，模型讀整份錯誤回應，再決定重試、改參數或放棄。

所以錯誤回應對 agent 有兩層讀者。status 與錯誤碼給 agent 框架裡寫死的 retry 邏輯與中介層；錯誤訊息的文字給模型。模型讀得到的是 MCP server 放進工具結果的內容：server 原樣轉發錯誤 body 時，API 的錯誤訊息直接給模型讀；server 自己改寫時，它只能用 API 給它的資訊，哪個參數錯、合法的值是什麼只有 API 知道，所以這些資訊仍要由 API 的錯誤回應提供（從機制推論）。

依 status 寫的 retry 邏輯，前提是 status 分得出可重試與終態；GraphQL 的執行錯誤回 2xx、錯誤寫在 `errors` 裡（GraphQL-over-HTTP 規格草案對同時有 `data` 與 `errors` 的回應建議回 294 Partial Success，不認得 294 的 client 把它當成 200），GitHub REST API 的限流與權限不足都可能回 403，這兩種情形下可重試與終態要另外寫在錯誤碼或 body 的欄位裡（GraphQL 寫在 `errors[].extensions`）。

Anthropic〈Writing effective tools for agents〉建議把工具的錯誤回應寫成清楚指出具體、可以照著改的方向，不要只給不透明的錯誤碼或 traceback。對照錯誤模型設計那一章的分類，錯誤訊息要寫出的方向依錯誤的種類分開寫；終態指原樣重送不會成功，改了參數會不會成功再分成兩種：

- **終態、改參數就能成功**（參數格式錯、必填欄位缺）：訊息寫出哪個參數錯、合法的值長什麼樣。模型讀得到這一句，下一次呼叫就改對；只給 `400 invalid_request`，模型可能原樣重送，或猜另一個值（從機制推論）。
- **終態、改參數也不會成功**（權限不足、業務規則拒絕、資源不存在）：訊息寫出這個動作在目前的權限或狀態下做不到。從機制推論，訊息沒說清楚時，模型可能換參數反覆嘗試，每一次都是一筆沒有用的請求。
- **可重試**（限流、暫時失效）：status 與 `Retry-After` 照 [11.9 對外流量語意](/backend/11-api-design/external-traffic-semantics/) 給。MCP server 放進工具結果的通常是 body，`Retry-After` 這類 header 不一定到得了模型（從機制推論），所以等待時間另外放進 body 的結構化欄位（RFC 9457 允許錯誤類型自訂擴充欄位），或由 MCP server 把 `Retry-After` 轉寫進工具結果；寫成結構化欄位，程式與模型都讀得到，也不會跟 header 的值分歧。agent 框架有 retry 邏輯時由它處理；沒有時，模型可能立刻重送（從機制推論）。

分類標錯有兩個方向：可重試被標成終態，暫時的故障變成永久失敗；終態被標成可重試，重試會反覆打在一個不會成功的請求上。後一個方向，[接收方的重試決策](/backend/11-api-design/consumer-retry-decision/) 寫的重試放大與 retry 風暴對 agent 一樣成立。差別是同一個錯誤要重試幾次，常常由模型在框架給的輪數上限之內自己決定什麼時候放棄，消費端的程式沒有寫死這個次數；同一個錯誤同時打到很多個 agent 對話時，各自的重試疊加在 API 上（從機制推論）。[retry budget](/backend/knowledge-cards/retry-budget/) 要做在發出重試的程式裡：自己營運 MCP server 的提供者在 server 裡做；agent 框架由設定 agent 的人決定，提供者改不到，所以 API 端照 11.9 做的限流，是提供者一定握得住的那一道，不能靠模型自己節制。

錯誤訊息寫給模型讀，另外帶來一個限制：訊息裡的內部細節（堆疊追蹤、資料表名稱、內部服務名稱）會進到模型的 context，再可能出現在模型給使用者的回答裡。錯誤細節對 API 呼叫方暴露多少，在 [錯誤傳播與信任邊界：中間服務的雙重身分](/backend/11-api-design/error-propagation-trust-boundary/)；[11.16 面向終端使用者的錯誤碼與請求編號](/backend/11-api-design/end-user-error-code-and-reference-id/) 的錯誤畫面不放內部服務名稱、資料表與堆疊追蹤，理由同樣適用於 agent 讀的錯誤訊息，而且 agent 還可能把它轉述給使用者。回應裡由終端使用者寫入的欄位（工單內文、客戶名稱），以及錯誤訊息回顯的請求參數，同樣原樣進到模型的 context。所以錯誤訊息要指出錯在哪裡時，寫參數名稱與合法的格式就夠了，不原樣回顯參數的值。有人在這些欄位裡寫進指令時，就是間接的 [prompt injection](/llm/knowledge-cards/prompt-injection/)。API 提供者擋不住這條路，後果怎麼治理（工具權限、agent loop 的限制、確認點）在 [LLM Agent Prompt Injection 後果治理](/backend/07-security-data-protection/llm-prompt-injection-in-agent/)。

## 長時操作的 202 與請求端的未知欄位

長時操作回 202 時，body 要寫出操作已接受、還沒完成、不要重送、去哪裡查、隔多久再查。只靠 status 與 `Location` header 時，模型讀到的工具結果可能只有空 body 或一個 id，它可能回報使用者已完成，或讀成沒做成而再呼叫一次（從機制推論）。MCP 規格另有讓 client 輪詢長時間執行工具的 task 機制：2025-11-25 版以實驗性功能放進規格（工具用 `ToolExecution.taskSupport` 宣告），2026-07-28 版移成 `io.modelcontextprotocol/tasks` extension。MCP server 可以拿 API 的狀態資源接上它。202 之後才失敗的表達在 [Status 裝不下的東西](/backend/11-api-design/status-expressiveness-boundary/)，長時操作的資源在 [11.7 集合介面設計](/backend/11-api-design/collection-interface-design/) 的〈長時操作：把「進行中」實體化〉。

請求端的未知欄位是 agent 才常見的情形：模型可能填一個 schema 沒有的參數（以為有 `dry_run`、`confirm: false`，或把欄位名拼錯）。API 對請求端的未知欄位靜默忽略時，那個參數不生效、寫入照常執行，回應看起來跟預覽一樣成功。對 agent 會呼叫的寫入 endpoint，請求端的未知欄位回終態錯誤、在訊息裡寫出不認得的欄位名，模型下一次呼叫才知道這個參數不存在（從機制推論）。回應端多了欄位要不要讓消費者忽略，是另一個決定，在 [11.6 向後相容的變更紀律](/backend/11-api-design/backward-compatibility-discipline/)。

## 寫入的冪等：agent 重送造成的重複寫入與扣款，以及 idempotency key 由誰產生

請求逾時、連線中斷之後的重送，任何消費者都會遇到；agent 多了一種：模型沒讀懂回應而再呼叫一次（從機制推論）。兩種都可能讓同一筆建立或扣款送出兩次。[11.8 API 層冪等設計](/backend/11-api-design/api-idempotency-design/) 寫的 [idempotency key](/backend/knowledge-cards/idempotency-key/) 是同一個解法：同一個 key 重送時，伺服器回傳第一次的結果，不再執行一次。

agent 這種呼叫方多出來的是「key 由誰產生」。11.8 要消費者產生 key，理由是只有消費者知道哪幾次請求屬於同一次操作；整合團隊的程式碼在一次邏輯操作開始時產生 key，重試時沿用同一個。呼叫方是 agent 時，消費者分成 MCP server 與模型兩方：MCP server 只知道一次工具呼叫的邊界，模型知道任務的意圖，而模型每一次重新產生呼叫時，不保證沿用上一次的 key，也可能根本沒填。從機制推論，key 要由確定性的程式產生，而不是交給模型填：MCP server 在一次工具呼叫裡產生 key，那次呼叫內部的重試沿用同一個；模型在下一輪重新呼叫同一支工具時，算新的一次邏輯操作。

MCP server 每次工具呼叫產生一個新 key 時，擋得住的是 MCP server 呼叫 API 那一段的網路重送。擋不住的有兩種，因為它們都是新的一次工具呼叫、拿到新的 key（從機制推論）：

- client 到 MCP server 那一段逾時之後，模型重新呼叫同一支工具。
- 模型沒讀懂回應，決定再做一次。

每次產生新 key 以外，key 還有兩種產生方式（從機制推論）：

- **從參數算出 key**：MCP server 把工具名稱、正規化之後的參數加上 session 的識別碼一起雜湊。模型原樣再呼叫一次時會算出同一個 key，所以逾時後的重新呼叫與模型決定再做一次都擋得住；代價是使用者刻意要做兩次相同的操作時會被合成一次，所以要設時間窗。
- **由業務識別碼組成 key**（訂單號加動作）：跟 11.8 說的「一次邏輯操作」對得上，同一張訂單的同一個動作不論重送幾次都是同一個 key；代價是組 key 的人（MCP server 或模型）要拿得到那個業務識別碼。

所有 key 都擋不住的重複（參數不同、卻是同一件事），要靠 API 的業務層檢查（同一張訂單已經退過款），或 [4.25〈server 端確認的兩種做法〉](/llm/04-applications/mcp-tool-approval-and-risk/)。Stripe 的 MCP 文件沒有提到寫入是否帶 idempotency key；用自己的 API 包 MCP server 時，這一點要在 server 的實作裡決定。模型寫程式碼呼叫 API 的形態（Cloudflare 那一種），key 由 server 提供給沙盒的 client 決定：client 自動替寫入補上 key 時，效果跟 MCP server 產生 key 相同；client 不補、要模型自己填時，key 等於交給模型（從機制推論）。

## OpenAPI spec 與 endpoint 說明在 agent 搜尋 endpoint 時的用途

agent 要從上百個 endpoint 裡找出這一次要用的那個時，搜尋的對象就是 API 的描述資料。Cloudflare 的 MCP server 讓模型寫程式碼在 Cloudflare 的 OpenAPI spec 裡找 endpoint（Cloudflare〈Code Mode: give agents an entire API in 1,000 tokens〉，2026-02-20；機制在 [4.24〈延遲載入以外控制工具定義的做法〉](/llm/04-applications/mcp-tool-surface-design/)）。MCP server 把 endpoint 包成工具、client 做[延遲載入](/llm/knowledge-cards/deferred-tool-loading/)時（一開始只把工具名稱交給模型，模型搜尋到要用的工具之後才載入它的完整定義），被搜尋的是工具的名稱與 description；這些從 OpenAPI spec 自動產生工具時，取的就是 `summary`、`description` 與參數說明（從機制推論）。

所以 OpenAPI spec 的說明欄位在 agent 這種呼叫方上，承擔的是搜尋索引的工作；GraphQL 的 schema description 經由 introspection 被搜尋時，承擔的是同一件事（Apollo MCP Server 用 introspection 讓 agent 探索可用的操作）。從機制推論，三種寫法會讓 agent 找不到 endpoint：說明只有內部代號或跟路徑重複（`GET /v2/acct_lnk` 的說明寫「account link」）；同一件事在不同 endpoint 用不同的詞（有的寫 customer、有的寫 client）；說明沒有使用者描述任務時會用的字詞。搜尋沒有命中時回傳的是空結果、不是錯誤，agent 不知道那個 endpoint 存在，回報做不到（[4.24〈延遲載入的機制與它的代價〉](/llm/04-applications/mcp-tool-surface-design/) 稱為搜尋落空）。描述格式的選型在 [描述格式的選型：OpenAPI 與 AsyncAPI](/backend/11-api-design/styles/standards/standards-description-formats/)，規範怎麼進審查與 CI 在 [11.10 API 規範治理](/backend/11-api-design/api-governance/)。spec 的說明寫得好不好，原本影響的是讀文件的工程師看不看得懂；對 agent 來說，endpoint 會不會被搜尋到，要看說明裡有沒有模型搜尋時用的字詞。

API 的回應被 agent 讀時，每一個欄位都佔模型的 [context](/llm/knowledge-cards/context-window/)，所以回應的欄位多寡也影響 agent：Anthropic〈Writing effective tools for agents〉建議工具只回傳高訊號的資訊，少用 `uuid`、`mime_type` 這類低階識別欄位，並對可能很大的回應提供分頁、篩選或截斷，給合理的預設值。API 的回應原本為程式設計，欄位多、識別碼多不影響程式；agent 讀回應時每個欄位都佔 context。挑欄位可以由 MCP server 這一層做，只把需要的欄位放進工具結果；API 這一端要做的是提供分頁（[11.7 集合介面設計](/backend/11-api-design/collection-interface-design/)）與欄位選擇（讓呼叫方指定只回傳哪些欄位的參數，稱為 sparse fieldsets，見 [11.12〈欄位級用量的可答性與介面的宣告機制〉](/backend/11-api-design/consumer-usage-observability/)）的參數，MCP server 才有參數可以傳。分頁的接續標記（[cursor](/backend/knowledge-cards/pagination-cursor/)）交給模型轉抄時，可能被截斷、改寫或憑空產生；接續標記不透明、而且伺服器端驗得出被改過時，改壞的值回終態錯誤，不會回錯的那一頁。MCP server 也可以把接續標記留在自己這一端，不交給模型。回應裡還有沒有下一頁要寫成明確的欄位，模型才不會把第一頁當成全部（從機制推論）。

## 用量觀測：把 agent 的流量分出來

[11.12 API 消費者用量觀測](/backend/11-api-design/consumer-usage-observability/) 把消費者身分分成歸屬層（API key 或 OAuth client_id，發放時就綁定組織）與診斷層（User-Agent、版本字串，呼叫端自己填）。11.12 的〈消費者身分的識別符：歸屬層與診斷層〉談身分時，針對的是會被通知、會回報的消費者；同一節列了三種用途（通知、舉證、影響評估），並寫明舉證與影響評估（事故當天算得出波及誰）不需要對方會回報。agent 的流量要分出來，用途有兩種：一是影響評估，agent 踩到錯誤不會回報，波及哪些 agent 只能從觀測算；二是那三種用途之外的一種，錯誤訊息或說明欄位改了之後，量 agent 的成功率有沒有變。

歸屬層的做法是發給 agent 專用的憑證。Stripe 在 Dashboard 以 Agent 標記辨識 agent 用的 API key，經 OAuth 授權的 MCP client 列在使用者設定的 OAuth sessions 裡，並公告 2026 年 12 月起 Stripe MCP 不再接受沒有 Agent 標記的完整權限 key 與受限 key（Stripe〈Model Context Protocol (MCP)〉）。專用憑證讓 agent 的流量在歸屬層就分開，權限範圍也可以單獨縮小；配額要不要照憑證分開計，是提供者另外的設計選擇：Stripe 的限流依帳號計，agent key 與同一個帳號的其他整合共用額度（Stripe〈Rate limits〉）；提供者把配額改成依憑證計時（[11.9 對外流量語意](/backend/11-api-design/external-traffic-semantics/)），一個 agent 的重試疊加起來時，耗盡的是它自己那一份，同一個帳號下的其他整合不受影響（從機制推論）。專用憑證分得出的，是經由提供者指定入口進來的 agent 流量；agent 拿開發者環境裡現成的 key 跑 CLI 或 SDK 時，歸屬層看到的是那個人，只能從診斷層或呼叫的模式推測（從機制推論）。

診斷層有 MCP 的 client 資訊：2025-11-25 版的規格裡，client 連上 MCP server 時在 `initialize` 送出 `clientInfo`，帶 client 的名稱與版本；2026-07-28 版改成每個請求都可以在 `_meta` 帶 `io.modelcontextprotocol/clientInfo`，並寫明這個值由 client 自己申報、協議不驗證，用途是顯示、記錄與除錯，server 不應該依它做安全決定。client 資訊跟 User-Agent 一樣只能歸在診斷層：值可能不準，不能拿來做歸屬或授權。client 資訊只送到 MCP server；MCP server 再呼叫 API 時，API 在診斷層看到的是 MCP server 自己的 User-Agent，歸屬層看到的是 MCP server 帶過去的憑證（從機制推論）。所以自己營運 MCP server 的團隊，要在 MCP server 呼叫 API 時把 client 的名稱與版本帶下去（例如放進自訂 header），API 端的觀測才分得出是哪一種 agent（從機制推論）。

## MCP 工具的切法與 endpoint 的切法

API 的 endpoint 依資源與操作切（[11.3 資源建模與操作語意](/backend/11-api-design/resource-modeling-operation-semantics/)），服務的是所有消費者；MCP 工具依模型挑工具、核准規則與 context 佔用切，服務的是 agent。兩者可以不同，各家的 MCP server 也確實不同：Stripe 用四支工具（搜尋 API 操作、取得某個操作的參數說明、執行讀取、執行寫入）開放它列出的那一批 API 操作（Stripe 文件稱為 API method，並寫這讓大部分 API 可經由 MCP 使用），另有帳戶、分析、文件搜尋這類專用工具；Cloudflare 用兩支工具涵蓋兩千五百多個 endpoint，`search` 搜的就是既有的 OpenAPI spec。Anthropic〈Writing effective tools for agents〉建議不要把 endpoint 逐一包成工具，舉的例子是用一支 `schedule_event` 取代 `list_users`、`list_events`、`create_event` 三支：合併發生在工具這一層，三個 endpoint 照樣存在。

這一節假設提供者自己營運 MCP server。提供者不營運、消費者用通用工具從 OpenAPI 轉出工具時，endpoint 的切法與說明直接就是工具的切法與說明，前面寫的說明欄位品質與這一節的切法都直接由 API 決定（從機制推論）。

提供者自己營運 MCP server 時，任務形狀的工具可以在 server 裡用既有的 endpoint 組出來，所以要為 agent 改 API 的，是 MCP server 組不出來的情形：

- **一件任務要好幾個寫入，而中途失敗會留下不一致的狀態時**，MCP server 依序呼叫幾個 endpoint，做不到全部成功或全部不生效（原子性）；這時 API 要提供一個在伺服器端完成整件事的 endpoint 或批次操作（[11.7 集合介面設計](/backend/11-api-design/collection-interface-design/) 的〈批次操作：部分失敗是預設、不是例外〉）。這個理由對任何消費者都成立，agent 只是讓它更常出現。
- **API 沒有分頁或欄位選擇的參數時**，MCP server 只能整份拿回來再裁，API 每次都要查出並傳完整份資料，MCP server 再丟掉用不到的部分。
- **API 只用 webhook 回報完成、沒有可以查詢的狀態資源時**，agent 收不到回呼；MCP server 要組出「等到做完」，就得自己接收 webhook 並保存完成狀態。API 提供可以查詢的狀態資源時，server 用 MCP 的 task 機制或輪詢就接得上，不必自己保存狀態（從機制推論）。
- **API 的權限範圍切不出 agent 要的最小權限時**（只有讀寫全部），核准規則管不到的路徑（程式碼執行、直接拿 token 呼叫）只剩 token 的權限擋得住，這要在 API 的 scope 或受限 key 裡切（從機制推論）。

有副作用的 GET、POST 做的查詢，以及同一個 endpoint 依 body 做不同風險的事，是另一類：提供者自己營運的 MCP server 可以逐個操作分類，把那支 GET 放進寫入那一支、把那支 POST 查詢放進讀取那一支，或逐支標 MCP 標註，不必改 API。只有 server 只能依 method 分類時（用通用的 OpenAPI 轉工具、或第三方的 server），才要動 API；動 API 的做法是新增一個用寫入 method 的 endpoint 做同一個動作，舊的 GET 照版本策略退場；POST 做的查詢在參數放得進 URL 時，另外提供 GET 版本；直接把 GET 改成寫入 method 對所有既有消費者都是破壞性變更，退場照 [11.5 版本策略與 deprecation](/backend/11-api-design/versioning-and-deprecation/) 走，而有副作用的 GET 在瀏覽器與 proxy 預取或重試時同樣會出錯，修它的理由不限於 agent。

其餘的情形，工具怎麼切、要不要延遲載入、要不要讓模型寫程式碼，是 MCP server 這一層的決定，條件在 [4.24 MCP 工具數量多時工具定義怎麼交給模型](/llm/04-applications/mcp-tool-surface-design/)。

## API 提供者要為 agent 做哪些事的判斷條件

上面幾節的條件在 agent 身上變得承重。API 提供者逐項對照自己的 API，各項的情形與後果如下：

- **API 裡有沒有會改狀態的 GET，或不改狀態的 POST。** 有會改狀態的 GET 時，依 method 分讀寫的 MCP server 會把它放進讀取那一支，而讀取那一支常被設成自動放行；有 POST 做的查詢時，查詢會落進寫入那一支，讀取也要確認。自己營運 MCP server 時逐個操作分類就能修；server 只能依 method 分類時，要動 API。既沒有會改狀態的 GET、也沒有做查詢的 POST 時，依 method 分讀寫的入口可以直接沿用。GraphQL 這類單一 endpoint 的 API，讀寫依 operation type 分。
- **授權範圍分不分得出讀與寫。** 分不出來時，agent 的憑證只能整份給，讀寫的分界只剩 client 的核准規則；分得出來時，唯讀的憑證送出寫入請求會被 API 直接拒絕。
- **寫入 endpoint 收到 schema 沒有的欄位時怎麼處理。** 靜默忽略時，模型以為生效的參數（例如預覽）不生效，寫入照常執行；回終態錯誤並寫出欄位名時，模型下一次呼叫就知道它不存在。
- **錯誤回應有沒有分出可重試與終態，訊息有沒有寫出能照著改的方向。** 沒有的話，agent 可能原樣重送終態錯誤、或不等 `Retry-After` 就立刻重送可重試的錯誤（從機制推論）；API 端的限流是提供者一定握得住的那一道，retry budget 做在自己營運的 MCP server 裡，不靠模型節制。
- **錯誤訊息有沒有帶堆疊追蹤、資料表或內部服務名稱。** 有的話，這些細節會進模型的 context，再可能被模型轉述給使用者。
- **會被重試的寫入有沒有 idempotency key，key 由誰產生。** 沒有 key 時，逾時重送與模型再呼叫一次都可能讓寫入執行兩次；由模型填 key 時，模型每次重新產生呼叫都可能換一個 key；由 MCP server 在一次呼叫裡產生時，擋得住 MCP server 到 API 那一段的網路重送，擋不住 client 端逾時後的重新呼叫與模型決定再做一次；由 MCP server 從工具名稱與參數雜湊出 key 時，模型原樣再呼叫也擋得住，代價是刻意的重複操作會被合併；模型寫程式碼呼叫 API 時，看沙盒裡的 client 會不會替寫入補 key。
- **OpenAPI spec 與 endpoint 的說明，寫的是不是使用者描述任務時會用的字詞。** 不是的話，agent 搜尋 endpoint 時落空，而落空時搜尋回傳的是空結果、不是錯誤。
- **觀測分不分得出 agent 的流量。** agent 不回報，分不出來時，它踩到的錯誤與說明改動之後的成功率變化都看不到；專用憑證在歸屬層分開，client 自報的名稱與版本只能當診斷層。
- **非同步操作有沒有可以查詢的狀態資源，202 的 body 有沒有寫明已接受、不要重送。** 只有 webhook 時，agent 收不到完成通知；202 的 body 沒寫清楚時，模型可能讀成沒做成而再呼叫一次。
- **集合 endpoint 有沒有分頁與欄位選擇的參數。** 沒有的話，MCP server 只能整份拿回來再裁，API 每次都要查出並傳完整份資料。
- **一件任務是否需要 API 端的原子性或批次。** 需要的話，MCP server 組不出來，要動 API；不需要、而提供者自己營運 MCP server 時，任務形狀的工具在 server 裡組，API 的切法照所有消費者的需要決定；提供者不營運 MCP server、消費者用通用工具從 OpenAPI 轉出工具時，endpoint 的切法與說明直接就是工具的切法與說明。

## 延伸閱讀：MCP server 的工具設計、核准規則、消費者形態與錯誤契約

- MCP server 把大量 API 交給模型的做法（延遲載入、分派工具、靜態篩選、程式碼執行）與各自的代價，在 LLM 模組的 [4.24 MCP 工具數量多時工具定義怎麼交給模型](/llm/04-applications/mcp-tool-surface-design/)；client 依工具名稱的核准規則、server 端確認與唯讀模式，在 [4.25 MCP 工具的核准規則與執行風險](/llm/04-applications/mcp-tool-approval-and-risk/)。
- 消費者依會不會回報、改不改得動分成的幾種形態，以及 agent 在這兩個軸上的值，在 [API Consumer Shape](/backend/knowledge-cards/api-consumer-shape/)。
- 錯誤回應的 status、錯誤碼與重試決策在消費者與提供者之間怎麼分工，在 [11.11 Status 與錯誤的雙向契約](/backend/11-api-design/error-bidirectional-contract/) 與它底下的 [接收方的重試決策](/backend/11-api-design/consumer-retry-decision/)。
- 契約條款經由機制、型別、執行期回饋與文件送達時各層的強制力，在 [11.14 契約條款的送達](/backend/11-api-design/contract-clause-delivery/)。
