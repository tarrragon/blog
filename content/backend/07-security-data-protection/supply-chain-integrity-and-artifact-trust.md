---
title: "7.12 供應鏈完整性與 Artifact 信任"
date: 2026-04-24
description: "大綱稿：定義 build provenance、artifact 信任與交付鏈風險問題"
weight: 82
---

本章的責任是定義供應鏈完整性問題節點，讓交付鏈的信任判讀可在實作前先被對齊。

## 本章寫作邊界

本章聚焦來源可信度、組件邊界與發佈節奏治理，不討論單一 CI/CD 平台操作流程。

## 大綱（待填充）

1. build provenance 的責任語意
2. artifact 信任鏈與邊界
3. 第三方組件風險傳導
4. 發佈凍結、恢復與再驗證節奏
5. 供應鏈事件後的收斂路由

## 問題節點（案例觸發式）

| 問題節點           | 判讀訊號                     | 風險後果               | 前置控制面                                                             |
| ------------------ | ---------------------------- | ---------------------- | ---------------------------------------------------------------------- |
| 來源可追溯性不足   | build 與來源提交無法一致回查 | 發佈可信度下降         | [ci-pipeline](/backend/knowledge-cards/ci-pipeline/)                   |
| artifact 信任斷點  | 發佈產物缺乏簽署與完整性證據 | 受污染產物進入正式流程 | [deployment-contract](/backend/knowledge-cards/deployment-contract/)   |
| 第三方依賴風險放大 | 同類組件事件波及多服務       | 修補與回退成本上升     | [dependency-isolation](/backend/knowledge-cards/dependency-isolation/) |
| 事件後發佈節奏混亂 | 凍結與恢復條件不一致         | 二次事故風險上升       | [release-gate](/backend/knowledge-cards/release-gate/)                 |
