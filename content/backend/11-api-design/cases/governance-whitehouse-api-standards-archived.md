---
title: "11.C54 White House API Standards：規範制定後棄置（反例）"
date: 2026-07-03
description: "反例：文件品質不差、但沒有 Guild / linter / review 等執行機制與持續 ownership、34 commits 後封存"
weight: 54
tags: ["backend", "api-design", "case-study", "governance"]
---

這個案例的核心責任是提供「guidelines 制定但治理缺席」的乾淨反例。

## 觀察

repo 於 2022-03 正式 archived、轉唯讀、總計僅 34 commits。內容是完整的 RESTful API guidelines（URL 結構、HTTP verbs、錯誤處理、版本策略、分頁）、README 強調平衡 RESTful 介面與 developer experience。

## 判讀

文件品質不差、但沒有 Guild / linter / review 流程等執行機制、也沒有持續的 ownership、停在 34 commits 後封存。與 Zalando 四件套（C47）並排可直接論證：規範的存活取決於配套組織機制、不取決於文件本身寫得多好。

## 對應大綱

11.10 API 規範治理（反例）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [WhiteHouse/api-standards（GitHub repo、已 archived）](https://github.com/WhiteHouse/api-standards)
