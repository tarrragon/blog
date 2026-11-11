---
title: "Frozen baseline"
date: 2026-05-14
description: "Eval 系統中固定特定 prompt + model 當長期對照、讓行為漂移可見的標準作法"
weight: 1
tags: ["llm", "knowledge-cards", "evaluation", "production"]
---

Frozen baseline 的核心概念是「**把某個特定 prompt + 特定 model 跑 production 一段時間後 freeze、每次新版本都跟它比、定期 refresh 並標明時點**」。Eval 系統的標準作法（常搭配 [LLM-as-judge](/llm/knowledge-cards/llm-as-judge/) 評分）、讓行為漂移可見、避免「永遠跟上一版比、長期累積漂移看不見」的常見失敗。

## 跟其他概念的關係

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

## 判斷條件與後果

Frozen baseline 的判斷看三個條件：每一版拿什麼當對照、baseline 在什麼時點凍結與更新，以及 baseline 的 eval set 跟 production 輸入的分佈差多遠。

1. **每次 A/B 都跟上一版比時**，單次的差距小到看起來都可以接受，好幾版累積的漂移卻沒有任何一次比較量得到，「整體比三個月前好還是壞」沒有數字可答；frozen baseline 是固定不動的對照點，累積的漂移才量得出來。
2. **凍結得太早時**（production 還沒跑穩、使用者滿意度還不能接受），之後每一版都跟一個不夠好的版本比，「贏過 baseline」不代表夠好；一直不凍結則回到上一項的處境。
3. **model 升級或產品大改版之後**，舊 baseline 處理的輸入跟現在的產品不同，跟它比的分數失去對照意義，所以這時更新 baseline（沒有這類事件時也定期更新，例如每季或每半年）；更新時標明時點、留著舊版當歷史對照，漂移的紀錄在更新那一刻才接得上。
4. **baseline 的 eval set 用實驗室設計的案例、而 production 是使用者的真實輸入時**，兩者分佈不同，分數反映的是實驗室案例上的表現，對 production 沒有參考價值；eval set 從 production trace 抽樣建，分佈才對得上。
5. **修好的 failed case 沒有收進 regression set 時**，下一次改 prompt 可能把同一個 case 再改壞而沒有任何比較抓得到，所以 regression set 跟 frozen baseline 一起跑。

完整 eval 系統設計見 [4.13 Eval 設計座標系](/llm/04-applications/eval-design-framework/)。
