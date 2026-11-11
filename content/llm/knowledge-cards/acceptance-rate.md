---
title: "Acceptance Rate"
date: 2026-05-12
description: "speculative decoding 中 drafter 提出的 token 被 target model 接受的比例、決定實際加速倍率"
weight: 1
tags: ["llm", "knowledge-cards", "speculative-decoding", "inference"]
---

Acceptance rate（接受率）的核心概念是「**在 [speculative decoding](/llm/knowledge-cards/speculative-decoding/) 中、[drafter](/llm/knowledge-cards/drafter-model/) 提出的 token 序列被 target model 驗證後接受的比例**」。Acceptance rate 直接決定 speculative decoding 的實際加速倍率：高 acceptance rate（如 0.8）能拉出接近理論上限的加速；低 acceptance rate（如 0.3）可能反而比純 target model 慢。

## 跟其他概念的關係

[Speculative decoding](/llm/knowledge-cards/speculative-decoding/) 一個 step 的流程：

```text
1. Drafter 一次生 K 個候選 token（如 K=5）
2. Target model 對「prefix + 這 K 個 token」並行驗證
3. 從前往後：
   - drafter token i 跟 target 第 i 個位置 sampling 一致 → 接受
   - 第一個不一致 → 接受到此為止、用 target 的 token 取代第一個不一致
4. 若全 K 個都接受、target 再 sample 一個 bonus token
```

Acceptance rate 影響：

| 場景                              | Acceptance rate | 實際加速            |
| --------------------------------- | --------------- | ------------------- |
| Drafter 跟 target 高度同分佈      | 0.8 ~ 0.95      | 接近 K 倍上限       |
| Drafter / target 一般搭配         | 0.5 ~ 0.7       | 約 1.5 ~ 2× 加速    |
| Drafter 訓練分佈差很多            | 0.2 ~ 0.4       | 接近 1×（甚至更慢） |
| Drafter / target tokenizer 不一致 | 不能用          | 概念不成立          |

## 影響 acceptance rate 的因素

1. **Drafter / target 同 family**：同訓練分佈、acceptance rate 高（如 Gemma 4 31B + Gemma 4 E4B）
2. **任務難度**：簡單任務（boilerplate、常見 pattern）drafter 容易猜對；困難任務（reasoning、罕見領域）acceptance rate 降
3. **Sampling temperature**：高 temperature 兩邊 sample 分佈都拉平、隨機性增加、acceptance rate 降；T=0（greedy）acceptance rate 最高
4. **K 設太大**：drafter 越往後預測、累積誤差越大、後半段 token acceptance rate 急降；K 通常設 3-5 為甜蜜點

## 判斷條件與後果

speculative decoding 的設定與 model card 上寫的「draft acceptance」「acceptance length」指的都是這個指標。drafter 跟 target 同 family 時（如 Gemma 4 31B + Gemma 4 E4B、Qwen3-30B + Qwen3-1.5B），兩者的訓練分佈相近，drafter 猜的 token 跟 target 的取樣常常一致，acceptance rate 落在最高的那一段；不同 family 時分佈差得遠，加速接近 1×。理論加速等於 K × acceptance rate，而 acceptance rate 隨任務難度與 sampling temperature 變動，寫 code 這類工作流的實際加速要用 `llama-bench` 在自己的工作負載上量，別處量到的數字換到自己的任務上不一定成立。量到的 acceptance rate 低於 0.3 時，drafter 與 target 多半不匹配，加速接近 1× 甚至比純 target 慢，換 drafter 的效果大於調參數；落在 0.3 到 0.5 之間時，搭配本身可用而還沒到一般搭配的 0.5 ~ 0.7，調 K 或 sampling 設定收得回一部分。MTP（Multi-Token Prediction）把外接的 drafter 換成 target 內建的多預測 head，head 跟 target 同分佈，acceptance rate 通常比外接 drafter 高。
