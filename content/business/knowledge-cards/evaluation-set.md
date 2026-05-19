---
title: "Evaluation Set"
date: 2026-05-19
description: "說明評估集如何把隱性知識編碼進 AI 產品"
weight: 61
tags: ["business", "knowledge-cards", "execution"]
---

Evaluation Set 的核心概念是「評估集」—用來測試 AI 模型表現好不好的測試資料集。一組 input + 期望 output + 通過判準，AI 跑出來的結果跟期望比對判斷是否合格。Evaluation Set 是 [Tacit Knowledge](/business/knowledge-cards/tacit-knowledge/) 的編碼形式。

## 概念位置

Evaluation Set 是 AI 產品開發的核心 artifact。對 AI Labs 來說它是模型訓練的方向盤；對企業 AI 應用來說它是把客戶腦袋裡的「這個 case 該怎麼處理」轉成可測試的資料點。[FDE](/business/knowledge-cards/fde/) 駐點工作的最終產出，本質就是該客戶的 evaluation set。

## 可觀察訊號與例子

Evaluation Set 的訊號：一組客戶實際遇到的 case + 業務專家標註的正確處理方式。例如保險理賠 evaluation set 會包含「這份理賠該批准 / 該拒絕 / 該調查」的歷史 case，AI 跑過要對得起來。Evaluation set 通常隨服務時間累積增大，新 edge case 不斷加入。

## 判讀方式

讀到「把 tacit knowledge encode 進 evaluation set」時，意味著該公司在做的不只是「賣 AI」而是「把客戶的判斷邏輯萃取進產品」。這就是 [FDE](/business/knowledge-cards/fde/) 在做的核心工作—現場跑案例、跟業務人員迭代、用業務人員的修正建立 evaluation set。Evaluation set 一旦累積到一定深度，就是該客戶獨有的 [Fat Data](/business/knowledge-cards/fat-data-fat-skill/)。
