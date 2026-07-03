---
title: "11.C48 Microsoft REST Guidelines：單一 repo 內的分軌治理"
date: 2026-07-03
description: "規範沿組織邊界分化的實況：Core / Azure / Graph 三軌並存、跟「像同一團隊設計」理想的張力"
weight: 48
tags: ["backend", "api-design", "case-study", "governance"]
---

這個案例的核心責任是提供大型組織規範分軌的實況證據。

## 觀察

repo 含三條 guidance track：核心 `Guidelines.md`、`/azure` 資料夾（Azure 服務團隊專用）、`/graph` 資料夾（Microsoft Graph 團隊專用）。約 23.3k stars、vNext 分支 949 commits、CC-BY 4.0。README 自述目的包含「fostering dialogue and learning in the API community at large」、鼓勵其他組織發展自己的 guidelines。

## 判讀

同一組織內分軌（Core vs Azure vs Graph）證明單一 guideline 無法覆蓋差異巨大的產品線、規範會沿組織邊界分化 — 跟 Zalando「像同一團隊設計」的理想（C47）形成有用的張力。公開 repo 加對外喊話也顯示大廠把內部規範開源當成社群影響力工具。

## 對應大綱

11.10 API 規範治理（anchor、治理模式比較的第三型）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Microsoft REST API Guidelines（GitHub repo）](https://github.com/microsoft/api-guidelines)
