---
title: "11.10 API 規範治理"
date: 2026-07-03
description: "設計規範怎麼讓幾十個團隊持續遵守 — 提案制、Guild 制、分軌制的治理模式比較、linting 進 CI、規範失敗的形狀"
weight: 10
tags: ["backend", "api-design", "governance"]
---

API 規範治理處理的問題在文件之外：規範寫得出來、讓幾十個團隊的 API 長得像同一家公司出的、靠的是組織機制。本章比較三種有公開一手資料的治理模式、再看規範落地的工具層與失敗的形狀。前面各章的判準（風格、錯誤、版本、冪等）都要靠這一層才能從「某個團隊的好品味」變成「組織的預設」。

## 治理模式三型

| 模式     | 代表       | 決策結構                            | 適合情境                     |
| -------- | ---------- | ----------------------------------- | ---------------------------- |
| 提案制   | Google AIP | 編號提案 + 狀態機 + 編輯團簽核      | 規範量大、需要決策可追溯     |
| Guild 制 | Zalando    | 社群 ownership + PR review + 工具鏈 | 中大型組織、貢獻文化強       |
| 分軌制   | Microsoft  | 核心 guideline + 產品線專屬軌       | 產品線差異大到蓋不進一份規範 |

**提案制**把規範做成有生命週期的提案系統。Google AIP 用編號提案累積規範、進入 Reviewing 需編輯核可、Approved 需兩位非作者 approver 簽核、TL 是 escalation 終點（見 [11.C46](/backend/11-api-design/cases/governance-google-aip-model/)）— 本質是把 IETF RFC 流程內化到單一組織、換到的是每條規範的決策可追溯、可演進。結構上仍是中心化：社群貢獻是輸入、不是決策權。

**Guild 制**的重點是規範外的配套。Zalando 在 8,000+ 服務、300+ 團隊的規模下、由 API Guild 擁有 guidelines 的 ownership、API spec 以 PR 提交 peer review、重要 API 由 Guild 介入、再加 API Portal 集中可發現性（見 [11.C47](/backend/11-api-design/cases/governance-zalando-api-first/)）。這個案例的教學價值在完整性：guidelines（文件）、Guild（人）、Zally（自動化）、Portal（可發現性）四件缺一環、規範就退化成書架文件。

**分軌制**是規模的誠實妥協。Microsoft 的 guidelines repo 內含核心軌加 Azure 與 Graph 兩條產品線專屬軌（見 [11.C48](/backend/11-api-design/cases/governance-microsoft-rest-guidelines/)）— 單一 guideline 蓋不住差異巨大的產品線、規範沿組織邊界分化。它跟 Zalando「像同一團隊設計」的理想構成一組張力：統一到什麼粒度是治理設計的自變數、不是越統一越好 — 分軌的成本是消費者跨產品線時要學兩套慣例、統一的成本是規範遷就最大公約數而失去產品線的貼合度。

## 工具層：規範進 CI

治理成本的關鍵優化是把可機檢的規則從人工 review 前移到 CI。OpenAPI 生態的代表是 Spectral（內建 OpenAPI 與 AsyncAPI rulesets、組織自帶自訂規則）跟 Zalando 的 Zally（預設 ruleset 直接執行 Zalando guidelines）；兩者的生態軌跡本身是選型訊號 — Spectral 有 8.1k dependent projects 且持續發版、Zally 的 release 停在 2022 — **通用 linter 加組織自帶 ruleset、比單一組織專用 linter 更能存活**（見 [11.C49](/backend/11-api-design/cases/governance-linting-spectral-zally/)）。protobuf 生態的對應物是 buf 的 lint 與 breaking check（[11.6](/backend/11-api-design/backward-compatibility-discipline/) 的工具層）。工具的邊界要誠實：linter 蓋得住命名、結構、必填欄位；蓋不住語意（這個資源建模合不合理）— 語意層仍回到 design review、工具的價值是讓人的注意力只花在語意上。

## 失敗的形狀：文件不會自己活著

治理缺席時規範的結局有公開的乾淨反例：White House API Standards — 內容完整的 RESTful guidelines、34 個 commit 後停止維護、2022 年正式 archived（見 [11.C54](/backend/11-api-design/cases/governance-whitehouse-api-standards-archived/)、反例）。文件品質過關、缺的是 Zalando 四件套裡的另外三件：沒有 owner、沒有 review 流程、沒有工具。跟 C47 並排的結論：**規範的存活取決於配套組織機制、不取決於文件寫得多好** — 評估自己組織的規範健康度、先問 owner 是誰、上次更新是何時、違反規範的 API 會在哪一關被擋。

## 採現成標準、還是自建規範

治理的另一個選項是直接採跨組織標準、讓別人維護規範。JSON:API 的價值主張就放在這 —「stop the bikeshedding」、用現成慣例消除團隊內的格式爭論（見 [11.C50](/backend/11-api-design/cases/standards-jsonapi-antibikeshedding/)）。反面的量尺是 OData：OASIS 標準加 ISO 認證、生態仍萎縮、Netflix 與 eBay 離場（見 [11.C51](/backend/11-api-design/cases/standards-odata-decline/)、反例、退場分析屬二手來源）— 標準機構背書不能替代生態動能、採標準前看的是 marquee adopter 與工具鏈、而非認證章。務實的中間路線是「採描述格式標準、自建設計規範」：OpenAPI 描述介面、AsyncAPI 補事件面（兩者的生態關係見 [11.C52](/backend/11-api-design/cases/standards-openapi-initiative-evolution/) 與 [11.C53](/backend/11-api-design/cases/standards-asyncapi-complement/)）、設計判準寫成自家 guidelines 配 Spectral ruleset。標準化嘗試的完整興衰史收在 styles/standards 流派層 backlog（見 [模組頁](/backend/11-api-design/)）。

## 判讀訊號

| 訊號                                  | 判讀                                                    |
| ------------------------------------- | ------------------------------------------------------- |
| 每個新 API 的 review 都在吵同樣的問題 | 規範缺位或不可發現、把重複爭論寫成 guideline 條目       |
| 有 guidelines、但新 API 明顯不遵守    | 缺執行機制、對照四件套補：owner、review、linter、portal |
| guidelines repo 一年沒 commit         | 治理已死、文件在誤導（讀者以為它反映現況）              |
| linter 規則被大量 inline 豁免         | 規則跟實際需求脫節、修規則而非繼續豁免                  |

## 下一步路由

- 相容性檢查的工具細節：[11.6 向後相容的變更紀律](/backend/11-api-design/backward-compatibility-discipline/)
- 各章判準是治理的內容物：從 [11.1](/backend/11-api-design/api-boundary-responsibility/) 依序讀
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
