---
title: "flutter devices 卡住的訊號：device 數從 N 變 N-1 與 emulator 半活"
date: 2026-05-19
draft: false
description: "`flutter devices` / `flutter run` 卡住又印 `Error -2 retrieving device properties` 時回來看。根因是 Android emulator 半活狀態，附恢復順序。"
tags: ["flutter", "android", "adb", "emulator", "debugging", "tooling"]
---

`flutter devices` 卡住時，最有用的訊號是「device 清單是否穩定」。這次的關鍵訊號是連續兩次掃描從 `Found 4 connected devices` 變成 `Found 3 connected devices`，再加上 `Error -2 retrieving device properties for sdk gphone64 arm64`。這代表 ADB server 看得到某個 emulator entry，但對該 entry 的 property 查詢已經不穩定。

這類狀態可以稱為 Android emulator 半活（zombie）：emulator host process 還在、ADB 清單仍殘留 device，但 emulator 內的 `adbd` 或 Android system 已停止回應。Flutter 在掃描階段會對每個 Android device 查 properties，掃描到這個半活 device 就卡在 timeout。

---

## 事故場景

事故場景的核心是「Flutter 指令看似卡住，其實卡在下游 device property 查詢」。連續跑 `flutter devices` 時，輸出長這樣：

```text
$ flutter devices
Found 4 connected devices:
Error -2 retrieving device properties for sdk gphone64 arm64:
[卡住]

$ flutter devices
Found 3 connected devices:
[繼續卡]
```

這段輸出有兩個值得注意的點：

1. `Error -2 retrieving device properties for sdk gphone64 arm64:` 訊息出現後仍繼續等待，代表 Flutter 沒有在第一個 device 失敗時 fail-fast
2. 第一次 `Found 4`、第二次 `Found 3`，代表 device 數在兩次掃描之間自己少了 1

`sdk gphone64 arm64` 是 Android Studio AVD 預設模板（Google Phone 64-bit ARM）建出來的 emulator 顯示名稱、macOS 上跑 Android system image 都會看到這個。

### 為什麼計數變化是關鍵徵兆

device 數從 4 變 3，代表 ADB 對某個 emulator 的狀態判斷在兩次查詢之間變了。ADB server 內部追蹤每個 device 的狀態（`device` / `offline` / `unauthorized` / `no permissions`）；半活 emulator 在第一次掃描時仍被列在 `Found 4`，第二次掃描時可能已被標成 offline 或從候選清單移除，所以掉到 `Found 3`。

判讀訊號是「同一條 list 指令連跑兩次，device 數或 device 狀態自己變」。正常穩定狀態下，清單應該保持一致；清單漂移代表 ADB server 對某個 entry 的看法不穩定，下一步要先找出那個 entry，再決定是否重啟 ADB 或 emulator。

---

## 為什麼 flutter devices 會卡住

`flutter devices` 的責任是把每個候選 device 補成 Flutter 可用的 target，而不只是印出 `adb devices` 的結果。Flutter 對每個 ADB 看得到的 Android device 還要做幾件事：

1. 跑 `adb shell getprop ro.product.cpu.abi` 拉 ABI
2. 跑 `adb shell getprop ro.build.version.sdk` 拉 SDK level
3. 跑 `adb shell getprop ro.product.model` 拉裝置型號
4. 視情況跑 `adb shell` 其他指令確認 Flutter 支援度

這些是同步、序列化、有 timeout 的呼叫；timeout 通常設得相對寬鬆，讓慢一點的真機也能跑通。當其中一個 device 是 zombie 狀態：

- `adb shell getprop ...` 送出後，ADB 把指令轉發給 emulator 內的 `adbd`
- `adbd` 收到了但 Android system 沒回應，或 emulator process 整個卡住沒在處理 ADB request
- Flutter 端等 timeout、再 retry、再等更長 timeout，看起來就是「整個指令卡住」

`Error -2 retrieving device properties` 是其中一次嘗試 timeout 拿到的訊息（`-2` 是 Dart `ProcessException` 對應 `adb` exit code 的內部映射）。Flutter 仍會繼續掃描其他 device，所以使用者看到的是「印出錯誤訊息 + 繼續卡」。

---

## 為什麼是半活狀態

Android emulator 在 macOS 上的結構大致是：

```text
qemu-system-aarch64 (host process)
  ├─ Android kernel
  ├─ Android system services
  └─ adbd (在 emulator 內部，跟 host ADB server 對接)
```

半活狀態指的是「host process 還在，但 device 內部服務已無法完成 ADB request」。完全正常時 emulator 跑得動、ADB 也通；完全退出時 emulator process 已結束、ADB 清單看不到它。半活介於兩者之間：

- qemu host process 還在（活著）
- emulator 內的某個環節卡住（Android system 沒在 schedule、或 adbd 卡在某個 mutex）
- ADB server 還記得有這個 device，尚未穩定 evict
- 任何 `adb shell` 指令都打不通

常見成因：

- **Quick Boot snapshot 還原失敗或部分還原**——AVD 預設關機是 quick boot（存 snapshot），下次開機從 snapshot 還原；snapshot 跟當前 host kernel / hypervisor 狀態不相容時會半開機
- **macOS 從 sleep 喚醒後 hypervisor framework 重置**——emulator 是用 Hypervisor.framework，喚醒後虛擬 CPU 可能停在奇怪 state
- **host 端記憶體壓力導致 emulator 被 swap 嚴重**——表面看起來像卡，其實是在等 page fault

這一層的操作目標是恢復工具鏈，而不是追到每個 emulator 內部 race condition。若症狀符合清單漂移與 property 查詢 timeout，先按恢復順序處理；只有反覆發生時，再追 AVD snapshot、system image 或 host 資源壓力。

---

## 恢復順序（從輕到重）

恢復順序的核心是先重置最小邊界，再逐層擴大。每一步都要重新跑一次 `flutter devices` 或 `adb devices`，確認是否已經恢復，避免直接砍掉 emulator 或清資料。

```bash
# 1. 看 ADB 對每個 device 的狀態
adb devices
# 看到 offline / no device / unauthorized 等異常狀態 → 先鎖定該 device
```

如果有 device 顯示 `offline`，或正常列出但實際打不通，先重啟 ADB server：

```bash
# 2. 重啟 ADB server（只重置 host 端 ADB session）
adb kill-server && adb start-server
adb devices
# 多數狀況下，ADB 重啟後對該 device 的查詢會 fail-fast，flutter devices 會恢復
```

如果 ADB 重啟後仍打不通該 emulator，再處理 emulator process：

```bash
# 3. 對特定 emulator 發 emu kill（讓它優雅關閉）
adb -s emulator-5554 emu kill   # 把 5554 換成實際 port

# 4. 還在的話，終止 qemu process
pkill -f qemu-system-aarch64
```

長期修復路由是清掉不穩定的 snapshot。開 Android Studio → **AVD Manager** → 該 emulator 旁邊的小箭頭 → **Cold Boot Now**（避免 Quick Boot）。如果冷啟動後仍反覆壞，選 **Wipe Data** 把 snapshot 與 emulator 內資料整個清掉。

---

## 通用診斷思維

工具鏈卡住的診斷核心是先區分「上游 CLI 壞掉」還是「下游 target 沒回應」。`flutter` / `adb` 指令卡住時，先用清單穩定性與 device 識別碼定位下游狀態，再決定重啟邊界。

1. **觀察「同一指令連跑兩次結果是否一致」**：不一致（device 數變、訊息變）等於某層狀態不穩定
2. **訊息裡有 device 識別碼就釘住它**：`sdk gphone64 arm64`、`emulator-5554`、序號等都是 ADB 層的識別，可直接拿來 `adb -s <id> ...` 局部診斷
3. **從外往內排除**：ADB server → 個別 device → emulator process → emulator 內 system，逐層重啟
4. **重啟邊界越大、副作用越大**：`adb kill-server` 只影響 ADB session（其他 device 連線會斷一下），`pkill qemu` 直接砍 emulator，`Wipe Data` 連 emulator 內的資料都清。能用輕量手段解決就停在那層

---

## 操作判準

1. **「device 數兩次掃描之間自己變」是 zombie emulator 的關鍵徵兆**：計數變化代表 ADB 內部狀態不穩定
2. **`Error -2 retrieving device properties` 是 property 查詢失敗訊號**：Flutter 仍可能繼續處理其他 device，結果是「印出錯誤訊息但繼續卡」
3. **`adb kill-server && adb start-server` 是輕量首選**：它只重置 ADB session，不動 emulator 本身，多數狀況下可讓壞 device fail-fast
4. **半活狀態跟 application code 層級不同**：先把工具鏈狀態釐清，再回到剛改的程式碼

---

## 適用範圍

這個診斷思維不限於 Android emulator：

- iOS Simulator 卡住時 `xcrun simctl list` 印不出來——同樣的「指令卡 + 訊息看似 fatal 但 process 仍存在」結構
- `flutter devices` 對任何 device（含 iOS、Web、desktop）的查詢都會走類似的「列出 → 逐個 query property」流程、任一層卡都會表現為類似症狀
- 廣義地說，任何「server 維護一份 client 清單 + 對每個 client 做同步呼叫」的架構（k8s `kubectl get pods` 對 zombie node、docker `docker ps` 對掛掉的 container runtime 等）都有同款 failure mode

辨認規則一致：**list 指令連跑兩次結果不一致 → 維護清單的 server 對某個 entry 的看法不穩定 → 找出那個 entry 局部處理**。這條規則的邊界是：如果清單穩定但操作失敗，問題更可能在該 target 的權限、版本或 runtime 狀態，需要改走對應工具的細部診斷。
