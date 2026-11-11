---
title: "llama.cpp Tensor Split"
date: 2026-05-14
description: "llama.cpp 多 GPU 場景中把模型張量按比例切到多張卡上的權重分配機制"
weight: 1
tags: ["llm", "knowledge-cards", "gpu", "llama-cpp"]
---

llama.cpp tensor split 的核心概念是「**在多 GPU 推論時，把模型張量按比例分配到不同 GPU**」。它解的是單張卡 [VRAM](/llm/knowledge-cards/vram/) 不足或多卡容量不均時的模型權重擺放問題。

## 跟其他概念的關係

Tensor split 位在 inference server / GPU serving 層，跟 [NVLink](/llm/knowledge-cards/nvlink/) 或 [PCIe](/llm/knowledge-cards/pcie/) 是不同責任：互連決定卡間傳輸成本，tensor split 決定權重怎麼分布。

## 可觀察訊號與例子

在 llama.cpp 看到 `--tensor-split` 或 `-ts`，通常是在手動指定多卡分配比例。兩張 VRAM 不同的卡可以用不同比例，避免小卡先 OOM。

## 判斷條件與後果

Tensor split 用在多 GPU 推論、而且要手動控制各卡分配比例的時候；單卡的消費級 PC 沒有分配可做。多卡之間沒有高速互連（只走 [PCIe](/llm/knowledge-cards/pcie/)、沒有 [NVLink](/llm/knowledge-cards/nvlink/)）時，分割之後卡與卡之間要傳中間結果，傳輸成本可能抵掉多一張卡的好處，推論反而變慢。分割與否、比例多少都改變這個傳輸成本，所以用實際 benchmark 的速度決定。
