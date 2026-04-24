---
title: "7.R11.P3 代理會話上下文混層"
date: 2026-04-24
description: "說明代理會話與原始會話混層如何放大高權限濫用風險"
weight: 7233
---

這個失效樣式的核心問題是代理上下文與原始上下文沒有清楚切分。當會話混層，代理能力會穿透原始責任邊界。

## 常見形成條件

- 代理會話與原始會話共用識別資訊。
- 代理流程缺少目的與時效綁定。
- 代理行為缺少獨立稽核欄位。

## 判讀訊號

- 代理事件與原始用戶事件難以區分。
- 代理主體短時間跨多租戶操作。
- 代理會話接續執行高風險動作。

## 案例觸發參考

- [MGM 2023](../../cases/identity-access/mgm-2023-identity-lateral-impact/)
- [Mailchimp 2023](../../cases/data-exfiltration/mailchimp-2023-support-tool-abuse/)

## 來源流程卡

- [代理操作濫用](../delegated-operation-abuse/)
