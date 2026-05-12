---
title: "Knowledge Cards"
tags: ["前置知識卡片", "Knowledge Cards", "LLM"]
date: 2026-05-11
description: "用原子化卡片整理本地 LLM 寫 code 場景所需的概念詞彙"
weight: -1
---

前置知識卡片的目標是把本地 LLM 章節會用到的高密度術語拆成可獨立閱讀的概念。模組零的心智模型文章會引用 token、自回歸、KV cache、量化、speculative decoding、MTP、MLX、推論伺服器、OpenAI 相容 API 等詞彙；這些詞彙背後都有明確的角色、訊號與設計責任。

這個模組先建立共同語言。每張卡片只處理一個概念，並用「概念位置、可觀察訊號、接近真實的例子、設計責任」說明它在本地 LLM 生態中的角色。讀者可以從章節中遇到陌生詞時點進來補完，回到原章節仍能接續閱讀。

## 卡片分類

### 模型輸出機制

| 卡片                                                         | 核心問題                                |
| ------------------------------------------------------------ | --------------------------------------- |
| [Token](/llm/knowledge-cards/token/)                         | 模型如何把文字切成可運算單位            |
| [Autoregressive](/llm/knowledge-cards/autoregressive/)       | 模型如何一次生一個 token                |
| [Tokens Per Second](/llm/knowledge-cards/tokens-per-second/) | 生字速度如何被量化                      |
| [TTFT](/llm/knowledge-cards/ttft/)                           | 從送出 prompt 到第一個 token 的等待時間 |
| [Context Window](/llm/knowledge-cards/context-window/)       | 模型一次能處理多少 token                |
| [Prefill](/llm/knowledge-cards/prefill/)                     | prompt 首次處理時的計算階段             |
| [KV Cache](/llm/knowledge-cards/kv-cache/)                   | 已處理過的 token 如何避免重算           |

### 模型權重與量化

| 卡片                                                               | 核心問題                                |
| ------------------------------------------------------------------ | --------------------------------------- |
| [Quantization](/llm/knowledge-cards/quantization/)                 | 模型權重如何用較少 bits 表示            |
| [GGUF](/llm/knowledge-cards/gguf/)                                 | llama.cpp 系統如何打包模型權重          |
| [Instruction-Tuned Model](/llm/knowledge-cards/instruction-tuned/) | 模型如何跟著 prompt 走                  |
| [Base Model](/llm/knowledge-cards/base-model/)                     | 未微調的原始模型適合什麼用途            |
| [Embedding Model](/llm/knowledge-cards/embedding-model/)           | 文字如何轉成可比對的向量                |
| [Model Card](/llm/knowledge-cards/model-card/)                     | 判讀模型來源、訓練資料、授權的 metadata |

### 推論加速技巧

| 卡片                                                               | 核心問題                          |
| ------------------------------------------------------------------ | --------------------------------- |
| [Speculative Decoding](/llm/knowledge-cards/speculative-decoding/) | 怎麼一次生多個 token              |
| [Multi-Token Prediction](/llm/knowledge-cards/mtp/)                | speculative decoding 的工程化實作 |
| [Drafter Model](/llm/knowledge-cards/drafter-model/)               | 預測未來 token 的小模型           |

### 推論基礎建設

| 卡片                                                           | 核心問題                           |
| -------------------------------------------------------------- | ---------------------------------- |
| [Inference Server](/llm/knowledge-cards/inference-server/)     | 載入模型、提供 API 的常駐 process  |
| [OpenAI 相容 API](/llm/knowledge-cards/openai-compatible-api/) | 介面層跟伺服器層之間的標準介面     |
| [Model Tag](/llm/knowledge-cards/model-tag/)                   | 推論伺服器如何指名某個模型版本     |
| [MLX](/llm/knowledge-cards/mlx/)                               | Apple Silicon 的數值運算 framework |

### macOS 與 shell 基礎

讓對 Mac 操作不熟的讀者也能跟上本地 LLM 章節。這組卡片不算 LLM 領域知識、但本地 LLM 章節必然會碰到。

| 卡片                                                                 | 核心問題                                       |
| -------------------------------------------------------------------- | ---------------------------------------------- |
| [Homebrew](/llm/knowledge-cards/homebrew/)                           | macOS 上 CLI 工具的標準安裝入口                |
| [launchd Service](/llm/knowledge-cards/launchd-service/)             | 讓 Ollama 等服務開機自動啟動的 macOS 機制      |
| [Shell 背景 Process](/llm/knowledge-cards/shell-background-process/) | 前景 vs 背景、`&`、`Ctrl+C`、找 process 的方法 |
| [Port 與 Localhost](/llm/knowledge-cards/port-and-localhost/)        | server 暴露在哪個地址、誰能連進來              |

### 硬體與架構

| 卡片                                                                | 核心問題                                       |
| ------------------------------------------------------------------- | ---------------------------------------------- |
| [Memory Bandwidth](/llm/knowledge-cards/memory-bandwidth/)          | 為什麼記憶體頻寬決定生字速度                   |
| [Unified Memory Architecture](/llm/knowledge-cards/unified-memory/) | Apple Silicon 怎麼讓模型用滿大記憶體           |
| [VRAM](/llm/knowledge-cards/vram/)                                  | 獨立 GPU 場景的顯卡記憶體、跟系統 RAM 分層     |
| [PCIe](/llm/knowledge-cards/pcie/)                                  | GPU 跟主機板之間的高速序列匯流排               |
| [NVLink](/llm/knowledge-cards/nvlink/)                              | NVIDIA 多卡互連、跟 PCIe 比的卡間頻寬優勢      |
| [GPU Compute Backend](/llm/knowledge-cards/gpu-compute-backend/)    | CUDA / ROCm / Vulkan / Metal / SYCL 對照       |
| [Transformer](/llm/knowledge-cards/transformer/)                    | 寫 code 用的 LLM 是哪種神經網路                |
| [Attention](/llm/knowledge-cards/attention/)                        | Transformer 內部讓 token 互相加權平均的機制    |
| [Self-Attention](/llm/knowledge-cards/self-attention/)              | Q/K/V 都來自同一序列的 attention、LLM 標誌     |
| [Multi-Head Attention](/llm/knowledge-cards/multi-head-attention/)  | 把 attention 切成多個 head 並行、MHA/GQA/MLA   |
| [Causal Mask](/llm/knowledge-cards/causal-mask/)                    | 擋掉「未來位置」的遮罩、decoder-only 的標誌    |
| [RoPE](/llm/knowledge-cards/rope/)                                  | 用旋轉矩陣編碼位置、Llama / Gemma / Qwen 主流  |
| [Flash Attention](/llm/knowledge-cards/flash-attention/)            | Attention 計算的記憶體友善實作                 |
| [FFN](/llm/knowledge-cards/ffn/)                                    | Transformer block 內部的兩層 linear、參數大頭  |
| [Activation Function](/llm/knowledge-cards/activation-function/)    | FFN 內的非線性、讓深度網路真的「深」起來       |
| [Layer Normalization](/llm/knowledge-cards/layer-normalization/)    | 對 hidden state 正規化、穩定深層訓練           |
| [Residual Connection](/llm/knowledge-cards/residual-connection/)    | layer 輸入直接加到輸出、讓 gradient 能回流深層 |
| [Embedding Layer](/llm/knowledge-cards/embedding-layer/)            | Transformer 第一層、把 token ID 轉成向量       |
| [Forward Pass](/llm/knowledge-cards/forward-pass/)                  | input 流經所有 layer 的單向計算流程            |
| [Diffusion](/llm/knowledge-cards/diffusion/)                        | 產圖用的是哪種神經網路                         |

### 線性代數基礎

| 卡片                                                                 | 核心問題                                         |
| -------------------------------------------------------------------- | ------------------------------------------------ |
| [Tensor](/llm/knowledge-cards/tensor/)                               | 多維陣列、framework 核心型別                     |
| [Vector Norm](/llm/knowledge-cards/vector-norm/)                     | 衡量向量大小、L1 / L2 / L∞ 的不同用途            |
| [Dot Product](/llm/knowledge-cards/dot-product/)                     | 兩向量相乘加總、attention / similarity 基礎      |
| [Matrix Multiplication](/llm/knowledge-cards/matrix-multiplication/) | LLM 推論最頻繁的單一運算、memory bandwidth bound |
| [Floating Point](/llm/knowledge-cards/floating-point/)               | FP32 / FP16 / BF16 的位元結構與精度取捨          |

### LLM 機率與資訊論

| 卡片                                                 | 核心問題                                           |
| ---------------------------------------------------- | -------------------------------------------------- |
| [Softmax](/llm/knowledge-cards/softmax/)             | 把實數向量轉成機率分佈、attention / sampling 共用  |
| [Logit](/llm/knowledge-cards/logit/)                 | softmax 之前的原始分數、可正可負                   |
| [Entropy](/llm/knowledge-cards/entropy/)             | 分佈的不確定性、cross-entropy / KL 的基底          |
| [Cross-Entropy](/llm/knowledge-cards/cross-entropy/) | 預測分佈跟真實分佈的距離、預訓練主要 loss          |
| [Perplexity](/llm/knowledge-cards/perplexity/)       | cross-entropy 的指數形式、人類直覺較好讀           |
| [KL Divergence](/llm/knowledge-cards/kl-divergence/) | 兩個分佈的不對稱差距、RLHF / DPO 的 alignment 約束 |

### LLM 訓練流程

| 卡片                                                                                 | 核心問題                                             |
| ------------------------------------------------------------------------------------ | ---------------------------------------------------- |
| [Loss Function](/llm/knowledge-cards/loss-function/)                                 | 訓練最佳化的目標、量化「預測 vs 真實」的差距         |
| [Gradient](/llm/knowledge-cards/gradient/)                                           | 該往哪個方向調權重才能降 loss                        |
| [Backpropagation](/llm/knowledge-cards/backpropagation/)                             | 從 output loss 反向算出每個權重 gradient 的演算法    |
| [Gradient Explosion / Vanishing](/llm/knowledge-cards/gradient-explosion-vanishing/) | 深層網路 chain rule 累乘的兩種失敗模式               |
| [Learning Rate](/llm/knowledge-cards/learning-rate/)                                 | gradient descent 每步幅度、最敏感的 hyperparameter   |
| [SGD](/llm/knowledge-cards/sgd/)                                                     | 用 mini-batch 算 gradient 更新的基礎 optimizer       |
| [Adam / AdamW](/llm/knowledge-cards/adam-adamw/)                                     | 對每個參數自適應 lr、LLM 訓練主流 optimizer          |
| [Pre-training](/llm/knowledge-cards/pre-training/)                                   | 第一階段、用 trillion-token 做 next-token prediction |
| [SFT](/llm/knowledge-cards/sft/)                                                     | 第二階段、用「指令-回答」對 fine-tune                |
| [RLHF](/llm/knowledge-cards/rlhf/)                                                   | 用人類偏好 + reward model + RL 對齊                  |
| [DPO](/llm/knowledge-cards/dpo/)                                                     | RLHF 的簡化替代、直接從偏好資料 fine-tune            |
| [LoRA](/llm/knowledge-cards/lora/)                                                   | 凍住原權重、只訓兩個小矩陣的 PEFT                    |

### Tokenization

| 卡片                                                     | 核心問題                                     |
| -------------------------------------------------------- | -------------------------------------------- |
| [BPE](/llm/knowledge-cards/bpe/)                         | 用「最常字元對」合併建詞彙、GPT / Llama 主流 |
| [SentencePiece](/llm/knowledge-cards/sentencepiece/)     | Google 開源多語言 tokenization 框架          |
| [Vocabulary Size](/llm/knowledge-cards/vocabulary-size/) | 詞彙表大小、影響 embedding / 多語言友善度    |
| [Special Tokens](/llm/knowledge-cards/special-tokens/)   | 邊界 / 角色 / tool call 等特殊用途 token     |

### Sampling 策略

| 卡片                                                          | 核心問題                                   |
| ------------------------------------------------------------- | ------------------------------------------ |
| [Beam Search](/llm/knowledge-cards/beam-search/)              | 保留 K 條候選的 decoding、translation 主流 |
| [Top-K / Top-P / Min-P](/llm/knowledge-cards/top-p-sampling/) | 過濾低機率 token 後取樣、現代 LLM 主流     |

### 評估指標

| 卡片                                         | 核心問題                  |
| -------------------------------------------- | ------------------------- |
| [SWE-bench](/llm/knowledge-cards/swe-bench/) | coding 能力如何被量化比較 |

### 應用層模式

| 卡片                                                       | 核心問題                                                      |
| ---------------------------------------------------------- | ------------------------------------------------------------- |
| [RAG](/llm/knowledge-cards/rag/)                           | 怎麼給 LLM 動態外掛知識                                       |
| [LLM Agent](/llm/knowledge-cards/agent/)                   | 把控制流交給 LLM 的應用模式                                   |
| [Agent Loop](/llm/knowledge-cards/agent-loop/)             | plan → act → observe 的自我循環、injection 放大器             |
| [Tool Use](/llm/knowledge-cards/tool-use/)                 | LLM 透過結構化呼叫外部工具擴展能力的設計                      |
| [Function Calling](/llm/knowledge-cards/function-calling/) | 模型訓練建立的呼叫工具能力                                    |
| [MCP](/llm/knowledge-cards/mcp/)                           | LLM application ↔ tool server 的標準化協議                    |
| [System Prompt](/llm/knowledge-cards/system-prompt/)       | 開發者預設、不直接顯示給使用者的指令層                        |
| [Chunking](/llm/knowledge-cards/chunking/)                 | 把長文件切成 retrieval 片段的 resolution vs context loss 取捨 |
| [Vector Database](/llm/knowledge-cards/vector-database/)   | 高維向量儲存 + ANN 檢索、RAG production 的關鍵元件            |

### 模型行為與安全

| 卡片                                                       | 核心問題                                         |
| ---------------------------------------------------------- | ------------------------------------------------ |
| [Hallucination](/llm/knowledge-cards/hallucination/)       | LLM 生成看似合理但事實錯誤的內容                 |
| [Prompt Injection](/llm/knowledge-cards/prompt-injection/) | 把惡意指令藏進 LLM 會讀到的內容、OWASP LLM01     |
| [Refusal Rate](/llm/knowledge-cards/refusal-rate/)         | LLM 拒絕回答的比例、production 偵測訊號          |
| [Bind Address](/llm/knowledge-cards/bind-address/)         | 推論伺服器決定接受哪些網路介面的請求             |
| [Sandbox](/llm/knowledge-cards/sandbox/)                   | 把 tool 跟 MCP server 跑在權限受限環境的隔離技術 |

### Production 推論

| 卡片                                                       | 核心問題                                                                  |
| ---------------------------------------------------------- | ------------------------------------------------------------------------- |
| [Batching](/llm/knowledge-cards/batching/)                 | 多 request 一起跑、攤平 memory bandwidth 成本、throughput vs latency 取捨 |
| [Prefix Cache](/llm/knowledge-cards/prefix-cache/)         | 多個請求共用前綴的 KV cache 重用優化                                      |
| [MoE](/llm/knowledge-cards/moe/)                           | Mixture of Experts 架構、總參數大但每 token 計算量小                      |
| [Active Parameter](/llm/knowledge-cards/active-parameter/) | MoE 每 token 實際參與計算的參數量                                         |
| [MoE CPU 卸載](/llm/knowledge-cards/moe-cpu-offload/)      | 把 MoE 不活躍專家放系統 RAM、讓有限 VRAM 跑大模型                         |

## 卡片寫法

每張卡片維持四段：

1. **核心概念**：用一句話說明這個術語承擔什麼責任。
2. **概念位置**：說明它在本地 LLM 三層架構（介面 / 伺服器 / 模型）的哪一層、跟其他概念的關係。
3. **可觀察訊號與例子**：用真實使用情境說明這個概念何時會出現、會以什麼形式被讀者察覺。
4. **設計責任**：使用者或工程師遇到這個概念時要做哪些判斷或設定。

卡片之間互相連結，章節文章使用術語時優先連到卡片。卡片是概念索引，章節文章負責情境推導；兩者分工讓讀者可以快速查詢術語，也能完整跟著章節思考。

## 卡片與章節的關係

模組零的概念文章（[本地 vs 雲端](/llm/00-foundations/local-vs-cloud/)、[為什麼 LLM 生字慢](/llm/00-foundations/why-llm-feels-slow/)、[三層架構](/llm/00-foundations/three-layer-architecture/) 等）會引用大量卡片術語；模組一的實作文章（[Ollama 安裝](/llm/01-local-llm-services/ollama/)、[模型選型](/llm/01-local-llm-services/model-selection-priority/) 等）也會用到同一批詞彙。卡片讓兩個模組共用詞彙、避免各自重新定義。
