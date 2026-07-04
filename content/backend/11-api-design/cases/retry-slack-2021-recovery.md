---
title: "11.C71 Slack 2021-01-04 事故：復原期 retry 加 circuit breaking 是藥方"
date: 2026-07-04
description: "retry 的反向平衡：網路恢復後正是 retry 與 circuit breaking 讓系統爬回服務狀態 — retry 是否有害取決於 provider 處於過載中還是恢復中"
weight: 71
tags: ["backend", "api-design", "case-study", "error-contract"]
---

這個案例的核心責任是給 retry 敘事一個必要的反向平衡：retry 不是純反派、circuit breaker 是它的閘門。

## 觀察

Slack 官方 postmortem（2021-01-04 事故）：誘因是假期後第一個上班日「client caches are cold and clients pull down more data than usual on their first connection」、AWS Transit Gateway 未及時擴容而過載、造成「widespread packet loss」。雪上加霜：CPU 利用率下降「initially triggered some automated downscaling」（最需要容量時反而縮容）；緊急擴容撞到 Linux open files limit 與 AWS quota。復原關鍵句：「This — plus retries and circuit breaking — got us back to serving」、加上 load balancer 的 panic mode；AWS 手動加 TGW 容量後 10:40am 恢復正常。

## 判讀

retry 的雙面性：底層網路恢復後、正是 retry 加 circuit breaking 讓系統爬回服務狀態。circuit breaker 是 retry 的閘門 —— 斷路時擋住無效重試保護 provider、半開時用少量探測請求驗證恢復、恢復後 retry 才轉為復原工具。責任判讀：consumer 的 retry 是否有害、取決於 provider 當下處於「過載中」還是「恢復中」—— 而 consumer 無法直接觀測這件事、所以需要 circuit breaker 這種本地推斷機制代替猜測。

## 對應大綱

11.11 接收方重試決策章「circuit breaker 作為 retry 閘門」段、「retry 的雙面性」收束。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Slack's Outage on January 4th 2021（Slack Engineering）](https://slack.engineering/slacks-outage-on-january-4th-2021/) — 一手官方 postmortem。已 WebFetch 驗證、正文完整取回。

## 二手來源與狀態標注

事故主因是網路層（TGW）而非 API 契約層 —— 引用定位為「retry / circuit breaker 在復原期的角色」、不包裝成 API retry 風暴主案例（主案例是 C70）。
