---
title: "Frozen baseline"
date: 2026-05-14
description: "Eval 系統中固定特定 prompt + model 當長期對照、讓行為漂移可見的標準作法"
weight: 1
tags: ["llm", "knowledge-cards", "evaluation", "production"]
---

Frozen baseline 的核心概念是「**把某個特定 prompt + 特定 model 跑 production 一段時間後 freeze、每次新版本都跟它比、定期 refresh 並標明時點**」。Eval 系統的標準作法（常搭配 [LLM-as-judge](/llm/knowledge-cards/llm-as-judge/) 評分）、讓行為漂移可見、避免「永遠跟上一版比、長期累積漂移看不見」的常見失敗。

## 概念位置

跟其他 eval 概念對照：

| 概念                                                  | 角色                                          |
| ----------------------------------------------------- | --------------------------------------------- |
| Eval set                                              | 測試 input 的集合                             |
| Frozen baseline                                       | 固定的「對照組」prompt + model 版本           |
| Regression set                                        | Failed case 進來、防止改 prompt 又壞同樣 case |
| [Production trace](/llm/knowledge-cards/llm-tracing/) | 實際 traffic、抽樣補進 eval set / baseline    |

工作流：

```text
Day 1：定義 eval set + 初始 prompt + model
   ↓ 跑 production 一段時間（如 2 週）
Day 14：把當下 prompt + model freeze 成 baseline-v1
   ↓
新版本 prompt / model 都跟 baseline-v1 比
   ↓ 定期（如每季）refresh
Day 90：baseline-v2、標明 refresh 時點
```

## 設計責任

讀 eval / production AI 文章看到「frozen baseline」「baseline drift」「regression set」就是這個機制。實作判讀：

1. **為什麼必要**：每次 A/B 都跟「最新版本」比、長期累積漂移完全不可見、「整體變好了沒」無從回答。Frozen baseline 是漂移的錨點。
2. **何時 freeze**：production 跑穩、user 滿意度可接受時 freeze。太早 freeze 鎖到不夠好的版本、太晚 freeze 鎖不到。
3. **何時 refresh**：定期（每季 / 每半年）、或當 baseline 明顯 obsolete（如 model 升級、產品大改版）。Refresh 後標明時點、舊版本仍可保留當歷史對照。
4. **跟 frozen baseline 一起的還有**：regression set（failed case 永遠進、防 fix 一個壞一個）、production trace 抽樣補進 eval set（讓 eval set 不脫節）。
5. **失敗模式**：baseline 跟 production 分佈差太遠（baseline 用 lab case、production 是 wild input）、跑出來分數沒參考價值。緩解：baseline 的 eval set 用 production trace 抽樣建。

完整 eval 系統設計見 [4.13 Eval 設計座標系](/llm/04-applications/eval-design-framework/)。
