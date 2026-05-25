---
title: "三 MCP 工作流與 Dart 實測：cbm / codegraph / serena 的職責分工與三刀流"
date: 2026-05-25
draft: false
description: "在同一個 Dart 商業專案上跑同一組 query，量化 codebase-memory-mcp / codegraph / serena 三個 code intelligence MCP 的能力差距，得到「不能互相取代、要互補使用」的三刀流結論。含 5 個實驗的 CLI baseline 跟 MCP 驗證對照。"
tags: ["MCP", "AI協作心得", "工具評估", "Claude Code", "Dart"]
---

## 為什麼需要對照、為什麼選 Dart

評估 code intelligence MCP 不能只看 README benchmark：每個工具的 benchmark 都選自己擅長的 codebase 跟語言，readme 數字只能參考、不能直接套到自家 stack。

這次選一個 Dart 商業專案做對照場域有兩個理由：

- Dart 是三個工具的「中間地帶」——[cbm]({{< relref "mcp-codebase-memory-deep-dive.md" >}}) 不在 hybrid resolution 名單、[codegraph]({{< relref "mcp-codegraph-deep-dive.md" >}}) 列為 full support、[serena]({{< relref "mcp-serena-deep-dive.md" >}}) 借 `dart analysis_server` 有完整 LSP。三條技術路線在同一語言上的能力差距會被最大化。
- Dart 大量用 extension type、generic、factory pattern，這些是 type-inferred dispatch 的高發場景，能逼出每個工具的真實精度差。

在 Go / TypeScript 上跑同樣對照，結論會反過來——cbm 的 hybrid resolution 在那裡會接近 LSP 精度，三刀流的必要性會降低。所以這篇結論限定「LSP 成熟但 cbm 不在 hybrid resolution 名單」的語言。

## 本質差異：tree-sitter syntactic vs LSP type-aware

三個工具在 Dart 上的能力差距，根源是兩條技術路線的本質落差：

**tree-sitter syntactic**：只看語法結構。看到 `a.b()` 知道有個 method call、不知道 `a` 是什麼型別、不知道 `b()` 連到哪個 declaration。對 receiver 是 literal 或顯式型別宣告的 callsite 可以解、對 local variable / parameter / 推斷型別的 callsite 會漏。

**LSP type-aware**：走 language server 內建的型別推斷引擎。跟 IDE 用同一套後端、能解出 `a` 的真實型別、再從 type declaration 找到對應的 method。所以 reference 是型別精確的。

cbm 的 hybrid type resolution（限 Go / C / C++ / TS / JS）是把 LSP 的型別解析算法 clean-room 重寫進 binary、所以那幾個語言上 cbm 等於有 LSP 級精度但沒 LSP 依賴。Dart 沒得到這個待遇，所以 cbm 在 Dart 上只剩純 syntactic 結構抽取。

判讀訊號：看一個工具對某語言的能力強弱，問「**它在這語言上做型別解析嗎？**」——做的話接近 LSP，不做的話只是個結構抽取器。

這個 framework 建立後、下節展開到 9 個維度的設計對照。

## 三個工具的設計差異對照

三個工具雖然都是「code intelligence MCP」，設計取向互補：

| 維度               | [cbm]({{< relref "mcp-codebase-memory-deep-dive.md" >}}) | [codegraph]({{< relref "mcp-codegraph-deep-dive.md" >}})     | [serena]({{< relref "mcp-serena-deep-dive.md" >}}) |
| ------------------ | -------------------------------------------------------- | ------------------------------------------------------------ | -------------------------------------------------- |
| 解析後端           | tree-sitter + 自寫 type resolver                         | tree-sitter + per-language query                             | LSP（per-language server）                         |
| 語言覆蓋           | 155（vendored grammar）                                  | 19+（每語言寫 query）                                        | 視 LSP 支援度（40+）                               |
| 持久化             | SQLite + WAL（可 zstd 匯出為 team artifact）             | SQLite + FTS5                                                | per-session、不持久化                              |
| Sync 機制          | 背景 git polling                                         | native OS file watcher 2s debounce                           | session warm-up                                    |
| Type resolution    | Go / C / C++ / TS / JS 有 hybrid、其他語言只有 syntactic | tree-sitter syntactic 為主、聲稱對部分 dynamic dispatch 有解 | 完整 LSP 型別解析                                  |
| 跨 service         | first-class HTTP_CALLS edge + channel                    | route definition 識別、不做 client URL → server route 比對   | 無                                                 |
| 概念性自然語言搜尋 | 11-signal scoring + camel split                          | symbol pattern match                                         | 無                                                 |
| Symbol-level 編輯  | 無（純讀）                                               | 無（純讀）                                                   | 完整（replace_symbol_body / rename）               |
| 編譯 diagnostic    | 無                                                       | 無                                                           | 有（`get_diagnostics_for_file`）                   |

這張表的判讀重點：**三者擅長的事不重疊**。cbm 強在「找東西」、codegraph 強在「日常 call graph + auto-sync」、serena 強在「型別精確 reference + 編輯出口」。

對照表的維度很多、但實務上踩到事故的多半集中在三個維度，把它們各自展開：

**Type resolution 決定 caller 數字的可信度**。Dart / Swift / Kotlin 這類「LSP 完整、但 cbm 沒 hybrid」的語言上、tree-sitter 工具回的 caller 數字是 lower bound、不是真實值。`samplePrice.multiplyByRate(...)` 這種 type-inferred receiver 是這層差距的主戰場。判讀訊號：對熱門 class 跑同一 query、若 tree-sitter 工具 caller 數比 LSP 工具低過半、type-inferred dispatch 在這語言是主流模式、tree-sitter 結果只能當 starting point。

**Sync 機制決定「邊改邊問」是否可用**。codegraph 的 native OS file watcher + 2s debounce 最貼近 IDE、cbm 的背景 git polling 有秒級至分級延遲、serena 的 session warm-up 是「啟動時等一次、之後即時」。事故型態：在 codegraph 改完檔案立刻問 caller 多半 OK、在 cbm 立刻問會拿到 stale graph。判讀訊號：問完 query 對結果存疑時、先檢查工具的 sync 狀態（cbm 跑 `index_status`、codegraph 跑 `codegraph_status`、serena 直接重 query）。

**持久化模式決定跨 session 的累積成本**。cbm / codegraph 寫 SQLite、跨 session 重用；serena per-session、每次 spawn LSP warm up。對「短任務反覆 ad-hoc 查詢」cbm / codegraph 邊際成本更低、對「會做 symbol-level edit 跟 diagnostic」serena 的 per-session warm up 是必要 cost。判讀訊號：第一次 query 慢、之後快——LSP indexing warm up、正常；每次 query 都慢——LSP 可能因記憶體不足重啟、需排查。

下面的實測是這張表在 Dart 上的數字驗證。

## Dart 實測對照：同題不同工具

實測環境：

```text
專案類型：Dart 商業專案（POS / 零售領域）
Branch：refactor/money-value-object
索引規模：
  cbm:        3,038 nodes,  6,355 edges（Dart 沒 CALLS edge）
  codegraph:  6,244 nodes, 12,223 edges（含 CALLS edge）
  serena:     per-session、無索引統計
```

cbm 跟 codegraph 的 nodes 約 2x、edges 約 2x，差異關鍵不在 nodes（cbm 缺 import / enum_member 等次要 node）、而在「**有沒有 CALLS edge**」——這直接決定 caller / impact 類查詢能不能用。

> **實測數字的適用範圍**：本節的所有 callsite / caller / impact 數字（含查詢 1-5）都是**單一 Dart 商業專案的內部 baseline**、不保證跨專案重現。Dart 上 type-inferred receiver 比例高的專案會放大三個工具的差距、比例低的專案會縮小差距。換到 Swift / Kotlin / Rust 等語言上、絕對數字會不同但「tree-sitter syntactic vs LSP type-aware」的差距方向通常一致。讀者要套用結論時、先在自家 repo 跑一遍同題對照、看自己的數字落差。

### 查詢 1：誰呼叫了 `Money.multiplyByRate`

| 工具      | 結果                                                           |
| --------- | -------------------------------------------------------------- |
| cbm       | 0（hybrid resolution 不含 Dart）                               |
| codegraph | 3 caller symbols（4 個檔案中漏 product.dart 的 3 個 callsite） |
| serena    | 4 個檔案、9 個 callsite                                        |

codegraph 漏掉的 3 個 callsite 共同特徵：

```dart
// lib/data/models/product/product.dart
final Money samplePrice = ...;
samplePrice.multiplyByRate(Decimal.parse('0.9'));
samplePrice.multiplyByRate(Decimal.parse('0.6'));
```

`samplePrice` 是 local variable、要型別推斷才知道是 `Money`。tree-sitter 看到的只是 `<identifier>.multiplyByRate(...)`、解不出 dispatch target。

serena 透過 `dart analysis_server` 拿到完整型別資訊、知道 `samplePrice` 宣告是 `Money`、能精確 dispatch。

### 查詢 2：誰呼叫了 `LocaleSymbolConfig.formatAmount`

| 工具      | 結果                             |
| --------- | -------------------------------- |
| cbm       | 0                                |
| codegraph | 30（`--limit 30`，預設 20 截斷） |
| serena    | 5 個檔案、21 個 callsite         |

這題 codegraph 跟 serena 的差距比較小——`formatAmount` 在很多地方是用顯式 receiver 呼叫（如 `LocaleSymbolConfig.cny.formatAmount(...)`），tree-sitter 對顯式 receiver 解得到。

兩邊數字的差異主因是 **caller symbol 數 vs callsite 數**的計數單位差：

- codegraph 算 caller symbol（一個 method 內呼叫幾次都算 1）
- serena 算 callsite

寫實測 baseline 時這個單位要寫死、否則 3 vs 9 看起來像精度差距、實際上一部分只是計數規則不同。

### 查詢 3：`Money` 符號的內部結構

| 工具      | 結果                                                             |
| --------- | ---------------------------------------------------------------- |
| cbm       | 只認得 File / Module、extension type 子結構抽不到                |
| codegraph | 認得 class 但 extension type 支援度未驗證                        |
| serena    | Namespace kind、3 個 Field、16 個 Method、3 個 Property 都附行號 |

Dart `extension type` 是相對新的特性、tree-sitter grammar 對它的支援深度不一。serena 走 LSP 直接拿到 `dart analysis_server` 對 extension type 的完整解析。

對需要「列出某 class / extension 所有 member」的場景、serena 是 Dart 上 LSP 級精度最可信的選項（其他 MCP 在 Dart extension type 上做不到完整 member 列舉）。

### 查詢 4：概念性搜尋「金額顯示」相關函式

對「我不知道精確名稱、只記得功能類別」這種 query：

| 名次 | cbm（11-signal scoring）             | codegraph_search                     |
| ---- | ------------------------------------ | ------------------------------------ |
| 1-4  | 4 個 `formatAmount` 實作（兩邊一致） | 4 個 `formatAmount` 實作（兩邊一致） |
| 5    | `externalDisplayMain`                | `displayCategories`                  |
| 6    | `connectExternalDisplay`             | `displayTags`                        |
| 7    | `_buildQuantityDisplay`              | `displayName`                        |
| 8    | `connectExternalDisplay`（另一個）   | `displayCover`                       |
| 9    | `getBalanceDisplay`                  | `displayName`（另一個）              |
| 10   | `_buildPriceDisplay`                 | `displayName`（另一個）              |

前 4 名兩邊都抓到核心 `formatAmount` 實作，第 5 名後分歧明顯：

- cbm 補進的 `getBalanceDisplay` / `_buildPriceDisplay` / `connectExternalDisplay` 都跟「金額顯示」概念相關（顯示金額 / 顯示餘額 / 外接顯示器）
- codegraph 補進的 `displayName` / `displayTags` 只是符號名含 "display" 子字串、跟金額無關

差異來源是 cbm 的 11-signal scoring + `cbm_camel_split` 對 camelCase 切詞做語意切分（`getMoneyField` → `get` + `money` + `field`）。codegraph 的 search 是 symbol pattern match、沒對自然語言 query 做語意處理。

這題的判讀很關鍵——**cbm 在「找東西」的角色不能被 codegraph 取代**。即使 codegraph 在 Dart 上有可用的 call graph、它的 search 仍然贏不了 cbm 的概念性 query。

### 查詢 5：`Money` 的 impact 範圍 / cross-symbol trace

| 工具      | 結果                                                      |
| --------- | --------------------------------------------------------- |
| cbm       | 無 impact 概念、回不出                                    |
| codegraph | 5 個 affected symbol、全在 MoneyFieldRenderer 一檔        |
| serena    | 走 `find_referencing_symbols` 跨 4 個檔案找完整 reference |

Money 是該專案大量使用的 value object、實際被使用的檔案橫跨 receipt_data 實作、settlement、cart_item、order_dto 等業務模組。codegraph 只回 1 個檔案 5 個 symbol、嚴重低估 blast radius。

漏掉的原因跟查詢 1 同源——`something.multiplyByRate(...)`、`Money` 在 factory 內被隱式構造這些都不在 tree-sitter 能解的範圍。MoneyFieldRenderer 之所以被抓到、是因為它的 field 顯式宣告為 `Money`，這是少數 tree-sitter syntactic 能抓的場合。

對 cross-symbol trace：

```text
codegraph_trace(from: "Money/multiplyByRate", to: "ProductSpecification")
→ "No direct path"、建議跳到 dynamic dispatch
```

graph 上根本沒這條 edge（漏掉的 product.dart 那 3 個 callsite 正是這條 trace 的關鍵跳）、所以 trace 直接失敗。

判讀訊號：**重要 refactor 不能單看 codegraph 的 impact 數字**。要走 serena `find_referencing_symbols` 二次確認；對 cbm 不在 hybrid resolution 名單的語言、blast radius 必須用 LSP 工具驗證。

## 三刀流工作流

實測結論：cbm / codegraph / serena 各有不可替代的角色，組合使用才是 Dart 主力專案的合理 stack。

```text
找東西（不知道精確名稱、概念性 query）
  → cbm search_graph(query="...")           ← 11-signal scoring 對概念性 query 最強

知道精確名稱、找 caller / callee
  → codegraph_callers / codegraph_callees   ← auto-sync 2s 反應最快
  ↓
  發現結果可能不完整（type-inferred dispatch 多的場合）
  → serena find_referencing_symbols         ← LSP 完整精度補位

重要 refactor 確認 blast radius
  → serena find_referencing_symbols         ← 不能單靠 codegraph_impact

符號層級的編輯
  → serena replace_symbol_body / rename     ← symbol-level atomic edit

跨 service HTTP/RPC 鏈接（若 monorepo 含 client + server）
  → cbm HTTP_CALLS edge                     ← 三個工具中只有 cbm 有這層
```

幾個關鍵的判讀原則：

**入口跟出口要分清楚**：cbm 是「廣度索引 + 模糊搜尋」的入口、拿到 qualified name 後轉給 serena 做精確查詢與編輯。codegraph 補在中間、做日常結構查詢。

**重要 refactor 必走 serena 補位**：codegraph 的 caller / impact 在 Dart 上系統性偏低、不能單看數字判斷影響範圍。決定 rename 或大幅修改 method 之前、用 serena 跑一次 `find_referencing_symbols` 對齊。

**Hook 不要打架**：cbm 會寫 PreToolUse hook 攔截 Grep / Glob / Read / Search（README 描述只擋前兩者、實裝版本含 Read / Search）、codegraph / serena 都不寫 hook。同時用三個工具時、注意 cbm hook 是否誤判把正常的 markdown grep 也擋掉（實測有 false positive）。

## 對其他語言 stack 怎麼變化

這個三刀流結論限定 Dart。不同語言 stack 的真實壓力不一樣、推薦組合也跟著變——把幾個常見 stack 各自展開。

### Go / TypeScript / C / C++ 主力

這層是 cbm 的甜蜜點：hybrid type resolution 涵蓋這四個語族、CALLS edge 抽得到、cbm 的 caller / blast radius 精度接近 LSP。實務影響是「cbm 在 Dart 上需要 codegraph + serena 補位」的場景大幅縮小——cbm 自己就能處理 caller / impact、加上它原本就強的 11-signal 概念搜尋跟跨 service HTTP_CALLS，等於一個工具撐住「找東西」「caller / impact」「cross-service」三層。

serena 在這個 stack 仍是 symbol-level edit 跟 compile diagnostic 的關鍵來源——cbm 純讀、沒 rename / replace_symbol_body、沒 LSP 診斷整合。所以合理組合是「cbm + serena 雙刀流」、codegraph 的角色被 cbm 取代掉。判讀訊號：在自家 repo 跑 cbm `trace_call_path` 對 5 個熱門 class、若 caller 數跟 serena 的 `find_referencing_symbols` 對得上、codegraph 確實可以省下。

### Swift / Kotlin / Rust 主力

這層跟 Dart 場景結構接近：serena 透過 sourcekit-lsp / kotlin-language-server / rust-analyzer 能拿到完整型別解析、cbm 不在 hybrid resolution 名單只剩純 syntactic。所以「三刀流」的論證仍適用。

但 codegraph 在這三個語言的 query 品質要實測——19+ 列表內這幾個都列為 supported、實際解析深度因語言成熟度而異。Swift 特別容易踩坑的點是 Objective-C interop（dispatch table 跨語言）跟 protocol extension 的型別推斷、Kotlin 則是 reified generics 跟 inline function、Rust 是 trait method 跟 macro 展開後的 callsite。判讀訊號：對自家專案最常用的 dispatch pattern 寫一個 minimal example、跑 codegraph callers、看抓不抓得到。

### Python 主力

三個工具的 Python 支援都成熟、但著力點不同：cbm 對 Python 有完整 hybrid resolution、codegraph 對 Python 是核心支援語言之一（VS Code benchmark 在它的 7 codebase 列表內）、serena 透過 pyright / pylsp 拿型別資訊。

Python 的特殊壓力是 dynamic dispatch（duck typing / monkey patching / metaclass / __getattr__）——這層任何 static 工具都會漏。判讀訊號：對自家 codebase 跑「找 X class 的所有 method 呼叫」、若大量真實 callsite 在 type annotation 缺失的位置、所有工具都只能給 lower bound。實務組合多半雙刀（codegraph + serena）夠用、cbm 對 Python 的不可替代價值在 cross-service HTTP_CALLS（Django / FastAPI 跨 service 場景）。

### 冷門語言 / DSL（Liquid / Pascal / Svelte template 等）

這層 serena 多半沒 LSP 可借（除非自備 server）、cbm 純 syntactic（hybrid 名單外）、codegraph 是少數仍有 query 的工具——但 query 品質要看 codegraph 對該語言投入多深、Pascal / Delphi / Liquid 這類列表末段的支援度可能只到 symbol 抽取、callsite 不一定有。

實務上對這層語言、退回 `grep + codegraph` 比強推三刀流合理——caller / impact 用 codegraph 試、不夠就 grep 補、別期待 LSP 級精度。判讀訊號：若 codegraph status 顯示 indexed file 多但 edges 數明顯偏低（< 1 條 edge per file）、call graph 多半沒抽起來、視同純 syntactic 工具用。

### 共通的評估方法

無論哪個 stack、第一次裝 MCP 前在自家 repo 跑「找重要 class / function 的所有 caller」這個基準題、把不同工具的數字並列比較、再決定組合。README benchmark 是行銷數字、自家 stack 跑出的數字才是真實 baseline。

## 評估新 MCP 工具的 checklist

從這次踩三個（含一個跳過實裝的 GitNexus）的經驗回推、未來評估新 code intelligence MCP 要先確認：

**License**：商業專案要 MIT / Apache 2.0 / BSD。PolyForm Noncommercial 之類限制商業使用的 license 直接刷掉。這條最便宜、最早做、最少人記得做。

**目標語言的 call graph 支援**：README 寫「full support」要實測。tree-sitter wrapper 通常只到「結構抽得到」、沒到「call edge 抽得到」。同樣是「有 CALLS edge」、有 type-inferred dispatch 的 syntactic 工具跟有完整 LSP 的差距可能 2-3x callsite 數。

**MCP tool 數量不等於能力**：14 個 tool 不一定贏過 10 個。看 caller / impact / find_referencing_symbols 這類核心功能有沒有、品質好不好、勝過 tool 多寡。

**是否會自動改 `~/.claude/` 設定**：大多會。先看 install script 動了哪些檔案、能不能還原、uninstall 是否徹底（cbm uninstall 不清 hook 是踩過的坑）。

**是否有 CLI 模式**：有的話本 session 就能實測、不必等 Claude Code 重啟載入 MCP。CLI mode 對「驗證 baseline」特別重要——拿 CLI 結果當 ground truth、再對 MCP 結果做差異比對。

**Auto-sync 機制**：file watcher / git polling / 純手動 reindex 差異很大。「邊改邊問」工作流對 sync 延遲很敏感、選錯會踩到 stale graph 的事故。

## 結論

對 Dart 主力專案：**三刀流（cbm + codegraph + serena）是合理 stack**。三者擅長的事不重疊、互相補位有明確角色：

- [cbm]({{< relref "mcp-codebase-memory-deep-dive.md" >}})：概念性搜尋入口、跨 service HTTP/RPC 鏈接
- [codegraph]({{< relref "mcp-codegraph-deep-dive.md" >}})：日常 80% 的結構查詢、auto-sync 反應最快
- [serena]({{< relref "mcp-serena-deep-dive.md" >}})：型別精確 reference、symbol-level atomic edit、編譯 diagnostic

對其他語言 stack、cbm 進入 hybrid resolution 名單後組合會收斂、但 serena 的 symbol edit 跟 diagnostic 角色仍不可取代。

評估方法的更普遍結論：**README benchmark 只是起點、要在自己的 stack 上跑同樣的基準題才算數**。每個工具的 benchmark 都選自己擅長的語言跟 codebase、跨語言遷移結論需要重新驗證。用 5 個查詢做 baseline、把 CLI 數字當 ground truth、再對 MCP 結果做差異對比、是現階段最低成本的工具評估法。
