---
title: "Sub-processor（子處理者）"
date: 2026-10-23
description: "平台把客戶的個人資料再交給物流、金流、雲端或其他供應商處理時，要判斷那家供應商外洩算誰的責任、委託前要先取得什麼授權"
weight: 491
tags: ["backend", "security", "privacy", "compliance", "incident-response"]
---

子處理者（sub-processor）是處理者再委託去處理控制者個人資料的另一個處理者。這是業界與契約的慣用名稱，GDPR 條文寫的是「另一個處理者」（another processor）。例如平台是商家的處理者，平台把商家的會員地址傳給串接的物流業者出貨時，那家物流業者就是子處理者。可先對照 [Data Controller and Data Processor（控制者與處理者）](/backend/knowledge-cards/data-controller-and-processor/)。

## 概念位置

依 GDPR 第 28 條，處理者委託子處理者之前要取得控制者的書面授權（逐一的授權，或一般性授權加上變更前通知、讓控制者有機會反對），並把自己對控制者承擔的資料保護義務以契約加到子處理者身上；子處理者沒有履行時，原處理者對控制者負全部責任（第 28 條第 4 項）。所以子處理者外洩時，對控制者來說仍是處理者這一側的外洩，處理者照自己外洩的方式通知控制者（通知方向見 [Data Controller and Data Processor（控制者與處理者）](/backend/knowledge-cards/data-controller-and-processor/)）。

## 可觀察訊號與例子

SaaS 平台公開的子處理者清單（列出雲端主機、寄信服務、支付處理、客服系統等供應商與它們處理的資料類別），就是一般性授權的做法。同一家物流業者可能同時是平台串接的子處理者、又是某些商家直接簽約的業者；它外洩時，外洩的那一份資料從平台傳過去，還是商家直接給的，決定了這次外洩屬於哪一方的責任。

## 設計責任

處理者要知道自己把哪些控制者的哪些欄位傳給了哪個子處理者、它保存多久，這份紀錄決定子處理者外洩時受影響的範圍；資料處理協議要讓處理者在事故時拿得到子處理者的存取紀錄或鑑識結論。子處理者被入侵時的歸屬判定與通知範圍，見 [8.26 資料外洩時對商家的通知〈子處理者的入侵通報〉](/backend/08-incident-response/security-incident-customer-notification/#子處理者的入侵通報)；資料交給供應商之前契約要寫的通報時限與責任鏈見 [7.4 資料保護與遮罩治理〈各節點的收斂動作〉](/backend/07-security-data-protection/data-protection-and-masking-governance/#各節點的收斂動作)。
