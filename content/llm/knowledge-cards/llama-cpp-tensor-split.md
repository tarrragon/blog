---
title: "llama.cpp Tensor Split"
date: 2026-05-14
description: "llama.cpp 多 GPU 場景中把模型張量按比例切到多張卡上的權重分配機制"
weight: 1
tags: ["llm", "knowledge-cards", "gpu", "llama-cpp"]
---

llama.cpp tensor split 的核心概念是「**在多 GPU 推論時，把模型張量按比例分配到不同 GPU**」。它解的是單張卡 [VRAM](/llm/knowledge-cards/vram/) 不足或多卡容量不均時的模型權重擺放問題。

## 概念位置

Tensor split 位在 inference server / GPU serving 層，跟 [NVLink](/llm/knowledge-cards/nvlink/) 或 [PCIe](/llm/knowledge-cards/pcie/) 是不同責任：互連決定卡間傳輸成本，tensor split 決定權重怎麼分布。

## 可觀察訊號與例子

在 llama.cpp 看到 `--tensor-split` 或 `-ts`，通常是在手動指定多卡分配比例。兩張 VRAM 不同的卡可以用不同比例，避免小卡先 OOM。

## 設計責任

只有多 GPU 且需要手動控制分配時才需要它。單卡消費級 PC 通常不用；多卡沒有高速互連時，分割模型可能降低速度，需用實際 benchmark 校準。
