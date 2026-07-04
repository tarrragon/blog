---
title: "4.C22 SRE Workbook：預寫模板、mitigation-first、活文件"
date: 2026-07-04
description: "盲飛下把不依賴當下狀態的決策提前固化：預寫溝通模板、先止血再理解、人維護的活文件替代失效儀表板"
weight: 22
tags: ["backend", "observability", "case-study"]
---

這個案例的核心責任是提供觀測退化時仍能運作的人層設計：把不依賴當下狀態的決策提前固化。

## 觀察

Google SRE Workbook 的 incident response 章：預寫溝通 —— 「prepare two or three ready-to-use templates for sharing information... No one wants to write these announcements under extreme stress」；預定通道 —— 「decide on a communication channel... beforehand—no Incident Commander wants to make this decision during an incident」；預備聯絡清單「saves critical time and effort」。決策姿態 —— 「To mitigate an incident, you don't have to fully understand the details—you only need to know the location of the root cause」。活文件 —— 「start a collaborative document that lists working theories, eliminated causes, and useful debugging information」；SRE Book 補：「The incident commander's most important responsibility is to keep a living incident document」。

## 判讀

這幾條的價值在觀測退化時被放大。儀表板能自己說話時、即席溝通還撐得住；telemetry 不可信、人得靠零碎訊號拼圖時、認知頻寬全被「判斷現況」吃掉、沒餘裕再設計溝通。預寫模板 / 預定通道 / 預備清單把「溝通這件事本身」從故障時的判斷負載裡移除。mitigation-first 承認「你不會有完整資訊」、允許先止血而非卡在「等監控告訴我發生什麼」。living document 是 telemetry 不可信時的人肉狀態機 —— working theories 由人維護、不依賴任何故障系統、工具全黑時它就是唯一的 dashboard。

## 對應大綱

觀測共命運章「人層應對」段（預固化資產、決策姿態、活文件替代儀表板）。

## 引用源

- [Incident Response（Google SRE Workbook）](https://sre.google/workbook/incident-response/) — 一手官方。已 WebFetch 驗證。
- [Managing Incidents（Google SRE Book）](https://sre.google/sre-book/managing-incidents/) — 一手官方。已 WebFetch 驗證。

## 二手來源與狀態標注

原文 framing 是「事故通用準備」、非專講「觀測退化」—— 「觀測退化時這些原則為何特別關鍵」的串接是本章推導、正文標明。活文件、角色定義與 08 事故處理章重疊、本章只截「工具退化 / telemetry 不可信」面向。
