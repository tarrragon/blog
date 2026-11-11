---
title: "Multimodal Fusion"
date: 2026-05-12
description: "VLM 把 vision encoder 跟 LLM 結合的方式：early fusion / cross-attention / native multimodal 三條路線"
weight: 1
tags: ["llm", "knowledge-cards", "vlm", "vision", "architecture"]
---

Multimodal fusion（多模態融合）的核心概念是「**[VLM](/llm/knowledge-cards/vlm/) 把 vision encoder 產出的 [image token](/llm/knowledge-cards/image-token/) 跟 text token 結合進 LLM 的設計方式**」。三條主流路線：early fusion（image token 跟 text token 串成同 sequence）、cross-attention（separate stream、attention 跨流）、native multimodal（單一網路統一處理）。

## 跟其他概念的關係

三種 fusion 方式的對比（差異在 [vision encoder](/llm/knowledge-cards/vision-encoder/) 輸出如何進入 LLM）：

### 1. Early Fusion（最主流）

```text
image → vision encoder → image tokens ─┐
                                       ├→ concat 成單一 sequence → 同 LLM Transformer 處理
text → tokenizer → text tokens ────────┘
```

- **特性**：image token 跟 text token 在同一個 token sequence、共用 LLM 的 attention / FFN
- **代表**：LLaVA、Qwen2-VL、Llama 3.2 Vision、Pixtral、GPT-4V 多數變體
- **優點**：實作簡單、可重用 LLM 的 weight、訓練資料效率高
- **缺點**：image token 佔 context、長對話 / 多圖時 context budget 吃緊

### 2. Cross-Attention（Flamingo-style）

```text
image → vision encoder → image features ─┐
                                          │ Cross-attention 層
text → tokenizer → tokens → LLM Transformer ──┤  插在每幾層 Transformer 之間
                                          │ Image features 不進 LLM 主流
output ←─────────────────────────────────┘
```

- **特性**：image features 不變成 LLM 的 token、透過額外的 cross-attention 層注入
- **代表**：Flamingo（DeepMind）、Idefics（Hugging Face）、部分 video LLM
- **優點**：text token sequence 不會被 image 撐大、長文字 + 多圖比較友善
- **缺點**：架構複雜、訓練難、推論伺服器支援度差

### 3. Native Multimodal（unified token space）

```text
image → patchify → discrete image tokens（如 VQ-VAE 編碼）
text → tokenizer → text tokens

兩者共用 vocab、同一個 Transformer 從頭訓
（沒有「分開的 vision encoder」、modality 在 vocab level 統一）
```

- **特性**：架構上「圖跟文字是同一種東西」、共用 vocab
- **代表**：Chameleon（Meta 研究）、未來 trend
- **優點**：理論最 clean、跨模態 generation 自然（生圖 + 生文都同個模型）
- **缺點**：訓練極貴、目前研究階段為主、實用 VLM 仍以 early fusion 為主流

## 主流選擇對比

| 路線              | 佔比（2026/5） | 對 coding 場景的影響                            |
| ----------------- | -------------- | ----------------------------------------------- |
| Early fusion      | ~85%           | Image token 佔 context、要算清楚 context budget |
| Cross-attention   | ~10%           | 推論伺服器支援度差、本地跑選項少                |
| Native multimodal | < 5%           | 研究階段、現在不適合 production / 本地工作流    |

## 判斷條件與後果

在本地跑 VLM 時，模型的 fusion 路線決定兩件事：推論伺服器是否載得起這個模型，以及圖片佔掉多少 context。Qwen2.5-VL、Llama 3.2 Vision、Gemma 3 Vision 都是 early fusion，llama.cpp、Ollama、LM Studio 都支援；Idefics 這類 cross-attention 模型，推論伺服器的支援度差，不一定有能跑的 GGUF，原因是它多出的 cross-attention 層不在一般 LLM 的架構裡。early fusion 下 image token 直接進入 context，多圖或長對話時 context budget 會被圖片吃掉；cross-attention 的 image features 走額外的層注入，不佔 LLM 主流的 context window。native multimodal 仍在研究階段，現在的 production 與本地工作流用 early fusion 的主流模型就有完整的工具支援，不必等它成熟。
