---
title: "MITRE D3FEND：防守技術詞彙地圖"
tags: ["MITRE", "D3FEND", "Defense Vocabulary"]
date: 2026-04-30
description: "把 MITRE D3FEND 轉成藍隊控制面與防守技術詞彙素材"
weight: 72513
---

MITRE D3FEND 的素材責任是提供防守技術的共用詞彙。D3FEND 把 countermeasure techniques 與 adversary techniques 建成知識圖譜，適合用來統一控制面、偵測能力與防守設計語言。

## 來源定位

[MITRE D3FEND](https://d3fend.mitre.org/) 與 [D3FEND FAQ](https://d3fend.mitre.org/faq/) 適合支撐「防守控制面需要標準詞彙」的論點。FAQ 明確說明 D3FEND 是 defensive cybersecurity techniques 的 knowledge graph，並說明它的主要目標是標準化描述防守技術功能的 vocabulary。

## 可引用論點

| 可引用論點             | 藍隊轉譯                                      |
| ---------------------- | --------------------------------------------- |
| 防守技術需要標準詞彙   | 7.B1 控制面地圖可用 D3FEND 統一命名           |
| 防守技術可對應攻擊技術 | 7.B 可把 red-team problem card 轉成防守控制面 |
| 技術詞彙服務架構決策   | 05/06/08 可用同一語言交接控制能力             |

## 後端服務轉譯

後端服務引用這張卡時，重點是把「防守技術名稱」轉成「服務控制面欄位」。例如 access control、[credential](/backend/knowledge-cards/credential/) protection、message validation、[artifact](/backend/knowledge-cards/artifact-provenance/) verification 與 monitoring 都需要 owner、訊號與驗證證據。

## 引用限制

D3FEND 適合作為詞彙與關係地圖，優先序、投資順序與效果驗證仍要回到服務風險、事件資料與控制測試。
