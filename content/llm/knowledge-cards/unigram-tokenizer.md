---
title: "Unigram Tokenizer"
date: 2026-05-14
description: "以機率模型選擇子詞切分的 tokenizer 演算法，常見於 SentencePiece 的 unigram 模式"
weight: 1
tags: ["llm", "knowledge-cards", "tokenization"]
---

Unigram tokenizer 的核心概念是「**把 [token](/llm/knowledge-cards/token/) 切分視為從候選子詞集合中選最可能切分的機率問題**」。它先有一組候選 subword，再用機率模型找出最合理的切分，有別於逐步合併字元對的做法。

## 跟其他概念的關係

Unigram 是 subword tokenizer 家族的一員，常由 [SentencePiece](/llm/knowledge-cards/sentencepiece/) 支援。它跟 [BPE](/llm/knowledge-cards/bpe/) 的差異在訓練與切分策略：BPE 是貪婪合併，unigram 是機率選擇與剪枝候選。

## 可觀察訊號與例子

讀 tokenizer 文件看到「unigram language model」「subword regularization」「SentencePiece unigram」就是這個概念。它可在訓練時對同一句話採不同合理切分，增加 tokenizer 層的資料多樣性。

## 判斷條件與後果

一般應用選的是模型，unigram tokenizer 隨模型的 tokenizer 一起決定，使用者不另外選它。它的影響出現在比較模型的多語言支援與 token 效率時：tokenizer 的切分方式與 [Vocabulary Size](/llm/knowledge-cards/vocabulary-size/) 一起決定某種語言的文字被切得多碎，切得越碎，同一段文字佔的 [Token](/llm/knowledge-cards/token/) 越多，context 用量與 API 費用越高。所以兩個模型在同一種語言上的 token 數差很多時，差別的來源在 tokenizer 這一層，而不在模型的生成能力。
