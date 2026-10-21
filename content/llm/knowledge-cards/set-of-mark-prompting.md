---
title: "Set-of-Mark prompting（編號標記提示）"
date: 2026-10-21
slug: "set-of-mark-prompting"
description: "要讓視覺語言模型指出圖片裡的某個元件、或讀到「在截圖上疊編號再讓模型選」這類做法時"
weight: 1
tags: ["llm", "knowledge-cards", "vlm", "vision"]
---

Set-of-Mark prompting（編號標記提示）是**在圖片的候選區域上疊加可見的編號或框，讓[視覺語言模型](/llm/knowledge-cards/vlm/)以編號回答「是哪一個」**的提示做法。Jianwei Yang、Hao Zhang、Feng Li、Xueyan Zou、Chunyuan Li 與 Jianfeng Gao 在 2023 年的論文 *Set-of-Mark Prompting Unleashes Extraordinary Visual Grounding in GPT-4V* 提出這個名稱。它把「在圖上定位一個元件」這個開放式問題，轉成「從這幾個編號裡選一個」的封閉選項題，模型不必輸出座標。

## 概念位置

| 作答方式                                                                    | 模型要輸出的內容       | 適合的用途                                           |
| --------------------------------------------------------------------------- | ---------------------- | ---------------------------------------------------- |
| 自由描述                                                                    | 一段文字描述元件的位置 | 人讀的說明，難以自動比對                             |
| 輸出座標                                                                    | 一組像素座標或框       | 需要精確位置；座標精度依模型而異，要在自己的模型上量 |
| Set-of-Mark                                                                 | 一個編號               | 自動比對、可以搭配單 token 決策                      |
| Set-of-Mark 加 [structured output](/llm/knowledge-cards/structured-output/) | 一個編號欄位           | 需要把答案交給程式處理時，以格式約束確保只回編號     |

候選區域的來源可以是影像分割模型（原論文用 SEEM、SAM 這類互動式分割模型把圖片切成區域，再疊上字母數字、遮罩或框），也可以是產生畫面的程式本身（例如 UI 框架的元件樹提供每個元件的邊界）；元件樹給的邊界是精確的，可以省掉分割這一步。

## 設計責任

用 Set-of-Mark 設計題目時，判讀的重點是：

1. **編號本身是提示**：框與編號標出了「這裡有一個元件」，模型不用自己找到元件也能答對一部分題目。要量模型能否自己找到某個元件，必須另外準備沒有編號的版本當對照。
2. **編號要每次重新分配**：模型對某些代碼有先天的偏好，不論代碼標在什麼內容上都給它較高的機率（見 [4.23 System 1 決策模型](/llm/04-applications/system-one-decision-model/#取得單-token-分布的方式token-機率與重複取樣)引用的選項代碼偏好量測）。同一個元件若固定用同一個編號，這個偏好會和模型對元件本身的判斷混在一起，事後分不開。每次取樣重新隨機分配編號並重繪。
3. **編號放在要判斷的區域之外**：要判斷元件有沒有裁切、對齊或顏色問題時，編號放在元件外緣，避免標記蓋住缺陷所在的像素。
4. **編號代碼要是單一 token**：搭配[單 token 決策](/llm/04-applications/system-one-decision-model/#取得單-token-分布的方式token-機率與重複取樣)時，編號要用該模型 tokenizer 切成單一 token 的字元，否則第一個 token 的機率分不出是哪一個編號。
