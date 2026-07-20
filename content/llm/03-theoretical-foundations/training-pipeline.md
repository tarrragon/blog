---
title: "3.4 訓練流程：pre-train → SFT → RLHF"
date: 2026-05-11
description: "LLM 的三階段訓練：預訓練、指令微調、人類反饋強化學習；各階段目標與最新替代方案"
tags: ["llm", "theory", "training"]
weight: 4
---

現代 LLM 的訓練分三個階段：**pre-training**（預訓練）、**supervised fine-tuning（SFT、指令微調）**、**alignment**（傳統用 RLHF、近年也用 DPO 等替代方案）。每個階段目標不同、資料不同、[loss function](/llm/knowledge-cards/loss-function/) 不同。理解這條鏈、能解釋為什麼「Gemma 4 31B base」跟「Gemma 4 31B instruct」是兩個版本、為什麼 fine-tuning 需要慎重、為什麼 RLHF 對對話品質這麼關鍵。

本章從預訓練的 next-token prediction 開始、進入 instruction tuning、最後展開 RLHF 與其替代方案。寫 code 場景的使用者通常不會自己跑這些訓練、但理解流程能解釋模型行為跟版本差異。

## 本章目標

讀完本章後、你應該能：

1. 解釋 [base model](/llm/knowledge-cards/base-model/) 跟 [instruction-tuned model](/llm/knowledge-cards/instruction-tuned/) 的訓練差異。
2. 解釋 RLHF 為什麼影響 LLM 的對話風格。
3. 區分 SFT、RLHF、DPO、LoRA 在訓練流程中的位置。
4. 理解「fine-tuning 為什麼可能讓模型變差」。

## 階段 1：Pre-training（預訓練）

[Pre-training](/llm/knowledge-cards/pre-training/) 的核心目標是「從大量未標註文字學語言模型」、用 [next-token prediction](/llm/knowledge-cards/autoregressive/) 當訓練 objective。

### 流程

1. **資料**：trillion token 級別的網路文字、書籍、code、論文。常見資料集如 Common Crawl、RefinedWeb、The Pile、Stack、Wikipedia。
2. **任務**：「給前 N 個 token、預測第 N+1 個 token」。
3. **Loss**：[cross-entropy](/llm/knowledge-cards/cross-entropy/) loss、衡量模型預測機率分佈跟實際下一個 token（one-hot）的差距、由 [backpropagation](/llm/knowledge-cards/backpropagation/) 算出 [gradient](/llm/knowledge-cards/gradient/) 更新權重。詳細展開見 [2.1 機率與資訊論](/llm/02-math-foundations/probability-and-information/)。
4. **訓練量**：數十億 GPU-hour、數百到數萬個 GPU 並行、訓練數週到數月。
5. **結果**：[base model](/llm/knowledge-cards/base-model/)、會做文字接龍、但對話能力有限。

### 為什麼 next-token prediction 這麼有效

「給前文預測下一個 token」看起來是簡單任務、但要做好需要：

- 理解語法、文法。
- 理解語意、世界知識。
- 理解 reasoning（推理鏈中的下一步是 token、模型要會推理才能準確預測）。
- 理解 multi-step task（複雜程式碼跟複雜文章的下一個 token 也是 next-token problem）。

LLM 的「智能」很大程度是 next-token prediction 在大資料上的 emergent property（湧現特性）。

### 預訓練成本

訓練前沿 LLM 的成本：

| 模型         | 估計訓練成本（美元） | 訓練資料量  |
| ------------ | -------------------- | ----------- |
| GPT-3 (2020) | ~$5M                 | 300B tokens |
| Llama 3 70B  | ~$30M                | 15T tokens  |
| GPT-4 (估)   | $100M+               | 不公開      |
| 訓練前沿模型 | 數億美元             | 10T+ tokens |

預訓練是 LLM 訓練成本的 95%+。後續 fine-tuning 跟 RLHF 的成本是預訓練的零頭。

## 階段 2：Supervised Fine-Tuning（SFT、指令微調）

[SFT](/llm/knowledge-cards/sft/) 的核心目標是「在 base model 上、用「指令-回答」對資料微調、讓模型會跟著指令走」。

### 流程

1. **資料**：人類標註或 AI 生成的「prompt - response」對、數萬到數百萬個樣本。
2. **任務**：跟 pre-training 同樣是 next-token prediction、但只對 response 部分算 loss（prompt 部分不算）。
3. **Loss**：cross-entropy、只在 response token 上計算。
4. **訓練量**：相對小、幾天到一週、單機可訓。
5. **結果**：[instruction-tuned model](/llm/knowledge-cards/instruction-tuned/)、會跟著 prompt 走、回答使用者問題。

### SFT 的關鍵性

Base model 雖然有大量知識、但「問問題、給答案」的交互模式對它不自然。SFT 後同一個模型行為大改：

- Base model：問「寫一個 Python fibonacci」可能得到「寫一個 Python fibonacci。寫一個 JavaScript fibonacci。寫一個...」（純文字接龍）。
- Instruction-tuned：問同樣問題、得到實際 function。

寫 code 場景的所有模型都是 instruction-tuned 後的版本。Coding-tuned（如 Qwen3-Coder）是 SFT 階段大量加入 code 對話資料的特化版本。

### Instruction Tuning 的資料來源

- **Human-annotated**：人類寫 prompt + 回答、品質高但成本高。Anthropic、OpenAI、Meta 都有自己的標註團隊。
- **AI-generated**：用更強的 model（如 GPT-4）生成 prompt + 回答、品質依賴 source model。Alpaca、Vicuna 是早期例子。
- **Synthetic**：規則生成 + LLM 改寫。Magpie、Self-Instruct 等方法。

主流模型多半混合上述三種來源。

## 階段 3：Alignment（對齊）

Alignment 的核心目標是「進一步調整模型、讓回答符合「helpful、harmless、honest」三個維度」。SFT 後的模型可能說出有害內容、誇大事實、給平庸答案；alignment 階段解決這些問題。

### RLHF：Reinforcement Learning from Human Feedback

[RLHF](/llm/knowledge-cards/rlhf/) 是 alignment 的經典方法（Ouyang et al., 2022、InstructGPT 論文）、三步驟：

#### Step 1：Reward Model

1. 收集 prompt、用模型生成多個 response。
2. 人類對 response 做 pairwise 排序（「A 比 B 好」）。
3. 訓練一個 reward model、輸入 (prompt, response)、輸出一個分數、最大化「人類偏好高的 response 拿高分」。

#### Step 2：用 PPO 最佳化模型

1. Policy = 當前的 LLM（在 RL 框架下、模型輸出的 token 分佈被視為「策略」、所以稱為 policy）。
2. 用 RL（通常用 PPO 演算法、Proximal Policy Optimization、一種限制每步參數更新幅度的 RL 演算法、訓練比較穩）最佳化 policy、讓 reward model 給的分數最大化。
3. 加 KL constraint：policy 不能偏離 base SFT model 太遠（用 [KL divergence](/llm/knowledge-cards/kl-divergence/)、推導見 [2.1 機率與資訊論](/llm/02-math-foundations/probability-and-information/)）、避免 reward hacking。

#### Step 3：迭代

可以再收集人類反饋、再訓 reward model、再 RL；多輪迭代。

RLHF 後的模型在 helpfulness、harmlessness 上明顯提升、但流程複雜、訓練不穩、reward model 易被 hack。

### DPO：Direct Preference Optimization

[DPO](/llm/knowledge-cards/dpo/)（Rafailov et al., 2023）是 RLHF 的替代方案、跳過 reward model、直接用人類偏好資料 fine-tune policy：

```text
loss = -log(σ(β × (log π(y_w|x)/π_ref(y_w|x) - log π(y_l|x)/π_ref(y_l|x))))
```

其中：

- y_w：人類偏好的 response。
- y_l：人類較不喜歡的 response。
- π：當前 policy。
- π_ref：reference model（通常 SFT model）。

公式的直觀解讀：對每對 (好回答, 差回答)、拉高 π 給好回答的相對機率（比 π_ref 高）、壓低 π 給差回答的相對機率（比 π_ref 低）、β 控制偏離 π_ref 的力度。σ 是 sigmoid、把整體 score 壓到 (0, 1) 區間。

DPO 比 RLHF 簡單、不用訓 reward model、不用 RL 演算法、訓練穩定、在「離線偏好資料量充足 + 偏好相對穩定」的場景是 2024 ~ 2026 主流選擇。Llama 3、Gemma 4 等都用 DPO 或變體。

### 其他替代方案

| 方法  | 特性                                                                 |
| ----- | -------------------------------------------------------------------- |
| RLAIF | 把 RLHF 中的「human feedback」換成「AI feedback」、由更強 model 評分 |
| ORPO  | 把 SFT 跟 alignment 合併成一步、簡化流程                             |
| KTO   | 用 binary preference（好 / 不好）而非 pairwise                       |
| RPO   | RLHF + DPO 混合方案                                                  |

主流前沿 LLM 用 SFT + DPO（或變體）的組合；資料量足夠 + 偏好穩定時 DPO 較佳、需要 online 人類反饋或 reward shaping（複雜環境互動、多輪偏好調整）的場景下 PPO 仍有實際空間、特別是 reasoning model（DeepSeek-R1 等）的後訓練階段。

## Fine-tuning：在 instruction-tuned model 上做特化

「Fine-tuning」這個詞在 LLM 社群有兩層意思：

1. **SFT 階段**（前面提的）：base model → instruction-tuned model。
2. **下游 fine-tuning**：使用者在 instruction-tuned model 上、用自己的資料再 fine-tune、做特定領域特化。

下游 fine-tuning 的常見方法：

### Full Fine-tuning

更新模型所有參數。需要大量 GPU、Gemma 4 31B 全參數 fine-tune 要 8 × H100 起。品質好、但成本高、容易過擬合小資料。

### LoRA（Low-Rank Adaptation）

[LoRA](/llm/knowledge-cards/lora/)（Hu et al., 2021）的核心想法是「凍結 base model 權重、只訓練一組小的 adapter 矩陣」：

```text
W_new = W_frozen + α × A @ B
```

其中 A、B 是低秩矩陣（rank=4 ~ 64）、總參數遠少於 full fine-tune。

優點：

- 記憶體佔用 1/10 ~ 1/100。
- 訓練快得多。
- 多個 LoRA adapter 可以共用同一個 base model、推論時切換。
- 不會破壞 base model（凍結）。

LoRA 是 consumer 級硬體做 fine-tuning 的主流選擇。32GB Mac + MLX 可以跑 7B / 14B 模型的 LoRA fine-tuning。

LoRA 何時不適用 / 必須走 full fine-tune：

- **大幅行為改變**：要把模型從通用 chat 轉成完全不同的人設 / 風格 / 領域。LoRA rank 容量有限（rank=4 ~ 64 對應幾百萬 ~ 幾千萬參數）、裝不下整體行為的大幅改寫；rank 拉到 256+ 後 LoRA 的記憶體優勢消失。
- **跨 domain transfer**：base model 是 general English、想 fine-tune 到醫學 / 法律等需要重學 vocab 跟結構的 domain。LoRA 只調整現有 layer 的偏移、難以從零學新 domain；通常要先做 continued pre-training（full fine-tune）再 LoRA。
- **跟量化推論的相容性**：base model 用 Q4 推論時、要先 dequantize 才能加上 LoRA delta、會導致 latency / memory 增加；production 場景常用 QLoRA + 在推論時 merge 回 base、避免每次推論都拆兩段。

### QLoRA

[QLoRA](/llm/knowledge-cards/qlora/) = Quantized LoRA、把 base model 量化到 4-bit、再做 LoRA。記憶體進一步降低、犧牲少量品質。

### 為什麼 fine-tuning 可能讓模型變差

下游 fine-tuning 對寫 code 場景的多數使用者價值有限、原因：

1. **過擬合**：fine-tune 資料量小、模型可能學到 spurious pattern、在 fine-tune 領域外能力下降。
2. **Catastrophic forgetting**：學新資料時忘記舊知識、原本會的東西變差。
3. **資料品質決定上限**：fine-tune 資料品質低、模型學到低品質回答。
4. **Alignment 退化**：fine-tune 可能破壞 RLHF / DPO 階段建立的「helpful、harmless」性質。

寫 code 場景優先用 instruction-tuned 通用模型（Gemma 4、Qwen3-Coder 等）、需要特化再評估 [RAG](/llm/knowledge-cards/rag/) 或 prompt engineering、最後才考慮 fine-tuning。三條路的取捨判讀見 [4.1 RAG 原理](/llm/04-applications/rag-principles/)。

## In-Context Learning：fine-tuning 的替代品

[In-context learning](/llm/knowledge-cards/in-context-learning/)（ICL）的核心想法是「不更新模型權重、只在 prompt 中給範例、讓模型 generalize」。

- **Zero-shot**：直接給任務描述、不給範例。
- **Few-shot**：給幾個 input-output 範例、再給新 input。
- **Chain-of-thought**：要求模型把推理過程寫出來、再給答案。

GPT-3 paper 顯示大模型有強 ICL 能力、不用 fine-tune 就能做新任務。現代 LLM 進一步強化 ICL、加上 long context、[agent](/llm/knowledge-cards/agent/) loop、[function calling](/llm/knowledge-cards/function-calling/) 等技術、覆蓋大部分原本需要 fine-tune 的場景。

實務啟示：「想做新任務、先試 prompt engineering、不夠再試 RAG、最後才考慮 fine-tuning」。fine-tuning 是最重的投資、適合放在最後驗證、prompt engineering 跟 RAG 跑完仍不夠才動。

## 訓練資料污染（Data Contamination）

訓練資料污染指「benchmark 的測試集出現在預訓練資料中」、模型「記住答案」而非真正能解問題。

問題：

- 公開 benchmark（SWE-bench、MMLU 等）的測試題常出現在 GitHub / 論壇、進入預訓練資料。
- 模型在這些 benchmark 上分數可能高估真實能力。

解決：

- **SWE-bench Verified**：OpenAI 篩選過、相對乾淨的子集。
- **HELM**：Stanford 的 holistic 評估、含污染檢測。
- **新 benchmark**：每隔一段時間出新 benchmark、用尚未被 LLM「看過」的資料。
- **自己跑 benchmark**：用自己工作流的真實任務評估、繞過所有污染問題。

詳見 [SWE-bench 卡片](/llm/knowledge-cards/swe-bench/) 跟 [模組零 0.6 判讀框架](/llm/00-foundations/info-judgment-frames/) 的框架二（量化宣稱三變數）。

## 下一章

下一章：[3.5 sampling 與 decoding 策略](/llm/03-theoretical-foundations/sampling-and-decoding/)、模型輸出後怎麼挑下一個 token。
