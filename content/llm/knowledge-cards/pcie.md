---
title: "PCIe"
date: 2026-05-12
description: "PC 上連接 GPU 跟主機板的高速序列匯流排、影響模型載入速度跟 MoE 卸載時的推論吞吐"
weight: 1
tags: ["llm", "knowledge-cards", "hardware", "bus"]
---

PCIe（PCI Express）的核心概念是「PC 上 GPU 跟主機板（CPU + 系統 RAM）之間的高速序列匯流排」。獨立 GPU 場景下、模型權重從 SSD / 系統 RAM 走 PCIe 進 VRAM、之後推論主要在 GPU 內部完成；但 [MoE CPU 卸載](/llm/knowledge-cards/moe-cpu-offload/) 啟用時、每 token 都需要從系統 RAM 走 PCIe 拉部分權重、PCIe 頻寬開始影響推論吞吐。

## 概念位置

PCIe 在本地 LLM 推論的兩個階段角色不同：

1. **模型載入階段**：模型權重從 SSD → 系統 RAM → 走 PCIe → [VRAM](/llm/knowledge-cards/vram/)。PCIe 是常見瓶頸、影響「啟動時間」、不影響推論。
2. **推論階段**：
   - 全載 VRAM 場景：權重已在 VRAM、推論時 PCIe 流量很少。
   - MoE 卸載場景：每 token 從系統 RAM 拉專家權重經 PCIe、PCIe 頻寬成為次要瓶頸。

PCIe 版本跟頻寬（廠商標稱、單向）：

| 版本         | x16 單向標稱頻寬 |
| ------------ | ---------------- |
| PCIe 4.0 x16 | 約 32 GB/s       |
| PCIe 5.0 x16 | 約 64 GB/s       |
| PCIe 6.0 x16 | 約 128 GB/s      |

實際傳輸吞吐受驅動、檔案系統、量化格式影響、通常低於規格上限。

> **事實查核註**：PCIe 各版本的標稱頻寬數字以 [PCI-SIG](https://pcisig.com/) 官方規格為主、實際可達吞吐依硬體配置變化、引用前以對應版本的官方規格文件為準。

消費級主機板的 PCIe lane 分配常見「一條 x16 + 一條 x4」、加第二張 GPU 時、第二張的有效頻寬可能只有 x4、影響多卡縮放效益。詳見 [5.3 llama.cpp 在 PC 上](/llm/05-discrete-gpu/llama-cpp-on-pc/) 的多卡 tensor split 段落。

## 設計責任

理解 PCIe 後可以解釋三個現象：為什麼模型載入要等幾秒到十幾秒（PCIe 是橋）、為什麼單卡 + MoE 卸載通常不卡 PCIe（每 token 拉的權重量小於 PCIe 頻寬）、為什麼雙卡縮放比沒有直接翻倍（PCIe lane 跟主機板配置）。

選 PC 配置時、PCIe 版本影響模型載入體感、但對單人推論的生字速度通常影響小。多卡升級前要看主機板的 PCIe lane 分配。
