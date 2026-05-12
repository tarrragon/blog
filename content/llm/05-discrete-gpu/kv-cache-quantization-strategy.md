---
title: "5.2 KV cache 量化策略"
date: 2026-05-12
description: "PC 場景用 K=Q8 / V=Q4 等量化把 KV cache 壓縮、騰出 VRAM 開大 context window 或加併發數的判讀"
tags: ["llm", "discrete-gpu", "kv-cache", "quantization", "context-window"]
weight: 3
---

KV cache 量化是 PC 場景開大 context 或提高併發數的常用工程選項：把 [KV cache](/llm/knowledge-cards/kv-cache/) 從 fp16 壓到 Q8 或 Q4、體積大幅縮減、騰出的 VRAM 拿去開長 [context](/llm/knowledge-cards/context-window/)、加併發、或載入更大模型。本章不重複[卡片定義](/llm/knowledge-cards/kv-cache/)、改處理「實際要不要量化、量化到哪一級」的判讀。卡片視角的 [量化](/llm/knowledge-cards/quantization/) 跟本章的 KV cache 量化是兩個方向：前者壓模型權重、後者壓推論時的 attention 暫存。

讀完本章後、你應該能對自己的工作流回答：KV cache 量化的好處能換到什麼、品質代價落在什麼範圍、K 跟 V 為什麼建議不同等級、跟 context 長度跟併發數怎麼搭配。

## 本章目標

1. 理解 KV cache 為什麼會隨 context 線性膨脹、為什麼 PC 場景常需要量化。
2. 區分 K 跟 V 在 attention 計算中的角色、解釋為何兩者對量化的容忍度不同。
3. 判讀「該不該量化 KV cache」的工作流類型。
4. 認識 llama.cpp 的 `--cache-type-k` / `--cache-type-v` 旗標與相關限制（如 flash attention 要求）。
5. 知道調參時的觀察訊號跟取捨方向。

## KV cache 為什麼會膨脹

LLM 推論時、每處理一個 token 都會把該 token 的 key 跟 value 向量算出來、暫存進 KV cache、供後續 token 的 attention 計算複用（不重算）。KV cache 的體積跟下面幾個變數線性相關：

```text
KV cache 體積 ≈ 2 × n_layers × n_heads × head_dim × bytes_per_value × context_長度 × batch
```

- 2：分別是 K cache 跟 V cache
- n_layers / n_heads / head_dim：模型結構參數
- bytes_per_value：fp16 是 2 bytes、Q8_0 約 1 byte、Q4_0 約 0.5 byte
- context_長度：context 開多大、KV cache 就放多大
- batch：併發處理多少 sequence

實際 KV cache 體積依模型 attention 變體（MHA / GQA / MLA）、head 數設計、量化方式而變。比起背公式、更實用的做法是看 llama.cpp 啟動時的 log、它會列出實際 KV cache 配置的記憶體：

```text
llm_load_print_meta: n_layer    = 48
llm_load_print_meta: n_head     = 32
llama_kv_cache_init: KV self size = 2048.00 MiB, K (q8_0): 1024.00 MiB, V (q8_0): 1024.00 MiB
```

> **事實查核註**：上面的 log 格式跟欄位名稱依 llama.cpp 版本變動、實際輸出以執行時為準。常見模型的 KV cache 估算工具可參考 [llama.cpp 官方文件](https://github.com/ggml-org/llama.cpp) 或社群維護的 calculator。

## K 跟 V 為什麼適合用不同量化等級

K 跟 V 在 attention 計算中扮演不同角色、對量化的容忍度也不同。K 參與內積比較（量化容忍度通常較高）、V 是被加權平均的輸出內容（量化誤差會線性累積）、社群常見做法是 K 用較激進的量化、V 保留較高精度。

attention 的計算流程簡化為：

```text
attention(Q, K, V) = softmax(Q · K^T / √d) · V
```

K 跟 V 在這個流程中的角色差異：

1. **K（key）**：用來跟 Q 算內積、產生 attention score。內積本質是「相對量級的比較」、量化造成的微小誤差容易在 softmax 後被吸收。
2. **V（value）**：是被 softmax 加權平均後直接輸出的內容、量化誤差會線性累積進輸出。

社群多數回報指出：

- **K 用 Q8_0 或 Q4_0 對品質影響相對小**：因為 softmax 對輸入量級的敏感度集中在最大值附近、其他位置的小幅誤差會被指數壓縮。
- **V 用 Q4_0 在長 context 末尾較易出現品質下降**：因為 V 是被加權平均的內容、累積誤差會在輸出中可見。

> **事實查核註**：K 跟 V 對量化敏感度不同的論述、來自社群常見回報跟若干針對 KV cache 量化的論文（如 KIVI、KVQuant 等）。具體影響因模型架構、量化方法（symmetric / asymmetric、per-head / per-channel scale 等）變化、不同模型的表現可能不一致；建議用自己工作流的任務跟自己選定的量化版本實測校準。

## KV cache 量化等級對照

llama.cpp 支援的常見 KV cache 量化等級：

| 量化等級 | bytes/value（約） | 相對 fp16 體積 | 社群常見用途                         |
| -------- | ----------------- | -------------- | ------------------------------------ |
| `fp16`   | 2                 | 100%           | 預設、品質基準                       |
| `q8_0`   | 1                 | 50%            | K 的常見起點、品質衰減社群回報為小幅 |
| `q5_1`   | ~0.7              | ~35%           | 中間選項                             |
| `q5_0`   | ~0.7              | ~35%           | 中間選項                             |
| `q4_1`   | ~0.5              | ~25%           | V 的常見極限                         |
| `q4_0`   | ~0.5              | ~25%           | V 的常見起點、品質衰減較 Q5 略大     |

常見組合（社群回報、需自行校準）：

- **保守（品質優先）**：K=fp16、V=fp16。完全不量化、VRAM 用量最大。
- **平衡起點**：K=Q8_0、V=Q8_0。體積約一半、品質衰減社群多數回報為小幅或不明顯。
- **激進（context 優先）**：K=Q8_0、V=Q4_0。體積約 fp16 的 35%、社群回報短 prompt 影響小、長 prompt 末尾可能出現品質下降。
- **極限**：K=Q4_0、V=Q4_0。體積約 fp16 的 25%、用於開超大 context 或極高併發、品質風險最高。

## 何時值得量化、何時不該量化

KV cache 量化的主要用途是「VRAM 不足以同時放下模型權重 + 目標 context 長度 + 目標併發數」的場景。當 VRAM 已有充裕餘量、量化省下的 VRAM 沒有對應的用途時、保留 fp16 通常較合適。下表整理常見的判讀情境：

| 場景                                  | 是否值得量化      | 主要考量                                                    |
| ------------------------------------- | ----------------- | ----------------------------------------------------------- |
| 寫 code、補完、跨檔案重構             | 值得（K=Q8/V=Q4） | 程式碼合法性約束會過濾小幅誤差、社群回報品質影響小          |
| RAG（大型 codebase 索引、長文件摘要） | 值得              | context 通常很長、KV cache 是 VRAM 主要瓶頸                 |
| 自由創作（小說、長對話、詩）          | 評估、可能不適合  | V 量化的累積誤差較易在創作品質上感知                        |
| 數學 / 邏輯推理（chain-of-thought）   | 從保守起點        | 推理鏈累積誤差較敏感、建議從 K=Q8 / V=Q8 起步、再依任務評估 |
| 短 prompt 短回答（< 4K context）      | 不必要            | KV cache 體積本來就小、量化省下的 VRAM 不多                 |
| 對品質高度敏感的研究或產品任務        | 從保守起點        | 先用 fp16 建立品質基準、再依需求逐步量化、確認品質可接受    |

判讀原則：**先確認瓶頸是「VRAM 不夠」還是「品質不夠」**。前者量化是解法、後者量化通常會惡化問題。

## 跟 context 長度、併發數的協調

KV cache 量化的好處要跟其他 VRAM 用量一起評估。常見的取捨方向：

1. **量化 → 開更大 context**：把省下的 VRAM 用在加大 `-c`、能開長 prompt（如 RAG、長對話、跨檔案分析）。
2. **量化 → 加併發**：把省下的 VRAM 用在加 `--parallel`、能同時服務多個 client（如多個編輯器視窗、多 agent）。
3. **量化 → 載入更大模型**：把省下的 VRAM 用在降 `--n-cpu-moe`、減少卸載、提升生字速度。

三者通常不能同時極大化、需要依工作流挑主軸。

實務上的常見搭配（社群回報、需校準）：

| 工作流                | 建議搭配                                                   |
| --------------------- | ---------------------------------------------------------- |
| 單人寫 code、補完為主 | K=Q8 / V=Q4、context 32K ~ 128K、`--parallel 1 ~ 2`        |
| RAG 大型 codebase     | K=Q8 / V=Q4、context 128K ~ 256K、`--parallel 1`           |
| 多 agent / 多視窗並用 | K=Q8 / V=Q4 或更激進、context 32K、`--parallel 4 ~ 8`      |
| 對話品質敏感、純創作  | K=Q8 / V=Q8 起步、context 適中、依品質確認再決定是否加量化 |

## llama.cpp 的相關旗標

跑 KV cache 量化時、常用的旗標：

| 旗標                          | 作用                                         | 備註                                                  |
| ----------------------------- | -------------------------------------------- | ----------------------------------------------------- |
| `--cache-type-k <type>`       | K cache 量化（如 `f16`、`q8_0`、`q4_0`）     | 預設 f16                                              |
| `--cache-type-v <type>`       | V cache 量化                                 | 預設 f16                                              |
| `-fa` / `--flash-attn`        | 啟用 flash attention                         | 部分量化組合需要 flash attention 才能啟用、見下方說明 |
| `-c <N>`                      | context window 大小                          | KV cache 體積跟此線性相關                             |
| `--parallel <N>`              | 併發處理數                                   | KV cache 體積跟此線性相關                             |
| `-ctk <type>` / `-ctv <type>` | `--cache-type-k` / `--cache-type-v` 的短旗標 | 同義、版本依 llama.cpp 變動                           |

### flash attention 的關係

部分 KV cache 量化組合（特別是 V=Q4_0 / Q4_1）在 llama.cpp 上需要同時啟用 flash attention（`-fa`）才能正常運作；沒啟用時可能載入失敗或 fallback 到 fp16。具體要求依 llama.cpp 版本變化、以實際 `llama-server --help` 跟 [llama.cpp 官方 issue / PR](https://github.com/ggml-org/llama.cpp/pulls?q=is%3Amerged+kv+cache+quant) 為準。

> **事實查核註**：flash attention 對 KV cache 量化組合的限制、是 llama.cpp 實作層面的演進議題、不是模型本身的限制。新版 llama.cpp 可能放寬或改變要求、引用前以最新版的 release notes 為準。

## 給讀者的調參步驟

實際設定 KV cache 量化時、可以照下面的步驟調：

1. **先用 fp16 基準跑一次**：用實際工作流的代表性任務、記錄補完品質、執行時間、VRAM 用量。這是後續比較的基準。
2. **切到 K=Q8 / V=Q8**：跑同樣的任務、比較品質。社群多數回報差異不明顯、但需以自己工作流確認。
3. **進一步切到 V=Q4**：再跑同樣任務、特別注意長 prompt 末尾、推理鏈、複雜邏輯任務的輸出品質。
4. **若品質可接受、評估省下的 VRAM 怎麼用**：加大 `-c`、提高 `--parallel`、或減少 `--n-cpu-moe`。
5. **建立可重複的校準腳本**：把代表性任務寫成 prompt 集、做為日後升級模型或調參時的回歸測試。

## 小結

KV cache 量化是 PC 場景換取 context 長度、併發數或 VRAM 餘量的工程選項、不是必選配置。K 跟 V 對量化的容忍度社群回報不同、K=Q8 / V=Q4 是寫 code 場景常見起點；品質敏感的工作流建議從保守組合起步、再依實測逐步調整。flash attention 對部分量化組合是必要前置、實際限制以 llama.cpp 當前版本為準。

下一章：[5.3 llama.cpp 在 PC 上](/llm/05-discrete-gpu/llama-cpp-on-pc/)、把本章跟 [5.1 MoE 卸載](/llm/05-discrete-gpu/moe-cpu-offload-strategy/) 的旗標放進完整的 llama.cpp 調參工作流。
