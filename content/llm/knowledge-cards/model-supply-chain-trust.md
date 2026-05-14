---
title: "Model Supply-Chain Trust"
date: 2026-05-14
description: "判斷模型權重、量化版本、registry 與本機檔案是否可信的供應鏈信任框架"
weight: 1
tags: ["llm", "knowledge-cards", "security", "supply-chain"]
---

Model supply-chain trust 的核心概念是「**把模型權重來源、量化者、registry 與本機檔案都視為信任邊界**」。本地 LLM 下載的是可影響模型行為的 [GGUF](/llm/knowledge-cards/gguf/) 或其他權重檔，來源與完整性會直接影響安全與可靠性。

## 概念位置

它位在模型層與安全治理交界，跟 [model card](/llm/knowledge-cards/model-card/) 不同：model card 提供 metadata，supply-chain trust 判斷來源、hash、量化流程、namespace 與散發路徑是否可信。

## 可觀察訊號與例子

官方 organization、知名量化者、verified registry、可比對 hash、清楚 license 與 model card 都提升信任；個人上傳、來源不明、檔案被替換、缺 metadata 都降低信任。GGUF、Safetensors、Ollama registry、Hugging Face Hub 都在這條鏈上。

## 設計責任

下載模型前確認來源；下載後記錄 SHA-256、檔案大小與版本；第三方量化要看量化者信譽與社群採用。MCP server 與 plugin 是另一條可執行程式碼供應鏈，要用更高權限標準判讀。
