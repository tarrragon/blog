---
title: "SWE-bench"
date: 2026-05-11
description: "用真實 GitHub issue 量化 LLM coding 能力的 benchmark"
weight: 1
tags: ["llm", "knowledge-cards"]
---

SWE-bench 的核心概念是「用真實開源專案的 GitHub issue 與 PR 當測試集、評量 LLM 解程式碼問題的能力」，是 [LLM benchmarks](/llm/knowledge-cards/llm-benchmarks/) 中聚焦程式碼修復能力的一種。它把 LLM 放在「給一個 issue 描述、看能否生成解決它的 patch」的任務上、跑完用 patch 是否能讓既有測試通過作為通過率。

## 概念位置

SWE-bench 比早期的 HumanEval（單一 function 生成）難得多、涵蓋多檔案理解、需求拆解、實際 patch 生成。它是 2026 年量化 coding LLM 能力最常被引用的指標、也是 [LLM benchmarks](/llm/knowledge-cards/llm-benchmarks/) 一覽表中的常見成員。SWE-bench Verified 是 OpenAI 篩選過的子集、確保任務描述清楚、是現在報告主流。

## 可觀察訊號與例子

2026 年 5 月各模型在 SWE-bench Verified 上的大致表現（僅供量級參考、實際數字以官方報告為準）：

| 模型                    | SWE-bench Verified |
| ----------------------- | ------------------ |
| Claude Sonnet 4.6       | 80+ 分             |
| GPT-5                   | 80+ 分             |
| Qwen3-Coder 30B（本地） | 77.2 分            |
| Gemma 4 31B（本地）     | 70+ 分             |
| Qwen3 14B               | 50+ 分             |

「分數」是百分比、代表通過率。本地最強模型在 SWE-bench 上跟雲端旗艦仍有差距、但對寫 code 場景已堪用。

## 設計責任

評估模型適合不適合本地寫 code 時、SWE-bench Verified 是核心指標之一。換新模型前看分數差距：5 分以上才值得試（適應新 prompt 風格的成本不低）。看到「新模型超越 GPT-X」報導時、確認是哪個 SWE-bench 變體（Lite / Verified / Full）；變體間分數差很多、混為一談會誤判。
