---
title: "Read Model"
tags: ["read-model", "cqrs", "repository"]
date: 2026-07-16
description: "查詢該由 repository 回 aggregate、還是該有自己的查詢側模型時使用。read model 是為讀需求的形狀而建的模型——回答「畫面需要什麼形狀」、與 aggregate 的形狀分離。"
weight: 14
---

read model 是為讀需求的形狀而建的查詢側模型：畫面或報表要什麼形狀（統計值、扁平列表、跨 aggregate 拼裝）、它就長什麼形狀。repository 回傳 [aggregate](/ddd/knowledge-cards/aggregate-root/) 的形狀、守一致性邊界；read model 回傳讀的形狀、不承擔寫入責任。兩者的分工判準是一句自檢問句：「這個查詢回傳的是讀的形狀、還是 aggregate 的形狀」。讀側的介面宣告是一種 [port](/ddd/knowledge-cards/port/)——同樣以領域語言表達、由查詢方的需要定義形狀。

## 概念位置

read model 是 CQRS 讀寫分離的讀側，與 [aggregate root](/ddd/knowledge-cards/aggregate-root/) 的寫側形成互補：aggregate 守一致性邊界、read model 服務讀的形狀。它的存在不以 CQRS 全套為前提——讀側是一道階梯：消費端自行投影、讀 port 抽離（獨立的 [port](/ddd/knowledge-cards/port/)）、專用投影、事件同步的獨立儲存，每一階都是 read model 概念的某種深度。低階的 read model 可以只是 ViewModel 裡幾行 `map`；高階的 read model 有自己的儲存與更新節奏，接受與寫側的最終一致性。階梯橫跨 ephemeral（ViewModel 內聯投影，沒有獨立生命週期）到 durable（獨立儲存、事件同步），但各階共享同一個設計責任——「讀的形狀由讀需求定義、不由 aggregate 形狀決定」——因此視為同一概念的深度變體。

## 可觀察訊號

repository 介面長出回傳統計值、分頁切片、反正規化投影的方法，是讀的形狀開始混進 aggregate 介面的訊號。反向的訊號同樣可觀察：還沒有第二條讀需求就先建投影層，抽象沒有消費者、每個新查詢多穿一層介面。

## 設計責任

read model 定義「讀側要什麼形狀」，升級到哪一階由訊號決定、不由架構偏好決定——五個升級訊號（讀需求增生、形狀偏離、負載分歧、新鮮度分級、獨立演進）與階梯各階的代價，教學層展開見 [讀模型的升級判準](/ddd/read-model-upgrade-signals/)。
