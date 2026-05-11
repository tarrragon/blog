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

**MLX**（Machine Learning eXchange，2023 年由 Apple 釋出）的核心是「為 Apple Silicon 設計的數值運算 framework，類似 PyTorch 或 JAX 在 Mac 上的對應物」。它的責任是：

1. 在 CPU、GPU、Neural Engine 之間自動排程運算。
2. 利用統一記憶體（UMA）避免在記憶體層級之間搬資料。
3. 提供 lazy evaluation 與 graph optimization，讓相同的 Python 程式碼在 M1 ~ M4 上都能用上各代硬體優勢。
4. 提供 `mlx.core`、`mlx.nn` 等 Python API，可以寫訓練 / 推論程式。

MLX 本身**不是**推論伺服器、**不是**模型、**不是**加速技巧。它是「跑神經網路用的底層數值庫」。可以類比：

| 通用世界                  | Apple 世界                         |
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

這段命令會載入 MLX 格式的模型權重，用 MLX framework 在 Apple Silicon 上跑推論。但這只是 library 等級的呼叫，不是常駐伺服器；要做成 server 還需要再 wrap 一層（例如 `mlx_lm.server` 或 oMLX）。

## MTP：一種加速技巧

**Multi-Token Prediction**（MTP）的核心是「一次預測多個 token 的加速技巧」，本質上是 [speculative decoding](/llm/00-foundations/why-llm-feels-slow/) 的工程化實作。它的責任是：

1. 用一個小模型（drafter）快速猜未來 N 個 token。
2. 把這 N 個 token 一次餵給大模型（target），讓大模型並行驗證。
3. 大模型保留它認同的 token 前綴，從第一個拒絕點繼續。

MTP **不是** framework、**不是**伺服器、**不是**模型；它是「跑模型時的一個演算法」。任何推論伺服器都可以選擇實作或不實作 MTP，模型可以選擇有沒有官方 drafter，這兩件事是分離的。

Google 為 Gemma 4 釋出官方 drafter 後，MTP 變成 Gemma 4 生態的標準配備。官方數據宣稱 coding 任務 2 ~ 3 倍加速；寫 code 的加速尤其明顯，因為 code 有大量可預測 pattern（縮排、括號、常見變數名），drafter 接受率高。

陷阱有三個：

1. **MTP ≠ Gemma 4 限定**。任何模型理論上都能用 speculative decoding；只是 Gemma 4 有官方 drafter、現成可用。其他模型要嘛社群自己訓 drafter，要嘛沒有。
2. **MTP 不一定加速所有任務**。對沒有預測 pattern 的任務（如生成隨機 ID、加密文字），接受率低，反而會拖慢。寫 code 是甜蜜點。
3. **加速倍數受實作品質影響**。網路上「MTP 加速 40%」這類來源不明數字常見；Google 官方數據是 2 ~ 3 倍，視任務而定。引用時要追到官方來源。

實作層面，要用 MTP 需要：

- 一個支援 speculative decoding 的伺服器（Ollama v0.23+、llama.cpp 在 2026 還在 beta、LM Studio、oMLX 都支援）。
- 一個有 drafter 的模型，或自己組合 target + drafter pair。

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
4. 支援 speculative decoding 與量化。

oMLX 跟 Ollama 並列同一層（都是推論伺服器），但定位不同：

| 維度           | Ollama                     | oMLX                          |
| -------------- | -------------------------- | ----------------------------- |
| 推論 backend   | llama.cpp                  | MLX                           |
| 目標場景       | 通用本地 LLM               | coding agent 長 context       |
| KV cache 策略  | 記憶體內，session 結束就丟 | paged SSD，跨 session 復用    |
| 安裝難度       | 一行 brew                  | 較高，要設 Python 環境        |
| 對 TTFT 的優化 | 一般                       | 主打：30 ~ 90 秒降到 1 ~ 3 秒 |
| 生態成熟度     | 高，大量 model tag         | 較新，模型支援要自己轉        |

oMLX 解的是 [0.1 為什麼 LLM 生字慢](/llm/00-foundations/why-llm-feels-slow/) 提到的痛點：當你用 aider 或 Cline 這類 coding agent，把整個 repo 塞進 prompt 時，本地 LLM 每次都要重新 prefill 10K+ tokens，等 30 ~ 90 秒。oMLX 的 SSD cache 把同前綴 prompt 的 prefill 結果保存下來，下次只 prefill 「新增的部分」，TTFT 從幾十秒降到幾秒。

陷阱是把 oMLX 當成「比 Ollama 強的替代品」。它解的是非常特定的痛點；如果你的使用場景是短 prompt code completion 或一般對話，Ollama 完全夠用，oMLX 的優勢用不上、反而要承擔較高的安裝與維護成本。

## 三者疊加：實際堆疊長什麼樣

三者不是競爭關係，是堆疊關係。下表是幾種常見組合：

| 堆疊                                           | 場景                            |
| ---------------------------------------------- | ------------------------------- |
| MLX framework + `mlx-lm` library               | 研究用，直接寫 Python 跑推論    |
| Ollama（用 llama.cpp 當 backend）              | 主流選擇，跟 MLX 無關           |
| Ollama + Gemma 4 with MTP drafter              | 主流選擇 + 加速，coding 場景 2x |
| oMLX（用 MLX 當 backend）+ Gemma 4 MTP         | 長 context agent 場景的完整堆疊 |
| LM Studio + Qwen3-Coder + speculative decoding | GUI 派 + 加速                   |

注意三件事：

1. Ollama 預設用 llama.cpp 當 backend，跟 MLX 沒關係。看到「Ollama 用 MLX 加速」這種句子要追問來源，多半是混淆。
2. oMLX 是少數真正把 MLX 用在 server 層的工具；它的賣點不是「MLX」本身，是 SSD KV cache。
3. MTP 是技巧層，可以疊在 Ollama 或 oMLX 上面，跟伺服器選擇正交。

## 網路上的常見混淆

下面是寫作本指南時掃過的常見錯誤說法，附正確版本：

1. ❌「llama.cpp 已整合 Gemma 4 MTP」
   - ✅ 2026 年 5 月時 llama.cpp 的 MTP 支援還在 beta，Gemma 4 drafter 還在 feature request 階段。Ollama 反而搶先支援，這是少見的「Ollama 比 llama.cpp 領先」情況。

2. ❌「MTP 加速 40%」
   - ✅ 官方數據是 2 ~ 3 倍加速，視任務而定。寫 code 接近 3x，純文字寫作只有 1.5x ~ 2x。「40%」這類數字來源不明，引用時要小心。

3. ❌「Ollama 用 MLX 比 llama.cpp 快」
   - ✅ Ollama 內部用 llama.cpp，不是 MLX。要用 MLX 當 backend 要選 oMLX 或自己 wrap mlx-lm。

4. ❌「oMLX 是 Ollama 的 MLX 版本」
   - ✅ oMLX 跟 Ollama 沒有 fork 關係。oMLX 的主要創新是 paged SSD KV cache，跟「換 backend 到 MLX」是不同的事情。

5. ❌「裝 MLX 就能跑 LLM」
   - ✅ MLX 只是 framework，要跑 LLM 還需要模型實作（`mlx-lm`）+ 模型權重 + 介面。對絕大多數使用者來說，直接用 Ollama 比較簡單。

## 給讀者的選擇順序

如果你只是想在 Mac 上寫 code，正確的選擇順序是：

1. 先裝 Ollama，跑 Gemma 4 31B MTP 或 Qwen3-Coder 30B。MTP 加速包含在 Ollama v0.23.1 內，不用額外設定。
2. 用一週後若覺得 TTFT 在塞長 context 時痛苦，再評估 oMLX。
3. MLX 本身對寫 code 場景的使用者來說，是抽象層下面的事；不用直接接觸。

不要本末倒置，一開始就鑽 MLX 細節或安裝 oMLX。先把日常路徑跑穩，再針對痛點做特化。

## 小結

MLX 是 framework，MTP 是技巧，oMLX 是特化 server，三者疊加而非互斥。看到網路上把它們混為一談的句子時，回到本章的三層定位就能精準判讀。

下一章：[0.5 Apple Silicon 記憶體預算](/llm/00-foundations/hardware-memory-budget/)，把心智模型對到自己 Mac 的真實規格。
