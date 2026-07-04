---
title: "REST 流派：這個歧義詞的選型用法、hypermedia 的適用邊界"
date: 2026-07-03
description: "REST 在選型溝通裡是歧義詞、本目錄給使用判準：怎麼把詞說死、hypermedia 落在哪個消費者形狀、成熟度模型怎麼當定位工具"
weight: 1
tags: ["backend", "api-design", "rest"]
---

REST 是選型溝通裡歧義最大的詞：它有明確的原始定義（Fielding 的六約束、含 HATEOAS —— 可用操作編碼在回應裡、client 不靠外部文件就能導航）、業界最通行的 JSON-over-HTTP 用法卻跟原義相距甚遠。本目錄不重述這個歧義的來龍去脈、只給三件在 design review 裡直接可用的使用判準、以及 hypermedia 與成熟度模型的適用邊界。中性建模判準見 [11.3 資源建模與操作語意](/backend/11-api-design/resource-modeling-operation-semantics/)。

## 把 REST 這個詞用對的三個判準

- **跨團隊溝通時把詞說死**：「REST」在 API design review 裡指涉不明確、規範文件（[11.10 治理](/backend/11-api-design/api-governance/) 的 guidelines）該明文定義自家用法。多數組織的誠實寫法是「HTTP+JSON、資源導向、Richardson Level 2」、而非裸的 RESTful。
- **判別線當設計問句用**：「這個 client 需要多少 out-of-band 知識才能操作」是好問題 —— client 需要外部文件才知道怎麼呼叫、就通不過 Fielding 意義的 REST（這條判別線出自 [11.C2](/backend/11-api-design/cases/rest-fielding-hypertext-driven/)）。無論最終選哪一側、這條問句都幫你把設計講清楚。
- **引用要對版本**：拿 Fielding 支持自家 URL 命名慣例、引到的多半是業界慣行而非原義（原義是六約束推導、HATEOAS 是其中一環、跟命名慣例無關、見 [11.C1](/backend/11-api-design/cases/rest-fielding-dissertation-ch5/)）。寫 style guide 時這類錯位引用很常見、值得回一手來源核對。

| 文章                                                                                                     | 主題                                              | 案例支撐   |
| -------------------------------------------------------------------------------------------------------- | ------------------------------------------------- | ---------- |
| [Hypermedia 與 HATEOAS 的適用邊界](/backend/11-api-design/styles/rest/hypermedia-hateoas-revival/)       | consumer 是誰決定方向、格式標準化的現實、適用邊界 | C4-C8、C14 |
| [Richardson 成熟度的實用讀法](/backend/11-api-design/styles/rest/richardson-maturity-practical-reading/) | 分級階梯當定位工具、不當合規認證                  | C3         |
