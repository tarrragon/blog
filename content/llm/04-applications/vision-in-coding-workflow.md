---
title: "4.15 Vision in coding workflow：本地 VLM 怎麼接寫 code"
date: 2026-05-12
description: "VLM 在 coding 工作流的 use cases、本地 VLM 選型、跟雲端 VLM 的分工、Continue.dev / Ollama 整合現狀"
tags: ["llm", "applications", "vlm", "vision", "multimodal", "ide-integration"]
weight: 15
---

寫 code 工作流不只是文字進文字出 — 大量任務需要看圖：browser 截圖 debug UI、Figma mockup 寫前端、架構白板照片寫文件、log 截圖找 error。[VLM](/llm/knowledge-cards/vlm/)（Vision-Language Model）把這些任務從「人類用文字描述給 LLM」升級到「LLM 直接看圖理解」。本章把 vision 在 coding 場景的 use cases、本地 VLM 選型、跟雲端 VLM 的分工、IDE 整合現狀拆成可操作的判讀。

> **本章 framing 重點**：教材整體聲明過「不放多模態」、但 VLM 在 coding 工作流的 trigger 已經響（雲端 IDE 普遍整合、本地推論伺服器陸續支援）、重新評估後加入本章。本章聚焦「跨工具世代不變的原理 + 寫 code 場景特有的判讀」、避開「具體 IDE plugin API」這類易過時內容。

## 本章目標

讀完本章後、你應該能：

1. 解釋 VLM 跟純文字 LLM 在 coding 場景的能力差異。
2. 看到截圖 / mockup / 設計稿時、判斷該用 VLM 還是純文字描述。
3. 對自己硬體預算選擇本地 VLM（Qwen2.5-VL / Llama 3.2 Vision / Gemma 3 Vision）。
4. 估算 VLM 推論的 context budget（image token + text token）。
5. 知道 IDE 整合 VLM 的現狀跟 trigger 訊號（什麼時候該升級到 vision-native workflow）。

## Coding 場景的 vision use cases

寫 code 工作流中、有 vision 跟沒 vision 的差距：

| 任務                            | 沒 vision                                            | 有 vision                                     |
| ------------------------------- | ---------------------------------------------------- | --------------------------------------------- |
| UI bug debug                    | 人類手寫「按鈕對齊不對、應該 vertically centered」   | 截圖貼進來、VLM 看 layout 直接判讀            |
| Figma → React code              | 人類描述「navbar、3 col grid、卡片含 icon + text」   | 把 mockup 截圖貼進來、VLM 直接生對應 code     |
| Error dialog / stack trace 截圖 | 人類複製貼上完整 error message                       | 截圖、VLM OCR + 理解 context                  |
| 白板 / 紙上 architecture        | 人類重新描述「3 個 microservice、訊息經過 queue...」 | 拍照、VLM 看圖生 mermaid 圖 / documentation   |
| Browser DevTools 看 console     | 人類複製 log                                         | 截圖、VLM 看 stack trace + 周圍 panel context |
| 跟設計師對齊 visual style       | 人類描述配色、字體                                   | 截圖比較、VLM 抓 RGB / 字體 hint              |
| Code screenshot 從別人帖文      | 人類重打                                             | 截圖、VLM OCR + 解讀                          |

判讀反射：**任務需要看「整體 visual context」**（如 layout 對齊、設計稿 → code）→ VLM 顯著贏；**純 OCR**（只認字）→ 專門 OCR 工具（Tesseract / PaddleOCR）可能更穩。

## VLM 在 coding 場景的失敗模式

VLM 不是萬能、寫 code 場景的常見失敗：

1. **看不清細節**：低解析度模式下、截圖中的小字 / 細邊框 / 1px 對齊看不出來；要開高解析度模式 + 高 image token budget
2. **OCR 出錯**：手寫字 / 模糊截圖 / 特殊字型上錯字、特別是中文 / 程式碼 special character
3. **空間關係推理弱**：「左上角的按鈕」「flexbox 第二行第三個」這類描述、VLM 推理仍不穩
4. **DPI 跟縮放問題**：Retina 截圖、放大縮小、subpixel 等情況、不同 VLM 結果差異大
5. **多張圖比較**：比兩張截圖差異、VLM 容易遺漏細節；最好給明確指令「請對比 A、B 兩張圖的 X 元素」

緩解：

- 截圖前裁切到「跟問題相關的區域」、別整個螢幕丟
- 高細節任務開高解析度模式（API 的 `detail: high` 或本地 VLM 的 `min_pixels` 設高）
- OCR-only 任務改用專門工具、不靠 VLM

## 本地 VLM 選型（2026/5）

本地可跑的主流 VLM：

| 模型                              | 大小               | Q4 量化後記憶體 | 適合硬體               | Coding 場景強項         |
| --------------------------------- | ------------------ | --------------- | ---------------------- | ----------------------- |
| **Qwen2.5-VL-7B / Qwen3-VL-7B**   | 7B（vision + LLM） | ~6 GB           | 16GB+ Mac / 12GB+ VRAM | 中英 OCR、UI 元素辨識   |
| **Qwen2.5-VL-32B / 72B**          | 32B / 72B          | ~18 / 40 GB     | 32GB+ Mac / 24GB+ VRAM | 強 reasoning、多圖比較  |
| **Llama 3.2 Vision-11B**          | 11B                | ~7 GB           | 16GB+ Mac / 12GB+ VRAM | 英文場景、通用          |
| **Llama 3.2 Vision-90B**          | 90B                | ~50 GB          | 64GB+ Mac / 多卡       | 接近雲端品質、本地高端  |
| **Gemma 3 Vision-4B / 12B / 27B** | 4-27B              | ~3-16 GB        | 24GB+ Mac / 16GB+ VRAM | 多語、輕量本地          |
| Pixtral 12B / 124B                | 12B / 124B         | ~7 / 70 GB      | 同上                   | Mistral 系、研究 / 評估 |

> **事實查核註**：本地 VLM 的推論伺服器支援度（llama.cpp、Ollama、MLX）依模型 / 推論伺服器版本變動很快、引用前以對應 release notes 為準。2026/5 主流是 llama.cpp 對 Qwen2-VL / Llama 3.2 Vision / Gemma 3 Vision 支援度較好、其他模型可能要等。

### 硬體 vs 模型對照

| 硬體                    | 推薦 VLM                                       | 預期體感                             |
| ----------------------- | ---------------------------------------------- | ------------------------------------ |
| M4 Pro 24GB / 4090 16GB | Qwen2.5-VL-7B / Llama 3.2 Vision-11B           | 可用、品質中等、適合輕度 vision 工作 |
| M4 Pro 36GB / 5090 24GB | Qwen2.5-VL-32B / Gemma 3 Vision-27B            | 寬鬆、品質接近 2024 雲端中階         |
| M4 Max 48-64GB          | Qwen2.5-VL-32B / Llama 3.2 Vision-90B（Q4 緊） | 高品質、coding-vision 主力           |
| M4 Max 128GB / 多卡 PC  | Llama 3.2 Vision-90B / Qwen2.5-VL-72B          | 接近雲端旗艦                         |

### 跟純文字 LLM 對照的記憶體成本

| 任務                 | 純文字 LLM      | VLM                                                                             | 額外成本                  |
| -------------------- | --------------- | ------------------------------------------------------------------------------- | ------------------------- |
| 模型本體             | 18 GB（31B Q4） | ~25 GB（32B VLM Q4）                                                            | +30-40% 給 vision encoder |
| Context budget 影響  | 純 text         | 一張 1024×1024 圖 ≈ 1500-2500 [image tokens](/llm/knowledge-cards/image-token/) | 多張圖直接擠 context      |
| Prefill 時間（TTFT） | 視 prompt 長度  | 圖處理階段顯著拉長 TTFT                                                         | 第一個字等較久            |
| Tokens/s 生成速度    | 同模型大小      | 比同規模純文字 LLM 慢 ~10-30%                                                   | Vision encoder overhead   |

## 本地 VLM vs 雲端 VLM 的分工

跟模組六的 [跨雲端 / 本地資料邊界](/llm/06-security/cross-cloud-local-data-boundary/) 同邏輯、按任務分流：

| 任務                          | 推薦                                | 理由                              |
| ----------------------------- | ----------------------------------- | --------------------------------- |
| 看 NDA / 機密 codebase 截圖   | 本地 VLM（Qwen2.5-VL 7B+）          | 截圖含敏感程式碼、不能送雲端      |
| 看自家內部 UI debug           | 本地 VLM                            | UI 設計可能機密                   |
| 看公開 OSS 截圖               | 雲端 VLM（Claude 4 / GPT-5 vision） | 雲端品質高、無隱私顧慮            |
| 看 Figma mockup（高品質要求） | 雲端 VLM                            | Figma → React code 雲端目前仍領先 |
| 看自己 whiteboard 拍照        | 本地 VLM                            | 個人 thinking 不送雲端            |
| 看 Stack Overflow 截圖        | 雲端 / 本地都行                     | 公開內容、看品質需求              |

混用配置（同 [4.11 long-context](/llm/04-applications/long-context-engineering/) 跟 [6.4 cross-cloud](/llm/06-security/cross-cloud-local-data-boundary/) 推薦模式）：

```text
Continue.dev config：
  Local VLM（default for vision）：Qwen2.5-VL-32B
    日常 vision 工作、敏感內容
  Cloud VLM（manual switch）：Claude 4 vision
    複雜 Figma → code、高品質要求

Local text model：Qwen3-Coder-30B-Instruct
  純文字 coding 任務
```

## Image token 跟 context budget

VLM 推論時、[image token](/llm/knowledge-cards/image-token/) 跟 text token 共用同一個 context window。預算估算：

```text
一張 1024×1024 截圖：
  低細節（low detail）：~85-256 image tokens
  中等：~500-1000 image tokens
  高細節（high detail）：~1500-3000 image tokens

VLM 對話的典型 context 構成：
  System prompt：~500 token
  之前對話歷史：~2000-5000 token
  3 張截圖：~3000-6000 token
  使用者當前 prompt：~200 token
  → 合計 ~6K-12K input
  → 加上 generated answer 跟 reasoning trace（若 VLM 也支援 reasoning）
  → 16K context 模型開始吃緊
```

實務建議：

1. **VLM 工作流配 long context 模型**：至少 32K context、64K 更好
2. **多輪對話控制歷史長度**：每幾輪 trim 舊截圖、避免 context 爆
3. **裁切截圖、只貼相關區域**：別把整個 4K 螢幕貼進來、跟問題相關的窗口就行
4. **看清楚 API 文件的 detail 模式**：不需要看小字的任務用 low detail、省 token

## IDE 整合的現狀（2026/5）

| 工具           | Vision 支援程度                                |
| -------------- | ---------------------------------------------- |
| Claude Desktop | 完整、拖拉截圖進 chat                          |
| Cursor         | 完整、`@image` 或拖拉                          |
| Continue.dev   | 部分（依 provider 跟版本）、本地 VLM 仍演化中  |
| Aider          | CLI 支援 image input、本地 VLM 看 backend      |
| Ollama         | Vision 支援部分模型（如 llava、gemma3-vision） |
| llama.cpp      | 部分模型支援（依 release）                     |
| LM Studio      | 部分 GUI 支援                                  |

> **事實查核註**：IDE 跟推論伺服器對 VLM 的支援度 2026/5 仍在快速演化、引用前以各工具當前 release notes 為準。雲端 IDE（Cursor / Claude Code）的 vision 支援多半成熟、本地 IDE plugin + 本地 VLM 的組合仍在追趕。

### Trigger 訊號

判斷「該升級到 vision-native coding workflow」的訊號：

1. Continue.dev / Ollama release notes 出現「first-class vision support」「image input now stable」
2. 本地 VLM 在自己工作流的 use case（如 debug UI）品質追上 2024 年的 Claude 3 vision
3. 同事 / 社群開始日常用截圖 + IDE 互動
4. 自己工作流出現「人類花時間文字描述視覺問題給 LLM」的 friction

任一觸發 → 開始 explore 本地 vision plugin、設配置。

## Multimodal RAG 跟 VLM 的關係

[RAG](/llm/04-applications/rag-principles/) 章節覆蓋了 text-based retrieval。Multimodal RAG 加上 vision 維度：

```text
傳統 RAG：
  text query → text embedding → 檢索 text docs

Multimodal RAG：
  text or image query → multimodal embedding → 檢索 text + image
  例：「跟這張 UI 截圖相似的設計」、「跟這個 error 一樣的 issue ticket」
```

Multimodal RAG 的 embedding 通常用 [CLIP](/llm/knowledge-cards/clip/)-style 模型（跟 [4.12 embedding model internals](/llm/04-applications/embedding-model-internals/) 介紹的 text-only embedding model 訓練 paradigm 同源、都用 contrastive learning、但同時 embed 圖跟文字到共享空間）。

寫 code 場景的潛在應用：

- **設計系統 RAG**：把過去設計稿、UI screenshots 都 embed 起來、給新 task 截圖時 retrieve 相似 case
- **Bug screenshot 知識庫**：歷史 bug 截圖 + 解法 embed、給新 bug 截圖時找相似 case
- **Architecture 圖譜**：架構圖 retrieve、給新需求找對應的舊架構

目前實用度比 text RAG 低、需要的 infrastructure（multimodal embedding service、image-friendly vector DB）尚不普及。

Tripwire（什麼時候值得評估 multimodal RAG）：

1. 推論伺服器（Ollama / llama.cpp）的 release notes 出現 first-class CLIP-style embedding 支援
2. Vector DB（Qdrant / Milvus / Weaviate）的 image embedding 索引從 experimental 變 stable
3. 自己工作流累積 1000+ 截圖（設計稿 / UI bug / 架構圖）、且 text 描述 retrieval 已撞天花板
4. Team 開始把「跟 X 類似的舊 case」當常規查詢、不只是「找特定關鍵字」

任一觸發 → 評估 multimodal RAG；都沒觸發 → 仍用 text RAG。

## 不在本章內的主題

1. **影片理解 / video LLM**：寫 code 場景用得到的相對少（screen recording 倒是會用、但實作上多半切 keyframe 變多張圖）、見專門 video LLM 教材
2. **Vision-only model（不含語言）**：OCR、object detection、image classification 等專門 vision 任務、用 specialised 工具更好
3. **生圖**（Diffusion 等）：跟 VLM 完全不同 paradigm、見 [Diffusion 卡片](/llm/knowledge-cards/diffusion/) 跟 ComfyUI 教材
4. **3D / point cloud**：CAD / 3D 模型理解、目前 VLM 支援少、屬研究階段
5. **具體 IDE plugin 設定**：Continue.dev 的 image upload UI、Ollama 的 vision API 細節等、隨版本變、見各工具當前文件

## 何時過時 / 何時不過時

**不會過時的部分**：

- Coding 場景 vision 的 use case 分類（UI debug、mockup → code、OCR 等）
- 本地 vs 雲端的分流邏輯（沿用 cross-cloud-local-data-boundary 框架）
- Image token 跟 context budget 的關係
- VLM 的失敗模式分類（細節、OCR、空間推理、DPI）
- Multimodal RAG 的概念框架

**會變的部分**：

- 具體本地 VLM 模型（Qwen2.5-VL → 2.6 → ...、Llama 3.2 → 4 → ...）
- 推論伺服器對 VLM 的支援度（llama.cpp、Ollama、LM Studio 都在追）
- IDE plugin 的 vision integration（Continue.dev、Cursor、Aider 都在演化）
- Vision encoder 設計（CLIP → SigLIP → DFN → ...）
- 雲端跟本地的品質差距（會持續縮小）

## 跟其他章節的關係

本章是 [4.1 RAG](/llm/04-applications/rag-principles/) / [4.3 Tool use](/llm/04-applications/tool-use-principles/) / [4.12 embedding model](/llm/04-applications/embedding-model-internals/) 在 vision 延伸的補完；隱私 / 跨雲端分流邏輯沿用 [6.4](/llm/06-security/cross-cloud-local-data-boundary/)；本地 VLM 配 IDE 的 hands-on 屬於 [模組一 hands-on](/llm/01-local-llm-services/hands-on/) 範圍、視推論伺服器支援度成熟度補。
