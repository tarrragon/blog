---
title: "4.16 LLM-as-Judge 評估方法"
date: 2026-05-12
description: "LLM 評估 LLM 的 production eval 方法：rubric design、pairwise / direct scoring、三大 bias 緩解、跟 trace 串接的閉環、calibration"
tags: ["llm", "applications", "evaluation", "production", "llm-as-judge"]
weight: 16
---

[4.9 benchmarking-and-evaluation](/llm/04-applications/benchmarking-and-evaluation/) 寫了 capability benchmark（MMLU、SWE-bench 等）跟 in-house benchmark 概念。但「自己工作流的真實案例該怎麼系統性 eval」這個操作層、4.9 點到沒展開。本章補上 [LLM-as-Judge](/llm/knowledge-cards/llm-as-judge/) — production AI app 的事實標準 eval 方法、比 human eval 便宜 500-5000×、跟人類有 80%+ agreement、但要處理 bias。

## 本章目標

讀完本章後、你應該能：

1. 區分 LLM-as-Judge、standard benchmark、human eval 三條 eval 路徑。
2. 設計可重現的 judge rubric（input / output / rubric / reasoning 四段）。
3. 用 pairwise vs direct scoring、知道何時用哪種。
4. 緩解三大 bias（position / verbosity / self-preference）。
5. 把 production [trace](/llm/04-applications/llm-tracing-and-observability/) 餵回 judge、形成自動 eval 閉環。

## 為什麼需要 LLM-as-Judge

[4.9](/llm/04-applications/benchmarking-and-evaluation/) 推「in-house benchmark 是 final test」、但操作層是個 gap：

| Eval 痛點                               | LLM-as-Judge 解法                               |
| --------------------------------------- | ----------------------------------------------- |
| Standard benchmark 跟自己 use case 不符 | Judge 用自己 case 跑、rubric 自定義             |
| Human eval 太貴 / 太慢                  | Judge 自動跑、$0.001-0.01 per item              |
| Production trace 量大、人工看不完       | Judge 跑 100% production trace 都可行           |
| Rule-based eval 抓不到語意問題          | Judge 能判斷「答案是否符合意圖、即使措辭不同」  |
| Iteration 需要快速 feedback             | Judge 幾分鐘跑完 100 items、prompt 改完馬上重測 |

主要 use case（重複 [LLM-as-Judge 卡片](/llm/knowledge-cards/llm-as-judge/)）：in-house benchmark、production trace eval、A/B test、synthetic data quality。

## Judge prompt 結構

可重現的 judge 必須四段式：

```text
[Section 1: Task description]
你是 LLM 輸出品質評估員。要評估 coding assistant 對使用者請求的回答品質。

[Section 2: Input + Output to evaluate]
User request: {input}
Assistant response: {output}

[Section 3: Rubric（評分標準）]
評分維度：
1. Correctness（程式碼能否運作、邏輯是否正確）：1-5
2. Style（是否符合 codebase convention）：1-5
3. Completeness（是否完整解決 user request）：1-5

評分規則：
- 5：完美無瑕、可直接 merge
- 4：小修可用、整體正確
- 3：方向正確、需 substantial 修改
- 2：部分對、主要邏輯有錯
- 1：完全錯、誤導使用者

明確不加分：
- 冗長 / verbose（同樣正確的短答 = 長答）
- 道歉 / 開場白
- 「我希望這有幫助」這類禮貌話

[Section 4: Output format]
請依下列 JSON 輸出：
{
  "correctness": <1-5>,
  "style": <1-5>,
  "completeness": <1-5>,
  "reasoning": "<簡短解釋>",
  "overall": <1-5>
}
```

關鍵設計原則：

1. **Rubric 明確、可重現**：用 1-5 scale + 每分明確定義、避免 judge 自由發揮
2. **明確列「不加分項」**：vag rubric 容易讓 judge 加分長答 / 道歉 / 客套（verbosity bias）
3. **要求 reasoning**：強迫 judge 寫評分理由、提升 calibration、後續可 debug
4. **Structured output**：用 JSON / [structured output](/llm/04-applications/application-protocols/) 強制格式、後續可程式化處理

## Pairwise vs Direct scoring

兩種主流評分方式：

### Direct scoring（直接打分）

給一個 (input, output)、judge 給絕對分數（1-5、1-10）。

優點：簡單、可看「絕對品質」隨時間改變
缺點：分數 calibration 不穩（不同 batch 跑、judge 可能 baseline drift）

### Pairwise comparison（兩兩比較）

給一個 input + 兩個 output（A、B）、judge 選哪個比較好。

優點：相對比較比絕對打分穩、適合 A/B testing
缺點：需要兩個 candidates、結果是「A > B」不是「A 多好」

實務組合：

| 場景                          | 適合方式                              |
| ----------------------------- | ------------------------------------- |
| Production quality monitoring | Direct scoring（每個 trace 一個分數） |
| Prompt / model A/B test       | Pairwise（A 跟 B 比）                 |
| Fine-tune 前後比較            | Pairwise                              |
| Regression detection          | Direct（跟 baseline 比較）            |
| Synthetic data filtering      | Direct（保留 ≥ 4 分）                 |

## 三大 Bias 跟緩解

### 1. Position bias（位置偏見）

Pairwise 比較時、judge 對「先出現」的 candidate 有偏好（通常偏 A）。

**緩解**：

- 換位置跑 2 次（A-B 跟 B-A）
- 只 count 兩次都偏 A 的為「prefer A」、不一致為「tie」
- 標準 LLM-as-Judge framework（如 MT-Bench）內建這做法

### 2. Verbosity bias（冗長偏見）

Judge 傾向給「長答」高分、即使內容沒比「短答」更好。

**緩解**：

- Rubric 明確寫「冗長不加分」「同樣正確的短答 = 長答」
- 長度 normalize：分數 = raw_score / log(length)
- 用 length-controlled benchmark（如 length-controlled AlpacaEval）

### 3. Self-preference bias（自家偏好）

Judge 偏好自家風格的答案（GPT 當 judge、偏好 GPT-style 輸出；Claude 當 judge、偏好 Claude-style）。

**緩解**：

- 用 3 個不同 family 的 judge model（如 Claude + GPT + Gemini）取多數
- 避免 judge 跟 test subject 同 model
- 用 reasoning model 當 judge（多家 reasoning model 共識更穩）

### 補充 bias：Format bias

Judge 對「有 markdown / 有 code block / 有結構」的答案偏好、即使內容沒比「純文字」更好。

**緩解**：rubric 明確寫「格式不加分、看內容」。

## Calibration（校準）

Judge 不該光信、要 calibrate：

```text
1. 蒐集 100 個 (input, output) pair
2. Human eval（你自己或可信 human）打 ground truth 分數
3. Judge 跑同樣 100 個
4. 算 agreement rate：
   - Pairwise：judge 跟 human 同意比例（target > 75%）
   - Direct scoring：Spearman correlation（target > 0.7）
5. 若 agreement 低：
   - 改 rubric（更明確）
   - 換 judge model（更強）
   - 改 prompt（few-shot example）
6. Calibrate 後的 judge 才能跑 production
```

Calibration 是「judge 評什麼」跟「人類評什麼」對齊的步驟、跳過會讓 production eval 失準。

## 跟 [4.15 LLM tracing](/llm/04-applications/llm-tracing-and-observability/) 的閉環

Production trace + LLM-as-Judge 形成自動 eval pipeline：

```text
Production users
   ↓ 產生 trace
[LLM tracing 平台]（LangSmith / Phoenix / Langfuse / Braintrust）
   ↓ filter：user thumbs-down、error、long latency 等 trace
   ↓ sample 100 個 / day
[LLM-as-Judge batch run]
   ↓ rubric scoring
[Dashboard]
   - 哪類 query 品質下降
   - 哪個 deployment version 品質差
   - 哪個 user segment 體驗差
   ↓
觸發 alert / 改 prompt / 改 model / 回退
   ↓ A/B test
   ↓ Pairwise judge eval new vs old
   ↓ Deploy 勝者
```

這是 production LLM 應用 quality engineering 的標準閉環。

## Judge model 選型

| Judge model 候選                           | 強項                           | 弱項                              |
| ------------------------------------------ | ------------------------------ | --------------------------------- |
| Claude Sonnet / Opus                       | reasoning 強、rubric 跟得緊    | Cost 中等                         |
| GPT-5 / GPT-4o                             | 普及、tool-calling 強          | 對自家 GPT 輸出有 self-preference |
| Gemini Pro 2.5                             | Long context 強、multi-modal   | rubric 跟得較鬆                   |
| o1 / o3 / R1（reasoning model）            | 推理能力強、判 nuanced case 穩 | Cost 高、latency 長               |
| 本地 30B+ 模型（QwQ、DeepSeek-R1 distill） | 隱私強、cost 0                 | 能力上限低於雲端旗艦              |

判讀：

1. **大 stake / final QA**：雲端旗艦 reasoning model
2. **大量 production trace eval**：中等模型（GPT-4o / Sonnet）、cost / speed 平衡
3. **隱私敏感（user trace 不能送雲端）**：本地 reasoning model（QwQ-32B / R1 distill）
4. **A/B test prompt 改進**：用同個 judge 跑前後比對、保持 baseline

## 失敗模式

1. **Rubric 太 vague**：judge 自由發揮、分數沒重複性

**緩解**：rubric 寫得像 unit test、每分有具體 criteria

2. **沒做 calibration**：judge 跟 human agreement 沒驗、可能 systematically off

**緩解**：每次大改 rubric / 換 judge model 都重新 calibrate

3. **Sample 不代表 production**：只 eval easy case、production 真實困難 case 沒覆蓋

**緩解**：用 stratified sampling（按 difficulty / user segment / feature 抽樣）

4. **Bias 沒緩解**：position / verbosity / self-preference 直接 baked in

**緩解**：標準 framework（DeepEval / Inspect / Braintrust）內建 bias 緩解、用既有 framework 比 DIY 穩

5. **Judge cost 比預期高**：production trace 全跑 judge、cost 爆

**緩解**：sample rate < 10%、配合 [LLM tracing](/llm/04-applications/llm-tracing-and-observability/) 的 sampling

6. **Over-reliance on judge**：忘記 judge 也會錯、把 judge 當絕對真理

**緩解**：高 stake 任務仍需 spot human review、judge 是 80% 解、不是 100%

## 主流 framework

| Framework               | 特色                                    |
| ----------------------- | --------------------------------------- |
| DeepEval                | OSS、Python、跟 pytest 整合             |
| Inspect（UK AI Safety） | 強 eval framework、reasoning model 友善 |
| Braintrust              | SaaS、eval + tracing 一體               |
| Langfuse evals          | OSS、跟 tracing 整合                    |
| OpenAI evals            | OSS、Anthropic 也支援                   |
| Patronus                | Production eval SaaS                    |

## 何時不該用 LLM-as-Judge

1. **可機械驗證**：unit test、exact match、output schema validation — 用 deterministic rule 比 judge 穩
2. **極小 dataset（< 20 items）**：直接 human eval、不必 judge
3. **判讀需要 domain expertise**：醫療 / 法律 / 安全的 high-stake 判讀、judge 不該替代 expert
4. **Judge 能力 < test subject**：用 GPT-4o judge 評 o3 輸出、judge 看不懂 reasoning trace

## 何時過時 / 何時不過時

**不會過時的部分**：

- LLM-as-Judge 作為 production eval 主流方法的地位
- 四段式 judge prompt 結構（task / input-output / rubric / format）
- Pairwise vs direct scoring 的取捨
- 三大 bias 分類跟緩解方法
- Production trace → judge → action 的閉環

**會變的部分**：

- 主流 framework（DeepEval / Inspect / Braintrust 等）
- 各 judge model 的具體能力（每代強模型）
- Bias 的具體量化（人類 agreement 數字會隨時間 / 任務變）
- 新興 bias 跟緩解方法

## 小結

LLM-as-Judge 把「in-house benchmark」從理論變成可操作、production AI app 的 eval 事實標準。設計核心：四段式 prompt（task / input-output / rubric / format）、pairwise 或 direct scoring 看場景、三大 bias（position / verbosity / self-preference）要緩解、必須 calibrate。Production trace + judge 形成自動 eval 閉環、是 quality engineering 的標準路徑。不替代 human eval 在高 stake 任務、不替代 rule-based 在可機械驗證任務。

下一步：模組四到此覆蓋從原理（4.0-4.5）、進階主題（4.6-4.11）到 coding agent + production 應用閉環（4.12-4.16：harness / caching / memory / tracing / eval）的完整應用層地圖。可進入 [模組五](/llm/05-discrete-gpu/) 看本地推論硬體、進入 [模組六](/llm/06-security/) 看安全議題（特別是 [6.6 OWASP LLM Top 10 對照](/llm/06-security/owasp-llm-top10-mapping/)、把 production eval 的安全議題對應到企業合規詞彙）、或回 [4.9 benchmarking 章節](/llm/04-applications/benchmarking-and-evaluation/) 對照 standard benchmark 視角。
