---
title: "0.0 本地 vs 雲端 LLM"
date: 2026-05-11
description: "從隱私、成本、速度、能力四個維度建立本地與雲端 LLM 的基本對照"
tags: ["llm", "foundations", "comparison"]
weight: 0
---

[本地 LLM 與雲端 LLM](/llm/knowledge-cards/local-vs-cloud/) 的核心差異是「模型權重在哪台機器上跑、誰能看到對話內容」。把模型權重載到自己 Mac 的記憶體裡、用本機算力跑[推論](/llm/knowledge-cards/inference-server/)，就是本地；把 prompt 透過 HTTPS 送到 Anthropic、OpenAI、Google 的伺服器，再把結果回傳，就是雲端。

這個差異一拆，後續所有取捨都會自然展開：隱私、成本、速度、能力四個維度在本地與雲端的權衡方向都不一樣。本章的責任是把這四個維度先攤開，後續章節再分別處理「速度為何慢」「記憶體為何決定能力」等具體問題。

## 本章目標

讀完本章後，你應該能回答：

1. 哪些情境下花時間在本地跑 LLM 比直接用雲端旗艦划算？
2. 本地 LLM 的「免費」實際成本怎麼算？
3. 本地 LLM 的速度跟雲端比、在不同任務上的差距如何？
4. 本地 LLM 在哪些任務上能跟 Claude / GPT-5 並肩、哪些任務改用雲端更划算？

## 四個維度的差異

| 維度 | 本地 LLM                                                                                           | 雲端 LLM                                                                      |
| ---- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| 隱私 | prompt、code、檔案完全不離開本機                                                                   | 內容會送到第三方伺服器，受其資料保留與訓練政策約束                            |
| 成本 | 一次性硬體投資（Mac 的記憶體），無 API 費用                                                        | 按 token 計費，重度使用每月可達數百美元                                       |
| 速度 | 受本機算力與記憶體頻寬限制，首字延遲與生字速度都低於雲端旗艦模型                                   | 旗艦模型在資料中心級 GPU（NVIDIA H100 等）或 TPU 上跑，首字延遲低、生字速度快 |
| 能力 | 受模型大小與量化等級限制，2026 年 5 月可在 Mac 上跑的最強模型約等於 GPT-4 mini / Claude Haiku 等級 | Claude Sonnet 4.6、Opus 4.7、GPT-5 等旗艦模型，能力斷崖式領先                 |

這張表是後續所有章節的判讀基底。下面四個小節分別把每一格展開到「實際使用情境下會怎麼影響決策」。

## 隱私維度：prompt 出境邊界

本地 LLM 在隱私維度的核心承諾是 prompt 內容不離開本機。對寫 code 來說這影響的是兩件事：手上的 code 會不會進入訓練資料、客戶 NDA 或公司資安政策能否接受 code 出境。

接近真實的情境：

- 接受 NDA 的外包專案，客戶明示不得把 code 上傳第三方 AI 服務。
- 公司內部 monorepo 包含未公開的商業邏輯，資安政策禁止流向 OpenAI 或 Anthropic。
- 個人 side project 沒有合規壓力，但仍想避免將 prompt 變成廣告或推薦演算法的訓練資料。

陷阱是把「本地 = 絕對私密」當成自動成立的事實。本地 LLM 的隱私保證僅在於 prompt 不離開機器；若同時開啟雲端同步、把對話紀錄存到 Notion、或用 IDE 的雲端 plugin 同時送 prompt 給其他服務，隱私邊界仍會被穿透。隱私是一條鏈，本地推論伺服器只是其中一環。

雲端旗艦模型如 Claude 與 GPT 都提供 zero-retention 與不訓練選項（企業方案、API 預設等），合規上多數場景仍能滿足。隱私是訴求，不是非選本地不可的唯一理由。

## 成本維度：一次性投資 vs 按 token 計費

本地 LLM 的成本特性是「先付硬體錢，後續推論免費」。雲端 LLM 反過來：硬體完全不用管，但每個 prompt 都按 token 收費。

接近真實的情境：

- 一台 32GB Mac mini M4 約 NT$45,000，能持續跑 Gemma 4 31B 等中型模型。如果原本每月雲端 API 花費超過 NT$3,000，硬體成本約 15 個月攤平。
- 偶爾使用者（每月 API 花費 NT$200 以下）若為了「省錢」買新 Mac，是負投資；只有重度使用者才會真正攤平。
- 用 Claude Code 寫 code 的工程師，月費約 USD 200，一年 USD 2,400；硬體攤平的數學就要重算，特別是考慮到雲端能力斷崖式領先時，省下的時間成本通常超過 API 費用。

陷阱是把硬體成本當成沉沒成本、把雲端按月看成「持續流血」。實際上 Mac 本來就要買，邊際成本是「為了跑 LLM 多買 16GB 記憶體」這一段，這個邊際成本通常只有 NT$5,000 ~ 10,000，比看起來低很多。但這個邊際成本買到的是「不太強的模型」，能力差距見下一節。

電費跟風扇噪音是被忽略的隱性成本。32GB Mac 跑大型模型時持續滿載，風扇可能整天轉、機殼會熱；fanless 機種（Air）會降頻，速度進一步下降。

## 速度維度：首字延遲與生字速度

本地 LLM 的速度有兩個獨立指標：**[首字延遲](/llm/knowledge-cards/ttft/)**（Time To First Token, TTFT，從送出 prompt 到第一個 token 出現）跟**[生字速度](/llm/knowledge-cards/tokens-per-second/)**（tokens per second, tok/s，後續每秒能吐幾個字）。雲端跟本地在這兩個指標上的差距很不對稱。

接近真實的數字（2026 年 5 月、僅供量級參考、不是 benchmark）：

| 模型 / 硬體                                                | TTFT       | 生字速度（tok/s） |
| ---------------------------------------------------------- | ---------- | ----------------- |
| Claude Sonnet 4.6 雲端                                     | 0.5 ~ 1 秒 | 80 ~ 120          |
| GPT-5 雲端                                                 | 0.5 ~ 1 秒 | 70 ~ 100          |
| Gemma 4 31B [MTP](/llm/knowledge-cards/mtp/) / M4 Max 32GB | 1 ~ 3 秒   | 25 ~ 40           |
| Qwen3-Coder 30B / M2 Pro 32GB                              | 2 ~ 4 秒   | 15 ~ 25           |
| 長 context（10K+ tokens）本地                              | 30 ~ 90 秒 | 與短 context 相近 |

讀這張表時要注意三件事：

1. 雲端的 TTFT 是「請求送到資料中心 + 模型開始推論 + 第一個 token 回傳」的總和；網路 RTT 通常佔 100 ~ 300ms。本地 TTFT 是純推論成本。
2. 本地生字速度受 Apple Silicon 的[記憶體頻寬](/llm/knowledge-cards/memory-bandwidth/)限制、而不是算力。詳見 [0.1 為什麼 LLM 生字慢](/llm/00-foundations/why-llm-feels-slow/)。
3. 長 context 的首字延遲是本地 LLM 最大的痛點、瓶頸落在 [prefill](/llm/knowledge-cards/prefill/) 階段把整個 prompt 灌進 [KV cache](/llm/knowledge-cards/kv-cache/)。coding agent 場景塞了整個專案進 prompt 時、本地可能等 30 ~ 90 秒才開始吐字；這是為什麼後來出現 [oMLX 這種特化伺服器](/llm/00-foundations/mlx-mtp-omlx/) 來解 KV cache 問題。

簡單的 chat 跟短 prompt 的 code completion，本地速度體感堪用。複雜的多檔案重構、塞大量 context 的 agent 場景，本地速度落差會被放大到難以忍受。

## 能力維度：本地模型能做到哪裡

能力是本地 LLM 最被誇大、也最容易讓人失望的維度。實話實說：2026 年 5 月在 Mac 上能跑的最強本地模型（如 Gemma 4 31B、Qwen3-Coder 30B、gpt-oss 20B），能力大約在 GPT-4 mini / Claude Haiku 4.5 這個層級。比雲端旗艦模型（Claude Sonnet 4.6、Opus 4.7、GPT-5）差一個明顯的品質差距。

接近真實的判讀：

- 簡單 function 寫作、單檔重構、加 type annotation、補 unit test、寫 docstring：本地堪用，速度差不多。
- 中等難度的 debug、解讀錯誤訊息、提建議：本地能給方向，但常需要追問才會收斂。
- 跨檔案重構、設計新架構、評估技術選型、寫長篇技術文件：雲端旗艦深度領先、改交給雲端更划算。
- 規劃 multi-step plan、把模糊需求拆成可執行步驟、做 deep debugging：規劃能力是雲端旗艦的明顯強項、現階段交給雲端是合理選擇。

陷阱是把網路上 cherry-picked 的成功案例當成普遍能力。「Gemma 4 31B 解出某個 leetcode 題」這類截圖無法代表它在你日常工作流的表現。判讀方法是直接用自己一週內實際處理過的 5 ~ 10 個任務當 benchmark、跑本地模型看通過率。

## 本地反而領先雲端的情境

雲端在「絕對能力」上領先、但本地在三類情境會反過來成為更好的選擇：

1. **離線或網路受限環境**：出差、保密廠房、機上工作、行動網路不穩、雲端 API 連不上的場景。本地是唯一可用選項、能力差距不再是判讀重點。
2. **極低延遲容忍度的高頻互動**：短 prompt 的 inline code completion、即時補 type annotation 等場景。本地省去 100 ~ 300ms 的網路 RTT、體感比雲端跳字流暢、適合「打字打到一半 IDE 自動補完」這類工作流。
3. **短 context 但隱私嚴格**：金融、醫療、法務工作流的單檔處理。Prompt 短到不會放大本地速度劣勢、隱私要求又排除雲端、加上若是有 NDA 限制、本地的合規性優勢直接覆蓋能力差距。

這三類不是「本地通用領先」、而是「在這些限制下本地的劣勢被中和、優勢被放大」。除此之外的場景仍是雲端旗艦領先。

## 混用是現階段的正確心態

本地與雲端不是二選一。寫 code 場景下比較穩定的分工是：

1. 高頻、重複、隱私敏感、不需要極致品質的任務交給本地（補 type、寫測試、解釋 code、簡單重構）。
2. 低頻、複雜、需要深度思考的任務交給雲端旗艦（設計、規劃、深度 debug、跨檔案重構）。
3. 一台中型 Mac（[24GB ~ 32GB 記憶體預算](/llm/00-foundations/hardware-memory-budget/)） + 雲端旗艦訂閱（Claude Code / GPT-5）的組合、現階段是大多數工程師的甜蜜點。

把本地 LLM 當成「免費的初階 pair programmer」而不是「Claude 替代品」，期望管理就會對齊現實。後續章節會回到這個心態，特別是 [模型選型](/llm/01-local-llm-services/model-selection-priority/) 與 [期望管理](/llm/01-local-llm-services/expectation-management/)。

## 下一章

下一章：[0.1 為什麼 LLM 生字慢](/llm/00-foundations/why-llm-feels-slow/)，解釋為什麼即使你的 Mac 看起來算力很強，生字速度仍受記憶體頻寬限制。
