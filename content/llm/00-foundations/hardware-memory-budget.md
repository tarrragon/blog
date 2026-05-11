---
title: "0.5 Apple Silicon 記憶體預算"
date: 2026-05-11
description: "記憶體決定能跑什麼，Q4 量化下的可運作模型對照與系統保留"
tags: ["llm", "foundations", "hardware", "apple-silicon"]
weight: 5
---

Apple Silicon Mac 跑本地 LLM 的核心限制是**記憶體大小**，不是 CPU 也不是 GPU。記憶體決定能載入多大的模型；模型載得進、推論才有得跑。本章把網路上常見的「24GB 能跑 70B」這類含糊說法，換成可操作的記憶體預算判讀。

讀完本章後，你可以對自己這台 Mac 直接回答：能跑哪些模型、要用什麼量化、要留多少給系統、風扇會不會狂轉、什麼時候該升級。

## 本章目標

讀完本章後，你應該能：

1. 看 Mac 規格立刻知道能跑哪一級的模型。
2. 理解量化等級跟模型大小的乘積為何決定可行性。
3. 為「給系統留多少記憶體」這件事設一個合理上界。
4. 判斷自己這台 Mac 適不適合跑本地 LLM。

## 記憶體預算的基本算式

跑本地 LLM 的記憶體預算大致拆成三塊：

```text
總記憶體 = 系統與其他 app（保留）+ 模型權重 + KV cache + 推論中間結果
```

各塊的估算原則：

1. **系統與其他 app**：至少留 8GB 給 macOS、VS Code、瀏覽器與其他工作流程。重度多工建議留 10 ~ 12GB。
2. **模型權重**：用「參數規模 × 每權重 bits / 8」算出 bytes。例如 31B 模型 Q4 量化 = 31 × 4 / 8 = 15.5 GB，加上 metadata 與 overhead 約 16 ~ 18GB。
3. **KV cache**：跟 context 長度成正比。短 context（< 2K tokens）約 0.5 ~ 1GB，長 context（10K+ tokens）可能超過 5GB。
4. **推論中間結果**：通常 1 ~ 2GB。

實際留給模型的可用記憶體 = 總記憶體 − 系統保留（8GB）− KV cache（2 ~ 5GB）− 推論 overhead（2GB）。

## Mac 記憶體與可運作模型對照

下表是 2026 年 5 月，Apple Silicon Mac 在 Q4 量化下的可運作模型對照。所有體感標籤都假設「主要用途是寫 code」，純文字對話的甜蜜點會往較小模型偏。

| Mac 記憶體 | 留給模型  | 能跑的最大模型                                   | 體感   | 備註                             |
| ---------- | --------- | ------------------------------------------------ | ------ | -------------------------------- |
| 8GB        | 0GB       | 跑不動實用的 LLM                                 | 不建議 | 連 4B 模型都很勉強               |
| 16GB       | 6 ~ 8GB   | Gemma 4 E4B、Qwen3 7B、Llama 3.2 8B              | 勉強   | 同時開 VS Code 就會吃緊，常 swap |
| 24GB       | 12 ~ 14GB | Gemma 4 12B、Qwen3-Coder 14B、Llama 3.3 13B      | 堪用   | 多數工程師的起點                 |
| 32GB       | 18 ~ 22GB | **Gemma 4 31B (MTP) 甜蜜點**、Qwen3-Coder 30B Q4 | 順暢   | 寫 code 場景最佳價格效能比       |
| 48GB       | 32 ~ 36GB | Qwen3-Coder 32B Q5、Llama 3.3 70B Q3             | 順暢   | 開始接近 GPT-4 mini 等級         |
| 64GB       | 48 ~ 52GB | Qwen3-Coder 32B bf16、Llama 3.3 70B Q4           | 順暢   | 大模型用較高量化，品質更好       |
| 96GB+      | 80GB+     | Llama 3.3 70B Q8、實驗 100B+ 模型                | 順暢   | 過度配置，除非有特殊需求         |

讀這張表要注意四件事：

1. **體感是 coding 場景**。純對話、寫文章、解釋程式的記憶體門檻較低。
2. **量化等級可以調整**。32GB 跑 31B Q4 順暢、跑 31B Q5 也行（吃 21GB 左右）；跑 70B Q3 會崩潰，因為 70B Q3 約 26GB，加上 KV cache 跟系統，超過 32GB。
3. **fanless 機種要打折**。MacBook Air 系列因為散熱被動，跑大型模型 5 分鐘後會降頻，實際生字速度比有風扇的同代機器低 30 ~ 50%。
4. **記憶體不是 SSD**。Apple Silicon 的「統一記憶體」是 RAM，不是 SSD swap。雖然 macOS 會 swap，但 swap 後生字速度會慢一個量級以上，等於跑不動。

## 為什麼 32GB 是寫 code 場景的甜蜜點

32GB Mac 跑 Gemma 4 31B（Q4 + MTP）是 2026 年 5 月寫 code 場景最佳的價格效能比，原因是三個趨勢的交會：

1. **31B 模型剛好能力夠用**。Gemma 4 31B / Qwen3-Coder 30B 在 SWE-bench 等 coding benchmark 上的表現大幅超越 14B 模型，接近 GPT-4 mini 等級。14B 等級的模型在跨檔案任務上仍經常失誤。
2. **Q4 量化在 31B 上的品質衰減仍可接受**。Q4 在 7B 模型上品質衰減明顯，但 31B 模型有「參數冗餘」，Q4 反而是甜蜜點。
3. **32GB 剛好夠 18GB 模型 + 8GB 系統 + 6GB 其他**。再小（24GB）跑 31B Q4 會吃緊；再大（48GB）邊際效益降低，除非要跑 70B。

對應的 Mac 機型（2026 年 5 月可購）：

- MacBook Pro 14 / 16 with M4 Pro / Max，32GB 配置。
- Mac mini M4 Pro，32GB 配置（最便宜的進入點）。
- Mac Studio M4 Max，32GB 起跳。

如果你正準備買新 Mac 主要為了跑本地 LLM 寫 code，32GB 是最值的起點。16GB 會綁手綁腳、48GB 以上對寫 code 來說是奢侈。

## 16GB Mac 還有救嗎

16GB Mac 是現實上的最小可用配置。能跑的最大實用模型是 Gemma 4 E4B（Google 的 8B 級實驗版本）或 Qwen3 7B。體感上：

1. 不能同時開 VS Code + Chrome + Slack + 跑模型。記憶體會被擠到 swap，整台 Mac 變慢。
2. 模型品質明顯弱於 31B 等級。簡單 function 補完還行，跨檔案重構幾乎不可用。
3. 適合「偶爾用本地、主要還是雲端」的混用策略。

如果你的 Mac 是 16GB，先用 Gemma 4 E4B 試試看，評估自己工作流是否真的需要本地 LLM。多數情況下答案是「雲端 API 月費比換 Mac 便宜」。

## KV cache 與長 context 的記憶體陷阱

模型權重佔的記憶體是固定的，但 KV cache 隨 context 長度線性增加。長 context 場景的記憶體陷阱常被忽略。

接近真實的估算（Gemma 4 31B、Q4 量化）：

| Context 長度 | KV cache 估算 | 總記憶體需求                          |
| ------------ | ------------- | ------------------------------------- |
| 1K tokens    | ~0.5 GB       | 模型 18GB + 0.5GB                     |
| 4K tokens    | ~2 GB         | 模型 18GB + 2GB                       |
| 16K tokens   | ~8 GB         | 模型 18GB + 8GB                       |
| 32K tokens   | ~16 GB        | 模型 18GB + 16GB → 32GB Mac 開始 swap |

陷阱是把 context 長度設到模型支援的上限（如 32K、128K）卻沒算 KV cache 成本。32GB Mac 跑 31B 模型，實際可用 context 大約只有 8 ~ 16K tokens；超過就會 swap，速度崩潰。

解法：

1. 短 prompt 場景（compact code completion）：完全沒問題，多數設定都在 2K 以下。
2. 中等 context（4 ~ 16K）：32GB Mac 仍可運作，但要留意 KV cache 吃多少。
3. 長 context（16K+）：考慮 oMLX 的 paged SSD KV cache，把 cache 推到 SSD。詳見 [0.4 MLX / MTP / oMLX](/llm/00-foundations/mlx-mtp-omlx/)。

## 風扇、發熱與降頻

Apple Silicon Mac 跑本地 LLM 會持續滿載 CPU / GPU。實際體感：

| 機型                   | 散熱 | 持續推論體感                           |
| ---------------------- | ---- | -------------------------------------- |
| MacBook Air（fanless） | 被動 | 5 ~ 10 分鐘後降頻，生字速度掉 30 ~ 50% |
| MacBook Pro 14 / 16    | 主動 | 風扇明顯轉，但能維持效能               |
| Mac mini               | 主動 | 風扇轉但較安靜                         |
| Mac Studio             | 主動 | 體感安靜，效能維持最好                 |

對「全天候用本地 LLM」的工作流，桌機型（Mac mini、Studio）比筆電好。筆電上跑長時間推論還要考慮電池與發熱對手部舒適度的影響。

## 給讀者的決策表

看完上面的對照後，可以照下表做決策：

| 情境                               | 建議                                                     |
| ---------------------------------- | -------------------------------------------------------- |
| 已有 16GB Mac，想試本地            | 用 Gemma 4 E4B 試一週，主力仍用雲端，評估是否值得升級    |
| 已有 24GB Mac，想試本地            | Gemma 4 12B 或 Qwen3-Coder 14B，是合理起點               |
| 已有 32GB Mac                      | Gemma 4 31B MTP 是預設選擇，能力 / 速度甜蜜點            |
| 已有 48GB+ Mac                     | Qwen3-Coder 32B 或 Llama 3.3 70B Q4，能力接近 GPT-4 mini |
| 正準備買新 Mac，預算敏感           | Mac mini M4 Pro 32GB 是最划算的進入點                    |
| 正準備買新 Mac，要兼顧攜帶         | MacBook Pro 14 with M4 Pro 32GB                          |
| 正準備買新 Mac，要追求最大本地能力 | Mac Studio M4 Max 64GB+                                  |

陷阱是把 96GB+ 配置當成「未來證明」。模型架構演進可能讓現在的記憶體預算明年就不重要（例如 1-bit 量化、新的稀疏架構）。除非有具體需求，不要為了「以後可能跑得到 100B+ 模型」買超大記憶體。

## 小結

Apple Silicon Mac 跑本地 LLM 的關鍵是記憶體預算，不是 CPU / GPU。32GB 是寫 code 場景的甜蜜點，能跑 Gemma 4 31B MTP；16GB 是現實下界，多數情況該升級或回到雲端；48GB+ 開始接近 GPT-4 mini 能力等級。KV cache、系統保留、fanless 降頻都是常被忽略的成本，要納入預算。

下一章：[0.6 網路上的常見誤解](/llm/00-foundations/common-misconceptions/)，把寫作本指南時遇到的網路文章錯誤說法一次點名清理。
