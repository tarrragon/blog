---
title: "4.C23 Google Home：客訴是監控失效時唯一生效的訊號源"
date: 2026-07-04
description: "內部監控漏掉未升級的真實 outage、是客訴量把事故推上去；consumer 回報作為 telemetry 替代品的正反面實證"
weight: 23
tags: ["backend", "observability", "case-study"]
---

這個案例的核心責任是提供「內部監控失效時、consumer 回報是唯一實際生效的訊號源」的一手實證。

## 觀察

Google SRE Workbook incident-response 的 Google Home / Assistant 案例：「The Google Home support team received numerous customer phone calls, tweets, and Reddit posts about the issue, and Google Home's help forum displayed a growing thread discussing the issue」。客戶症狀從某日開始累積、直到客訴持續增加數天後、「the support team finally raise the bug priority to the highest level」—— 內部監控沒把它升級、是客訴量把事故推上去的。

## 判讀

當內部監控漏掉或未升級一個真實 outage 時、consumer 回報是唯一實際生效的訊號源。設計含義有二：support-to-engineering 的升級路徑必須存在且低摩擦、否則客訴訊號會像本案一樣延遲數天才轉成事故；客訴裡的症狀 / request-id / 時間點是可用的一手 telemetry 替代品（跟 [11.11 錯誤回報的回饋迴路](/backend/11-api-design/error-feedback-loop/) 的 request-id 契約接得上）。它同時是反例：Google 自己這次「客訴訊號沒被即時當升級觸發器」、正好示範缺這條設計的代價。

## 對應大綱

觀測共命運章「人層應對」段（客訴作為 telemetry 替代訊號、可作開場 case）。

## 引用源

- [Incident Response（Google SRE Workbook、Google Home 案例）](https://sre.google/workbook/incident-response/) — 一手官方 case study。已 WebFetch 驗證。

## 二手來源與狀態標注

原案例 framing 是「delayed incident declaration」（升級太慢）—— 引用重點放「訊號源替代」、跟 08 的 declaration timing 討論區隔。
