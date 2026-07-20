---
title: "Token"
date: 2026-05-11
description: "LLM 處理文字時的最小單位：介於字元與單字之間"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Token 的核心概念是「LLM 內部處理文字的最小單位」，介於字元（character）與單字（word）之間。模型接收 prompt 前會先用 tokenizer 把文字切成 token 序列，輸出時也以 token 為單位逐個生成，序列切法與長度由 tokenizer 的 [vocabulary size](/llm/knowledge-cards/vocabulary-size/) 決定。Token 是計費、速度、context 容量等所有 LLM 量化指標的共同單位。

## 概念位置

Token 位於介面層送出文字與模型層實際運算之間的轉換點。介面層的「字串」進入模型前會被 tokenizer 切成整數序列；模型輸出的整數序列再被 tokenizer 還原成字串給介面層顯示。不同模型用不同 tokenizer（多數採 [BPE](/llm/knowledge-cards/bpe/) 或其變體），同一段文字在 GPT、Claude、Gemma 上切出的 token 數量會有差異。

## 可觀察訊號與例子

英文約「4 個字元 ≈ 1 token」，中文約「1 ~ 2 個字 ≈ 1 token」。`Hello, world!` 約 4 個 token；「你好，世界」約 5 ~ 7 個 token，視 tokenizer 而定。雲端 API 的計費單據用 token 計量，本地推論的速度指標 [tokens per second](/llm/knowledge-cards/tokens-per-second/) 也以 token 為單位。

## 設計責任

理解 token 後可以做幾件實用判斷：估算 prompt 是否會超過 [context window](/llm/knowledge-cards/context-window/)、估算雲端 API 費用、解讀 benchmark 數字。寫程式時用 OpenAI 的 `tiktoken`、Hugging Face 的 `transformers.AutoTokenizer` 可以精確計算特定模型的 token 數量。
