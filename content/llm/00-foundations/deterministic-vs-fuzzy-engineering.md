---
title: "0.8 Deterministic vs Fuzzy Engineering：軟體設計典範的位移"
date: 2026-05-14
description: "傳統 deterministic 軟體跟 fuzzy LLM 軟體在資料、邏輯、分解、實驗成本四個維度的根本差異、以及哪段該 deterministic、哪段該 fuzzy 的決策框架"
tags: ["llm", "foundations", "paradigm", "architecture"]
weight: 8
---

LLM 進到軟體工程的最大影響、不是「多了一個 API 可以呼叫」、而是軟體設計典範本身的位移（見 [deterministic-vs-fuzzy](/llm/knowledge-cards/deterministic-vs-fuzzy/) 卡）。傳統軟體建立在 deterministic 假設上——同樣的 input 永遠對應同樣的 output、邏輯靠人類寫定、行為可以靠 test 鎖住。LLM 軟體則建立在 fuzzy 假設上——同樣的 input 在不同溫度、不同 sampling 下會給不同 output、邏輯是模型自己推、行為只能用統計方式驗證。

這個位移影響的不只是「在某段程式裡呼叫 LLM」、而是整套設計思維：怎麼處理資料、怎麼定義「正確」、怎麼分解任務、怎麼版本控制、怎麼測試、怎麼除錯。本章把這個典範位移寫成跨應用都成立的心智模型、讓你在後續模組（特別是 [模組四 LLM 應用層](/llm/04-applications/)）讀到 RAG、agent、workflow pattern 時、知道自己在跟哪個典範打交道、該套哪一邊的設計直覺。

## 本章目標

讀完本章後你能：

1. 區分一段程式碼是 deterministic 還是 fuzzy。
2. 列出兩個典範在四個維度（資料、邏輯、分解、實驗成本）的差異。
3. 判斷一個系統的哪段該 deterministic、哪段該 fuzzy。
4. 設計 fuzzy 邊界的 guardrail（schema / validator / HITL）。
5. 看到一個失敗案例、能定位是「典範用錯」還是「實作問題」。

## 兩個典範的對照

| 維度       | Deterministic 軟體                                | Fuzzy 軟體                                     |
| ---------- | ------------------------------------------------- | ---------------------------------------------- |
| 資料形狀   | 結構化（JSON、DB row、form 欄位）                 | 半結構化 / 非結構化（自由文字、圖像、音訊）    |
| 邏輯來源   | 人類寫死規則                                      | 模型推論、依 prompt + context 浮動             |
| 行為一致性 | 同 input → 同 output                              | 同 input → 分佈、需 sample 多次才看見平均行為  |
| 分解原則   | 按職責 / 模組（monolith / microservice）          | 按角色 / agent（manager 思維：誰負責什麼任務） |
| 測試方式   | unit test、integration test、覆蓋率               | eval、judge、distribution-level metric         |
| 除錯       | step debugger、log、stack trace                   | trace、prompt diff、token-level inspection     |
| 版本控制   | code diff 是行為差異的完整來源                    | code diff + prompt diff + model version 三者   |
| 實驗成本   | 高（改 code 要 review、可能影響穩定性）           | 低（改 prompt 即可、推翻重做便宜）             |
| 失敗模式   | crash、wrong value、type error                    | hallucination、tone drift、partial completion  |

這張表是後續所有判讀的骨架。看到一段程式時、用這幾個維度自問「這段在哪個典範」、設計直覺自然分開。

## 為什麼這個位移是典範級、不是只是換工具

很多人把 LLM 當「多了一個 API」、結果是把 LLM 塞進 deterministic 設計框架裡、然後因為它「不夠 deterministic」而 frustrated。這個 framing 錯了。LLM 不是 deterministic 工具的下一代、是另一條工具線、需要另一套設計直覺。

幾個容易踩的混淆：

- **把 LLM 行為當 bug 修**：模型輸出不穩定、想用更多 `if` 把它「夾」回固定行為。這條路會走到死巷——當 prompt 越夾越窄、模型反而開始失去原有能力。正確方向是讓邊界本身可以容忍變化（schema validation + retry、distribution metric、HITL）。
- **用 deterministic 的 test 思維測 LLM**：寫了一個「input X 應該得到 output Y」的單元測試、期望 byte-exact match。LLM 行為是分佈、即使 temperature=0、prompt brittleness 也讓單次測試結果不穩。Fuzzy 系統的測試是「在 N 次採樣中、output 落在期望範圍內的比例」、或「分佈級別 metric」、不是「精確等於某 string」。
- **用 deterministic 的 code review 審 LLM-generated code**：要求 generated code 完全符合 style guide、結果耗在 nitpick 而不是行為正確性。LLM 生成是 fuzzy 過程、review 焦點該是「功能對 + 安全 + 可讀」、style 交給 linter / formatter 後處理。

典範位移的真正意涵：**設計時就承認 fuzziness 存在、並圍繞它設計**、不是假裝它不存在。

## 哪段該 Deterministic、哪段該 Fuzzy

一個系統幾乎不會「全 deterministic」或「全 fuzzy」、實務上是混合。判讀「哪段該哪個」的決策框架：

| 屬性                 | 偏 deterministic                       | 偏 fuzzy                            |
| -------------------- | -------------------------------------- | ----------------------------------- |
| 行為定義             | 規則可窮舉                             | 規則太多 / 邊界模糊                 |
| 失敗代價             | 高（金錢、安全、不可逆）               | 低（可 retry、可 fallback）         |
| 解釋需求             | 必須能解釋為什麼做這個決定             | 解釋是 nice-to-have                 |
| 一致性需求           | 必須 byte-exact 重現（auditing、test） | 統計上一致即可                      |
| 資料形狀             | 結構化                                 | 自由文字 / 多模態                   |
| 變化頻率             | 規則穩定、長期不變                     | 需求 / 領域知識 / 用戶輸入快速變化  |
| 邊界條件             | 邊界清楚（valid / invalid 兩段式）     | 邊界連續（差不多好 / 還行 / 不夠好）|

實務上一個 production LLM 應用的常見組合：

- **使用者輸入解析**：偏 fuzzy（LLM 解意圖、parse 自由文字）。
- **資料庫查詢 / 更新**：偏 deterministic（SQL、API、schema validation）。
- **業務規則檢查**（如「能否退款」「能否變更地址」）：偏 deterministic（policy as code）。
- **回應草稿生成**：偏 fuzzy（LLM 寫 email、考慮語氣）。
- **發送 / 寫入動作**：偏 deterministic（API call、template render）。

這個混合不是隨機、是按上述決策框架推出來的。LLM 強在「理解模糊輸入」跟「生成有風格的輸出」、其餘部分能 deterministic 就 deterministic。

### 反模式：典範用錯的訊號

- **Deterministic 的需求硬用 fuzzy 解**：例如用 LLM 算稅金、然後用 retry + LLM judge 校驗。這條路的成本跟錯誤率都遠高於直接寫 deterministic 規則。判讀訊號：能用 30 行 code 寫死的規則、不要 LLM。
- **Fuzzy 的需求硬用 deterministic 解**：例如用 regex 解析自由文字客服訊息、然後維護一個越來越長的 case list。判讀訊號：規則 list 每週都在加新 case、加完還是漏、就該換 fuzzy。
- **邊界用錯**：把 deterministic 的部分塞進 prompt（如「請計算 9.32 × 47 並退款」）、或把 fuzzy 的部分塞進 code（如 `if user_intent == "refund"`）。前者讓 LLM 出算術錯、後者讓 code 漏 case。判讀訊號：prompt 在做算術 / 字串解析、或 code 在做意圖分類、就該重切。

## Fuzzy 邊界的 Guardrail 設計

承認 fuzziness 存在後、設計重點轉成「邊界要怎麼包」。Guardrail 是 deterministic 包 fuzzy 的設計模式、防止 fuzzy 行為溢出到不該影響的地方。

四種常見 guardrail：

### Schema validation

LLM 輸出被強制符合某個 schema（JSON schema、Pydantic model、TypeScript type）。不符合就 retry 或 fallback。

適用：LLM 結果要直接餵給下游 deterministic 系統（API、DB、UI）。

實作位置：LLM call 之後、下游 system 之前。

失敗模式：schema 對了但語意錯（structurally valid、semantically wrong）——這層 guardrail 接不住、要加 semantic check。

### Output validator

對 LLM 輸出跑語意驗證、不是只看 schema。例：生成的 email 不能包含未經授權的折扣承諾、生成的 code 不能呼叫 deprecated API。

適用：LLM 輸出有「該做 / 不該做」的清單。

實作位置：LLM call 之後、deliver 之前。可以是 deterministic check（regex、AST 分析）、可以是另一個 LLM judge（見 [4.21 LLM-as-Judge](/llm/04-applications/llm-as-judge/)）。

失敗模式：validator 自己 hallucinate（如果是 LLM judge）、或漏 case（如果是 deterministic check）。混用兩種比較穩。

### Action gating

LLM 想做高代價動作前、強制走人類確認或外部驗證。例：寫 production DB 前要 human approval、發 email 前要 dry-run 給內部 review、執行 shell 前要看到 diff。

適用：副作用範圍大、失敗不可逆。對應 [4.4 agent 架構](/llm/04-applications/agent-architecture/) 的 step-by-step approval / HITL 協作模型。

實作位置：tool layer、不是 prompt layer。Prompt 「請小心」是不夠的、靠 tool 本身不執行才有保證。

失敗模式：人類疲勞（rubber-stamp approval）、確認流程變橡皮圖章。設計時要讓 high-risk 跟 low-risk 動作走不同 gate、不要全部要人類確認、否則人類會關掉腦袋。

### Distribution monitoring

不在 single call 層擋、而是看 LLM 行為的分佈。例：每天客服回應的「拒絕率」「退款承諾率」、跑 alert；新 prompt 上線後追 token 用量、語氣 polarity、user satisfaction 的 baseline 漂移。

適用：行為層面的 silent drift（個別 call 看不出問題、加總起來偏掉）。

實作位置：production observability、trace pipeline（見 [4.20 LLM tracing](/llm/04-applications/llm-tracing-and-observability/)）。

失敗模式：baseline 沒先建、新 prompt 上線後不知道「正常範圍」是什麼、alert 無基準。

### 四種 guardrail 怎麼選

順序通常是：schema validation 最便宜先上、output validator 看內容風險再加、action gating 看不可逆性決定、distribution monitoring 是長期經營必備。

混用比例：一個成熟的 production LLM 應用通常四種都有、但分擔不同 risk class。輕量 query 只走 schema、會寫資料的走 schema + validator + gating、會影響多人的走全套加 monitoring。

## 實驗成本的位移

Deterministic 軟體的實驗成本高、改 code 要 PR review、要跑 CI、要考慮回退、所以團隊文化是「想清楚再寫」。Fuzzy 軟體的實驗成本低——改 prompt 一行、跑兩個 case、就能看新行為——所以更接近「快速試、不行就丟」。

這個位移對工程師的工作方式有實質影響：

- **Throw-away code 更可接受**：原本「寫了就要維護」、現在「先試、不行就重來」。
- **Prompt 是 source、但生命週期不一樣**：跟 code 一樣 version control（見 [4.10 衍生產物管理](/llm/04-applications/artifact-management/)）、但 iteration 速度比 code 快一個量級。
- **Eval 比 unit test 重要**：unit test 鎖行為、但 fuzzy 行為本來就會變、eval 看「行為分佈是否在期望範圍」才是有用的測試。
- **失敗的歸因分層**：壞掉時要問「是 prompt 問題、model 問題、context 問題、tool 問題、還是 deterministic glue 的 bug」——deterministic 軟體的歸因比較單一、fuzzy 軟體要分這幾層查。

這個位移是雙面刃。便宜實驗讓 iteration 快、但也讓 prompt / config / 行為快速分裂、production 跑著的東西跟 git 上看到的東西可能不一致。Mitigation 是 prompt template 上 version control、prompt diff 進 CI、production behavior 進 distribution monitoring。

## 跟 Agent / Workflow 設計的關係

Agent 跟 multi-call workflow 是「fuzzy 軟體」最複雜的型態。[4.4 agent 架構](/llm/04-applications/agent-architecture/) 列出 agent 的三大失敗模式（context drift / goal drift / tool misread）、本質上都是 fuzzy 行為在多步累積後溢出 guardrail。

這個 framing 對 agent 設計的啟示：

- **Loop 的每一步都是一個 fuzzy 邊界**：每步都要決定 schema / validator / gating / monitoring 的組合。
- **越多步累積、越需要 deterministic checkpoint**：「跑 10 步 fuzzy 推理、最後一步寫 DB」是高風險、要在中間插 deterministic verification。
- **Termination 是 deterministic 邊界**：靠模型自己說「完成了」是純 fuzzy、容易失控（見 [4.4 termination 條件](/llm/04-applications/agent-architecture/)）。混用 step cap、cost cap、external validation 是 deterministic guardrail 包 fuzzy loop 的標準做法。

## 何時過時 / 何時不過時

**不會過時的部分**：

- 兩個典範的四維對照（資料、邏輯、行為一致性、實驗成本）。
- 「哪段該 deterministic / 哪段該 fuzzy」的決策框架。
- 四種 guardrail 的分類跟組合原則。
- Fuzzy 邊界要包 deterministic、不是反過來的設計直覺。

**會變的部分**：

- 具體 schema 工具（Pydantic、Zod、各家 framework 的 typed output API）。
- 具體 LLM-as-judge 平台跟方法（見 [4.21](/llm/04-applications/llm-as-judge/)）。
- 各家 framework 的 guardrail SDK（隨工具世代換）。
- Fuzzy / deterministic 的邊界位置會隨模型能力移動——模型越強、能 fuzzy 處理的範圍越大、但「該包 guardrail」的原則不變。

## 小結

LLM 不是 deterministic 工具的下一代、是另一條工具線。Deterministic 軟體建立在「同 input → 同 output」假設上、fuzzy 軟體建立在「同 input → 分佈」假設上。兩者在資料、邏輯、分解、實驗成本四個維度都不同、設計直覺要分開。實務上一個 LLM 應用是兩者混合：使用者輸入解析、回應生成走 fuzzy、業務規則、資料庫操作、發送動作走 deterministic。Fuzzy 部分要用 schema / validator / gating / monitoring 四種 guardrail 包邊界、不是試圖把 fuzzy 變 deterministic。

下一章：[模組一 本地 LLM 服務](/llm/01-local-llm-services/) 進入工具層、或跳到 [模組四 LLM 應用層](/llm/04-applications/) 看這個典範怎麼落到 RAG / agent / workflow 設計。Agent 設計怎麼把 fuzzy / deterministic 邊界體現在 loop 結構上見 [4.4 agent 架構](/llm/04-applications/agent-architecture/)、人類介入點的設計選擇見 [4.5 人機協作拓樸](/llm/04-applications/human-ai-collaboration/)、跨多 call workflow 的 fuzzy 邊界設計見 [4.7 workflow 編排模式](/llm/04-applications/workflow-patterns/)。
