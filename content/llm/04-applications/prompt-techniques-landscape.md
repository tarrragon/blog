---
title: "4.0 Prompt 技術光譜：手法分類、取捨、組合模式"
date: 2026-05-14
description: "Zero-shot / few-shot、chain-of-thought、role / template、reflection 等 prompt 技術的分類與取捨、何時 stack 何時不要 stack、跟 fine-tune / RAG / chaining 的邊界"
tags: ["llm", "applications", "prompt-engineering", "tradeoffs"]
weight: 0
---

Prompt 技術不缺教學文章——但多數教學是「教你怎麼寫」、半年後模型換代、寫法跟著過時。本章不教「怎麼寫」、寫的是**這個技術 landscape 的結構**：有哪些手法、每個解什麼問題、它們的 trade-off 在哪、什麼時候該組合、什麼時候不該。這些結構性問題跨模型世代不變。

讀完本章後、看到任何新 prompt 技術都能放回正確座標、判斷「這是哪一軸的優化、跟我現在的問題對上嗎、能不能跟既有技術疊」——而不是每出一個新技術都從零學一次。

## 本章目標

讀完本章後你能：

1. 把任何 prompt 技術放進三軸座標（context 提供 / 推理引導 / 角色與格式）。
2. 對單一技術評估四維 trade-off（accuracy、latency、cost、debuggability）。
3. 判斷何時 stack 技術、何時 stack 會互相抵消。
4. 區分 prompt 層解法 vs fine-tune / RAG / chaining 解法的邊界。
5. 看到「prompt 改了沒效」時、診斷是 systematic error 還是 random error。

## 本章鎖定的是結構層、不是寫法層

Prompt 知識可以分兩層：**易變層**是具體寫法（特定模型偏好哪種句型、特定任務最佳 step 切法）、**不變層**是「有哪些技術可選、各解什麼問題、能不能組合」的結構。本章只寫不變層。

易變層為什麼留給 case-by-case：

- **跨模型差異**：對 GPT-4 有效的寫法、對 Claude 可能反效果。模型 SFT 分佈不同、對 prompt 結構的偏好不同。
- **跨任務差異**：對 summarization 有效的格式、對 classification 沒幫助。每個任務的最佳 prompt 形狀要實驗。

不變層的價值是：看到任何新 prompt 技術都能放回正確座標、判斷它解什麼問題、跟既有技術疊能不能。具體寫法（act as XYZ 怎麼設計、step 怎麼分）屬於客製工作、不在本章。

## 三軸分類

把 prompt 技術放到三軸座標、看到任何新手法都能定位：

| 軸           | 解決什麼問題                 | 代表技術                                    |
| ------------ | ---------------------------- | ------------------------------------------- |
| Context 提供 | 模型「缺資料 / 缺對齊範例」  | zero-shot、few-shot、retrieval-augmented    |
| 推理引導     | 模型「直接答錯、需要 think」 | chain-of-thought、decomposition、reflection |
| 角色與格式   | 模型「不知該以什麼姿態回應」 | role prompting、persona、output template    |

每個技術可能跨軸（如 few-shot CoT 同時 context + 推理）、但歸到主軸有助判讀「這技術在解哪一類問題」。看到新技術時、先問「它放哪一軸」、再看它跟既有技術的關係。

## Context 軸：模型缺什麼資料

### Zero-shot

直接給任務、不給範例。

- **適用**：模型對任務分佈熟、輸出格式可預測。例：「將下列文字翻譯成英文」。
- **失效**：任務邊界模糊、模型沒「對齊到你的標準」。例：「分類這個 review 是正向 / 中性 / 負向」——「中性」的邊界在不同產業差很多。

### Few-shot

[Few-shot prompting](/llm/knowledge-cards/few-shot-prompting/) 在 prompt 內塞幾個 input-output 範例、模型透過範例對齊任務。

- **適用**：任務有「我的標準跟模型預設不同」、但能舉幾個代表性例子。常見場景：分類、抽取、格式轉換、tone alignment。
- **核心收益**：把「對齊任務」這件事從 fine-tune 移到 prompt——iteration 從幾天縮到幾分鐘、不動模型權重。
- **失效**：範例選不好（cherry-picked、cover 不到 edge case）、範例太多撐爆 context、任務本質需要外部知識（這時該用 RAG 不是 few-shot）。

Few-shot 跟 fine-tune 是「對齊」這件事的兩個 endpoint。Trade-off：

| 維度      | Few-shot in prompt              | Fine-tune                            |
| --------- | ------------------------------- | ------------------------------------ |
| Iteration | 分鐘級、改 prompt 即可          | 天級、要 retrain                     |
| 範例容量  | 受 context window 限制（10–50） | 可以幾千幾萬、整個 dataset 都行      |
| Cost      | 每次 inference 多付 token       | 一次性訓練 cost、之後 inference 不變 |
| 模型遷移  | 跨模型即時換、prompt 直接搬     | 綁特定 base model、換模型要 retrain  |
| 知識更新  | 改 prompt 即可                  | 要 retrain                           |

實務啟示：先 few-shot、等到範例真的多到撐爆 context 又每天都用、再考慮 fine-tune。本指南對 fine-tune 的整體看法見 [3.4 訓練流程](/llm/03-theoretical-foundations/training-pipeline/)。

### Retrieval-augmented prompting

跟 few-shot 像、但範例不是寫死、是**從一個範例庫即時 retrieve**。技術上落在 [4.1 RAG 原理](/llm/04-applications/rag-principles/)、但概念上是 few-shot 的延伸——把固定範例變成動態範例。

- **適用**：範例庫大、每次任務最相關的範例不同。
- **跟 RAG 知識檢索的差異**：RAG 取「事實 / 文件」、retrieval-augmented prompting 取「相似任務的解答範例」。兩個目的不同、但 infra 共用。

## 推理軸：模型該不該「think」

### Chain-of-Thought（CoT）

[Chain-of-Thought](/llm/knowledge-cards/chain-of-thought/) 要求模型「show your work」、把推理步驟寫出來、再給最終答案。

- **適用**：multi-step reasoning（數學、邏輯、複雜判斷）、模型直接答錯但 step-by-step 後對。
- **失效在 reasoning model 出現後**：[reasoning model](/llm/03-theoretical-foundations/reasoning-models/) 本身就在生成內部推理 trace、再外加 explicit CoT prompt 邊際收益遞減、部分模型可能反而干擾內部推理路徑。判讀訊號：模型卡片寫「reasoning model」、就不要再加 "think step by step"。
- **失效在低能力模型**：模型本身推理能力不足、CoT 變成「把錯誤推理寫得更詳細」、不會把答案變對。CoT 是「把潛在能力擠出來」、不是「給模型新能力」。

### Task decomposition

把大任務拆成幾個明確子任務、prompt 內 enumerate 出來。

- **跟 CoT 的差異**：CoT 是「過程要 explicit」、decomposition 是「子任務要 explicit」。CoT 在 single call 內展開、decomposition 可以單 call 也可以多 call。
- **適用**：任務有明顯的 phase（如「先抽要點、再寫 outline、再展開段落」）、不分階段就會走錯。
- **跟 chaining 的邊界**：decomposition 寫在 single prompt 裡是 prompt 技術；拆成多 call 是 [4.7 workflow patterns](/llm/04-applications/workflow-patterns/) 的 pipeline 模式。判讀：每階段 output 要不要被審查 / 被 inject 不同 context → 要 → 走 chaining；不需要 → 留在 single prompt 內 decomposition。

### Reflection / self-critique

[Reflection](/llm/knowledge-cards/reflection/) 要求模型先輸出一版、再 critique 自己、再修改。

- **適用**：模型有能力辨識「自己寫的不夠好」、critique 跟 generator 不會共用同樣 blind spot。
- **失效**：critique 跟 generator 是同個模型、訓練分佈中的盲點不會因為「再想一次」消失。判讀訊號：critique 每次都給很像的建議、或修完還是同一類錯——這是 systematic error、加 reflection 沒收益。
- **完整失敗模式分析見** [4.7 workflow patterns](/llm/04-applications/workflow-patterns/) reflection 段。

## 角色與格式軸：模型該以什麼姿態回應

### Role prompting

"Act as X" 系列——指定模型扮演的角色或專業領域。

- **適用**：通用模型在多種風格之間漂、加 role 把它鎖到特定分佈。例：「act as a senior backend engineer reviewing this PR」鎖技術深度。
- **失效**：role 跟任務無關（"act as a wizard" 做財務分析）、或 role 設定跟使用者實際需求衝突。Role 是調 tone / 深度 / 視角的工具、不會給模型新能力。
- **常見過度迷信**："you are the best in the world at this" 這類自誇式 prompt 跨模型效果不穩定、難以可靠重現。不值得當核心策略。

### Output template

指定 output 格式（JSON schema、Markdown 結構、特定欄位）。

- **適用**：output 要餵下游 deterministic 系統（API、DB、UI）、格式錯就整個流程斷。
- **執行層次**：純 prompt 指定（弱）→ few-shot 範例（中）→ structured output / constrained decoding（強、見 [3.10 constrained decoding 內部](/llm/03-theoretical-foundations/constrained-decoding-internals/)）。三者疊用最穩。
- **失效**：模板太緊、模型為了符合格式犧牲內容品質。Trade-off：嚴格 schema 換來下游穩定、但 prompt 的 expression 空間變小。

### Persona / system prompt

跨 turn 持續性的角色與行為設定、放在 [system prompt](/llm/knowledge-cards/system-prompt/)。

- **跟 role prompting 的差異**：role prompting 是 single call 的暫時角色、persona 是跨 turn 的長期人設。多數 chatbot 應用都在後台塞 persona。
- **失效**：persona 跟 user request 衝突時、模型在「跟 persona 一致」跟「滿足 user」之間擺盪、行為不穩。

## 四維 Trade-off

每個 prompt 技術都可以用這四維評估：

| 維度          | 意義                                | 典型代價                    |
| ------------- | ----------------------------------- | --------------------------- |
| Accuracy      | 任務完成品質                        | —                           |
| Latency       | 從 request 到 final response 的時間 | Token 累積拉長生成時間      |
| Cost          | 每次 inference 的 token 成本        | Token 累積放大成本          |
| Debuggability | 失敗時能不能定位是哪一步出問題      | Single 大 prompt 失敗難排查 |

四維是 trade-off、不是「都拉到最高」。Few-shot 提高 accuracy 但加 cost 跟 latency；CoT 提高 accuracy 但顯著拉長 latency；reflection 進一步提高 accuracy 但 cost / latency 翻倍以上。

Latency 的展開：標準 LLM 生成的 latency 由 TTFT（首 token 時間）+ output token 數 × per-token latency 決定。Few-shot 加 input token、影響 TTFT 但不影響 per-token；CoT / reflection 加 output token、顯著拉長總生成時間。Reasoning model 例外——它的 thinking token 也算 output、顯著拉長 TTFT 跟總時間、加 explicit CoT 在 reasoning model 上是重複收費。

Debuggability 的展開：single 大 prompt 跑出錯時、要排查是 task 拆解錯、role 不對、few-shot 範例誤導、還是格式描述不清——所有問題混在一個 call 裡。Chaining / decomposition 把流程拆成多個獨立 step、每 step 有自己的 input / output trace、可以 isolate 故障點。Trade-off：chaining 加 latency / cost、但 debug 時間遠少。

設計時先問「我的 binding constraint 是哪個」：

- 即時 chatbot → latency / cost 優先、accuracy 次要、避開 reflection
- 後台 batch（每晚跑、明早看）→ accuracy 優先、latency 不重要、reflection 可用
- 高代價任務（醫療、法律、財務）→ accuracy + debuggability 優先、cost 不在乎

## 組合：Stack 的兩個條件

Stack 有效的必要條件是**兩技術解不同軸的問題、且底層假設一致**。兩條件都滿足才有疊加收益、任一失效就會抵消甚至反效果。

### 有效的 stack 組合

- **Few-shot + role**：few-shot 解「任務對齊」、role 解「回應姿態」、兩軸不衝突。
- **Few-shot + output template**：few-shot 教任務、template 鎖格式、互補。
- **CoT + decomposition**：decomposition 拆 phase、CoT 展開每 phase 的推理、層級互補。

### 失效的 stack 組合（同軸或假設衝突）

- **CoT + reasoning model**：reasoning model 內部已在做 chain-of-thought、外加 explicit CoT 邊際收益遞減、部分模型可能反而干擾內部推理路徑。判讀：模型卡片寫 reasoning、就不要再加 "think step by step"。
- **Reflection + 低能力模型**：reflection 需要 critique 能力、低能力模型 critique 不出有用建議、徒增 cost。
- **多重 role 衝突**："act as a creative writer AND a strict editor"——指令互相牴觸、模型隨機選一邊。
- **Few-shot 太多 + long context 任務**：few-shot 撐爆 context、留給實際任務的空間不足、accuracy 反降。

判讀 stack 是否有效的反射動作：問「兩個技術解的是不同問題嗎、它們有沒有共用底層假設」。

## 跟相鄰技術的邊界

Prompt 技術不是萬能、有些問題該換層解：

| 問題                           | Prompt 層能解到哪                 | 該換的層                                                               |
| ------------------------------ | --------------------------------- | ---------------------------------------------------------------------- |
| 模型不知道某個事實             | few-shot 塞少量、不夠             | RAG（[4.1](/llm/04-applications/rag-principles/)）                     |
| 模型完全不會某個任務           | few-shot 撐不住、頻繁失敗         | Fine-tune（[3.4](/llm/03-theoretical-foundations/training-pipeline/)） |
| 任務要多步、每步要不同 context | single prompt 塞不下、邏輯混      | Chaining / workflow（[4.7](/llm/04-applications/workflow-patterns/)）  |
| 任務要外部資料 / API           | prompt 描述不出、需要實際呼叫     | Tool use（[4.3](/llm/04-applications/tool-use-principles/)）           |
| 任務要 LLM 自主推進            | prompt 無法表達「持續決定下一步」 | Agent（[4.4](/llm/04-applications/agent-architecture/)）               |

判讀訊號：prompt 改了五版、accuracy 還是不到 baseline、就該往這個表的右欄移、不是再改 prompt 第六版。

## 失敗診斷：Prompt 改了沒效時

Prompt 修改沒效、定位是 systematic 還是 random error：

- **Random error**：同 prompt 跑 N 次、output 不穩定、有時對有時錯。可以靠 reflection / 多採樣 / temperature 降低收斂——這條路 prompt 層有解。
- **Systematic error**：同 prompt 跑 N 次、output 一致地錯（或一致地朝某個方向偏）。reflection 沒用、prompt 改寫也救不回——這是模型能力 / 訓練分佈問題、要往 RAG / fine-tune / 換模型走、不是再改 prompt。

判讀步驟：

1. 同 prompt 跑 5–10 次、看 output 分佈
2. 若分佈寬：random error、prompt 層可解
3. 若分佈窄但錯：systematic error、不要再 iterate prompt、換層

這個判讀直接呼應 [模組零 fuzzy engineering](/llm/00-foundations/deterministic-vs-fuzzy-engineering/) 的「同 input → 分佈」假設——不看分佈、debug 就是瞎猜。

## 何時過時 / 何時不過時

**不會過時的部分**：

- 三軸分類（context / 推理 / 格式）。
- 四維 trade-off（accuracy / latency / cost / debuggability）。
- Stack 有效 vs 抵消的判讀原則（不同軸 vs 同軸 / 底層假設）。
- Prompt 層 vs 換層的邊界判讀。
- Systematic vs random error 的診斷流程。

**會變的部分**：

- 對特定模型有效的具體寫法（每個模型偏好的 prompt structure）。
- 角色 prompting 的有效程度（隨 model alignment 訓練成熟、role hack 的效果逐年降低）。
- CoT 的必要性（reasoning model 普及後、explicit CoT 的場景縮小）。
- Output format 強制手段（從 prompt-only 走向 structured output API、再走向 constrained decoding）。

## 下一章

下一章：[4.1 RAG 原理](/llm/04-applications/rag-principles/)、把「prompt 層塞不下知識」這個邊界往外推、進入 LLM 跟外部資料互動的領域。Prompt 跟 fine-tune 的對齊取捨見 [3.4](/llm/03-theoretical-foundations/training-pipeline/)、跟 chaining 的邊界完整討論見 [4.7](/llm/04-applications/workflow-patterns/)、跟 fuzzy engineering 典範的關係見 [0.8](/llm/00-foundations/deterministic-vs-fuzzy-engineering/)。
