---
title: "測試輸出的雜訊治理：預期的環境狀態不該走例外路徑"
date: 2026-07-17
draft: false
description: "測試輸出長期印著兩行「已知無害」的錯誤——相機偵測 MissingPluginException、toast 套件的 assert fallback。已知雜訊會訓練人忽略輸出，新警報混在裡面就被過濾掉。修法是把「預期的環境狀態」變成前置判斷（channel mock 回空、無畫面早退），讓例外路徑只剩真正的例外。"
tags: ["flutter", "dart", "test", "noise", "fallback", "platform-channel", "runZonedGuarded"]
---

> **核心議題**：測試環境沒有相機、沒有 widget tree——這些是**必然且預期**的狀態，但程式用「拋例外→catch→印 log」的路徑處理它們，於是每次跑測試都固定印出兩行看起來像壞掉的輸出。人對重複出現的警報會建立心理過濾，等真的有新問題印出相似訊息時，一起被過濾掉。
> **案例骨幹**：POS App 的流程測試輸出固定出現「偵測相機失敗（MissingPluginException）」與「toast 套件不可用（assert 失敗）」。使用者的裁定是：無法使用的就該移除、可疑的要查清是什麼——結果一個在 harness 補 channel mock 讓偵測走正常路徑，一個查證為環境必然後改成前置判斷，例外接管降級為真正非預期的兜底。

---

## 1. 兩行雜訊的解剖

| 輸出                                                                         | 來源                                                                                                                   | 性質                     |
| ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| `偵測相機失敗，視為無相機: MissingPluginException(...)`                      | 啟動期呼叫 `availableCameras()`，測試環境無 plugin → 拋例外 → 產品的 catch 把它降級成「無相機」並印 log                | 產品行為正確、輸出是雜訊 |
| `[fallback] toast 套件不可用: Failed assertion: '_key.currentState != null'` | 顯示提示時 toast 套件斷言 widget tree 上有掛載點——headless 測試沒有畫面 → assert → 被 `runZonedGuarded` 兜底接住印 log | 兜底行為正確、輸出是雜訊 |

兩者共同點：**觸發條件在測試環境是 100% 必然**。每一次執行、每一條會經過這些路徑的測試，都固定貢獻幾行「錯誤長相」的輸出。

## 2. 為什麼要治理：已知雜訊遮蔽新警報

單看無害——catch 有接、fallback 有兜、測試全綠。傷害在人這一側：讀輸出的人很快學會「那兩行不用看」，心理過濾建立後，過濾的是**模式**不是內容——某天一行真正的新錯誤以相似的形狀出現（另一個 MissingPluginException、另一個 assert fallback），會被同一個過濾器吃掉。

治理原則一句話：**測試輸出裡的每一行錯誤長相的文字，都應該值得停下來看**。做不到就治理到做得到。

## 3. 修法一：讓偵測走正常路徑（harness 補 channel mock）

相機那行的問題不是 catch 寫錯——生產環境「枚舉失敗保守視為無相機」是正確防護。問題是測試環境讓它天天走例外路徑。修在 harness：

```dart
// 測試環境沒有相機 plugin，回空清單讓啟動期的相機偵測
// 得到「無相機」的乾淨結果，不走例外路徑留下雜訊 log。
TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
    .setMockMethodCallHandler(const MethodChannel('plugins.flutter.io/camera'),
        (call) async => call.method == 'availableCameras' ? <dynamic>[] : null);
```

偵測照常執行、得到空清單、安靜地判定無相機。產品碼一行不動。

## 4. 修法二：預期狀態前置判斷，例外接管留給非預期

toast 那行先查證：正式 App 在根 widget 正確掛了套件的初始化 builder——**不是產品 bug**，assert 純粹是 headless 環境沒有畫面。既然「無畫面」是可以直接判斷的狀態，就不該用「撞 assert → zone 接住」的方式發現它：

```dart
runZonedGuarded(() {
  // 無畫面（headless 測試等）時 toast 沒有掛載點；
  // 訊息已先記進 log 服務，略過顯示即可
  if (WidgetsBinding.instance.rootElement == null) return;
  showToast(...);
}, (error, stack) {
  // 這裡從此只會接到真正非預期的失敗——留著的 log 才是警訊
});
```

分工因此變乾淨：**前置判斷處理已知的環境狀態，`runZonedGuarded` 兜底處理未知的失敗**。兜底的 log 從「每次測試都響的假警報」變成「響了就該查」的真警報——這才是兜底該有的信噪比。（zone 接管機制本身的分析見 [sync try-catch 接不到 async 錯誤](/work-log/flutter_test_async_unhandled_error/)。）

前置判斷放在 zone 內而非 zone 外有一個小理由：極端環境（binding 未初始化）連 `WidgetsBinding.instance` 都會拋，放 zone 內讓這種罕見情況也落入兜底而不是炸到 caller。

## 5. 可複用的判準

1. 測試輸出固定出現的錯誤長相文字 = 治理對象，不因「無害」豁免——它的成本收在未來某次被過濾掉的真警報上。
2. 分類處理：觸發條件在測試環境**必然**成立 → 前置判斷或 harness mock 讓它走正常路徑；觸發條件**不確定** → 保留例外接管，且它的 log 要因稀有而醒目。
3. 動手前先查證「這是誰的問題」——toast 那行若不查，可能誤修產品的初始化；查證後才知道是環境必然，修法完全不同。
4. fallback 的價值與它的觸發頻率成反比：天天觸發的 fallback 是常態路徑的錯位，不是防護。

## 下一步

- zone 與 async 錯誤接管的機制層 → [sync try-catch 接不到 async 錯誤](/work-log/flutter_test_async_unhandled_error/)
- harness 的完整組裝 → [讓 UI 控制器在 headless 測試立起來](/work-log/flutter_headless_controller_test_bootstrap/)
