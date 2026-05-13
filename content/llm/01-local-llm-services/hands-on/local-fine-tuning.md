---
title: "Hands-on：用 QLoRA 在本機 fine-tune coding 模型"
date: 2026-05-12
description: "Apple Silicon Mac / PC 獨立 GPU 上跑 QLoRA fine-tune 的完整流程：環境、資料、訓練、evaluation、合併、部署到 Ollama"
tags: ["llm", "hands-on", "fine-tuning", "qlora", "lora"]
weight: 7
---

[QLoRA](/llm/knowledge-cards/qlora/)（4-bit 量化 base model + [LoRA](/llm/knowledge-cards/lora/) adapter）讓消費級硬體也能 fine-tune 7B-32B 模型、是 2026/5 本地 fine-tuning 的主流方法。「在本機 fine-tune 一個小 coding 模型懂我 codebase 的慣例」是個人 dev 的合理目標、特別是在「本地 RAG 不夠精準、prompt engineering 已到天花板」的場景。本篇用 QLoRA 把 fine-tuning 的最短路徑走完：環境準備、資料蒐集、訓練、evaluation、合併權重、部署到 Ollama / llama.cpp 配 VS Code Continue.dev。

本篇 framing 是「**真實會跑、不只跑 demo**」、所以包含：硬體預算估算、catastrophic forgetting 防護、evaluation 確認真的有提升、回退方案（fine-tune 失敗時怎麼辦）。

> **驗證日期**：2026-05-12
> **環境**：M4 Max 64GB + Hugging Face PEFT 0.13、或 5090 24GB + bitsandbytes
> **目標模型**：Qwen3-Coder-7B-Instruct（fine-tune 後輸出符合自己 codebase 慣例的 code）

## 為什麼這個議題重要

寫 code 場景的常見 fine-tune 動機：

1. **私有 codebase 慣例**：自家專案有特殊 naming、特殊 design pattern、prompt engineering 拉不到、希望模型「自然知道」
2. **特殊框架 / library**：用 obscure 的內部 framework、通用模型沒看過、補完品質差
3. **特定文檔風格**：commit message、PR description、code comment 有 team-specific 格式
4. **Reduce RAG dependence**：把高頻 knowledge 編進模型權重、減少每次 query 都要 retrieve

但**不該 fine-tune**的情境（先排除）：

1. **新增世界知識**：fine-tune 不擅長加新事實、用 [RAG](/llm/04-applications/rag-principles/) 即可
2. **複雜 reasoning 能力**：fine-tune 一般不會讓模型變更會 reason、reasoning 來自 pre-training + RL
3. **改善通用對話品質**：通用對話品質取決於 RLHF、fine-tune 多半會 [catastrophic forgetting](/llm/knowledge-cards/catastrophic-forgetting/)
4. **資料太少（< 500 對）**：fine-tune 收益低、不如優化 prompt + RAG

## 整體流程

```text
1. 硬體預算估算       → 知道能跑哪個 size 的 base model
2. 蒐集 fine-tune 資料 → 50-5000 對 (prompt, response)
3. 環境準備           → Python + bitsandbytes / PEFT / transformers
4. 跑 QLoRA 訓練      → 1-3 epochs、看 loss 趨勢
5. Evaluation         → 在 held-out set + 通用 benchmark 都跑
6. Merge LoRA → base  → 得到合併權重 .safetensors
7. Convert → GGUF     → 用 llama.cpp convert 工具
8. Deploy 到 Ollama   → ollama create my-coder -f Modelfile
9. 配 Continue.dev    → config.json 加新 provider
```

## Step 1：硬體預算估算

QLoRA 訓練的記憶體需求（粗略估算）：

```text
記憶體 ≈ N (B 參數) × 0.6 GB     ← 訓練時
        ≈ N (B 參數) × 0.3 GB     ← 推論（4-bit）

Apple Silicon Mac：
  M4 Pro 24GB → 訓 7B 可、訓 14B 緊
  M4 Pro 36GB → 訓 7B 寬鬆、訓 14B 可
  M4 Max 64GB+ → 訓 30B 可、推論 70B 可

PC 獨立 GPU：
  RTX 4090 / 5090 24GB → 訓 7B 寬鬆、訓 14B / 30B with `--n-cpu-moe` 可
  RTX A6000 48GB → 訓 30-32B 寬鬆
```

> **事實查核註**：Apple Silicon 上的 QLoRA 支援度跟 bitsandbytes / MLX 工具鏈版本相關、2026/5 主流是用 MLX 自己的 LoRA 實作（`mlx-lm`）、CUDA 路線用 transformers + bitsandbytes + PEFT。具體支援度以對應 release 為準。

本篇假設 fine-tune Qwen3-Coder-7B、所以 24GB+ Mac 或 16GB+ GPU 都能跑。

## Step 2：蒐集 fine-tune 資料

最關鍵的 step。資料品質決定 fine-tune 成敗。

### 資料格式（典型 SFT format）

```json
[
  {
    "instruction": "用我們 codebase 的慣例寫一個 REST endpoint 處理 user signup",
    "input": "需求：accept email + password、回 JWT",
    "output": "// 完整符合我們慣例的 code..."
  },
  ...
]
```

或對話格式（ChatML）：

```json
[
  {
    "messages": [
      {"role": "system", "content": "你是我們 codebase 的 coding assistant"},
      {"role": "user", "content": "..."},
      {"role": "assistant", "content": "..."}
    ]
  }
]
```

### 資料來源

| 來源                        | 取得方式                                      | 品質                 |
| --------------------------- | --------------------------------------------- | -------------------- |
| 過往 commit 的「good code」 | 從 main branch 抽函式 + git log message       | 中（人工挑）         |
| Code review 通過的 PR diff  | 從 GitHub API 抽 merged PR                    | 高                   |
| 內部 wiki 跟 design docs    | 轉成 Q&A 對                                   | 中                   |
| Synthetic data：用大模型生  | 給雲端旗艦 prompt「以這個 codebase 風格寫 X」 | 中（要 review）      |
| Pair programming 紀錄       | 自己跟 IDE 互動的 log                         | 高（最貼近真實使用） |

### 資料量門檻

| 資料量      | 預期效果                                   |
| ----------- | ------------------------------------------ |
| < 50 對     | 通常無感、不如優化 prompt + RAG            |
| 50-500 對   | 開始有 in-domain 效果、但易 forgetting     |
| 500-5000 對 | 顯著效果、QLoRA fine-tune 甜蜜點           |
| 5000+ 對    | 邊際收益遞減、開始接近 full fine-tune 效果 |

### 資料 mixing（防 [catastrophic forgetting](/llm/knowledge-cards/catastrophic-forgetting/)）

訓練 batch 內 mix 通用資料、避免 fine-tune 把通用能力洗掉：

```text
80% in-domain data（你的 codebase 範例）
20% 通用 instruction data（如 Alpaca、ShareGPT subset）
```

通用 data 可從 Hugging Face datasets 抓（如 `tatsu-lab/alpaca`、`teknium/OpenHermes-2.5`）。

## Step 3：環境準備

### Apple Silicon Mac（用 MLX）

```bash
# MLX 是 Apple 的 ML framework、原生支援 Apple Silicon
pip install mlx mlx-lm

# 或用 conda（推薦）
conda create -n llm-ft python=3.11
conda activate llm-ft
pip install mlx-lm
```

### PC（CUDA + transformers + bitsandbytes）

```bash
# 安裝 CUDA 12.x（依 GPU 驅動）

# Python 套件
pip install torch transformers peft bitsandbytes accelerate datasets trl
```

## Step 4：跑 QLoRA 訓練

### Apple Silicon（MLX）方式

```bash
# 把 base model 下載到本機
huggingface-cli download Qwen/Qwen3-Coder-7B-Instruct \
  --local-dir ~/models/qwen3-coder-7b

# 把資料整理成 JSONL（一行一筆）
# data/train.jsonl、data/valid.jsonl

# 跑 LoRA fine-tune（MLX 內建 4-bit）
mlx_lm.lora \
  --train \
  --model ~/models/qwen3-coder-7b \
  --data data/ \
  --batch-size 4 \
  --lora-layers 16 \
  --iters 1000 \
  --learning-rate 1e-4 \
  --steps-per-eval 100 \
  --adapter-path ./adapters
```

### PC（CUDA）方式

```python
# train.py（簡化版）
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer
from datasets import load_dataset

# 4-bit 量化載入 base
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype="bfloat16",
)
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen3-Coder-7B-Instruct",
    quantization_config=bnb_config,
)

# LoRA 配置
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora_config)

# 資料
dataset = load_dataset("json", data_files="data/train.jsonl")

# 訓練
training_args = TrainingArguments(
    output_dir="./checkpoints",
    learning_rate=1e-4,
    num_train_epochs=2,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    save_steps=200,
    logging_steps=20,
    optim="paged_adamw_8bit",
    bf16=True,
)
trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    max_seq_length=2048,
)
trainer.train()
trainer.save_model("./adapters")
```

關鍵超參數的判讀邏輯：

| 參數                          | 預設               | 怎麼調                                                            |
| ----------------------------- | ------------------ | ----------------------------------------------------------------- |
| `r`（LoRA rank）              | 16                 | 小 dataset（< 1000 對）可降到 8、大 dataset 升到 32 / 64          |
| `lora_alpha`                  | 32（通常 = 2 × r） | 增大會放大 LoRA 影響、太大易 catastrophic forgetting              |
| `target_modules`              | q_proj, v_proj     | 8B+ 模型可加 k_proj + o_proj 提品質、加 ffn 是進階                |
| `lora_dropout`                | 0.05               | dataset 小時加大（0.1）防 overfit                                 |
| `num_train_epochs`            | 2                  | 1-3 是常見範圍、看 validation loss 何時開始升                     |
| `per_device_train_batch_size` | 4                  | 視 GPU 記憶體；不夠用 `gradient_accumulation_steps` 補            |
| `learning_rate`               | 1e-4               | LoRA 適合較大 lr（vs full fine-tune 的 1e-5）、初值可 1e-4 ~ 5e-4 |

### 看 training loss 趨勢

訓練過程中、loss 應該：

```text
Initial：~2.5（cross-entropy on next-token）
1/4 訓練：降到 ~1.5
1/2 訓練：降到 ~1.0
3/4 訓練：降到 ~0.7
末段：穩定在 ~0.5

警示訊號：
- Loss 不降（≈ 2.0+ 持平） → lr 太小、或資料品質差、或 base 跟資料分佈完全不合
- Loss 降到 < 0.1 → over-fit、validation loss 應該已升、stop training
- Loss 出 NaN → lr 太大、降 lr 重來
```

## Step 5：Evaluation

訓練完不能只看 training loss、要實測：

### 1. Held-out test set（你自己的 in-domain 資料）

```bash
# 拿 valid.jsonl 跑、看模型輸出 vs expected
# 用 BLEU / ROUGE / 或 LLM-as-judge 評分
mlx_lm.generate \
  --model ~/models/qwen3-coder-7b \
  --adapter ./adapters \
  --prompt "<test prompt from valid.jsonl>"
```

### 2. 通用 benchmark（防 catastrophic forgetting）

跑通用 HumanEval、看分數有沒有崩：

```bash
# 用 lm-evaluation-harness
git clone https://github.com/EleutherAI/lm-evaluation-harness
cd lm-evaluation-harness
pip install -e .

lm_eval --model hf \
  --model_args pretrained=~/models/qwen3-coder-7b,peft=./adapters \
  --tasks humaneval \
  --batch_size 8
```

判讀：

- HumanEval 從 75% → 75%：通用能力保留、in-domain 提升、成功
- HumanEval 從 75% → 55%：catastrophic forgetting、要重新 fine-tune（用 LoRA + 資料 mixing 加強）

### 3. 自己工作流測試（最重要）

實際在 Continue.dev 用幾天、看：

- In-domain 任務輸出是否確實貼近 codebase 慣例
- 通用 coding 任務（如「寫一個 helper function」）是否仍 OK
- 對話流暢度有沒有變差
- 出現怪行為的頻率

## Step 6：合併 LoRA 跟 base model

訓練完得到 adapter（小檔、< 100MB）。要用於日常推論、通常 merge 進 base：

```bash
# MLX 方式
mlx_lm.fuse \
  --model ~/models/qwen3-coder-7b \
  --adapter-path ./adapters \
  --save-path ~/models/qwen3-coder-7b-mycodebase

# PEFT 方式
python -c "
from peft import AutoPeftModelForCausalLM
import torch

model = AutoPeftModelForCausalLM.from_pretrained('./adapters', torch_dtype=torch.bfloat16)
merged = model.merge_and_unload()
merged.save_pretrained('./merged-model')
"
```

## Step 7：Convert 成 GGUF（給 Ollama / llama.cpp 用）

```bash
# 安裝 llama.cpp
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
pip install -r requirements.txt

# Convert HF → GGUF
python convert_hf_to_gguf.py ~/models/qwen3-coder-7b-mycodebase \
  --outfile ~/models/qwen3-coder-7b-mycodebase.gguf

# 量化（可選、Q4_K_M 是甜蜜點）
./llama-quantize \
  ~/models/qwen3-coder-7b-mycodebase.gguf \
  ~/models/qwen3-coder-7b-mycodebase-Q4_K_M.gguf \
  Q4_K_M
```

## Step 8：Deploy 到 Ollama

```bash
# 寫 Modelfile
cat > ~/models/Modelfile-mycodebase <<EOF
FROM ~/models/qwen3-coder-7b-mycodebase-Q4_K_M.gguf

TEMPLATE """<|im_start|>system
{{ .System }}<|im_end|>
<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
"""

PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER num_ctx 32768
EOF

# 註冊到 Ollama
ollama create mycodebase-coder -f ~/models/Modelfile-mycodebase

# 測試
ollama run mycodebase-coder "寫一個 user signup endpoint"
```

## Step 9：配 Continue.dev

```json
// ~/.continue/config.json 加：
{
  "models": [
    {
      "title": "My Codebase Coder",
      "provider": "ollama",
      "model": "mycodebase-coder",
      "apiBase": "http://localhost:11434"
    },
    // ... 既有 models
  ]
}
```

VS Code restart 後、Continue panel 下拉就能切換。

## 失敗模式跟回退

### 失敗 1：訓練 loss 不降

可能原因：

- 資料品質差 → 人工 review 50 對、看 instruction-response 是否真有對應
- 資料 token 太短 → 多數 < 100 token、模型學不到複雜 pattern
- lr 太小 → 試 lr 5e-4

回退：把資料品質提升、或放棄 fine-tune 用 RAG。

### 失敗 2：HumanEval 大幅下降（catastrophic forgetting）

緩解：

- 加入 20% 通用 data mixing、重訓
- 降低 epochs（從 3 → 1）
- 降低 LoRA rank（從 16 → 8）

### 失敗 3：In-domain test 進步、但日常用感覺沒變

可能原因：

- Test set 跟真實工作流分佈不符
- Prompt template 在訓練跟推論不一致

緩解：實際在 Continue.dev 跑 1-2 週、看真實效果再判斷。

### 失敗 4：訓練爆 OOM

緩解：

- 降 batch size（4 → 2 → 1）
- 加 gradient_accumulation_steps（保持 effective batch size）
- 用更小的 LoRA rank
- 換更小的 base model（7B → 3B）

## 何時不該繼續 fine-tune 路線

跑完一次 fine-tune 評估後、若：

1. **In-domain 提升 < 10%**：相對成本（時間 + 維護）不划算、用 RAG
2. **Catastrophic forgetting > 10%**：跟其他能力 trade-off 不值得
3. **資料量不夠（< 500 對）**：RAG 比 fine-tune 更有效
4. **工作流變化快（codebase 慣例每月變）**：fine-tune 過時得快、RAG 更靈活

## 跟其他模組的關係

- 原理層的 LoRA 設計見 [LoRA 卡片](/llm/knowledge-cards/lora/) 跟 [QLoRA 卡片](/llm/knowledge-cards/qlora/)
- Catastrophic forgetting 跟整體 alignment 議題見 [3.4 訓練流程](/llm/03-theoretical-foundations/training-pipeline/)
- Fine-tune 後的模型評估見 [4.14 Benchmarking](/llm/04-applications/benchmarking-and-evaluation/)
- 隱私 / 供應鏈面：fine-tune 後 model 怎麼分享（給 team / 上 HuggingFace）見 [6.0 模型供應鏈](/llm/06-security/model-supply-chain-trust/)
- 跟 RAG 的取捨見 [4.1 RAG 原理](/llm/04-applications/rag-principles/) 的「RAG vs Fine-tuning vs Long Context」段

## 小結

QLoRA 在消費級硬體上 fine-tune 30B+ 模型已經可行、是「教模型懂自己 codebase 慣例」的最短路徑。流程：估算硬體 → 蒐集資料（500-5000 對是甜蜜點）→ 跑 QLoRA → evaluate（in-domain + 通用 benchmark）→ merge → 轉 GGUF → 部署 Ollama。最大失敗模式是 catastrophic forgetting、用 LoRA + 資料 mixing + 低 epochs 緩解。Fine-tune 不能取代 RAG、是補 RAG 不足的特殊情境工具。
