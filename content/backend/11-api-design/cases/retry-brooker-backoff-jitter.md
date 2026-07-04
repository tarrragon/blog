---
title: "11.C68 Exponential Backoff And Jitter：無 jitter 的退避是明確輸家"
date: 2026-07-04
description: "N 個 client 同時競爭時總工作量隨 N² 成長；三種 jitter 公式實測、Full Jitter 總工作量最少 — consumer 之間的隱性同步要主動打散"
weight: 68
tags: ["backend", "api-design", "case-study", "error-contract"]
---

這個案例的核心責任是提供 backoff 公式選擇的一手實測：consumer 的責任除了退讓、還有彼此去相關。

## 觀察

Marc Brooker 在 AWS Architecture Blog 的實測：N 個 client 同時競爭時「the total amount of work done by the system increases with N²」。三種 jitter 公式逐字：Full Jitter `sleep = random(0, min(cap, base * 2^attempt))`；Equal Jitter `sleep = base*2^attempt/2 + random(0, base*2^attempt/2)`；Decorrelated Jitter `sleep = min(cap, random(0, last_sleep * 3))`。結論：無 jitter 的純 exponential backoff 是「the clear loser」；100 個競爭 client 下 jitter「reduced call count by more than half」；Full Jitter 總工作量最少。

## 判讀

這篇補上「consumer 各自理性、集體災難」的機制：所有 client 同步 backoff 會形成整齊的 retry 波、每一波都是對 provider 的同步衝擊。jitter 把 consumer 之間的隱性同步打散 —— consumer 的契約責任除了「退讓」（backoff）、還有「彼此去相關」（jitter）、後者是單一 consumer 視角看不到的集體契約。

## 對應大綱

11.11 接收方重試決策章「backoff 公式選擇」段、retry 風暴的同步波成因。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Exponential Backoff And Jitter（AWS Architecture Blog、Marc Brooker）](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/) — 一手、作者本人。已 WebFetch 驗證、正文完整取回。

## 二手來源與狀態標注

發表於 2015、模擬情境是 OCC 寫入競爭而非 HTTP API retry —— 結論可遷移、但引用時說明實驗設定不同。
