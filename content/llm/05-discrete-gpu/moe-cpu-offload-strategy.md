---
title: "5.1 MoE 模型與 CPU 卸載策略"
date: 2026-05-12
description: "PC 場景把 MoE 不活躍專家層留在系統 RAM 的判讀：何時值得卸載、卸幾層、對 prefill 跟生成的影響各自不同"
tags: ["llm", "discrete-gpu", "moe", "cpu-offload", "llama-cpp"]
weight: 2
---

MoE CPU 卸載是 PC 場景相對 Mac 統一記憶體場景多出來的工程選項：把 [Mixture-of-Experts (MoE)](/llm/knowledge-cards/moe/) 模型不活躍的專家層權重留在系統 RAM、活躍時走 [PCIe](/llm/knowledge-cards/pcie/) 拉到 GPU。本章不再重複[卡片定義](/llm/knowledge-cards/moe-cpu-offload/)、而是處理「實際要不要用、用多少」的判讀。卸載判讀的關鍵變數是 [active parameter](/llm/knowledge-cards/active-parameter/) 比例。

讀完本章後、你應該能對自己的硬體配置回答：這個模型適不適合用 MoE 卸載、卸幾層是合理起點、卸到讓 prefill 變慢時該怎麼調、跟 KV cache 量化怎麼搭配。

## 本章目標

1. 理解 MoE 架構為什麼適合卸載（active parameter 少 ≠ 模型小）。
2. 判讀「該不該用 MoE 卸載」的工作流類型。
3. 知道卸載層數的調參範圍跟兩端的徵兆。
4. 區分卸載對 prefill 跟 generation 的影響差異。
5. 認識 llama.cpp 的 `--n-cpu-moe` 旗標與相關旗標的協作。

## MoE 架構為什麼適合卸載

MoE 模型適合卸載的關鍵是「總參數大、active parameter 小」這個結構特性：每個 token 只啟用少數專家、走 PCIe 的權重量遠小於 Dense 模型卸載同比例層數的傳輸量。卸載因此變成可行的工程選項、而不是「速度大幅下降的退路」。

對比 Dense 模型：Dense 模型每個 token 都會用到所有層的所有權重、任何一層放到 RAM 都會讓每個 token 等 PCIe 拉回來、生字速度衰減較明顯。MoE 在每個 transformer block 內把 FFN（feed-forward network）拆成多個「專家」、router 為每個 token 挑選少數啟用、不啟用的專家權重留在 RAM 不參與計算。

MoE 卸載成立的三個結構要點：

1. **總參數大、active parameter 小**：例如 Qwen3-30B-A3B 的 A3B 表示 active parameter 約 3B、總參數約 30B、每個 token 只走 ~10% 的權重。
2. **每 token 走 PCIe 的權重量大幅縮減**：不活躍的專家權重留在 RAM、不參與本 token 的計算。具體幅度依模型 active 比例變化、可透過 [量化](/llm/knowledge-cards/quantization/) 再進一步壓縮。
3. **共用層（[attention](/llm/knowledge-cards/attention/)、layernorm）放 VRAM**：這些是每 token 必經、放 VRAM 確保速度上限不被拉低、跟 [KV cache](/llm/knowledge-cards/kv-cache/) 一起佔用 VRAM 主要區段。

> **事實查核註**：MoE 模型的 active / total parameter 比例依模型而異（Qwen3-30B-A3B、Llama 4 Scout、DeepSeek V3 等各有不同設計）。具體比例見各模型的官方技術報告或 Hugging Face model card。

對照 Dense 模型的卸載（在 llama.cpp 中、Dense 模型可以用 `-ngl` 控制放 GPU 的層數、剩下走 CPU）：Dense 卸載每 token 都要傳輸卸載層權重、生字速度衰減較明顯；MoE 卸載每 token 只傳輸啟用的專家、衰減較小。社群常見回報指出「MoE 卸載比 Dense 同比例卸載友善」、但具體幅度依模型架構（專家數、active 比例）變化、需用 `llama-bench` 校準。

## 何時值得用 MoE 卸載

MoE 卸載的主要用途是「處理 VRAM 容量不足以全載目標模型」的場景。當模型已能全載 VRAM、卸載通常會降低生字速度而沒有對應的收益。下表整理常見的判讀情境：

| 場景                                           | 是否值得卸載            | 主要考量                                                              |
| ---------------------------------------------- | ----------------------- | --------------------------------------------------------------------- |
| 16GB VRAM 想跑 30B 級 MoE 模型                 | 值得                    | 沒卸載則 VRAM 不足以載入                                              |
| 24GB VRAM 跑 30B 級 MoE                        | 視 context 跟併發數需求 | 全載也許可行、卸載可換取更大 context 或更多併發                       |
| 16GB VRAM 跑 14B Dense                         | 通常不需要              | 模型已可全載 VRAM、卸載反而降速                                       |
| 跑 70B 級 MoE 模型                             | 多數情況需要卸載        | 即使 32GB VRAM 也通常需要部分卸載                                     |
| 高頻短補完工作流（追求即時補完）               | 評估、可能不適合        | 卸載會降速、若工作流對即時體感敏感、改用較小 Dense 模型全載可能更合適 |
| 長 context 工作流（大型 codebase RAG、長對話） | 值得                    | 卸載換 VRAM 給 KV cache、能開更大 context                             |

判讀原則：**先確認瓶頸是「模型載不進」還是「速度不夠」**。前者卸載是解法、後者卸載通常會惡化問題、應該往別的方向調（選較小模型、升級顯卡、提高量化等級）。

## 卸載層數的調參範圍

llama.cpp 的 `--n-cpu-moe <N>` 旗標表示「把 N 層的 MoE 專家權重放 CPU 記憶體」。實際範圍取決於模型結構：

1. **下限**：0、表示所有 MoE 專家層都在 VRAM。對 16GB VRAM + 30B MoE 而言通常不可行（VRAM 不足）。
2. **上限**：模型的 MoE 層總數、表示所有 MoE 層的專家都在 CPU。對應 VRAM 佔用最低、生字速度也最低。

調參的兩端徵兆：

| 徵兆                                           | 表示                         | 建議調整                               |
| ---------------------------------------------- | ---------------------------- | -------------------------------------- |
| llama.cpp 報 CUDA OOM、模型載入失敗            | VRAM 餘量不足                | 增加 `--n-cpu-moe`、把更多層放 RAM     |
| 模型載入成功、但 KV cache 開不大、context 受限 | VRAM 餘量足、但邊際空間少    | 增加 `--n-cpu-moe`、或開 KV cache 量化 |
| 生成速度顯著低於對應 VRAM 頻寬的理論值         | 卸載過多、PCIe 跟 CPU 在拖速 | 減少 `--n-cpu-moe`、把更多層放回 VRAM  |
| 系統 RAM 接近上限、page cache 被擠壓           | 卸載量超出 RAM 容量          | 減少 `--n-cpu-moe`、或升級 RAM         |

常見起點：對 16GB VRAM + 64GB RAM 跑 30B 級 MoE 模型、社群常見回報的 `--n-cpu-moe` 落在 25 ~ 35 區間、具體值依模型 MoE 層數而定。建議從中間值（如 30）起步、再依 OOM / 速度徵兆雙向調整。

## 卸載對 prefill 跟 generation 的影響不同

[prefill](/llm/knowledge-cards/prefill/) 跟 generation 是兩個不同的計算階段、對卸載的反應也不同：

1. **prefill（處理 prompt）**：一次處理整個 prompt、可用 batch 平行化、屬於 compute-bound 階段。卸載對 prefill 的衰減相對小、因為 batch 大可以攤平 PCIe 傳輸成本。
2. **generation（生字）**：一個 token 接一個 token、每 token 都要走完整個 forward pass、屬於 memory-bandwidth-bound 階段。卸載對 generation 的衰減較明顯、因為每 token 都要走 PCIe 拉部分權重。

實務影響：

- **長 prompt + 短回答**（如「總結這份 codebase」）：prefill 主導總時間、卸載的代價較小。
- **短 prompt + 長回答**（如「從 spec 寫一段功能」）：generation 主導、卸載的代價較大、可能適合用較小 Dense 模型全載。
- **互動式補完**（每幾秒一次短 prompt 短回答）：prefill 跟 generation 都重要、卸載的整體成本依工作流節奏而定。

> **事實查核註**：prefill 跟 generation 的具體 t/s 差異依模型、量化、batch size、CUDA backend 變化；建議用 `llama-bench` 或實際工作流任務分別校準。

## 跟 KV cache 量化的協調

MoE 卸載騰出 VRAM、KV cache 量化讓騰出的 VRAM 拿去開大 context。兩者的關係是「先後」而非「替代」：

```text
總 VRAM 預算
├── 模型權重（活躍部分）= 由 --n-cpu-moe 決定
├── KV cache             = 由 -c (context) × cache-type 決定
└── 推論中間結果         = 通常固定
```

調參順序（社群常見做法）：

1. **先決定目標 context 長度**：例如 32K、128K、256K。
2. **估算 KV cache 體積**：依模型 attention head 配置、context 長度、量化等級。具體值用 llama.cpp 啟動時的 log 確認。
3. **算出 VRAM 餘量**：總 VRAM − KV cache − 推論中間結果。
4. **決定 `--n-cpu-moe`**：讓「模型權重活躍部分」放得進 VRAM 餘量。

如果做完上面四步發現 VRAM 仍不夠、就回頭調 KV cache 量化（K=fp16 → Q8 → Q4_0）、或降低 context 長度。

詳細的 KV cache 量化判讀見 [5.2 KV cache 量化策略](/llm/05-discrete-gpu/kv-cache-quantization-strategy/)。

## llama.cpp 的相關旗標

跑 MoE 卸載時、常一起出現的旗標：

| 旗標                    | 作用                                      | 對 MoE 卸載的關係                               |
| ----------------------- | ----------------------------------------- | ----------------------------------------------- |
| `-ngl <N>`              | 把 N 層丟到 GPU（Dense + MoE 共用層）     | 通常設成 99 或 max、表示所有可放 GPU 的都放 GPU |
| `--n-cpu-moe <N>`       | 把 N 層的 MoE 專家權重保留在 CPU 記憶體   | MoE 卸載的核心旗標                              |
| `--cache-type-k <type>` | KV cache 中 K 的量化（如 `q8_0`、`q4_0`） | 用於騰出 VRAM 給更大 context                    |
| `--cache-type-v <type>` | KV cache 中 V 的量化                      | 用於騰出 VRAM 給更大 context                    |
| `-c <N>`                | context window 大小                       | 跟 KV cache 體積線性相關                        |
| `--parallel <N>`        | 併發處理數                                | 高併發會增加 KV cache 體積、需重新調預算        |
| `-b <N>` / `-ub <N>`    | batch size / micro-batch size             | 影響 prefill 速度與記憶體用量                   |

完整旗標清單見 [llama.cpp 官方文件](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)；版本更新後參數名稱可能變動、以實際 `llama-server --help` 為準。

## 給讀者的判讀步驟

實際設定 MoE 卸載時、可以照下面的步驟調：

1. **確認模型適合 MoE 卸載**：模型是 MoE 架構（如 Qwen3-30B-A3B、Llama 4 Scout、DeepSeek V3 系列）、且總參數量明顯超過 VRAM 容量。
2. **抓取 GGUF 量化版本**：寫 code 場景的常見起點是 Q4_K_M、品質 / 體積平衡較好。
3. **設定起點旗標**：

   ```bash
   llama-server -m <model.gguf> -ngl 99 --n-cpu-moe 30 \
     --cache-type-k q8_0 --cache-type-v q4_0 -c 32768
   ```

4. **觀察啟動 log**：llama.cpp 會列出「實際載入 VRAM 的層數」「KV cache 體積」「剩餘 VRAM」。
5. **跑 `llama-bench` 校準**：用同樣的旗標跑 prefill / generation benchmark、記錄 t/s。
6. **依瓶頸調整**：
   - 想開更大 context → 加大 `-c`、若 VRAM 不足則加 `--n-cpu-moe` 或量化 KV cache
   - 想要更快生字 → 減 `--n-cpu-moe`、確認 VRAM 仍夠
   - VRAM OOM → 加 `--n-cpu-moe` 或降量化

完成這六步後、再進入 [5.3 llama.cpp 在 PC 上](/llm/05-discrete-gpu/llama-cpp-on-pc/) 了解更全面的旗標組合。

## 下一章

下一章：[5.2 KV cache 量化策略](/llm/05-discrete-gpu/kv-cache-quantization-strategy/)、深入 K=Q8 / V=Q4 跟 context 長度的權衡。
