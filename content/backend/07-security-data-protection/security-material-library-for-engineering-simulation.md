---
title: "7.26 資安素材庫如何支援工程推演"
tags: ["Security", "Materials", "Simulation", "Knowledge Routing"]
date: 2026-04-30
description: "說明專業來源、案例、情境與控制模式如何組合成工程推演與章節回寫流程"
---

本篇的責任是說明素材庫如何支援工程推演。讀者讀完後，能把來源卡、案例卡、情境卡與控制模式組成可執行推演。

## 核心論點

素材庫支援推演的核心概念是分層組合。分層一旦穩定，團隊可以快速從外部來源走到內部演練，再走到章節與流程回寫。

## 素材分層

| 分層                 | 責任                   | 典型輸出      |
| -------------------- | ---------------------- | ------------- |
| Professional sources | 提供可回溯專業依據     | source card   |
| Field cases          | 提供現場壓力與決策節點 | case card     |
| Scenarios            | 提供可重播推演情境     | scenario card |
| Control patterns     | 提供可搬運控制模板     | pattern card  |

## 推演組裝流程

推演組裝流程的責任是把素材轉成操作路由。建議流程為來源選型、案例映射、情境組裝、控制驗證、回寫更新五步。

## 來源選型規則

來源選型規則的責任是提高引用品質。流程與治理論點優先 NIST/CISA，防守詞彙優先 D3FEND，驗證方法優先 ATT&CK Evaluations，規則生命周期優先 Sigma/SANS，壓力模型優先 Mandiant。

## 回寫路由

回寫路由的責任是讓素材使用可追蹤。每次推演完成後，至少回寫到藍隊章節、主章延伸章節與知識卡片連結。

## 判讀訊號與路由

| 判讀訊號               | 代表需求                      | 下一步路由   |
| ---------------------- | ----------------------------- | ------------ |
| 文章論點缺少可回溯來源 | 需要先補 professional sources | 7.26 → 7.BM1 |
| 演練情境缺少現場壓力   | 需要補 field cases            | 7.26 → 7.BM2 |
| 控制驗證缺少可搬運模板 | 需要補 control patterns       | 7.26 → 7.BM4 |
| 推演完成後章節未更新   | 需要補 write-back 路由        | 7.26 → 7.24  |

## 必連章節

- [7.BM 藍隊素材庫](/backend/07-security-data-protection/blue-team/materials/)
- [7.B9 Blue Team Scenario Library](/backend/07-security-data-protection/blue-team/blue-team-scenario-library/)
- [7.B12 Defender Pressure From Real Incidents](/backend/07-security-data-protection/blue-team/defender-pressure-from-real-incidents/)
- [7.24 資安事故如何回寫產品與架構](/backend/07-security-data-protection/security-incident-write-back-to-product-and-architecture/)

## 完稿判準

完稿時要讓讀者能把素材庫組裝成一次工程推演。輸出至少包含分層素材、組裝流程、來源規則與回寫路由。
