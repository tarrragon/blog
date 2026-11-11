---
title: "In-Context Learning"
date: 2026-05-14
description: "模型在不更新權重的情況下，從 prompt 內範例、規則與上下文臨時對齊任務的能力"
weight: 1
tags: ["llm", "knowledge-cards", "prompting", "training"]
---

In-context learning（ICL）的核心概念是「**模型在不更新權重的情況下，從 [context window](/llm/knowledge-cards/context-window/) 內資訊臨時學會任務格式與判斷標準**」。它是 LLM 跟傳統模型最不同的能力之一：任務規則可以放在 context 裡，而不是一定要 fine-tune 進權重。

## 跟其他概念的關係

ICL 是推論時行為，不是訓練流程。[Few-shot prompting](/llm/knowledge-cards/few-shot-prompting/) 是 ICL 最常見的操作方式；SFT、LoRA、QLoRA 則是修改權重的訓練或微調方式。

## 可觀察訊號與例子

給模型三個分類範例後，第四個樣本就按同一標準分類，這是 ICL。把專案命名規則、輸出格式、review rubric 放進 prompt，模型在當次回合遵守，也屬於 ICL。

## 判斷條件與後果

ICL 跟 fine-tune 之間的選擇看範例量與標準的穩定度。範例少、標準還在調整時，改 context 就改了模型這一次的行為，不必重新訓練，迭代以分鐘計；範例多到佔滿 [context window](/llm/knowledge-cards/context-window/)、每天重複使用而且標準已經穩定時，每次推論都重付同一批範例的 token，把標準一次訓練進權重的 fine-tune 這時才划算。ICL 讓模型照範例模仿格式，不保證每次輸出都合法，所以需要穩定輸出格式時，搭配 [structured output](/llm/knowledge-cards/structured-output/) 或 validator 擋下不合法的輸出。
