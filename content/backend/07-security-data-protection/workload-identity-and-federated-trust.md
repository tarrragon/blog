---
title: "7.10 Workload Identity 與聯邦信任邊界"
date: 2026-04-24
description: "大綱稿：定義非人類身份、跨平台信任與短時憑證治理問題"
weight: 80
---

本章的責任是定義非人類身份與聯邦信任問題節點，讓機器到機器的信任鏈在概念層先被完整描述。

## 本章寫作邊界

本章聚焦 workload identity、federation、短時憑證與信任收斂，不討論雲廠商特定設定語法。

## 大綱（待填充）

1. 人類身份與機器身份的責任分離
2. workload identity 的語意與邊界
3. federation trust 的傳導路徑
4. 短時憑證與長時憑證的風險差異
5. 供應商事件下的信任重評估節奏

## 問題節點（案例觸發式）

| 問題節點            | 判讀訊號                     | 風險後果           | 前置控制面                                                     |
| ------------------- | ---------------------------- | ------------------ | -------------------------------------------------------------- |
| 機器身份來源不清    | credential 缺乏發放責任鏈    | 憑證可用窗口失控   | [credential](/backend/knowledge-cards/credential/)             |
| 跨平台信任擴張過快  | token 使用面超出預期服務邊界 | 外部事件可快速傳導 | [trust-boundary](/backend/knowledge-cards/trust-boundary/)     |
| 短時憑證策略不完整  | 失效節奏與授權節奏分離       | 撤銷成本上升       | [token-revocation](/backend/knowledge-cards/token-revocation/) |
| federation 回查不足 | 信任來源與授權決策無法回串   | 事故判讀時間延長   | [audit-log](/backend/knowledge-cards/audit-log/)               |
