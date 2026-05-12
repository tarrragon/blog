---
title: "Flash Attention"
date: 2026-05-12
description: "Attention 計算的記憶體友善實作、減少 GPU memory 讀寫、提升長 context 推論吞吐"
weight: 1
tags: ["llm", "knowledge-cards", "attention", "performance", "optimization"]
---

Flash Attention 的核心概念是「重新組織 [Attention](/llm/knowledge-cards/attention/) 計算的順序、把中間結果留在 GPU 高速 cache、減少對 GPU memory 的讀寫往返」。它不改變 attention 的數學定義（輸出跟原始實作在浮點誤差範圍內一致）、但實作層面對長 context 推論吞吐有明顯提升、且是部分 [KV cache 量化](/llm/05-discrete-gpu/kv-cache-quantization-strategy/) 組合在 llama.cpp 上的必要前置。

## 概念位置

Flash Attention 在推論架構中的角色：

```text
推論時的 attention 計算：
  ├── 原始實作：Q · K^T 整個算完、寫進 memory、再讀出來做 softmax、再算 · V
  │     └── 多次 memory 讀寫、長 context 下 IO 成為瓶頸
  └── Flash Attention：用 tiling 把計算切塊、中間結果留在 SRAM / register
        └── 減少 memory 讀寫、長 context 加速明顯
```

跟 attention 變體的關係：

- Flash Attention 是**實作層**的優化、跟 [MHA / GQA / MLA](/llm/knowledge-cards/attention/) 等**架構層**變體是兩個獨立維度。
- 不同變體都能搭配 Flash Attention 的實作技巧。

在 llama.cpp 中的旗標：

```bash
llama-server -fa  # 啟用 flash attention
# 或
llama-server --flash-attn
```

> **事實查核註**：Flash Attention 的版本演進快（Flash Attention 1 / 2 / 3）、不同推論引擎的支援度依版本變化。具體限制（如「V cache Q4 量化要 -fa 才能啟用」）依 llama.cpp 版本變動、引用前以 `llama-server --help` 跟 release notes 為準。

## 設計責任

理解 Flash Attention 後可以解釋兩個現象：為什麼啟用 `-fa` 後長 context 推論速度提升明顯（IO bound 變 compute bound）、為什麼部分 KV cache 量化組合（如 V=Q4_0）在 llama.cpp 上需要 flash attention 才能跑（實作層面的耦合）。

工程實務上、啟用 flash attention 通常沒副作用（數學上等價、品質不變）、是 PC 場景長 context 推論的預設啟用旗標。詳見 [5.2 KV cache 量化策略](/llm/05-discrete-gpu/kv-cache-quantization-strategy/) 的 flash attention 段落。
