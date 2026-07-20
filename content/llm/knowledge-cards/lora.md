---
title: "LoRA"
date: 2026-05-12
description: "Low-Rank Adaptation：凍住原模型權重、只訓兩個小矩陣的 parameter-efficient fine-tuning"
weight: 1
tags: ["llm", "knowledge-cards", "training", "fine-tuning"]
---

LoRA（Low-Rank Adaptation、低秩適配）的核心概念是「**凍住原模型所有權重、在指定 layer 旁邊掛兩個小矩陣 A、B（rank 很低、如 r=8）、只訓 A、B**」。凍住原權重的好處之一是避開整個模型被覆寫造成的 [catastrophic forgetting](/llm/knowledge-cards/catastrophic-forgetting/)。Hu et al. (2021) 提出、是現在 fine-tuning 的主流選擇、大幅降低訓練成本與記憶體需求。

## 概念位置

LoRA 的數學形式：

```text
原 layer 輸出：y = W × x       （W 凍住）
加 LoRA 後：  y = W × x + B × A × x
                          └──┬──┘
                       LoRA update（rank r）
                       A shape: (r, hidden_dim)
                       B shape: (hidden_dim, r)
```

關鍵特性：

| 維度             | 完整 fine-tuning        | LoRA fine-tuning（r=16）         |
| ---------------- | ----------------------- | -------------------------------- |
| 可訓練參數       | 全部（如 7B、70B）      | ~0.1% ~ 1%（只 A、B）            |
| GPU 記憶體       | 高（要存所有 gradient） | 大幅降低                         |
| Adapter 檔案大小 | 跟原模型同大            | 幾 MB ~ 幾百 MB                  |
| 訓練成本         | 全模型 backprop         | 只算 A、B 的 gradient            |
| 部署             | 載入新模型              | 載入原模型 + adapter、推論時合併 |
| 多任務切換       | 載入不同模型            | 切換 adapter 即可（同個底）      |

[QLoRA](/llm/knowledge-cards/qlora/)（Dettmers et al., 2023）進一步把原模型量化到 4-bit、LoRA 訓在量化模型上、消費級 GPU 也能 fine-tune 大模型。

## 設計責任

讀 fine-tuning 教學 / Hugging Face PEFT 看到 LoRA、QLoRA 是現在主流。寫 code 場景的判讀：LoRA 適合「在現有模型上加領域知識 / 風格」（如教模型用特定 codebase 慣例）、不適合「教模型新世界知識」（仍要 [pre-training](/llm/knowledge-cards/pre-training/) 級資料）；adapter 形式讓「多客戶 / 多風格」場景可以共用 base model、只切換 adapter、節省 GPU 記憶體。
