---
title: "0.4 MLX / MTP / oMLX 的區別"
date: 2026-05-11
description: "三個常被混為一談的術語：framework、加速技巧、特化 server，疊加而非互斥"
tags: ["llm", "foundations", "mlx", "mtp"]
weight: 4
---

MLX、MTP、oMLX 是本地 LLM 生態中最容易被網路文章混為一談的三個術語。它們分別屬於不同的技術層級：MLX 是 Apple 自家的數值運算 framework，MTP 是一種加速技巧，oMLX 是一個建在 MLX 上的特化推論伺服器。三者**疊加而非互斥**，可以同時存在於一套堆疊裡。

把這三個分清楚後，看到「MLX 加速 50%」「MTP 整合到 llama.cpp」「oMLX 用上 MTP」這類句子就能精準判讀。本章的責任是把每個術語放回正確的位置，再說明它們如何疊加。

## 本章目標

讀完本章後，你應該能：

1. 用一句話分別說清楚 MLX、MTP、oMLX 是什麼。
2. 看懂「MLX backend」「啟用 MTP」「用 oMLX 跑」這些句子。
3. 判斷三者組合的可行性與效果。
4. 避開把它們當成競爭關係的常見誤解。

## MLX：Apple 的數值運算 framework

**MLX** 是 Apple 為 Apple Silicon 設計的數值運算 framework、類似 PyTorch 或 JAX 在 Mac 上的對應物（全名 Machine Learning eXchange、2023 年釋出）。它的責任是：

1. 在 CPU、GPU、Neural Engine 之間自動排程運算。
2. 利用統一記憶體（UMA）避免在記憶體層級之間搬資料。
3. 提供 lazy evaluation（延遲計算、把運算累積成圖再一次優化執行）與 graph optimization（自動合併多個運算、減少記憶體 round-trip）、讓相同的 Python 程式碼在 M1 ~ M4 上都能用上各代硬體優勢。
4. 提供 `mlx.core`、`mlx.nn` 等 Python API、可以寫訓練 / 推論程式。

MLX 的角色就是「跑神經網路用的底層數值庫」、把 server / 模型 / 加速技巧三個責任都留給上層工具去做。可以類比：

| 主流生態                  | Apple Silicon 對應                 |
| ------------------------- | ---------------------------------- |
| PyTorch / JAX             | MLX                                |
| CUDA                      | Metal（MLX 在 GPU 上跑會用 Metal） |
| NumPy                     | `mlx.core`                         |
| Hugging Face Transformers | `mlx-lm`、`mlx-community` 上的模型 |

MLX 的角色定位是「basic infrastructure」。要拿 MLX 跑 LLM，你需要：MLX framework + 一份用 MLX 寫的模型實作（如 `mlx-lm` package）+ 模型權重（MLX format）+ 一個介面（CLI 或 server wrapper）。所有上層工具都站在 MLX 這塊地基上。

接近真實的例子：

```bash
pip install mlx-lm
mlx_lm.generate --model mlx-community/Llama-3.2-3B-Instruct-4bit --prompt "hi"
```

這段命令會載入 MLX 格式的模型權重、用 MLX framework 在 Apple Silicon 上跑推論。但這只是 library 等級的呼叫、不是常駐伺服器；要做成 server 還需要再 wrap 一層（例如 `mlx_lm.server` 或 oMLX）。

### 常見 MLX 誤用

1. **以為裝 MLX 就有 server**：MLX 只是 library、要 expose HTTP API 需要再 wrap 一層（`mlx_lm.server`、oMLX、或自己用 FastAPI 包）。
2. **以為 MLX 跟 Metal 互斥**：MLX 跑在 GPU 上會自動用 Metal、兩者是上下層關係、不是擇一。Metal 是 Apple 的 GPU 加速 API、MLX 是利用 Metal 的高階 framework。
3. **以為 Ollama 用 MLX backend**：Ollama 內部用 [llama.cpp](/llm/01-local-llm-services/llama-cpp/) 配 Metal、跟 MLX 沒關係。看到「Ollama 用 MLX 加速」要追問來源、多半是混淆。

## MTP：一種加速技巧

**Multi-Token Prediction**（MTP）的核心是「一次預測多個 token 的加速技巧」，本質上是 [speculative decoding](/llm/knowledge-cards/speculative-decoding/) 的工程化實作。它的責任是：

1. 用一個小模型（drafter）快速猜未來 N 個 token。
2. 把這 N 個 token 一次餵給大模型（target），讓大模型並行驗證。
3. 大模型保留它認同的 token 前綴，從第一個拒絕點繼續。

MTP 是跑模型時的演算法層、跟伺服器與模型實作互相正交：任何推論伺服器都可以選擇實作或不實作 MTP、模型可以選擇有沒有官方 drafter、兩件事分離。

Google 為 Gemma 4 釋出官方 drafter 後，MTP 變成 Gemma 4 生態的標準配備。官方數據宣稱 coding 任務 2 ~ 3 倍加速；寫 code 的加速尤其明顯，因為 code 有大量可預測 pattern（縮排、括號、常見變數名），drafter 接受率高。

陷阱有三個：

1. **MTP ≠ Gemma 4 限定**。任何模型理論上都能用 speculative decoding；只是 Gemma 4 有官方 drafter、現成可用。其他模型要嘛社群自己訓 drafter，要嘛沒有。
2. **MTP 不一定加速所有任務**。對沒有預測 pattern 的任務（如生成隨機 ID、加密文字），接受率低，反而會拖慢。寫 code 是甜蜜點。
3. **加速倍數受實作品質影響**。網路上「MTP 加速 40%」這類來源不明數字常見；Google 官方數據是 2 ~ 3 倍，視任務而定。引用時要追到官方來源。

實作層面、要用 MTP 需要：

- 一個支援 speculative decoding 的伺服器（2026 年 5 月時 Ollama v0.23+ 已支援、LM Studio 跟 oMLX 也支援、llama.cpp 上游 speculative decoding 框架仍 beta）。
- 一個有 drafter 的模型、或自己組合 target + drafter pair。

Ollama 在 2026/5/7 釋出的 v0.23.1 加入 Gemma 4 MTP 一鍵支援：

```bash
ollama run gemma4:31b-coding-mtp-bf16
```

這個 model tag 內含 drafter，伺服器自動啟用 speculative decoding。

## oMLX：建在 MLX 上的特化伺服器

**oMLX**（"optimized MLX server" 的縮寫，2024 年由社群釋出）的核心是「建在 MLX 之上、針對 coding agent 長 context 場景優化的推論伺服器」。它的責任是：

1. 用 MLX 當推論 backend，吃 Apple Silicon 統一記憶體優勢。
2. 提供 OpenAI 相容 HTTP API。
3. **paged SSD KV cache**：把已 prefill 過的 prompt context 存到 SSD，下次同前綴 prompt 可以直接讀 cache。
4. 支援 speculative decoding 與[量化](/llm/knowledge-cards/quantization/)。

oMLX 跟 Ollama 並列同一層（都是推論伺服器），但定位不同：

| 維度           | Ollama                     | oMLX                          |
| -------------- | -------------------------- | ----------------------------- |
| 推論 backend   | llama.cpp                  | MLX                           |
| 目標場景       | 通用本地 LLM               | coding agent 長 context       |
| KV cache 策略  | 記憶體內，session 結束就丟 | paged SSD，跨 session 復用    |
| 安裝難度       | 一行 brew                  | 較高，要設 Python 環境        |
| 對 TTFT 的優化 | 一般                       | 主打：30 ~ 90 秒降到 1 ~ 3 秒 |
| 生態成熟度     | 高，大量 model tag         | 較新，模型支援要自己轉        |

oMLX 解的是 [0.1 為什麼 LLM 生字慢](/llm/00-foundations/why-llm-feels-slow/) 提到的痛點：當你用 aider 或 Cline 這類 [coding agent](/llm/04-applications/agent-architecture/)（用 LLM 自動操作 git / 檔案的 CLI 工具、模組四會展開）、把整個 repo 塞進 prompt 時、本地 LLM 每次都要重新 [prefill](/llm/knowledge-cards/prefill/) 10K+ tokens、等 30 ~ 90 秒。oMLX 的 SSD cache 把同前綴 prompt 的 prefill 結果保存下來、下次只 prefill「新增的部分」、TTFT 從幾十秒降到幾秒。

陷阱是把 oMLX 當成「比 Ollama 強的替代品」。它解的是非常特定的痛點；短 prompt code completion 或一般對話場景下、Ollama 的 TTFT 痛點不浮現、oMLX 的 SSD cache 賣點換不到體感、卻要先承擔較高的安裝與維護成本。長 context coding agent 才是 oMLX 的甜蜜點。

## 三者疊加：實際堆疊長什麼樣

三者不是競爭關係，是堆疊關係。下表是幾種常見組合：

| 組合                                           | 適用情境                        |
| ---------------------------------------------- | ------------------------------- |
| MLX framework + `mlx-lm` library               | 研究用、直接寫 Python 跑推論    |
| Ollama（用 llama.cpp 當 backend）              | 主流選擇、跟 MLX 無關           |
| Ollama + Gemma 4 with MTP drafter              | 主流選擇 + 加速、coding 場景 2x |
| oMLX（用 MLX 當 backend）+ Gemma 4 MTP         | 長 context agent 場景的完整堆疊 |
| LM Studio + Qwen3-Coder + speculative decoding | GUI 派 + 加速                   |

兩個主流堆疊的延伸判讀：

- **Ollama + Gemma 4 MTP**：成立條件是 Ollama 版本 ≥ v0.23.1（內建 MTP 一鍵支援）、target / drafter 同 family（都是 Gemma 4）。換成 Llama 或 Qwen 系列就要找對應的 drafter 配對、或退回沒 MTP 的版本；2026 年 5 月時 Qwen3-Coder 還沒有官方 drafter。
- **oMLX + Gemma 4 MTP**：成立條件是有長 context coding agent 工作流（10K+ tokens）、且 Mac 記憶體足夠同時載入 target + drafter（32GB+）。短 context 或一般對話場景、oMLX 的 SSD cache 帶不來體感優勢、改用 Ollama 配同樣 model tag 更省事。

注意三件事：

1. Ollama 預設用 llama.cpp 當 backend，跟 MLX 沒關係。看到「Ollama 用 MLX 加速」這種句子要追問來源，多半是混淆。
2. oMLX 是少數真正把 MLX 用在 server 層的工具；它的賣點不是「MLX」本身，是 SSD KV cache。
3. MTP 是技巧層，可以疊在 Ollama 或 oMLX 上面，跟伺服器選擇正交。

## 用三層定位判讀新資訊

三層定位的用法是「把每則資訊放回 framework / server / 技巧層、再追問該層的證據」。社群文章在描述這三者時常會混用層級、用這個流程可以快速還原它真正在說什麼。下面是幾個常見句子、加上三層定位重新解析的版本：

**「llama.cpp 已整合 Gemma 4 MTP」**：要追問版本與時間點。2026 年 5 月時 llama.cpp 上游的 speculative decoding 框架仍 beta、Gemma 4 官方 drafter 整合是 feature request；Ollama 反而在 v0.23.1（2026/5/7）一鍵支援、是少見的「Ollama 領先底層 llama.cpp」情境。Ollama 維護自己的 fork、有時搶先加 patch。

**「MTP 加速 40%」**：要追問任務與基準。Google 官方數據是 coding 任務 2 ~ 3 倍、其他任務 1.5 ~ 2 倍。「40%」這類數字若沒附上任務、硬體、比較基準、判讀價值有限。回到 Google Gemma 4 技術報告比對原始三變數。

**「Ollama 用 MLX 比 llama.cpp 快」**：混淆了 framework 層與 server 層。Ollama 內部用 llama.cpp（library 層）當推論引擎、配 Metal backend 接 Apple Silicon GPU。它跟 MLX 是平行的選擇、不是包含關係。想用 MLX 當 backend 要選 oMLX 或自己 wrap mlx-lm。

**「oMLX 是 Ollama 的 MLX 版本」**：兩者沒有 fork 關係。oMLX 的主要創新是 paged SSD KV cache、解的是長 [context window](/llm/knowledge-cards/context-window/) coding agent 的 [TTFT](/llm/knowledge-cards/ttft/) 痛點。「換 backend 到 MLX」是另一回事、不是 oMLX 的賣點。

**「裝 MLX 就能跑 LLM」**：[MLX](/llm/knowledge-cards/mlx/) 只是 framework。實際要跑 LLM 還需要模型實作（`mlx-lm`）+ 模型權重（MLX format）+ 介面（CLI 或 server wrapper）。對寫 code 場景的多數使用者、直接用 Ollama 反而更直接、不用接觸 MLX 細節。

詳細的判讀框架見 [0.6 判讀本地 LLM 資訊的五個框架](/llm/00-foundations/info-judgment-frames/)；其中框架一（追溯版本與時間點）、框架二（量化宣稱三變數）、框架三（工具放回三層架構）對本章三個術語的混淆特別有用。

## 給讀者的選擇順序

寫 code 場景的優先順序：

1. **先裝 Ollama**、跑 Gemma 4 31B MTP 或 Qwen3-Coder 30B。MTP 加速包含在 Ollama v0.23.1 內、開箱即用。
2. **用一週後**若發現 TTFT 在塞長 context 時體感痛、再評估 oMLX。
3. **MLX 本身**對寫 code 使用者是抽象層下面的事、多數場景由 Ollama 把 MLX 細節包起來；直接接觸 MLX 的時機是想自己 wrap library 或調試底層 framework。

順序設計的核心是「先解決日常路徑、再針對痛點做特化」。先鑽 MLX 細節或安裝 oMLX、會在還沒驗證痛點存在時就承擔額外的學習與維護成本。

## 下一章

下一章：[0.5 Apple Silicon 記憶體預算](/llm/00-foundations/hardware-memory-budget/)、把心智模型對到自己 Mac 的真實規格。
