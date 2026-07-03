---
title: "11.C17 Facebook Graph API v1.0 退場：靜默語意切換（反例）"
date: 2026-07-03
description: "反例：到期後把 v1.0 請求靜默當 v2.0 處理而非回明確錯誤、長尾 app 默默壞掉"
weight: 17
tags: ["backend", "api-design", "case-study", "versioning"]
---

這個案例的核心責任是提供 deprecation 執行的反例：靜默語意切換比明確錯誤更危險。

## 觀察

Facebook 2014 年為 Graph API 引入版本化、給 v1.0 一年遷移期（官方版本表：v1.0 2010-04-21 到 2015-04-30）；到期後未遷移的請求被靜默改以 v2.0 語意處理、而非關閉。v2.0 移除了 friends 資料等大範圍權限。未遷移 app 的行為直接改變、拿不到明確錯誤。損壞影響的描述依賴二手來源（Amazon Appstore 對開發者的警告轉述）、事實句以官方版本表可支撐的範圍為準。

## 判讀

「到期後語意靜默切換」的危險在 client 不會炸在認證層、而是拿到形狀不同的資料默默壞掉 — 明確錯誤反而是對消費者更友善的失敗模式。它同時是「平台從無版本到版本化」的轉折案例：v1.0 活了近 5 年沒有契約、之後每版才有明文窗口。

## 對應大綱

11.1 違約模式段（主展開、反例）、11.5 到期行為與 11.6 邊界條款交叉、版本策略爭論文章。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Graph API version schedule（Meta for Developers、官方版本表）](https://developers.facebook.com/docs/graph-api/changelog/versions/)
- [Facebook Deprecates API v1.0 on April 30th（Amazon developer blog、二手轉述）](https://developer.amazon.com/blogs/post/TxTORRXOM8UG9G/Announcement-Facebook-Deprecates-API-v1-0-on-April-30th)
