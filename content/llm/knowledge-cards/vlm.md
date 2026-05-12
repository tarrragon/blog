---
title: "VLM（Vision-Language Model）"
date: 2026-05-12
description: "同時吃圖片 + 文字輸入、產生文字輸出的 LLM 變體、coding 工作流中處理截圖 / 設計稿 / UI debug 的基底"
weight: 1
tags: ["llm", "knowledge-cards", "vlm", "multimodal", "vision"]
---

VLM（Vision-Language Model、視覺語言模型）的核心概念是「**同時接受圖片 + 文字輸入、產生文字輸出的 LLM 變體**」。內部結構是「[vision encoder](/llm/knowledge-cards/vision-encoder/) 把圖片轉成 [image token](/llm/knowledge-cards/image-token/)、跟文字 token 一起進 Transformer」。寫 code 場景的 VLM 用途：看截圖 debug、看 mockup 寫前端 code、看 architecture 白板照片寫文件。

## 概念位置

VLM 跟純文字 LLM 的差異：

```text
純文字 LLM：
  text → tokenizer → token IDs → embedding → Transformer → output token

VLM：
  text → tokenizer → text token IDs ─┐
                                     ├→ 統一 token sequence → Transformer → output token
  image → vision encoder → image tokens ─┘
```

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

## 設計責任

讀 model card 看到「vision」「VL」「multimodal」「-VL」「visual」就是 VLM。寫 code 場景的判讀：

1. **任務適合用 vision 才用**：純文字描述夠清楚就別塞圖、image token 多、context 跟推論成本上升
2. **本地跑 VLM 比純文字 LLM 吃資源**：vision encoder 通常 0.3-1B 參數、image 處理階段算力需求大、TTFT 變長
3. **OCR-heavy 任務不一定要 VLM**：純 OCR（識別截圖中文字）用專門 OCR 工具（Tesseract / PaddleOCR）可能更穩、VLM 強項在「理解圖 + 推理」
4. **影片不是免費**：「VLM 看影片」本質是抽 frames 變多張圖、token 用量爆炸、效益看任務
