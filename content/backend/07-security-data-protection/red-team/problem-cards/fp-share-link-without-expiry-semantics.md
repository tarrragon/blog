---
title: "7.R11.P9 分享連結缺少到期語意"
date: 2026-04-24
description: "說明分享連結缺少到期語意如何把協作路徑轉成長尾暴露路徑"
weight: 7239
---

這個失效樣式的核心問題是分享機制把內部邊界轉為外部可達邊界，且缺少到期收斂條件。當分享連結長期可達，風險會累積成長尾暴露。

## 常見形成條件

- 分享連結缺少到期時間與用途限制。
- 分享撤銷與快取更新節奏不同步。
- 分享權限變更缺少即時回收機制。

## 判讀訊號

- 分享連結在預期期限後仍可存取。
- 高敏感資料分享行為在異常時段上升。
- 分享撤銷後持續出現存取事件。

## 案例觸發參考

- [GoAnywhere 2023](../cases/data-exfiltration/goanywhere-mft-2023-exfiltration-chain/)
- [LastPass 2022](../cases/data-exfiltration/lastpass-2022-backup-chain/)

## 來源流程卡

- [分享流程濫用](sharing-flow-abuse/)
