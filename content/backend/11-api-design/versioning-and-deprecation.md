---
title: "11.5 版本策略與 deprecation"
date: 2026-07-03
description: "版本方案怎麼選（URI/header/date-based）、支援窗口怎麼承諾、舊版怎麼安全退場 — 承諾分期與回收的操作設計"
weight: 5
tags: ["backend", "api-design", "versioning"]
---

版本策略是承諾的分期方式：介面要演進、消費者要穩定、版本機制決定兩者的張力由誰、在什麼時點、付出什麼成本來吸收。同一家公司的答案會隨規模演進 — Stripe 2011 年起用日期滾動版本、2017 年公開轉換層設計、現行方案又演進成具名 major release 加月度相容 release（[11.C10](/backend/11-api-design/cases/versioning-stripe-rolling-date-versions/) 與 [11.C11](/backend/11-api-design/cases/versioning-stripe-named-major-releases/) 是同一策略的兩個時間切片）— 版本策略是活的設計、不是上線前勾一次的選項。

## 版本擺哪裡：URI、header、日期

版本識別的三個主流位置、差異在「版本被當成什麼」：

| 方案           | 形式                               | 版本的語意             | 代表          |
| -------------- | ---------------------------------- | ---------------------- | ------------- |
| URI 版本       | `/v1/orders`                       | 版本是資源身分的一部分 | 業界大量存在  |
| header 版本    | `X-GitHub-Api-Version: 2022-11-28` | 版本是內容協商         | GitHub（C12） |
| date-based pin | 帳號 pin 首次呼叫日、header 可覆寫 | 版本是消費者的屬性     | Stripe（C10） |

URI 版本的優勢是可見性：版本寫在每個請求上、curl 就能切版、快取與路由基礎設施天然按版本分流。代價是「v2」的粒度太粗 — 整個 API 一起翻版、消費者面對的是大遷移、服務端面對的是雙版本長期並行的維護。

header 與 date-based 把版本移出資源身分、版本粒度可以細到單一 breaking change。GitHub 2022 年為 REST API 引入 calendar versioning 時同步給了承諾結構：新版釋出後舊版至少支援 24 個月（見 [11.C12](/backend/11-api-design/cases/versioning-github-calendar-versioning/)）— 支援窗口從隱性期待變成 SLA 式的明文契約、消費者可以據此排遷移計畫。Stripe 的 date-based pin 更進一步：帳號自動 pin 住首次呼叫時的版本、服務端把每個 breaking change 封裝成一個 version change module、response 依時間反向流過模組鏈、轉換成該帳號 pin 住版本的回應 schema — 截至 2017 年累積約 100 個 backwards-incompatible 升級、維持與 2011 年以來每一版相容（見 [11.C10](/backend/11-api-design/cases/versioning-stripe-rolling-date-versions/)；這種「服務端吸收」的成本分配框架見 [11.1](/backend/11-api-design/api-boundary-responsibility/)）。

選型判準回到 11.1 的成本分配：消費者多而異質、值得投資 header / date-based 加服務端吸收層；消費者少而可協調、URI 版本的簡單性划算。另一派主張版本化本身是錯的 — Fielding 的立場是「DON'T」、用 hypermedia 的執行期演化取代版本號（InfoQ 訪談、2014、見 [11.C14](/backend/11-api-design/cases/versioning-fielding-no-versioning/)）；GraphQL 的 versionless 路線是這個方向的工程化實例（見 [11.C26](/backend/11-api-design/cases/graphql-versionless-evolution/)）。兩者的完整交鋒收在掛本章的「版本策略流派之爭」爭論文章 backlog（見 [模組頁](/backend/11-api-design/)）。

## Deprecation 的執行工具箱

宣告 deprecation 容易、讓長尾消費者實際完成遷移才是工程問題。公開案例累積出一組執行工具、各自解決通訊鏈的不同斷點：

**分階段日期**。Slack 收斂四族舊 API 到 Conversations API 時用三個日期各擋一種風險：宣告日起算、五個月後新建 app 拿不到舊方法（掐斷新增量）、十三個月後全面停用（處理存量）（見 [11.C16](/backend/11-api-design/cases/versioning-slack-conversations-api-sunset/)）。先斷增量再清存量的順序讓債務停止成長、清理才有終點。

**In-band warning**。同一案例的過渡期、呼叫舊方法會在 response 收到 `method_deprecated` warning 加退場日期 — 訊號出現在開發者一定會看的地方（自己的 response）、觸及率高於任何公告渠道。

**Brownout**。GitHub 廢止 Git 操作密碼認證前、在兩個預告時窗暫時停用再恢復（見 [11.C13](/backend/11-api-design/cases/versioning-github-password-auth-brownout/)）— 沒讀公告的長尾消費者、只有短暫的真實故障能觸達、且是在低風險時窗先遭遇明確失敗、不是在強制日全面斷線。

**Sunset header**。RFC 8594 定義用 HTTP header 宣告退場時點的機器可讀層（見 [11.C15](/backend/11-api-design/cases/versioning-sunset-header-rfc8594/)）— Informational 地位、實務採用有限、Slack 與 GitHub 都沒等它。引用價值是概念完整性：通訊鏈該有一層給程式讀、具體形式各家自選。

工具的組合邏輯：公告觸及會讀公告的人、in-band warning 觸及在開發的人、brownout 觸及所有人。退場計畫的完整度檢查是「三類人各被哪個工具覆蓋」。

## 退場的量測與到期行為

退場決策要有數據：舊版的呼叫量、呼叫方分布、衰減曲線。量測的基礎設施跟 [04 觀測](/backend/04-observability/) 共用、版本維度要進 metrics label。到期行為的設計原則承接 [11.1 的違約模式分析](/backend/11-api-design/api-boundary-responsibility/)：到期回明確錯誤、而非靜默改變語意 — Facebook Graph v1.0 的靜默語意切換反例在該段完整展開。

版本策略運作不良的訊號可以從三個地方讀：舊版呼叫量長期不衰減（deprecation 工具箱沒有形成遷移壓力）、多數帳號 pin 死在首版（新能力的價值不足以驅動升級、或遷移成本被低估）、每次退場都演變成客訴事故（通訊鏈有一類消費者始終沒被覆蓋）。三個訊號指向的修法分別是執行工具、版本內容、通訊覆蓋 — 對症下藥、而非一律延長支援期。

## 下一步路由

- 什麼算 breaking、變更怎麼審：[11.6 向後相容的變更紀律](/backend/11-api-design/backward-compatibility-discipline/)
- 承諾成本結構的上游框架：[11.1 API 作為服務邊界的責任](/backend/11-api-design/api-boundary-responsibility/)
- 退場量測的觀測基礎：[04 可觀測性平台](/backend/04-observability/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
