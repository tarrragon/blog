---
title: "Flutter 實戰指南"
date: 2026-07-10
description: "Flutter 與 Dart 的實作層教材：型別設計與語言機制、狀態與渲染、測試策略、工具鏈，從實際專案 case 抽出判準。"
weight: 33
tags: ["flutter", "dart", "mobile"]
---

本模組收 Flutter 與 Dart 的實作層知識：語言機制、框架行為、測試策略與工具鏈。內容從實際專案的 case 抽出——每個判準都有踩過的情境支撐，不是官方文件的轉述。設計理論（entity、不變式、稽核軌跡）的地基在 [DDD 領域驅動設計指南](/ddd/)，本模組承擔的是「這些理論在 Dart 生態碰到什麼實作限制」：例如 copyWith 與 freezed 的預設路徑如何影響領域模型的完整性。

## 章節大綱（backlog）

大綱是 backlog、章節邊界隨 case 回補調整。四個章節群從既有 work-log case 聚類而來：

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

### 狀態與渲染

| 主題                      | 既有 case                                                                                                            |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| 重繪訊號與按需 render     | [重繪訊號排查與心跳做法](/work-log/flutter_repaint_heartbeat/)、[scheduleFrame()](/work-log/flutter_schedule_frame/) |
| 命中測試                  | [HitTestBehavior 三種模式](/work-log/flutter_hit_test_behavior/)                                                     |
| 系統資源邊界              | [App 音量 vs 系統音量](/work-log/flutter_audio_volume_control/)                                                      |
| Riverpod 容器與狀態作用域 | [雙容器狀態脫節：App 永遠卡在載入畫面](/work-log/flutter_riverpod_dual_container_state_desync/)                      |

### 測試

| 主題                     | 既有 case                                                                                                                                     |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| 三層測試策略與 mock 遮蔽 | [192 個測試全過、實機全壞](/work-log/testing_three_layer_strategy/)                                                                           |
| 跨測試狀態污染           | [GetX 跨檔案狀態污染](/work-log/dart_test_getx_cross_file_state_pollution/)、[新增欄位忘記同步 reset](/work-log/reset_state_leak_cross_test/) |
| async 錯誤的接管         | [sync try-catch 接不到 async 錯誤](/work-log/flutter_test_async_unhandled_error/)                                                             |
| 測試訊號可信度           | [紅燈在量什麼：斷言 / 量測 / 環境三層失真](/work-log/flutter_test_signal_credibility_three_layers/)                                           |
| 產品碼是 mock 的假綠     | [ViewModel 假實作通過了 15 個測試](/work-log/flutter_viewmodel_mock_implementation_passes_tests/)                                             |
| 持久化迴圈驗收           | [功能完成卻從未持久化](/work-log/flutter_feature_complete_never_persisted/)                                                                   |
| 覆蓋率的分母             | [重複 service 的 100% 覆蓋率假象](/work-log/flutter_duplicate_service_fake_coverage/)                                                         |

### 架構與分層

| 主題                  | 既有 case                                                                           |
| --------------------- | ----------------------------------------------------------------------------------- |
| 過度設計的兩種膨脹    | [異步查詢系統的過度設計震盪](/work-log/flutter_async_query_overdesign_oscillation/) |
| Domain 層的 i18n 邊界 | [Domain 層的 947 處硬編碼中文](/work-log/flutter_domain_layer_i18n_hardcoded_text/) |

### 工具鏈

| 主題               | 既有 case                                                                                 |
| ------------------ | ----------------------------------------------------------------------------------------- |
| 裝置偵測的失效訊號 | [flutter devices 卡住的訊號](/work-log/flutter_devices_hangs_on_zombie_android_emulator/) |

## Case 回補

case 先進 [work-log](/work-log/)、模組章節再引用——這條管道讓專案裡處理掉的問題有固定的沉澱路徑。回補來源是專案的開發記錄與 ticket；章節從 case 聚類長出來，不從大綱硬生。
