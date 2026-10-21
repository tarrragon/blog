---
title: "Probability calibration（機率校準）"
date: 2026-10-21
slug: "probability-calibration"
description: "讀到模型的信心值、選項機率或多次取樣的一致比例，要判斷這個數字能不能當成答對的機率時"
weight: 1
tags: ["llm", "knowledge-cards", "evaluation", "sampling"]
---

Probability calibration（機率校準）描述**模型給出的機率（經 [softmax](/llm/knowledge-cards/softmax/) 轉成的分布，或多次取樣的比例）與它實際答對的頻率之間的對應程度**。一個校準良好的模型，在所有它給出 80% 信心的題目裡，大約有 80% 答對；校準不良的模型，可能在 80% 信心的題目裡只答對一半。信心值要拿來當決策依據，前提是這個對應關係已經在同一類題目上量過。

## 概念位置

| 概念                                                                   | 量測對象                                                                                                |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| 準確率（accuracy）                                                     | 整體答對的比例，不看信心                                                                                |
| 機率校準（probability calibration）                                    | 信心的高低與答對頻率是否相符                                                                            |
| 取樣一致性（consistency）                                              | 同一題在 [temperature](/llm/knowledge-cards/sampling-constraint/) 大於 0 時多次取樣，是否給出同一個答案 |
| [LLM-as-Judge](/llm/04-applications/llm-as-judge/) 的 calibration 步驟 | judge 的評分與人的評分是否一致，屬於評分對齊，跟本卡的機率校準是不同的量測                              |

量測方式是把題目依模型的信心分組（例如 0–10%、10–20%⋯⋯），每組算實際答對的比例，畫成信心對準確率的圖；完全校準時各點落在對角線上。偏離對角線的程度可以濃縮成一個數字，常見的是 expected calibration error（ECE）：各組「信心與準確率的差距」依題數加權平均。Chuan Guo 等人（2017，*On Calibration of Modern Neural Networks*）量到現代神經網路普遍校準不良，並指出 temperature scaling（Platt scaling 的單參數變體）修正校準的效果出奇地好：在驗證集上學一個參數、把 softmax 前的數值整體縮放，事後修正信心而不改變模型選出的答案。

## 設計責任

讀到「模型很有把握」「十次取樣有九次選 A」這類敘述時，判讀的重點是：

1. **一致不等於正確**：多次取樣的一致比例量的是模型對這一題的傾向有多集中，傾向本身可能建立在錯誤的前提上。它也不是模型和人選了同一項的比例（agreement rate），那是另一個量。錯誤前提寫在輸入裡的題目上，模型是否會以很高的一致性選錯、信心是否還能預測對錯，[4.23 System 1 決策模型](/llm/04-applications/system-one-decision-model/#單-token-分布的量測對象)整理的既有量測都沒有直接涵蓋，那是一個待驗證的假設。在量過之前，一致比例不能當成答對的機率讀。
2. **校準依題型與格式而變**：同一個模型在一類題目上校準良好，不代表在另一類題目上也是。Saurav Kadavath 等人（2022，*Language Models (Mostly) Know What They Know*）量到較大的模型在格式合適的選擇題上校準良好，而把其中一個選項換成「以上皆非」就明顯降低準確率與校準。拿信心當門檻之前，要用同一類題目、同一種選項格式量過。
3. **訓練後處理會改變校準**：GPT-4 技術報告（2023）讀取模型在 [MMLU](/llm/knowledge-cards/llm-benchmarks/) 子集上給 A、B、C、D 四個選項的對數機率，預訓練後的 [base model](/llm/knowledge-cards/base-model/) 信心與答對比例相當吻合，經過 [RLHF](/llm/knowledge-cards/rlhf/) 這類後訓練之後校準明顯變差。Kadavath 等人量到 RLHF 後的模型乍看校準不良，用 temperature scaling 調整之後在多項評估上相當接近校準，所以後訓練造成的偏差有一部分可以事後修正。換模型或換版本就要重新量。
4. **失敗模式**：把未經校準的信心直接當成機率使用，例如「信心高於 0.9 就自動採用」。在校準不良的題型上，這條規則放行的錯誤答案，會跟正確答案一樣有把握。
