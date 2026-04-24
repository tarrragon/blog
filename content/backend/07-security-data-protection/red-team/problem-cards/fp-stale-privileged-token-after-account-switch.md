---
title: "7.R11.P4 帳號切換後沿用高權限 token"
date: 2026-04-24
description: "說明帳號切換後權限 token 殘留如何造成身份邊界漂移"
weight: 7234
---

這個失效樣式的核心問題是身份切換與 token 收斂節奏不一致。當切換完成仍沿用前一身份 token，流程會形成隱性越權。

## 常見形成條件

- 帳號切換只更新顯示層，未同步更新授權上下文。
- 高權限 token 在切換後保持可用。
- 切換流程缺少高風險動作再驗證。

## 判讀訊號

- 切換後立即執行前一身份專屬操作。
- 同一 token 出現在多身份上下文。
- 會話事件在身份對齊上出現斷點。

## 案例觸發參考

- [Citrix Bleed 2023](../../cases/edge-exposure/citrix-bleed-2023-session-hijack/)
- [Uber 2022](../../cases/identity-access/uber-2022-mfa-fatigue/)

## 來源流程卡

- [帳號切換濫用](../account-switching-abuse/)
