---
title: "2.4 想學更深：推薦公開課程"
date: 2026-05-11
description: "MIT、Stanford、Harvard 等公開課程：數學基礎跟 LLM 預備知識的完整學習路線"
tags: ["llm", "math", "courses"]
weight: 4
---

本模組前三章把 LLM 推論需要的數學概念走過一遍、給定義跟用途、保留實務脈絡。想看完整推導、跟練習題、跟系統教學、公開課程是更有效率的路徑。本章整理「為 LLM 打數學基礎」這條學習路線上的高品質公開課與書籍、並標出每門課的定位、適合的讀者、跟前置依賴。

選課的原則：先從跟 LLM 連結最緊密的開始、由近至遠。3Blue1Brown 的視覺化系列適合入門複習、MIT / Stanford 的正式課程適合認真打底、Karpathy 的 YouTube 系列適合「想直接看 LLM 怎麼從零實作」（需要階段 1 ~ 3 的數學基礎才能順暢跟上、所以排在路線後段）。

## 路線總覽

| 階段 | 內容           | 前置依賴                 | 適合誰                     |
| ---- | -------------- | ------------------------ | -------------------------- |
| 1    | 視覺化複習     | 任何工程背景             | 入門 / 概念複習            |
| 2    | 線性代數正式課 | 高中代數                 | 想紮實打底                 |
| 3    | 機率論 + 統計  | 大學一年級數學           | 想懂機率論完整體系         |
| 4    | 資訊論         | 機率論 + 微積分          | 想懂 entropy / KL 數學起源 |
| 5    | 最佳化         | 多變數微積分 + 線代      | 想懂 SGD / Adam 數學起源   |
| 6    | 深度學習 + LLM | 階段 2 + 3 的線代 / 機率 | 想做研究 / 自己訓練        |
| 7    | 從零實作 LLM   | 階段 6 或 Python ML 經驗 | 想直接接觸完整系統實作     |

## 階段 1：3Blue1Brown 的視覺化系列（YouTube 免費）

Grant Sanderson 的 3Blue1Brown 頻道是入門 / 複習數學概念最有效率的選擇。動畫品質高、講解直觀、每集 15 ~ 30 分鐘。

| 系列                               | 涵蓋內容                                          | 直接相關章節                                                                                                                   |
| ---------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Essence of Linear Algebra（15 集） | 向量、矩陣、線性變換、特徵值、向量空間            | [2.0](/llm/02-math-foundations/linear-algebra-for-llm/)                                                                        |
| Essence of Calculus（12 集）       | 導數、積分、chain rule、Taylor series             | [2.2](/llm/02-math-foundations/calculus-and-optimization/)                                                                     |
| Neural Networks（4 集）            | 神經網路怎麼學、backpropagation、gradient descent | [2.2](/llm/02-math-foundations/calculus-and-optimization/) + [3.0](/llm/03-theoretical-foundations/neural-network-basics/)     |
| But what is a GPT?（多集系列）     | Transformer 內部、attention、embedding 視覺化     | [3.2](/llm/03-theoretical-foundations/attention-mechanism/) + [3.3](/llm/03-theoretical-foundations/transformer-architecture/) |

**為什麼從這裡開始**：3Blue1Brown 的影片不依賴背景知識、用視覺直觀傳達核心概念、適合在進入正式課之前對齊直覺。看完 Essence of Linear Algebra 跟 Neural Networks 兩個系列、本模組大部分概念都能 grasp 到直覺層。

## 階段 2：線性代數正式課

### MIT 18.06 Linear Algebra by Gilbert Strang（OCW 免費）

教授 Gilbert Strang 的線性代數課是公開課的金標準、涵蓋向量空間、特徵值、SVD、最小平方等完整內容。課程網站包含影片、講義、作業、教科書。

- **教科書**：Introduction to Linear Algebra by Gilbert Strang（也有 PDF 可下載）
- **課程連結**：ocw.mit.edu 站內搜尋 18.06 或 18.06SC
- **時長**：18 ~ 35 講、每講 50 分鐘、約 30 小時
- **適合**：認真打底、想做完整作業
- **跟本模組關係**：完整補完 [2.0](/llm/02-math-foundations/linear-algebra-for-llm/) 的數學深度

### MIT 18.06SC Linear Algebra（Self-Paced 版本）

同樣 Gilbert Strang、但設計成自學版本、有 problem sessions 補講解。建議自學選擇這版而非原始 18.06。

## 階段 3：機率論 + 統計

### Harvard Stat 110 Probability by Joe Blitzstein（YouTube 免費）

Harvard 教授 Joe Blitzstein 的機率論課、是 LLM 機率基礎最完整的公開課。涵蓋條件機率、貝氏定理、各種分佈、generating function、Markov chain 等。

- **課程連結**：projects.iq.harvard.edu/stat110（YouTube 有對應錄影）
- **教科書**：Introduction to Probability by Blitzstein & Hwang
- **時長**：35 講、每講 50 分鐘、約 30 小時
- **適合**：想懂機率論完整體系
- **跟本模組關係**：補完 [2.1](/llm/02-math-foundations/probability-and-information/) 的數學深度

### MIT 6.041 Probabilistic Systems Analysis（OCW 免費）

工程取向、比 Stat 110 更貼近應用。涵蓋 Bayes、Markov、隨機過程等。適合工程師背景的讀者。

### Stanford CS109 Probability for Computer Scientists

Stanford 的 CS 系開設、機率論 + 程式應用、適合想直接看「機率在 ML 中怎麼用」的讀者。課程材料在 Stanford CS109 網站。

## 階段 4：資訊論

### MIT 6.050J Information and Entropy（OCW 免費）

涵蓋 entropy、cross-entropy、KL divergence、Shannon coding theorem、channel capacity 等資訊論完整基礎。

- **教科書**：Information Theory, Inference, and Learning Algorithms by David MacKay（也免費 PDF）
- **適合**：想懂 [2.1](/llm/02-math-foundations/probability-and-information/) 中 entropy / KL 的數學起源
- **跟 LLM 的連結**：cross-entropy 為什麼是訓練 LLM 的標準 loss、perplexity 的資訊論意義

### Stanford EE376A Information Theory

Stanford 的 EE 系開設、跟通訊工程結合、適合 EE 背景讀者。

## 階段 5：最佳化

### Stanford EE364A Convex Optimization by Stephen Boyd（YouTube + 教科書免費）

凸最佳化的金標準課程。涵蓋 gradient descent、Lagrangian、duality、KKT 條件等。雖然 LLM 訓練是非凸最佳化、但凸最佳化的觀念是基礎。

- **教科書**：Convex Optimization by Boyd & Vandenberghe（線上 PDF 免費）
- **適合**：想懂 SGD、Adam、Lagrangian 等最佳化技術的數學起源
- **跟本模組關係**：補完 [2.2](/llm/02-math-foundations/calculus-and-optimization/) 的最佳化理論深度

## 階段 6：深度學習與 LLM

### MIT 6.S191 Introduction to Deep Learning（每年更新、YouTube 免費）

MIT 的入門 deep learning 課、每年寒假開課並錄影上傳、涵蓋 RNN、Transformer、Diffusion、LLM。

- **課程連結**：introtodeeplearning.com
- **時長**：每集 1 小時、約 7 ~ 10 集
- **適合**：deep learning 全面 overview、跟最新主題對齊

### Stanford CS229 Machine Learning by Andrew Ng（Stanford Online + YouTube）

ML 基礎金標準、涵蓋 linear regression、logistic regression、SVM、CNN、強化學習等。雖然較舊（沒有最新 Transformer）、但基礎扎實。CS229 的免費影片版在 Stanford Online 跟 YouTube（cs229.stanford.edu 有講義跟舊版錄影連結）；OCW 沒有 CS229 官方版本。

- **新版**：Coursera 上有付費版「Machine Learning Specialization」、更新且互動性強
- **適合**：想完整懂 ML 數學基礎

### Stanford CS224N Natural Language Processing with Deep Learning

NLP + Transformer 的標杆課程。涵蓋 word embedding、RNN、attention、Transformer、BERT、GPT 等。每年更新材料。

- **適合**：[3.2 attention 機制](/llm/03-theoretical-foundations/attention-mechanism/) 與 [3.3 Transformer 架構](/llm/03-theoretical-foundations/transformer-architecture/) 的最佳補完
- **連結**：Stanford CS224N 課程網站、YouTube 有錄影

### Stanford CS25 Transformers United

Stanford 的 Transformer 專題課、每集邀請業界與學界專家、涵蓋 Transformer 在不同領域的應用與進展。

- **適合**：想跟最新 Transformer 研究進度
- **連結**：YouTube 上搜尋「Stanford CS25」

### Stanford CS336 Language Modeling from Scratch（2024 新開、後續每年更新）

Stanford 新開的 LLM 從零訓練課程、涵蓋資料、tokenization、模型架構、訓練、評估、部署整條鏈。課程材料逐年更新、引用時請註明你看的是哪一年的版本（2026 年後內容可能跟本章引用時有差異）。

- **適合**：想懂 LLM 完整 lifecycle
- **連結**：Stanford CS336 課程網站

## 階段 7：直接動手實作

### Andrej Karpathy 的 Neural Networks: Zero to Hero（YouTube 免費）

OpenAI 前研究員 Andrej Karpathy 的系列影片、從手刻 micrograd 到實作 GPT-2、是「想動手懂 LLM」的最佳路徑。每集 1 ~ 4 小時、邊講邊寫 code。

- **核心集數**：
  - Micrograd（自己刻 autograd）
  - Makemore 系列（從 bigram 到 Transformer）
  - Let's build GPT（從零實作 GPT-2）
  - Let's reproduce GPT-2（更完整的訓練 pipeline）
  - Let's build the GPT Tokenizer（BPE 詳細實作）
- **適合**：完成階段 1-3、想直接接觸完整系統實作
- **連結**：YouTube 搜尋「Karpathy zero to hero」

### Hugging Face NLP Course

Hugging Face 官方教材、涵蓋 Transformers library、tokenizer、訓練、推論、deployment。實作取向、適合工程師。

- **連結**：huggingface.co/learn

## 書籍補充

| 書名                                                             | 涵蓋                                        | 免費 PDF |
| ---------------------------------------------------------------- | ------------------------------------------- | -------- |
| Mathematics for Machine Learning by Deisenroth et al.            | 線性代數、機率、最佳化、PCA、SVM            | 是       |
| Deep Learning by Goodfellow, Bengio, Courville                   | DL 全面教科書、ML 基礎到 Transformer 出現前 | 是       |
| Information Theory, Inference, and Learning Algorithms by MacKay | 機率 + 資訊論 + ML 整合                     | 是       |
| Convex Optimization by Boyd & Vandenberghe                       | 最佳化理論金標準                            | 是       |
| The Elements of Statistical Learning by Hastie et al.            | 統計學習方法                                | 是       |

這幾本書的官方免費 PDF 來源（避免落到盜版站）：

- Mathematics for Machine Learning：mml-book.github.io
- Deep Learning（Goodfellow）：deeplearningbook.org
- Information Theory, Inference, and Learning Algorithms：inference.org.uk/mackay/itila/
- Convex Optimization（Boyd）：stanford.edu/~boyd/cvxbook/
- The Elements of Statistical Learning：hastie.su.domains/ElemStatLearn/

## 何時不適用本路線

本路線假設「想紮實打底數學跟 LLM 內部、之後做研究或寫 LLM-related code」。以下情境的路線需求不同：

| 情境                                  | 該怎麼安排                                                                 |
| ------------------------------------- | -------------------------------------------------------------------------- |
| 直接做 LLM application（RAG / agent） | 階段 1（3B1B）即可、不需要 MIT 18.06 完整 30 小時；應用層 paper 看得懂就夠 |
| 已具備 ML 背景（修過 CS229 / 同等）   | 跳過階段 1 ~ 5、直接進階段 6 ~ 7                                           |
| 純使用本地 LLM、不寫 ML code          | 模組零 + 模組一已足夠、本路線可全跳過                                      |
| 想 fine-tune 模型                     | 階段 1（複習）+ 階段 6 ~ 7 為主、最佳化 / 資訊論可後補                     |
| 想懂 paper 但不打算實作               | 階段 1（3B1B）+ Karpathy zero-to-hero 前兩集已足夠                         |
| 學術研究 / 想自己 propose 架構        | 全路線 + Stanford CS336 / CS25 持續追蹤新論文                              |

## 建議的時間投入

| 目標                                 | 預估時間（投入 5 ~ 10 小時 / 週） |
| ------------------------------------ | --------------------------------- |
| 看完 3Blue1Brown 三個系列            | 2 ~ 4 週                          |
| 完成 MIT 18.06 線性代數              | 8 ~ 12 週                         |
| 完成 Stat 110 機率                   | 8 ~ 12 週                         |
| 完成 Karpathy zero-to-hero           | 4 ~ 8 週                          |
| 完成 Stanford CS224N                 | 10 週                             |
| 完成 Stanford CS336 LLM from scratch | 10 週                             |

**機會成本提醒**：本系列文章在「Mac 上跑本地 LLM 寫 code」場景中、不需要完整跑完上述課程。3Blue1Brown 三系列 + Karpathy zero-to-hero 已經涵蓋「能讀懂 LLM paper、能看懂模型架構討論」的程度、約 6 ~ 10 週投入。想做研究或自己訓練模型、再進入 MIT / Stanford 正式課程。

## 小結

數學基礎跟 LLM 預備知識的學習路線、從視覺化複習（3Blue1Brown）開始、進入正式課程（MIT 18.06、Stat 110、Stanford CS224N）、最後動手實作（Karpathy）。寫 code 場景使用者用 6 ~ 10 週投入 3Blue1Brown + Karpathy 系列、就能跟 LLM 進展接軌；想深入研究、再進入 Stanford CS336 等專業課程。

下一個模組：[模組三 LLM 的理論基礎](/llm/03-theoretical-foundations/)、把本模組的數學工具拼成完整的 LLM 運作機制。
