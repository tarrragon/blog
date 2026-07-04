---
title: "採現成格式標準還是自建規範"
date: 2026-07-03
description: "採現成 response 格式標準買到什麼、綁定什麼、以及怎麼在採用前預測一個標準會不會活下去"
weight: 1
tags: ["backend", "api-design", "standards"]
---

採現成的 response 格式標準（JSON:API 這類）省的是組織成本：團隊不用再為「JSON 回應該長什麼樣」開會吵、也能重用圍繞該標準的工具。自建規範換到的是貼合自己資料形狀的自由、代價是要自己維護規範與治理。這道選擇題比的是這兩筆帳、不是技術能力 —— 多數格式標準做得到的事、一份認真的自建規範也做得到。本文先講採現成標準各買到與綁定什麼、再回答一個更難的問題：一個格式標準會不會活下去、怎麼在採用前就看出來。（本文的 response 格式指 JSON body 的結構慣例；binary 格式如 Protobuf、hypermedia 格式如 HAL／Siren 在別層、後者見 [REST 流派層](/backend/11-api-design/styles/rest/)。）

## 採現成標準買到的是組織成本

JSON:API 把價值主張直接寫在組織成本上。官網開宗明義：如果團隊曾為 JSON 回應怎麼格式化吵過架、JSON:API 能讓你停止這種 bikeshedding（為瑣碎細節沒完沒了地爭）（見 [11.C50](/backend/11-api-design/cases/standards-jsonapi-antibikeshedding/)）。它賣的不是更強的格式能力、而是一個大家都同意的現成慣例 —— 附帶好處是圍繞這個慣例的工具可以重用、client 端也能靠標準化的結構做快取、有時省掉一次網路請求。

採現成標準的代價相對隱性：response 形狀從此綁在該標準的設計上、標準沒覆蓋的需求要嘛繞、要嘛回頭自建。JSON:API 的版本節奏很慢（1.1 距 1.0 約七年）—— 這既可讀成 spec 穩定、也可讀成演進動能有限。採用前要自己判：這個「慢」對你是保障、還是把你綁在一份不太會跟上新需求的格式上。response 的結構驗證是正交的另一層 —— JSON Schema 這類工具管「回應符不符合約定的形狀」、跟選哪個 response 格式標準是兩件事、選了 JSON:API 不代表驗證也一併有了。

## 怎麼預測一個標準會不會活

一個標準的正式化程度、不能拿來預測它會不會活。OData 是這條判準最清楚的反例：它是 OASIS 標準、還拿到 ISO/IEC 認證、正式化程度在同類裡最高、主流採用卻不成比例（見 [11.C51](/backend/11-api-design/cases/standards-odata-decline/)、退場分析為二手來源）。Netflix 低調關掉 OData catalogue、eBay 同步棄用 —— 招牌級採用者（marquee adopter）的離場、比任何標準機構的背書都更能預測一個標準會不會活。生態才是存活的變數、認證徽章不是。

OData 退場還有更深一層、而且直接是使用層判準：它的設計把 repository 幾乎直通到 wire（對外的網路傳輸層）、自動生成 generic 查詢介面、暴露資料庫內部結構。這種「magic box」跟「API 是刻意設計的對外契約」的治理理念正面衝突 —— 採一個會把 DB 內部直通出去的標準、等於在這一層放棄了契約設計。所以判斷一個格式標準能不能採、除了看生態、還要看它逼你交出多少契約控制權。

## 採、自建、還是採一部分

三個問題把這道選擇題收斂。團隊會不會為格式反覆爭論、又需要現成工具生態 —— 會、採現成標準的組織成本節省就有買家。response 需求特不特殊、有沒有治理量能維護自建規範 —— 需求夠標準又沒有治理量能、自建規範會退化成沒人遵守的文件、還不如採現成的。這個標準的生態在長還是在縮 —— 看 marquee adopter 的進出、不看認證；看它逼你交出多少契約控制權、不看 feature 清單有多長。

這三題的答案不必指向同一邊。務實的常見解是採一份現成標準的子集當對外骨架、內部保留自建的擴充空間 —— 既拿到「停止爭論」的組織成本節省、又不把特殊需求鎖死在別人的格式設計裡。這道「採標準 vs 自建規範」的選擇、在組織治理層的完整判準見 [11.10 API 規範治理](/backend/11-api-design/api-governance/)。

## 下一步路由

- 採標準 vs 自建的治理層判準：[11.10 API 規範治理](/backend/11-api-design/api-governance/)
- 描述 API 形狀的格式標準怎麼選：[描述格式的選型：OpenAPI 與 AsyncAPI](/backend/11-api-design/styles/standards/standards-description-formats/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
