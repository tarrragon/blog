---
title: "4.C17 GitLab 2017：告警靜默失效、儀表板被事故流量壓垮"
date: 2026-07-04
description: "備份失敗的通知信被 DMARC 拒收、沒人知道觀測已死；事故時公開監控頁被同一波流量壓垮 — 兩層共命運"
weight: 17
tags: ["backend", "observability", "case-study"]
---

這個案例的核心責任是提供觀測靜默失效與儀表板容量共命運的一手實證。

## 觀察

GitLab 官方 database outage postmortem（2017-01-31）：告警靜默失效 —— cronjob error 的通知走 email、但「DMARC was not enabled for the cronjob emails, resulting in them being rejected by the receiver」、結果「This means we were never aware of the backups failing, until it was too late」。被觀測對象已空：去找 `pg_dump` 備份時「they were not there」、「The S3 bucket was empty」。事故中對外儀表板被壓垮：「the current setup for this website was not able to handle the load produced by users using this service during the outage」（指其公開監控 dashboard）。

## 判讀

兩層共命運：告警管道（email 加未驗證的 DMARC）跟被監控對象共享同一個沒人測過的假設 —— 沒人驗證告警本身會不會送達、於是觀測靜默死亡直到災難才發現；事故發生時大量使用者湧向公開監控頁、觀測前端在它最該提供資訊的時刻被同一波事故流量壓垮。設計含義：告警管道要有 meta-監控（告警本身有沒有送達要被監控、對應 dead man's switch，見 [4.C19](/backend/04-observability/cases/watchdog-dead-mans-switch/)）、觀測前端的容量要獨立於事故流量域。

## 對應大綱

觀測共命運章「失效模式」段（觀測靜默失效 + 儀表板容量共命運）。

## 引用源

- [Postmortem of database outage of January 31（GitLab 官方）](https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/) — 一手官方 postmortem。已 WebFetch 驗證。

## 二手來源與狀態標注

本篇主軸是備份 / 複製失效、觀測失效是其中一環 —— 引用時框成「觀測前端容量共命運」的佐證、不誇大成整場事故都因觀測而起。
