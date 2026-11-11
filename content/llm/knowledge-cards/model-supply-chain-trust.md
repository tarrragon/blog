---
title: "Model Supply-Chain Trust"
date: 2026-05-14
description: "判斷模型權重、量化版本、registry 與本機檔案是否可信的供應鏈信任框架"
weight: 1
tags: ["llm", "knowledge-cards", "security", "supply-chain"]
---

Model supply-chain trust 的核心概念是「**把模型權重來源、量化者、registry 與本機檔案都視為信任邊界**」。本地 LLM 下載的是可影響模型行為的 [GGUF](/llm/knowledge-cards/gguf/) 或其他權重檔，來源與完整性會直接影響安全與可靠性。

## 跟其他概念的關係

它位在模型層與安全治理交界，跟 [model card](/llm/knowledge-cards/model-card/) 不同：model card 提供 metadata，supply-chain trust 判斷來源、hash、量化流程、namespace 與散發路徑是否可信。

## 可觀察訊號與例子

官方 organization、知名量化者、verified registry、可比對 hash、清楚 license 與 model card 都提升信任；個人上傳、來源不明、檔案被替換、缺 metadata 都降低信任。GGUF、Safetensors、Ollama registry、Hugging Face Hub 都在這條鏈上。

## 判斷條件與後果

模型檔的來源無法確認時，下載的權重可能被替換過，而權重決定模型行為，所以推論結果與安全性都失去依據；官方 organization、知名量化者與 verified registry 是可以確認來源的那一端。下載之後沒有記下 SHA-256、檔案大小與版本時，檔案之後被換掉也比對不出來，出問題時說不出當初用的是哪一份。第三方量化的版本多了一個信任對象：量化者沒有信譽或社群採用紀錄時，量化流程是否只做了它宣稱的精度轉換無從查證。MCP server 與 plugin 是另一條供應鏈，散發的是可執行程式碼而不是權重，它在本機執行時拿得到的權限比權重檔大，所以判讀標準比權重檔更嚴。
