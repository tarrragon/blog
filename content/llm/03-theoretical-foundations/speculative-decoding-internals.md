---
title: "3.9 Speculative decoding 內部：drafter / 驗證 / 加速上限"
date: 2026-05-12
description: "speculative decoding 的演算法細節、drafter 跟 target 怎麼配對、acceptance rate 怎麼決定實際加速、MTP 跟 EAGLE 等變體"
tags: ["llm", "theory", "speculative-decoding", "inference-optimization"]
weight: 9
---

[Speculative decoding](/llm/knowledge-cards/speculative-decoding/) 在多個前面章節被引用作為「LLM 推論加速的主要技術之一」。本章把這個機制完整展開：為什麼能加速、acceptance 怎麼運作、實際加速倍率怎麼算、[drafter model](/llm/knowledge-cards/drafter-model/) 怎麼選、跟 [MTP](/llm/knowledge-cards/mtp/) / EAGLE 等變體的關係。

讀完本章後、看到「speculative decoding 加速 2.5×」這類聲稱時、能判斷可信度、能對自己工作流估算實際收益、能挑對 drafter。

## 本章目標

1. 解釋為什麼 speculative decoding 能在「不降品質」前提下加速。
2. 區分 drafter-based、MTP、EAGLE 三條主流路線。
3. 用 [acceptance rate](/llm/knowledge-cards/acceptance-rate/) 估算實際加速倍率。
4. 判斷一個 drafter / target 配對是否值得用。
5. 看到 `llama-bench` 結果時、判讀「speculative speed」對自己場景的意義。

## 為什麼能加速：[memory bandwidth](/llm/knowledge-cards/memory-bandwidth/) bound 的縫隙

回顧 LLM 推論的瓶頸：[forward pass](/llm/knowledge-cards/forward-pass/) 每生一個 token 要把整份模型權重從記憶體讀到處理器一次、所以 memory bandwidth 是上限。每次讀的時候、處理器有大量算力是閒置的（modern GPU / Apple Silicon 算力遠超頻寬）。

Speculative decoding 攻擊這個閒置：

```text
單純 autoregressive 推論：
  每 token：讀整份權重 → 算 forward → 出 1 個 token
  讀權重 N 次、生 N 個 token
  瓶頸 = memory bandwidth × N

Speculative decoding（K=4）：
  Drafter 一次生 4 個候選 token（drafter 小、讀它的權重快）
  Target 一次驗證 4 個位置（並行算 forward、權重只讀 1 次）
  若全部接受、生 4-5 個 token（含 bonus）
  讀 target 權重次數從 4 降到 1、平均 token 成本顯著降
```

關鍵理解：

1. **Target model 的 forward pass 對 K 個位置是並行的**：一次讀權重、做矩陣乘法時把 K 個位置同時算（batch dimension 變大）
2. **算力是免費資源**：原本閒置的算力被用來「同時算多個位置」、不增加 memory bandwidth 消耗
3. **正確性保證**：sampling 階段的接受 / 拒絕邏輯確保最終輸出分佈跟「純 target 自回歸生成」一致 — speculative decoding 不降品質、只省時間

## 演算法核心：sampling 階段的接受邏輯

詳細的接受機制（簡化版）：

```text
給定：drafter D、target T、context prefix x、speculative length K

Step 1：D 從 x 生 K 個候選 token：d_1, d_2, ..., d_K
        對每個位置算 D(d_i | x, d_1..i-1) 機率

Step 2：T 對 (x, d_1, d_2, ..., d_K) 做一次 forward pass、得到每個位置的 T 分佈
        T_1 = T(· | x)
        T_2 = T(· | x, d_1)
        ...
        T_K = T(· | x, d_1..K-1)
        T_{K+1} = T(· | x, d_1..K)   ← bonus token 位置

Step 3：從前往後處理：
        for i = 1 to K:
          r = uniform random in [0, 1]
          if r < min(1, T_i(d_i) / D(d_i)):
            accept d_i           ← d_i 在 T 下機率 ≥ D 下機率、接受
          else:
            reject、sample 替代 token from (T_i - D)+ normalized
            break

Step 4：若全 K 個接受、再 sample 一個 bonus token from T_{K+1}
```

關鍵性質（數學上可證明）：

1. **最終輸出分佈 ≡ 純 target 自回歸**：不管 drafter 多爛、speculative decoding 的輸出在統計上跟「就用 T 從頭生」完全相同 — 不是「近似」、是「等價」
2. **Drafter 越接近 target、acceptance rate 越高**：但即使 drafter 完全亂猜、輸出仍正確、只是沒加速
3. **每 step 至少生 1 個 token**：最差情況第一個就拒絕、用 T 取代、退化成單純 T 自回歸

## 加速倍率 = K × acceptance rate 的限制

理論加速分析：

```text
Step 平均生 token 數 = E[接受長度] + 1（bonus 若有）
                    ≈ K × acceptance_rate （簡化估算）

每 step 主要成本：
  Drafter K 次小 forward + Target 1 次大 forward
  ≈ K × T_drafter + T_target
  ≈ T_target × (1 + K × C)   where C = T_drafter / T_target

加速倍率 ≈ K × acceptance_rate / (1 + K × C)
```

實際例子（Gemma 4 31B target + Gemma 4 E4B drafter、K=5）：

- T_drafter / T_target ≈ 4B / 31B ≈ 0.13
- K = 5、acceptance rate ≈ 0.7（同 family、estimate）
- 加速倍率 ≈ 5 × 0.7 / (1 + 5 × 0.13) ≈ 3.5 / 1.65 ≈ **2.1×**

對照 LM Studio / llama.cpp 實測常見的「2-3×」加速、推導合理。

什麼破壞加速：

1. **Drafter 太大**：C 接近 1、(1 + K × C) 爆增、淨收益消失
2. **Acceptance rate 太低**：K × acceptance 達不到 1 + K × C、淨收益負
3. **K 設太大**：drafter 後面 token acceptance rate 急降、且每步成本 K × T_drafter 線性增加

## 三條主流變體

### Drafter-based（經典 speculative decoding）

Leviathan et al. 2022 / Chen et al. 2023 提出：

- **方式**：獨立訓練一個小 drafter model、跟 target 同 family / 同 tokenizer
- **代表**：Gemma 4 31B + E4B、Llama 3.1 405B + 8B、Qwen3 30B + 1.5B
- **優點**：相對成熟、各推論伺服器（llama.cpp、vLLM）廣泛支援
- **缺點**：要訓 / 維護兩個 model；drafter 跟 target 必須完全相容

### MTP（Multi-Token Prediction）

DeepSeek-V3 / Gemma 4 等內建：

- **方式**：訓練 target 時、output 端額外加 K 個 head、每個 head 學「預測 N+1, N+2, ..., N+K」
- **代表**：DeepSeek-V3（MTP=4）、Gemma 4 coding 變體
- **優點**：不需獨立 drafter、head 跟 target 完全同分佈、acceptance rate 高（通常 0.7-0.85）
- **缺點**：需要 target model 訓練時就支援、現存模型不能後加

### EAGLE（Extrapolation Algorithm for Greater LLM Efficiency）

Li et al. 2024 / EAGLE-2 / EAGLE-3：

- **方式**：drafter 用 target 內部的 hidden state（不是 token embedding）當輸入、預測下一個位置的 token 機率、逼近 target 的分佈。因為 drafter 看的是 target 已經處理過的 feature、acceptance rate 比純 token-based drafter 高
- **代表**：EAGLE-2、EAGLE-3 應用在 Llama 系列
- **優點**：acceptance rate 通常更高（0.8+）、且 drafter 可以很小
- **缺點**：實作較複雜、需要 access target 的 hidden state、推論伺服器支援度較窄

> **事實查核註**：MTP / EAGLE 的具體 acceptance rate 跟加速倍率依模型、任務、量化、推論伺服器實作而異、引用前以各推論伺服器 release notes 跟自己 `llama-bench` 結果為準。

## 怎麼挑 drafter

實務判讀：

| 條件                                       | 選擇                                                 |
| ------------------------------------------ | ---------------------------------------------------- |
| Target 有內建 MTP（如 Gemma 4 coding-mtp） | 直接用 MTP、不另找 drafter                           |
| Target 沒 MTP、有同 family 小模型          | 用 drafter-based、選小一個量級的同 family 模型       |
| Target 沒 MTP、無同 family 小模型          | 多半不值得 speculative、用一般推論                   |
| 用 Apple Silicon Mac、target ≤ 30B         | MTP 是首選、見 [MTP 卡片](/llm/knowledge-cards/mtp/) |
| 用 PC 獨立 GPU、target 較大                | 看 llama.cpp 支援度、EAGLE-2 / drafter-based 都可    |

挑 drafter 的反例（不該配）：

1. **跨 family**：Llama 3 + Qwen3 — tokenizer 不一致、無法配對
2. **跨 generation**：Llama 2 + Llama 3 — vocab 不同
3. **太大 drafter**：target 8B + drafter 3B — drafter 成本接近 target、淨收益小
4. **量化不對稱**：target Q4 + drafter Q8 — drafter 不必比 target 精度高、浪費記憶體

## 怎麼測自己的加速倍率

`llama-bench` 是 llama.cpp 官方 benchmark 工具：

```bash
# 純 target 推論
llama-bench -m gemma-4-31b-Q4_K_M.gguf -p 512 -n 128

# 加 drafter（speculative decoding）
llama-bench -m gemma-4-31b-Q4_K_M.gguf \
            --draft-model gemma-4-e4b-Q4_K_M.gguf \
            --n-predict 128 --speculative-draft 5
```

看的指標：

- **tg128 (純 target)**：純自回歸生 128 token 的 tokens/s
- **tg128 (with draft)**：speculative decoding 模式的 tokens/s
- **加速倍率**：後者 / 前者

實際工作流的 acceptance rate 跟 benchmark 上可能不同（取決於任務）、benchmark 是上限估算。

## 跟其他加速技巧的關係

| 技巧                                                     | 攻擊的瓶頸           | 跟 speculative decoding 的關係            |
| -------------------------------------------------------- | -------------------- | ----------------------------------------- |
| [Quantization](/llm/knowledge-cards/quantization/)       | 權重大小             | 正交、可疊加（兩個都用）                  |
| [Flash Attention](/llm/knowledge-cards/flash-attention/) | Attention 記憶體佔用 | 正交、可疊加                              |
| [KV cache 量化](/llm/knowledge-cards/kv-cache/)          | KV cache 大小        | 正交、可疊加                              |
| [Batching](/llm/knowledge-cards/batching/)               | 多請求共用權重讀取   | 跟 speculative 邏輯衝突（共用 batch dim） |
| [Prefix cache](/llm/knowledge-cards/prefix-cache/)       | Prompt 重複部分      | 正交、可疊加                              |

關鍵注意：**Speculative decoding + batching 同時開的支援度差** — 推論伺服器多半要選一個。個人 dev 場景 batch size = 1、用 speculative 是合理選擇；高併發 production 場景多半選 batching。

## 何時不適合用 speculative decoding

1. **Batch size > 1 場景**：跟 batching 衝突、加速可能反向
2. **Reasoning model**：reasoning trace 的 token 多樣化、drafter 很難猜對、acceptance rate 低（多數 reasoning model 不用 speculative）
3. **Drafter 不存在或不合**：勉強配差 family 的 drafter 反而拖慢
4. **記憶體吃緊**：drafter 也要載入、可能擠掉 KV cache budget、其他地方變慢

## 何時過時 / 何時不過時

**不會過時的部分**：

- 「Memory bandwidth bound 留下算力閒置」的根本觀察
- 接受 / 拒絕 sampling 邏輯（數學上等價於純 target）
- Acceptance rate × K 是加速倍率主要 driver
- Drafter / target 必須 tokenizer 相容
- 跟 batching 衝突的 trade-off

**會變的部分**：

- 具體變體（drafter-based / MTP / EAGLE → 未來可能新方法）
- 各推論伺服器的支援度（llama.cpp、vLLM、TGI 都在演化）
- 模型廠商是否內建 MTP（目前 Gemma 4、DeepSeek 等先行、未來普及）
- Reasoning model 是否會有 reasoning-aware speculative 變體

## 下一步

下一步：模組三的內容到此完整、進入 [模組四 應用層原理](/llm/04-applications/) 看 LLM 作為系統元件的設計取捨。
