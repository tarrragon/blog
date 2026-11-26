# 實機與模擬器上的陷阱與處置

> **何時讀**：`SKILL.md` 的流程在某一步出現跟預期不同的結果時（截圖全黑、操作沒反應、對話框不見、模擬器拍不到某個狀態），依症狀查下表；開始一批截圖之前，先讀〈會寫入資料的點按〉與〈設備設定的還原〉。

## 症狀與處置

| 症狀 | 成因 | 處置 |
|------|------|------|
| 截圖整張是黑的 | Android 螢幕關了或鎖上了。`drive.dart` 的點按是 APP 內部的事件，系統不把它算成使用者操作，螢幕逾時照樣計時 | `"${ADB:-adb}" -s "$ANDROID_SERIAL" shell dumpsys power \| grep mWakefulness` 是 `Dozing` 或 `Asleep` 時，請使用者解鎖。每一步之前送 `KEYCODE_WAKEUP`（`drive.sh` 已經做）只能延後螢幕關閉；螢幕已經鎖上時，喚醒鍵只點亮螢幕，解不開鎖 |
| `flutter run` 結束，log 最後是 `Lost connection to device` | 螢幕鎖上後，debug 連線中斷（實測：Samsung SM-S9010、Android 16） | 使用者解鎖後重新 `flutter run`，取新的 VM service 位址，改寫 `<暫存目錄>/env.sh` 的 `FLUTTER_VM_WS` 那一行；APP 已經裝好，重跑比第一次快 |
| 操作沒反應、畫面停在換頁中途，或之後的 push 與 back 都不再換頁 | 實測（Android 16 實機、iPhone 16 模擬器，Flutter 3.41）是動作送得太密：上一個換頁動畫（Flutter 3.41 預設 Material 450ms、Cupertino 500ms）還沒跑完就送下一個。實測當時的工作紀錄推測，機制是 Navigator 的除錯鎖（`_debugLocked`）在一次 assertion 之後沒有解開（沒有驗證）；`push` 或 `back` 印出的求值失敗訊息含 `_debugLocked` 時就是這個情形 | 每個動作之後等 0.8 秒（`drive.sh` 已經做），自己寫迴圈時不要省掉等待；已經不再換頁時熱重啟（`kill -USR2 <pid>`），從首頁重新操作 |
| 剛打開的面板或對話框不見了 | 拿「點一下畫面角落」當截圖觸發，那一下點按落在暗幕（modal barrier）上，APP 把面板關掉 | 截圖用 `drive.sh shot <path>`，不靠點按觸發 |
| 對話框裡的輸入框開著鍵盤，按返回鍵之後對話框也不見了 | Android 上（實測：Samsung SM-S9010、Android 16，APP 以 Flutter 3.41 建置、targetSdk 36）系統返回鍵會連對話框一起關掉，不是只收起鍵盤；換了 targetSdk 或預測式返回（predictive back）的設定要重測 | 要拍「鍵盤收起的對話框」時不用返回鍵。Flutter 在 Android 與 iOS 上預設不因為觸控點到輸入框外面而取消焦點（`drive.sh tap` 送的是觸控事件），只有 APP 自己實作了點外面失焦（`TextField` 的 `onTapOutside`，或外層呼叫 `unfocus()`）時，點對話框裡輸入框以外的位置才收得起鍵盤；APP 沒有實作時，只拍鍵盤開著的那一張，`states.md` 那一行寫「未拍（APP 沒有收起鍵盤的方式）」 |
| `type` 印出「求值失敗」，訊息含 Null check；或 `type` 把文字寫進了另一個輸入框 | 求值失敗是沒有任何輸入框有焦點（對話框還沒開完）；文字寫進別的輸入框是焦點在那一個輸入框 | 打開對話框之後先 `drive.sh shot` 截一張，確認對話框已經開完、游標在輸入框裡，再 `type` |
| iOS 模擬器的輸入畫面沒有鍵盤 | 模擬器把電腦的實體鍵盤當成輸入，螢幕鍵盤不出現 | 在 Simulator 的 I/O › Keyboard 關掉 Connect Hardware Keyboard（agent 沒有權限送按鍵時請使用者操作）；做不到時，鍵盤開著的狀態寫「未驗（模擬器：接著實體鍵盤）」 |
| iOS 模擬器的掃描或相機畫面只有權限說明 | 模擬器沒有相機 | 相機以外的路徑（手動輸入）照常驗；相機掃描本身留給實機，寫「未驗（模擬器：沒有相機）」 |
| 截圖右緣有一個圓角的半透明把手 | Samsung 的 Edge Panel，系統元件 | 不是 APP 的畫面；交給審查時寫明 |
| 改了程式碼、熱重啟之後畫面沒變 | 程式有編譯錯誤（`flutter.log` 有 `<檔案>:<行>:<欄>: Error:`，修好再送），`flutter run` 已經結束，或改到的是熱重啟不會重新載入的部分（原生碼、原生設定檔如 AndroidManifest、Info.plist、Gradle 設定，以及拿掉了的系統列樣式欄位；系統列欄位改值會反映） | 確認 `flutter run` 的程序還在（`--pid-file` 的 pid）；送 `kill -USR2 <pid>`（熱重啟）之後在 log 找 `Restarted application`，次數有增加才算成功。改到的是原生碼或原生設定檔時，熱重啟怎麼送都不會生效：結束 `flutter run`，重新執行（會重新建置與安裝，VM service 位址也會變，改寫 `env.sh`）；系統列的設定見下一列 |
| 系統列（狀態列、導覽列）的設定改了，熱重啟之後沒有回到預設 | 視窗保留上一次設定的系統列樣式；熱重啟不會重設 | 程式裡每個欄位寫明確的值；要確認預設行為時，結束 `flutter run`，照 SKILL.md「改程式碼之後熱重啟」那一步重新執行並改寫 `env.sh` |
| Gradle 建置失敗，錯誤指向快取裡的 journal 檔損壞 | 快取檔被寫壞（實測那一次是 macOS 主機的磁碟滿），背景的 Gradle daemon 還拿著壞掉的檔 | 先 `./gradlew --stop`（在 `android/` 底下），再刪錯誤訊息指出的那個 journal 檔，重新建置 |

## 會寫入資料的點按

同一個座標，在不同狀態下是不同的鍵。實例：條碼查詢的結果面板，查到的項目已經在 APP 的資料裡時，第一顆鍵是「繼續掃下一個」；不在資料裡時，第一顆鍵是「加入」，第二顆才是「繼續掃下一個」。照前一個狀態量的座標去關面板，會把測試資料寫進 APP。

- 點任何會寫入資料的鍵（加入、儲存、刪除、送出）之前，先截圖確認那個座標是哪一顆鍵；座標依狀態分開記，寫進腳本時在旁邊註明是哪一個狀態的哪一顆鍵。要關掉的面板上每一顆鍵都會寫入資料時（找不到關閉或取消鍵），用 `drive.sh back`，或點面板外的暗幕（點之前同樣先截圖確認那個位置是暗幕）。
- 用測試資料拍。開拍之前截一張顯示資料筆數的畫面（例如清單頁頂欄的總數），記下計數。誤寫之後，在 APP 裡把那筆資料刪掉，確認計數回到記下的原值，並把誤寫之後拍的截圖全部重拍：那些截圖裡的資料跟其他截圖不一致。
- 刪除這類動作在 APP 裡做，不直接改 APP 的資料庫檔：直接改檔會繞過 APP 的同步與快取，畫面跟資料庫可能對不上。

## 設備設定的還原

拍亮暗兩組、驗大字級或換 Android 導覽方式時，要改使用者設備的設定。改之前記下要改的那幾項的原值，拍完把改過的每一項還原並確認（沒改的不動）。先 `source` `env.sh`（SKILL.md 的啟動那一步）。表裡的 `adb` 指 `"${ADB:-adb}" -s "$ANDROID_SERIAL"`，`$IOS_UDID` 也取自 `env.sh`：adb 不在 PATH 時照 `SKILL.md`〈前置〉的順序找到路徑後設成 `ADB`；接了不只一台設備時要帶 `-s`，否則 adb 回報 more than one device。兩台設備各用一個子目錄時，`source` 的是那台的 `env.sh`，原值寫進那台的 `device-original.txt`。

| 設定 | 讀原值 | 改與還原 |
|------|--------|---------|
| Android 深色模式 | `adb shell cmd uimode night`（印 `Night mode: yes`、`no`、`auto` 或 `custom`） | `adb shell cmd uimode night <值>`，`<值>` 填 `yes`、`no` 或 `auto` 其中一個，還原時填讀到的原值。讀到的值不是 `yes`、`no`、`auto` 其中之一時（例如依排程或就寢時間切換的設定），這一批不切換深色模式，請使用者在手機上切換，拍完再請使用者切回 |
| Android 導覽方式 | `adb shell settings get secure navigation_mode`（`0` 三鍵導覽、`1` 兩鍵導覽（舊版 Android）、`2` 手勢導覽） | 請使用者在手機的設定裡切換，拍完再請使用者切回。`adb shell cmd overlay enable com.android.internal.systemui.navbar.threebutton`（切三鍵）與 `adb shell cmd overlay enable com.android.internal.systemui.navbar.gestural`（切手勢）在部分機型可以切換，在 Samsung 上沒有實測；用了之後照樣讀一次 `navigation_mode` 確認 |
| Android 字級 | `adb shell settings get system font_scale` | `adb shell settings put system font_scale <值>`（最大值依機型而定：請使用者在設定裡把字級拉到最大，讀一次 `font_scale` 記成這台的上限）；原值讀到 `null`（沒設過）時用 `adb shell settings delete system font_scale` 還原 |
| iOS 模擬器外觀 | `xcrun simctl ui "$IOS_UDID" appearance` | `xcrun simctl ui "$IOS_UDID" appearance <值>`，`<值>` 填 `light` 或 `dark`，還原時填讀到的原值 |
| iOS 模擬器字級 | `xcrun simctl ui "$IOS_UDID" content_size`（預設印 `large`） | `xcrun simctl ui "$IOS_UDID" content_size <值>`，值見 `xcrun simctl ui` 的說明，還原時填讀到的原值 |

原值寫進暫存檔，不只記在對話裡：context 被壓縮之後，對話裡的原值可能就讀不到了。使用者沒有要求驗的設定（例如字級）不改。
