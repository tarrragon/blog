---
title: "Image Token"
date: 2026-05-12
description: "VLM 把圖片轉成「對 Transformer 而言跟 text token 同質」的向量、計入 context window 預算"
weight: 1
tags: ["llm", "knowledge-cards", "vlm", "vision", "token"]
---

Image token（圖片 token）的核心概念是「**[VLM](/llm/knowledge-cards/vlm/) 把圖片過 [vision encoder](/llm/knowledge-cards/vision-encoder/) 後、產出的向量序列、在 Transformer 內跟 text [token](/llm/knowledge-cards/token/) 同質處理**」。理解這個概念能解釋為什麼「一張圖 = 幾百到幾千 token」、為什麼塞圖會吃掉 context budget、為什麼 VLM 推論比純文字 LLM 慢。

## 概念位置

從圖到 image token 的轉換：

```text
Input image: 1024×1024 RGB
   ↓ Patchify（切 14×14 patch、得 ~5000 個 patch）
   ↓ Vision encoder（ViT 處理每個 patch、產 768/1024 維向量）
   ↓ Optional: 2D position embedding
   ↓ Optional: pooling / merging（減少 token 數）
Image tokens: ~500-2500 個（依模型設計）
   ↓ Projection（vision_dim → LLM hidden_dim、配合 LLM 內部維度）
   ↓ 跟 text token 串成單一 sequence
   ↓ Transformer 跟一般 token 一樣處理
```

主流 VLM 的單張圖 token 用量（粗略、依模型 / 解析度而變）：

| 模型             | 預設輸入解析度        | 單張圖約用 token | Context 影響               |
| ---------------- | --------------------- | ---------------- | -------------------------- |
| GPT-4o vision    | 動態（最高 2048×768） | ~85 - 1000+      | 高解析度模式消耗大         |
| Claude 3 vision  | 動態                  | ~1000-1600       | 一張圖 ≈ 1.5K text token   |
| Qwen2.5-VL       | 動態、可調 min/max    | ~500 - 4000      | 設定 `min_pixels` 控制下限 |
| Llama 3.2 Vision | 固定（560×560）       | ~1600            | 多張圖直接乘               |
| Gemma 3 Vision   | 動態                  | ~256 - 2000      | 多語 / 多解析度            |

> **事實查核註**：上述 token 數量級依模型版本、推論配置（如「low / high detail」模式）變化、引用前以對應 model card 跟 API 文件為準。

## 設計責任

讀 VLM API / 推論 log 看到「image tokens used: 1247」「visual tokens: 580」就是這指標。寫 code 場景的判讀：

1. **多張截圖 = context 吃緊**：一張 1500 token、丟 10 張就 15K、加上 prompt 跟回答、long context 模型才能 handle
2. **同張圖、解析度模式影響成本**：許多 API 提供 low / auto / high detail 模式、low detail 約 1/10 token；OCR 需要高解析、不細節辨識可選 low
3. **本地 VLM 推論 prefill 慢**：image token 多、prefill 階段（[TTFT](/llm/knowledge-cards/ttft/)）對應變長、第一個字出來要等較久
4. **API 計費通常 image token 跟 text token 同價**：算成本看實際用了多少 image token、不要假設「一張圖 = 一個 token」
5. **Image token 是消耗品、不是參數**：跟模型內部權重不同、純粹是「這次 forward pass 的 input」
