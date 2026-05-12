---
title: "模組三：LLM 的理論基礎"
date: 2026-05-11
description: "從神經網路、embedding、attention、Transformer 架構、訓練到 sampling：LLM 內部運作的完整理論圖像"
tags: ["llm", "theoretical-foundations"]
weight: 3
---

本模組整理 LLM 內部運作的理論機制。模組零（[基礎知識與心智模型](/llm/00-foundations/)）回答「裝跟用」的問題、模組二（[數學基礎](/llm/02-math-foundations/)）提供數學工具；本模組把數學工具組合起來、解釋「LLM 內部到底發生什麼事」。

讀完本模組後、看到 attention head、positional encoding、residual stream、layer norm 等 LLM paper 中的術語、能知道每個概念在整體運作中扮演什麼角色。看到「為什麼模型會 hallucinate」「為什麼 instruction tuning 改變模型行為」「為什麼 RLHF 的 reward model 是關鍵」等討論、能回到具體機制追問。

本模組的目標是建立完整理論圖像、不是讓讀者能自己訓練 LLM。完整訓練流程、實作細節、最新研究進展交給[模組末尾的公開課程](/llm/03-theoretical-foundations/going-deeper-theory/)；本模組的責任是把術語跟機制連起來。

## 章節列表

| 章節                                                                    | 主題                                  | 關鍵收穫                                                       |
| ----------------------------------------------------------------------- | ------------------------------------- | -------------------------------------------------------------- |
| [3.0](/llm/03-theoretical-foundations/neural-network-basics/)           | 神經網路基礎                          | layer、weights、activation function、forward / backward pass   |
| [3.1](/llm/03-theoretical-foundations/embedding-spaces/)                | Embedding 空間                        | 為什麼相似 token 在向量空間靠近、embedding 是怎麼學出來的      |
| [3.2](/llm/03-theoretical-foundations/attention-mechanism/)             | Attention 機制                        | Query / Key / Value、scaled dot-product、multi-head attention  |
| [3.3](/llm/03-theoretical-foundations/transformer-architecture/)        | Transformer 架構細節                  | Decoder-only、positional encoding、layer norm、residual stream |
| [3.4](/llm/03-theoretical-foundations/training-pipeline/)               | 訓練流程：pre-train → SFT → RLHF      | 三階段訓練、各階段目標、為什麼這順序                           |
| [3.5](/llm/03-theoretical-foundations/sampling-and-decoding/)           | Sampling 與 decoding 策略             | Greedy、beam、top-k、top-p、temperature、min-p                 |
| [3.6](/llm/03-theoretical-foundations/tokenization-algorithms/)         | Tokenization：BPE、SentencePiece      | 為什麼不同 model 切出來的 token 數不同、tokenizer 的選擇影響   |
| [3.7](/llm/03-theoretical-foundations/cross-language-tokenization/)     | 跨語言 tokenizer 與訓練分佈原理       | 雙因素：tokenizer + 訓練資料分佈、語言選擇取捨                 |
| [3.9](/llm/03-theoretical-foundations/reasoning-models/)                | Reasoning models 與 test-time compute | CoT 從 prompting 變訓練 paradigm、本地 reasoning model 選型    |
| [3.10](/llm/03-theoretical-foundations/speculative-decoding-internals/) | Speculative decoding 內部             | Drafter / target 配對、acceptance rate、MTP / EAGLE 變體       |
| [3.11](/llm/03-theoretical-foundations/going-deeper-theory/)            | 想學更深：推薦公開課程                | Karpathy、Stanford CS224N / CS25 / CS336、DeepLearning.AI      |

## 跟其他模組的分工

| 模組   | 角度                                              |
| ------ | ------------------------------------------------- |
| 模組零 | 操作層：怎麼跑、怎麼選工具                        |
| 模組一 | 工具層：怎麼裝 Ollama / Continue.dev / 怎麼挑模型 |
| 模組二 | 數學工具：線性代數、機率、最佳化、數值精度        |
| 模組三 | 理論機制：模組二的數學怎麼組合成完整 LLM          |

模組二跟模組三設計成可以並讀。模組三會引用模組二的概念（softmax、cross-entropy、矩陣乘法等）；遇到陌生數學詞時跳回模組二補完、再回模組三繼續。

## 適合的讀者

| 你的背景                           | 適合程度                                                                            |
| ---------------------------------- | ----------------------------------------------------------------------------------- |
| 工程師、會用過 LLM、想懂內部       | 直接適合、可從 3.0 依序讀                                                           |
| 有 ML 背景但沒碰過 Transformer     | 可從 3.2 attention 開始                                                             |
| 想做 LLM 應用開發（RAG、agent 等） | 重點讀 3.1、3.2、3.5、3.6                                                           |
| 想做 fine-tuning                   | 重點讀 3.4、再進 [3.7 公開課](/llm/03-theoretical-foundations/going-deeper-theory/) |
| 完全沒碰過機器學習                 | 建議先讀 [模組二 數學基礎](/llm/02-math-foundations/) 後再進本模組                  |

## 為什麼這順序

本模組章節順序的設計：

1. **3.0 神經網路基礎**：建立 layer、weight、activation 等基本詞彙、是後續章節的底層概念。
2. **3.1 embedding 空間**：解釋 token 怎麼變成向量、是 LLM 輸入端的核心。
3. **3.2 attention 機制**：Transformer 的招牌技術、解釋「LLM 怎麼決定該注意哪些 token」。
4. **3.3 Transformer 架構**：把 embedding + attention 組裝成完整 forward pass。
5. **3.4 訓練流程**：解釋這些權重怎麼學出來、三階段訓練的角色。
6. **3.5 sampling**：模型輸出後怎麼挑下一個 token、temperature / top-p 等參數的意義。
7. **3.6 tokenization**：補完 input / output 端的細節。
8. **3.7 跨語言原理**：tokenizer + 訓練分佈雙因素、語言選擇取捨。
9. **3.9 reasoning models**：CoT 從 prompting 變訓練 paradigm、test-time compute 是新軸。
10. **3.10 speculative decoding 內部**：另一條推論加速軸、drafter / MTP / EAGLE 細節。
11. **3.11 公開課**：完整學習路線。

每章可以單獨讀、但若你是第一次接觸 LLM 內部運作、照順序讀最不容易迷路。

## 用語約定

| 英文                     | 中文                   |
| ------------------------ | ---------------------- |
| Layer                    | 層（layer）            |
| Weight                   | 權重                   |
| Activation               | 激活值（activation）   |
| Embedding                | 嵌入向量（embedding）  |
| Attention                | 注意力（attention）    |
| Self-attention           | 自注意力               |
| Query / Key / Value      | Q / K / V（保留原文）  |
| Positional encoding      | 位置編碼               |
| Layer normalization      | 層正規化（layer norm） |
| Residual connection      | 殘差連接               |
| Forward pass             | 前向傳播               |
| Backward pass / Backprop | 反向傳播               |
| Pre-training             | 預訓練                 |
| Fine-tuning              | 微調                   |
| RLHF                     | RLHF（保留原文）       |

英文原文在第一次出現時保留括號錨點、後續用中文。

## 不在本模組內的主題

1. **完整實作 code**：本模組給概念與機制、不展開完整 PyTorch / MLX 實作。Karpathy 的 zero-to-hero 系列是更直接的實作學習路徑。
2. **最新研究進展**：本模組整理截至 2026 年 5 月相對穩定的概念。最新進展（如 mixture of experts 新變體、長 context 技術新方法、agentic LLM 等）交給 Stanford CS25。
3. **多模態的理論細節**：vision encoder 內部架構、speech / audio LLM、video LLM 等理論深度交給專門課程；應用層的 vision 在 coding 工作流的設計見 [4.10 Vision in coding workflow](/llm/04-applications/vision-in-coding-workflow/)。
4. **訓練的工程細節**：data parallelism、tensor parallelism、pipeline parallelism、ZeRO、FlashAttention 等訓練工程主題交給專門課程與 paper。
