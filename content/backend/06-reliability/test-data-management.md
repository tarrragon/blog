---
title: "6.16 Test Data Management"
date: 2026-05-01
description: "把 fixture / seed / production-like data 作為跨模組共用 artifact，治理資料層次、遮罩策略與可重現性"
weight: 16
tags: ["backend", "reliability"]
---

## 概念定位

測試常常失敗在資料而非邏輯 — fixture 過期、seed 跟 schema 漂移、staging 資料分佈跟 production 差太遠。Test data management 把 fixture、seed 與 production-like data 當成共用資產來治理，讓測試建立在可控且可重播的資料基礎上。

## 核心判讀

Test data 的健康度先看資料是否足夠代表真實情境，再看資料是否能安全重建與清理。

關鍵判準：

- fixture 是否覆蓋關鍵情境，而不是只有 happy path
- seed 是否可版本化與重播
- production-like data 是否完成去識別化與權限隔離
- data lifecycle 是否和 CI / migration / contract testing 互相對齊

## 資料層次

測試資料按用途分四層，每層的責任、治理成本與真實度不同。

| 層次              | 生命週期           | 真實度 | 治理成本 |
| ----------------- | ------------------ | ------ | -------- |
| Unit fixture      | 跟 test case 綁定  | 低     | 低       |
| Integration seed  | 跟 test suite 綁定 | 中     | 中       |
| Staging dataset   | 長期存在於環境中   | 中高   | 高       |
| Production sample | 定期從 prod 抽樣   | 高     | 最高     |

**Unit fixture** 是硬編碼或 factory-generated 的資料，不碰外部系統。fixture 的責任是提供可控的輸入與預期輸出，讓 unit test 驗證邏輯正確性。fixture 覆蓋 happy path 與 edge case，但不反映 production 資料分佈 — 這是設計取捨，因為分佈驗證的責任在更高層次。

**Integration seed** 寫進真實 DB / [broker](/backend/knowledge-cards/broker/) / cache，生命週期跟 test suite 綁定（setup 建立、teardown 清理）。seed 需要版本化，跟 [schema migration](/backend/knowledge-cards/schema-migration/) 對齊 — 見下方「可重現性與版本化」段。seed 品質的判準是：它是否能讓 integration test 驗證跨服務邊界的行為，而不是只驗證資料是否存在。

**Staging dataset** 長期存在於 staging 環境，模擬 production 規模與分佈。這一層的挑戰是漂移：production 的資料結構、量體與分佈持續變化，staging dataset 需要定期更新才能維持代表性。更新頻率跟 schema 變更頻率對齊 — 每次重大 schema 變更後，staging dataset 應同步重建。

**Production sample（脫敏）** 從 production 抽樣加 PII masking，是真實度最高的選項。它的價值在於保留真實資料的分佈、關聯與邊界條件 — 這些是 synthetic data 很難完整模擬的。代價是隱私風險與合規成本，需要遮罩管線、存取控制與定期稽核。連到 [07 資料保護](/backend/07-security-data-protection/)。

## 遮罩與合成策略

當測試需要接近 production 的資料，PII 處理策略決定了安全性與真實度的平衡。

| 策略                         | 原理                             | 適用場景                   | 限制                           |
| ---------------------------- | -------------------------------- | -------------------------- | ------------------------------ |
| Tokenization                 | PII 替換成無意義 token、保留格式 | 需要 referential integrity | token mapping 本身需要安全儲存 |
| Format-preserving encryption | 保留原始格式但值不可逆           | 需要格式驗證（信用卡位數） | 加密強度受格式限制             |
| Synthetic generation         | 用規則或統計模型生成假資料       | 無 PII 風險、合規最簡單    | 資料分佈可能偏移               |

Tokenization 適合需要跨表關聯的場景：同一個 user ID 在 order、payment、session 表中需要一致替換，referential integrity 才不會被破壞。format-preserving encryption 適合需要通過格式驗證的場景（信用卡號通過 Luhn check）。synthetic generation 最安全，但資料分佈偏移會讓某些測試結論失真 — [Pinterest 的快取可靠性案例](/backend/06-reliability/cases/pinterest/cache-reliability-and-capacity-surprises/)說明資料分佈差異會改變 cache 命中率，進而改變瓶頸位置。

三者的選擇取決於測試需要的真實度與隱私風險。多數團隊會混合使用：unit fixture 用 synthetic、integration seed 用 tokenization、staging dataset 用 production sample + format-preserving encryption。

## 可重現性與版本化

Seed 資料需要版本化，跟 schema migration 對齊。當 DB schema 新增欄位或改型別，既有 seed 如果沒同步更新，integration test 會因資料問題失敗而非邏輯問題 — 這類 failure 的除錯成本高，因為錯誤訊息指向 schema 不符，團隊會懷疑是 migration bug 還是 seed bug。

**Seed migration** 是把 seed 更新綁進 schema migration workflow 的做法：每次 DB migration 加一份對應的 seed migration。這讓 seed 狀態跟 schema 狀態同步演進，CI 跑 integration test 時永遠拿到匹配的組合。

**Fixture factory** 用 factory pattern 生成測試資料，讓新增欄位自動帶 default。factory 的優勢是欄位變更只需改 factory 定義，不需要手動更新每個 fixture file — 這在高頻 schema 變更的服務中可以顯著降低 fixture 維護負擔。

**資料清理** 策略決定 integration test 的隔離性。transaction rollback 最乾淨（每個 test case 跑在 transaction 內、結束後 rollback），但不適用於跨 transaction 的流程測試。truncate 較快但需要處理外鍵順序。獨立 DB per suite 隔離最強但成本最高 — 每個 test suite 用自己的 database instance。選擇時對齊 CI 的隔離需求（連到 [6.1 CI pipeline](/backend/06-reliability/ci-pipeline/) 的 environment 隔離段）。

## Fixture 與 contract testing 的整合

[Contract testing](/backend/06-reliability/contract-testing/) 定義 schema shape，fixture factory 可以用 contract 作為資料生成的來源。當 contract 變更時（新增欄位、型別調整），fixture factory 自動更新生成邏輯，讓 test data 跟 contract 保持同步。

這個整合的價值是把「契約變更是否影響測試資料」從人工 review 變成自動化流程。[Stripe 的交易正確性實踐](/backend/06-reliability/cases/stripe/idempotency-and-zero-downtime-migration/)對此有額外要求：交易路徑的 test data 需要能重播到相同狀態，確保 [idempotency](/backend/knowledge-cards/idempotency/) 驗證的資料基礎一致。

## 案例對照

- [Pinterest](/backend/06-reliability/cases/pinterest/cache-reliability-and-capacity-surprises/)：資料分佈差異改變 cache 命中率與瓶頸位置，staging dataset 若分佈偏離 production，壓測結論會失真。
- [Stripe](/backend/06-reliability/cases/stripe/idempotency-and-zero-downtime-migration/)：交易資料需要嚴格控制可重播性，fixture 與 seed 要能產出一致的 idempotency 驗證結果。

## 判讀訊號

| 訊號                                         | 判讀條件                                                                  | 行動建議                                       |
| -------------------------------------------- | ------------------------------------------------------------------------- | ---------------------------------------------- |
| 工程師為 debug 把 production data 拷到 local | PII 暴露風險 — 需要遮罩管線而非直接複製                                   | 建立遮罩 pipeline、禁止直接複製 production DB  |
| staging DB 含真實用戶 PII                    | 合規風險 — 需要用 tokenization 或 synthetic 替代                          | 導入 tokenization 工具或 synthetic generation  |
| fixture 跟 schema 漂移、測試常壞             | seed migration 未跟 schema migration 對齊                                 | 每次 schema migration 同步更新 seed 版本       |
| 新測試靠拷貼舊 fixture                       | 缺少 fixture factory — 變更範圍模糊、維護成本累積                         | 導入 factory pattern 自動帶 default            |
| production bug 重現不出                      | staging dataset 分佈跟 production 差異太大 — 需更新或用 production sample | 定期用脫敏 production sample 更新 staging data |

## 交接路由

- [6.1 CI pipeline](/backend/06-reliability/ci-pipeline/)：test data 如何進入 fast / slow stage
- [6.10 contract testing](/backend/06-reliability/contract-testing/)：contract 定義 fixture shape
- [6.11 migration safety](/backend/06-reliability/migration-safety/)：seed migration 跟 schema migration 對齊
- [6.15 environment parity](/backend/06-reliability/environment-parity/)：production-like data 是 parity 的一部分
- [07 資料保護](/backend/07-security-data-protection/)：PII 遮罩與最小揭露
