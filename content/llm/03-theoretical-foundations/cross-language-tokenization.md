---
title: "3.7 跨語言場景的 tokenizer 與訓練分佈原理"
date: 2026-05-11
description: "為什麼模型對不同語言表現不一致：tokenizer + 訓練資料分佈雙因素、語言選擇取捨"
tags: ["llm", "theory", "tokenization", "multilingual"]
weight: 7
---

模組三 [3.6 tokenization 章節](/llm/03-theoretical-foundations/tokenization-algorithms/) 提到 Llama 2 對中文支援差、Gemma 4 改善很多——但「為什麼」展開後不只 tokenizer 一層、還涉及訓練資料分佈、模型容量分配、跨語言 reasoning 行為差異。本章把跨語言場景的根本原理走過、讓「該用什麼語言寫 prompt」「commit message 用中文還是英文」這類取捨從直覺變成可推導判斷。

本章寫的是「跨語言能力為什麼這樣分佈」「該如何依場景選語言」的原理層。具體模型在 2026/5 的中文 / 多語言 benchmark 不在本章——這些隨新模型版本變、用本章的雙因素 framework 重新評估就好。

## 本章目標

讀完本章後、你應該能：

1. 解釋為什麼模型在不同語言上表現不一致、有哪兩個獨立因素。
2. 看到 tokenizer 對中文「一字切 N token」時、知道對 context cost 跟能力的影響。
3. 判讀「該翻英寫 prompt 還是維持中文」的取捨。
4. 解釋為什麼跨語言 reasoning 比 monolingual reasoning 容易失敗。

## 為什麼模型對不同語言表現不一致：雙因素

模型對不同語言的表現受兩個獨立因素疊加影響：

### 因素 1：Tokenizer Vocab Coverage

Tokenizer 把文字切成 [token](/llm/knowledge-cards/token/)、不同 tokenizer 對不同語言的切割密度不同：

- 英文中心的 tokenizer（如 Llama 2 的 32K vocab）對中文一字常切 2-3 個 token、context 利用率差。
- 多語言 tokenizer（如 Gemma 4 的 256K vocab）對中文多半一字一 token、跟英文接近。

Tokenizer 影響三件事：

- **Context 成本**：同樣 prompt 在不同 tokenizer 上吃 token 量級不同、API 費用、[context window](/llm/knowledge-cards/context-window/) 利用率都跟著差。
- **Token 粒度**：粗粒度 tokenizer 對某語言的「字」切割不細、影響模型對該語言細微差異的辨識。
- **訓練效率**：tokenizer 切得好、模型每個 token 學到更多語意、訓練收斂快。

### 因素 2：訓練資料分佈

模型預訓練資料的語言佔比決定模型「學了多少」這個語言：

- Common Crawl 等主流預訓練資料英文佔 70%+、中文約 1-3%、其他語言更少。
- 即使 tokenizer 對某語言支援好、訓練資料少仍會限制模型在該語言上的能力。

訓練分佈影響三件事：

- **事實準確度**：訓練資料少 → 該語言的事實覆蓋低 → hallucination 多。
- **Reasoning 深度**：複雜推理需要大量該語言範例支撐、訓練少就退化。
- **風格自然度**：訓練少的語言、模型輸出可能語法 OK 但「不像母語人說的」。

### 雙因素的獨立性

兩個因素獨立、各自影響不同維度：

| Tokenizer 好 | 訓練資料多 | 結果                                                    |
| ------------ | ---------- | ------------------------------------------------------- |
| 是           | 是         | 跨語言能力接近 native（Gemma 4 / Qwen3 在中文上的狀態） |
| 是           | 否         | 「會讀」但「不熟」、輸出語法 OK 但內容平庸              |
| 否           | 是         | 能力 OK 但 cost 高、context 利用率差                    |
| 否           | 否         | 該語言基本不可用（Llama 2 對中文的狀態）                |

判讀模型某語言能力時、兩個因素都要評估、單看一個會誤判。「Gemma 4 vocab 對中文好」不代表「中文表現一定好」、還要看訓練資料佔比。「OpenAI 訓練資料量大」不代表「對所有語言都好」、還要看 tokenizer 設計。

## Tokenizer Vocab 對非英文的影響

具體看 tokenizer 對中文的影響、用實際數字比較：

| Tokenizer      | Vocab   | 中文「敏捷的棕色狐狸跳過懶狗」估算 token 數 |
| -------------- | ------- | ------------------------------------------- |
| Llama 2 BPE    | 32K     | 約 20（byte 級切割、一字常 2-3 個 token）   |
| GPT-4 tiktoken | ~100K   | 約 12                                       |
| Llama 3 BPE    | 128,256 | 約 10                                       |
| Qwen3 BPE      | 152,064 | 約 10                                       |
| Gemma 3        | 262,144 | 約 9                                        |
| Gemma 4        | 256,000 | 約 9                                        |

數字差異看似不大、累積起來影響顯著：

- **128K context 的「實際容量」**：Llama 2 對中文約 6K 中文字、Gemma 4 對中文約 14K 中文字。差兩倍以上。
- **API 費用**：同樣中文 prompt、Llama 2 費用是 Gemma 4 的兩倍以上（按 token 收費的話）。
- **長 prompt 的 [prefill](/llm/knowledge-cards/prefill/) 時間**：token 多 prefill 慢、[TTFT](/llm/knowledge-cards/ttft/) 受影響。

但這只是其中一個因素。Tokenizer 改進不會自動讓模型「懂」這個語言——還要訓練資料配合。Llama 3 vocab 比 Llama 2 大很多、但對中文表現的提升不只是 vocab 帶來的、也是訓練資料多語言比例提升的結果。

## 訓練資料分佈：語言佔比決定能力

Web 文字的語言分佈嚴重不平衡。Common Crawl 跟同類資料源的語言佔比約：

- 英文：60-70%
- 中文：2-5%
- 西班牙文、葡萄牙文、日文、法文、德文：各 1-3%
- 其他幾百種語言：合計 < 10%

模型預訓練多半反映這個分佈。即使「主打多語言」的模型、英文仍是主導。

實務影響：

- **事實準確度**：問模型「台灣某縣市的人口」這類本地化問題、中文回答的準確度通常低於英文回答同個問題（即使翻譯為相同 query）。
- **Reasoning 深度**：複雜中文推理（如解中文奧數題）、模型可能「翻譯成英文 reasoning、再翻回中文」、中間步驟跳過、答案合理但推理鏈不通。
- **風格 / 慣用語**：中文輸出可能語法 OK、但詞彙選擇偏「翻譯腔」、不像母語自然書寫。
- **長尾事實**：訓練資料少的語言、長尾事實更容易 hallucinate。

判讀模型在某語言上的能力強弱、看訓練資料佔比是主要訊號。Qwen 系列訓練資料大量中文、中文能力強；Llama 系列訓練資料英文為主、即使最新版中文表現仍弱於 Qwen 在中文上的表現。

## 兩因素的獨立性對實務的影響

雙因素獨立、實際模型多半落在某個組合狀態：

**Gemma 4 / Qwen3 / Llama 3 主流開源旗艦**：

- Tokenizer：多語言、vocab 256K 級、中文 token 效率接近英文。
- 訓練資料：中英都有大量比例、Qwen 中文比例高、Llama 英文比例高。
- 結果：中文能力接近 native level、跨語言能力差距縮小。

**OpenAI / Anthropic 雲端旗艦**：

- Tokenizer：tiktoken 等、中文 token 效率中等。
- 訓練資料：規模極大、所有語言絕對量都多（即使相對佔比低）。
- 結果：中英都強、絕對能力受訓練規模支撐。

**早期 Llama 2 / 純英文模型**：

- Tokenizer：32K 英文中心、中文切散。
- 訓練資料：英文主導、其他語言極少。
- 結果：中文勉強可讀、無法用於正式工作。

判讀新模型對某語言能力時、先看這兩個因素、再參考實測——比直接看 benchmark 數字準。

## 中文 Prompt 何時該翻英：機會成本判讀

寫 code 場景常見問題「該用中文還是英文寫 prompt」、答案取決於三個變數：

### 變數 1：模型在中英的能力差距

主流開源旗艦（Gemma 4 / Qwen3 / Llama 3）中英差距已縮小、寫 code 場景中英 prompt 表現接近。早期 / 較小模型差距大、英文 prompt 較穩。

判讀：用較強模型可以維持中文、用較弱模型考慮翻英。

### 變數 2：翻譯成本

翻譯成本包括：時間、認知負擔、可能的精度損失。

- 簡短 prompt（補完、寫單個 function）：翻英成本低、可考慮。
- 長 prompt（描述複雜需求、多個檔案 context）：翻英成本高、維持中文較划算。
- 含技術術語的 prompt：英文是 LLM 訓練的主流、術語維持英文較好（即使句子是中文也保留英文 keyword）。

### 變數 3：輸出語言要求

- 要中文回答（如寫中文 docs、跟中文團隊溝通）：維持中文 prompt 一致性較好。
- 要英文回答（如 commit message、open source PR）：英文 prompt 自然引導英文輸出、不需 explicit instruct。

### 綜合判讀

寫 code 場景的多數情境（主流模型 + 短 prompt + 維持原語言輸出）：直接用中文寫即可、不必特別翻英。例外：

- 用較弱模型（< 14B）、英文較穩。
- 特殊領域（法律、醫療、學術）、英文資料豐富、翻英可能更穩。
- Domain-specific reasoning（數學、邏輯）、英文訓練資料多、翻英可能改善 reasoning 鏈。

「直覺說該翻英」常是過度小心、實測通常發現中文跟英文 prompt 表現接近、翻譯成本浪費。

## Commit / Docstring / 註解的語言選擇取捨

寫 code 場景的「該用什麼語言」決策多半取決於非模型因素：

### Commit Message

- **團隊一致性**：團隊都用英文就英文、都用中文就中文。
- **長期保留**：commit message 進 git 歷史、長期保留、跨團隊成員 / 外部貢獻者讀。
- **可讀性受眾**：團隊有非中文 reader 就英文、純中文團隊用中文也 OK。
- **隱私 / 合規**：commit 進 git、可能進 public repo、敏感資訊不該寫進去（不論語言）。

模型對中英 commit message 都能寫、選擇主要看團隊跟 repo 屬性、不是看模型偏好。

### Docstring

- **語言生態慣例**：Python / JavaScript 開源社群慣例是英文 docstring；JetBrains / 微軟在地化文件多中文。
- **API consumer**：API 給誰用、用什麼語言。
- **自動化工具**：docs generator、type checker、IDE hint 對英文 docstring 支援較成熟。

### 程式內註解

- **團隊母語 vs 國際慣例**：團隊母語寫註解最自然、國際慣例（特別 open source）多英文。
- **複雜邏輯**：用最能精確表達的語言寫、不一定要英文。
- **TODO / FIXME**：跟團隊慣例一致。

這些決策本質上是團隊跟生態問題、不是 LLM 問題。LLM 對中英都能 handle、選哪個取決於 downstream 讀者。

## 跨語言 Reasoning 的失敗訊號

跨語言 reasoning（如中文 prompt 要求模型用中文推理過數學題、或用中文回答需要英文事實 retrieval 的問題）容易出現幾種失敗：

### 內部翻譯失敗

模型「中文 prompt → 內部翻譯成英文 reasoning → 翻回中文輸出」、中間步驟跳過、中文輸出看起來合理但推理鏈不通。

判讀訊號：要求模型「請用中文逐步推理」、模型輸出推理鏈不連貫、步驟跳躍。

緩解：強制 step-by-step prompt、或乾脆翻英 prompt 拿英文輸出、再人工譯回中文。

### 訓練語言切換

模型在某語言上 reasoning 訓練不足、即使理解 query、輸出推理深度受限。

判讀訊號：中文 query 拿到淺薄答案、同樣 query 翻英拿到深入答案。

緩解：複雜推理任務用英文 prompt + 英文輸出、最後再翻譯。

### Tokenizer 引發的細節遺失

中文一字切多個 token 時、模型可能在 token 邊界誤判語意、輸出細節不準。

判讀訊號：細節錯（如把「2024 年」誤讀成「2024 月」）、英文同義問題不會錯。

緩解：對細節敏感的任務（數字、日期、人名）強調確認、或翻英降低 tokenizer 誤判機率。

## Code 跟自然語言的不對稱

Code 本身是「英文偏向」的：keyword（`if`、`for`、`return`）、變數名（多半 ASCII）、API（多半英文）。LLM 對 code 的能力跨語言差距較小——code 本身就跨語言、模型不需要「翻譯」code。

但「code + 自然語言」的混合場景仍受自然語言訓練分佈影響：

- 寫 code + 中文 docstring：模型寫 code 表現一致、寫 docstring 受訓練分佈影響。
- 解釋 code 給人聽：用哪種語言解釋、受該語言訓練分佈影響。
- 改寫 code 註解：改 code 行為一致、改自然語言部分受訓練分佈影響。

判讀「該不該翻英」時、要區分「code 部分」跟「自然語言部分」。Code 部分中英差距小、自然語言部分中英差距視模型而定。

## 何時過時 / 何時不過時

**不會過時的部分**：

- Tokenizer + 訓練分佈雙因素 framing。
- 跨語言能力受結構性限制的本質（不只是「模型不夠強」）。
- 三個變數判讀（能力差距、翻譯成本、輸出語言要求）。
- 跨語言 reasoning 失敗模式的分類。
- Code 跟自然語言的不對稱觀察。

**會變的部分**：

- 具體模型在特定語言上的當下能力（會隨新模型版本變、Gemma 5 / Qwen4 等出來會再變）。
- 各 tokenizer 的 vocab 大小（會調整）。
- 訓練資料的多語言比例（業界正在改善）。
- 哪些模型「中文能力好」的具體 ranking。

看到新模型時、回到雙因素 framework 評估：tokenizer vocab 多大、中文 token 效率如何、訓練資料中文佔比、實測中文表現是否符合預期——這個 framework 不變、評估結果會隨模型版本更新。

## 小結

模型對不同語言表現不一致、根因是 tokenizer vocab coverage 跟訓練資料分佈兩個獨立因素疊加。Gemma 4 / Qwen3 等主流開源旗艦在中文上接近 native level、是兩因素都改善的結果。實務上「該用什麼語言寫 prompt」取決於模型能力差距、翻譯成本、輸出語言要求——多數寫 code 場景維持中文即可。跨語言 reasoning 失敗有自己的訊號跟緩解策略。Code 部分跟自然語言部分受訓練分佈影響不對稱、判讀時要區分。

下一章：[3.8 想學更深：推薦公開課程](/llm/03-theoretical-foundations/going-deeper-theory/)。
