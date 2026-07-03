---
title: "11.C1 Fielding 論文第 5 章：REST 是約束推導的架構風格"
date: 2026-07-03
description: "REST 由六個約束從 null style 推導而來、uniform interface 以效率換一般性；所有 REST 論爭的定義基準"
weight: 1
tags: ["backend", "api-design", "case-study", "rest"]
---

這個案例的核心責任是提供 REST 定義的一手基準、讓各流派的論證有共同錨點。

## 觀察

REST 在論文中由六個約束從 null style 逐步推導：client-server、stateless、cache、uniform interface、layered system、code-on-demand（optional）。Uniform interface 是 REST 的區別性特徵、由四個子約束構成：resource identification、manipulation through representations、self-descriptive messages、hypermedia as the engine of application state。文中明示 uniform interface 以效率為代價換取一般性與互動可見性。

## 判讀

這是所有 REST 論爭的 SSoT 錨點 — 純粹派、pragmatic 派、hypermedia 復興派都引用它。教學價值在揭露「REST 是約束集合、不是 URL + JSON + 動詞的 checklist」、並建立「約束是有 trade-off 的推導結果、不是教條」的框架。

## 對應大綱

styles/rest/「REST 語意學之爭」（定義基準）、11.3 資源建模（representation 概念來源）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Architectural Styles and the Design of Network-based Software Architectures, Chapter 5（Roy Fielding、2000）](https://roy.gbiv.com/pubs/dissertation/rest_arch_style.htm)
