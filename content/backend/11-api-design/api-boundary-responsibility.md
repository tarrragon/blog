---
title: "11.1 API 作為服務邊界的責任"
date: 2026-07-03
description: "介面變更該由誰付成本、哪些介面性質算對外承諾、承諾違約有哪些形狀 — 動手設計 endpoint 前的責任框架"
weight: 1
tags: ["backend", "api-design", "contract"]
---

API 設計的核心責任是管理一組對外承諾的成本結構。服務內部的實作可以隨時重構、成本收在自己團隊；對外語意一旦被消費者依賴、每次變更都要付出跨組織的遷移協調成本。這個不對稱決定了 API 設計的所有下游議題：版本策略在決定承諾怎麼分期、相容紀律在決定承諾怎麼守、錯誤模型在決定失敗時承諾什麼。本章建立這個責任框架；框架本身是從 [案例庫](/backend/11-api-design/cases/) 跨案例合成的推導、非單一案例原文。

## 承諾的範圍比 schema 大

對外承諾的範圍涵蓋所有消費者觀察得到、且會寫進程式碼依賴的介面性質 — 欄位與型別只是最顯眼的一層。錯誤碼、HTTP status 的使用慣例、欄位預設值、回應時序、分頁行為、ID 字串的長度與格式、甚至欄位在 JSON 裡的順序、都可能被某個消費者拿去依賴。這個現象有個常被引用的名字：Hyrum's Law — 使用者夠多時、介面的每個可觀察行為都會被某人依賴、無論你有沒有承諾過。

契約邊界的有效管理方式是把「消費者不可依賴的性質」明文寫出來、而非留給雙方猜。Stripe 的 upgrade 文件明列什麼算 backwards-compatible 變更：新增資源、新增 optional 參數、新增 response property、property 順序改變、opaque string（object ID、可長到 255 字元）的長度與格式改變、新增 event type（見 [11.C11](/backend/11-api-design/cases/versioning-stripe-named-major-releases/)）。這份清單的作用是雙向的：服務端保留了這些軸上的變更自由、消費者拿到了「寫 client 時什麼不能 hardcode」的明確指引。缺少這種明文劃界時、每個未宣告的性質都處於灰色地帶 — 服務端改了算誰的錯、只能事後吵。

## 變更成本的兩種分配設計

承諾確立之後、變更成本的分配有兩種本質設計：由服務端吸收、或攤給所有消費者。這是版本策略章（模組頁章節規劃的版本策略與 deprecation 主題）背後的經濟結構、在本章先建立判讀框架。

服務端吸收的極端案例是 Stripe 的轉換層：每個 breaking change 封裝成一個 version change module、response 依時間反向流過模組鏈、轉換成該帳號 pin 住的版本形狀 — 截至 2017 年累積約 100 個 backwards-incompatible 升級、同時維持與 2011 年以來每一版相容（見 [11.C10](/backend/11-api-design/cases/versioning-stripe-rolling-date-versions/)）。這個設計把變更成本一次收在服務端的基礎設施投資裡、換來的是消費者幾乎永遠不被迫遷移。

攤給消費者的設計則以「版本 + 遷移窗口」的形式出現：服務端宣告新版、給一段支援期、到期消費者必須完成遷移。成本較低、但把協調負擔外部化 — 適合消費者數量有限、或平台對生態有強制力的情境。兩種設計的選擇判準是消費者的數量、異質性、跟你對他們的控制力：內部服務間的 API 可以直接協調升級、公開平台的十萬個 integration 只能靠承諾與窗口。

## 承諾違約的形狀

違約的傷害大小跟違約的「形狀」有關、明確的失敗優於靜默的行為改變。Facebook Graph API v1.0 退場時、到期的 v1.0 請求被靜默改以 v2.0 語意處理、而非回傳明確錯誤 — v2.0 移除了 friends 資料等大範圍權限、未遷移的 app 不會炸在認證層、而是拿到形狀不同的資料默默壞掉（見 [11.C17](/backend/11-api-design/cases/versioning-facebook-graph-v1-forced-upgrade/)、反例）。對照組是明確錯誤：消費者立刻知道、監控立刻報警、修復路徑清楚。設計退場行為時的判準是「消費者發現問題的延遲」— 靜默切換把發現延遲拉到不可控、明確錯誤把它壓到第一個請求。

## 判讀訊號

| 訊號                                     | 判讀                                               |
| ---------------------------------------- | -------------------------------------------------- |
| 消費者回報「你們沒改版但行為變了」       | 有未明文的介面性質被依賴、契約劃界不完整           |
| 團隊內對「這個改動要不要發版本」反覆爭論 | 缺「什麼算 breaking」的明文清單、先補清單再談流程  |
| 改一個欄位要跨三個團隊開會               | 變更成本已攤給消費者、評估是否值得投資服務端吸收層 |
| 消費者停在舊版不動、新功能推不出去       | 遷移壓力設計缺位、看 11.5 的 deprecation 執行工具  |

這些訊號的共同根因是承諾範圍或成本分配沒有被當成明確的設計對象。修法從明文化開始：先有相容變更清單、再有版本與退場政策、最後才是工具。

## 邊界

本章的框架適用於「有外部消費者」的介面 — 外部指組織邊界或部署邊界之外、修正代價無法用一次 refactor 收掉的情境。同一個 repo 內、同一次部署一起上線的模組間介面、變更成本結構完全不同、用內部重構紀律處理即可、套用本章框架是過度設計。

## 下一步路由

- 選風格與建模：[11.2 風格選型總覽](/backend/11-api-design/api-style-selection/)、[11.3 資源建模與操作語意](/backend/11-api-design/resource-modeling-operation-semantics/)
- 承諾怎麼分期、什麼算 breaking：版本策略與變更紀律兩章（[模組頁](/backend/11-api-design/) 章節規劃 backlog）
- 契約的驗證手段（consumer-driven contract test）：[06 契約測試](/backend/06-reliability/contract-testing/)
- 名詞層：[API Contract](/backend/knowledge-cards/api-contract/)、[Contract](/backend/knowledge-cards/contract/) 知識卡
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
