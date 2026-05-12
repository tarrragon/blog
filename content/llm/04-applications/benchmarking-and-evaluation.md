---
title: "4.9 Benchmarking 與評估方法論"
date: 2026-05-12
description: "判讀 model card benchmark 數字、做自己工作流的 in-house benchmark、量測本地推論速度的完整方法論"
tags: ["llm", "applications", "benchmark", "evaluation"]
weight: 9
---

讀 model card 看到「MMLU 78.5」「HumanEval 82.3」「SWE-bench 12.6」等數字、要能判讀對自己場景的意義；自己跑本地 LLM、要能量化「tok/s、TTFT、實際品質」；想對比不同 model / 量化等級、要有可重現的 evaluation 方法。本章把「LLM 能力評估」跟「本地推論性能評估」兩條軸拆成可操作的方法論。

## 本章目標

讀完本章後、你應該能：

1. 看 model card benchmark 數字、判讀對自己場景的相關性。
2. 區分 capability benchmark（MMLU 等）跟 performance benchmark（tok/s 等）。
3. 跑 `llama-bench` 量測自己硬體 + 模型的真實速度。
4. 設計 in-house benchmark 評估自己工作流的真實品質。
5. 看到 benchmark 異常數字時、知道可能的陷阱。

## Capability benchmarks：衡量模型「會什麼」

[LLM benchmarks](/llm/knowledge-cards/llm-benchmarks/) 卡片列了主流 benchmark 的覆蓋面。本節展開對寫 code 場景最相關的幾個：

### Coding benchmarks 的演化

| Benchmark              | 任務性質                                  | 適合衡量               | 飽和狀態                 |
| ---------------------- | ----------------------------------------- | ---------------------- | ------------------------ |
| HumanEval              | 寫一個 Python function 通過簡單 unit test | 初級 coding 能力       | 飽和（90%+）             |
| MBPP                   | 同 HumanEval、規模較大                    | 同上                   | 飽和                     |
| HumanEval+             | HumanEval + 更嚴格 test cases             | 排除 edge case 漏寫    | 部分飽和                 |
| BigCodeBench           | 真實 library use（pandas、numpy 等）      | 中級 coding            | 進行中                   |
| LiveCodeBench          | LeetCode 風格 problems、定期更新避免污染  | Algorithm + reasoning  | 進行中                   |
| **SWE-bench**          | 真實 GitHub issue 修復、要看懂 codebase   | 真實 coding agent 能力 | 仍有大空間（前沿 < 60%） |
| **SWE-bench Verified** | SWE-bench 的人工 verify 子集              | 同上、更可靠           | 同上                     |

判讀建議：

1. **看 SWE-bench、別只看 HumanEval**：HumanEval 早飽和、無法區分前沿模型；SWE-bench 仍有大差距、可信度高
2. **HumanEval 90% vs 95% 差異不大**：飽和區間的 noise 大、判斷 coding 能力靠 SWE-bench / 真實任務測
3. **LiveCodeBench 避免污染**：定期出新題、模型訓練 cutoff 後的題目不在 pretrain corpus、更能反映真實能力

### Reasoning benchmarks

| Benchmark   | 任務性質                          | 主要 audience                                                         |
| ----------- | --------------------------------- | --------------------------------------------------------------------- |
| MMLU        | 通用知識多選                      | Pretrain 能力                                                         |
| MMLU-Pro    | MMLU 更困難版本、5 → 10 選 1      | 同上、區分前沿模型                                                    |
| GSM8K       | 小學數學 word problem             | 早期 reasoning                                                        |
| MATH        | 高中 / 競賽數學                   | 中級 reasoning                                                        |
| AIME / GPQA | 競賽數學 / graduate-level science | [Reasoning models](/llm/03-theoretical-foundations/reasoning-models/) |
| ARC-AGI     | 視覺 reasoning puzzle             | General reasoning                                                     |

判讀：

1. **Reasoning model 在 AIME / GPQA 顯著領先 instruct model**：這正是 reasoning model 的優勢區
2. **MMLU 飽和**：85%+ 後差別意義不大、改看 MMLU-Pro
3. **GSM8K 接近飽和**：90%+、改看 MATH / AIME

### Long context benchmarks

| Benchmark                                                      | 任務性質                             | 衡量                          |
| -------------------------------------------------------------- | ------------------------------------ | ----------------------------- |
| [Needle in haystack](/llm/knowledge-cards/needle-in-haystack/) | 抓單一事實                           | Lower bound effective context |
| RULER                                                          | Multi-needle、aggregation、reasoning | 真實 long context 能力        |
| LongBench                                                      | QA、summarization、code 等真實任務   | 全方面 long context           |
| ∞Bench                                                         | 100K+ context tasks                  | 極長 context                  |

判讀：聲稱「128K context」要配 RULER / LongBench 分數才知道實用、見 [4.7 Long context engineering](/llm/04-applications/long-context-engineering/)。

## Performance benchmarks：衡量「跑多快」

跟 capability 並列的另一條軸 — 推論速度：

| 指標                                                         | 定義                     | 影響使用者體感              |
| ------------------------------------------------------------ | ------------------------ | --------------------------- |
| [Tokens per second](/llm/knowledge-cards/tokens-per-second/) | 生成速度（tok/s）        | 連續輸出感受                |
| [TTFT](/llm/knowledge-cards/ttft/)                           | Time to first token      | 「按下 enter 多久才看到字」 |
| Prefill speed                                                | Prompt 處理速度（tok/s） | 長 prompt 的等待時間        |
| Memory footprint                                             | 推論記憶體佔用           | 能不能塞進機器              |
| Energy consumption                                           | 推論電力                 | 長期使用成本                |

### llama-bench：標準工具

llama.cpp 內建 benchmark 工具：

```bash
# 基本測試：純 generation 速度
llama-bench -m model.gguf -p 512 -n 128
# -p 512：prompt 512 token（測 prefill）
# -n 128：generate 128 token（測 decode）

# 不同 context 長度的影響
llama-bench -m model.gguf -p 512,2048,8192 -n 128

# 開 flash attention
llama-bench -m model.gguf -p 512 -n 128 -fa 1

# Speculative decoding 對比
llama-bench -m target.gguf --draft-model drafter.gguf \
            -p 512 -n 128 --speculative-draft 5
```

輸出範例：

```text
| model                |       size |     params | backend    | ngl |   test |              t/s |
| -------------------- | ---------: | ---------: | ---------- | --: | -----: | ---------------: |
| gemma3 31B Q4_K - M  |  18.45 GiB |    31.21 B | Metal      |  99 |  pp512 |    324.21 ± 1.27 |
| gemma3 31B Q4_K - M  |  18.45 GiB |    31.21 B | Metal      |  99 |  tg128 |     28.43 ± 0.31 |
```

讀法：

- `pp512`：prefill 512 token 的 throughput（tok/s）
- `tg128`：generate 128 token 的 throughput（tok/s、即 tok/s）
- `± 0.31`：多次跑的 std deviation、< 5% 是穩定基線

### 推論成本 vs 品質的 trade-off 矩陣

對自己機器跑 `llama-bench` 後、可以建一個矩陣：

```text
                     tok/s 高           tok/s 中           tok/s 低
品質（HumanEval）
     高              [Q4 7B coder]      [Q4 14B coder]    [Q4 30B reasoning]
     中              [Q4 14B instruct]  [Q4 30B instruct]
     低              [Q4 30B base]      [unused]          [unused]
```

對應到實際選型：

- 自動補完（高頻、低品質需求）：左上 tok/s 高的小模型
- 對話（中頻、中品質需求）：中段
- 複雜 reasoning（低頻、高品質需求）：右下大 reasoning model

## In-house benchmark：自己工作流的真實評估

最重要的 benchmark 是「自己真實任務上的表現」、公開 benchmark 是粗略 filter。

### 建立 in-house benchmark 的步驟

```text
1. 蒐集真實案例
   - 從過往工作流挑 30-100 個有代表性的任務
   - 含「容易任務」「中等任務」「困難任務」三類
   - 每個任務記錄 (input prompt, expected output 或評分標準)

2. 定義評分機制
   - Objective（最理想）：unit test、exact match、能機械驗證
   - Semi-objective：rubric 評分、人工或 LLM-as-judge
   - Subjective（最後手段）：人工 A/B 偏好

3. 跑 candidate models
   - 對每個模型、每個任務都跑、記錄輸出
   - 注意推論參數一致（temperature、top-p、max_tokens 一樣）
   - 注意 prompt 一致（chat template、system prompt）

4. 評分
   - Objective：跑 test、算 pass rate
   - Semi-objective：建 rubric、評分
   - Subjective：人工 / LLM 評

5. 看分佈、不只看平均
   - 平均 80% 可能來自「20 題滿分 + 80 題 70%」或「100 題 80%」
   - 看 std、看哪些任務崩、針對性 debug
```

### LLM-as-judge 的注意點

用 LLM（如 GPT-4、Claude）評其他 LLM 是省人力的方法、但有 bias：

1. **Verbosity bias**：judge 傾向給「答得長」的高分、即使內容沒提升
2. **Position bias**：A/B 比較時、judge 對 A、B 位置敏感、要做 swap 平均
3. **Self-preference bias**：judge 模型偏好自己風格的答案
4. **Judge 能力上限**：judge 模型本身不夠強、評不出兩個強模型的差距

緩解：

1. **用結構化 rubric**：給 judge 明確評分標準、不只「哪個好」
2. **多 judge 取共識**：用 2-3 個不同 judge model 各評、取一致 / 平均
3. **Critical task 仍要人工 review**：高 stake 任務不能全靠 LLM-as-judge

## 常見陷阱跟反例

### 陷阱 1：訓練資料污染

模型在 benchmark 題目上「看似強」、實際是 memorization：

判讀訊號：

- benchmark cutoff date 之前的 dataset、新模型分數異常高
- 同模型在「同 dataset 變體（rephrase）」上分數顯著低

緩解：用較新出題的 benchmark（如 LiveCodeBench 定期更新）。

### 陷阱 2：Single benchmark 過擬合

模型廠商針對特定 benchmark fine-tune、benchmark 高但通用能力沒提升：

判讀訊號：

- 在 benchmark A 顯著領先、在 benchmark B（測類似能力）沒差
- 同模型實際使用後評價跟 benchmark 不符

緩解：看多個 benchmark + in-house benchmark。

### 陷阱 3：Prompt sensitivity

同 benchmark 用不同 prompt 格式、score 差幾個百分點：

判讀訊號：

- model card 報的數字跟自己跑差很多
- 同模型不同 prompt template 結果差距大

緩解：自己跑、用一致的 prompt template；report 時明確標 prompt 版本。

### 陷阱 4：Sampling 設定不一致

不同模型用不同 temperature / top-p、結果不可比：

判讀訊號：

- 兩篇 paper 用同 benchmark 報不同數字、推論參數不同

緩解：對 reproduction 用 temperature=0 + greedy decoding 確保一致。

## Benchmark 之間的關係跟導讀路徑

各 benchmark 在不同階段的角色：

```text
研究模型能力（paper 階段）：
  HELM / MT-Bench / Chatbot Arena → 通用能力 baseline
  MMLU / GSM8K / AIME            → reasoning 能力
  HumanEval / SWE-bench           → coding 能力
  RULER / LongBench               → long context

挑選模型（user 階段）：
  Open LLM Leaderboard            → 快速 filter
  MTEB（若 RAG）                  → embedding model
  In-house benchmark              → final 確認

監控模型（production 階段）：
  自己工作流 KPI                  → 真實品質
  A/B test                       → 部署前的決策
  User feedback                  → 持續迭代
```

## 何時過時 / 何時不過時

**不會過時的部分**：

- Benchmark 跟自己任務對齊的必要性
- 訓練污染 / 飽和 / single-task overfit 的陷阱
- LLM-as-judge bias 的存在
- In-house benchmark 是最後 final test
- `llama-bench` 是量測本地推論的標準工具

**會變的部分**：

- 各 benchmark 的飽和狀態跟前沿 score
- 主流 benchmark 的選擇（HumanEval → MBPP → SWE-bench → ...）
- LLM-as-judge model 的偏好（隨 judge model 更新而變）
- 新 benchmark 出現（特別是 reasoning / long-context 領域）

## 小結

Benchmark 評估有兩條軸：capability（會什麼）跟 performance（跑多快）。Capability 要看多個 benchmark + 自己 in-house benchmark、看分佈跟絕對分數同樣重要；performance 用 `llama-bench` 標準工具量自己硬體上的真實數字。Benchmark 常見陷阱包含訓練污染、飽和、single-task overfit、prompt sensitivity；LLM-as-judge 的 bias 要透過 rubric + 多 judge + 人工 review 緩解。實務最重要的是 in-house benchmark — 公開 benchmark 是 filter、自己案例是 final test。

至此模組四覆蓋了 LLM 作為系統元件的設計取捨：RAG、tool use、agent、應用層協議、workflow、production resource planning、long context、embedding model 內部、benchmarking — 寫 code 場景需要的應用層概念已完整。下一步可進入 [模組五 PC 獨立 GPU](/llm/05-discrete-gpu/) 或 [模組六 安全](/llm/06-security/)。
