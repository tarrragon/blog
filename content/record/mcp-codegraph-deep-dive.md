---
title: "codegraph：用 tree-sitter per-language query 撐起 19+ 語言 call graph 的 MCP"
date: 2026-05-25
draft: false
description: "codegraph MCP 的設計拆解：tree-sitter per-language query 抽 call graph、native OS file watcher 2 秒 debounce auto-sync、14 web framework routing、7 codebase benchmark 的 token 節省方法論。重點在 tree-sitter syntactic 路線能解到什麼程度、type-inferred dispatch 仍漏什麼。"
tags: ["MCP", "AI協作心得", "工具評估", "Claude Code"]
---

## 這個 MCP 解什麼問題

codegraph 的設計動機很具體：**Claude Code 探索 codebase 時 spawn 的 Explore agent 會用 grep / glob / read 連續刷檔，每個 tool call 都吃 token**。codegraph 把這層探索預先做好，agent 直接查預建好的 graph。

> When Claude Code explores a codebase, it spawns Explore agents that scan files with grep, glob, and Read — consuming tokens on every tool call. CodeGraph gives those agents a pre-indexed knowledge graph — symbol relationships, call graphs, and code structure.

跟 [cbm]({{< relref "mcp-codebase-memory-deep-dive.md" >}}) 比，codegraph 的 scope 更窄、更專注：不做跨 service 鏈接、不做 ADR / runtime trace 管理、不做 11-signal 語意搜尋，**只把 call graph 跟 symbol relationship 做好**。這個取捨讓它的 MCP tool 只有 10 個、每個責任都很單一。

## 技術架構：tree-sitter + per-language query + FTS5

codegraph 的核心 pipeline：

```text
tree-sitter parse → per-language query 抽 nodes/edges
                  → 解析 reference（import / extends / implements / calls）
                  → 寫進 SQLite + FTS5
```

關鍵設計：**對每個語言寫專屬的 tree-sitter query**，而不是用一份通用的 AST visitor。

> Language-specific queries extract nodes (functions, classes, methods) and edges (calls, imports, extends, implements).

這個設計選擇直接決定了 codegraph 對非主流語言（如 Dart / Svelte / Liquid）的支援深度——因為每個語言都有專屬 query，所以 19+ 語言裡的 Dart 真的有 working call graph，不像純 tree-sitter wrapper 那樣只能抽結構。

實際支援的 19+ 語言：

TypeScript、JavaScript、Python、Go、Rust、Java、C#、PHP、Ruby、C、C++、Swift、Kotlin、Scala、Dart、Svelte、Vue、Liquid、Lua、Luau、Pascal/Delphi。

過濾規則：「**Files larger than 1 MB are skipped**」（generated bundle / minified JS / vendored blob 自動忽略）。

## Auto-sync：native OS file watcher + 2s debounce

codegraph 預設啟用 file watcher、用 native OS 事件（macOS FSEvents / Linux inotify / Windows ReadDirectoryChanges）：

- Debounce window：2 秒（避免快速連續存檔重複觸發）
- 過濾範圍：只看 source 檔案（按副檔名）
- 行為描述：「**Incremental sync. The graph stays current as you code — no configuration needed**」

這層比 [cbm]({{< relref "mcp-codebase-memory-deep-dive.md" >}}) 的「背景 git polling」更貼近 IDE — 改完檔案 2 秒內 graph 就同步好，「邊改邊問」工作流更順。

判讀訊號：剛存完檔立刻問 caller 還是漏，等 3 秒再試一次；持續漏的話跑 `codegraph status` 看 indexed 數字對不對得上預期。

## Call graph 抽取的能力與聲稱

codegraph 對 caller / callee / impact / trace 這四個查詢的覆蓋是它的主賣點。README 對 `codegraph_trace` 的聲稱是：

> Follow dynamic-dispatch hops (callbacks, React re-render, interface→impl) that grep can't.

實際機制 README 沒詳細寫，從 source 推測是「**對某些常見動態 dispatch pattern 寫了專屬 query**」——比如 React component 的 JSX → component definition 解析、interface method → implementation 對應這類。

這個 claim 在實測上**有但有限**——對 type-inferred receiver 仍會漏。例如 Dart 上（`Money` 在該專案是 extension type）：

```dart
final Money samplePrice = ...;
samplePrice.multiplyByRate(rate);   // ← codegraph 抽不到這條 edge
```

`samplePrice` 是 local variable，要做型別推斷才知道 receiver 是 `Money`。tree-sitter 看到的只是 `<identifier>.multiplyByRate(...)`、不知道 `samplePrice` 的型別、無法 dispatch 到 `Money.multiplyByRate`。

判讀訊號：**對「靠型別解析才能找到的 callsite」會漏**。如果專案大量使用 generics、type aliasing、factory pattern 隱藏型別、duck typing，codegraph 的 caller 數字會系統性偏低。重要 refactor 別只看它的數字決策。

下一步路由：實測對照數字見 [三 MCP 工作流與 Dart 實測]({{< relref "mcp-three-way-workflow-and-dart-experiment.md" >}})。

## Caller 跟 callsite 的計數單位差異

codegraph 的 `codegraph_callers` 回的是「**caller symbol 數**」、不是「callsite 數」。同一個 method 內呼叫目標兩次仍然只算 1 個 caller。

這個設計的影響：跟 LSP-based 工具（如 [serena]({{< relref "mcp-serena-deep-dive.md" >}})）對比時，數字會看起來「少」，但這是計數規則差異而非精度差異。寫實測 baseline 時要把這個單位寫死，避免「codegraph 回 3、serena 回 9」被誤判成「codegraph 漏 6 個」。

實際上這 3 vs 9 的差距要分兩段看：codegraph 抓到的 3 個 caller symbol 對應 6 個 callsite（同一個 method 內有多處呼叫、被計數規則合併成 1 caller）、剩下的 3 個 callsite 在第 4 個檔案（`product.dart`）、是真的漏（type-inferred dispatch）。算術：6 callsite（codegraph 算 3 caller）+ 3 callsite（真的漏）= serena 的 9。要拆開看才知道哪部分是計數差異、哪部分是能力差距。

## 14 web framework 的 route 識別

codegraph 內建對 web framework 的 route 識別：

Django、Flask、FastAPI、Express、NestJS、Laravel、Drupal、Rails、Spring、Gin / chi / gorilla / mux、Axum / actix / Rocket、ASP.NET、Vapor、React Router、SvelteKit。

README 標稱「14 個」、實際展開後是 15 條（Gin / chi / gorilla / mux 跟 Axum / actix / Rocket 各算一組路由生態）。這個小落差源自分組計數方式、不影響功能。

這層的角色是讓 `codegraph_search` 能用 URL pattern 找到對應 handler，不必去猜 handler 函式名。但跟 [cbm]({{< relref "mcp-codebase-memory-deep-dive.md" >}}) 的 first-class HTTP_CALLS edge 不一樣，codegraph 沒做「client URL 字面值 → server route 比對」，所以**單一 service 內找 handler 可以、跨 service 鏈接做不到**。

判讀訊號：純前端 / 純後端 repo 上這層夠用；要跨 service 追 cross-service call 仍要靠 cbm 或別的工具。

## 10 個 MCP tool 的責任分工

| Tool                | 責任                                      |
| ------------------- | ----------------------------------------- |
| `codegraph_search`  | 用名稱 / pattern 找 symbol                |
| `codegraph_context` | 給定 task，組出相關 code context          |
| `codegraph_trace`   | 兩個 symbol 之間的 call path、每跳含 body |
| `codegraph_callers` | 找誰呼叫了 X（一跳）                      |
| `codegraph_callees` | 找 X 呼叫了誰（一跳）                     |
| `codegraph_impact`  | 改 X 會影響什麼（blast radius）           |
| `codegraph_node`    | 取 symbol 詳情 + 原始碼                   |
| `codegraph_explore` | 一次回多個相關 symbol 的原始碼            |
| `codegraph_files`   | 已索引的檔案結構                          |
| `codegraph_status`  | 索引健康度跟統計                          |

設計上有四個值得單獨展開的 tool：

**`codegraph_explore`** 是為了**省 tool call** — 不用對 N 個 symbol 各呼叫一次 `codegraph_node`、一次拿到所有 source。這直接呼應 codegraph 整體「省 token / 省 tool call」的設計目標。

**`codegraph_trace`** **單一 call 涵蓋整個路徑**、每一跳的 function body 直接 inline 在結果裡。對「X 怎麼影響到 Y」這種多跳問題，傳統做法要 N 次 `codegraph_callers` + N 次 `codegraph_node`，trace 把這壓成 1 次。代價是若兩個 symbol 之間沒有 static-resolvable 路徑（如 type-inferred dispatch 中斷），會直接回「No direct path」、不會主動找替代解釋。

**`codegraph_context`** 跟 `codegraph_explore` 的責任差別常被搞混。`codegraph_explore` 是「我已經知道要看哪幾個 symbol」、一次拿原始碼；`codegraph_context` 是「我有個 task description、不知道相關 symbol 是哪些」、由它從 task 內容拉出可能相關的 graph 鄰域。前者是「精確檢索」、後者是「概念性彙整」。實務上 task agent 開新任務時用 `codegraph_context`、debug 細節時用 `codegraph_explore`。

**`codegraph_impact`** 是 blast radius 工具、但**它的精度被 tree-sitter syntactic 限制卡住**——跟 caller / callee 同源、type-inferred dispatch 的影響範圍會漏。實務影響：對「rename method 會影響什麼」這類重要 refactor 不能單看它的數字、要走 LSP 工具 cross-check。判讀訊號：`codegraph_impact X` 回的 affected symbol 數明顯少於預期、且 X 是被廣泛使用的 type / method 時、blast radius 多半有漏、要補 LSP 驗證。

## Token efficiency benchmark：方法論與限制

README 聲稱「**~35% cheaper · ~70% fewer tool calls · 100% local**」、median 跨 7 codebase：

- Cost: 35% reduction
- Tokens: 57% fewer
- Time: 46% faster
- Tool calls: 71% fewer

方法論：

> Claude Opus 4.7 run headlessly. WITH = CodeGraph's MCP server enabled, WITHOUT = empty MCP config. Same question per repo, 4 runs per arm, median reported.

7 個 benchmark codebase：

| Repo       | 語言       | 規模    |
| ---------- | ---------- | ------- |
| VS Code    | TypeScript | ~10k 檔 |
| Excalidraw | TypeScript | ~640 檔 |
| Django     | Python     | ~3k 檔  |
| Tokio      | Rust       | ~790 檔 |
| OkHttp     | Java       | ~645 檔 |
| Gin        | Go         | ~110 檔 |
| Alamofire  | Swift      | ~110 檔 |

幾個要注意的解讀偏差：

**Benchmark 集中在 codegraph 強項語言**。VS Code / Django / Tokio 都是 codegraph 的核心支援語言、且 LSP 生態成熟。Dart / Svelte / Liquid 這類 long-tail 語言沒列在 benchmark 內，token 節省效果在那些語言上是否成立不知道。

**Empty MCP config 的對照組不一定貼近實務**。沒裝任何 MCP 時 agent 的 baseline 探索行為跟「裝了其他 MCP」不同。實務 stack 通常多個 MCP 並用，這個 35% 對「加裝 codegraph 進已有 MCP stack」的邊際效益會打折。

判讀訊號：benchmark 數字當「值得試」的參考、不當「裝了就省 35%」的硬保證。實際省多少要在自己的 stack 上跑同樣 question set 才知。

## 安裝行為

```bash
npm i -g @colbymchenry/codegraph
codegraph install --target claude --location global -y
cd your-project && codegraph init -i
```

`codegraph install` 會把 MCP server 條目寫進 `~/.claude.json` 的 `mcpServers`、`codegraph init -i` 在當前 repo 建 `.codegraph/codegraph.db`、啟動 watcher。

跟 [cbm]({{< relref "mcp-codebase-memory-deep-dive.md" >}}) 不一樣：codegraph **不寫 PreToolUse hook**、不攔截 Grep/Glob。它純粹當 MCP server 提供 tool、決策權留給 agent，對既有工作流的干擾較小。

CLI mode 是另一個方便點：所有 MCP tool 在 CLI 都有對應指令（`codegraph callers X` / `codegraph trace X Y`），不必等 Claude Code 重啟載入 MCP 就能先在 terminal 驗證效果。

## 適用 / 不適用情境的判讀

**適用情境**：

- 主力語言在 19+ 支援列表內，且需要可靠的 caller / impact / trace 查詢
- 「邊改邊問」工作流（auto-sync 2s debounce 比較貼近 IDE）
- 希望 MCP 保持原生 grep / glob 行為、把決策權留給 agent 而非 hook 攔截
- 要 CLI 跟 MCP 雙管道使用（CLI 可先試、MCP 給 agent 用）

**不適用情境**：

- 語言不在支援列表（codegraph 不像 cbm 一次 vendor 155 個 grammar）
- 需要跨 service 的 client URL → server route 鏈接（codegraph 只認 route definition）
- 需要 symbol-level atomic edit（codegraph 純讀、沒 rename / replace_symbol_body）
- 重要 refactor 要保證不漏 callsite（tree-sitter syntactic 上限會漏 type-inferred dispatch）

**搭配建議**：對 type-inferred dispatch 漏的部分，可以靠 LSP-based 工具（如 [serena]({{< relref "mcp-serena-deep-dive.md" >}})）補位。對概念性自然語言搜尋，[cbm]({{< relref "mcp-codebase-memory-deep-dive.md" >}}) 的 11-signal scoring 比 codegraph 的 symbol pattern match 更強。三者怎麼分工見 [三 MCP 工作流與 Dart 實測]({{< relref "mcp-three-way-workflow-and-dart-experiment.md" >}})。

## 結論

codegraph 的核心價值是**用 per-language tree-sitter query 把 call graph 做成 19+ 語言通用的 MCP 服務**，加上 auto-sync 跟 CLI 雙管道。它的 scope 聚焦在 call graph、比 cbm 窄很多、但聚焦範圍內品質很高。

它的型別解析靠 tree-sitter syntactic：**receiver 是顯式型別宣告或 literal 的 callsite 解得好、receiver 要靠型別推斷的 callsite 會漏**。判斷 codegraph 在自己專案上的可信度，先估專案有多少比例的 call 是 type-inferred receiver——比例高就要配 LSP 工具補位、比例低就放心用。
