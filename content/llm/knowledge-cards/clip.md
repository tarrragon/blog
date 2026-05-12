---
title: "CLIP"
date: 2026-05-12
description: "OpenAI 2021 提出的 contrastive image-text pretraining、現代 VLM 的 vision encoder 大多衍生自它"
weight: 1
tags: ["llm", "knowledge-cards", "vlm", "vision", "pretraining"]
---

CLIP（Contrastive Language-Image Pre-training、Radford et al., 2021）的核心概念是「**用 4 億組 (image, caption) 對、訓 image encoder 跟 text encoder、讓對應圖文的 embedding 在共享空間靠近**」。CLIP 本身不是 VLM、但它的 image encoder 成為現代幾乎所有 [VLM](/llm/knowledge-cards/vlm/) 的 [vision encoder](/llm/knowledge-cards/vision-encoder/) 起點。

## 概念位置

CLIP 的訓練架構（簡化）：

```text
4 億組 (image, caption) 從網路爬：
  (photo of cat, "a fluffy orange cat sitting")
  (screenshot of code, "Python error: NameError x undefined")
  ...

訓練：
  image → Image encoder（ViT-L/14）→ image_embedding
  caption → Text encoder（Transformer）→ text_embedding

  正向對（matching image-caption）：embedding 應該相似
  負向對（同 batch 內其他不匹配）：embedding 應該遠

  [Contrastive learning](/llm/knowledge-cards/contrastive-learning/) loss
```

訓完後得到：

1. **共享 embedding 空間**：圖跟文字 embedding 都在 768/1024 維空間、相似度比較有意義
2. **Zero-shot classification 能力**：給一張圖、給 100 個文字標籤、看哪個 embedding 最接近 → 不用 fine-tune 就能分類
3. **Image search / 多模態 retrieval**：text 跟 image 互查、是 multimodal RAG 基底

對 VLM 的影響：

```text
CLIP 訓出來後：
  image encoder 已經學會「把圖片變成有意義的 embedding」

VLM 訓練時：
  - 直接拿 CLIP 的 image encoder 當 vision encoder（凍住或一起 fine-tune）
  - 接上 LLM、用 image-text 任務資料訓 alignment
  - 不用從頭訓 vision encoder、省下大量 compute
```

跟 SigLIP 的關係：SigLIP（Zhai et al., 2023）是 Google 提出的 CLIP 變體、用 sigmoid loss 取代原本 InfoNCE、訓練更穩、品質略佳；Gemma 3 / Idefics 等用 SigLIP 而非原 CLIP。

## 設計責任

讀 VLM paper / model card 看到「CLIP backbone」「SigLIP encoder」「OpenCLIP weights」就是這 family。寫 code 場景的判讀：

1. **CLIP 本身不是 VLM**：CLIP 只有 image-text 相似度、不能生文字回答；VLM 是「CLIP 的 image encoder + LLM + alignment training」
2. **不同 CLIP 變體影響 VLM 能力**：CLIP ViT-L/14 是經典、SigLIP / DFN（Apple）等變體在某些任務更強
3. **Multimodal RAG 直接用 CLIP**：純 image-text retrieval（如「找跟這張圖相似的 doc」）不需要完整 VLM、CLIP-like 模型就夠
4. **CLIP 用於 zero-shot 分類仍實用**：給定固定的 class label set（如「截圖 / 設計稿 / 程式碼 / 文件」）、CLIP 能直接 zero-shot 分類、不需要訓 specific classifier
