---
title: "4.C24 PagerDuty Customer Liaison：客訴的雙向 out-of-band 管道"
date: 2026-07-04
description: "專責角色把客戶回報聚合成 IC 可用的 scope 訊號、把確認過的狀態往外送；never lie never guess 在盲飛時尤其關鍵"
weight: 24
tags: ["backend", "observability", "case-study"]
---

這個案例的核心責任是把客訴訊號制度化成雙向管道：訊號進、狀態出。

## 觀察

PagerDuty 官方 Customer Liaison 角色定義：「the primary individual in charge of notifying our customers of the current conditions, and informing the Incident Commander of any relevant feedback from customers as the incident progresses」；職責含「Monitor the incident call, Slack room, and incoming support requests」。回報範例：「We've had 6 customers call so far and say they haven't received notifications for the last several minutes」幫 IC 判斷調查優先序與範圍。溝通紀律：「Never lie, and never guess. Work with the incident commander if you are unsure as to what is actually happening」。

## 判讀

Customer Liaison 把散落的客訴制度化成一個雙向 out-of-band 管道：一邊把 incoming support requests 聚合成 IC 可用的 scope 訊號（「6 個客戶說沒收到通知」在監控失效時就是 blast-radius 的量測）、一邊把 IC 確認過的狀態往外送。「never guess」在工具退化時尤其關鍵 —— 當內部都不確定發生什麼、對外溝通只講確認的、不猜 ETA、避免把盲飛狀態變成錯誤承諾。這條把 4.C23 的散訊號變成有人負責的通道。

## 對應大綱

觀測共命運章「人層應對」段（制度化的雙向客戶管道）。

## 引用源

- [Customer Liaison（PagerDuty 官方 incident response）](https://response.pagerduty.com/training/customer_liaison/) — 一手官方。已 WebFetch 驗證。

## 二手來源與狀態標注

PagerDuty 這頁是通用 IR 角色、非專講「觀測退化」—— 本章只抽「客訴聚合成 scope 訊號」對接工具退化約束。完整角色定義與指揮鏈屬 08 事故處理章。
