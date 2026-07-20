---
title: "Flutter 實戰指南"
date: 2026-07-10
description: "Flutter 與 Dart 的實作層教材：型別設計與語言機制、狀態與渲染、測試策略、工具鏈，從實際專案 case 抽出判準。"
weight: 33
tags: ["flutter", "dart", "mobile"]
---

本模組收 Flutter 與 Dart 的實作層知識：語言機制、框架行為、測試策略與工具鏈。內容從實際專案的 case 抽出——每個判準都有踩過的情境支撐，不是官方文件的轉述。設計理論的地基在 [DDD 領域驅動設計指南](/ddd/)（[entity 與 value object 的判準](/ddd/entity-vs-value-object/)、[不變式的強制層次](/ddd/invariant-enforcement-layers/)），本模組承擔的是「這些理論在 Dart 生態碰到什麼實作限制」：例如 [copyWith](/flutter/knowledge-cards/copywith/) 與 [freezed](/flutter/knowledge-cards/freezed/) 的預設路徑如何影響領域模型的完整性。

## 章節

章節從 case 聚類長出——同主題 case 累積到臨界量、互相引用密集時，才值得一篇判準層的聚合章：

| 章節                                                              | 核心問題                                                                       | 聚合的 case                                    |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------ | ---------------------------------------------- |
| [Riverpod 的 reactive 邊界](/flutter/riverpod-reactive-boundary/) | reactive 保證只覆蓋 provider 圖內部——變化在圖上嗎、哪個容器、節點活著嗎        | 空間／涵蓋／接入／時間四邊界共五篇             |
| [流程測試基礎設施](/flutter/flow-test-infrastructure/)            | Dart 生態的四個實作限制：headless 控制器、binding 互斥、輸出雜訊、假後端序列化 | binding + headless + noise + fake-backend 四篇 |

## 章節大綱（backlog）

大綱是 backlog、章節邊界隨 case 回補調整。章節群從既有 work-log case 聚類而來：

### Dart 語言機制與型別設計

| 主題                       | 既有 case                                                                                               |
| -------------------------- | ------------------------------------------------------------------------------------------------------- |
| copyWith 的適用邊界        | [copyWith 是逃生口，不是設計](/work-log/dart_copywith_entity_escape_hatch/)                             |
| freezed 的結構與選型       | [Freezed 三層結構解剖](/work-log/dart_freezed_anatomy/)、[Freezed 選型評估](/work-log/freezed/)         |
| 欄位的隱藏 getter / setter | [late final 欄位不能用欄位覆蓋](/work-log/late_final_field_override_getter_setter/)                     |
| 屬性遮蔽                   | [Widget 子類重新宣告 key](/work-log/widget_key_shadowing_duplicate/)                                    |
| 高階函式與 typedef         | [typedef 改寫前後比較](/work-log/dart_hof_typedef_readability/)                                         |
| Stream 的訂閱模型          | [StreamController single vs broadcast](/work-log/dart_stream_controller_single_vs_broadcast/)           |
| 金額的 domain type         | [Money 三段遷移：double→Decimal→extension type](/work-log/dart_money_extension_type_migration/)         |
| VO 封裝邊界與取值出口      | [VO 封裝擺盪：全移除、完全封裝、加回 getter](/work-log/flutter_value_object_encapsulation_oscillation/) |
| import 路徑與 library 身份 | [同一個類別被判成兩個型別](/work-log/dart_import_path_type_conflict/)                                   |
| exception 階層與錯誤分類   | [Exception 型別綁 ErrorCategory 的建構不變式](/work-log/flutter_exception_error_category_invariant/)    |
| 分層 enum 的粒度分工       | [16 種支付渠道、4 種行為分類](/work-log/dart_payment_dual_layer_enum/)                                  |
| VO accessor 一致性         | [取個原始值有四種寫法](/work-log/flutter_vo_tostring_leak_accessor_inconsistency/)                      |
| 函式分解的邊界             | [88 行拆 13 個函式、90 行決定不拆](/work-log/flutter_function_decomposition_split_vs_keep/)             |
| 傘狀名與重命名原子性       | [兩個 ImportResult 各自都合理](/work-log/flutter_import_result_name_collision/)                         |

### 狀態與渲染

| 主題                                | 既有 case                                                                                                               |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 重繪訊號與按需 render               | [重繪訊號排查與心跳做法](/work-log/flutter_repaint_heartbeat/)、[scheduleFrame()](/work-log/flutter_schedule_frame/)    |
| 命中測試                            | [HitTestBehavior 三種模式](/work-log/flutter_hit_test_behavior/)                                                        |
| 系統資源邊界                        | [App 音量 vs 系統音量](/work-log/flutter_audio_volume_control/)                                                         |
| Riverpod 容器與狀態作用域           | [雙容器狀態脫節：App 永遠卡在載入畫面](/work-log/flutter_riverpod_dual_container_state_desync/)                         |
| Riverpod 的 reactive 邊界           | [加書後統計不刷新：ref.watch 觀察的是 provider 圖、不是資料庫](/work-log/flutter_riverpod_reactive_boundary_ref_watch/) |
| StreamProvider 包 repository stream | [broadcast、初始值、dispose 實作點](/work-log/flutter_streamprovider_wraps_repository_watch/)                           |
| ephemeral 流程狀態                  | [只活在結帳流程裡的領域物件](/work-log/flutter_ephemeral_domain_object_rx_immutable/)                                   |
| async gap 與 ref 生命週期           | [await 回來的時候、頁面已經關了](/work-log/flutter_unmounted_ref_async_gap/)                                            |
| Notifier 的依賴注入與清理掛法       | [手寫 dispose() 沒有呼叫者](/work-log/flutter_notifier_lifecycle_ref_ondispose/)                                        |
| 版面約束與溢出預防                  | [溢出 714px、22 個測試同時紅](/work-log/flutter_renderflex_overflow_prevention_spec/)                                   |

### 測試

| 主題                     | 既有 case                                                                                                                                     |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| 三層測試策略與 mock 遮蔽 | [192 個測試全過、實機全壞](/work-log/testing_three_layer_strategy/)                                                                           |
| 接線測試與組裝層證言     | [測試全綠、功能失聯](/work-log/flutter_composition_root_wiring_gap/)                                                                          |
| 跨測試狀態污染           | [GetX 跨檔案狀態污染](/work-log/dart_test_getx_cross_file_state_pollution/)、[新增欄位忘記同步 reset](/work-log/reset_state_leak_cross_test/) |
| async 錯誤的接管         | [sync try-catch 接不到 async 錯誤](/work-log/flutter_test_async_unhandled_error/)                                                             |
| 測試訊號可信度           | [紅燈在量什麼：斷言 / 量測 / 環境三層失真](/work-log/flutter_test_signal_credibility_three_layers/)                                           |
| 產品碼是 mock 的假綠     | [ViewModel 假實作通過了 15 個測試](/work-log/flutter_viewmodel_mock_implementation_passes_tests/)                                             |
| 持久化迴圈驗收           | [功能完成卻從未持久化](/work-log/flutter_feature_complete_never_persisted/)                                                                   |
| 覆蓋率的分母             | [重複 service 的 100% 覆蓋率假象](/work-log/flutter_duplicate_service_fake_coverage/)                                                         |
| 大規模失敗分診           | [16 個失敗只有 2 個是缺口：先分診、再按 ROI 修](/work-log/flutter_test_failure_triage_root_cause_roi/)                                        |
| mock 負擔與介面寬度      | [mock 55 個方法只用 5 個：Port 介面](/work-log/flutter_port_interface_mock_hell_isp/)                                                         |
| 測試基礎設施的重量       | [1101 行自建測試基礎設施、刪掉 82.5%](/work-log/flutter_mock_infrastructure_overengineering_deleted/)                                         |
| fixture 與真實資料通路   | [遷移計畫有寫入、有消費、缺讀出](/work-log/flutter_migration_read_path_gap_fake_green/)                                                       |
| 遷移安全網               | [測「不變」、不測「正確」：characterization test](/work-log/flutter_characterization_test_migration_safety_net/)                              |
| binding 與真實網路的互斥 | [TestWidgetsFlutterBinding 會擋掉真實網路](/work-log/flutter_test_binding_blocks_real_network/)                                               |
| headless 立起 UI 控制器  | [platform channel mock、no-op 子類與 postFrameCallback 手工補位](/work-log/flutter_headless_controller_test_bootstrap/)                       |
| 測試輸出雜訊治理         | [預期的環境狀態不該走例外路徑](/work-log/flutter_test_noise_expected_paths/)                                                                  |
| 假後端的回應資料來源     | [有狀態假後端用真實模型序列化回應](/work-log/flutter_fake_backend_real_model_serialization/)                                                  |

上表末四項的判準與建置順序已聚合為 [流程測試基礎設施](/flutter/flow-test-infrastructure/)，各 case 保留完整程式碼與現場細節。

### 架構與分層

| 主題                  | 既有 case                                                                                               |
| --------------------- | ------------------------------------------------------------------------------------------------------- |
| 過度設計的兩種膨脹    | [異步查詢系統的過度設計震盪](/work-log/flutter_async_query_overdesign_oscillation/)                     |
| Domain 層的 i18n 邊界 | [Domain 層的 947 處硬編碼中文](/work-log/flutter_domain_layer_i18n_hardcoded_text/)                     |
| VO 的持久化序列化     | [SQLite 只吃三種型別](/work-log/flutter_sqlite_value_object_serialization_boundary/)                    |
| 領域計算的歸屬        | [「該收多少錢」抽成 pure function](/work-log/dart_unsettled_cart_pure_function/)                        |
| entity 遷移策略       | [Deprecated Getter Facade：140+ 檔零修改](/work-log/flutter_deprecated_getter_facade_entity_migration/) |
| 砍掉重練與需求盤點    | [宣告回歸原生、階層重生](/work-log/flutter_exception_hierarchy_regrowth/)                               |
| 資料存取的查詢次數    | [1000 本書、1001 次 SQL](/work-log/flutter_sqlite_n_plus_one_query/)                                    |
| 聚合結構演化          | [文件裡的扁平 Product、程式碼裡的雙層聚合](/work-log/pos_product_model_doc_vs_code_evolution/)          |
| 跨 domain 通訊的量級  | [用事件做同步查詢、等於手工重建 RPC](/work-log/cross_domain_event_request_response_cost/)               |
| 比對訊號的分級        | [相同 ISBN 相似度只有 0.67](/work-log/flutter_weighted_average_dilutes_identity_signal/)                |
| 驗證的兩層分工        | [「978ABC」被拒的理由寫著長度不對](/work-log/flutter_domain_input_validation_placement/)                |

### 工具鏈

| 主題               | 既有 case                                                                                 |
| ------------------ | ----------------------------------------------------------------------------------------- |
| 裝置偵測的失效訊號 | [flutter devices 卡住的訊號](/work-log/flutter_devices_hangs_on_zombie_android_emulator/) |

## Case 回補

case 先進 [work-log](/work-log/)、模組章節再引用——這條管道讓專案裡處理掉的問題有固定的沉澱路徑。回補來源是專案的開發記錄與 ticket；章節從 case 聚類長出來，不從大綱硬生。
