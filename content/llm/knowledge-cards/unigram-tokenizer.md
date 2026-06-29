---
title: "Unigram Tokenizer"
date: 2026-05-14
description: "以機率模型選擇子詞切分的 tokenizer 演算法，常見於 SentencePiece 的 unigram 模式"
weight: 1
tags: ["llm", "knowledge-cards", "tokenization"]
---

Unigram tokenizer 的核心概念是「**把 [token](/llm/knowledge-cards/token/) 切分視為從候選子詞集合中選最可能切分的機率問題**」。它先有一組候選 subword，再用機率模型找出最合理的切分，有別於逐步合併字元對的做法。

## 概念位置

Unigram 是 subword tokenizer 家族的一員，常由 [SentencePiece](/llm/knowledge-cards/sentencepiece/) 支援。它跟 [BPE](/llm/knowledge-cards/bpe/) 的差異在訓練與切分策略：BPE 是貪婪合併，unigram 是機率選擇與剪枝候選。

## 可觀察訊號與例子

讀 tokenizer 文件看到「unigram language model」「subword regularization」「SentencePiece unigram」就是這個概念。它可在訓練時對同一句話採不同合理切分，增加 tokenizer 層的資料多樣性。

## 設計責任

一般應用不會手動選 unigram tokenizer，但理解它能幫助比較模型的多語言支援與 token 效率。判讀時搭配 [Vocabulary Size](/llm/knowledge-cards/vocabulary-size/) 與 [Token](/llm/knowledge-cards/token/)。
