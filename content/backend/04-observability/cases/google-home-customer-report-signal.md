---
title: "4.C23 Google Home：客訴是監控失效時唯一生效的訊號源"
date: 2026-07-04
description: "內部監控沒有發現的部分失效、客訴累積約四天才把 bug 優先度推到最高、團隊始終沒有宣告事故；consumer 回報作為 telemetry 替代品的正反面實證，以及客訴沒有寫成升級條件的代價"
weight: 23
tags: ["backend", "observability", "case-study"]
---

這個案例的核心責任是提供「內部監控失效時、consumer 回報是唯一實際生效的訊號源」的一手實證。

## 觀察

Google SRE Workbook incident-response 的 Google Home / Assistant 案例：「The Google Home support team received numerous customer phone calls, tweets, and Reddit posts about the issue, and Google Home's help forum displayed a growing thread discussing the issue」。客戶症狀從某日開始累積、直到客訴持續增加數天後、「the support team finally raise the bug priority to the highest level」—— 症狀是裝置對喚醒詞回應錯誤訊息（約半數請求失敗），客訴從 5 月 31 日開始累積，「Despite all the user reports and feedback, the bug wasn't escalated to a higher priority」，約四天後支援團隊才把 bug 優先度提到最高；原文另寫「The team did not declare an incident」，處理一直走一般的 bug 追蹤流程。

## 判讀

當內部監控沒有發現一個真實的部分失效時、consumer 回報是唯一實際生效的訊號源，而這個訊號源在本案沒有觸發任何升級。設計含義有二：support-to-engineering 的升級路徑必須存在且低摩擦、否則客訴訊號會像本案一樣延遲數天才轉成事故；客訴裡的症狀 / request-id / 時間點是可用的一手 telemetry 替代品（跟 [錯誤回報的回饋迴路：request-id、trace 與呈現回報分工](/backend/11-api-design/error-feedback-loop/) 的 request-id 契約接得上；客服回報轉給值班的條件見 [8.24 客服回報的處理](/backend/08-incident-response/support-escalation-and-engineering-reply/#轉給值班的條件與轉交方式)）。它同時是反例：Google 自己這次「客訴訊號沒被即時當升級觸發器」、正好示範缺這條設計的代價。

## 對應大綱

觀測共命運章「人層應對」段（客訴作為 telemetry 替代訊號、可作開場 case）。

## 引用源

- [Incident Response（Google SRE Workbook、Google Home 案例）](https://sre.google/workbook/incident-response/) — 一手官方 case study。已 WebFetch 驗證。

## 二手來源與狀態標注

原案例 framing 是「delayed incident declaration」（升級太慢）—— 引用重點放「訊號源替代」、跟 08 的 declaration timing 討論區隔。
