---
title: "4.4 Workflow 編排模式"
date: 2026-05-11
description: "Pipeline / router / parallel / reflection：多 LLM call 組合的四種基本模式與退化條件"
tags: ["llm", "applications", "workflow", "orchestration"]
weight: 4
---

LLM 應用很少是單一 call、多半是多次 LLM call 的組合。Multi-call 組合的模式雖然各 framework（LangGraph、LlamaIndex Workflow、各家 DAG runner）包裝不同、本質上可歸納成幾種基本模式：pipeline、router、parallel、reflection。理解這幾個模式、看到任何 LLM application 都能拆解成基本元件、判斷複雜度合不合理、識別常見反模式。

本章寫的是這四種模式的本質、它們的失敗模式、彼此組合的方式、何時退化成 single call 更好。具體 framework 的 DAG syntax / workflow API 不在本章——這些跨 framework 差異大、半年一變、原理層級更穩。

## 本章目標

讀完本章後、你應該能：

1. 區分四種基本 workflow 模式。
2. 看到一個 LLM application 時、能畫出它的 workflow 結構圖。
3. 判斷一個 workflow 是否該退化成 single call。
4. 識別 workflow 設計常見的反模式。

## LLM 應用的本質是多 Call 組合

單一 LLM call 解的問題有上限：

- Context 限制：再大的 [context window](/llm/knowledge-cards/context-window/) 也有上限、長文件得切。
- 推理深度：複雜推理拆步驟通常比一次推完更穩。
- Tool 範圍：multi-step tool use 需要多次 call 串起來。
- 多面向評估：同時要管邏輯、風格、合規時、單次 call 容易偏其中一面。

Multi-call 組合擴展能力範圍、代價是每多一個 call 多一份成本：

- **Latency**：N 個 call sequential 跑是 N 倍 latency；parallel 跑也至少要 max(call latency)。
- **Cost**：每個 call 的 token 成本累加、N 個 call 是 N 倍 cost。
- **失敗點**：每個 call 都可能失敗、N 個 call 串起來成功率是個別成功率連乘。
- **複雜度**：error handling、retry、partial success 處理複雜度爆炸。

「設計 workflow」的核心問題不是「能不能拆成多 call」、是「拆成多 call 的收益值不值得這份成本」。Workflow 設計常見的失敗是過早優化、把簡單問題切成複雜 DAG、最終比 single call 慢、貴、難維護、品質卻沒提升。

四種基本模式各自解不同的「為什麼需要多 call」、下面逐個展開。

## Pipeline：線性串接

**結構**：`call_1 → call_2 → call_3 → ...`、後一個 call 用前一個的 output 當 input。

**適合場景**：

- 任務有清楚的線性子步驟（萃取 → 摘要 → 翻譯、或 plan → execute → review）。
- 每個子步驟用同個模型最划算（一個 call 撐不下、拆成幾個 call 接力）。
- 子步驟輸出需要中間驗證 / 處理（前一步先過 schema 解析、再餵下一步）。

**典型例子**：

- Code review pipeline：先 LLM 找問題列表 → 再 LLM 對每個問題寫修改建議 → 最後 LLM 合成 summary。
- 文件處理：原文 → 萃取結構化資訊 → 套用 template → 輸出最終格式。

**失敗模式**：

- **中間步驟誤差累積**：第一步小錯、第二步基於錯誤輸出、第三步累積到完全跑偏。整體錯誤率是個別錯誤率連乘的補集（任一步錯整個 pipeline 錯）。
- **無法檢測前段錯誤**：後段沒辦法回頭修正前段、即使發現結果不對。
- **過度拆解**：本來 single call 能處理的事拆成 3 步、latency 跟 cost 都暴增。

**緩解策略**：

- 中間步驟加 validation（schema 解析、簡單 sanity check）、catch 早期錯誤。
- 關鍵 pipeline 加 logging、出問題時能定位是哪一步壞。
- 定期重新評估「這個 pipeline 真的需要拆嗎」、不需要就合併回 single call。

## Router：依輸入分流

**結構**：`input → classifier → path A / B / C → output`、依分類結果走不同處理路徑。

**適合場景**：

- 輸入類型多樣、不同類型需要不同處理（簡單 query 用小模型、複雜 query 用大模型）。
- Cost 優化（多數簡單請求走便宜 path、少數複雜請求走貴 path）。
- 功能分流（query 是 search、summarization、還是 code edit）。

**典型例子**：

- 客服分流：先判斷使用者意圖（查訂單 / 退貨 / 一般諮詢）、再分到對應 specialized agent。
- 模型分流：先 1B classifier 判斷複雜度、簡單問題給本地 14B、複雜問題給雲端旗艦。

**失敗模式**：

- **Classifier 錯判**：分流錯了、整個 query 跑進最差 path、結果完全不對。
- **Classifier 比下游還複雜**：本來 router 是 cost saver、結果 classifier 本身就要強模型、變成多花錢的繞路。
- **Path 設計不完整**：有些 query 不符合任何 path、router 強塞到某個 path、結果差。

**緩解策略**：

- Classifier 用較弱模型但加 confidence 判讀、低 confidence 走 fallback path。
- 簡化 path 數量（3-5 個內、不要無限細分）。
- 設計「unknown / catch-all」path、不假設所有 input 都能歸類。

## Parallel：多 Call 並行、結果合併

**結構**：`input → [call A, call B, call C 並行跑] → 合併 → output`、多次 LLM call 同時跑、結果合起來。

**適合場景**：

- 任務有獨立面向（評估一份 PR 的程式碼品質 / 安全性 / 可讀性、各自一個 call）。
- Ensemble（同個任務跑多次、用 majority vote 提高可靠度）。
- Multi-source retrieval（從不同來源平行拉資料、合起來餵下游）。

**典型例子**：

- 多面向審查：同份 code 同時跑「邏輯」「風格」「安全」三個 review、合併成總評。
- Ensemble decoding：同個 prompt 用不同 seed / temperature 跑 5 次、majority vote 拿最穩答案。

**失敗模式**：

- **合併邏輯難設計**：parallel 容易、合併難。三個 reviewer 意見不一致時怎麼裁判？多數決還是加權？
- **Cost 是 sequential 數倍**：parallel 跑 N call 的 cost 是 sequential single 的 N 倍、latency 才有節省。
- **不需要並行**：本來 sequential single call 能解的事、parallel 變浪費。
- **不獨立的「平行」**：兩個 call 其實依賴彼此、強制 parallel 反而漏訊號。

**緩解策略**：

- Parallel 前先問：這些 call 真的獨立嗎？依賴的應該 sequential。
- 合併邏輯先設計、再開始 parallel；沒想清楚怎麼合的就先別 parallel。
- Cost 監控：parallel 是 cost amplifier、生產環境注意。

## Reflection：產出 → 評估 → 修正

**結構**：`產出 → critic 評估 → 依評估修正 → 再評估 → ...`、self-improvement loop。

**適合場景**：

- 任務有客觀評估訊號（test 跑通、規範符合、structured output 合法）。
- 一次產出品質不夠、可以迭代改善。
- 創意任務的「初稿 → 修稿」流程。

**典型例子**：

- Code 生成 + test 驅動：產出 code → 跑 test → 失敗的話讀 error 修正 → 再跑 test → 直到通過。
- 文章寫作：生成草稿 → critic 模型評論 → 依評論修改 → 再評論 → 直到滿意。

**失敗模式**：

- **Critic 跟 generator 共用 blind spot**：兩個都同個模型、有同樣的盲點、reflection 不可能 catch（如兩個都不認識某個 framework 的 API、再 reflect 也不對）。
- **無限循環**：沒有客觀停止訊號、reflection 一直跑、cost 爆掉。
- **過度修正**：每次 reflection 都改一點、累積結果變糟（過度 fitting critic 意見）。
- **Critic 失職**：critic 太寬鬆、什麼都說 OK；或太嚴格、什麼都挑、永遠停不下來。

**緩解策略**：

- Critic 用不同模型、或不同 prompt 角度、減少 blind spot。
- Reflection 設 step 上限、即使沒達標也強制停。
- 客觀驗證訊號（test pass、schema 合法、外部 metric）優先於 LLM critic 主觀評估。
- 用 reflection 改進「明顯錯」、不用來改進「主觀偏好」。

## 四種模式的組合

實際應用通常混用、不是純單一模式：

- **Pipeline of routers**：第一步先 router 分類、每個 path 內部又是 pipeline。
- **Parallel of pipelines**：多個 pipeline 平行跑、最後合併。
- **Reflection inside pipeline**：pipeline 中某幾步用 reflection loop 改進、其他步驟 single call。
- **Router into reflection**：依輸入複雜度分流、簡單走 single call、複雜走 reflection loop。

複雜應用通常是這四種模式的多層組合。看 LLM application 結構時、能識別出基本模式組合、就能判斷它的複雜度合不合理。

組合的判讀訊號：

- 三層以上嵌套通常 over-engineered、考慮簡化。
- 同個模式重複用很多次（如 5 個 pipeline 串）可能拆得太細。
- 看不出基本模式的 ad-hoc 流程、通常維護困難。

## 何時退化成 Single Call 更好

判讀「該不該設計 workflow」的反射：先問「single call 能不能解」、不行再考慮拆。

Single call 更適合的訊號：

- 上下文短（< 8K token、塞得進現代 LLM）。
- 推理單純、不需要 multi-step。
- 不需要 tool 或只需一兩個簡單 tool。
- 沒有客觀驗證訊號可用、reflection 沒意義。
- Latency 敏感、不能接受多次 round trip。

「我先寫個 pipeline」常是過早優化：

- 簡單問題切成 5 步、累積誤差大過拆分收益。
- 為了「靈活性」抽象太多、最終比 single prompt 還難改。
- 寫 workflow framework 的成本超過用 raw API 的成本。

實務做法：先 single call baseline、跑半週看品質、不夠用再分解；不要從 workflow 開始設計。

## Workflow 設計常見的反模式

幾種特別容易踩的反模式：

### 過度切碎 pipeline

把任務切成 10 步、每步一個 LLM call、累積誤差大、latency 拖長、cost 爆。問題通常是「我以為拆細了品質會好」、實際相反。

訊號：pipeline 步驟超過 5 個、每步輸入輸出量級接近、看不出為什麼需要分。

緩解：能合併的合併、保留必要切點（中間有外部 tool 介入、或需要驗證的步驟）。

### Parallel 跑根本不需要並行的事

兩個 call 其實依賴彼此、或本質是同個任務、硬要 parallel。Cost 是 sequential 的 N 倍、品質沒提升。

訊號：parallel 出來的結果合併邏輯複雜、或合併結果跟「直接 sequential 跑」差不多。

緩解：parallel 前問「這幾個 call 真的獨立、結果真的可合併嗎」、不獨立就 sequential。

### Reflection 沒有客觀停止條件

Reflection loop 純靠模型自己判斷「夠好了沒」、容易過度修正或無限循環。

訊號：reflection loop 沒有 step cap、沒有外部 metric、純依模型自評。

緩解：每個 reflection loop 都設 step 上限 + 客觀停止訊號（test pass、external check）。

### Router classifier 過於複雜

Classifier 本身就需要強模型、變成 router「省 cost」反而花更多。

訊號：classifier 用的模型跟下游 path 同等級或更強。

緩解：classifier 應該用最便宜的小模型、不行就接受「沒有 router、全部走主 path」。

### 看不出基本模式的 ad-hoc 流程

完全自訂的 control flow、不能對應到任何標準模式、維護困難。

訊號：流程圖畫不出來、新人接手要花一週搞懂、改一個 bug 影響不知道擴散到哪。

緩解：重新設計、強制套用基本模式組合。不能套用通常代表設計過度複雜。

## 何時過時 / 何時不過時

**不會過時的部分**：

- 四種基本模式（pipeline / router / parallel / reflection）的結構跟失敗模式分類。
- Multi-call 成本（latency / cost / 失敗點累乘）的本質。
- 「先 single call baseline、不夠再分解」的設計順序。
- 五個常見反模式的識別。

**會變的部分**：

- 具體 workflow framework（LangGraph、LlamaIndex Workflow、各家 DAG runner）的 API。
- 「最佳化」的具體技巧（caching、batching、streaming 整合）。
- 哪些 framework 對哪種模式支援好（會持續演化）。

看到新 workflow framework 時、回到本章四模式 framing、看它支援哪些模式、有沒有解決常見反模式、能不能跟你的應用場景對齊。Framework 換代不影響這四個模式的本質結構。

## 小結

LLM 應用是 multi-call 組合、本質歸納成四個基本模式：pipeline、router、parallel、reflection。每個模式各自解不同問題、各有失敗模式、實際應用組合使用。Workflow 設計的核心反射是「先 single call baseline、不夠再分解」、過早優化是最常見的失敗源。

讀到這裡、本模組的應用層原理就完整收尾。回到 [模組四首頁](/llm/04-applications/) 看完整地圖、或回到 [指南首頁](/llm/) 重新整理整體學習路徑。
