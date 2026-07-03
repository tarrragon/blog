---
title: "11.C49 Spectral 與 Zally：guidelines 變成可執行檢查"
date: 2026-07-03
description: "治理成本從人工 review 前移到 CI；通用 linter 加組織 ruleset 比單一組織專用 linter 更能存活"
weight: 49
tags: ["backend", "api-design", "case-study", "governance"]
---

這個案例的核心責任是說明規範 machine-checkable 化的工具譜系與工具治理的選型訊號。

## 觀察

Spectral 是 JSON / YAML linter、內建 OpenAPI 2.0 / 3.0 / 3.1、AsyncAPI 2.x、Arazzo 1.0 rulesets、支援自訂 rule / function、整合 GitHub Actions、git hooks、IDE、CI pipeline；約 3.1k stars、8.1k dependent projects、2026-06 仍在發版、README 列 Adidas / Azure / Box / Zalando 的實際 ruleset。Zally 是 Zalando 的 OpenAPI linter、預設 ruleset 直接執行 Zalando guidelines、提供 API / CLI / Web UI 三介面；最近 release 停在 2022-12。

## 判讀

規則寫成 machine-checkable ruleset、在設計期給 early feedback、把治理成本從人工 review 前移到 CI — 這是 guidelines 落地的關鍵一步。Spectral 的 8.1k dependents 對比 Zally 的停滯顯示：「通用 linter 加組織自帶 ruleset」比「單一組織專用 linter」更能存活、是工具治理選型的判讀訊號。

## 對應大綱

11.10 API 規範治理（linting 進 CI 段、anchor）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [stoplightio/spectral（GitHub repo）](https://github.com/stoplightio/spectral)
- [zalando/zally（GitHub repo）](https://github.com/zalando/zally)
