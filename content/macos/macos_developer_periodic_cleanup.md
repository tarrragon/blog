---
title: "開發機的定期空間清理：專案產物、依賴快取、並存版本與虛擬磁碟的判讀"
date: 2026-10-23
slug: "macos_developer_periodic_cleanup"
description: "開發機的佔用依「刪除之後由誰重建」分類，每一類各自的判斷依據與檢查指令；涵蓋專案編譯產物、跨專案依賴快取、Gradle／NDK／模擬器映像這類並存的工具鏈版本、容器虛擬磁碟，以及刪除前要先辨識出來的被忽略機密檔。"
tags: ["macos", "disk-space", "android", "flutter", "xcode", "docker", "tooling"]
---

這篇整理在 macOS 開發機上定期檢查磁碟佔用時，各類佔用的判斷依據與檢查指令，範圍涵蓋 Flutter、Android、iOS 與容器工具鏈留下的資料。磁碟已經滿載、需要從頭定位大戶時的排查順序在 [macOS 磁碟空間被吃光的診斷流程](../macos_disk_space_diagnosis/)，這篇接在定位之後，判斷定位出來的每一項是否可以刪除、刪除之後會發生什麼。

## 佔用來源依刪除後的重建者分類

判斷一項佔用是否可以刪除，依據是刪掉之後由誰把它重建回來。開發機上的大戶依這個依據分成四類，每一類的刪除代價各不相同：

| 類別               | 刪除後由誰重建                       | 刪除的代價                                     |
| ------------------ | ------------------------------------ | ---------------------------------------------- |
| 專案編譯產物       | 下次 build 由建置工具重新產生        | 下一次 build 變慢                              |
| 跨專案依賴快取     | 下次 build 由套件管理器重新下載      | 下一次 build 變慢，並消耗網路流量              |
| 並存的工具鏈版本   | 專案指定該版本時由建置工具或人重新裝 | 被刪的版本若仍有專案指定，需要重新下載或安裝   |
| 狀態資料與虛擬磁碟 | 沒有人會重建                         | 資料直接消失：容器裡的資料庫、App 的登入與設定 |

這張表的作用是把「能不能刪」這個問題換成兩個可以查證的問題：這一項屬於哪一類，以及屬於並存版本那一類時，目前是否還有專案指定它。編譯產物與依賴快取刪除之後由工具自動重建，代價只有時間；並存版本的代價取決於是否還有專案指定它，狀態資料的代價取決於裡面是否還有要留的資料，這兩類的刪除前要各自查證。

## 專案目錄內的編譯產物

專案目錄裡的編譯產物是建置工具的輸出與中間檔，原始碼在，建置工具就能把它們完整產生回來。Flutter 專案常見的有 `build/`（APK、iOS app 與各平台的編譯輸出）、`.dart_tool/`（套件解析結果與 build_runner 的中間檔）、`android/.gradle/`（該專案的 Gradle 快取）、`ios/Pods/`（CocoaPods 下載的 iOS 依賴），以及用 `--split-debug-info` 輸出的符號檔目錄。不再開發的專案，這些產物常常比原始碼大兩個量級以上。

找出一個專案有哪些產物，最可靠的清單是 git 自己的忽略清單。編譯產物幾乎都寫在 `.gitignore` 裡，所以列出被忽略的路徑、再按實際佔用排序，就得到這個專案的產物清單：

```bash
# 在專案根目錄執行：列出被 .gitignore 忽略的路徑，依實際佔用由大到小排序
git status --ignored --porcelain | grep '^!!' | sed 's/^!! //' \
  | xargs -I{} du -sh "{}" 2>/dev/null | sort -rh | head -20
```

`--porcelain` 讓輸出固定成機器可讀的格式，被忽略的路徑以 `!!` 開頭；`sed` 去掉這個前綴之後交給 `du` 量實際佔用。`head -20` 的數字只控制列出幾項，專案的忽略項目多時調大。

這份清單裡混著兩種性質相反的檔案。`.gitignore` 排除一個檔案的理由有兩種：它是可以重建的產物，或者它是不能進版控的機密。Android 的簽章金鑰（`*.jks`、`*.keystore`、`key.properties`）、`.env` 這類環境變數檔、本機的設定檔，都因為屬於機密而被忽略，而它們在本機上常常是唯一的一份。所以 `git clean -fdX`（刪除全部被忽略的檔案）對產物有效，同時也會刪掉這些機密；刪除前先預演一次，逐項讀過清單：

```bash
# -n 只列出會被刪除的項目、不實際刪除；-d 包含目錄；-X 只處理被忽略的檔案
git clean -ndX
```

清單裡出現金鑰、`.env` 或任何不認得的檔案時，改成逐個目錄指名刪除（例如 `rm -rf build .dart_tool android/.gradle ios/Pods`），讓機密留在原位。一個專案要封存而簽章不再使用時，金鑰也可以刪；仍要發版的專案，金鑰要另外備份，因為新金鑰簽出來的 APK 無法覆蓋安裝在用舊金鑰簽章的裝置上。專案停止開發、要封存到遠端時，被忽略的檔案裡還可能有該保存的文件與腳本，盤點與搬遷的流程在 [停止開發的專案封存](/work-log/project_archive_before_cleanup/)。

`flutter clean` 能清掉 `build/` 與 `.dart_tool/`，它需要專案指定的 Flutter SDK 能正常執行；用 fvm 固定版本的專案，SDK 被移除之後這條指令就跑不起來，這時直接刪目錄的效果相同。專案底下另有本地 plugin（例如 `packages/<plugin>/`）時，每個 plugin 有自己的 `.dart_tool/` 與 Gradle 快取，根目錄的 `flutter clean` 涵蓋不到它們。

## 跨專案共用的依賴快取

依賴快取是套件管理器下載過的套件，存在家目錄底下供所有專案共用。刪除快取不會讓任何專案失效：下次 build 時套件管理器發現快取裡沒有，就重新下載。代價是那一次 build 的時間與網路流量，所以清理快取適合在網路穩定、近期沒有趕工的時候做。

各工具的快取位置與清理方式：

| 快取                                    | 預設位置                                | 清理方式                                    |
| --------------------------------------- | --------------------------------------- | ------------------------------------------- |
| Gradle 依賴與 build script 編譯結果     | `~/.gradle/caches`                      | 停掉 Gradle daemon 之後刪除目錄             |
| Dart 套件                               | `~/.pub-cache`                          | `dart pub cache clean`                      |
| Dart analysis server 的分析快取         | `~/.dartServer`                         | 關掉 IDE 之後刪除目錄，下次開專案時重新分析 |
| Python uv 套件                          | `~/.cache/uv`                           | `uv cache clean`                            |
| npm 套件                                | `~/.npm`                                | `npm cache clean --force`                   |
| Xcode 的編譯產物（所有 Xcode 專案共用） | `~/Library/Developer/Xcode/DerivedData` | 關掉 Xcode 之後刪除目錄                     |

工具自帶清理指令的，用工具的指令：工具知道快取裡哪些檔案正被鎖定、哪些是索引，直接刪目錄有機會在工具執行中刪掉它正在讀寫的檔案。Gradle 沒有清理指令，所以刪 `~/.gradle/caches` 前要確認沒有 daemon 在跑——daemon 是常駐的背景程序，持有快取目錄裡的檔案鎖，在它執行時刪除會讓正在進行的 build 讀到半套快取：

```bash
# 列出執行中的 Gradle daemon；有輸出時，到對應專案執行 ./gradlew --stop 或結束該程序
pgrep -fl GradleDaemon
```

`~/.gradle` 底下另有兩個目錄不屬於快取。`~/.gradle/jdks` 是 Gradle toolchain 自動下載的 JDK，刪了會在下次 build 時重抓；`~/.gradle/wrapper/dists` 是各版本的 Gradle 本體，屬於並存版本，判斷方式見〈並存的工具鏈版本〉。

## 並存的工具鏈版本

並存版本是同一個工具的多個版本同時裝在機器上。它們累積的機制相同：每個專案各自指定要用的版本，建置工具照指定下載，而沒有任何工具會在專案改用新版之後移除舊版。一台用了幾年的開發機，Gradle 本體可以累積十幾個版本、NDK 四五個、模擬器映像七八個，每一個都在當初某個專案需要時被裝進來。

判斷一個版本是否可以刪除，要查目前是否還有專案指定它。被刪的版本若仍被指定，下次 build 時建置工具會重新下載；所以刪錯的代價是時間，查證的目的是避免反覆下載同一個版本。

### Gradle 本體

Gradle 的版本由每個專案的 `gradle/wrapper/gradle-wrapper.properties` 的 `distributionUrl` 指定，wrapper 照這個網址下載 Gradle 本體到 `~/.gradle/wrapper/dists/`。列出所有專案指定的版本：

```bash
# 引數 ~/project 換成存放專案的根目錄；Flutter 專案的 wrapper 在 android/ 底下，所以搜尋深度要涵蓋兩層以上
find ~/project -name gradle-wrapper.properties -not -path '*/build/*' \
  -exec grep -h distributionUrl {} \; | sort | uniq -c
```

`dists/` 裡不在這份清單上的版本可以刪。目錄名稱裡有一類要單獨辨識：目錄底下只有 `.zip.part` 與 `.zip.lck` 的，是下載中斷的殘檔；名稱像 `gradle-REPLACEME-all` 的，是某個專案範本的佔位字串沒有被替換，wrapper 照著字面去下載而留下的目錄。這兩類不會有專案能用，直接刪。

### Android NDK

NDK 版本由專案的 `android/app/build.gradle` 的 `ndkVersion` 指定。Flutter 專案多半寫成 `ndkVersion = flutter.ndkVersion`，版本由使用中的 Flutter SDK 決定，所以同一個專案換了 Flutter 版本，要的 NDK 也跟著換。Android Gradle Plugin 在 build 時發現指定的 NDK 沒裝，會自動下載，所以保留最新版、刪除其餘的代價是遇到舊版需求時多一次下載。

辨識最新版要看主版本號，build 號只反映發行的先後。修補版可能在下一個主版本之後才發行，例如某個 28.2 的 build 號就比 29.0 的大，按主版本號排序 29 仍是最新。

NDK、模擬器映像這類 Android SDK 元件用 `sdkmanager` 移除，它會同時更新 SDK 的安裝紀錄。套件名稱要完整寫出，先列出已安裝的套件取得正確名稱：

```bash
# 路徑為 Android Studio 的預設 SDK 位置；自訂過 ANDROID_HOME 的以該環境變數為準
SDKMANAGER=$(ls -d ~/Library/Android/sdk/cmdline-tools/*/bin/sdkmanager | head -1)
"$SDKMANAGER" --list_installed

# 引數是 --list_installed 輸出的第一欄，逐字複製
"$SDKMANAGER" --uninstall "ndk;25.1.8937393"
```

`--uninstall` 的套件名稱對不上時，`sdkmanager` 只印一行 warning 就結束、回傳值仍是成功，所以移除之後要回到 SDK 目錄確認資料夾已經消失。模擬器映像特別容易對不上，因為名稱包含 ABI：同一個 API 版本的 `arm64-v8a` 與 `x86` 是兩個套件，Apple Silicon 機器上留著的舊映像常是早年裝的 `x86` 版本。

### Android 模擬器映像

模擬器映像（system image）與模擬器裝置（AVD）分開存放：映像在 SDK 的 `system-images/` 底下，AVD 在 `~/.android/avd/`。刪除一台 AVD 只會刪掉它自己的資料，它使用的映像留在原處，所以 AVD 刪光之後，映像仍可能佔著十幾 GB。判斷映像是否可以刪除，看目前的 AVD 用到哪幾個：

```bash
# 列出目前所有 AVD；輸出為空代表沒有任何 AVD 在使用映像
~/Library/Android/sdk/emulator/emulator -list-avds

# 每台 AVD 的設定檔裡，image.sysdir.1 指向它使用的映像目錄
grep -h 'image.sysdir' ~/.android/avd/*.avd/config.ini
```

沒有被任何 AVD 指向的映像，同樣用 `sdkmanager --uninstall` 移除，套件名稱取自 `--list_installed` 的輸出。要保留一個映像以便日後建 AVD 時，保留最新 API 版本的一般版即可：名稱帶 `ps16k` 的是 16KB 記憶體分頁的測試版本，帶 `tablet` 的是平板預設組態，只在需要測試這兩種情境時才用得到。

### iOS 模擬器 runtime

iOS 模擬器的 runtime 以磁碟映像的形式安裝，掛載成獨立的 APFS 卷。`du` 量 `/Library/Developer/CoreSimulator/Volumes` 會把掛載進來的內容算進去，量到的數字比實際佔用大，判斷佔用要看 `simctl` 回報的映像大小。runtime 的架構與為什麼一組要十幾 GB，在 [iOS Simulator Runtime 架構](../macos_ios_simulator_runtime_architecture/)。

```bash
# 列出已安裝的 runtime 與各自的映像大小；每一行的 UUID 是刪除時的引數
xcrun simctl runtime list

# 引數換成要刪除的 runtime 的 UUID；狀態會先變成 Deleting，背景完成後才釋放空間
xcrun simctl runtime delete <runtime-uuid>

# 刪掉 runtime 已不存在的模擬器裝置
xcrun simctl delete unavailable
```

模擬器裝置的資料另外存在 `~/Library/Developer/CoreSimulator/Devices`，每一台裝置一個目錄，裡面是裝進去的 App 與它們的資料。刪除 runtime 後，屬於它的裝置會變成 unavailable，用最後那條指令清掉。完整的移除流程與 Xcode GUI 的限制見 [移除多餘的 iOS Simulator Runtime](../macos_remove_redundant_ios_simulators/)。

### Flutter SDK

用 fvm 管理 Flutter 版本時，每個版本是一份完整的 SDK，存在 `~/fvm/versions/`。專案用的版本寫在專案根目錄的 `.fvmrc`（舊版 fvm 是 `.fvm/fvm_config.json`），查法與 Gradle 相同——列出所有專案指定的版本，不在清單上的用 `fvm remove <版本>` 移除。

## 容器與虛擬機的虛擬磁碟

OrbStack、Docker Desktop 這類容器工具把整台 Linux 虛擬機的磁碟存成主機上的一個映像檔，容器、image、volume 全部住在裡面。這個映像檔是 sparse file（稀疏檔）：`ls -l` 顯示的是它宣告的容量上限，`du` 量到的才是實際寫入的區塊，兩者可以差到好幾倍以上。

映像檔屬於狀態資料：刪除它等於刪掉虛擬機裡全部的容器與資料庫，沒有任何工具會重建。縮小它要從虛擬機裡面清：

```bash
# 列出 image、容器、volume 與 build cache 各佔多少，以及其中可回收的量
docker system df

# 刪除停止的容器、沒有容器使用的 image、未使用的網路與 build cache
docker system prune -a

# volume 預設不在 prune 範圍內；確認裡面沒有要留的資料庫之後才加這個選項
docker system prune -a --volumes
```

`-a` 讓 prune 也刪除沒有任何容器使用的 image，少了它只會刪除沒有標籤的懸空 image。虛擬機裡釋放的空間要經過虛擬化層才回到主機，回收的時機依工具而定，清完之後用 `du -sh` 量一次映像檔確認是否變小。

同一類的還有 Claude 桌面版的 `~/Library/Application Support/Claude/vm_bundles`：它是本地沙箱功能使用的虛擬機映像，沒有使用那個功能時可以刪，刪除與否的判讀見 [macOS 磁碟空間被吃光的診斷流程](../macos_disk_space_diagnosis/) 裡處理佔用大戶的那一節。

## App 的狀態資料與更新殘留

`~/Library` 底下屬於 App 的資料多半是狀態資料，刪除後 App 會回到初次安裝的狀態。開發機上有兩種可以放心刪的特例。

自己開發的 App 在本機執行過 macOS 版本時，沙箱會在 `~/Library/Containers/<bundle-id>` 建立它的資料目錄。Flutter 專案的 bundle id 預設是 `com.example.<專案名>`，專案停止開發之後這個目錄就只剩測試資料。刪除時目錄裡的資料可以刪掉，而目錄本身與根部的 `.com.apple.containermanagerd.metadata.plist` 受系統保護，一般權限執行 `rm` 會回報 `Operation not permitted`；那個檔案只有幾十 KB，留著不影響任何事，要清掉需要給終端機「完整取用磁碟」權限。沙箱容器的結構見 [App Sandbox 與 Containers 架構](../macos_app_sandbox_container/)。

App 自動更新程式留下的安裝包是另一種特例，例如 VS Code 的 `~/Library/Caches/com.microsoft.VSCode.ShipIt`。更新程式下載新版、替換完成之後，舊的安裝包與暫存目錄常常留在原處，下次更新時更新程式會重新下載需要的檔案。

## 定期檢查清單

以下清單依「刪除代價由低到高」排列，代價低的項目可以直接清，代價高的項目每一項都附了刪除前要查證的事：

- **不再開發的專案的編譯產物**：在專案根目錄跑 `git clean -ndX` 預演，確認清單裡沒有金鑰與 `.env` 之後逐個目錄刪除。
- **依賴快取**：`~/.gradle/caches`（先跑 `pgrep -fl GradleDaemon` 確認沒有 daemon）、`~/.pub-cache`、`~/.dartServer`、`~/.cache/uv`、`~/.npm`、Xcode 的 DerivedData，用工具自帶的指令或刪除目錄。
- **App 更新殘留**：`~/Library/Caches` 底下名稱帶 `ShipIt`、`updater` 的目錄。
- **Gradle 本體的舊版**：用 `distributionUrl` 列出各專案指定的版本，刪除 `~/.gradle/wrapper/dists` 裡不在清單上的版本與 `.part` 殘檔。
- **NDK 舊版**：保留最新主版本，用 `sdkmanager --list_installed` 取得套件名稱後 `--uninstall`，移除後確認資料夾已消失。
- **Android 模擬器映像**：`emulator -list-avds` 與 AVD 設定檔的 `image.sysdir.1` 查出使用中的映像，其餘移除。
- **iOS 模擬器 runtime**：`xcrun simctl runtime list` 列出版本，刪除不再測試的版本，再跑 `xcrun simctl delete unavailable`。
- **Flutter SDK**：對照各專案的 `.fvmrc`，`fvm remove` 移除沒有專案使用的版本。
- **自己開發的 App 的沙箱容器**：`~/Library/Containers/com.example.*` 這類開發用 bundle id 的目錄，確認專案已停止開發。
- **容器工具的虛擬磁碟**：`docker system df` 看可回收量，`docker system prune -a`；加 `--volumes` 前確認沒有要留的資料庫。

刪除完成之後，`df` 回報的可用空間可能要過一段時間才會增加，有時在刪除後的幾分鐘內甚至會減少：APFS 的本地快照與 purgeable 空間在背景浮動，刪除的空間不會即時反映在可用空間上。本地快照與 purgeable 讓可用空間浮動的機制，在 [macOS 磁碟空間被吃光的診斷流程](../macos_disk_space_diagnosis/)。

## 延伸閱讀：佔用的定位、App 層聚合與 APFS 的空間計算

這篇處理的是已經知道大戶在哪裡之後的判斷。大戶還沒定位時，從 container 可用空間、本地快照到逐層 `du` 的排查順序在 [macOS 磁碟空間被吃光的診斷流程](../macos_disk_space_diagnosis/)；想把 `~/Library` 底下散落的佔用聚合回各個 App、看出哪個 App 該清，用 [macOS App 聚合佔用報告](../macos_app_footprint_report/)。`du`、`df` 與 `diskutil` 對同一顆磁碟回報不同數字的原因，在 [APFS 卷結構與空間池](../macos_apfs_volume_structure/)。
