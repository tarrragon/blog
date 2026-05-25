---
title: "codebase-memory-mcp：155 語言 tree-sitter 知識圖譜 MCP 的能力與邊界"
date: 2026-05-25
draft: false
description: "codebase-memory-mcp (cbm) 的設計拆解：155 vendored tree-sitter grammar、11-signal 語意搜尋、Go / TS / C / C++ 上的 hybrid type resolution、跨 service HTTP/RPC 鏈接，以及在沒有 hybrid resolution 的語言上會降級成什麼樣。"
tags: ["MCP", "AI協作心得", "工具評估", "Claude Code"]
---

## 這個 MCP 解什麼問題

codebase-memory-mcp（下稱 cbm）的核心定位是「**把整個 codebase 預先解析成可被 LLM 廉價查詢的知識圖譜**」。它要替代的是 agent 在不熟悉的 codebase 上「拿 grep / glob / read 連環翻檔」的探索 pattern——不是 IDE。

設計上跟其他「graph + LLM」工具的關鍵分野，在於它**不內嵌任何 LLM 做自然語言 → 查詢轉換**：

> Other code graph tools embed an LLM for natural language → graph query translation. This means extra API keys, extra cost, and another model to configure. With MCP, the agent you're already talking to _is_ the query translator.

所以 cbm 自己只是個提供高品質 graph 查詢 API 的 server，「翻譯自然語言」這件事直接讓呼叫端的 agent 做。這個取捨對 Claude Code 這類 host 是理想的，因為 host 端已經有一顆夠強的模型在跑。

## 部署形態決定它的甜蜜點

cbm 是**單一靜態 binary**，所有依賴（155 種 tree-sitter grammar、SQLite、tokenizer）都在 binary 內，安裝後沒有外部 runtime 依賴。

這個取捨直接影響它的甜蜜點：

- 跨平台分發成本低，CI 上跑也方便
- 不需要為個別語言裝 toolchain（不像 LSP 路線要對應 language server）
- 但代價是「能力上限」被 binary 內附的 grammar 跟自寫的 type resolution 算法綁住，無法靠 IDE 生態的成熟度借力

知道這個取捨之後，後面所有能力差異都解釋得通：能做的事多半是「靜態可推導」的，需要 query 外部 toolchain（如 IDE language server）的場景多半要靠別的工具補。

## 索引架構：多 pass + RAM-first

cbm 的索引流程是 **RAM-first 的多 pass pipeline**，pass 之間有明確的責任分工：

| Pass          | 責任                                   | 抽出的 edge / node（為主）                           |
| ------------- | -------------------------------------- | ---------------------------------------------------- |
| structure     | tree-sitter 解 AST，建初始 node        | Project / Package / Folder / File / Module           |
| definitions   | 抽函式 / 類別 / 介面 / 型別定義        | Class / Function / Method / Interface / Enum / Type  |
| calls         | 解析 function call、結合 import 與型別 | CALLS / ASYNC_CALLS / USAGE / USES_TYPE / IMPLEMENTS |
| HTTP links    | 偵測 REST / gRPC / GraphQL route       | Route、HTTP_CALLS、HANDLES                           |
| configuration | 掃 Docker / Kubernetes / Kustomize     | Resource、CONFIGURES、WRITES                         |
| tests         | 偵測測試函式與被測對象關係             | TESTS、FILE_CHANGES_WITH                             |

執行期用 LZ4 壓縮的記憶體 SQLite 加速，所有 pass 跑完一次性 dump 成持久化 DB（路徑 `~/.cache/codebase-memory-mcp/`，WAL mode）。team 共享情境下可加跑 zstd 壓縮（best tier 用 `zstd -9` + index strip、fast tier 用 `zstd -3` 走 watcher 增量），匯出成 `.codebase-memory/graph.db.zst` artifact 給 CI / 隊友共用。

Pass 排序不是任意的、有明確的依賴關係：calls 一定在 definitions 之後（因為 call edge 要連到已被建出來的 function / method node）、HTTP links 一定在 calls 之後（需要先有 call edge 才能比對 route 跟 handler）、configuration / tests 是 cross-cutting 的最終層（前面的結構與 call graph 都齊備、它們才能掛上 CONFIGURES / TESTS edge）。實務影響：HTTP links pass 在「單 service repo」上等於 no-op、configuration pass 在「沒 IaC manifest」的 repo 上也是 no-op、這兩個 pass 的價值高度依賴 repo 結構。

這個架構的副作用是：**單次完整 index 速度快**（README 聲稱 Linux kernel 3 分鐘），但**增量更新仰賴背景 git polling**而非 IDE-style file watcher 立即觸發。對「邊改邊查」的工作流，會有秒級延遲。

## 11-signal 語意搜尋：cbm 最強的差異化

如果只看 README 寫的「BM25 全文搜尋」，會嚴重低估 cbm 的搜尋能力。實際上 `search_graph` 的 ranking 是 **11 個 signal 的加權組合**：

| Signal                           | 角色                                             |
| -------------------------------- | ------------------------------------------------ |
| TF-IDF                           | 詞頻 / 逆文檔頻率，傳統文字相關性                |
| RRI                              | Reverse rank importance，符號在 graph 中的重要性 |
| API / Type / Decorator signature | 函式簽章、型別標註、decorator 是高權重訊號       |
| AST profile                      | AST 結構相似性                                   |
| Data flow                        | 變數與參數依賴鏈                                 |
| Halstead-lite                    | 簡化的程式複雜度指標                             |
| MinHash                          | 近重複偵測（找變體 / 複製貼上）                  |
| Module proximity                 | 符號在依賴 graph 上的距離                        |
| Graph diffusion                  | 在 graph 上做 spreading activation               |

表格列了 9 個明確 signal、README 另說有 11 個（剩 2 個是 implementation detail 沒公開細節）。實務上 11-signal 的價值在於**幾個高權重 signal 各自負責不同 query 類型**——所有 signal 並非等權：

- **RRI** 是 cbm 對「重要符號優先」的 graph 結構 prior。一個被大量檔案 import 的核心 class、即使在 query 字串裡只有間接匹配、RRI 也會把它往上推。這層對「找這個 codebase 的入口 / 主要抽象」類 query 特別重要。
- **Data flow** 是 cbm 對「概念上接近、但符號名沒共字」的 query 的關鍵 signal。例如查「金額顯示」、`formatAmount` 跟 `_buildPriceDisplay` 在符號名上沒共字、但 data flow 能捕捉「`formatAmount` 的回傳值流入了 `_buildPriceDisplay` 的 widget」這層連結。
- **Graph diffusion** 是 cbm 對「擴散式相關性」的最終 boost——已經被前面 signal 推到高分的符號，會把分數擴散到 graph 上鄰近的符號。實務影響：monorepo 上效果最強（跨 module 鄰近性有意義）、單一檔案的小專案上幾乎沒效果。

加上一層 **`cbm_camel_split` tokenizer**：對 `getMoneyField` 這類 identifier 做 camelCase / snake_case 切詞，所以查 `money field display` 能命中 `getMoneyField`、`MoneyFieldRenderer` 之類符號。

這套組合的判讀價值在於：**對「我不知道精確符號名」的概念性查詢，cbm 是少數能給出合理 top-N 的工具**。例如查「金額顯示相關」、結果裡會出現 `formatAmount` 實作 + `_buildPriceDisplay` + `getBalanceDisplay`，這些都跟「金額顯示」業務概念相關、不會被 `displayName` / `displayTags` 這種只共享 `display` 子字串的雜訊淹沒。

下一步路由：要看實測案例，見 [三 MCP 工作流與 Dart 實測]({{< relref "mcp-three-way-workflow-and-dart-experiment.md" >}})。

## Hybrid type resolution：只給五個語言的特殊待遇

cbm 對 **Go / C / C++ / TypeScript / JavaScript**（JS 含 JSX、TS 含 TSX）額外跑一層 type resolution，README 描述是：

> Clean-room reimplementation of tsserver / typescript-go's type resolution algorithms — parameter binding, return-type inference, generic substitution, JSX component dispatch, JSDoc inference for plain JS files.

換言之，這幾個語言的 `CALLS` edge 有 type-aware 的 dispatch resolution（不只停在 syntactic match），效果接近 LSP。其他 149 個語言只跑純 tree-sitter pass，能力會降到「**結構抽得到、call edge 抽不到或抽很少**」。

實測對照（在某 Dart 商業專案上）：

```text
cbm 索引完成統計：3,038 nodes、6,355 edges
其中 CALLS edge 總數：2（整個專案僅 2 條）
```

這個數字反映 cbm 的設計選擇——**Dart 不在 hybrid resolution 名單**——所以 `trace_call_path` 對 Dart symbol 永遠回 0 caller，這個 0 是 by design 不是 bug。對 Go / TS 主力專案，這個能力上限會完全不一樣。

判讀訊號：開發前先確認自己的主力語言在不在那五個語言內。在的話 cbm 是準 LSP；不在的話它只是個「結構 + 全文搜尋」工具，呼叫鏈相關問題要靠別的 MCP 補。

## 跨 service 鏈接：first-class HTTP_CALLS edge

cbm 的另一個差異化能力是把 **REST / gRPC / GraphQL / tRPC route 當 first-class node**，建立跨 service 的 `HTTP_CALLS` edge：

- Route 偵測：對應主流 web framework（Express / NestJS / FastAPI / Gin / Rails 等）的 route 定義語法
- Call site 比對：以 route pattern 比對 client 端的 URL 字面值或變數，附 confidence score
- 額外的 channel edge：Socket.IO / EventEmitter / 各種 pub-sub 的 `EMITS` / `LISTENS_ON`

這層能力對單一 monorepo 內的多 service 架構（microservice repo / BFF / API gateway pattern）特別有價值——可以查「這個前端 API call 對應哪個後端 handler」這種跨 service 問題。對單一 service 的單體 repo，這層能力派不上用場。

實際使用前提：要 index 的 repo 必須**同時包含 client 跟 server 端**，分散在多 repo 的話 cbm 不會自動跨 repo 連邊。

## Cypher 子集：支援的查詢與邊界

cbm 提供的 `query_graph` 是 Cypher 的**真子集**，不是完整 Cypher：

**支援**：

- `MATCH` 含 label / relationship type / 變長路徑
- `WHERE` 含比較 / regex / `CONTAINS`
- `RETURN` 含 property access、`COUNT`、`DISTINCT`
- `ORDER BY`、`LIMIT`

**不支援**：

- `WITH`（不能多階段 pipeline）
- `COLLECT`（不能 aggregate 成 list）
- `OPTIONAL MATCH`（不能 left-join）
- `labels(n)` / `type(r)` 等函數呼叫
- `AS` 別名
- 任何 mutation（純讀）

幾個限制各自踩到的事故型態：

- **`WITH` 缺席**：所有需要「先 match 一組、再 filter / aggregate」的二階段 query 都寫不出來。例如「列出每個 module 內最常被呼叫的 function」這種 Top-K per group 的 query、在 Cypher 是 `MATCH ... WITH module, COUNT(*) AS c ORDER BY c LIMIT 1`、在 cbm 要拆成「先 list modules、再對每個 module 跑一次 callers query、外層排序」。
- **`OPTIONAL MATCH` 缺席**：left-join 場景做不到。例如「列出所有 class、附上它的 supertype（若有）」這種「主結果不該因為某個關係缺失就丟掉」的 query 寫不出來。cbm 上的做法是先抓全部 class、再對每個 class 跑一次 supertype query、在 client 端合併。
- **`labels(n)` 缺席**：拿不到 graph 內所有 node label 種類的清單。想做「我的 graph 裡有哪幾類 node」這種 schema 探索類 query、得退回 `get_graph_schema` 拿固定的 schema 介紹、看不到 instance 層真實分布。
- **`AS` 別名缺席**：query 結果直接是 node / relationship object、沒法 rename 欄位給 downstream consumer。

這些限制的共通實際影響：**想做 group-by-count 類的 graph stats 查詢得退回 `search_graph` 逐 label 抽**。例如「列出每個 file 有幾個 method」這種一行 Cypher 在標準 Neo4j 能寫的、在 cbm 上要拆成多次 query 在外層彙整。

判讀訊號：若 query 需要 `WITH ... COLLECT(...) AS xs` 這類二階段語法，先別硬寫 Cypher，改用 `search_graph` 加 client 端聚合。

## 安裝行為與兩個要注意的小坑

cbm 的 `install.sh` 對 `~/.claude/settings.json` 動的範圍比 README 寫得多。實際安裝會：

- 下載對應平台 binary、剝 macOS quarantine、ad-hoc sign
- 自動偵測 11 種 coding agent，逐一注入 MCP server config
- 對 Claude Code 寫入 `.claude/.mcp.json`、4 個 Skill、PreToolUse hook
- Hook 名稱：`cbm-code-discovery-gate`，攔截 Grep / Glob 注入結構化 context

兩個實際踩過的小坑：

**Hook matcher 與 README 不一致**。README 描述「intercepts Grep/Glob — never Read」，實際安裝版本 matcher 是 `"Grep|Glob|Read|Search"`，連 Read 也被擋。修法：手動把 matcher 改成 `"Grep|Glob|Search"`。注意 `codebase-memory-mcp update` 可能會把這行改回原樣，每次升級要重新確認。

**uninstall 不清 hook**。卸載 binary 不會主動把 `~/.claude/settings.json` 裡的 hook 條目移除。決定不再用 cbm 時要手動清掉 `PreToolUse` 下的 `cbm-code-discovery-gate` 條目，否則之後安裝其他工具或除錯時會看到神祕的 BLOCKED 訊息。

## 14 個 MCP tool 的分類

| 類別 | Tool                                                                                                                                          |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| 索引 | `index_repository`、`list_projects`、`delete_project`、`index_status`                                                                         |
| 查詢 | `search_graph`、`trace_call_path`、`detect_changes`、`query_graph`、`get_graph_schema`、`get_code_snippet`、`get_architecture`、`search_code` |
| 管理 | `manage_adr`（架構決策紀錄 CRUD）、`ingest_traces`（runtime trace 驗證 HTTP_CALLS）                                                           |

特別值得提的兩個：

- `manage_adr`：把 Architecture Decision Records 當持久化資源管理。對長期專案有累積架構決策需求的場景有用，但若團隊已用 ADR-tools 或 Notion 管 ADR，這層會重複。
- `ingest_traces`：餵 runtime trace 進來驗證 `HTTP_CALLS` edge 是不是真的活著。可以把靜態推測的 cross-service edge 與實際 runtime 行為對齊。實務上要先有 distributed tracing 基礎建設才開得了，門檻不低。

## 適用 / 不適用情境的判讀

**適用情境**：

- **主力語言在 Go / C / C++ / TS / JS 名單內** → 享受 hybrid type resolution。判讀方法：對 5 個熱門 class 跑 `trace_call_path`、若 caller 數跟 IDE「Find Usages」結果對得上、表示 hybrid 正常工作。
- **概念性 / 自然語言搜尋需求高** → 11-signal scoring 是少數能勝任的 MCP。判讀方法：對「我只記得功能類別、不記得名字」的 query 跑 cbm 跟其他工具的 search、若 cbm top-10 命中率明顯高、值得當主要入口。
- **跨 service 的 monorepo** → first-class HTTP_CALLS edge 抽得到 cross-service 鏈。判讀方法：repo 內若有多個 service 用 HTTP / gRPC / GraphQL 互相呼叫、又分散在同一個 git tree 內、cbm 能跨 service 連邊；若只是單 service repo 這條沒效。
- **偏好單 binary 部署** → 不想為個別語言裝 toolchain、cbm 是少數零外部依賴的選項。

**不適用情境**：

- **主力語言不在 hybrid resolution 名單**（如 Dart / Swift / Kotlin）且核心需求是 caller / blast radius 追蹤。判讀方法：在自己 repo 跑 cbm `trace_call_path` 對 5 個熱門 class、若 caller 數明顯偏低或 0、表示 cbm 在這語言只剩結構抽取、要靠 LSP 工具補。
- **要 symbol-level 編輯**（rename / replace_symbol_body）— cbm 純讀、沒這層。判讀方法：要做「rename method 並更新所有 reference」這類 atomic refactor 時、cbm 完全幫不上忙、要走 LSP 工具。
- **要編譯 diagnostic 整合** — cbm 不接 LSP、沒法把 type error / unused import 拋給 agent。

**搭配建議**：在不在 hybrid resolution 名單的語言上，cbm 通常需要配合一個 LSP-based MCP（如 [serena]({{< relref "mcp-serena-deep-dive.md" >}})）做 caller / impact 補位，加上一個 tree-sitter call graph 工具（如 [codegraph]({{< relref "mcp-codegraph-deep-dive.md" >}})）做日常結構查詢。三者怎麼分工見 [三 MCP 工作流與 Dart 實測]({{< relref "mcp-three-way-workflow-and-dart-experiment.md" >}})。

## 結論

cbm 的核心價值在三件事：**單 binary 部署**、**11-signal 語意搜尋**、**跨 service HTTP/RPC 鏈接**。前兩件對任何語言都成立，第三件對微服務 monorepo 特別有意義。

它的能力上限被 hybrid type resolution 的語言名單卡死——名單內等於準 LSP，名單外只是個結構抽取器。評估時第一個要問的問題是：「我的主力語言在不在那五個（Go / C / C++ / TS / JS）？」答案決定 cbm 是主刀還是輔刀。
