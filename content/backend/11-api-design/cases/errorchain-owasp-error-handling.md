---
title: "11.C77 OWASP error handling：錯誤訊息是攻擊者的偵察面"
date: 2026-07-04
description: "非預期錯誤回 generic response、細節只留 server side log — provider 少暴露的安全端論證、跟 AIP-193 的機器可讀路線形成張力"
weight: 77
tags: ["backend", "api-design", "case-study", "error-contract"]
---

這個案例的核心責任是提供「provider 暴露下限」的安全端論證、跟 C75（AIP-193）對撞出中間路線。

## 觀察

OWASP Error Handling Cheat Sheet 核心規則：非預期錯誤時「a generic response is returned by the application but the error details are logged server side for investigation, and not returned to the user」。理由是偵察風險：「unhandled errors can assist an attacker in this initial phase」—— 實例包含 stack trace 洩漏 Struts2/Tomcat 版本、SQL error 洩漏安裝路徑並幫攻擊者「identify an injection point」。實作範例是統一回 HTTP 500 加 generic body（如 `{"message":"An error occur, please retry"}`）。另建議監控 5xx：「a good indication of the application failing for some sets of inputs」。

## 判讀

OWASP 給了「provider 少暴露」的安全端論證、跟 AIP-193 的「多給機器可讀細節」形成張力的兩端 —— 全 generic 讓 consumer 完全無法自助、全細節變成攻擊偵察面。AIP-193 的 (reason, domain) 設計正是中間路線：給分支用的機器可讀識別符、不洩內部實作。這組對撞是「provider 該暴露什麼」的邊界討論骨架、對應 backend/07 的攻擊面思路。

## 對應大綱

11.11 錯誤鏈傳播章「暴露的下限：安全邊界」段（與 C75 對照）、連 [07 安全](/backend/07-security-data-protection/)。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Error Handling Cheat Sheet（OWASP Cheat Sheet Series）](https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html) — 一手、現行版。已 WebFetch 驗證。

## 二手來源與狀態標注

該頁完全沒提 error ID / correlation id 回傳給使用者 ——「generic message + 附 trace id 供回報」這個常見組合不能掛 OWASP 出處：trace id 部分引 C76（W3C Trace Context）、組合本身標明是常見實務而非 OWASP 規範。
