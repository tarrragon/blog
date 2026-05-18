---
title: "3.C49 Airbnb Inspekt：Visibility timeout 當 retry budget"
date: 2026-05-18
description: "Airbnb Inspekt 隱私掃描器、scanner pull message、visibility timeout 自然觸發重現、用重現次數當 retry budget。"
weight: 49
tags: ["backend", "message-queue", "case-study", "aws-sqs"]
---

這個案例的核心責任是說明 visibility timeout 不只是「處理時間」、可當隱式的 retry 機制。

## 觀察

Airbnb 的 Inspekt 隱私資料掃描系統用 SQS task queue 派發 scan task（每 table/object/app 一個 message）、Scanner nodes 水平 pull。"each message reappears N times back into the queue until a scanner node deletes it" 是 visibility timeout 在實戰的應用。

## 判讀

用 message 重現次數做 retry budget、scanner 失敗時不用自管 retry table。揭露 SQS 的「不刪除即重現」是設計、不是 bug、可以當隱式 retry 機制用。

## 對應大綱

SQS 進階主題：Visibility timeout + in-flight messages。

## 下一步路由

回 [SQS vendor 頁](/backend/03-message-queue/vendors/aws-sqs/) 與 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)。

## 引用源

- [Automating Data Protection at Scale Part 2](https://medium.com/airbnb-engineering/automating-data-protection-at-scale-part-2-c2b8d2068216)
