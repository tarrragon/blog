---
title: "測「不變」、不測「正確」 — characterization test 當遷移安全網"
date: 2026-07-10
draft: false
description: "大規模型別遷移前，對著舊實作寫一批鎖住現有行為的測試——包括看起來像 bug 的邊界怪癖也照鎖，遷移後全綠證明「換底沒改行為」。正確性是另一批測試的職責、混在一起紅燈就無法歸因。附測試環境的原生依賴三個斷點（FFI、plugin、late init）與替身解法。"
tags: ["flutter", "dart", "testing", "characterization-test", "migration", "mock", "getx"]
---

> **觸發場景**：POS 專案要做金額型別的全面遷移（Decimal 換 Money extension type），動的是全部 model 的金額欄位。測試目錄裡出現一批名字帶 `_characterization_test` 的檔案、開頭都有同一段宣告：「在 Money value object 遷移前建立、鎖住現有行為」
> **疑問來源**：這批測試跟一般的單元測試差在哪？為什麼連「找零算出負數歸零」這種邊界怪癖也被鎖進去？
> **整理目的**：記下 characterization test 的方法、跟正確性測試的分工、以及它依賴的測試環境前置（原生依賴的三個斷點）
> **本文邊界**：素材是該專案的五個 characterization 測試檔與 DEVLOG 的測試環境除錯史；characterization test 是 Michael Feathers 在 legacy code 領域的術語、這裡是它在型別遷移的應用

---

## 斷言的對象是「現況」、包括現況的怪癖

characterization test 跟一般測試共用全部語法、差別只在斷言的依據：一般測試斷言**規格**（找零應該是多少）、characterization test 斷言**現況**（現在的實作算出多少）。寫法是對著舊實作跑一次、把輸出原樣釘進 expect——實作是測試的 oracle、不是規格。

所以連怪癖也照鎖：現有實作在找零算出負數時歸零、這個行為對不對是另一回事，characterization test 把它鎖住。五個檔案的分佈跟著遷移的影響面走——checkout 的應付金額 fold 與現金找零、order 的小計、cart item 的價格計算、product spec 的三種價格——**遷移會經過的每條金額計算路徑、各有一張行為快照**。

分工的必要性在遷移期間顯形：換型別的過程中紅燈亮起，唯一要回答的問題是「**換壞了、還是本來就錯**」。characterization test 的紅燈只有一種含義（行為變了、遷移引入了差異）；如果這批測試混著「找零不該是負數」的正確性期望，紅燈就要逐個歸因——遷移的每一步都拖著這個排查成本。正確性的討論值得做、但排在遷移完成之後、在綠的基線上做：那時改行為的 diff 乾乾淨淨只有行為修正、不會跟型別替換攪在一起。

這跟[測試分診](/work-log/flutter_test_failure_triage_root_cause_roi/)的洞見同源：測試訊號的價值取決於它的含義夠不夠單一。characterization test 是刻意把含義收窄到「變 / 沒變」一個 bit 的設計。

## 退場：遷移完成後、快照可以轉正

characterization test 的生命週期跟著遷移走。遷移全綠收工後有兩條路：把有規格依據的斷言**轉正**成行為測試（找零的正常路徑）、把當初鎖住的怪癖**開案處理**（負數歸零是不是該改成拋錯？——現在可以安全地討論了，因為改它的 diff 不會跟遷移混在一起）。留著不動也無害、它繼續當回歸網——但檔名裡的 characterization 字樣要保留，它告訴未來的讀者「這些斷言記錄的是某個時刻的現況、不是設計承諾」。

## 前置：測試環境的原生依賴三個斷點

這批測試能跑的前提、在同專案 DEVLOG 的除錯史裡有完整的代價記錄——`flutter test` 的環境沒有原生 plugin 與 FFI，三個斷點三種症狀：

| 症狀                                                        | 根因                                                    | 替身解法                                                   |
| ----------------------------------------------------------- | ------------------------------------------------------- | ---------------------------------------------------------- |
| `LateInitializationError: Field 'packageInfo' ...`          | `package_info_plus` 在測試中不可用、late 欄位沒人初始化 | `TestAppService` 提供 mock `PackageInfo`                   |
| storage 相關初始化失敗                                      | `get_storage` plugin 不存在於測試環境                   | `TestStorageProvider`                                      |
| `Failed to lookup symbol 'init': dlsym(RTLD_DEFAULT, init)` | Rive 動畫走原生 FFI、測試環境查無符號                   | `MockLoadingPage`——用 `Container` + 進度圈保持相同 UI 結構 |

三個事件的解法收斂成同一個模式：**原生依賴在測試環境一律要有替身**、用 `Get.put<T>(testInstance)` 綁進依賴注入。症狀查表的價值在診斷速度——`dlsym` 字樣指向 FFI、`LateInitializationError` 指向沒被初始化的服務欄位、plugin 名字出現在錯誤裡就是 plugin 斷點；三種在第一次遇到時都像靈異事件、記下來之後都是五分鐘的事。Rive 那條的細節值得注意：mock 頁面保持了相同的 UI 結構與 Key，測試驗證邏輯不用改——替身的職責是**補環境、不是簡化被測物**。

## 判讀徵兆

- 即將進行「換底不換行為」的遷移（型別、ORM、序列化庫）而現有測試稀疏——先補 characterization、對著舊實作寫、怪癖照鎖
- 遷移期間紅燈需要逐個討論「這是不是本來就錯」——正確性期望混進了安全網，拆開
- characterization 檔案在遷移完成很久後仍在、且被當成規格引用——轉正或標註，快照不是承諾
- 測試錯誤含 `dlsym` / plugin 名 / `LateInitializationError`——原生依賴斷點，查替身清單、缺的補上

## 相關閱讀

- 這張安全網守護的遷移：[Money 三段遷移](/work-log/dart_money_extension_type_migration/)——characterization test 在那篇的角色是配角、本文是它的完整方法
- 訊號含義要單一的同源原則：[16 個失敗只有 2 個是缺口](/work-log/flutter_test_failure_triage_root_cause_roi/)、[紅燈在量什麼](/work-log/flutter_test_signal_credibility_three_layers/)
- 替身的反面教材：[1101 行自建測試基礎設施](/work-log/flutter_mock_infrastructure_overengineering_deleted/)——替身補環境是正當的、替身變平行框架就過了界
