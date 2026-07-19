---
title: "流程測試基礎設施"
date: 2026-07-17
description: "在 Flutter 專案建立流程測試時碰到的 Dart 實作限制：控制器能不能在 headless 環境立起來、binding 怎麼跟真實網路測試共存、測試輸出雜訊怎麼治理、假後端的回應資料走什麼路徑序列化——限制形成一條建置鏈，前一個的答案決定後一個的形態"
weight: 2
tags: ["flutter", "dart", "test", "flow-test", "fake-backend", "binding", "platform-channel"]
---

[流程測試](/testing/knowledge-cards/flow-test/)驅動的是跨服務的真實編排，[語意級假後端與流程測試](/testing/01-test-strategy-layers/semantic-fake-backend/)從策略層回答了「什麼時候值得建假後端、流程測試驗證什麼」；本章處理拿著策略在 Dart/Flutter 生態落地時碰到的實作限制。四個限制形成一條建置鏈：前一個的答案決定後一個的形態，跳著解會繞遠路。

## 閘門 spike：編排的宿主能不能在 headless 環境立起來

流程測試要驅動的是控制器裡的真實編排——順序約束、防護動作、收尾同步——而 Flutter 的控制器在 `onInit` 常帶平台耦合（platform channel 訂閱、相機偵測、外接裝置 plugin）。這些耦合在 headless 測試環境全部失效。

開工前先做一條最小測試 spike：能否建構控制器並呼叫編排入口。spike 的答案決定整個套件形態——立得起來就直接驅動真實編排（零漂移），立不起來要先評估重構接縫的成本。

平台耦合的中和工具在 Dart 生態有固定的對應：

| 耦合類型                            | 中和手段                            | 時序要求                       |
| ----------------------------------- | ----------------------------------- | ------------------------------ |
| EventChannel（plugin 建構子就訂閱） | `setMockStreamHandler` 掛空 handler | 在**建構 plugin 物件之前**掛好 |
| MethodChannel（查詢類呼叫）         | `setMockMethodCallHandler` 回空結果 | 在**呼叫發生之前**掛好         |
| 服務級平台依賴（掃碼、藍牙）        | 手寫 no-op 子類覆寫碰平台的成員     | 在 DI 容器註冊子類取代原服務   |
| `addPostFrameCallback` 承載的初始化 | 測試裡手動呼叫同一個方法            | 控制器建構後、斷言前           |

時序欄位承載的是這張表最容易踩的陷阱：EventChannel 的訂閱發生在 plugin 建構子裡，晚一步掛 mock，訂閱已經對著真實 channel 成立、之後補掛不會回溯生效——症狀是測試偶發卡在等事件。MethodChannel 的容錯高一些（呼叫當下才查 handler），但同樣要在第一次呼叫前就位。no-op 子類優於 mock 框架的場景：要中和的成員少（覆寫列表一目瞭然）、其餘行為要保留真實。流程測試的精神是假件越少，測試的證言越可信——這裡指的是平台耦合層的假件（與被驗編排無關的雜訊），被測邊界本身的假後端是另一回事，它的設計判準與忠實性把關見[語意級假後端](/testing/01-test-strategy-layers/semantic-fake-backend/)。

這套 channel mock 加 no-op 子類的組合（後文稱 harness）一旦成立就收斂為共用 bootstrap 方法——之後每條流程測試的邊際成本只剩劇本本身。完整 case 與程式碼範例：[讓 UI 控制器在 headless 測試立起來](/work-log/flutter_headless_controller_test_bootstrap/)。

## 兩種測試的共存：binding 的檔案級 isolate 隔離

流程測試需要 `TestWidgetsFlutterBinding`（mock channel、立控制器），真實後端驗證測試需要真實網路——兩者互斥。`TestWidgetsFlutterBinding.ensureInitialized()` 的副作用之一是把 `dart:io` 的 `HttpClient` 換成一律回 400 的假件，且這個副作用是程序級全域、沒有乾淨的關閉開關。

共存機制不需要額外設計：`flutter test` 讓每個測試檔案跑在獨立 isolate，而 isolate 之間記憶體不共享——binding 換掉的全域物件只在自己的 isolate 內生效，副作用因此以檔案為邊界。

|            | 流程測試檔               | 真實後端驗證檔     |
| ---------- | ------------------------ | ------------------ |
| binding    | `ensureInitialized()`    | 不初始化           |
| HttpClient | 假件（走假後端 adapter） | 真實（需要）       |
| 隔離邊界   | 檔案自己的 isolate       | 檔案自己的 isolate |

硬約束：真實後端驗證測試的檔案**不可 import 流程測試的 harness**——harness 為了 mock channel 第一步就是 `ensureInitialized`，import 進來即使不直接呼叫，任何共用 helper 順手初始化都會中招。違反這條約束的症狀是「穩定 400、無網路痕跡」——症狀與原因之間距離太遠，值得寫進檔頭。

真實後端驗證檔裡繞開產品 DI 的做法：手組最小可用的 `Dio`，請求與解析仍走產品的 API client 與模型（型別化解析層共用、不手寫 JSON）。完整機制與程式碼：[TestWidgetsFlutterBinding 會擋掉真實網路](/work-log/flutter_test_binding_blocks_real_network/)。

## 輸出雜訊治理：預期環境狀態的正確處理路徑

harness 立起後，測試輸出可能固定印出幾行「錯誤長相」的文字——相機偵測的 `MissingPluginException`、toast 套件的 assert fallback。這些在生產環境是正確的防護路徑，在測試環境是必然觸發的假警報。假警報訓練人忽略輸出，新的真警報混在裡面就被同一個心理過濾器吃掉。

治理原則：測試環境 100% 必然成立的觸發條件，用前置判斷或 harness mock 讓它走正常路徑，讓例外接管只剩真正的例外。

| 雜訊類型                                             | 修法                                                           |
| ---------------------------------------------------- | -------------------------------------------------------------- |
| 平台 plugin 不存在導致的 `MissingPluginException`    | harness 的 channel mock 回空結果（上一節已掛的 mock 同時解決） |
| headless 環境沒有 widget tree 導致的 assert fallback | 顯示前前置判斷 `rootElement != null`，無畫面時跳過顯示         |

前置判斷放在 `runZonedGuarded` 的 zone 內而非外——極端環境（binding 未初始化）連 `WidgetsBinding.instance` 都會拋，放 zone 內讓它落入兜底。分工因此變乾淨：前置判斷處理已知的環境狀態，zone 兜底處理未知的失敗。完整案例與判準：[測試輸出的雜訊治理](/work-log/flutter_test_noise_expected_paths/)。

## 假後端的回應序列化：物件 → toJson，不是手寫 JSON

有狀態假後端的回應資料從哪裡來，是 Dart 生態特有的選型：freezed 模型天生雙向（`fromJson`/`toJson`），假後端持有模型物件、出口一律 `toJson()`，服務層走的反序列化路徑與生產環境完全相同。

手寫 JSON 樣板跳過這個閉環的前半段——樣板對不對靠人眼比對 API 文件。實際案例：同一批測試裡的 raw 寫法重踩了產品早已內建處理的分頁包裝（信封解析層的知識被重複實作在測試 helper 裡），改走產品的 API client 與模型後，helper 連同它代表的重複知識一起刪除。

判準一句話：**回應形狀的知識只該存在一份**。測試裡出現 `data['data']` 之類手挖回應欄位的 helper，就是重複知識的訊號。

假後端的狀態演變用 `copyWith` 在 handler 裡宣告式完成，一個 handler 對應一條已證實的後端行為。toJson 閉環的忠實性由配對的[真實後端驗證測試](/testing/03-protocol-integration-test/real-backend-verification/)把關——模型的 `fromJson`/`toJson` 若與真實後端不對稱，會在那裡先於產品爆出來。完整做法與對照組事故：[有狀態假後端用真實模型序列化回應](/work-log/flutter_fake_backend_real_model_serialization/)。

## 建置順序

四個限制的處理有先後依賴：

1. **spike**：一條最小測試驗證控制器能否在 headless 環境建構並呼叫編排入口
2. **harness 收斂**：spike 過了之後，把 channel mock + no-op 子類 + postFrameCallback 補位收進共用 bootstrap
3. **檔案隔離規劃**：真實後端驗證測試另開檔案、不 import harness、不初始化 binding
4. **雜訊治理**：harness 的 channel mock 順便解決大部分雜訊；剩餘的 headless 環境假警報加前置判斷
5. **假後端序列化**：以 freezed 模型持有狀態、toJson 出口，seed builder 集中維護初始狀態
6. **第一條劇本**：走完一段跨服務業務旅程，斷言散佈在各階段的可觀察結果上

步驟 1 決定後續全部形態——立不起來就回到策略層重新評估（[語意級假後端與流程測試](/testing/01-test-strategy-layers/semantic-fake-backend/)的「可測性閘門」段）。

## 下一步路由

- 策略層的完整判準（什麼時候值得建假後端）→ [語意級假後端與流程測試](/testing/01-test-strategy-layers/semantic-fake-backend/)
- 配對的真實後端驗證（假後端行為漂移的防線）→ [真實後端驗證測試](/testing/03-protocol-integration-test/real-backend-verification/)
- 憑證的存放與 CI 注入 → [測試憑證管理](/testing/03-protocol-integration-test/credential-management/)
- 各限制的完整 case：[headless 控制器](/work-log/flutter_headless_controller_test_bootstrap/)、[binding 互斥](/work-log/flutter_test_binding_blocks_real_network/)、[雜訊治理](/work-log/flutter_test_noise_expected_paths/)、[假後端序列化](/work-log/flutter_fake_backend_real_model_serialization/)
