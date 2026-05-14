---
title: "In-Context Learning"
date: 2026-05-14
description: "模型在不更新權重的情況下，從 prompt 內範例、規則與上下文臨時對齊任務的能力"
weight: 1
tags: ["llm", "knowledge-cards", "prompting", "training"]
---

In-context learning（ICL）的核心概念是「**模型在不更新權重的情況下，從 [context window](/llm/knowledge-cards/context-window/) 內資訊臨時學會任務格式與判準**」。它是 LLM 跟傳統模型最不同的能力之一：任務規則可以放在 context 裡，而不是一定要 fine-tune 進權重。

## 概念位置

ICL 是推論時行為，不是訓練流程。[Few-shot prompting](/llm/knowledge-cards/few-shot-prompting/) 是 ICL 最常見的操作方式；SFT、LoRA、QLoRA 則是修改權重的訓練或微調方式。

## 可觀察訊號與例子

給模型三個分類範例後，第四個樣本就按同一標準分類，這是 ICL。把專案命名規則、輸出格式、review rubric 放進 prompt，模型在當次回合遵守，也屬於 ICL。

## 設計責任

ICL 適合快速迭代與少量範例；當範例多到吃滿 [context window](/llm/knowledge-cards/context-window/)、每天重複使用且標準穩定時，再考慮 fine-tune。需要穩定輸出格式時，ICL 應搭配 [structured output](/llm/knowledge-cards/structured-output/) 或 validator。
