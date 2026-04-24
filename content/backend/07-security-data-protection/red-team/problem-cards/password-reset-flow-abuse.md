---
title: "7.R11.5 密碼重設流程濫用"
date: 2026-04-24
description: "說明密碼重設流程為何常成為身份接管入口"
weight: 7215
---

密碼重設流程的核心風險是把身份恢復能力放在可外部觸發的入口。當恢復驗證弱於登入驗證，流程會成為身份接管捷徑。

## 為什麼會出問題

密碼重設流程追求可恢復性。可恢復性若缺少風險分層與異常節奏判讀，攻擊者可利用重設管道繞過原本身份邊界。

## 常見失效樣式

- 重設憑證有效期過長且可重放。
- 重設後舊會話仍維持可用。
- 重設流程缺少異常來源檢查。

## 判讀訊號

- 同一帳號短時間觸發多次重設。
- 重設完成後出現異常地理登入。
- 重設事件與高風險操作連續發生。

## 案例觸發參考

- [Twilio 2022](/backend/07-security-data-protection/red-team/cases/identity-access/twilio-2022-social-engineering/)
- [Dropbox 2022](/backend/07-security-data-protection/red-team/cases/identity-access/dropbox-2022-code-repo-phishing-chain/)

## 可連動章節

- [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)
- [8.8 事故報告轉 workflow](/backend/08-incident-response/incident-report-to-workflow/)

## 對應失效樣式卡

- [7.R11.P5 重設憑證可重放且有效期過長](/backend/07-security-data-protection/red-team/problem-cards/fp-replayable-reset-token-with-long-ttl/)
