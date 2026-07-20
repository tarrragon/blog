---
title: "Testing 知識卡片"
date: 2026-06-19
description: "測試策略相關的術語卡片索引"
weight: 91
tags: ["testing", "knowledge-cards"]
---

測試策略教學中出現的關鍵術語卡片。每張卡片說明一個語意責任，跨情境變義的概念拆成獨立卡片。

| 卡片                                                                                     | 概念群            | 一句話定位                                            |
| ---------------------------------------------------------------------------------------- | ----------------- | ----------------------------------------------------- |
| [Protocol Integration Test](/testing/knowledge-cards/protocol-integration-test/)         | 測試分層          | 驗證協議契約（transport 層）的測試層級                |
| [Mock 遮蔽](/testing/knowledge-cards/mock-masking/)                                      | 測試分層          | mock 跳過協議層與環境層造成的結構性盲區               |
| [名義 Integration Test](/testing/knowledge-cards/nominal-integration-test/)              | 測試分層          | 名為 integration 實為 mock 的測試型態辨識             |
| [Screen State Test](/testing/knowledge-cards/screen-state-test/)                         | 測試分層          | 驗證畫面狀態覆蓋度與轉換完整性的測試層級              |
| [Consumer-Driven Contract Test](/testing/knowledge-cards/consumer-driven-contract-test/) | 測試分層          | 後端不可寫入或跨團隊維護時，用契約取代協議整合測試    |
| [語意級假後端](/testing/knowledge-cards/semantic-fake-backend/)                          | 假後端 + 流程測試 | 持有狀態、只固化已證實行為的測試假件                  |
| [流程測試](/testing/knowledge-cards/flow-test/)                                          | 假後端 + 流程測試 | 在假後端上驅動真實服務鏈的跨服務業務旅程驗證          |
| [真實後端驗證測試](/testing/knowledge-cards/real-backend-verification-test/)             | 假後端 + 流程測試 | 對共用測試環境常駐斷言後端行為、承接假後端漂移警報    |
| [Stub](/testing/knowledge-cards/stub/)                                                   | Test Double 分類  | 測試作者寫死回應資料，驗證不出後端行為假設本身的錯誤  |
| [Test Double Taxonomy](/testing/knowledge-cards/test-double-taxonomy/)                   | Test Double 分類  | dummy / stub / spy / mock / fake 五種角色的分野與選用 |
| [Fire-and-forget 編排](/testing/knowledge-cards/fire-and-forget-orchestration/)          | 測試設計          | 呼叫後不等待完成的編排形態，flaky test 常見根因之一   |
| [凍結參照與活解析](/testing/knowledge-cards/frozen-vs-live-reference/)                   | 測試設計          | 下游持有上游 id 的兩種策略，凍結版在上游重建後失效    |
| [Skip vs Fail Semantics](/testing/knowledge-cards/skip-vs-fail-semantics/)               | 測試設計          | 跳過與失敗兩種訊號各自對應的成因類別與處置路徑        |
| [Characterization Test](/testing/knowledge-cards/characterization-test/)                 | 重構安全網        | 鎖住現有行為的測試，用於 legacy 重構前的安全網        |
| [Quarantine](/testing/knowledge-cards/quarantine/)                                       | 團隊治理          | 把已知 flaky 測試隔離觀察、保留回收壓力的機制         |
| [測試環境判定](/testing/knowledge-cards/environment-identification/)                     | 測試基礎設施      | 防止自動化測試對生產環境執行的誤擊防護前提            |
