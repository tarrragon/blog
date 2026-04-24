---
title: "7.R7.2.4 XZ Backdoor 2024：開源供應鏈長期滲透"
date: 2026-04-24
description: "開源維護鏈遭滲透後，為何會直接影響廣泛 Linux 發行流程"
weight: 71724
---

## 事故摘要

2024 年 3 月，XZ Utils 事件揭露開源供應鏈可被長期滲透並在釋出流程埋入後門，對基礎設施信任鏈造成直接衝擊。

## 攻擊路徑

1. 長期滲透維護流程。
2. 在釋出包鏈條加入惡意邏輯。
3. 透過下游發行與部署流程擴散風險。

## 失效控制面

- 開源維護與釋出治理缺少獨立覆核。
- 下游對上游釋出信任過高。
- 供應鏈檢測流程無法及時抓到異常組件行為。

## 如果 workflow 少一步會發生什麼

若缺少「上游重大事件觸發的版本凍結與風險重評」，下游仍可能將高風險版本推進正式環境。

## 可落地的 workflow 檢查點

- 發布前：關鍵依賴建立雙人覆核與來源驗證。
- 日常：維護套件清單與影響面地圖。
- 事故中：啟動版本凍結、替代版本切換與復測流程。

## 可引用章節

- `backend/05-deployment-platform` 的依賴治理
- `backend/06-reliability` 的變更風險控制

## 來源

- http://www.openwall.com/lists/oss-security/2024/03/29/4
- https://www.cisa.gov/news-events/alerts/2024/03/29/reported-supply-chain-compromise-affecting-xz-utils-data-compression-library-cve-2024-3094
- https://nvd.nist.gov/vuln/detail/CVE-2024-3094

