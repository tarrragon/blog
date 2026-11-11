---
title: "VLM（Vision-Language Model）"
date: 2026-05-12
description: "同時吃圖片 + 文字輸入、產生文字輸出的 LLM 變體、coding 工作流中處理截圖 / 設計稿 / UI debug 的基底"
weight: 1
tags: ["llm", "knowledge-cards", "vlm", "multimodal", "vision"]
---

VLM（Vision-Language Model、視覺語言模型）的核心概念是「**同時接受圖片 + 文字輸入、產生文字輸出的 LLM 變體**」。內部結構是「[vision encoder](/llm/knowledge-cards/vision-encoder/) 把圖片轉成 [image token](/llm/knowledge-cards/image-token/)、跟文字 token 一起進 Transformer」。寫 code 場景的 VLM 用途：看截圖 debug、看 mockup 寫前端 code、看 architecture 白板照片寫文件。

## 跟其他概念的關係

VLM 跟純文字 LLM 的差異：

```text
純文字 LLM：
  text → tokenizer → token IDs → embedding → Transformer → output token

VLM：
  text → tokenizer → text token IDs ─┐
                                     ├→ 統一 token sequence → Transformer → output token
  image → vision encoder → image tokens ─┘
```

text token 與 image token 混合進 Transformer 的機制細節、見 [multimodal fusion](/llm/knowledge-cards/multimodal-fusion/)。

主流 VLM family（2026/5）：

| Family                       | 商業 / 開源 | 本地可跑              | Coding 場景強項              |
| ---------------------------- | ----------- | --------------------- | ---------------------------- |
| GPT-4o / GPT-5 vision        | 商業 API    | 不可                  | 截圖理解、OCR、UI 推理       |
| Claude 3.7 / 4 Sonnet vision | 商業 API    | 不可                  | 截圖 debug、code from mockup |
| Gemini 2.5 Pro vision        | 商業 API    | 不可                  | 長視訊 / 多張圖              |
| **Qwen2.5-VL / Qwen3-VL**    | 開源        | 7B / 32B / 72B 可本地 | 中英 OCR、UI 元素辨識        |
| **Llama 3.2 Vision**         | 開源        | 11B / 90B             | 通用 vision、英文場景        |
| **Gemma 3 Vision**           | 開源        | 4B / 12B / 27B        | 多語、輕量本地               |
| LLaVA / InternVL / Pixtral   | 開源        | 7B-34B                | 研究 / 特定 use case         |

> **事實查核註**：主流 VLM family、本地可跑狀態、coding 場景強項在 2026/5 是估計、依模型更新跟推論伺服器支援度持續變化、引用前以對應 model card 跟 Hugging Face leaderboard 為準。

## 判斷條件與後果

一張圖值不值得送進 VLM，看圖裡有沒有文字描述不出來的資訊。純文字描述就夠清楚時，加一張圖只多出大量 [image token](/llm/knowledge-cards/image-token/)，context 用量與推論成本上升，答案不會因此變好。在本地跑時，VLM 比同級的純文字 LLM 需要更多記憶體與算力：[vision encoder](/llm/knowledge-cards/vision-encoder/) 通常有 0.3-1B 參數，圖片處理階段的算力需求讓 TTFT 變長。任務只是辨識截圖裡的文字時，專門的 OCR 工具（Tesseract、PaddleOCR）可能更穩，VLM 的長處在理解圖之後的推理，例如從截圖判斷 UI 哪裡出錯。影片進 VLM 時是抽出的多張 frame，每一張都換成 image token，token 用量隨 frame 數倍增，所以送不送影片，看任務需要的時間資訊值不值得這份成本。讀 model card 時，「vision」「VL」「multimodal」「-VL」「visual」這些字樣標的都是 VLM。
