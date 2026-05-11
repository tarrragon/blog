---
title: "3.8 想學更深：推薦公開課程"
date: 2026-05-11
description: "Karpathy、Stanford CS224N / CS25 / CS336、DeepLearning.AI、Hugging Face：LLM 理論深入學習的完整路線"
tags: ["llm", "theory", "courses"]
weight: 8
---

本模組前八章把 LLM 理論基礎走過一遍：神經網路、embedding、attention、Transformer 架構、訓練流程、sampling、tokenization。深入學習需要更系統的課程、實作練習、跟 paper 閱讀。本章整理「LLM 理論深入」這條學習路線上的高品質資源、標出每門課的定位與適合的讀者。

本章跟[模組二 2.4 數學基礎公開課](/llm/02-math-foundations/going-deeper-math/) 互補：那邊是數學工具、這邊是 LLM 理論機制。兩者組合涵蓋從零基礎到能跟業界研究接軌的完整路線。

## 路線總覽

| 階段 | 內容                     | 適合背景             |
| ---- | ------------------------ | -------------------- |
| 1    | 視覺化 + 直觀理解        | 任何工程背景         |
| 2    | 動手實作 LLM             | 想直接看完整系統     |
| 3    | NLP + Transformer 系統課 | 想紮實打底           |
| 4    | LLM 完整 lifecycle       | 想做 LLM 應用 / 訓練 |
| 5    | 最新研究進展             | 想跟業界 / 學界進度  |

## 階段 1：3Blue1Brown LLM 視覺化系列

Grant Sanderson 的「Neural Networks」+「But what is a GPT?」系列、視覺化動畫解釋 Transformer 內部運作。

| 影片                                   | 涵蓋                                              |
| -------------------------------------- | ------------------------------------------------- |
| What is a neural network? (Chapter 1)  | Neural network 基礎、forward / backward 直覺      |
| Gradient descent (Chapter 2)           | 梯度下降直觀                                      |
| What is backpropagation? (Chapter 3-4) | Backprop 完整推導                                 |
| But what is a GPT? (Chapter 5)         | Transformer / GPT 高層次運作                      |
| Attention in Transformers (Chapter 6)  | Attention 機制的視覺化                            |
| How LLMs might store facts (Chapter 7) | FFN 在 Transformer 中的角色、模型怎麼「記住」事實 |

**為什麼從這裡開始**：影片把抽象的 attention、embedding、residual stream 變成可視覺化的幾何運動。看完這個系列、本模組前 4 章的概念都能 grasp 到直觀層次。

連結：YouTube 上搜尋 `3Blue1Brown Neural Networks`。每集 15 ~ 30 分鐘、總共約 4 小時。

## 階段 2：Andrej Karpathy 的 Neural Networks: Zero to Hero

Andrej Karpathy（OpenAI 前研究員、Tesla 前 AI 主管）的 YouTube 系列、是「動手實作 LLM」的金標準。完整實作從 micrograd（自己刻 autograd）到 GPT-2 訓練。

### 核心集數

| 集數                                                         | 時長   | 涵蓋                                                  |
| ------------------------------------------------------------ | ------ | ----------------------------------------------------- |
| The spelled-out intro to neural networks and backpropagation | 2.5 hr | 從零實作 autograd、理解 backprop                      |
| The spelled-out intro to language modeling                   | 2.5 hr | Bigram model、character-level 預測                    |
| Building makemore: MLP                                       | 1.5 hr | 簡單 MLP 做 character 預測                            |
| Building makemore: Activations & BatchNorm                   | 1 hr   | 訓練深度網路的細節                                    |
| Building makemore: Backprop from scratch                     | 2 hr   | 手刻 backprop 跑通                                    |
| Building makemore: WaveNet                                   | 1 hr   | Hierarchical 結構                                     |
| Let's build GPT from scratch                                 | 2 hr   | **從零實作 GPT、Transformer 完整 forward + backward** |
| Let's build the GPT Tokenizer                                | 2 hr   | BPE tokenizer 詳細實作                                |
| Let's reproduce GPT-2 (124M)                                 | 4 hr   | 完整訓練 pipeline、跑出 GPT-2 級別模型                |
| Let's build LLaMA from scratch                               | 進行中 | Llama 架構、RoPE、SwiGLU 等                           |

### 為什麼這系列重要

- **講者深度高**：Karpathy 把每個概念講清楚、不跳步。
- **完整可執行 code**：每個影片都有 GitHub repo、可跟著跑。
- **從零實作**：不依賴黑箱 framework、所有東西都自己刻、理解深度。
- **涵蓋完整**：autograd → MLP → CNN → Transformer → 完整 GPT-2 訓練。

完成這系列、你能：

- 解釋 Transformer 內部每一行 code 的角色。
- 用 PyTorch 從零實作一個簡單 LLM。
- 看懂主流 LLM 的 architecture code（Llama、Mistral 等）。

連結：YouTube 搜尋 `Karpathy Neural Networks Zero to Hero`。

預估時間：完整跑完 30 ~ 50 小時（含跟著寫 code）、4 ~ 8 週投入。

## 階段 3：Stanford CS224N Natural Language Processing with Deep Learning

Stanford 的 NLP + Deep Learning 旗艦課、由 Chris Manning、Tatsu Hashimoto 等講授。每年更新材料、是 LLM 系統教學的金標準。

### 內容

- Word vectors（word2vec、GloVe）
- RNN、LSTM、GRU
- Attention、Transformer
- BERT、GPT、T5
- 預訓練、fine-tuning、RLHF
- Multimodal、tool use、agent
- 最新 LLM 進展

### 為什麼選這門

- **教材深度**：每堂課有 slides + 推薦 paper、可深入研究。
- **作業扎實**：5 個 programming assignment、從 word2vec 到實作 Transformer。
- **每年更新**：跟最新研究進展對齊。

連結：Stanford CS224N 課程網站。YouTube 上有歷年錄影。

預估時間：跟著影片 + 作業約 80 ~ 120 小時、10 週投入。

## 階段 4：Stanford CS336 Language Modeling from Scratch

2024 年 Stanford 新開的 LLM 從零訓練課。Percy Liang、Tatsu Hashimoto 講授、涵蓋從資料到部署的完整 LLM lifecycle。

### 內容

- 訓練資料：收集、過濾、deduplication
- Tokenizer 訓練
- 模型架構選擇
- 大規模分散式訓練
- 評估方法
- Alignment（SFT、DPO、RLHF）
- Inference 優化
- 部署、安全

### 為什麼這門特別

- **完整 lifecycle**：少數涵蓋「資料 → 訓練 → 評估 → 部署」全鏈的課。
- **業界視角**：講者跟前沿實驗室（Anthropic、Stanford CRFM 等）合作密切。
- **最新內容**：2024 開課、覆蓋最新 LLM 技術。

連結：Stanford CS336 課程網站。YouTube 上有錄影。

預估時間：80 ~ 100 小時、10 週投入。

## 階段 5：Stanford CS25 Transformers United

Stanford 的 Transformer 專題課、每集邀請業界 / 學界專家、涵蓋 Transformer 在不同領域的應用。每年更新、講者更迭。

### 涵蓋領域

- Transformer 各種變體（Vision Transformer、Audio Transformer 等）
- Diffusion + Transformer
- Long context 技術
- Mixture of Experts
- 多模態 LLM
- Agent / Tool use
- 最新研究進展

### 為什麼有價值

- **業界視角**：講者多是 OpenAI、Anthropic、Google DeepMind、Meta 等實驗室的核心研究員。
- **跟前沿同步**：每年內容隨主題更新。
- **適合「想知道現在發生什麼」**：補課堂教學跟不上的最新進展。

連結：YouTube 搜尋 `Stanford CS25 Transformers United`。

預估時間：每集 1 小時、可挑感興趣的看、不一定看完整系列。

## 階段 6：MIT 6.S191 Introduction to Deep Learning

MIT 入門 DL 課、每年寒假開課並錄影上傳。涵蓋 RNN、CNN、Transformer、Diffusion、LLM 等廣度。

- **深度**：較 Stanford CS224N 淺、適合入門。
- **廣度**：覆蓋 DL 所有主要分支、不只 NLP。
- **更新頻率**：每年新版、跟最新進展。

連結：introtodeeplearning.com。

預估時間：每集 1 小時、約 7 ~ 10 集、總時數 10 ~ 15 小時。

## 階段 7：DeepLearning.AI Specializations

Andrew Ng 創辦的 DeepLearning.AI 提供多個 LLM 相關 specialization、Coursera 上有付費 + 免費 audit 選項。

### 推薦課程

| Specialization                             | 涵蓋                                        |
| ------------------------------------------ | ------------------------------------------- |
| Deep Learning Specialization               | DL 基礎、CNN、RNN、Sequence Models          |
| Natural Language Processing Specialization | NLP 從基礎到 Transformer                    |
| Generative AI with Large Language Models   | LLM lifecycle、prompt、fine-tuning、RLHF    |
| 各種 short courses（免費 audit）           | 1 ~ 2 小時的專題、LangChain、RAG、Agents 等 |

**Short courses 特別推薦**：免費 + 短、跟最新工具同步。例：

- `ChatGPT Prompt Engineering for Developers`
- `LangChain for LLM Application Development`
- `Building Systems with the ChatGPT API`
- `Functions, Tools and Agents with LangChain`
- `Fine-tuning LLMs`
- `Pretraining LLMs`

連結：deeplearning.ai 的 short courses 頁面。

## 階段 8：Hugging Face NLP Course

Hugging Face 官方教材、實作取向。涵蓋 Transformers library、tokenizer 訓練、模型 fine-tuning、deployment。

- **連結**：huggingface.co/learn/nlp-course
- **特性**：免費、用 Hugging Face 生態系實作、適合工程師
- **章節**：12 章、約 30 ~ 40 小時

完成這門課、你能用 Transformers library 做：

- 載入跟用任何 Hugging Face 模型
- 自己訓練 tokenizer
- Fine-tune 模型（含 LoRA）
- 部署到 Inference Endpoints

## 必讀 Papers

讀完課程後、跟最新研究進度的方式是讀 paper。以下是 LLM 領域的「必讀經典」、按時間順序：

| Paper                                                   | 重要性                                |
| ------------------------------------------------------- | ------------------------------------- |
| Attention Is All You Need (Vaswani et al., 2017)        | Transformer 原始 paper                |
| BERT (Devlin et al., 2018)                              | Bidirectional pretraining             |
| GPT-2 paper (Radford et al., 2019)                      | Decoder-only 規模化的開端             |
| Scaling Laws (Kaplan et al., 2020)                      | 模型 / 資料 / 算力之間的 scaling 關係 |
| GPT-3 paper (Brown et al., 2020)                        | In-context learning 的湧現            |
| Chinchilla (Hoffmann et al., 2022)                      | 修正 scaling laws、改變訓練配比       |
| InstructGPT (Ouyang et al., 2022)                       | RLHF 的標誌性實作                     |
| LLaMA (Touvron et al., 2023)                            | Open-weight 大模型的標竿              |
| LLaMA 2 (Touvron et al., 2023)                          | Open chat model                       |
| DPO (Rafailov et al., 2023)                             | RLHF 的簡化替代                       |
| Mixture of Experts (Shazeer et al., 2017、Mixtral 2024) | MoE 路線                              |
| RoPE (Su et al., 2021)                                  | 現代 LLM 主流位置編碼                 |
| Flash Attention (Dao et al., 2022)                      | Attention 高效實作                    |

訂閱 arXiv `cs.CL`、`cs.LG` daily list、或關注 Hugging Face Daily Papers、X / Twitter 上的 ML researcher、能持續跟最新進展。

## 書籍補充

| 書名                                                           | 涵蓋                               | 免費       |
| -------------------------------------------------------------- | ---------------------------------- | ---------- |
| Speech and Language Processing by Jurafsky & Martin            | NLP 完整教科書、第 3 版含 LLM      | 是         |
| Build a Large Language Model From Scratch by Sebastian Raschka | 從零實作 GPT-style LLM             | 否（紙本） |
| Hands-On Large Language Models by Jay Alammar                  | 視覺化 + 實作                      | 否         |
| The Illustrated Transformer by Jay Alammar                     | 部落格文章、視覺化解釋 Transformer | 是         |

Jay Alammar 的 `The Illustrated Transformer`、`The Illustrated GPT-2` 等部落格文章、是視覺化解釋的經典。免費、google 直接搜尋。

## 建議的時間投入

| 目標                         | 預估時間（投入 5 ~ 10 小時 / 週） |
| ---------------------------- | --------------------------------- |
| 看完 3Blue1Brown GPT 系列    | 1 ~ 2 週                          |
| 完成 Karpathy zero-to-hero   | 4 ~ 8 週                          |
| 完成 Stanford CS224N         | 10 週                             |
| 完成 Stanford CS336          | 10 週                             |
| 完成 Hugging Face NLP Course | 4 ~ 6 週                          |
| 讀完上面 12 篇必讀 paper     | 4 ~ 8 週                          |

寫 code 場景的使用者通常用「3Blue1Brown + Karpathy zero-to-hero + 跟最新 paper」這個組合就能跟 LLM 進展接軌、約 6 ~ 12 週投入。想做研究 / 自己訓練模型、再進入 Stanford CS336、CS224N、必讀 paper 等正式學習路徑。

## 建議的學習順序

對「想理解 LLM 內部、不打算自己訓練」的工程師：

1. 看 3Blue1Brown GPT 系列（1 ~ 2 週）
2. 看 Karpathy `Let's build GPT from scratch`（1 週）
3. 看 Karpathy `Let's reproduce GPT-2`（2 週）
4. 看 Stanford CS25 感興趣的集數（自由）

對「想做 LLM 應用開發」的工程師：

1. 同上
2. + DeepLearning.AI short courses（LangChain、RAG、Agents、Prompt Engineering）
3. + Hugging Face NLP Course

對「想做 LLM 訓練 / fine-tuning」的研究者：

1. 同上
2. + Karpathy 完整 zero-to-hero 系列
3. + Stanford CS224N（系統補課）
4. + Stanford CS336（完整 lifecycle）
5. + 必讀 paper

## 小結

LLM 理論深入學習的路線清楚：3Blue1Brown 視覺化 → Karpathy 動手實作 → Stanford CS224N / CS336 系統打底 → Stanford CS25 跟最新進展。寫 code 場景使用者用 6 ~ 12 週投入就能跟業界接軌；想做研究投入更多時間進入正式課程。書籍跟必讀 paper 提供補充資源。

讀到這裡、本系列指南就完整收尾。你應該能：

- 在 Mac 上跑本地 LLM 寫 code（模組零 + 模組一）
- 判讀任何 LLM 相關資訊（模組零 0.6 五個框架）
- 理解 LLM 推論的數學基礎（模組二）
- 理解 LLM 內部運作機制（模組三）
- 知道想再深入該往哪走（本章 + [模組二 2.4](/llm/02-math-foundations/going-deeper-math/)）

回到 [LLM 寫 code 實務指南首頁](/llm/) 看完整地圖。
