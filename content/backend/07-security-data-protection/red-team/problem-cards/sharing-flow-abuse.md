---
title: "7.R11.9 分享流程濫用"
date: 2026-04-24
description: "說明分享流程為何容易把內部資料邊界轉成外部可達邊界"
weight: 7219
---

分享流程的核心風險是把存取邊界從內部身份改成連結或第三方可達路徑。當分享條件與資料敏感度脫鉤，流程會形成外部擴散通道。

## 為什麼會出問題

分享流程追求協作速度。協作導向若缺少到期語意、範圍限制與回收機制，分享路徑會長期維持可達。

## 常見失效樣式

- 分享連結缺少到期與用途邊界。
- 分享對象範圍可被任意擴張。
- 分享撤銷在快取與副本呈現同步延遲。

## 判讀訊號

- 高敏感資料分享行為在異常時段增加。
- 分享連結在非預期地理位置被存取。
- 分享撤銷後仍有持續存取事件。

## 案例觸發參考

- [GoAnywhere 2023](/backend/07-security-data-protection/red-team/cases/data-exfiltration/goanywhere-mft-2023-exfiltration-chain/)
- [LastPass 2022](/backend/07-security-data-protection/red-team/cases/data-exfiltration/lastpass-2022-backup-chain/)

## 可連動章節

- [7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)
- [7.5 傳輸信任與憑證生命週期](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/)

## 對應失效樣式卡

- [7.R11.P9 分享連結缺少到期語意](/backend/07-security-data-protection/red-team/problem-cards/fp-share-link-without-expiry-semantics/)
