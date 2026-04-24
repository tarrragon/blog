---
title: "7.R7.2.1 SolarWinds 2020：更新鏈被濫用"
date: 2026-04-24
description: "合法更新流程遭植入後，攻擊者如何長期潛伏與橫向擴散"
weight: 71721
---

## 事故摘要

2020 年公開的 SUNBURST 事件顯示，攻擊者透過供應鏈植入，將惡意行為包裹在合法更新流程中進入大量組織。

## 攻擊路徑

1. 滲透供應鏈節點。
2. 在合法交付流程植入惡意內容。
3. 依賴受害端對更新的高信任擴散。

## 失效控制面

- 更新來源信任過於單點。
- 行為監測難以區分合法元件與惡意利用。
- 供應鏈異常事件缺少快速隔離流程。

## 如果 workflow 少一步會發生什麼

若缺少「合法更新異常行為審查」，團隊會把事件視為一般系統活動，延長停留時間與清除成本。

## 可落地的 workflow 檢查點

- 發布前：供應鏈節點做分層信任與簽章驗證。
- 日常：建立異常更新行為的 [symptom-based alert](/backend/knowledge-cards/symptom-based-alert/)。
- 事故中：切換受影響更新鏈、建立替代交付路徑與回復順序。

## 可引用章節

- `backend/05-deployment-platform` 的交付與簽章治理
- `backend/08-incident-response` 的供應鏈事件指揮流程

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：[solarwinds.com](https://www.solarwinds.com/securityadvisory)
- 政府或監管：[cisa.gov](https://www.cisa.gov/news-events/cybersecurity-advisories/aa20-352a)
- 技術分析：[mandiant.com](https://www.mandiant.com/resources/blog/evasive-attacker-leverages-solarwinds-supply-chain-compromises)
