---
title: "Case Study：customer support agent 從 task decomposition 到 eval"
date: 2026-05-14
description: "把模組四原理串成端到端案例：observe → decompose → design workflow → instrument trace → design eval → iterate。每段標出引用哪章。"
tags: ["llm", "applications", "hands-on", "case-study", "agent", "evals"]
weight: 1
---

本案例的責任是把模組四前面所有原理章節串成一個端到端的設計過程、示範**遇到實際 LLM 應用任務時、設計反射動作的順序**。每段都標出引用哪章原理、讓讀者看到 principle 章節怎麼落到具體工作。

用作走查的任務：PM 交派「做一個 customer support agent、能處理用戶查詢、必要時自動完成操作（如改地址）。」本案例聚焦「改地址」這個高頻 query type 走完整流程。

## 本案例的設計反射

整個流程分七階段：

1. **觀察人類工作流**：訪談、決定 task decomposition
2. **典範定位**：哪段該 deterministic、哪段該 fuzzy
3. **工作流設計**：每個 step 選對應的 LLM / tool / RAG / HITL 形態
4. **協議跟自主度決定**：是 single agent / multi-call / multi-agent
5. **Trace instrumentation**：哪些資訊要記
6. **Eval 設計**：先選座標、再選工具
7. **Iteration loop**：error analysis → 修哪一層 → 看 metric 收斂

初次設計 LLM 應用時最常省略階段 1、2、5、6、直接跳到階段 3 開始寫 prompt——這條路會走進「prompt 改了 20 版、無法判讀有沒有變好」的迭代無收斂。本案例強調的是設計反射動作的順序、不是寫 prompt 技巧。

## 階段 1：觀察人類工作流

PM 給的任務描述是「處理用戶查詢」、但「查詢」涵蓋的範圍可能很大。第一個反射動作是**坐在客服旁邊觀察兩天**、不是打開 IDE。

實際做的事：

- 統計收到的 query 類型分佈（退款 / 改地址 / 查詢訂單狀態 / 抱怨 / 開放問題各佔多少）。
- 看每類 query 的 human resolution 流程（哪幾步、要查哪些系統、要遵守哪些 policy）。
- 看哪幾類 query 是 high volume + low complexity（最值得自動化）、哪幾類是 low volume + high complexity（自動化 ROI 差）。
- 記下 human 在哪些 step 卡住、哪些 step 反覆需要查同樣資料。

訪談結束、你得到一張 task decomposition map。本案例假設聚焦在「用戶請求改地址」這個高頻 query type：

```text
User: 「我搬家了、訂單編號 #12345、新地址是 ___」
   ↓
1. 解析意圖 + 抽取訊息（訂單編號、新地址）
2. 查訂單狀態（已出貨？未出貨？已送達？）
3. 查 policy（這個訂單狀態 + user tier 能不能改地址？）
4. 若可：執行改地址（呼叫物流 / 庫存 API）
5. 若不可：解釋為什麼、給替代方案
6. 草擬回覆 email、發出
```

引用原理：這個 decomposition 本身對應 [0.8 fuzzy engineering](/llm/00-foundations/deterministic-vs-fuzzy-engineering/)（[deterministic-vs-fuzzy](/llm/knowledge-cards/deterministic-vs-fuzzy/) 卡）的「先分解任務、再判讀每段該 deterministic 還是 fuzzy」。

## 階段 2：典範定位

對每個 step 做典範定位（deterministic / fuzzy）：

| Step                   | 典範                                 | 為什麼                                          |
| ---------------------- | ------------------------------------ | ----------------------------------------------- |
| 1. 解析意圖 + 抽取訊息 | Fuzzy                                | 自由文字 input、需要 LLM 理解                   |
| 2. 查訂單狀態          | Deterministic                        | 結構化 query（給 order_id、回 status）          |
| 3. 查 policy           | Deterministic                        | 規則可窮舉、policy as code                      |
| 4. 執行改地址          | Deterministic                        | API call、有 schema 跟錯誤碼                    |
| 5. 解釋 / 給替代方案   | Fuzzy                                | 要寫人話、要 tailored to 情境                   |
| 6. 草擬 email + 發出   | Fuzzy（草擬）+ Deterministic（發送） | 寫 email 是 fuzzy、發 API call 是 deterministic |

判讀的重點是**邊界各歸各位**：規則跟政策走 code、人話跟意圖解析走 LLM。

- Policy check 寫成 code（如「user tier + 訂單狀態 → 能否改地址」是 deterministic 規則）。對應反例：把規則塞進 prompt 讓 LLM 判斷、會偶爾跳過規則或誤判 tier。
- 「能不能做」這類 yes/no 走規則。對應反例：用 LLM 算判斷、debug 困難且非確定性。
- 「Helpful 的回覆」走 LLM 寫。對應反例：在 code 內 hard-code 模板、變成僵化的客服機器人腔。

最容易混的邊界在 step 6：「草擬 email」是 fuzzy（要寫人話、tailor to 情境）、「發送 email」是 deterministic（呼叫 API、處理錯誤碼）。把這兩件事拆開、草擬可以 retry / 改 prompt 不影響發送邏輯、發送有結構化 error 不被 LLM hallucinate 蓋過。Step 4「執行改地址」也類似：tool call 本身 deterministic、但是否該 call 的判讀回到 step 3 的 policy check。

引用原理：[0.8 fuzzy engineering](/llm/00-foundations/deterministic-vs-fuzzy-engineering/) 的「哪段該 deterministic / 哪段該 fuzzy」決策框架、特別是反模式「邊界用錯」段。

## 階段 3：工作流設計

對每個 step 選對應的工具：

| Step                   | 設計選擇                                                                                         |
| ---------------------- | ------------------------------------------------------------------------------------------------ |
| 1. 解析意圖 + 抽取訊息 | Vanilla LLM call + structured output（output 強制 JSON schema：intent / order_id / new_address） |
| 2. 查訂單狀態          | Tool call → 內部 order API                                                                       |
| 3. 查 policy           | Tool call → policy engine（純 deterministic、不過 LLM）                                          |
| 4. 執行改地址          | Tool call → logistics API、寫操作前要 pre-act HITL（高風險 + 不可逆）                            |
| 5. 解釋 / 給替代方案   | LLM call + few-shot（從 case 庫 retrieve「類似情境怎麼解釋」、配 RAG）                           |
| 6. 草擬 email + 發出   | LLM call 寫 email + structured output 含 subject/body、發送透過 email API                        |

兩個容易選錯的 step 展開：

**Step 1 為何要 structured output、不是純 prompt 解析**：抽取結果要餵 step 2-4 的 deterministic tool、order_id 抽錯就整個流程斷。純 prompt 描述「請輸出 JSON」是弱保證、structured output / constrained decoding 是強保證（見 [3.10 constrained decoding 內部](/llm/03-theoretical-foundations/constrained-decoding-internals/)）。Trade-off：強格式可能犧牲表達彈性、但這個 step 不需要彈性、要的是可靠。

**Step 5 為何配 RAG 而非純 few-shot**：客服 case 涵蓋多種情境（訂單已出貨 / 已送達 / VIP / 一般 user / 不同國家 policy）、固定 few-shot 範例 cover 不全。RAG 從歷史 case 庫即時 retrieve 最相似的解釋範例、屬於 [4.0 prompt 技術光譜](/llm/04-applications/prompt-techniques-landscape/) context 軸的 retrieval-augmented prompting。

引用原理：

- Step 1 的 structured output → [4.6 應用層協議](/llm/04-applications/application-protocols/)
- Step 2-4 的 tool 設計 → [4.3 tool use](/llm/04-applications/tool-use-principles/)
- Step 4 的 pre-act HITL → [4.5 人機協作拓樸](/llm/04-applications/human-ai-collaboration/) pre-act 段。對比講座 Workera appeal 是 post-hoc、本案例選 pre-act 是因為改地址不可逆 + 物流影響大、必須在執行前審
- Step 5 的 RAG → [4.1 RAG 原理](/llm/04-applications/rag-principles/) + [4.0 prompt 技術光譜](/llm/04-applications/prompt-techniques-landscape/) context 軸

## 階段 4：協議跟自主度決定

這個工作流的控制流是線性的（1→2→3→4→5→6）、有條件分支（step 3 結果決定走 4 還是 5）、但每步順序固定。判讀：

**該用什麼結構**：

- ❌ Multi-agent：步驟順序固定、角色差異不大、orchestration overhead 純增。
- ❌ Single agent loop（model 自決下一步）：本案例假設 single-turn / 短多 turn、步驟順序明確、不需要 agent 自決。若 user 互動多輪 + turn 數不固定（如 user 中途補資訊、改主意、追問）、可考慮 agent loop。
- ✓ Multi-call pipeline + router：寫成 deterministic pipeline、step 3 後有 router 分流。

引用原理：

- [4.8 multi-agent 拓樸](/llm/04-applications/multi-agent-topology/) 的「先 multi-call、不夠再 multi-agent」反射
- [4.7 workflow patterns](/llm/04-applications/workflow-patterns/) 的 pipeline + router 模式
- [4.4 agent 架構](/llm/04-applications/agent-architecture/) 的「先 single-call、不夠再 agent」反射

**自主度**：

- Step 1（parse）、5（解釋）、6（草擬 email）：full auto。
- Step 2、3（查訂單、查 policy）：full auto（read-only）。
- Step 4（執行改地址）：pre-act HITL（高風險 + 不可逆）、有 diff show、user 可以 reject。
- Step 6（發 email）：可選 pre-act HITL（看公司風格、保守版要審 email、激進版自動發）。

## 階段 5：Trace Instrumentation

工作流上線前、先設計要記哪些資訊。**Eval 跟 debug 都靠 trace、沒 trace 後面什麼都做不了**。

每個 step 要記：

| 欄位                | 為什麼                         |
| ------------------- | ------------------------------ |
| Input（完整）       | Debug 時要重現                 |
| Output（完整）      | 比對預期、做 regression set    |
| Latency             | 找 bottleneck                  |
| Token cost          | 算成本                         |
| Step name + version | 追蹤是哪個版本的 prompt / tool |
| Decision branch     | Step 3 的 router 走哪邊        |
| Error（若有）       | 結構化 error、不是 string      |

整段 trace 要綁同一個 conversation_id、可以後面 join 起來看完整流程。

引用原理：[4.20 LLM tracing](/llm/04-applications/llm-tracing-and-observability/)。

## 階段 6：Eval 設計

先選座標、再選工具。對本案例的每個 eval 需求、用 [4.13 三軸座標](/llm/04-applications/eval-design-framework/) 定位。下面列的 threshold 數字（95%、80%、≥4 等）是 illustrative、實際數字隨產品 baseline、user 容忍度、業務代價而定、不是通用標準。

### Eval 1：Step 1 抽取準不準

- **三軸**：Objective（有 ground truth）+ Component（測單 step）+ Quantitative（accuracy）。
- **工具**：寫 100 個有標註的 query、跑 step 1、看 extraction accuracy（order_id 對 + new_address 對的比例）。
- **Threshold**：< 95% 不上線。

### Eval 2：Step 2-4 tool call 行為正確

- **三軸**：Objective + Component + Quantitative。
- **工具**：mock API、給 step 2-4 各 50 個 case、看 tool call 參數對不對、返回值處理對不對。
- **Threshold**：100%（這是 deterministic 行為、不該有錯）。

### Eval 3：Step 5 解釋品質

- **三軸**：Subjective（沒有單一正解）+ Component + Quantitative。
- **工具**：LLM-as-judge with rubric（clarity / helpfulness / tone）、scale 1-5、aggregate average。
- **Threshold**：average ≥ 4、no 1-2 比例 < 5%。

### Eval 4：Step 6 email 品質

- **三軸**：Subjective + Component + Quantitative + 加 Qualitative human review。
- **工具**：LLM judge 給分 + 每週抽 20 封 human review、看是否有 hallucinate 承諾、是否符合公司 tone。
- **Threshold**：judge 平均 ≥ 4、human review 沒有 critical issue。

### Eval 5：E2E success rate

- **三軸**：Objective + End-to-end + Quantitative。
- **工具**：跑 200 個 representative case、看「完整完成 + user 沒申訴」的比例。
- **Threshold**：≥ 85% baseline、降到 < 80% alert。

### Eval 6：User 滿意度

- **三軸**：Subjective + End-to-end + Quantitative。
- **工具**：每次互動結束顯示 thumbs up/down + optional 留言、追蹤 weekly。
- **Threshold**：thumbs up rate > 80%、appeal rate < 5%。

### Eval 7：Failure mode pattern（持續做）

- **三軸**：Objective / Subjective + End-to-end + Qualitative。
- **工具**：每週讀 50 個 sampled traces + 100% 讀 failure / appeal traces、找 emerging pattern。
- **產出**：bug ticket、prompt 修改 hypothesis、policy 補強 hypothesis。

引用原理：

- 三軸座標 → [4.13 eval design framework](/llm/04-applications/eval-design-framework/)
- LLM judge rubric → [4.21 LLM-as-Judge](/llm/04-applications/llm-as-judge/)
- Trace 接 eval → [4.20 LLM tracing](/llm/04-applications/llm-tracing-and-observability/)

## 階段 7：Iteration Loop

上線後、不是「等出問題」、是**持續 iteration**。典型 iteration cycle：

```text
Production trace + eval result
   ↓
[Error analysis：找 emerging pattern]
   ↓
   Hypothesis：哪一層有問題？
   ├── Prompt 層 → 改 prompt → A/B test → 看 eval 收斂
   ├── Tool 層   → 改 tool / schema → 跑 component eval → 收斂
   ├── RAG 層    → 改 chunking / query rewriting → 跑 [retrieval recall](/llm/knowledge-cards/retrieval-recall/) → 收斂
   ├── Policy 層 → 改 deterministic rule → 跑 step 3 component eval → 收斂
   └── Model 層  → 換 model → 跑全 eval set → 收斂
   ↓
[改動進 production]
   ↓
[Frozen baseline 留著、新版本跟它比、漂移看得見]
```

判讀「該改哪一層」的反射：

| 失敗訊號                  | 該改的層                                 |
| ------------------------- | ---------------------------------------- |
| Step 1 抽錯訊息           | Prompt / structured output schema        |
| Tool call 參數錯          | Prompt 內 tool description / few-shot    |
| Tool 跑掛                 | Tool 實作（不是 LLM 問題）               |
| RAG retrieve 不到相關案例 | Chunking / embedding / query rewriting   |
| Policy judgment 錯        | Deterministic rule（不是 LLM 問題）      |
| Email tone 不對           | Prompt（role / few-shot）                |
| Email hallucinate 承諾    | Output validator（不只是 prompt）        |
| 整體 latency 太高         | 找 trace bottleneck、可能要 cache / 並行 |

引用原理：

- Prompt 跟 model 層的失敗診斷 → [4.0 prompt 技術光譜](/llm/04-applications/prompt-techniques-landscape/) systematic vs random error
- 整體 fuzzy / deterministic 邊界判讀 → [0.8](/llm/00-foundations/deterministic-vs-fuzzy-engineering/)

## 五個容易遺漏的設計反射

實務上常常省略這五個反射動作、走進無收斂迭代：

### 反射一：先觀察、再開 IDE

階段 1 的價值是把 task decomposition 跟真實人類工作流對齊。沒這層對齊、寫出來的 prompt 跟 tool 拆法跟 reality 偏離、三天後重做。階段 1 的兩天比階段 3 的兩週值得。對應反例：「我先寫個 prompt 試試」、跳過觀察直接寫 code。

### 反射二：Policy 寫成 code、LLM 只解析意圖

判斷類規則（user tier、訂單狀態、可否操作）走 deterministic code、LLM 只負責「user 想做什麼」這層意圖抽取。這條邊界讓 debug 容易、規則更新不用 prompt iteration。對應反例：「LLM、請判斷這個訂單能不能改地址、規則如下：...」——把判斷塞進 prompt、debug 困難、規則漂移無從追蹤。對應 [0.8](/llm/00-foundations/deterministic-vs-fuzzy-engineering/) 的「邊界用錯」反模式。

### 反射三：Trace 是 day-1 設計

從第一天就把 input / output / latency / token / step name / decision branch / error 進 trace、綁同一個 conversation_id。Eval 跟 debug 都靠 trace、沒 trace 後面什麼都做不了。對應反例：「先讓系統跑起來、之後再加 trace」——出 bug 時 debug 從零開始、production trace 不可回溯。

### 反射四：Deterministic 行為用 deterministic check

有 ground truth 的行為（抽取對不對、API 參數對不對、JSON schema 合不合）用 Python 函數驗證、判斷成本低、精度高。LLM judge 留給沒 ground truth 的 subjective 行為。對應反例：用 LLM judge 測「step 1 抽取對不對」——cost 翻倍、精度反而不如 deterministic check。對應 [4.13](/llm/04-applications/eval-design-framework/) 軸誤選一。

### 反射五：保留 frozen baseline

[Frozen baseline](/llm/knowledge-cards/frozen-baseline/) 是把某個特定 prompt + 特定 model 跑 production 一段時間後 freeze 起來、每次新版本都跟它比、漂移看得見。對應反例：每次只跟「上一版」比、半年後累積漂移完全不可見、「整體變好了沒」無從回答。

## 跟其他章節的對應總表

本案例每階段引用的原理章節彙整：

| 階段                                              | 引用章節                                                                                                                                                                                                     |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1. 觀察人類工作流                                 | [0.8 fuzzy engineering](/llm/00-foundations/deterministic-vs-fuzzy-engineering/)                                                                                                                             |
| 2. 典範定位                                       | [0.8 fuzzy engineering](/llm/00-foundations/deterministic-vs-fuzzy-engineering/)                                                                                                                             |
| 3. 工作流設計（prompt / tool / RAG / HITL）       | [4.0](/llm/04-applications/prompt-techniques-landscape/)、[4.1](/llm/04-applications/rag-principles/)、[4.3](/llm/04-applications/tool-use-principles/)、[4.5](/llm/04-applications/human-ai-collaboration/) |
| 4. 結構決定（multi-call vs agent vs multi-agent） | [4.4](/llm/04-applications/agent-architecture/)、[4.7](/llm/04-applications/workflow-patterns/)、[4.8](/llm/04-applications/multi-agent-topology/)                                                           |
| 5. Trace instrumentation                          | [4.20 LLM tracing](/llm/04-applications/llm-tracing-and-observability/)                                                                                                                                      |
| 6. Eval 設計                                      | [4.13 eval framework](/llm/04-applications/eval-design-framework/)、[4.14](/llm/04-applications/benchmarking-and-evaluation/)、[4.21](/llm/04-applications/llm-as-judge/)                                    |
| 7. Iteration loop                                 | [4.0 prompt 光譜](/llm/04-applications/prompt-techniques-landscape/) systematic vs random error 段                                                                                                           |

## 下一步

返回：[模組四首頁](/llm/04-applications/)、或回到 [hands-on 索引](/llm/04-applications/hands-on/)。
