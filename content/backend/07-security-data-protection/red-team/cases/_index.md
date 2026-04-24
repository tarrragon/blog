---
title: "7.R7 事故案例庫（可引用）"
date: 2026-04-24
description: "把公開事故整理成可引用案例體系，讓服務章節與 incident workflow 可雙向回寫"
weight: 717
---

這個分類的責任是把事故拆成可重複引用的決策素材。每篇案例都用同一組結構回答：事故摘要、攻擊路徑、失效控制面、少一步的後果、可落地的 workflow 檢查點、可引用章節、可追溯來源。

## 分類入口

- [Identity & Access](identity-access/)：身分、認證流程、社交工程、第三方身分鏈。
- [Supply Chain](supply-chain/)：CI/CD、更新鏈、RMM、開源與 MSP 供應鏈。
- [Edge Exposure](edge-exposure/)：邊界設備、外網入口、管理平面、鏈式漏洞。
- [Data Exfiltration](data-exfiltration/)：資料外送、備份鏈、營運中斷與回復壓力。
- [案例引用地圖](case-reference-map/)：服務主題到案例與 workflow 檢查點的對照。

## 使用方式

1. 先在服務章節定義風險主題與控制面。
2. 選一篇同類型案例，引用「如果 workflow 少一步會發生什麼」。
3. 把該步驟落地到 [incident-report-to-workflow](/backend/08-incident-response/incident-report-to-workflow/) 的 runbook 流程。
