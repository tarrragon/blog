---
title: "NVLink"
date: 2026-05-12
description: "NVIDIA 多 GPU 之間的高速互連介面、提供比 PCIe 更高的卡間頻寬、消費級 RTX 系列普遍不支援"
weight: 1
tags: ["llm", "knowledge-cards", "hardware", "multi-gpu", "nvidia"]
---

NVLink 的核心概念是「NVIDIA 自家的 GPU 之間高速互連介面、頻寬高於 [PCIe](/llm/knowledge-cards/pcie/)、適合多卡 tensor parallel 場景」。資料中心級 GPU（如 A100 / H100 / H200）普遍支援、消費級 RTX 30 系列部分支援（如 3090）、RTX 40 / 50 系列普遍移除 NVLink、消費級多卡通常只能走 PCIe。

## 概念位置

NVLink 在多卡推論場景的角色：

1. **tensor parallel**：把一個 transformer 層的 weight 切到多張卡、每 token 計算時需要卡間同步、卡間頻寬影響直接。
2. **pipeline parallel**：把不同層分到不同卡、卡間需要傳 activation、頻寬要求中等。
3. **資料分發**：把不同 request 分到不同卡（data parallel）、卡間流量低、PCIe 也夠。

頻寬對照（廠商標稱、依世代變化）：

| 介面           | 卡間頻寬（標稱）         |
| -------------- | ------------------------ |
| PCIe 4.0 x16   | 約 32 GB/s 單向          |
| PCIe 5.0 x16   | 約 64 GB/s 單向          |
| NVLink（H100） | 約 900 GB/s 雙向、依世代 |
| NVLink（A100） | 約 600 GB/s 雙向         |

NVLink 比 PCIe 高一個量級、是資料中心多卡推論的關鍵；消費級 RTX 場景多卡通常只能走 PCIe、縮放效益相對受限。

> **事實查核註**：NVLink 各世代的頻寬數字依 NVIDIA 官方規格、不同 GPU 跟世代有差異；NVLink 在哪些消費級 / 工作站 / 資料中心 GPU 可用、依時段跟廠商策略變化、引用前以 [NVIDIA 官方產品頁](https://www.nvidia.com/) 跟對應 GPU 的 datasheet 為準。

## 設計責任

理解 NVLink 後可以解釋兩個現象：為什麼資料中心多卡 LLM 推論能線性 scale（NVLink 頻寬足以做 tensor parallel）、為什麼消費級雙卡 RTX 推論縮放比通常低於線性（沒 NVLink、走 PCIe x4 / x8、卡間頻寬限制）。

選消費級 GPU 跑本地 LLM 時、NVLink 不是常見選項；多卡升級的判讀應該基於「能否容忍縮放比低於線性」、而不是預期 NVLink 等級的卡間頻寬。詳見 [5.6 GPU 廠商差異](/llm/05-discrete-gpu/gpu-vendor-differences/)。
