---
title: "Fault Domain（故障域）"
date: 2026-10-24
description: "建立 Oracle Cloud 主機時看到 fault domain 欄位、要讓同一個服務的幾台主機不落在同一組實體硬體上，或所在區域只有一個可用區、要找可用區以外的隔離手段時，查故障域的範圍、它防的事件與各家對應的放置政策"
weight: 64
tags: ["infra", "knowledge-cards", "cloud", "availability"]
---

故障域（fault domain）在這張卡上指 Oracle Cloud 建立主機時選的那個隔離單位：一個 [Availability Zone（可用區）](/infra/knowledge-cards/availability-zone/) 內部的一組實體硬體與基礎設施。它是 [Failure Domain（失效域）](/backend/knowledge-cards/failure-domain/) 這個一般概念的一種業者實作：失效域是會因同一個原因一起停掉的元件集合，Oracle Cloud 把可用區內的硬體組直接命名為 fault domain。Oracle Cloud 的每個可用區有三個故障域，官方說明它防的是兩種事件：某一組硬體的非預期故障，以及業者對那一組硬體做的計畫性維護。一個故障域受影響時，放在其他故障域的主機不受影響。

## 概念位置

故障域提供的是反親和性（anti-affinity）：把幾台主機刻意放在不同的實體硬體上，讓一次硬體事件不會讓它們同時停擺。它比[可用區](/infra/knowledge-cards/availability-zone/)小一層——可用區隔離的是整棟資料中心的電力與網路，故障域隔離的是同一棟裡的機櫃與實體主機。

Oracle Cloud 以「故障域」這個名稱讓使用者在建立主機時直接選；AWS 與 Google Cloud 沒有對應的欄位名稱，同一個效果用放置政策取得：AWS 的 placement group（spread 策略）、Google Cloud 的 spread placement policy，作用都是讓一組主機分散到不同的實體硬體上。AWS 要先停止主機才能換進或移出 placement group，Google Cloud 可以把政策套用到既有的主機上。

只有一台主機時，故障域沒有選擇的意義，那台主機總是只在一組硬體上。Oracle Cloud 建立頁的預設「讓 Oracle 選擇」會依當下容量挑一個，而手動指定會縮小可用的容量。

## 可觀察訊號

- 建立主機時收到 `Out of host capacity`：Oracle Cloud 的 Compute〈Known Issues〉頁列的處置之一是不指定 fault domain 再建一次，因為指定故障域等於只接受那一個故障域裡的硬體，可用容量跟著變小
- 同一個服務的兩台主機在主機詳細資訊裡顯示同一個 `FAULT-DOMAIN-<N>`：一次硬體維護可能同時重開兩台
- `oci iam availability-domain list` 只回傳一筆：這個區域只有一個可用區，跨可用區做不到，故障域是同一個區域內剩下的硬體隔離手段

## 設計責任

- **同一個服務兩台以上的主機**：區域有多個可用區時先分到不同可用區，故障域用在同一個可用區之內；區域只有一個可用區時，分散到不同故障域。Oracle Cloud 允許建立之後再修改故障域
- **只有一個可用區的區域**：高可用的設計從跨可用區改成跨故障域，並接受整個可用區故障時服務會停的風險，或另外跨區域
- **單一台主機**：維持讓業者選

## 鄰卡

- [Availability Zone（可用區）](/infra/knowledge-cards/availability-zone/) — 故障域上面那一層的隔離單位
- [Managed Instance Group（MIG，代管執行個體群組）](/infra/knowledge-cards/managed-instance-group/) — 一組主機自動分散與修復的機制
- [位置：區域、可用區與故障域](/infra/cloud-providers/vm-options/placement/) — 建立主機時這三層選項的取捨
