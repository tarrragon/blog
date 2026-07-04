---
title: "11.C76 W3C Trace Context：traceparent 的傳播義務與 security boundary 重開機制"
date: 2026-07-04
description: "跨 vendor trace 關聯的標準鉤子：每一跳 MUST 傳播、security boundary 可 restart trace、無效 id MUST ignore — 信任邊界寫進規範"
weight: 76
tags: ["backend", "api-design", "case-study", "error-contract"]
---

這個案例的核心責任是提供「trace id 作為雙向 debug 契約」的規範根據：傳播義務與不信任機制同時內建。

## 觀察

W3C Trace Context（Recommendation、2021-11-23）解決的問題原文：「Traces that are collected by different tracing vendors cannot be correlated as there is no shared unique identifier」。traceparent 格式 `version-trace-id-parent-id-trace-flags`（trace-id 32 hex、parent-id 16 hex、flags 2 hex）。收到 traceparent 的服務 MUST 往 outgoing request 傳、允許的變更只有三種：更新 parent-id、更新 sampled flag、restart trace（在 security boundary 全部重新生成）。tracestate 載 vendor 專屬 key-value、「If the value of the traceparent field wasn't changed before propagation, tracestate MUST NOT be modified」。無效 id 的處理：trace-id 全零或含非法字元、parent-id 無效時「Vendors MUST ignore the traceparent」。

## 判讀

consumer 回報問題時附的 trace id 之所以能關聯全鏈、是因為每一跳都有 MUST 級的傳播義務 —— 這是回饋迴路的規範地基。但 spec 同時內建信任邊界的兩個機制：security boundary 可 restart trace（provider 不必信 consumer 給的 trace-id）、無效 id MUST ignore（不把不可信識別符往下游傳播）。中間服務的雙重身分在這裡最具體：對 upstream 是「要不要信 incoming traceparent」的 consumer、對 downstream 是「必須產新 parent-id 再傳」的 provider。

## 對應大綱

11.11 回饋迴路章「trace id 作為雙向 debug 契約」段；restart-at-boundary 交叉到錯誤鏈傳播章的信任邊界段。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Trace Context（W3C Recommendation、2021-11-23）](https://www.w3.org/TR/trace-context/) — 一手 W3C 規範。已 WebFetch 驗證。

## 二手來源與狀態標注

Trace Context Level 2 目前僅 Candidate Recommendation Draft（2024-03-28、自述「should not be cited as final」）—— 引用以 Level 1 Recommendation 為準、Level 2 最多當註腳。
