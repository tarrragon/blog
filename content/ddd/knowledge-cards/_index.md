---
title: "Knowledge Cards"
tags: ["前置知識卡片", "Knowledge Cards"]
date: 2026-07-10
description: "DDD 教學章節引用的領域建模術語：用原子化卡片建立共同語言"
weight: -1
---

本模組的知識卡片把領域建模的高密度術語拆成可獨立閱讀的概念索引。教學章節（[資料袋與領域模型](/ddd/data-bag-vs-domain-model/)、[entity 與 value object 的判準](/ddd/entity-vs-value-object/)、[不變式的強制層次](/ddd/invariant-enforcement-layers/)、[狀態轉換與稽核軌跡](/ddd/state-transition-and-audit-trail/)、[建構路徑設計](/ddd/construction-path-design/)、[組裝層的可達性](/ddd/composition-root-reachability/)、[觀測出口的職責三分](/ddd/observation-outlet-responsibility-split/)、[讀模型的升級判準](/ddd/read-model-upgrade-signals/)、[domain event 與狀態流](/ddd/domain-event-vs-state-stream/)、[domain event 與命令、查詢](/ddd/domain-event-vs-command-and-query/)）遇到術語時連到對應卡片；卡片先回答概念本質、再放設計責任——讓讀者先知道該概念在領域模型裡承擔什麼責任。

## 術語建卡判準

建卡判準是教學需求：讀者若缺少某個術語的知識就難以理解教材章節，這個術語就值得建卡。出現頻率與是否影響實作判斷都只是補充訊號、不參與「是否要建卡」的必要判準。

## 核心概念

| 卡片                                                                               | 核心問題                                                    |
| ---------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| [Invariant](/ddd/knowledge-cards/invariant/)                                       | 業務規則落在文件層、型別層還是執行層                        |
| [Entity](/ddd/knowledge-cards/entity/)                                             | 同一性由身份定義——操作需不需要 identity-based 回寫          |
| [Value Object](/ddd/knowledge-cards/value-object/)                                 | 同一性由內容定義——語意封閉與合法運算集合                    |
| [Aggregate Root](/ddd/knowledge-cards/aggregate-root/)                             | 對外代表一組資料一致性的邊界物件                            |
| [Data Bag](/ddd/knowledge-cards/data-bag/)                                         | 欄位組合全部合法、沒有不變式要守的型別                      |
| [Snapshot](/ddd/knowledge-cards/snapshot/)                                         | 某一時刻的狀態複本——歷史不隨現在漂移                        |
| [Port](/ddd/knowledge-cards/port/)                                                 | domain 對外宣告的介面——依賴方向為何朝內                     |
| [Adapter](/ddd/knowledge-cards/adapter/)                                           | port 的具體實作——技術細節被擋在六角形之外的位置             |
| [Composition Root](/ddd/knowledge-cards/composition-root/)                         | 應用程式唯一的組裝起點——DI、路由、事件接線集中處            |
| [Dependency Injection](/ddd/knowledge-cards/dependency-injection/)                 | 依賴由誰提供——建構與使用分成兩個責任                        |
| [Test Seam](/ddd/knowledge-cards/test-seam/)                                       | 不修改本體就能替換行為的位置——mock 從哪裡換進去             |
| [Wiring Test](/ddd/knowledge-cards/wiring-test/)                                   | 零 override 驗組裝——port 插上 adapter 的唯一證言            |
| [Placeholder](/ddd/knowledge-cards/placeholder/)                                   | 先立介面後補實作的中間態——失效比文件層約束更靜默            |
| [Read Model](/ddd/knowledge-cards/read-model/)                                     | 為讀需求的形狀而建的查詢側模型——與 aggregate 形狀分離       |
| [Domain Event](/ddd/knowledge-cards/domain-event/)                                 | 已發生的業務事實——過去式、不可變、錯過代表事實遺失          |
| [State Stream](/ddd/knowledge-cards/state-stream/)                                 | 資料當前值的連續觀測——新值蓋舊值、錯過無代價                |
| [Observation Outlet](/ddd/knowledge-cards/observation-outlet/)                     | repository 的「資料變了」推送能力——pull 介面的 push 對應    |
| [Repository](/ddd/knowledge-cards/repository/)                                     | aggregate 的存取抽象——回傳的是 aggregate 形狀、不是讀的形狀 |
| [Bounded Context](/ddd/knowledge-cards/bounded-context/)                           | 模型與詞彙保持一致的邊界——邊界內的推導在邊界外不必然成立    |
| [EventBus](/ddd/knowledge-cards/event-bus/)                                        | 行程內的發布／訂閱事件匯流排——只解決送達、不承擔涵蓋保證    |
| [CQRS](/ddd/knowledge-cards/cqrs/)                                                 | 讀寫模型拆開的架構決定——是階梯的頂端、不是二選一的開關      |
| [Event-Carried State Transfer](/ddd/knowledge-cards/event-carried-state-transfer/) | 事件攜帶足量當前狀態、讓下游免回頭查詢來源的跨服務設計      |
