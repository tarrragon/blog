---
title: "7.B8 Defensive Vocabulary Map"
tags: ["Blue Team", "D3FEND", "Defense Vocabulary", "Control Mapping"]
date: 2026-04-30
description: "用防守技術詞彙地圖統一控制面、偵測規則與服務交接語言"
weight: 728
---

本篇的責任是建立 defensive vocabulary map。讀者讀完後，能用一致詞彙描述控制面能力、偵測責任與交接欄位。

## 核心論點

Defensive vocabulary map 的核心概念是用共用詞彙降低跨團隊摩擦。詞彙一旦一致，規則設計、事件交接與演練回寫都能更快收斂。

## 讀者入口

本篇適合銜接 [7.B1 防守控制面地圖](/backend/07-security-data-protection/blue-team/defense-control-map/)、[MITRE D3FEND](/backend/07-security-data-protection/blue-team/materials/professional-sources/mitre-d3fend-defense-vocabulary/) 與 [trust boundary](/backend/knowledge-cards/trust-boundary/)。

## 詞彙地圖欄位

| 欄位     | 責任             | 產出             |
| -------- | ---------------- | ---------------- |
| Term     | 定義防守技術名稱 | vocabulary entry |
| Scope    | 說明技術作用範圍 | boundary note    |
| Signal   | 對應可觀測訊號   | signal mapping   |
| Owner    | 對應主責角色     | owner mapping    |
| Evidence | 對應驗證證據     | evidence mapping |
| Handoff  | 對應交接章節     | routing link     |

## 詞彙分層

詞彙分層的責任是避免同詞多義。建議至少分三層：

1. Control term：描述防守能力。
2. Detection term：描述訊號與規則。
3. Response term：描述分級、處置與回寫。

## 邊界對齊

邊界對齊的責任是讓詞彙對上服務邊界。每個詞彙都要能回答它作用在哪個 trust boundary、影響哪種資產、由哪個 owner 維護。

## 與規則生命周期整合

與規則生命周期整合的責任是把詞彙直接接到規則資產。詞彙卡可對應到 rule source、triage question、severity 與 evidence，形成可追溯的維護鏈。

## 判讀訊號與路由

| 判讀訊號                     | 代表需求                 | 下一步路由  |
| ---------------------------- | ------------------------ | ----------- |
| 同一事件在不同團隊有不同命名 | 需要統一詞彙地圖         | 7.B8 → 7.B1 |
| 規則描述與控制描述尚未對齊   | 需要補 term-to-rule 映射 | 7.B8 → 7.B5 |
| 交接文件使用抽象詞彙         | 需要補邊界與證據欄位     | 7.B8 → 7.B6 |
| 演練回寫尚未回到章節         | 需要補 handoff 欄位      | 7.B8 → 7.B9 |

## 必連章節

- [7.B1 防守控制面地圖](/backend/07-security-data-protection/blue-team/defense-control-map/)
- [7.B5 Detection Engineering Lifecycle](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)
- [7.B6 Incident Triage Loop](/backend/07-security-data-protection/blue-team/incident-triage-loop/)
- [7.BM1 藍隊專業來源卡](/backend/07-security-data-protection/blue-team/materials/professional-sources/)

## 完稿判準

完稿時要讓讀者能把防守詞彙寫成可交接地圖。輸出至少包含 term、scope、signal、owner、evidence 與 handoff。
