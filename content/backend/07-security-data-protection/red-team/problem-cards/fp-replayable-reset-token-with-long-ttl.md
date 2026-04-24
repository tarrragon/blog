---
title: "7.R11.P5 重設憑證可重放且有效期過長"
date: 2026-04-24
description: "說明密碼重設憑證可重放與長時效如何形成身份接管窗口"
weight: 7235
---

這個失效樣式的核心問題是恢復流程的驗證強度低於登入流程。當重設憑證可重放且時效過長，身份接管窗口會持續擴張。

## 常見形成條件

- 重設 token 缺少一次性消耗語意。
- token 有效期未依風險分層。
- 重設完成後舊會話仍維持可用。

## 判讀訊號

- 同一帳號短時間出現多次重設。
- 重設完成後快速接續高風險操作。
- 重設事件與異常地理登入重疊。

## 案例觸發參考

- [Twilio 2022](../../cases/identity-access/twilio-2022-social-engineering/)
- [Dropbox 2022](../../cases/identity-access/dropbox-2022-code-repo-phishing-chain/)

## 來源流程卡

- [密碼重設流程濫用](../password-reset-flow-abuse/)
