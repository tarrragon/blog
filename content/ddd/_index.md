---
title: "DDD 領域驅動設計指南"
date: 2026-07-10
description: "領域模型的理論與判準層：一袋欄位還是領域模型、什麼時候值得建 entity、不變式該落在哪一層強制、狀態轉換怎麼留下稽核軌跡、建構路徑怎麼設計。語言無關，實作限制路由到各語言模組。"
weight: 34
tags: ["ddd", "domain-model", "architecture", "design"]
---

DDD 是一種設計精神：把業務規則放進領域模型、讓違反規則的路徑走不通，而不是寫在文件裡請大家遵守。這句話是本模組的源頭句——各章的判準都要能折算回它。這個精神在每種語言會碰到不同的實作限制——Dart 的 copyWith 生態、Go 的零值與組合、TypeScript 的 structural typing——所以本模組只承擔理論與判準層，語言特定的實作細節放在各語言模組，章節末路由過去。判準的敘述以物件導向語言為主要載體；函數式生態的對應形態（opaque type、smart constructor、module 可見性）判準相同、強制的載體不同。

## 與其他教材的分工

| 教材                     | 承擔什麼                                       | 本模組的關係                   |
| ------------------------ | ---------------------------------------------- | ------------------------------ |
| [Backend](/backend/)     | 服務能力層：資料庫、快取、佇列等跨語言後端能力 | DDD 談模型設計、Backend 談選型 |
| [Flutter](/flutter/)     | Dart / Flutter 的語言與框架實作限制            | 本模組理論的 Dart 實作對照     |
| [Go](/go/)               | Go 語言精神與工程實踐                          | 本模組理論的 Go 實作對照       |
| [UX Design](/ux-design/) | 畫面狀態設計                                   | 畫面狀態機與領域狀態機的邊界   |

路由方向是單向的：本模組的理論不依賴任何語言實作作為理解前提；語言模組引用本模組建立概念地基。

## 學習路線

已成章的部分有一條主梯：型別的入口判準 → 身份與內容 → 規則落點 → 變更路徑 → 建構路徑 → 組裝層；讀側、觀測與事件另成一支：觀測出口 → 讀模型 → 事件與狀態流 → 事件與命令、查詢。這一支四章共用同一條 meta 判準——歸屬由事物自身的本質決定（介面看表達語言、查詢看回傳形狀、通知看時態語意、訊息看責任結構），不由需求來源或現成系統的方便性決定。依目的四條路線：

| 路線         | 適合情境                                                  | 建議順序                                                                                                                                                                                                                                                                                                                                            | 讀完能做什麼                                                                   |
| ------------ | --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| 模型設計主梯 | 從零建立領域模型的設計判準                                | [資料袋與領域模型](/ddd/data-bag-vs-domain-model/) → [entity 與 value object 的判準](/ddd/entity-vs-value-object/) → [不變式的強制層次](/ddd/invariant-enforcement-layers/) → [狀態轉換與稽核軌跡](/ddd/state-transition-and-audit-trail/) → [建構路徑設計](/ddd/construction-path-design/) → [組裝層的可達性](/ddd/composition-root-reachability/) | 能判定一個型別要不要模型化、規則落哪層、變更與建構路徑怎麼收斂、組裝怎麼驗     |
| 讀側與觀測   | 畫面刷新靠補償、repository 長滿查詢方法、事件被當刷新訊號 | [觀測出口的職責三分](/ddd/observation-outlet-responsibility-split/) → [讀模型的升級判準](/ddd/read-model-upgrade-signals/) → [domain event 與狀態流](/ddd/domain-event-vs-state-stream/) → [domain event 與命令、查詢](/ddd/domain-event-vs-command-and-query/)                                                                                     | 能判定變更通知的三層歸屬、讀側該停在階梯哪一階、事件對狀態流／命令／查詢的邊界 |
| 測試證言     | 測試全綠但功能失聯、驗收條款設計                          | [組裝層的可達性](/ddd/composition-root-reachability/) → [不變式的強制層次](/ddd/invariant-enforcement-layers/) → 各章「下一步」對應的 work-log case                                                                                                                                                                                                 | 能區分行為測試與接線測試的證言範圍、把可達性寫進 use case 完成定義             |
| 術語地基     | 讀章節前先補共同語言                                      | [knowledge cards](/ddd/knowledge-cards/) → 回模型設計主梯                                                                                                                                                                                                                                                                                           | 能用卡片語言描述模型設計的責任分佈                                             |

## 章節大綱（backlog）

大綱是 backlog、不是承諾清單：章節邊界會隨 case 回補調整。候選章節從兩個專案的 case（書籍管理 App 的開發日誌、POS App 的領域模型）浮現：

| 候選章節                                                             | 核心問題                                                                              | 已有素材                                                                                                                                                                                                                                                                                                |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [資料袋與領域模型](/ddd/data-bag-vs-domain-model/)                   | 什麼時候一袋欄位就夠、什麼時候需要有行為的模型                                        | [copyWith 是逃生口](/work-log/dart_copywith_entity_escape_hatch/)、[同一個品項、四個 model](/work-log/dart_pos_item_four_lifecycle_models/)、[扁平 Product 到雙層聚合](/work-log/pos_product_model_doc_vs_code_evolution/)                                                                              |
| [entity 與 value object 的判準](/ddd/entity-vs-value-object/)        | 同一個概念的「同一個」由什麼定義——操作需不需要 identity-based 回寫                    | [同一個品項、四個 model](/work-log/dart_pos_item_four_lifecycle_models/)、[Money 三段遷移](/work-log/dart_money_extension_type_migration/)、[分層 enum](/work-log/dart_payment_dual_layer_enum/)、[跨邊界參照的生命週期](/work-log/pos_cross_boundary_reference_lifecycle/)                             |
| [不變式的強制層次](/ddd/invariant-enforcement-layers/)               | 約束落在文件層、型別層、執行層的差異與代價                                            | [copyWith 是逃生口](/work-log/dart_copywith_entity_escape_hatch/)、[會員/計價/支付原子切換](/work-log/pos_member_pricing_payment_atomic_switch/)、[Exception 分類不變式](/work-log/flutter_exception_error_category_invariant/)、[驗證的兩層分工](/work-log/flutter_domain_input_validation_placement/) |
| [狀態轉換與稽核軌跡](/ddd/state-transition-and-audit-trail/)         | 領域方法作為唯一變更路徑、稽核軌跡出洞的靜默機制與凍結端點                            | [copyWith 是逃生口](/work-log/dart_copywith_entity_escape_hatch/)、[同一個品項、四個 model](/work-log/dart_pos_item_four_lifecycle_models/)、[單調狀態機與樂觀更新回滾](/work-log/pos_monotonic_status_optimistic_rollback/)                                                                            |
| [建構路徑設計](/ddd/construction-path-design/)                       | 工廠表達力不足時缺陷如何被逃生口吸收、原始值的官方出口                                | [copyWith 是逃生口](/work-log/dart_copywith_entity_escape_hatch/)、[VO 封裝擺盪](/work-log/flutter_value_object_encapsulation_oscillation/)                                                                                                                                                             |
| [組裝層的可達性](/ddd/composition-root-reachability/)                | domain 全對、系統不可用——composition root 的測試證言與可達性強制                      | [測試全綠、功能失聯](/work-log/flutter_composition_root_wiring_gap/)                                                                                                                                                                                                                                    |
| [觀測出口的職責三分](/ddd/observation-outlet-responsibility-split/)  | repository 的變更通知橫跨三層時、契約/機制/組裝各歸誰——歸屬由介面語言決定、非需求來源 | [ref.watch 觀察的是 provider 圖](/work-log/flutter_riverpod_reactive_boundary_ref_watch/)、[StreamProvider 包 repository watch stream](/work-log/flutter_streamprovider_wraps_repository_watch/)                                                                                                        |
| [讀模型的升級判準](/ddd/read-model-upgrade-signals/)                 | 讀側階梯該爬到哪一階——五訊號與自檢問句「讀的形狀還是 aggregate 的形狀」               | [觀測出口案例停在第一階的決策](/work-log/flutter_riverpod_reactive_boundary_ref_watch/)、[mock 55 個方法只用 5 個](/work-log/flutter_port_interface_mock_hell_isp/)、[自持狀態與可導出狀態](/work-log/pos_held_vs_derived_state_migration/)                                                             |
| [domain event 與狀態流](/ddd/domain-event-vs-state-stream/)          | 離散事實與連續觀測的載體分界——消費者問「發生了什麼」還是「現在是什麼」                | [ref.watch 觀察的是 provider 圖](/work-log/flutter_riverpod_reactive_boundary_ref_watch/)、[Domain Event 命名的過去式](/work-log/domain_event_naming_past_tense/)                                                                                                                                       |
| 從操作推導領域                                                       | 使用者操作 → domain / event → 邊界切分的推導流程                                      | [桌子跟購物車是兩個聚合](/work-log/pos_table_cart_lifecycle_decoupling/)、[過度設計震盪](/work-log/flutter_async_query_overdesign_oscillation/)、[pure function 領域計算](/work-log/dart_unsettled_cart_pure_function/)                                                                                 |
| 分層責任與基礎設施歸位                                               | domain 對呈現與技術細節無知、共用能力歸哪層                                           | [Domain 層的 947 處硬編碼中文](/work-log/flutter_domain_layer_i18n_hardcoded_text/)、[重複 service 假覆蓋率](/work-log/flutter_duplicate_service_fake_coverage/)、[Port 介面與 mock 地獄](/work-log/flutter_port_interface_mock_hell_isp/)                                                              |
| entity 的持久化邊界                                                  | 完成定義要含持久化迴圈、entity 欄位與 schema 的差集                                   | [功能完成卻從未持久化](/work-log/flutter_feature_complete_never_persisted/)、[SQLite VO 序列化邊界](/work-log/flutter_sqlite_value_object_serialization_boundary/)                                                                                                                                      |
| entity 的演化與遷移                                                  | 大 ripple 的重寫策略、遷移通路三段齊（寫入 / 讀出 / 消費）                            | [Deprecated Getter Facade](/work-log/flutter_deprecated_getter_facade_entity_migration/)、[read-path 缺口與 fixture 假綠](/work-log/flutter_migration_read_path_gap_fake_green/)                                                                                                                        |
| [跨邊界參照與狀態所有權](/ddd/cross-boundary-reference-ownership/)   | 下游持有上游 id 時有效性由誰決定——穩定身份、解引用時機、自持與可導出狀態的遷移分工    | [跨邊界參照的生命週期](/work-log/pos_cross_boundary_reference_lifecycle/)、[自持狀態與可導出狀態](/work-log/pos_held_vs_derived_state_migration/)、[T.C5 凍結參照失效被 stub 遮蔽](/testing/cases/stale-reference-stub-blindspot/)                                                                      |
| entity 的生命週期                                                    | 生命週期由業務流程定義、ephemeral 物件的丟棄即重置                                    | [只活在結帳流程裡的領域物件](/work-log/flutter_ephemeral_domain_object_rx_immutable/)、[桌子跟購物車是兩個聚合](/work-log/pos_table_cart_lifecycle_decoupling/)                                                                                                                                         |
| [domain event 與命令、查詢](/ddd/domain-event-vs-command-and-query/) | 訊息的責任結構分界——事件只承載已發生的事實、意圖與對話各有自己的通道                  | [Domain Event 命名的過去式](/work-log/domain_event_naming_past_tense/)、[用事件做同步查詢等於手工重建 RPC](/work-log/cross_domain_event_request_response_cost/)                                                                                                                                         |

Aggregate 生命週期已有第一個 case（桌位與購物車）；bounded context、repository 邊界等主題等 case 累積後再進大綱——本模組的章節由 case 驅動，理論陳述要有實際踩過的專案情境支撐。

## Case 回補

本模組的 case 來源是實際專案的開發記錄與 ticket：過去專案內處理掉的設計討論陸續回補成 [work-log](/work-log/) 文章（兩個專案），模組章節再引用這些 case。目前的 case 基底集中在兩個 Dart / Flutter 專案，章節的判準以敘事層抽象維持語言無關；跨生態的驗證隨其他語言模組的 case 累積補強。
