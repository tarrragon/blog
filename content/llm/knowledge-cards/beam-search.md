---
title: "Beam Search"
date: 2026-05-12
description: "同時保留 K 條候選 sequence 的 decoding 策略、機器翻譯主流、chat / coding 場景慎用"
weight: 1
tags: ["llm", "knowledge-cards", "sampling", "decoding"]
---

Beam search 的核心概念是「**每步同時保留 K 條最有機率的候選 sequence（beam width = K）、最終挑一條總機率最高的當輸出**」。相比 greedy decoding 只保一條、beam search 能探索更多可能、避免「貪心一時、累積失誤」；但對話 / coding 場景常出現副作用、是 [top-p sampling](/llm/knowledge-cards/top-p-sampling/) 取代它的原因。

## 跟其他概念的關係

Beam search 跟其他 decoding 策略（如 [top-p sampling](/llm/knowledge-cards/top-p-sampling/)）的對比：

| 策略                  | 機制                               | 適合場景                                      | LLM 常見性          |
| --------------------- | ---------------------------------- | --------------------------------------------- | ------------------- |
| Greedy                | 每步選機率最大的 token             | 確定性任務、debugging                         | 高                  |
| **Beam search (K)**   | 維護 K 條候選、最後挑總機率最高的  | 機器翻譯、summarization、有「正確答案」的任務 | 中（傳統 NLP 主流） |
| Top-k / top-p / min-p | 從機率分佈隨機取樣（限制候選範圍） | 對話、寫作、coding、創意輸出                  | 高（LLM 主流）      |

Beam search 的算法直覺：

```text
beam_width = 3
Step 1：從機率分佈挑前 3 個 token、得到 3 條 partial sequence
Step 2：每條 partial 各自展開所有可能下個 token、組合機率排序、保留前 3
Step 3：重複 Step 2、直到所有 beam 都遇到 EOS 或達到 max_length
Final：選總 log-probability 最高的 beam 當輸出
```

Beam search 在 LLM chat / coding 場景的副作用：

1. **輸出偏 boilerplate**：K 個 beam 容易收斂到同樣的高頻開頭（「Sure!」「That's a great question」）、各 beam 平均化掉原本該有的多樣性。
2. **缺乏隨機性**：給同 prompt 永遠生同輸出、缺乏寫作 / 創意任務需要的變化。
3. **計算貴**：K 倍記憶體 + K 倍 forward pass。

## 判斷條件與後果

Inference framework 的 `num_beams: 1` 預設值代表 greedy 或 sampling，設成 5 這類大於 1 的值才會開 beam search。用哪一種 decoding 看任務要的是變化、重現還是挑選：日常對話與寫 code 要輸出有變化，beam search 的 K 條候選會收斂到同樣的高頻開頭，同一個 prompt 永遠得到同一個輸出，所以這類任務用 [top-p sampling](/llm/knowledge-cards/top-p-sampling/)；確定性測試要同一個輸入得到同一個輸出，greedy 每步只選最大機率的 token 就做得到，不必付 K 倍的計算；要從多個候選挑最好的一個時，best-of-N 讓每個候選獨立 sample、再挑 reward 最高的，候選之間保有差異，beam search 的候選則被同樣的高機率前綴拉在一起。Translation 與 structured output 這類有正確答案的任務不追求多樣性，beam search 在這些場景仍有人用。
