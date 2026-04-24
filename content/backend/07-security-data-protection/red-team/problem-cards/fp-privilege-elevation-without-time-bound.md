---
title: "7.R11.P6 權限提升缺乏時效綁定"
date: 2026-04-24
description: "說明權限提升缺乏時效綁定如何把例外能力轉成常態能力"
weight: 7236
---

這個失效樣式的核心問題是權限提升沒有清楚回收邊界。當提升缺少時效與目的綁定，例外能力會長期停留。

## 常見形成條件

- 提升請求缺少有效期限欄位。
- 提升回收依賴人工排程。
- 提升事件未同步到所有授權系統。

## 判讀訊號

- 提升後高權限存續時間持續拉長。
- 同一主體反覆觸發提升後批次操作。
- 提升與審核時序對齊持續偏移。

## 案例觸發參考

- [Confluence 2023（22515/22518）](../cases/edge-exposure/confluence-2023-cve-22515-22518-access-control-chain/)
- [Fortinet 2022（40684）](../cases/edge-exposure/fortinet-cve-2022-40684-auth-bypass/)

## 來源流程卡

- [權限提升流程濫用](privilege-escalation-flow-abuse/)
