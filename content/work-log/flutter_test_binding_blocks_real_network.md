---
title: "TestWidgetsFlutterBinding 會擋掉真實網路：真實後端測試與流程測試的檔案級隔離"
date: 2026-07-17
draft: false
description: "flutter_test 的 binding 初始化後會把 HttpClient 換成回 400 的假件——需要真實網路的後端驗證測試不可初始化 binding，也因此不可 import 任何會初始化 binding 的 harness。靠測試檔案各自跑在獨立 isolate 的特性，兩種測試在同一個目錄共存。"
tags: ["flutter", "dart", "test", "binding", "http", "integration-test", "isolate"]
---

> **核心議題**：`TestWidgetsFlutterBinding.ensureInitialized()` 的副作用之一是把 `HttpClient` 換成一律回 400 的假件（防止 widget test 意外打真實網路）。POS App 要在測試套件裡加一層「對真實後端驗證行為」的測試時，這個副作用成為硬約束。
> **案例骨幹**：真實後端驗證測試與流程測試住在同一個 `test/integration/` 目錄；前者不可初始化 binding、不可 import 流程測試的 harness（harness 第一行就 `ensureInitialized`）。兩者能共存的原因是 `flutter test` 讓每個測試檔案跑在獨立 isolate——binding 的全域副作用以檔案為邊界。

---

## 1. 症狀：測試裡所有真實 HTTP 請求回 400

對真實後端（QA 環境）發請求的測試，若與一般測試共用同一個 setup，會得到一個誤導性極強的症狀：請求沒有網路錯誤、沒有逾時，而是穩定回 400。看起來像後端拒絕，實際上請求根本沒離開測試程序。

機制：`TestWidgetsFlutterBinding` 初始化時安裝 `HttpOverrides`，把 `dart:io` 的 `HttpClient` 換成假實作——這是 flutter_test 的刻意設計，避免 widget test 因為 `Image.network` 之類的呼叫打到真實網路造成不穩定。它保護了大多數測試，也無差別地擋掉了「就是要打真實網路」的那一種。

## 2. 約束的傳染性：不可 import 會初始化 binding 的東西

這個副作用是**程序級全域**的，且沒有乾淨的關閉開關（`HttpOverrides.global = null` 可以事後拆除，但依賴「記得拆」的紀律，且 binding 的其他副作用仍在）。實務上更穩的做法是把它當成檔案級的硬約束：

- 真實後端驗證測試的檔案**從頭到尾不初始化 binding**
- 因此也**不可 import 流程測試的 harness**——harness 為了 mock platform channel、立起 UI 控制器，第一步就是 `ensureInitialized`；import 進來即使不呼叫，任何一個共用 helper 順手初始化都會中招

這條約束值得寫在檔案頭部的註解裡，因為違反它的症狀（400）與原因（binding）之間的距離太遠，下一個維護者幾乎不可能自己連起來。

## 3. 共存機制：檔案級 isolate 隔離

看似矛盾的需求——同一個目錄裡，流程測試需要 binding（mock channel、UI 控制器）、真實後端測試不能有 binding——不需要任何額外設計就能共存，因為 `flutter test` 的執行模型是**每個測試檔案一個獨立 isolate**：

|            | 流程測試檔                     | 真實後端驗證檔     |
| ---------- | ------------------------------ | ------------------ |
| binding    | `ensureInitialized()`          | 不初始化           |
| HttpClient | 假件（無妨，走假後端 adapter） | 真實（需要）       |
| 隔離邊界   | 檔案自己的 isolate             | 檔案自己的 isolate |

推論：**binding 相關的全域副作用，思考單位是「檔案」而不是「目錄」或「套件」**。同目錄混放兩種測試完全安全；同檔案混放必炸。

## 4. 真實後端測試的請求層組裝

不初始化 binding 之後，還要繞開產品 HTTP 層的執行環境依賴。產品的 Dio 由 DI 容器組裝，攔截器依賴登入服務（token）與翻譯資源（語系前綴）——在無 binding、無 DI 的測試檔裡拉不起來。做法是手組最小可用的傳輸層、但**請求與解析仍走產品的 API client 與模型**：

```dart
final dio = Dio(BaseOptions(
  baseUrl: '$baseUrl/$languagePrefix',   // 語系前綴改由 baseUrl 提供
  connectTimeout: const Duration(seconds: 5),
));
final api = ApiClient(dio);              // retrofit client 只需要一個 Dio
// 登入後手動掛 token，取代攔截器
dio.options.headers['Authorization'] = 'Bearer $token';
```

「走產品的 client 與模型」是刻意選擇：手刻 raw JSON 曾在同一批測試裡重踩產品早已解決的坑（列表回應的分頁包裝），而型別化解析讓後端回應形狀的變化在這層先於產品爆出來。

## 5. 可複用的判準

1. 測試出現「穩定 400、無網路痕跡」→ 先查是不是 binding 的 HttpClient 假件，再查後端。
2. 需要真實網路的測試檔：不初始化 binding、不 import 任何會初始化的模組，約束寫進檔頭。
3. 兩種測試同目錄共存靠檔案級 isolate——組織測試時以檔案為 binding 副作用的邊界單位。
4. 繞開 DI 不等於繞開產品程式碼：傳輸層手組、解析層共用。

## 下一步

- 這層測試的完整設計（預設可執行、離線降級、憑證失效紅燈）→ [真實後端驗證測試](/testing/03-protocol-integration-test/real-backend-verification/)
- harness 那一側的組裝 → [讓 UI 控制器在 headless 測試立起來](/work-log/flutter_headless_controller_test_bootstrap/)
