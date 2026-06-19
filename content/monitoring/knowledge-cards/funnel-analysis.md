---
title: "Funnel Analysis"
date: 2026-06-19
description: "說明追蹤使用者在多步驟流程中每一步的轉換率和流失率的分析方法"
weight: 1
tags: ["monitoring", "analytics", "funnel", "knowledge-card"]
---

Funnel analysis 的核心概念是「追蹤使用者在多步驟流程中每一步的轉換率和流失率」。每一步有多少使用者完成、多少使用者離開，構成漏斗形狀的轉換圖。可先對照 [cohort analysis](/monitoring/knowledge-cards/cohort-analysis/)（按群組比較留存）和 [RFM](/monitoring/knowledge-cards/rfm/)（按行為分群）。

## 概念位置

Funnel analysis 位在行為資料收集之後、產品決策之前。它的輸入是 event 類監控事件（使用者操作記錄），輸出是每步的轉換率。Funnel analysis 的前提是去識別化（[redaction](/monitoring/knowledge-cards/redaction/)）已完成 — 分析行為資料前必須確保資料不含可識別個人的敏感欄位。

## 可觀察訊號與例子

產品需要 funnel analysis 的訊號是「使用者在某個流程中的完成率低於預期，但不知道卡在哪一步」。註冊流程的轉換率從填寫 email 到完成驗證只有 30%，funnel analysis 揭露 60% 的使用者在「等待驗證信」步驟流失。

## 設計責任

Funnel analysis 要定義步驟順序、步驟之間的時間窗口（使用者在多久內完成下一步才算轉換）、以及分群維度（按平台、來源、使用者類型拆分 funnel）。步驟定義需要和事件命名規範對齊 — funnel 的每一步對應一個具體的事件名稱。
