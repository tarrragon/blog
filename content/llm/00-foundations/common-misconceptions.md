---
title: "0.6 網路上的常見誤解"
date: 2026-05-11
description: "點名本地 LLM 圈最常見的錯誤說法，附正確理解與來源追溯方法"
tags: ["llm", "foundations", "misconceptions"]
weight: 6
---

本地 LLM 是近一兩年快速發展的領域，網路上資訊更新速度跟錯誤資訊產出速度都很快。本章把寫作本指南時掃過、實際讀者最常被誤導的說法整理成可對照的清單。每條都先給錯誤版本、再給正確版本、最後給判讀方法，避免下次遇到類似句子時又被帶歪。

讀完本章不代表你能識破所有錯誤資訊，但會建立一個基本反射：看到「N 倍加速」「能跑 X 大小模型」「換 model 就能 Y」這類絕對化句子時，自動回到前面章節的概念基底追問來源。

## 本章目標

讀完本章後，你應該能：

1. 辨識十個本地 LLM 圈最常見的錯誤說法。
2. 看到陌生的 LLM 技術說法時，建立追問來源的反射。
3. 知道哪些是「過時資訊」、哪些是「根本錯誤」。
4. 不再被 cherry-picked 的 benchmark 數字誤導。

## 誤解 1：llama.cpp 已整合 Gemma 4 MTP

**錯誤版本**：「llama.cpp 在 v0.5.x 已經支援 Gemma 4 MTP，本地推論速度直接 3 倍。」

**正確版本**：2026 年 5 月，llama.cpp 的 speculative decoding 支援還在 beta，Gemma 4 的官方 drafter 整合還是 feature request（GitHub issue 開著沒合）。Ollama 反而搶先在 v0.23.1（2026/5/7）支援 Gemma 4 MTP；這是少見的「Ollama 比底層 llama.cpp 領先」情境。

**判讀方法**：看到 X 支援 Y 的說法，先去 X 的 GitHub release notes 與 changelog 確認版本與時間；不要相信 Reddit 二手轉述。Ollama 的 release notes 在 `github.com/ollama/ollama/releases`，llama.cpp 在 `github.com/ggerganov/llama.cpp/releases`。

**為什麼這個誤解流行**：Ollama 用 llama.cpp 當 backend，多數人直覺以為 llama.cpp 是 Ollama 的「上游」，新功能應該先在 llama.cpp 出現。但 Ollama 維護自己的 fork、自己加 patch，反向 upstream 通常落後。

## 誤解 2：MTP 加速 40%

**錯誤版本**：「Gemma 4 開 MTP 後速度提升 40%。」

**正確版本**：Google 官方數據是 coding 任務 2 ~ 3 倍加速（200% ~ 300% 提升）。「40%」這類數字來源不明，可能是某個非典型 benchmark 或文章作者隨手寫的估算。

**判讀方法**：看到 N 倍 / N% 加速時，問三件事：

1. 什麼任務？coding、creative writing、數學推理的加速幅度差很多。
2. 什麼基準？跟「沒開 MTP」比，還是跟「另一個模型」比？
3. 什麼硬體？M4 Max 跟 M2 Pro 上的加速幅度不同。

Google 官方在 Gemma 4 技術報告中明確區分這些變數；社群文章常常省略。

## 誤解 3：換個 model 就能產圖

**錯誤版本**：「Ollama pull 一個 Stable Diffusion 模型就能在本地產圖。」

**正確版本**：產圖（Stable Diffusion、Flux、SDXL）用的是 **Diffusion 架構**，跟寫 code 用的 **Transformer 架構**是兩個完全不同的神經網路類型。架構不同、推論流程不同、伺服器不同、生態系不同：

1. Ollama / LM Studio 都不支援 Diffusion 模型。
2. 產圖工具是 ComfyUI、Draw Things、AUTOMATIC1111、Diffusers。
3. 產圖的硬體需求與 LLM 也不同（記憶體需求較低、但對 GPU 算力更敏感）。

**判讀方法**：看到「換 model 就能跑 X」的說法，先確認 X 跟原任務是不是同一個架構家族。LLM、產圖、語音合成、影片生成各自獨立，工具鏈不通用。

**本指南的立場**：先把寫 code 跑穩，再玩產圖。同時學兩個只會兩邊都半生不熟。

## 誤解 4：Ollama 只是聊天工具

**錯誤版本**：「Ollama 就是一個本地聊天 CLI，類似 ChatGPT 終端機版。」

**正確版本**：Ollama 是**本地推論伺服器**，預設聽 `localhost:11434`，提供 OpenAI 相容 API 與自家原生 API。`ollama run gemma4:31b` 看起來是 CLI，但背後啟動的是常駐 server；CLI 只是 client。看 [0.2 三層架構](/llm/00-foundations/three-layer-architecture/) 重新定位 Ollama 在伺服器層的角色。

**判讀方法**：看到 X 是「聊天工具」「終端機版 ChatGPT」這類描述時，去看它是否提供 HTTP API。提供 API 的就是伺服器，不只是介面。

**為什麼這個誤解重要**：把 Ollama 當聊天工具的話，你不會想到「用 VS Code 接 Ollama」這條路；用了三層架構視角，這條路就是自然的下一步。

## 誤解 5：本地 LLM 已能取代雲端

**錯誤版本**：「Gemma 4 31B 已經追上 GPT-4，雲端 API 月費可以省了。」

**正確版本**：本地最強模型（Gemma 4 31B、Qwen3-Coder 30B、gpt-oss 20B）大約等於 GPT-4 mini 或 Claude Haiku 4.5 等級。比雲端旗艦（Claude Sonnet 4.6、Opus 4.7、GPT-5）仍有明顯能力斷崖。

**判讀方法**：看到「追上」「達到」「取代」這類絕對說法，問：

1. 在什麼任務上追上？SWE-bench、HumanEval、MMLU 各自不同。
2. 拿什麼版本比？GPT-4o、GPT-4-turbo、GPT-5 是不同模型。
3. 是 cherry-picked 任務還是分佈式 benchmark？

更穩定的判斷方法：把自己一週實際工作的 5 ~ 10 個任務當 benchmark，本地模型跑一遍，看通過率。不要相信別人的 demo 截圖。

**正確心態**：本地 LLM 是免費的初階 pair programmer，不是 Claude 替代品。混用才是 2026 年的正確姿勢。

## 誤解 6：MLX 加速會比 llama.cpp 快

**錯誤版本**：「用 MLX backend 跑 LLM 比 llama.cpp 快很多，因為 Apple 原生。」

**正確版本**：MLX 跟 llama.cpp 在 Apple Silicon 上的效能各有勝負，差距通常在 10 ~ 30% 之內，不是「快很多」。llama.cpp 的 Metal backend 經過多年優化，跟 MLX 接近；MLX 在某些 kernel 與量化路徑上更快，但 Ollama / llama.cpp 的生態更成熟、坑更少。

**判讀方法**：看到 framework A 比 framework B 快 N 倍的說法，問是哪個模型、哪個量化、哪個硬體、哪個版本。同模型同量化同硬體的精確對照才有意義。

**實務建議**：對絕大多數使用者，這個差距不值得糾結。先用 Ollama 把日常路徑跑穩；只有「日常生字速度真的不夠用、且明確指向 backend」時才換 MLX 系統。

## 誤解 7：量化越激進越省記憶體就越好

**錯誤版本**：「24GB Mac 用 Q3 量化可以跑 70B 模型！」

**正確版本**：技術上能載入不代表能用。Q3 量化在 70B 模型上的品質衰減在 coding 任務上非常明顯，常常輸給同硬體上跑 Q5 的 14B 模型。「跑得起來」跟「跑得好」是兩件事。

**判讀方法**：看到極端量化的截圖時，要看實際輸出品質而不只是「跑起來」。下面是 coding 任務的經驗法則：

- Q8、Q5_K：品質損失幾乎察覺不到。
- Q4_K：可察覺但實用，是主流甜蜜點。
- Q3：明顯衰減，code 任務開始出錯。
- Q2：基本不能用於正經任務。

**為什麼這個誤解流行**：YouTube / Reddit 截圖容易給人「我也想試」的衝動，但 demo 場景跟你日常工作流不一定一致。

## 誤解 8：所有 OpenAI 相容工具能無縫互通

**錯誤版本**：「只要伺服器是 OpenAI 相容，所有功能都能用。」

**正確版本**：OpenAI 相容承諾的是 API 形狀（基本 chat completions）；不承諾進階功能（function calling 進階模式、structured output、reasoning effort、vision）的等價。本地伺服器多半實作了基本 chat completions，進階功能參差不齊。詳見 [0.3 OpenAI 相容 API](/llm/00-foundations/openai-compatible-api/)。

**判讀方法**：要用某個進階功能前，去伺服器與模型的文件確認支援程度。不要假設「OpenAI 文件有的本地都有」。

**實務建議**：日常寫 code 用基本 chat completions 就夠了，這部分本地通通支援。要用 structured output 或 function calling 強模型 / 強伺服器才能保證。

## 誤解 9：跑得起來就等於跑得好

**錯誤版本**：「我用 16GB Mac 跑 31B 模型啊，可以啊！」

**正確版本**：跑得起來常常意味著系統正在 swap、生字速度掉到 1 ~ 2 tok/s、其他 app 全部變慢。這種「跑得起來」不是日常可用配置。

**判讀方法**：本地 LLM 的可用性看三個指標：

1. **生字速度**：< 10 tok/s 體感像 dial-up，> 20 tok/s 才算流暢。
2. **首字延遲**：> 10 秒會打斷思路，< 3 秒接近順暢。
3. **整台 Mac 響應**：開 VS Code、切 tab、滑滑鼠是否仍順暢。

只看「能載入」忽略後續體感，是常見的自我安慰。

## 誤解 10：本地 LLM 完全沒有隱私風險

**錯誤版本**：「跑在本地，所以絕對私密，可以餵任何敏感資料。」

**正確版本**：本地推論伺服器確保 prompt 不會送到雲端，但隱私是一條鏈。實際風險包括：

1. **IDE plugin 雙送**：某些 IDE plugin 同時把 prompt 送本地 LLM 跟雲端服務，例如 Cursor 預設可能同時做 telemetry。
2. **對話紀錄**：Ollama 本身會 log，Open WebUI 會存資料庫。本機被入侵的話對話紀錄仍可能外洩。
3. **網路服務**：如果你開了 `OLLAMA_HOST=0.0.0.0` 讓區網存取，等於把本地 LLM 暴露在 LAN 上。
4. **第三方 plugin**：介面層的 plugin 可能把 prompt 送到第三方 telemetry。

**判讀方法**：把隱私視為「資料流」而不是「位置」。畫一張資料流圖，看 prompt 從鍵盤打進去到收到回應的過程經過多少 process / 服務 / 網路節點；每一節都是潛在洩漏點。

## 給讀者的反射訓練

下次看到本地 LLM 文章時，建議建立這些反射：

| 看到這類句子        | 立刻問                                       |
| ------------------- | -------------------------------------------- |
| 「N 倍加速」        | 什麼任務、什麼基準、什麼硬體、什麼版本？     |
| 「能跑 X 大小模型」 | 哪種量化、留多少給系統、長 context 還行嗎？  |
| 「換 model 就能 Y」 | Y 是不是同一個架構家族？                     |
| 「追上 / 達到雲端」 | 哪個雲端模型、哪個任務、有沒有 cherry-pick？ |
| 「絕對私密」        | 整條資料流誰能看到？                         |
| 「比 X 快」         | 同模型、同量化、同硬體、同版本嗎？           |
| 「最新支援」        | 去 release notes 確認版本與日期。            |
| 「免費」            | 硬體攤平要多久？電費、機會成本算了嗎？       |

把這張表存著，看新文章時對照一下。本地 LLM 領域變化太快，沒有反射的話會持續被誤導。

## 小結

本地 LLM 圈的常見誤解多半來自「混淆技術層級」「過時資訊」「cherry-picked benchmark」這三類。回到本指南的概念基底（[三層架構](/llm/00-foundations/three-layer-architecture/)、[MLX / MTP / oMLX 區分](/llm/00-foundations/mlx-mtp-omlx/)、[記憶體預算](/llm/00-foundations/hardware-memory-budget/)）能識破大多數誤導；對絕對化句子建立追問來源的反射，能擋下剩下的。

讀到這裡，模組零的心智模型就建立完了。下一步是 [模組一：本地 LLM 服務的安裝與應用](/llm/01-local-llm-services/)，把概念落地到實際安裝、整合 VS Code、選模型、做期望管理。
