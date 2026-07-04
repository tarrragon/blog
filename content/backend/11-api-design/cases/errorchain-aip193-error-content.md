---
title: "11.C75 AIP-193 錯誤內容規範：三層受眾與「不假設使用者懂內部實作」"
date: 2026-07-04
description: "機器可讀的 (reason, domain) 契約、developer-facing message、LocalizedMessage 三層分工；message 穩定性規則反向揭露 Hyrum's Law"
weight: 75
tags: ["backend", "api-design", "case-study", "error-contract"]
---

這個案例的核心責任是提供「provider 該暴露什麼、給誰」的規範根據：錯誤內容按受眾分三層。

## 觀察

AIP-193（Approved、updated 2024-10-18）規定 error 用 `google.rpc.Status`（code / message / details）、details 必含 `ErrorInfo`：reason（`[A-Z][A-Z0-9_]+[A-Z0-9]`、max 63 字元）、domain（全域唯一、通常是服務名如 `pubsub.googleapis.com`）、metadata（request-specific key-value）。(reason, domain) 組成機器可讀識別符、同一錯誤必須保持一致。信任邊界原文：「error messages **must not** assume that the user will know anything about its underlying implementation」。message 定位是「developer-facing, human-readable "debug message"」、給終端使用者的文案走 `LocalizedMessage`。另有穩定性規則：沒帶 ErrorInfo 的舊 API「The content of `Status.message` **must** be stable」—— client 已在 parse message、動了就 break。

## 判讀

AIP-193 把「provider 暴露多少」拆成三個受眾層：機器（ErrorInfo 的 reason/domain、可程式化分支）、開發者（message、可變動但不可當 API）、終端使用者（LocalizedMessage）。「must not assume underlying implementation」是信任邊界的正面規範 —— 錯誤要用 consumer 的語彙寫、不是把內部狀態倒出來。message 穩定性規則反向揭露 Hyrum's Law 張力：provider 沒給機器可讀欄位、consumer 就會把人類可讀欄位當契約、之後改字就是 breaking change。

## 對應大綱

11.11 錯誤鏈傳播章「錯誤契約的三層受眾」「provider 該暴露什麼」段（與 C77 OWASP 對撞成中間路線）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [AIP-193 Errors](https://google.aip.dev/193) — Approved、updated 2024-10-18。已 WebFetch 驗證（兩次交叉確認）。

## 二手來源與狀態標注

AIP-193 沒有任何「中間服務怎麼轉譯 upstream 錯誤」的條文（兩次針對性取回確認缺席）—— 它只規範 outbound error 的形狀。「跨服務轉譯」的責任論證是從雙重身分推導、正文標明是推導不是引用。
