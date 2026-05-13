---
title: "4.8 Multi-Agent 拓樸：flat / hierarchical / agent-as-tool"
date: 2026-05-14
description: "從 multi-call workflow 走到 multi-agent system 的判讀、flat vs hierarchical 拓樸、agent-as-tool 的 MCP 視角、specialization 跟 orchestration overhead 的取捨"
tags: ["llm", "applications", "agent", "multi-agent", "architecture"]
weight: 8
---

[4.7 workflow patterns](/llm/04-applications/workflow-patterns/) 寫的是「多次 LLM call 怎麼組合」、四個基本模式（pipeline / router / parallel / [reflection](/llm/knowledge-cards/reflection/)）解的是 single-thread 多 call 問題。當問題進一步複雜——需要平行的多個專業化角色、需要跨產品的 [agent](/llm/knowledge-cards/agent/) 重用、需要 agent 之間互相呼叫——就進入 [multi-agent system](/llm/knowledge-cards/multi-agent-system/) 的領域。

本章寫的是 multi-agent 系統的**拓樸結構**：何時值得從多 call 走到多 agent、flat 跟 hierarchical 兩種拓樸的差異、agent-as-tool 的 MCP 視角、specialization 跟 orchestration overhead 的核心 trade-off。具體 framework（CrewAI、AutoGen、LangGraph 多 agent 等）半年一個世代、本章不寫具體 API。

## 本章目標

讀完本章後你能：

1. 判斷一個系統該停在 multi-call workflow 還是進入 multi-agent。
2. 區分 flat / hierarchical / agent-as-tool 三種拓樸、各自的適用場景。
3. 估算 specialization gain vs orchestration overhead 的 trade-off。
4. 識別 multi-agent 特有的失敗模式（循環依賴、責任歸屬模糊、context 重複傳遞）。
5. 把 agent-as-tool 對應回 MCP / function calling 的協議設計。

## 從 Multi-Call 走到 Multi-Agent 的判讀

Multi-agent 跟 multi-call 不是「agent 數量多寡」的差別、是控制流跟責任邊界的差別。

| 維度       | Multi-call workflow                     | Multi-agent system                          |
| ---------- | --------------------------------------- | ------------------------------------------- |
| 控制流     | 主程式編排、每 call 是 step             | Agent 自己決定下一步、可能呼叫其他 agent    |
| 角色       | Step 跟 step 之間沒有「身份」、就是函數 | 每個 agent 有 role / 專業 / 工具集          |
| Context    | 主程式傳 context、step 不擁有 context   | Agent 自帶 memory、有「自己知道的事」       |
| 重用       | Step 是函數、容易 import 重用           | Agent 是黑盒、跨系統重用要透過協議          |
| 失敗歸屬   | Step 失敗、主程式接               | Agent 失敗、可能 cascading 影響別的 agent   |

判讀「該走 multi-agent」的四條件（**任一不滿足、就留在 multi-call**）：

- **角色差異顯著**：不同 step 要不同 prompt / model / tool / memory。任一條件同質就退回 multi-call、硬拆成多 agent 只是換個名字、orchestration overhead 純增。
- **跨產品重用**：同一個 agent 要被多團隊 / 多場景使用。單一 user / 單一場景的話、寫成函數比 agent 簡單。
- **真正平行 / 動態協作**：多個 agent 各做自己的事最後合併、或哪些 agent 參與是 query-dependent。控制流可寫死、step 順序固定時、multi-call pipeline 已足夠。
- **團隊熟悉度足**：multi-agent 失敗模式比 multi-call 多、debug 比較難。團隊還在學階段、debug 容易性 > 靈活性、先 stick to multi-call。

「先 multi-call、不夠再 multi-agent」是合理預設姿勢。Multi-agent 是「特定問題的解法」、不是「更高級的設計」。對應 [4.4 agent 架構](/llm/04-applications/agent-architecture/) 的「先 single-call、不夠再 agent」反射、層級往上類似。

## 三種拓樸

Multi-agent 的拓樸結構決定 agent 之間怎麼通訊、誰決定誰做什麼。三種主流拓樸各有適用場景。

### Flat 拓樸：all-to-all

所有 agent 同層級、可以互相呼叫、沒有固定 orchestrator。

```text
       Agent A ─────── Agent B
         │  ╲          ╱  │
         │   ╲        ╱   │
         │    ╲      ╱    │
       Agent C ─────── Agent D
```

- **適用**：agent 之間平等、任務需要動態協商（agent A 想知道 X、問 B 跟 D、再決定）。
- **典型場景**：研究型多 agent debate、模擬多個利害關係人協商。
- **失敗模式**：
  - **N² 通訊複雜度**：agent 多了之後、通訊路徑潛在 N²、實務常較稀疏但難預測、cost / latency 上限不可控。
  - **無權威仲裁**：兩個 agent 意見衝突、沒有第三方決定、容易死鎖。
  - **責任歸屬模糊**：最終結果是誰決定的不清楚、debug 困難。
- **規模限制**：實務上 flat 拓樸超過 5–6 個 agent 就難維護、不推薦大規模。

### Hierarchical 拓樸：orchestrator + specialists

一個 orchestrator agent 對外、底下若干 specialist agent、orchestrator 決定 dispatch 給誰、合併結果回 user。

```text
              User
                │
          ┌─────────────┐
          │ Orchestrator │
          └──┬──┬──┬──┬─┘
             │  │  │  │
        ┌────┘  │  │  └────┐
   Specialist  │  │   Specialist
       A    Spec  Spec      D
             B    C
```

- **適用**：對 user 要單一介面、底下 agent 專業化、orchestrator 知道每個 specialist 的 capability。
- **典型場景**：智慧家庭中央控制（user 對 orchestrator 說話、orchestrator 派給 climate / security / energy agent）、複雜客服系統（orchestrator 派給 product / refund / billing 不同 specialist）。
- **失敗模式**：
  - **Orchestrator 變單點瓶頸**：所有請求過 orchestrator、它的 prompt / model 限制整個系統能力。
  - **Specialist 之間訊息傳遞要過 orchestrator**：增加 latency、容易丟細節。
  - **Orchestrator 不知道何時該派誰**：需要動態描述 specialist capability、複雜 query 容易 dispatch 錯。
- **變體**：multi-level hierarchy（orchestrator 下面還有 sub-orchestrator），實務上 2 層夠用、3 層以上 overhead 大於 specialization gain。

### Agent-as-Tool：agent 互通就是 tool call

把每個 agent 包成「另一個 agent 的 tool」、agent A 呼叫 agent B 跟呼叫 weather API 在介面上一樣——都是 tool call。

```text
Agent A
  ├── tool: weather_api
  ├── tool: database_query
  └── tool: agent_B  ←── 內部其實是另一個 agent loop
                            └── 它也有自己的 tools
                                ├── tool: code_executor
                                └── tool: agent_C
```

- **適用**：agent 之間有清楚的「誰呼叫誰」、不是平等協商；想透過標準協議（function calling / MCP）讓 agent 跨系統重用。
- **典型場景**：[MCP](/llm/knowledge-cards/mcp/) 的 tool primitive 視角下、agent-as-tool 可以包成 MCP server 暴露、client agent 把它當 tool 用。跨組織 agent 互通常走這個模式。注意 MCP 還有 resources / prompts 另外兩類 primitive、不是所有 MCP server 都是 agent-as-tool。
- **跟 hierarchical 的關係**：agent-as-tool 是 hierarchical 的一個實作策略——orchestrator 把 specialist agent 當 tool。差異在於：hierarchical 可能是同進程內的緊耦合、agent-as-tool 走標準協議、跨進程 / 跨組織 / 可替換。
- **失敗模式**：
  - **協議的 schema 太薄**：agent 跟 agent 之間的 input/output 用 string 傳、丟結構資訊、下游難解析。
  - **Cascading failure**：下游 agent 失敗、上游 agent 不知道為什麼失敗、誤判繼續。
  - **重複 context 傳遞**：每次呼叫都要重新 brief 一次下游 agent、token cost 爆。緩解：下游 agent 自帶 session memory（見 [4.19 agent memory architecture](/llm/04-applications/agent-memory-architecture/)）。

### 三種拓樸的選擇

| 場景特性                              | 推薦拓樸             |
| ------------------------------------- | -------------------- |
| 2–4 個 agent、需要動態協商            | Flat                 |
| 多個專業 agent、單一對外介面          | Hierarchical         |
| 跨組織 / 跨進程 / 標準化重用          | Agent-as-tool        |
| 大規模（10+ agents）、固定協作模式    | Hierarchical 多層    |
| 想簡單開始                            | Hierarchical 兩層    |

教材建議的組合：對外是 hierarchical（單一 orchestrator）、orchestrator 內部跟 specialist 通訊走 agent-as-tool 協議（如 MCP tool primitive）、specialist 之間用 flat 模式平等溝通。實務上組合方式因團隊跟產品差異很大、這只是一個合理起點。

## Specialization Gain vs Orchestration Overhead

Multi-agent 的核心 trade-off 是**專業化收益跟協調成本的拉鋸**。

### Specialization gain：把 agent 拆細的好處

- **單一責任**：每個 agent prompt 短、focus 清楚、debugging 容易。
- **獨立優化**：每個 agent 可以用不同 model（具體 routing 思路屬於 [4.7 workflow patterns](/llm/04-applications/workflow-patterns/) router 模式）、不同 prompt、獨立 eval。
- **重用**：同一個 specialist 跨多個系統用、攤平訓練 / 設計成本。
- **平行**：獨立 agent 可平行跑、latency 降。

### Orchestration overhead：拆細的成本

- **Context 傳遞成本**：每個 agent 要被 brief、context 重複傳、token 累積。
- **Latency 累積**：每跳一個 agent 加一個 LLM call 的 latency、跨 agent chain 跟 reflection / multi-step retrieval 一樣會累積。
- **失敗模式多**：每個 agent 自己會 drift、agent 之間也會誤判、debug 比 single agent 難。
- **責任歸屬**：bug 出現時、定位是哪個 agent 跑偏要看完整 trace。

### 何時 specialization 划算

| 條件                                    | Specialization 划算？     |
| --------------------------------------- | ------------------------- |
| Agent 之間 role 差異顯著                | ✓                         |
| Agent 之間 role 同質                    | ✗                         |
| 重用機會多（多產品 / 多場景）           | ✓                         |
| 單一場景 / 單一團隊                     | ✗                         |
| 每個 sub-task 各自有客觀 eval           | ✓                         |
| Sub-task 無法獨立評估                   | ✗（debugging 困難）      |
| Latency 容忍度高（後台 batch）          | ✓                         |
| 即時 chatbot                            | ✗（orchestration latency 殺死 UX）|

兩個容易低估的條件展開：

- **「sub-task 無法獨立評估」為何讓 debugging 困難**：當 specialist agent 出問題、若沒有 component-level eval、要從 final output 倒推到「哪個 agent 跑偏」要看完整 trace + 人工讀。Single agent 失敗只需查一個 agent 的 trace、multi-agent 失敗要查 N 個、且 cascading failure 讓 root cause 模糊。要配 sub-task 客觀 eval（如 retrieval recall、抽取 accuracy）才能秒抓問題層、不然 specialization 換來的是更貴的 debug。
- **「orchestration latency 殺死 UX」的量級**：每跳一個 agent 加一個 LLM call（雲端旗艦 ~1-3s）。Hierarchical 三層、user query 到回應走 3+ 次 LLM、累積 3-10s。即時 chatbot 的 latency budget 通常 < 3s、multi-agent 容易超標。Workaround：specialist 換小 model、或某些 step 改 deterministic、或退回 single agent + multi-step prompt。

### 「先粗、再細」的演化路徑

實務多採演化路徑、不是一開始就設計多 agent：

1. **Single agent 開始**：把整個任務塞一個 agent、看跑得起來嗎。
2. **發現某子任務 systematic 失敗**：那個子任務拆出來、變成 specialist agent。
3. **更多子任務需要拆**：演化成 hierarchical。
4. **要跨產品重用**：把某個 specialist 包成 agent-as-tool（透過 MCP）。

這條路徑的好處是**每一步都有具體痛點驅動拆分**、不是「為了 multi-agent 而 multi-agent」。

## Multi-Agent 特有的失敗模式

除了單 agent 共通的失敗（context drift / goal drift / tool misread、見 [4.4](/llm/04-applications/agent-architecture/)）、multi-agent 系統有自己特有的失敗模式：

### 循環依賴

循環依賴是 agent 呼叫圖在執行期才形成 cycle、靜態 declaration 抓不出來、結果無限執行。例：Agent A 呼叫 B、B 呼叫 C、C 又呼叫 A、形成 cycle。

緩解：

- Call stack 監測、深度超過 N 強制中止。
- Agent 設計時明確 declare 它會呼叫哪些下游 agent、靜態 check 不出 cycle。
- Cycle 的合法用例（如 negotiation）要明確設停止條件。

### 責任歸屬模糊

責任歸屬模糊是 multi-agent 的 cascading 結構讓 final output 的「哪個 agent 出錯」可能跨多個 agent 累積、debug 時不知道從哪查。

緩解：

- 強制 trace 全部 agent call（見 [4.20 LLM tracing](/llm/04-applications/llm-tracing-and-observability/)）。
- 每個 agent 明確 declare 它對 final output 的貢獻範圍。
- Error 用結構化、明確標出 raised by 哪個 agent。

### Context 重複傳遞

Context 重複傳遞是 agent-as-tool 介面下、上游每次呼叫下游都要重新 brief 一遍、缺乏跨 call 的狀態保留、累積成 token cost 跟 latency 雙重浪費。

緩解：

- Specialist agent 自帶 session memory、不用每次 brief（見 [4.19 agent memory architecture](/llm/04-applications/agent-memory-architecture/)）。
- 共享 context（global state、reference passing）取代複製。
- Agent-as-tool 協議設計時、輸入 schema 包含「已 brief 過、跳過 intro」flag。

### Orchestrator 成為單點認知瓶頸

Orchestrator 是 hierarchical 拓樸的核心、要理解所有 specialist 跟分派邏輯、它的 prompt / capability 限制整個系統上限。換 specialist 容易（介面標準）、換 orchestrator 牽動所有 routing 邏輯（耦合深）。

緩解：

- Orchestrator 的 dispatch 邏輯外部化（不寫在 prompt 內、寫在 deterministic routing rule）。
- Specialist 自己 declare capability（用 OpenAPI / MCP schema）、orchestrator 動態讀、不寫死。

### Agent 之間互相 hallucinate

Agent 之間互相 hallucinate 是 agent 介面信任假設失效——上游 agent 給的 input 被視為「可信」、下游沒驗證就執行、hallucinated 內容沿著 agent chain 層層放大。

緩解：

- Agent 之間互通也要走 schema validation（見 [0.8 fuzzy engineering](/llm/00-foundations/deterministic-vs-fuzzy-engineering/) guardrail 段）。
- Critical path 加 deterministic check、不只靠 LLM 自評。

## 跟 MCP / Function Calling 的協議對應

[4.6 應用層協議](/llm/04-applications/application-protocols/) 寫 function calling / structured output / MCP 的層級差異。Multi-agent 拓樸的 agent-as-tool 模式直接對應 MCP：

```text
Agent-as-tool 在 MCP 視角下的展開：

Client Agent
  ├── MCP client
  │     ↓ stdio / SSE / HTTP
  │   MCP server #1 ← 包了一個 specialist agent
  │   MCP server #2 ← 包了另一個 specialist agent
  │   MCP server #3 ← 包了一個外部 service
  └── 對 client agent 來說、三者介面一致、都是 tool
```

這個 framing 的價值：**目前 agent 跨組織重用的主要工程問題是 agent-as-tool 協議普及度**——MCP 是當前的主流選項。當業界對協議 schema 達成共識（無論是 MCP 還是後續演化的標準）、agent-as-tool 拓樸的工程成本會大幅下降。

判讀訊號：自家 agent 想暴露給其他團隊用、預設選 MCP server 包裝、不要設計 proprietary protocol。

## 何時過時 / 何時不過時

**不會過時的部分**：

- Multi-call vs multi-agent 的判讀框架（控制流 / 角色 / context / 重用 / 失敗歸屬五維度）。
- Flat / hierarchical / agent-as-tool 三種拓樸的結構分類。
- Specialization gain vs orchestration overhead 的 trade-off。
- 「先粗、再細」的演化路徑反射。
- Multi-agent 特有的五類失敗模式跟緩解。
- Agent-as-tool 對應 MCP 的 framing。

**會變的部分**：

- 具體 multi-agent framework（CrewAI / AutoGen / LangGraph multi-agent 等會持續演化）。
- MCP server 生態的成熟度（普及度會大幅影響 agent-as-tool 的工程成本）。
- 各家 framework 對 multi-agent 失敗模式的 handling 工具（debugging / tracing tooling）。

## 小結

Multi-agent 不是「更高級的 agent」、是當 multi-call 不夠用時的下一層工具。三種拓樸（flat / hierarchical / agent-as-tool）各擋不同 trade-off、實務常組合使用。Specialization gain 跟 orchestration overhead 是核心 trade-off、「先粗再細」是合理演化路徑。Multi-agent 特有的失敗（循環依賴 / 責任歸屬 / context 重複 / orchestrator 瓶頸 / 互相 hallucinate）要對應的 guardrail 設計、不是預設就有。Agent-as-tool 直接對應 MCP、agent 跨組織重用就是 MCP 普及問題。

下一章：[4.9 Production 部署資源評估](/llm/04-applications/production-resource-planning/)、把多 LLM call / 多 agent 系統的 cost / latency / capacity 落到具體 production 評估。Multi-agent 跟 multi-call 的對比基礎見 [4.7 workflow patterns](/llm/04-applications/workflow-patterns/)、agent 自身的失敗模式見 [4.4 agent 架構](/llm/04-applications/agent-architecture/)、MCP 協議層討論見 [4.6 應用層協議](/llm/04-applications/application-protocols/)。
