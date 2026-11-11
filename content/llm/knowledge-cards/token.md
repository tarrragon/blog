---
title: "Token"
date: 2026-05-11
description: "LLM 處理文字時的最小單位：介於字元與單字之間"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Token 的核心概念是「LLM 內部處理文字的最小單位」，介於字元（character）與單字（word）之間。模型接收 prompt 前會先用 tokenizer 把文字切成 token 序列，輸出時也以 token 為單位逐個生成，序列切法與長度由 tokenizer 的 [vocabulary size](/llm/knowledge-cards/vocabulary-size/) 決定。Token 是計費、速度、context 容量等所有 LLM 量化指標的共同單位。

## 跟其他概念的關係

Token 位於介面層送出文字與模型層實際運算之間的轉換點。介面層的「字串」進入模型前會被 tokenizer 切成整數序列；模型輸出的整數序列再被 tokenizer 還原成字串給介面層顯示。不同模型用不同 tokenizer（多數採 [BPE](/llm/knowledge-cards/bpe/) 或其變體），同一段文字在 GPT、Claude、Gemma 上切出的 token 數量會有差異。

## 可觀察訊號與例子

英文約「4 個字元 ≈ 1 token」，中文約「1 ~ 2 個字 ≈ 1 token」。`Hello, world!` 約 4 個 token；「你好，世界」約 5 ~ 7 個 token，視 tokenizer 而定。雲端 API 的計費單據用 token 計量，本地推論的速度指標 [tokens per second](/llm/knowledge-cards/tokens-per-second/) 也以 token 為單位。

## 判斷條件與後果

Prompt 能不能放進 [context window](/llm/knowledge-cards/context-window/)、雲端 API 收多少費用、benchmark 的長度數字，都以 token 計量，所以拿字數或字元數去估，估出來的值會隨語言與 tokenizer 偏移。英文約 4 個字元 1 個 token，中文約 1 到 2 個字 1 個 token；用英文的換算估中文 prompt，會低估 token 數，prompt 實際長度可能超過 context window，費用也比預估高。換模型時，同一段文字切出的 token 數也不同，原因是各模型用不同的 tokenizer，拿 A 模型的 token 數估 B 模型的用量會有誤差。需要精確值時，用該模型的 tokenizer 計算：OpenAI 的 `tiktoken`，或 Hugging Face 的 `transformers.AutoTokenizer`。
