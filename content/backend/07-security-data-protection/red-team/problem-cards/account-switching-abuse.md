---
title: "7.R11.4 帳號切換濫用"
date: 2026-04-24
description: "說明多帳號切換為何容易形成會話混層與身份擴散"
weight: 7214
---

帳號切換的核心風險是把多個身份上下文放在同一操作節奏。當上下文切換與權限切換沒有同步，流程會形成隱性越權。

## 為什麼會出問題

帳號切換通常是為了營運效率與多角色工作。多角色共存若缺少清楚上下文提示與會話隔離，誤用與濫用都會升高。

## 常見失效樣式

- 切換後沿用前一身份的高權限 token。
- 切換狀態缺乏明確可見標記。
- 切換流程缺少高風險動作二次確認。

## 判讀訊號

- 同一裝置在短時間跨多身份切換。
- 切換後立刻執行高風險批次動作。
- 會話事件無法清楚對齊身份上下文。

## 案例觸發參考

- [Citrix Bleed 2023](../cases/edge-exposure/citrix-bleed-2023-session-hijack/)
- [Uber 2022](../cases/identity-access/uber-2022-mfa-fatigue/)

## 可連動章節

- [7.2 身分與授權邊界](../../identity-access-boundary/)
- [7.5 傳輸信任與憑證生命週期](../../transport-trust-and-certificate-lifecycle/)
