---
title: "Instruction Following"
date: 2026-05-14
description: "模型遵守任務範圍、格式、限制與停止條件的能力，是評估 instruction-tuned 模型能否落地的核心訊號"
weight: 1
tags: ["llm", "knowledge-cards", "evaluation", "prompting"]
---

Instruction following 的核心概念是「**模型能否遵守使用者或系統給定的任務約束**」。它關注模型是否照格式輸出、是否留在任務範圍、是否遵守長度與禁止事項，跟 [instruction-tuned model](/llm/knowledge-cards/instruction-tuned/) 這種訓練後模型類型相關，但不是同一件事。

## 概念位置

[Instruction-tuned model](/llm/knowledge-cards/instruction-tuned/) 是訓練狀態，instruction following 是行為表現。模型可能經過 SFT，仍在細格式、邊界條件或多約束任務上失敗；也可能在簡單指令上表現穩定，但遇到衝突指令或長 prompt 漏掉限制。

## 可觀察訊號與例子

測試訊號包含：是否輸出指定 JSON、是否只回答要求的欄位、是否避免多餘解釋、是否在資料不足時說不知道、是否遵守「不要呼叫工具」或「只讀不寫」。本地小模型常在簡單問答可用，但在多條格式限制同時存在時掉分。

## 設計責任

評估 instruction following 時要做 coverage 測試：格式、長度、拒答、資料不足、衝突指令、跨語言指令都要看。失敗時優先用更清楚的 prompt、few-shot、structured output 或 validator 兜底；長期穩定需求才考慮 fine-tune。
