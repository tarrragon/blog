---
title: "7.BM1 藍隊專業來源卡"
tags: ["Blue Team", "Professional Sources", "Security References"]
date: 2026-04-30
description: "整理藍隊可引用的專業來源，明確標示可支撐論點與引用限制"
weight: 7251
---

專業來源卡的責任是把藍隊文章的外部依據整理成可回溯材料。每張卡只承擔一個來源，並標示來源定位、可引用論點、後端轉譯方式與引用限制。

## 來源地圖

| 來源卡                                                                                                                                                         | 支撐主題            | 主要用途                           |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- | ---------------------------------- |
| [NIST SP 800-61r3](/backend/07-security-data-protection/blue-team/materials/professional-sources/nist-sp-800-61r3-incident-response/)                          | 事故回應與 CSF 對齊 | 把 incident response 接到治理流程  |
| [CISA Playbooks](/backend/07-security-data-protection/blue-team/materials/professional-sources/cisa-incident-vulnerability-response-playbooks/)                | 事故與漏洞回應程序  | 把流程拆成 checklist 與狀態追蹤    |
| [MITRE D3FEND](/backend/07-security-data-protection/blue-team/materials/professional-sources/mitre-d3fend-defense-vocabulary/)                                 | 防守技術詞彙        | 統一控制面與 countermeasure 語言   |
| [MITRE ATT&CK Evaluations](/backend/07-security-data-protection/blue-team/materials/professional-sources/mitre-attack-evaluations-threat-informed-validation/) | 威脅導向驗證        | 把防守能力接到 adversary emulation |
| [Sigma](/backend/07-security-data-protection/blue-team/materials/professional-sources/sigma-detection-rule-lifecycle/)                                         | 偵測規則格式        | 建立 detection-as-code 語言        |
| [Mandiant M-Trends 2025](/backend/07-security-data-protection/blue-team/materials/professional-sources/mandiant-m-trends-defender-pressure/)                   | 現場防守壓力        | 補充攻擊者繞過與 dwell time 壓力   |
| [SANS Detection Engineering Survey](/backend/07-security-data-protection/blue-team/materials/professional-sources/sans-detection-engineering-survey/)          | 偵測工程職能趨勢    | 支撐偵測規則維護與協作流程         |

## 引用規則

專業來源卡的引用規則是先確認文章要支撐的論點類型。流程論點引用 NIST/CISA，詞彙論點引用 MITRE D3FEND，驗證論點引用 MITRE ATT&CK Evaluations，規則生命週期引用 Sigma/SANS，現場壓力引用 Mandiant。

## 反向驗證

專業來源卡的限制段落是寫作安全閥。每張卡都要說明來源適合支撐什麼，也要說明來源需要在後端服務情境中重新轉譯的地方。
