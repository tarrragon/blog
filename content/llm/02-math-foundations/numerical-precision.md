---
title: "2.3 數值精度與量化的數學依據"
date: 2026-05-11
description: "fp32 / bf16 / fp16 / int8 / int4 的差別、量化能省哪些 bits、品質衰減從哪裡來"
tags: ["llm", "math", "numerical-precision"]
weight: 3
---

[量化](/llm/knowledge-cards/quantization/) 是讓 30B+ LLM 跑在 consumer 等級硬體上的關鍵技術。直覺說法是「用較少 bits 表示權重」、但這背後有完整的數值精度數學依據：浮點數怎麼編碼、不同 format 的取捨在哪、量化在哪一步損失資訊、Q4 vs Q5 的品質差距是怎麼算出來的。

本章拆開「浮點數的位元結構」、「不同 format 的取捨」、「量化的數學流程」三件事、讓 Q4_K_M、bf16、fp16、int8 等術語從口號變成可推導的工程選擇。

## 本章目標

讀完本章後、你應該能：

1. 解釋 fp32、bf16、fp16 三者的位元結構差異。
2. 看到「Q4 量化」時、知道是把每個權重壓成 4 bits。
3. 推算 31B 模型用不同精度的記憶體佔用。
4. 解釋為什麼 Q3 衰減品質遠大於 Q4 → Q5。

## 浮點數的位元結構

浮點數（floating point）的核心定義是「用「符號 + 指數 + 尾數」三段位元表示實數」。IEEE 754 標準：

```text
value = (-1)^sign × 1.mantissa × 2^(exponent - bias)
```

各 format 的位元分配：

| Format | 總 bits | Sign | Exponent | Mantissa | 表示範圍                 | 精度          |
| ------ | ------- | ---- | -------- | -------- | ------------------------ | ------------- |
| fp32   | 32      | 1    | 8        | 23       | ±10^38                   | 約 7 位十進位 |
| fp16   | 16      | 1    | 5        | 10       | ±65,504                  | 約 3 位十進位 |
| bf16   | 16      | 1    | 8        | 7        | ±10^38（跟 fp32 同範圍） | 約 2 位十進位 |
| fp8    | 8       | 1    | 4-5      | 2-3      | 視變體                   | 約 1 位十進位 |

關鍵觀察：

1. **fp32 vs bf16 vs fp16**：
   - fp32 是基準、訓練最穩、推論最浪費。
   - bf16 跟 fp32 同 exponent 範圍、不會 overflow、但 mantissa 較少、精度低。
   - fp16 範圍小（±65,504）、訓練容易 overflow、需要 loss scaling。

2. **訓練主流選 bf16**：保留 fp32 的範圍、用 fp16 的位元數、避免 overflow / underflow 問題。Apple Silicon、NVIDIA Ampere+ 都原生支援 bf16。

3. **推論常見更低精度**：fp16、int8、int4 在推論時夠用；訓練多數情境精度不足、需要更高 format 或特殊技巧（loss scaling、mixed precision）。

## bf16 為什麼比 fp16 更適合 LLM 訓練

bf16（brain float 16、Google Brain 提出）跟 fp16 都是 16 bits、但結構不同：

- **fp16**：sign 1 + exponent 5 + mantissa 10
- **bf16**：sign 1 + exponent 8 + mantissa 7

fp16 的 exponent 只有 5 bits、能表達的最大值 65,504、最小正值約 6e-5。LLM 訓練中的 gradient 經常超出這個範圍：

- Gradient 太大 → overflow → NaN → 訓練崩潰。
- Gradient 太小 → underflow → 變 0 → 那個權重學不到東西。

要用 fp16 訓練、得加 loss scaling（把 loss 乘一個大數、讓 gradient 落在 fp16 範圍內、最後再除回去）、流程複雜。

bf16 的 exponent 8 bits、跟 fp32 同範圍、在 LLM gradient 的典型範圍內不會 overflow / underflow（fp32 的全範圍 ±3.4e38 仍可能 overflow、但 LLM 場景遠超這個值的機率極低）。代價是 mantissa 只剩 7 bits、精度更低。對 LLM 訓練來說、範圍比精度重要（gradient 的方向比精確值關鍵）。

硬體前提：bf16 訓練主流是 NVIDIA Ampere（A100、2020+）跟 Apple Silicon、舊 GPU（Pascal、Volta）只有 fp16 硬體加速、用 bf16 會走 software fallback、性能差。

所以 2026 年主流選擇：

- **訓練**：bf16（forward + backward）+ fp32（master copy of weights）
- **推論**：bf16 或更低（fp16、int8、int4）

## 量化：把權重從 bf16 壓到 Q4 / Q8

量化（quantization）的核心定義是「把連續的浮點數值 map 到離散的整數值」。最簡單的對稱量化：

```text
給定一組權重 W ∈ ℝⁿ：

1. 算 scale = max(|W|) / (2^(bits-1) - 1)
   例如 4-bit、scale = max(|W|) / 7
2. 把每個 wᵢ 量化成整數 qᵢ = round(wᵢ / scale)
3. 還原時：w̃ᵢ = qᵢ × scale
```

幾何意義：把連續實數軸切成 2^bits 個格子、每個權重 snap 到最近的格子。bits 越少、格子越粗、量化誤差越大。

各量化等級的格子數：

| Bits | 格子數 | 適合場景                   |
| ---- | ------ | -------------------------- |
| 16   | 65,536 | 訓練 + 推論                |
| 8    | 256    | 推論、品質敏感任務         |
| 4    | 16     | 推論主流、寫 code 甜蜜點   |
| 3    | 8      | 較大模型強塞較小硬體時備用 |
| 2    | 4      | 實驗、實用品質崩           |

## K-quants：更聰明的量化

[GGUF](/llm/knowledge-cards/gguf/) 的 K-quants 比樸素量化更聰明：

1. **Block-wise quantization**：權重切成小 block（例如 32 個權重一組）、每個 block 各自的 scale。讓 scale 適應 local 數值範圍、減少全域量化誤差。
2. **Mixed precision**：不同 layer 用不同 bits。LLM 中某些 layer（如 attention output、embedding）對品質影響大、用較高 bits（Q5）；其他用較低 bits（Q4）。整體平均落在「Q4_K_M」這個標籤。

「Q4_K_M」拆解：

- `Q4`：平均約 4 bits / 權重
- `K`：K-quants（block-wise、混合精度）
- `M`：medium variant、不同 layer 用不同 bits 的具體配方（也有 `S` small、`L` large 等變體）

實際每個權重的 bits 不剛好是 4、會稍高一點（Q4_K_M 取中值約 4.5 bits / 權重、實際隨模型架構與 attention layer 比例落在 4.4 ~ 4.8 之間、Hugging Face 上具體檔案大小可能跟下方表格估算差 5 ~ 10%）。

## 模型大小推算

知道每個權重幾 bits 後、可以推算模型佔用：

```text
模型大小（GB）= 參數數 × bits / 8 / 1024^3
```

例子：

| 模型 | 量化   | 計算                    | 大小      |
| ---- | ------ | ----------------------- | --------- |
| 7B   | bf16   | 7e9 × 16 / 8 / 1024^3   | 約 13 GB  |
| 7B   | Q8     | 7e9 × 8 / 8 / 1024^3    | 約 6.5 GB |
| 7B   | Q4_K_M | 7e9 × 4.5 / 8 / 1024^3  | 約 3.7 GB |
| 31B  | Q4_K_M | 31e9 × 4.5 / 8 / 1024^3 | 約 16 GB  |
| 70B  | Q4_K_M | 70e9 × 4.5 / 8 / 1024^3 | 約 37 GB  |
| 70B  | Q3     | 70e9 × 3 / 8 / 1024^3   | 約 25 GB  |

加上 metadata、tokenizer、[KV cache](/llm/knowledge-cards/kv-cache/) 等 overhead、實際記憶體佔用會比表上多 10 ~ 30%。

## 量化在哪一步損失資訊

量化的品質損失來自三個位置：

1. **Rounding error**：把連續實數 snap 到離散格子、每個權重產生一個小誤差。Block size 越大、scale 越粗、誤差越大。
2. **Clipping**：若 max(|W|) 估錯（例如忽略 outlier）、超出範圍的權重被 clip 到範圍內、損失大值資訊。K-quants 用 block-wise 解決 outlier 影響。
3. **Layer-wise 累積**：每個 layer 的量化誤差會經過後續 layer 放大或累積；某些 layer（如 attention 的 output projection）對誤差特別敏感。Mixed precision 對這些 layer 保留較高 bits。

實務上：

- Q4_K_M 在 31B 模型上品質衰減約 1 ~ 2%（用 perplexity 衡量）、實用上幾乎察覺不到。
- Q3 在 31B 模型上衰減約 5 ~ 10%、coding 任務開始失誤。
- Q2 衰減 20%+、實用情境受限、多半用於極端硬體預算的實驗。

## 為什麼 31B Q4 常勝 70B Q3

模型大小與量化等級的乘積決定實際品質。31B Q4 跟 70B Q3 的記憶體佔用接近（16GB vs 25GB）、但實際表現常常 31B Q4 勝：

- 70B Q3 的量化誤差累積在每一層、深網路放大誤差。
- 31B Q4 誤差較小、雖然參數量較少但能力穩定。

這就是 [模型選型](/llm/01-local-llm-services/model-selection-priority/) 的核心啟示：「夠大」跟「夠好」是兩件事、優先選穩定量化等級、把激進量化留給有預算驗證的場景。

## 推論時的數值精度

寫 code 場景的推論大致流程：

1. **權重儲存**：Q4_K_M 格式（4.5 bits / 權重）。
2. **推論時 dequantize**：每次用到權重時、暫時 unpack 回 fp16 / bf16 跟 input 做矩陣乘法。
3. **Activation 維持 fp16 / bf16**：樸素 Q4_K_M 的預設行為是不量化 activation、避免進一步損失精度。進階場景（[KV cache 量化](/llm/05-discrete-gpu/vram-ram-budget/) K=Q8 / V=Q4、AWQ、GPTQ 等 activation-aware 量化）會例外處理、需依框架文件配置。

所以「Q4 模型」內部運算精度其實是 fp16 / bf16、只有「儲存」是 4 bits。這是為什麼量化主要省記憶體與頻寬、不省算力（算力差距小）。

## 小結

浮點數的位元結構（sign + exponent + mantissa）決定不同 format 的取捨。bf16 在訓練主流、保留 fp32 範圍；推論主流是 Q4_K_M、平均 4.5 bits / 權重、用 K-quants 跟 block-wise 維持品質。理解這條鏈、模型大小推算、量化等級選擇、品質衰減判讀都變得可計算。

想看完整數值分析（IEEE 754 細節、條件數、誤差傳播等）、見 [2.4 公開課推薦](/llm/02-math-foundations/going-deeper-math/) 的相關資源。

下一章：[2.4 想學更深：推薦公開課程](/llm/02-math-foundations/going-deeper-math/)。
