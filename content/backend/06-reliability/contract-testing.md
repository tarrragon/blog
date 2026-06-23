---
title: "6.10 Contract Testing 與 Schema 演進"
date: 2026-05-01
description: "把跨服務 / API / event schema 的隱性期待變成可驗證契約，控制演進相容性"
weight: 10
tags: ["backend", "reliability"]
---

## 概念定位

Contract testing 在服務邊界上驗證 producer 與 consumer 的相容性，把跨團隊協作的隱性期待變成可執行的[契約](/backend/knowledge-cards/contract/)。

這一頁處理的是服務邊界上的信任問題。當服務彼此頻繁演進，契約測試是避免變更互相踩踏的最小保護層。契約對準的是真實 consumer 的期待，而不是抽象的 spec 文件。

## 核心判讀

好的 contract testing 會明確劃出兼容視窗，並把驗證放進 CI 或 [release gate](/backend/knowledge-cards/release-gate/)。

判讀時看三件事：

- 契約是否對準真實 consumer，而非假想 client
- schema evolution 是否有明確 compatibility window
- 失敗是否能回到責任邊界，而非只看到測試紅燈

## Consumer-driven vs Provider-driven

契約驗證有兩個驅動方向，適用場景不同。

**Consumer-driven**：consumer 先定義對 producer 回應的期望（欄位、型別、值域），producer 驗證是否能滿足。這種做法讓驗證對準真實消費需求 — consumer 只關心它用到的欄位，producer 可以自由演進不被使用的部分。缺點是 consumer 數量多時，契約管理成本上升：每個 consumer 維護自己的契約檔，producer 需要跑所有 consumer 契約才能確認相容。

**Provider-driven**：producer 定義 API spec（OpenAPI / gRPC schema），consumer 驗證自己能否適配。producer 主導 schema 演進節奏，consumer 接收變更通知並更新。這種做法適合公開 API 或 consumer 數量大且不可控的服務。缺點是可能漏掉 consumer 依賴的隱性行為 — spec 上合規但語意變了，consumer 仍會失敗。

判斷依據：consumer 少且已知（內部微服務）→ consumer-driven；consumer 多或不可控（公開 API / 平台整合）→ provider-driven。兩者可混用：核心 consumer 用 consumer-driven 保護關鍵路徑，其他 consumer 靠 provider spec 覆蓋。

## 契約驗證的三個層次

契約驗證按深度分三層，每一層攔截不同類型的破壞。

| 層次        | 驗證內容                               | 常見工具                               |
| ----------- | -------------------------------------- | -------------------------------------- |
| Schema 結構 | 欄位是否存在、型別是否一致             | JSON Schema validation / protobuf 編譯 |
| 語意相容    | 值域、enum 範圍、nullable 語意是否對齊 | Pact interaction / custom assertion    |
| 向後相容性  | 新版輸出能否被舊版 consumer 解析       | Avro compatibility check / Buf         |

**Schema 結構**是最基礎的防線。欄位缺失或型別錯誤會直接導致 runtime 解析失敗。這一層成本低、回饋快，適合放在 CI fast path。

**語意相容**攔截的是「schema 通過但行為不同」的問題。例如某個欄位從 nullable 改成 required，或 enum 新增一個值但 consumer 的 switch 沒有 default branch。這類問題在結構層驗證不出來，需要 consumer 定義語意期望（Pact interaction 的 matcher / assertion）。

**向後相容性**是跨版本共存的保障。Avro 和 Protobuf 有內建 compatibility mode（backward / forward / full）；JSON Schema 需要外部工具（如 json-schema-diff）做版本比較。向後相容性驗證的成本最高，但能攔截最嚴重的破壞 — 一旦 event 寫入 [broker](/backend/knowledge-cards/broker/)，舊版 consumer 就必須能解析它。

## Schema 演進規則

Schema 演進按協議類型有不同的安全邊界。

### API schema（OpenAPI / gRPC）

API schema 的演進判讀：新增可選欄位通常安全；移除欄位、重新命名欄位、或把可選改成必填是 breaking change；型別變更（如 int32 → int64）視 consumer 的容忍度而定。gRPC 的 field number 機制讓欄位新增與移除的相容性比 JSON 更明確 — 未知 field number 被忽略，已知 field number 被刪除會觸發 default value，兩者都有可預測行為。

### Event schema（Avro / Protobuf / JSON Schema）

Event schema 的相容性要求比 API 更嚴格。API 的 breaking change 可以靠 versioning（`/v2/`）隔離，event 一旦寫入 broker 就跟所有版本的 consumer 共存。backward compatibility（新 schema 能讀舊資料）是最低要求；forward compatibility（舊 schema 能讀新資料）讓 consumer 可以延遲升級。

Schema registry（Confluent Schema Registry / AWS Glue Schema Registry）提供集中式的相容性 gate：producer 註冊新版 schema 前，registry 自動比對相容性規則，拒絕 breaking change。這個 gate 比 CI 更早攔截，因為它在 schema 發布時就生效。

DB schema 演進的契約驗證銜接到 [6.11 migration safety](/backend/06-reliability/migration-safety/) — expand/contract pattern 讓新舊版本共存，本質上跟 event schema 的 backward compatibility 是同一個問題。

## CI 整合

Contract test 在 CI 的位置跟 unit test 不同 — 需要跨服務的契約同步。

**Fast path**：producer 的 schema 變更觸發 consumer 的 contract test。實作上需要 CI 能跨 repo 觸發（webhook / pipeline trigger），或用 contract broker（如 Pact Broker）做非同步驗證。fast path 只跑受影響 consumer 的契約，保持回饋速度。

**Slow path**：完整 contract matrix 驗證 — 所有 consumer × producer 組合。這個矩陣在 merge gate 或 scheduled path 跑，覆蓋 fast path 漏掉的間接影響。矩陣規模隨服務數增長，需要 selective matrix（只跑有變更的 producer 相關 consumer）控制成本。

**失敗處理**：contract test 失敗時的責任分派是關鍵流程。失敗可能來自 producer 的 breaking change，也可能來自 consumer 的 expectation 過期。Pact 的 can-i-deploy 機制提供自動化判斷：比對 producer 當前版本與 consumer 上次驗證通過的版本，定位責任方。

## 案例對照

- [Stripe](/backend/06-reliability/cases/stripe/idempotency-and-zero-downtime-migration/)：外部整合的 API 需要嚴格的 backward compatibility — 交易 API 的 breaking change 會直接影響商戶收入，schema 演進靠 expand/contract 逐步過渡。
- [Shopify](/backend/06-reliability/cases/shopify/bfcm-capacity-and-game-day/)：跨服務 deploy 順序錯誤是高峰期常見事故源 — contract test 攔截 schema 不相容，讓 deploy 順序有驗證依據。
- [GitHub](/backend/08-incident-response/cases/github/)：API 與 webhook 的契約覆蓋面廣，契約失配會直接影響整合生態。

## 判讀訊號

| 訊號                                       | 判讀條件                                                       | 行動建議                                        |
| ------------------------------------------ | -------------------------------------------------------------- | ----------------------------------------------- |
| 跨服務 deploy 順序錯誤導致 production 故障 | contract test 應在 CI 攔截相容性問題，deploy 順序才有驗證依據  | 補 contract test 到 CI fast path                |
| API 文件跟實作漂移、新接入服務出意外       | provider-driven spec 需要自動化 diff 偵測，手動更新會漂移      | 接 OpenAPI diff 工具到 CI、spec 變更自動 PR     |
| event schema 變更後下游 consumer 解析失敗  | schema registry 的 compatibility gate 應在 publish 前攔截      | 啟用 schema registry 的 compatibility check     |
| breaking change 靠 release note 標註       | 標註是通知、contract test 是攔截，兩者責任不同                 | 加 CI contract gate 攔截 breaking change        |
| contract 違規只在 staging 才發現           | contract test 應在 CI fast path 跑，staging 發現代表 CI 沒覆蓋 | 把 contract test 從 staging 提前到 CI push 觸發 |

## 交接路由

- [6.1 CI pipeline](/backend/06-reliability/ci-pipeline/)：contract test 作為 fast path 的跨服務驗證
- [6.8 release gate](/backend/06-reliability/release-gate/)：contract 通過作為放行條件
- [6.11 migration safety](/backend/06-reliability/migration-safety/)：DB schema 演進的契約驗證
- [6.14 dependency budget](/backend/06-reliability/dependency-reliability-budget/)：依賴契約穩定性
- [6.15 environment parity](/backend/06-reliability/environment-parity/)：契約覆蓋的環境邊界
- [6.16 test data](/backend/06-reliability/test-data-management/)：fixture shape 契約
- [6.17 feature flag](/backend/06-reliability/feature-flag-governance/)：flag 不同分支的契約覆蓋
- [05 部署](/backend/05-deployment-platform/)：跨服務 deploy 順序協調
