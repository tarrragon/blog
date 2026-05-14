---
title: "0.1 為什麼 LLM 生字慢"
date: 2026-05-11
description: "自回歸架構與記憶體頻寬瓶頸：為何即使 Mac 算力很強，本地 LLM 仍一個字一個字吐"
tags: ["llm", "foundations", "performance"]
weight: 1
---

LLM 生字慢的核心原因有兩個：**[自回歸架構](/llm/knowledge-cards/autoregressive/)**（autoregressive）讓模型一次生一個 [token](/llm/knowledge-cards/token/)、**[記憶體頻寬](/llm/knowledge-cards/memory-bandwidth/)瓶頸**讓 Apple Silicon 在算力之外有一個獨立的速度上限。這兩個瓶頸結合起來、才能解釋為什麼 32GB Mac 跑 31B 模型約 30 [tok/s](/llm/knowledge-cards/tokens-per-second/)、而資料中心的 H100 跑同樣模型能到 200 tok/s。

理解這個機制不只是為了知識本身。後續所有加速技巧（[speculative decoding](/llm/knowledge-cards/speculative-decoding/)、[MTP](/llm/knowledge-cards/mtp/)、[KV cache](/llm/knowledge-cards/kv-cache/)、[量化](/llm/knowledge-cards/quantization/)）都是在攻擊這兩個瓶頸的不同部分；不懂瓶頸在哪，看到「2x 加速」「3x 加速」這種廣告詞就無從判讀。

## 本章目標

讀完本章後，你應該能回答：

1. 為什麼 LLM 採用「一個 token 接一個 token」的生成方式、而非整段一次生出？
2. 為什麼 Apple Silicon 的「[統一記憶體](/llm/knowledge-cards/unified-memory/)」對 LLM 推論是優勢？
3. 為什麼[模型量化](/llm/knowledge-cards/quantization/)能加速、而非只是省記憶體？
4. 為什麼長 prompt 的[首字延遲](/llm/knowledge-cards/ttft/)特別有感？

## 自回歸架構：一次只能吐一個 token

自回歸的核心概念是「下一個 token 的生成需要前面所有 token 的結果」。模型每生成一個 token，都要把目前已有的 token 序列（你的 prompt + 它已經生成的部分）重新丟進神經網路算一次，得到下一個 token 的機率分佈，挑一個輸出，然後重複。

舉個具體例子。當你輸入 `寫一個 Python function 計算費氏數列`，模型生成回答的過程大致是：

1. 把 prompt 丟進模型，產出第一個 token，例如 `def`。
2. 把 prompt + `def` 丟進模型，產出 `fib`。
3. 把 prompt + `def fib` 丟進模型，產出 `(`。
4. 一直重複到模型決定產出結束 token。

每一步都要跑一次完整的神經網路 forward pass（神經網路把輸入資料從第一層算到最後一層、產出輸出的單次計算）。這就是為什麼回答長度直接影響等待時間、跟雲端旗艦模型一樣；差別只是雲端每個 forward pass 跑得更快。

陷阱是把自回歸跟 streaming 混淆。Streaming 只是把已產出的 token 即時顯示在畫面上，看起來「邊想邊說」；模型內部該跑幾次 forward pass 就是幾次，streaming 不會加速生成本身。

## 記憶體頻寬：Apple Silicon 真正的瓶頸

LLM 推論的瓶頸幾乎一定落在記憶體頻寬、而不是算力。原因是每生成一個 token 都要把整個模型的權重從記憶體讀到處理器一次；模型有多大、每秒能讀多少 GB、就決定了每秒能吐幾個 token。每生一個 token 都要把整份權重讀過一次、所以「每秒能讀完幾份權重」就是「每秒能吐幾個 token」。

模型大小的換算規則很簡單：bf16 每個權重佔 2 bytes、Q4 量化後每個權重約 0.5 byte。所以：

- Gemma 4 31B 的 bf16 權重約 62GB（31B × 2 bytes）、Q4 量化後約 18GB。
- M4 Max 的記憶體頻寬約 546 GB/s、M2 Pro 約 200 GB/s。
- 理論上限 = 頻寬 / 模型大小。M4 Max 跑 Q4 量化 31B 模型、理論上限約 546 / 18 ≈ 30 tok/s。

實際數字會比理論上限低 30 ~ 50%（attention 機制的 KV cache 也要讀寫、有些運算需要中間結果），所以 M4 Max 跑 Q4 31B 大約落在 20 ~ 25 tok/s。這個推導讓你看到任何「在 Mac 上跑 70B 模型很快」的說法時，可以直接用頻寬算一下合不合理。

Apple Silicon 的**[統一記憶體](/llm/knowledge-cards/unified-memory/)**（Unified Memory Architecture, UMA）讓 CPU、GPU、Neural Engine 共用同一塊記憶體、省下跨 PCIe 搬資料的成本。傳統 PC + NVIDIA GPU 的記憶體分成系統記憶體跟 VRAM；模型權重要放進 VRAM 才能用 GPU 跑、跨 PCIe 搬資料的速度成本很高。Mac 的 64GB 統一記憶體可以幾乎全部給模型用（扣掉系統保留部分）、同等價位的 PC 通常只有 12GB ~ 24GB VRAM。

這就是為什麼 Mac 在「跑得動多大的模型」上佔優勢，但在「跑多快」上輸給 H100。H100 的 HBM 頻寬約 3,300 GB/s，是 M4 Max 的 6 倍。能跑得動 vs 跑得快，是兩件事。

## 量化：用精度換頻寬

量化的核心是把模型權重從 16-bit float 壓成 4-bit、5-bit、8-bit integer。權重數量不變，但每個權重佔的 bytes 變少；模型總大小變小，每秒能讀過的權重變多，生字速度直接變快。

常見量化等級：

| 量化 | 每權重 bits | 相對 bf16 大小 | 品質衰減                             | 適合場景                            |
| ---- | ----------- | -------------- | ------------------------------------ | ----------------------------------- |
| bf16 | 16          | 1x             | 無（基準）                           | 開發、評估、有大量記憶體            |
| Q8   | 8           | 0.5x           | 幾乎不可察覺                         | 32GB+ Mac、品質敏感任務             |
| Q5_K | 5           | 0.31x          | 輕微                                 | 24GB Mac、日常使用                  |
| Q4_K | 4           | 0.25x          | 可察覺但實用                         | 16 ~ 24GB Mac、最常用甜蜜點         |
| Q3   | 3           | 0.19x          | 明顯、coding 任務 hallucination 上升 | 記憶體緊張時的權宜選擇、coding 慎用 |

接近真實的選擇：

- 32GB Mac 跑 31B 模型：選 Q4_K，記憶體佔用 ~ 18GB，留 14GB 給系統與 IDE。
- 24GB Mac 跑 14B 模型：選 Q5_K 或 Q4_K，看任務品質要求。
- 16GB Mac 跑 7B 模型：選 Q4_K，是現實上界。

陷阱是把量化等級拉到極限以塞下更大模型。Coding 任務上 Q3 的 31B 模型常輸給 Q5 的 14B 模型；模型「夠大」跟「夠好」是兩件事、選 model size 時先看任務通過率、再用量化等級調記憶體。後續 [模型選型章節](/llm/01-local-llm-services/model-selection-priority/) 會展開這個取捨。

## KV cache 與長 prompt 痛點

[KV cache](/llm/knowledge-cards/kv-cache/)（key-value cache）把 attention 機制每個 token 產生的中間結果暫存、後續 token 生成時直接讀 cache 跳過重算、讓「已經算過的 prompt」省下重複跑 forward pass。

但 KV cache 有兩個性質會放大長 prompt 的痛點：

1. **首次處理 prompt 時要完整算過一次**、這個階段稱為 **[prefill](/llm/knowledge-cards/prefill/)**。10K token 的 prompt 在本地可能需要 30 ~ 90 秒才 prefill 完、這 30 ~ 90 秒就是 [TTFT](/llm/knowledge-cards/ttft/) 的主要來源。
2. **KV cache 本身佔記憶體**：長 [context](/llm/knowledge-cards/context-window/) 跑下來、KV cache 可能比模型權重還大、會擠壓可用記憶體。

這就是為什麼 coding agent 場景（塞整個 repo 進 prompt）在本地特別痛：每次都要重新 prefill，每次都等 30 ~ 90 秒。oMLX 這類特化伺服器就是針對這個痛點，用 paged SSD KV cache 把已 prefill 過的 context 存到 SSD，下次同樣的 prompt 前綴可以直接讀 cache，把 TTFT 從 30 ~ 90 秒降到 1 ~ 3 秒。詳見 [0.4 MLX / MTP / oMLX](/llm/00-foundations/mlx-mtp-omlx/)。

## Speculative decoding 與 MTP

既然瓶頸是「每生一個 token 都要讀一次完整模型權重」、那能否一次生多個 token？[speculative decoding](/llm/knowledge-cards/speculative-decoding/)（推測解碼）就是這個想法的具體實作。

機制大致是：

1. 用一個小模型（[drafter](/llm/knowledge-cards/drafter-model/)、例如 1B 參數）快速猜未來 N 個 token。
2. 把這 N 個 token 一次餵給大模型（target、例如 31B 參數）、讓大模型並行驗證每個位置的機率分佈。
3. 大模型保留認同的前綴、從第一個拒絕點之後重新生成。

這個機制能加速的關鍵是「大模型的驗證可以並行」。一次 forward pass 驗證 N 個 token 的時間，跟驗證 1 個 token 的時間差不多（因為瓶頸是讀權重，不是算力）。如果接受率高，等於一次 forward pass 產出多個 token。

寫 code 場景特別適合 speculative decoding、因為 code 有大量可預測 pattern（縮排、括號、常見變數名、import 語句）、小模型猜對的接受率高。Google 為 Gemma 4 釋出官方 drafter、官方數據在 coding 任務有 2 ~ 3 倍加速；接受率低的任務（純創意寫作、隨機字串生成）加速幅度可能降到 1.5 倍左右、加速倍數跟任務 pattern 強相關。

**[Multi-Token Prediction](/llm/knowledge-cards/mtp/)**（MTP）是這個概念的具體實作、本質是 speculative decoding 的工程化版本。下一章 [0.4 MLX / MTP / oMLX](/llm/00-foundations/mlx-mtp-omlx/) 會把 MTP 跟其他容易混淆的術語放在一起對照。

## 何時這套推導失準

「頻寬決定生字速度」是 dense 模型 + 單請求情境下的乾淨推導。實務上有三類情境會讓這個公式失準、解讀效能數字時要對應調整：

1. **MoE 模型（Mixture of Experts）**：每個 token 只啟用部分專家層、實際讀的權重遠小於總權重。例如 Mixtral 8x7B 名義 46B 參數、但每個 token 只啟用約 12B、速度上限要用「啟用權重」算、不是總權重。判讀 MoE 模型在 PC 獨立 GPU 上的部署細節見 [MoE CPU 卸載](/llm/knowledge-cards/moe-cpu-offload/)。
2. **多請求 batching**：資料中心級推論伺服器把多請求 batch 一起跑、權重讀一次處理 N 個 token、攤平頻寬成本。本章開頭舉的「H100 跑 200 tok/s」是 batch=1 的單 user 數字、production 場景 batch=32 時單 user 看到的速度更接近 50 tok/s、但 total throughput 翻 N 倍。詳見 [batching 卡片](/llm/knowledge-cards/batching/)。
3. **Speculative decoding 接受率變動**：MTP / drafter 的加速幅度跟任務 pattern 強相關、coding 任務的 2 ~ 3 倍無法直接 carryover 到創意寫作、看 benchmark 數字時要追問「跑的是哪類任務」。

判讀效能數字時的反射動作：先問「dense 還是 MoE」「batch 多少」「任務 pattern 強弱」、再決定能不能套頻寬公式。

## 小結

LLM 生字慢的根源是自回歸架構（一次只能吐一個 token）與記憶體頻寬瓶頸（每個 token 都要讀一次完整模型權重）。Apple Silicon 的統一記憶體讓 Mac 在「能跑多大」上佔優勢，但頻寬仍輸給資料中心 GPU，所以「跑得多快」會有量級差距。

量化（用精度換頻寬）、KV cache（避免重算）、speculative decoding / MTP（並行驗證多個 token）都是攻擊這兩個瓶頸的具體技巧；後續看到任何「N 倍加速」的廣告詞，回到這兩個瓶頸推導一次就知道合不合理。

下一章：[0.2 三層架構](/llm/00-foundations/three-layer-architecture/)，把任何本地 LLM 工具放回正確的層級。
