---
title: "Wireframe"
date: 2026-05-19
description: "說明線框圖在傳統產品設計流程中的角色"
weight: 63
tags: ["business", "knowledge-cards", "execution"]
---

Wireframe 的核心概念是「線框圖」—用簡單線條表示 UI 結構與資訊流的草圖，不含顏色、字型、圖像。它的目的是讓設計師、工程師、PM 對齊「畫面上有什麼、按了會去哪」，不討論視覺風格。Wireframe 是 [PRD](/business/knowledge-cards/prd/) 之後、設計稿之前的中間 artifact。

## 概念位置

Wireframe 在傳統 SaaS 開發中承擔「視覺化需求」的責任—把 PRD 的文字轉成畫面草圖，讓利害關係人能評論。它依賴的前提是「產品的核心價值可以用 UI 描述」。AI 產品的核心價值在 AI 行為而非 UI，wireframe 描述不了，就需要 [Vibe Code](/business/knowledge-cards/vibe-code/) 現場跑。

## 可觀察訊號與例子

Wireframe 的訊號：黑白線條、灰塊代表圖、虛擬文字（lorem ipsum）佔位、箭頭表示流程跳轉。Figma、Sketch、Balsamiq 都是常見工具。Wireframe 通常會跟 user flow（流程圖）一起出現，形成完整的需求視覺化。

## 判讀方式

讀到「AI 不能靠 wireframe 描述」時，意味著該產品的核心價值不在 UI 而在 AI 行為—wireframe 畫得再漂亮也描述不出 AI 跑出來會多準確。這是 AI 產品開發跟傳統 SaaS 的根本差異—描述工具失效後，[FDE](/business/knowledge-cards/fde/) 現場迭代成為唯一可行路徑。
