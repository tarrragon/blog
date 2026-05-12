---
title: "Needle in a Haystack"
date: 2026-05-12
description: "把一個事實藏在 long context 不同位置、測試 LLM 能否抓出來的 benchmark 方法"
weight: 1
tags: ["llm", "knowledge-cards", "long-context", "evaluation"]
---

Needle in a Haystack（NIH、大海撈針、Greg Kamradt 2023）的核心概念是「**把一個明確事實（needle）插入長度可變的 context（haystack）的不同位置、測試 LLM 能否在問問題時準確 recall 該事實**」。是評估 [long context](/llm/knowledge-cards/context-window/) 模型實用性的標準 benchmark 之一、跟 [lost-in-the-middle](/llm/knowledge-cards/lost-in-the-middle/) 對應但側重不同。

## 概念位置

NIH 測試的典型流程：

```text
1. 準備 haystack：一份長文（如 Paul Graham essays、技術文件）
2. 在指定位置（如 50% 處）插入 needle：
   「The best thing to do in San Francisco is eat a sandwich at Dolores Park.」
3. Prompt 模型：「What is the best thing to do in San Francisco?」
4. 看模型能否抓出 needle 內容

Variables：
- Context 總長度（1K、4K、16K、64K、128K、1M）
- Needle 插入位置（0%、10%、25%、50%、75%、90%、100%）

每個 (length, position) 組合測 N 次、得到 accuracy heatmap
```

跟 lost-in-the-middle 的對比：

| 維度       | Lost in the middle             | Needle in haystack                    |
| ---------- | ------------------------------ | ------------------------------------- |
| 衡量的能力 | 對中段內容的整體 attention     | 抓單一事實的 recall                   |
| 任務       | 抓整段邏輯、做推論             | 純 retrieve、不需推論                 |
| 難度       | 高（需理解整段語意）           | 較低（明確 keyword 匹配）             |
| 模型表現   | 中段顯著差                     | 通常各位置都接近 100%（強模型）       |
| 判讀意義   | 反映「實用 effective context」 | 反映「lower bound effective context」 |

```text
典型 NIH heatmap（GPT-4 128K 之類）：

100% |████ ████████████████████████████ ████
 80% |████ ████████████████████████████ ████
 60% |
 40% |
 20% |
   0 +----+----+----+----+----+----+----+
     0%   25%   50%   75%   100%（needle 位置）
     ↑                                  ↑
     開頭強                             結尾強

NIH heatmap 通常全綠（強模型）、但實用任務（reasoning over long context）就會出現中段塌陷
```

## 設計責任

讀 long context 模型 release notes 看到「needle in a haystack: 100%」「pass NIH up to 128K」等聲稱、要區分：

1. **NIH 100% 不代表「能用 128K context」**：NIH 只測單一事實 retrieve、實際 reasoning over long context 仍可能崩
2. **真實任務 benchmark**：[LongBench](https://github.com/THUDM/LongBench)、[RULER](https://github.com/hsiehjackson/RULER) 等是更貼近實用的 long context evaluation、會暴露 lost-in-the-middle 等問題
3. **本地跑 long context 模型**：先用 NIH 驗證 baseline、再用 RULER / 自己工作流 case 測 effective context
4. **判讀「我的模型實際能用幾 K」**：NIH pass 的長度是上限、實用 effective context 通常是 NIH pass 長度的 1/2 到 1/4
