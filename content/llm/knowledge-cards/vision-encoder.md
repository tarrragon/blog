---
title: "Vision Encoder"
date: 2026-05-12
description: "VLM 內部負責把圖片轉成可進 Transformer 的向量序列的模組、ViT / CLIP encoder 為主流"
weight: 1
tags: ["llm", "knowledge-cards", "vlm", "vision", "architecture"]
---

Vision encoder（視覺編碼器）的核心概念是「**[VLM](/llm/knowledge-cards/vlm/) 內部把圖片轉成向量序列的模組**」。主流做法是「把圖片切成 patch、每個 patch 過 ViT（Vision Transformer）變一個向量」、再進入 LLM 的 Transformer 層。Vision encoder 通常用 [CLIP](/llm/knowledge-cards/clip/) 預訓練的權重起始、再跟 LLM 一起 fine-tune。

## 概念位置

Vision encoder 在 VLM 中的位置：

```text
Input image（如 1024×1024 RGB）
   ↓ 切 patch（如 14×14 patch、每張圖 ~5000 個 patch）
   ↓ Vision encoder（ViT 或 CLIP image encoder）
Image feature vectors（每個 patch 對應一個 768/1024 維向量）
   ↓ Projection layer（vision dim → LLM hidden dim）
[Image tokens](/llm/knowledge-cards/image-token/)（變成 LLM 可吃的「視覺 token」）
   ↓
跟 text token 混合 → Transformer → output token
```

主流 vision encoder 設計：

| 設計                          | 機制                                       | 代表 VLM                     |
| ----------------------------- | ------------------------------------------ | ---------------------------- |
| CLIP ViT-L/14（或變體）       | OpenAI CLIP 的 image encoder 直接用        | LLaVA-1.5、Qwen2-VL、Pixtral |
| SigLIP                        | Google 的 sigmoid-loss CLIP 變體、訓得更穩 | Gemma 3 Vision、Idefics2     |
| 自訓 / 多解析度 ViT           | 從頭訓、支援動態解析度（不固定 224×224）   | Qwen2.5-VL、GPT-4V           |
| Native multimodal（單一網路） | 圖跟文字共用 Transformer、不分開 encoder   | Chameleon（Meta 研究）       |

Vision encoder 的關鍵設計取捨：

1. **解析度**：固定（224×224 / 336×336）vs 動態（依輸入圖大小）
2. **參數量**：vision encoder 0.3B-1B 是主流；太小辨識能力差、太大拖累整體推論速度
3. **Pretrain 來源**：用 CLIP / SigLIP 預訓練的權重起始、加上 multimodal fine-tune；少數從頭訓
4. **跟 LLM 結合方式**：見 [multimodal fusion](/llm/knowledge-cards/multimodal-fusion/) 卡

## 設計責任

讀 VLM model card 看到「vision tower」「ViT backbone」「image encoder」就是這部分。寫 code 場景的判讀：

1. **解析度影響細節辨識**：低解析度（224）對「截圖中的小字 / 細邊框」可能模糊、看不清；高解析度（1024+）能看清楚但 token 用量大
2. **Token 用量估算**：一張 1024×1024 圖經過 vision encoder 後、產出 ~500-2500 image tokens（依設計）、相當於一段中等長度的文字 prompt
3. **動態解析度模型更實用**：Qwen2.5-VL / GPT-4V 等支援動態解析度、不會把高清截圖縮成 224 失去細節
4. **Vision encoder 不能單獨 fine-tune**：通常跟 LLM 一起訓、單獨換 vision encoder 會破壞 alignment
