---
title: "11.C13 GitHub：密碼認證廢止的 brownout 執行"
date: 2026-07-03
description: "deprecation 執行機制案例：公告觸及不到的長尾 client、用排程 brownout 的短暫真實故障叫醒"
weight: 13
tags: ["backend", "api-design", "case-study", "versioning"]
---

這個案例的核心責任是說明 deprecation 的執行機制設計：brownout 作為遷移警報。

## 觀察

GitHub 2020-12 宣布 2021-08-13 起 Git 操作停用密碼認證、強制 token。執行前在 2021-06-30 與 07-28 兩個 UTC 時窗做 brownout（暫時停用再恢復）、讓沒讀公告的使用者在低風險時窗先撞牆。已開 2FA 者、GHES、GitHub App 不受影響。

## 判讀

brownout 承擔的角色是「email 與 blog 公告觸及不到的長尾 client、只有短暫真實故障叫得醒」。宣告日到強制日約 8 個月、且提前明列豁免族群 — 遷移窗口設計包含「誰不用動」的邊界宣告、跟「何時動」同等重要。

## 對應大綱

11.5 版本策略與 deprecation、11.6 向後相容的變更紀律。與 C12 同公司 cluster。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Token authentication requirements for Git operations（GitHub blog、2020）](https://github.blog/2020-12-15-token-authentication-requirements-for-git-operations/)
