---
title: "11.6 向後相容的變更紀律"
date: 2026-07-03
description: "哪些變更算 breaking、相容性檢查放人工還是 CI、檢查粒度怎麼選 — 讓介面變更可審可擋的日常紀律"
weight: 6
tags: ["backend", "api-design", "compatibility"]
---

向後相容的變更紀律回答一個高頻的日常問題：這個 diff 能不能直接上。版本策略（[11.5](/backend/11-api-design/versioning-and-deprecation/)）處理「決定要 breaking 之後怎麼辦」、本章處理更前面的一層 — 怎麼在每次變更時判定它 break 不 break、以及這個判定由人還是由工具把關。

## Breaking 的定義要明文、且比直覺寬

變更紀律的地基是一份「什麼算 breaking」的明文清單、而且清單的範圍比直覺預期的寬。直覺抓得到的：刪欄位、改型別、改必填。直覺常漏的：改欄位預設值（消費者依賴舊預設）、改錯誤碼（消費者的分支邏輯建在上面）、改回應時序（輪詢邏輯依賴）、收緊驗證規則（昨天合法的請求今天 400）。反向的參照是 Stripe 明文的相容變更清單 — 新增資源、新增 optional 參數、新增 response property、property 順序改變、opaque ID 的長度格式改變、新增 event type（見 [11.C11](/backend/11-api-design/cases/versioning-stripe-named-major-releases/)）：清單同時劃出「這些軸服務端保留自由」、消費者不可依賴。兩份清單（breaking 清單、相容清單）合起來才是完整的契約邊界、只有其中一份時灰色地帶照樣存在。

## 紀律的三個放置層：格式、工具、流程

相容紀律可以放在三個層、強度遞減、適用情境不同。

**格式層**：相容性做成編碼格式的性質、違規在技術上不可行或立即失效。protobuf 是代表 — field number 一旦投入使用即不可變更、刪除必須 reserve、重用會造成解碼歧義與資料損毀（見 [11.C28](/backend/11-api-design/cases/grpc-protobuf-field-number-discipline/)）；官方文件直接把 schema 變更分成 wire-safe、wire-unsafe 與 conditionally wire-compatible 三類 — 判定規則明文化之後、不依賴資深工程師在場。GraphQL 的 versionless 紀律同型、案例判讀把它歸納為三個支柱：只加不改、deprecation 標注、nullable 預設、由 schema 語言承載（C26 的判讀整理、觀察層見 [11.C26](/backend/11-api-design/cases/graphql-versionless-evolution/)；GraphQL 內部機制的深化見 [Schema 演進](/backend/11-api-design/styles/graphql/graphql-schema-evolution/)）。

**工具層**：相容檢查做成 CI gate、在 merge 前擋下。Buf 的 breaking detection 對比歷史 schema、在 merge 前擋下破壞性變更、規則分四級（FILE、PACKAGE、WIRE_JSON、WIRE）、文件明言「Catching this before merge is the point」（見 [11.C29](/backend/11-api-design/cases/grpc-buf-breaking-detection/)）。從四級的分級設計可以抽出選級判準（C29 判讀）：選符合消費者實際依賴的等級 — 只走 wire 的消費者用 WIRE、有 generated code 依賴的要更嚴的級。這條主張可以推廣成本章的通用判準：**相容性檢查的粒度是產品決策、不是工具預設** — 檢查太嚴、內部重構寸步難行；太鬆、消費者實際依賴的層沒被保護。HTTP+JSON 的對應工具是 OpenAPI diff 類檢查、把 spec 當 schema 跑同樣的 gate（工具治理見 [11.10 規範治理](/backend/11-api-design/api-governance/)）。

**流程層**：格式與工具都蓋不到的語意變更（預設值、時序、驗證規則）、由變更審查流程把關 — review checklist 上有「對照 breaking 清單」一項、重大變更走 API design review。流程層是三層裡唯一蓋得住全部變更類型的、也是唯一依賴人自覺的 — 所以務實的配置是三層疊加：格式層鎖結構、工具層鎖 spec、流程層鎖語意。

## 到期與豁免的邊界設計

紀律需要兩個邊界條款才能長期運作。**到期行為**：宣告過的 breaking 變更到期執行時、回明確錯誤而非靜默改語意 — 原則的完整推導與 Facebook Graph v1.0 的反例展開見 [11.1 的違約模式段](/backend/11-api-design/api-boundary-responsibility/)；審查視角的增量是把到期行為當成變更提案的必填欄位、跟 brownout 這類預告機制（見 [11.C13](/backend/11-api-design/cases/versioning-github-password-auth-brownout/)）一起在 review 時就定案、而非退場當天即興。**豁免宣告**：每次變更公告要明列「誰不受影響」— GitHub 的密碼認證廢止同時明列 2FA 使用者、GHES、GitHub App 不受影響、讓多數消費者第一段就能停止閱讀、注意力留給真正要動的人。

## 判讀訊號

| 訊號                                    | 判讀                                                  |
| --------------------------------------- | ----------------------------------------------------- |
| 「這算不算 breaking」在 review 裡反覆吵 | 缺明文清單、先立清單、吵架轉為修清單                  |
| 相容性事故的變更當初過了 CI             | 檢查粒度低於消費者實際依賴的層、對照 buf 四級思路重選 |
| 內部重構常被相容檢查誤擋                | 檢查粒度高於任何消費者依賴的層、同上反向調整          |
| 消費者依賴了相容清單裡宣告可變的性質    | 契約已明文、屬消費者責任、但值得檢討清單的傳達位置    |

四個訊號的排查有方向性：前一個的修法是後三個的前提 — 清單沒立好、CI 粒度沒有校準對象；粒度爭議反覆出現、多半是清單跟消費者依賴的實況脫節。從清單開始修、工具與流程的爭論通常跟著消失。

## 下一步路由

- Breaking 決定要做之後的分期與退場：[11.5 版本策略與 deprecation](/backend/11-api-design/versioning-and-deprecation/)
- 消費端驗證（consumer-driven contract test 把「誰依賴什麼」顯性化）：[6.10 契約測試](/backend/06-reliability/contract-testing/)
- 相容檢查工具進 CI 的組織面：[11.10 API 規範治理](/backend/11-api-design/api-governance/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
