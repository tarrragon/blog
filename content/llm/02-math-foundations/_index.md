---
title: "模組二：LLM 的數學基礎"
date: 2026-05-11
description: "整理 LLM 推論背後需要理解的線性代數、機率與資訊論、最佳化、數值精度等數學概念"
tags: ["llm", "math-foundations"]
weight: 2
---

本模組整理 LLM 推論背後的數學概念。寫 code 場景的使用者通常無需親自實作這些公式、但理解它們的存在與意義、能讓「為什麼模型佔這麼多記憶體」「為什麼量化會衰減品質」「為什麼長 prompt 的 prefill 成本特別高」等現象從黑箱變成可推導的工程現實。

本模組假設讀者熟悉中學以上的數學、但無需具備機器學習背景。每個概念給出定義、在 LLM 中扮演的角色、以及實務上會怎麼遇到它。深度推導與練習題交給[公開課程](/llm/02-math-foundations/going-deeper-math/)；本模組的責任是把名詞跟用途連起來。

## 章節列表

| 章節                                                         | 主題                       | 關鍵收穫                                                   |
| ------------------------------------------------------------ | -------------------------- | ---------------------------------------------------------- |
| [2.0](/llm/02-math-foundations/linear-algebra-for-llm/)      | 線性代數：向量、矩陣、空間 | LLM 內部所有運算都是矩陣乘法、為什麼維度匹配是常見錯誤源頭 |
| [2.1](/llm/02-math-foundations/probability-and-information/) | 機率與資訊論               | softmax、cross-entropy、KL divergence、perplexity 的角色   |
| [2.2](/llm/02-math-foundations/calculus-and-optimization/)   | 微積分與最佳化             | gradient、chain rule、SGD / Adam 在訓練流程中的位置        |
| [2.3](/llm/02-math-foundations/numerical-precision/)         | 數值精度與量化的數學依據   | floating point、bf16 vs fp32、量化能在哪裡省 bits          |
| [2.4](/llm/02-math-foundations/going-deeper-math/)           | 想學更深：推薦公開課程     | MIT、Stanford、Harvard、3Blue1Brown 等系統教材路線         |

## 跟模組零的分工

模組零（[基礎知識與心智模型](/llm/00-foundations/)）的責任是「裝模型、用模型」需要的操作層概念；本模組的責任是這些操作層概念背後的數學基礎。兩者各自獨立、可分開讀：

| 模組零問的問題                | 本模組問的問題                       |
| ----------------------------- | ------------------------------------ |
| 32GB Mac 能跑多大模型         | 為什麼模型大小 ≈ 參數數 × bits / 8   |
| 量化怎麼選                    | 量化在數學上做了什麼、哪裡會衰減品質 |
| 為什麼長 prompt 的 TTFT 高    | prefill 階段在做什麼運算             |
| 為什麼 MTP 對寫 code 加速明顯 | 為什麼 attention 的驗證可以並行      |

讀過本模組後、回頭看模組零會發現「為什麼這個現象成立」變得清楚。

## 跟模組三的分工

模組二（本模組）給數學工具、模組三（[LLM 的理論基礎](/llm/03-theoretical-foundations/)）用這些工具拼出完整 LLM 的運作機制。兩個模組可以並讀：遇到陌生數學概念時跳回本模組補完。

| 本模組（工具）   | 模組三（用法）                            |
| ---------------- | ----------------------------------------- |
| 矩陣乘法         | attention 的 Q × K^T、output 的 W × x     |
| softmax          | attention 權重正規化、輸出 token 機率分佈 |
| cross-entropy    | 訓練時的 loss function、衡量模型預測品質  |
| gradient descent | 訓練時更新權重的演算法                    |
| floating point   | bf16 / fp16 / fp32 在訓練與推論時的取捨   |

## 適合的讀者

| 你的背景                                | 適合程度                                                                               |
| --------------------------------------- | -------------------------------------------------------------------------------------- |
| 工程師、會用過雲端 LLM、想懂底層        | 直接適合、可從 2.0 依序讀                                                              |
| 學過大學線性代數 + 機率、但忘得差不多了 | 直接適合、本模組是有效的複習索引                                                       |
| 完全沒碰過矩陣 / 機率                   | 可以讀、但會略吃力；建議搭配 [2.4 公開課](/llm/02-math-foundations/going-deeper-math/) |
| 想跳過數學、直接用 LLM                  | 跳過本模組無妨、模組零跟模組一已足夠日常使用                                           |

## 用語約定

本模組固定下列翻譯：

| 英文                        | 中文                    |
| --------------------------- | ----------------------- |
| Vector                      | 向量                    |
| Matrix                      | 矩陣                    |
| Tensor                      | 張量                    |
| Dot product / Inner product | 內積                    |
| Norm                        | 範數（norm）            |
| Probability distribution    | 機率分佈                |
| Cross-entropy               | 交叉熵（cross-entropy） |
| KL divergence               | KL 散度                 |
| Entropy                     | 熵                      |
| Gradient                    | 梯度（gradient）        |
| Partial derivative          | 偏導數                  |
| Chain rule                  | 連鎖律                  |
| Floating point              | 浮點數                  |

英文原文在第一次出現時保留括號錨點、後續用中文。

## 不在本模組內的主題

1. **完整數學證明**：本模組只給定義跟用途、不展開推導。完整證明交給 [2.4](/llm/02-math-foundations/going-deeper-math/) 推薦的公開課。
2. **數值分析的進階主題**：條件數、誤差累積、迭代法收斂等屬於數值分析專門課程的範圍。
3. **機率論進階**：測度論、隨機過程等屬於數學系的範圍、跟 LLM 推論的關聯較淡。
4. **最佳化理論**：凸最佳化、二階方法等深度主題交給 Stanford CS229 / Boyd 的最佳化課程。
