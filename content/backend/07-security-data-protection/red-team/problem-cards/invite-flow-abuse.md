---
title: "7.R11.1 邀請流程濫用"
date: 2026-04-24
description: "說明邀請流程為何容易形成身份擴散與越權入口"
weight: 7211
---

邀請流程的核心風險是把身份建立權限暴露在高頻操作節點。當邀請邊界與角色邊界沒有同步收斂，流程會從協作入口轉成擴散入口。

## 為什麼會出問題

邀請流程通常追求低摩擦啟用。低摩擦設計若缺少角色上限與上下文驗證，攻擊者可利用合法邀請節奏建立後續操作落點。

## 常見失效樣式

- 邀請可直接綁定高權限角色。
- 邀請連結可重放或長時間有效。
- 邀請發送與審核責任由同一主體完成。

## 判讀訊號

- 同一主體短時間建立大量邀請。
- 新邀請帳號快速接觸高風險操作。
- 邀請接受行為與正常地理/裝置分佈偏移。

## 案例觸發參考

- [Uber 2022](../cases/identity-access/uber-2022-mfa-fatigue/)
- [MGM 2023](../cases/identity-access/mgm-2023-identity-lateral-impact/)

## 可連動章節

- [7.2 身分與授權邊界](../../identity-access-boundary/)
- [7.7 稽核追蹤與責任邊界](../../audit-trail-and-accountability-boundary/)

## 對應失效樣式卡

- [7.R11.P1 可重放邀請連結](fp-replayable-invitation-link/)
