---
title: "4.C18 Datadog 2023：觀測廠商自己掛、客戶 monitors 停止告警"
date: 2026-07-04
description: "monitoring-as-a-dependency 的純粹形態：把「我有沒有事」外包給單一觀測供應商、供應商跨區同時更新一起垮"
weight: 18
tags: ["backend", "observability", "case-study"]
---

這個案例的核心責任是提供「觀測作為外部依賴、且可能是共享單點」的一手實證。

## 觀察

Datadog 官方 outage postmortem（2023-03-08）：客戶側觀測全失能 —— 「users could not access the platform or various Datadog services via the browser or APIs and monitors were unavailable and not alerting」；「Data ingestion for various services was also impacted at the beginning of the outage」；規模達「tens of thousands of nodes」。根因是一個自動套用的 systemd 安全更新讓「systemd-networkd forcibly deleted the routes managed by the Container Network Interface (CNI) plugin (Cilium)」、更新視窗跨區同時觸發、打到多個本應獨立的部署。

## 判讀

這是「觀測作為外部依賴」的純粹形態：客戶把「我的系統有沒有事」外包給 Datadog、當 Datadog 自己 down、客戶的 monitors「unavailable and not alerting」—— 觀測層變成客戶事故的放大器（客戶系統可能沒事但看不到、或有事但沒被叫醒）。根因「更新視窗跨區同時」是 correlated failure 的教科書：以為獨立的多個部署共享同一個觸發器。設計含義：關鍵告警不能只有單一觀測供應商這一條路徑、需要 meta-monitoring 或第二條獨立通道（dead man's switch、外部 synthetic、見 [4.C19](/backend/04-observability/cases/watchdog-dead-mans-switch/)）。

## 對應大綱

觀測共命運章「失效模式」段（monitoring as a dependency、meta-monitoring 缺口）。

## 引用源

- [2023-03-08 Multiregion connectivity issue（Datadog 官方 postmortem）](https://www.datadoghq.com/blog/2023-03-08-multiregion-infrastructure-connectivity-issue/) — vendor 一手官方。已 WebFetch 驗證。

## 二手來源與狀態標注

這是觀測廠商自身的失效（跟 4.C16 被觀測系統反噬觀測後端機制不同）—— 撐的是「觀測是獨立失效域、且可能是共享單點」這條軸、分節時勿與 4.C16 混寫。
