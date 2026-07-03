---
title: "11.C47 Zalando API-first：Guidelines、Guild、Zally、Portal 四件套"
date: 2026-07-03
description: "規範存活靠配套組織機制：文件、人的治理、自動化、可發現性缺一環就退化成書架文件"
weight: 47
tags: ["backend", "api-design", "case-study", "governance"]
---

這個案例的核心責任是展示「規範文件 + 執行機制」的完整治理系統。

## 觀察

Guidelines repo 開宗明義「Great RESTful APIs look like they were designed by a single team」、CC-BY 4.0、約 3.2k stars、自述為 living document。Engineering blog 描述治理配套：8,000+ 服務、300+ 團隊規模下、API Guild（API 愛好者與架構師組成）擁有 guidelines 的 ownership、所有人可貢獻；API spec 以 PR 提交 peer review、重要 API 由 Guild 介入審查；另有 API Portal 集中所有已部署服務的 spec。核心哲學是 API-as-a-Product / API-First。

## 判讀

Guidelines（文件）、Guild（人的治理）、Zally（自動化）、Portal（可發現性）構成完整系統 — 缺一環都會退化成書架文件。Guild 模式介於中心化委員會與完全去中心之間：ownership 集中、貢獻開放、適合跟 Google 編輯團制（C46）對照。

## 對應大綱

11.10 API 規範治理（anchor）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Zalando RESTful API and Event Guidelines（GitHub repo）](https://github.com/zalando/restful-api-guidelines)
- [Developing Zalando APIs（Zalando engineering blog、2019）](https://engineering.zalando.com/posts/2019/04/developing-zalando-apis.html)
