---
title: "11.C70 AWS DynamoDB 2015 事故：內部元件的 retry 自保把錯誤率推到 55%（反例）"
date: 2026-07-04
description: "反例：metadata 服務過載後 storage server 逾時自我下線再重試、風暴成形後系統不自癒、要人工暫停請求才能喘息；事後修正同時動兩端"
weight: 70
tags: ["backend", "api-design", "case-study", "error-contract"]
---

這個案例的核心責任是提供 retry 風暴的教科書實例：consumer 是 AWS 自己的內部元件、說明這是任何 caller 的結構性行為、不是外部客戶不守規矩。

## 觀察

AWS 官方 postmortem（Summary of the Amazon DynamoDB Service Disruption、2015-09-20、US-East）：GSI 採用讓 membership 資料膨脹（「a table with large numbers of partitions could have its contribution of partition data to the membership lists quickly double or triple」）。網路擾動後、大量同時的 membership 請求讓 metadata 服務處理變慢並超過時限 —— 逾時的 storage server 自我下線、再重試、進一步壓垮 metadata 服務。「By 2:37am PDT, the error rate … had risen far beyond any level experienced in the last 3 years, finally stabilizing at approximately 55%」。復原手段是 5:06am 主動暫停對 metadata 服務的請求以卸載、加容量、7:10am 恢復。事後修正：加大 metadata 容量、監控 membership 大小、降低 retry 請求速率、metadata 服務分片。

## 判讀

consumer 的 retry 自保在 provider 過載時等效於 DDoS —— 而這裡的 consumer 是 AWS 自己的 storage server、證明這是結構性行為。風暴一旦成形、系統不會自癒：復原必須人為切斷 retry 迴路（暫停請求）讓 provider 喘息。事後修正同時動兩端 —— provider 加容量加分片、consumer 降 retry 率 —— 責任是雙向的、單邊修不了這類事故。

## 對應大綱

11.11 接收方重試決策章「retry 風暴實例」段、「風暴成形後為何要人工斷路」。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Summary of the Amazon DynamoDB Service Disruption（AWS 官方 postmortem）](https://aws.amazon.com/message/5467D2/) — 一手。已 WebFetch 驗證、正文完整取回。

## 二手來源與狀態標注

postmortem 未逐字出現「retry storm」一詞 —— 放大機制從「simultaneous requests + 自我下線再重連」敘述推得、正文引述貼原句、不替 AWS 造詞（「retry storm」的官方定義見 C72）。
