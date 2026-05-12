---
title: "Mixture of Experts (MoE)"
date: 2026-05-12
description: "把 transformer 的 FFN 層拆成多個專家、每 token 只啟用少數、總參數大但每 token 計算量小的架構"
weight: 1
tags: ["llm", "knowledge-cards", "model-architecture", "moe"]
---

MoE（Mixture of Experts）的核心概念是「把 transformer block 內的 FFN 層拆成多個專家網路、router 為每個 token 動態挑選少數啟用」。結果是模型總參數可以擴張到很大、但每個 token 實際計算量保持在「[active parameter](/llm/knowledge-cards/active-parameter/)」這個較小的數目；同硬體下 MoE 模型常比同總參數的 Dense 模型跑得快、且能力強於同 active parameter 的 Dense 模型。

## 概念位置

MoE 在 transformer 架構中的位置：

```text
transformer block：
  ├── attention 層（所有 token 共用）
  ├── layer norm
  └── FFN 層
        ├── Dense 架構：所有 token 走同一組 FFN
        └── MoE 架構：FFN 拆成多個 expert、router 挑選 top-k 個啟用
```

主流 MoE 模型的設計選擇（依模型而異）：

- **expert 數量**：通常 8 ~ 256 個
- **每 token 啟用 expert 數**：通常 1 ~ 2 個（top-k routing）
- **shared expert**：部分模型保留少數所有 token 共用的 expert
- **total / active parameter 比**：常見 5x ~ 10x（如 Qwen3-30B-A3B：30B total / 3B active）

> **事實查核註**：MoE 架構的具體實作（router 演算法、load balancing loss、expert 並行策略等）依模型快速演進、引用前以該模型的技術報告或 paper 為準。

代表性 MoE 模型（依公開資訊）：Mixtral 8x7B、DeepSeek V3、Qwen3-30B-A3B、Llama 4 Scout 等。

## 設計責任

理解 MoE 後可以解釋三個現象：為什麼 MoE 模型的「30B 總參數」跟「3B active parameter」是兩個獨立指標（前者影響記憶體需求、後者影響速度）、為什麼 MoE 適合 [CPU 卸載](/llm/knowledge-cards/moe-cpu-offload/)（不活躍的 expert 可以留在系統 RAM）、為什麼 MoE 在多 GPU 場景的並行策略跟 Dense 模型不同（expert 可以分到不同卡）。

選 MoE 模型 vs Dense 模型、需考慮：MoE 對 RAM 容量要求較高（要放所有 expert 權重）、對 GPU 算力要求較低（每 token 走 active parameter）；Dense 對 VRAM 容量要求較低（可全載中型模型）、對 GPU 算力要求較高。詳見 [5.1 MoE 模型與 CPU 卸載策略](/llm/05-discrete-gpu/moe-cpu-offload-strategy/) 跟 [5.5 PC 場景的模型選型優先順序](/llm/05-discrete-gpu/model-selection-priority-pc/)。
