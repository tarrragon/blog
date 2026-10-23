---
title: "開發機的定期空間清理：專案產物、快取、並存的工具鏈版本、虛擬磁碟與 App 沙箱容器的判讀"
date: 2026-10-23
slug: "macos_developer_periodic_cleanup"
description: "開發機的佔用依「刪除之後由誰重建、刪除前要查證什麼」分類，每一類各自的判斷依據與檢查指令；涵蓋專案編譯產物、套件與 App 的快取、Gradle／NDK／模擬器映像／Flutter SDK 這類並存的工具鏈版本、容器的虛擬磁碟、模擬器裝置與自己開發的 App 的沙箱容器，以及刪除前要先辨識出來的被忽略檔。"
tags: ["macos", "disk-space", "android", "flutter", "xcode", "docker", "tooling"]
---

這篇整理在 macOS 開發機上定期檢查磁碟佔用時，各類佔用的判斷依據與檢查指令，範圍涵蓋 Flutter、Android、iOS 與容器工具鏈留下的資料。磁碟已經滿載、需要從頭定位大戶時的排查順序在 [macOS 磁碟空間被吃光的診斷流程](../macos_disk_space_diagnosis/)，這篇接在定位之後，判斷定位出來的每一項是否可以刪除、刪除之後會發生什麼。

## 佔用來源依刪除後的重建者分類

判斷一項佔用是否可以刪除，依據是刪掉之後由誰把它重建回來，以及因此刪除前要先查證什麼。開發機上的大戶依這個依據分成四類：

| 類別               | 刪除後由誰重建                                                       | 刪除前要查證的事                                 | 刪除的代價                               |
| ------------------ | -------------------------------------------------------------------- | ------------------------------------------------ | ---------------------------------------- |
| 專案編譯產物       | 下次 build 由建置工具重新產生                                        | 清單裡是否混著被忽略的機密、文件或平台專案       | 下一次 build 變慢                        |
| 快取               | 產生它的套件管理器、IDE 或 App，從原本的來源重新下載或重新產生       | 重建的來源是否還在                               | 下一次使用變慢，有些要消耗網路流量       |
| 並存的工具鏈版本   | 還有設定指向它時，Gradle 與 NDK 由建置工具自動下載，其餘由人重新安裝 | 是否還有仍在開發的專案、裝置設定或測試需求指向它 | 被刪的版本若仍被指向，需要重新下載或裝回 |
| 狀態資料與虛擬磁碟 | 沒有人會重建                                                         | 裡面的資料是否還有人要                           | 資料直接消失                             |

狀態資料指程式執行時寫下、無法從原始碼或網路重新取得的資料：資料庫內容、登入狀態、設定、使用者建立的檔案、模擬器裝置裡裝的 App 與資料。它沒有重建者，所以刪除的判斷依據換成「這些資料還有沒有人要」。

編譯產物與快取刪除之後由工具自動重建，前提是重建所需的來源還在：產物要原始碼在，快取要原本的下載來源還能連得上。並存版本要查是否還有設定指向它，狀態資料要查是否還有人要，各工具的查法寫在下列各節。

## 專案目錄內的編譯產物

專案目錄裡的編譯產物是建置工具的輸出與中間檔，原始碼在，建置工具就能把它們完整產生回來。Flutter 專案常見的有 `build/`（APK、iOS app 與各平台的編譯輸出）、`.dart_tool/`（套件解析結果與 build_runner 的中間檔）、`android/.gradle/`（該專案的 Gradle 快取）、`ios/Pods/`（CocoaPods 下載的 iOS 依賴），以及 IDE 與程式碼索引工具的目錄（`.idea/`、`*.iml`）。不再開發的專案，這些產物常常佔掉專案目錄的絕大部分空間。

用 `--split-debug-info` 輸出的符號檔目錄與混淆對照檔（`app.*.map.json`）是例外。已發佈、經過混淆的版本，要靠當初那次 build 的符號檔才能把崩潰堆疊還原成原始碼位置，重新 build 產生的符號檔對不上已發佈的 binary。所以裝置上還有使用者在跑那個版本時，它們屬於狀態資料，要和簽章金鑰一起備份。

找出一個專案有哪些產物，起點是 git 的忽略清單。編譯產物幾乎都寫在 `.gitignore` 裡，所以列出被忽略的路徑、再按實際佔用排序，就得到產物的候選清單：

```bash
# 在專案根目錄執行：列出被 .gitignore 忽略的路徑，依實際佔用由大到小排序
git status --ignored --porcelain -z | tr '\0' '\n' | grep '^!!' | sed 's/^!! //' \
  | tr '\n' '\0' | xargs -0 du -sh | sort -rh | head -20
```

加上 `--porcelain` 時，git 把輸出固定成機器可讀的格式，被忽略的路徑以 `!!` 開頭；`-z` 讓 git 以 NUL 字元分隔每一項並且原樣輸出路徑。少了 `-z`，git 會把中文路徑轉成 `"\346\226\207..."` 這種跳脫字串，`du` 找不到這個路徑，那一項就從清單上消失；`xargs -0` 對應 NUL 分隔，路徑裡有空白或引號也能正確傳給 `du`。`head` 後面的 20 是列出的項數，忽略項目多時調大。

這份清單裡混著性質不同的檔案。`.gitignore` 排除一個檔案的理由有三種：

- **可以重建的產物**：`build/`、`.dart_tool/` 這類編譯產物目錄，刪除之後由建置工具產生回來。
- **不能進版控的機密與本機設定**：Android 的簽章金鑰（`*.jks`、`*.keystore`、`key.properties`）、`.env` 這類環境變數檔，以及 `local.properties` 這類寫著本機路徑的設定。它們在本機上常常是唯一的一份。
- **範圍過寬而誤被排除的內容**：`/doc/`、`/scripts/`、`/macos/` 這類整個目錄被忽略的規則，可能連設計文件、工具腳本或平台專案本體一起排除了。

`git clean -fdX`（刪除全部被忽略的檔案）對產物有效，同時也會刪掉機密與誤被排除的內容，所以刪除前先預演一次：

```bash
# 預演：-n 只列出會被刪除的項目、不實際刪除；-d 包含目錄；-X 只處理被忽略的檔案
# -c core.quotePath=false 讓中文路徑原樣顯示，否則會顯示成跳脫字串而無法辨識
git -c core.quotePath=false clean -ndX
```

預演清單只列到目錄名稱，目錄名稱判斷不了裡面是否為產物：`macos/`、`web/` 可能只有 Flutter 自動產生的檔案，也可能是含 `Runner.xcodeproj` 的平台專案本體。所以清單裡的每個目錄，先用 `find <目錄> -type f` 看裡面的檔案再判斷，判斷方式在 [停止開發的專案封存](/work-log/project_archive_before_cleanup/) 的〈誤被忽略的內容〉。確認清單上只有產物之後，才用 `git clean -fdX` 一次刪除；有金鑰、`.env`、文件、腳本、平台專案或任何不認得的檔案時，改成逐個目錄指名刪除（例如 `rm -rf build .dart_tool android/.gradle ios/Pods`），讓其餘檔案留在原位。專案停止開發、要封存到遠端時，誤被排除的內容要先納入版控，金鑰的去留也要在那時決定，盤點與搬遷的流程在同一篇封存文章。

`flutter clean` 能清掉 `build/` 與 `.dart_tool/`，它需要專案指定的 Flutter SDK 能正常執行；用 fvm（Flutter 的版本管理工具，見〈Flutter SDK〉）固定版本的專案，SDK 被移除之後這條指令就跑不起來，這時直接刪除 `build/` 與 `.dart_tool/` 的效果相同。專案底下另有本地 plugin（例如 `packages/<plugin>/`）時，每個 plugin 有自己的 `.dart_tool/` 與 Gradle 快取，根目錄的 `flutter clean` 涵蓋不到它們。

## 套件管理器、IDE 與 App 的快取

快取是工具為了下次不必重做而保存的結果：套件管理器下載過的套件、IDE 的分析結果、跨專案共用的編譯中間檔、App 下載的暫存檔。下次需要時，產生它的工具會發現快取裡沒有，從原本的來源重新下載或重新產生；代價是那一次的時間與網路流量，所以清理快取適合在網路穩定、近期沒有趕工的時候做。

刪除快取不讓專案失效的前提，是重建的來源還在。下列幾種快取的來源可能已經不在，刪除前要個別查證：

- **指向私有或即將停用主機的 git 依賴**：`pubspec.yaml` 的 `git:` 依賴會把整個倉庫 clone 進 `~/.pub-cache/git/`，主機停用之後，快取裡的那一份可能就是唯一的副本。
- **本機 build、沒有推上 registry 的 Docker image**：刪除之後只能從 Dockerfile 重新 build。
- **要由人重新安裝的工具**：例如 `dart pub global activate` 裝的 CLI 工具、Playwright 下載的瀏覽器（`~/Library/Caches/ms-playwright`，要重新執行 `npx playwright install`）。專案的 build 不會把它們裝回來。

清除快取也可能讓先前被快取掩蓋的建置問題浮現，機制與排查在 [Gradle Cache 掩蓋潛伏問題的邏輯](/work-log/gradle_cache_latent_bug/)。

各工具的快取位置與清理方式：

| 快取                                          | 預設位置                                          | 清理方式                                                       |
| --------------------------------------------- | ------------------------------------------------- | -------------------------------------------------------------- |
| Gradle 依賴與 build script 編譯結果           | `~/.gradle/caches`                                | 停掉 Gradle daemon 之後刪除目錄                                |
| Dart 套件、git 依賴與全域安裝的 Dart CLI 工具 | `~/.pub-cache`                                    | `dart pub cache clean`                                         |
| Dart analysis server 的分析結果               | `~/.dartServer`                                   | 關掉 IDE 之後刪除目錄，下次開專案時重新分析                    |
| fvm 下載 Flutter SDK 用的 git 快取            | `~/fvm/cache.git`                                 | 刪除目錄，下次 `fvm install` 時重新 clone                      |
| Python uv 套件                                | `~/.cache/uv`                                     | `uv cache clean`                                               |
| npm 套件                                      | `~/.npm`                                          | `npm cache clean --force`                                      |
| Xcode 的編譯中間檔（所有 Xcode 專案共用）     | `~/Library/Developer/Xcode/DerivedData`           | 關掉 Xcode 之後刪除目錄                                        |
| Xcode 實體裝置除錯的符號快取                  | `~/Library/Developer/Xcode/iOS DeviceSupport`     | 刪除目錄，下次接上同一台裝置除錯時重建                         |
| App 自動更新程式留下的安裝包                  | `~/Library/Caches/` 底下名稱帶 `ShipIt` 的目錄    | 刪除目錄，下次更新時更新程式重新下載需要的檔案                 |
| Claude 桌面版 Cowork 功能的本地沙箱虛擬機     | `~/Library/Application Support/Claude/vm_bundles` | 沒有使用 Cowork 時刪除目錄，下次開啟 Cowork session 時重新佈建 |

工具自帶清理指令的，用工具的指令：工具知道快取裡哪些檔案正被鎖定、哪些是索引，直接刪目錄有機會在工具執行中刪掉它正在讀寫的檔案。`dart pub cache clean` 會清掉整個 `~/.pub-cache`，包含 git 依賴與用 `dart pub global activate` 裝的 CLI 工具。

Gradle 沒有手動清理的指令。Gradle 會在背景自動刪除一段時間沒用過的快取項目（預設的保留天數與適用的 Gradle 版本，以 [Gradle 官方文件的目錄說明](https://docs.gradle.org/current/userguide/directory_layout.html) 中 cache cleanup 的段落為準），而手動刪 `~/.gradle/caches` 前要確認沒有 daemon 在跑——daemon 是常駐的背景程序，執行中的 build 正在讀寫快取目錄，這時刪除會讓那次 build 讀到半套快取：

```bash
# 列出執行中的 Gradle daemon；第一欄是 PID，命令列裡含有該 daemon 的 Gradle 版本
pgrep -fl GradleDaemon

# 在任一個使用該 Gradle 版本的專案執行（Flutter 專案在 android/ 目錄底下執行）；它會停掉同一版本的所有 daemon
./gradlew --stop
```

`./gradlew --stop` 停的範圍是「與這個 wrapper 同版本的 Gradle 啟動的所有 daemon」，跟在哪個專案執行無關；機器上同時有幾個版本的 daemon 在跑，就要對每個版本各執行一次，或用 `kill <PID>` 結束 `pgrep` 列出的程序。

`~/.gradle` 底下另有兩個目錄不屬於快取，兩者都是並存版本：`~/.gradle/wrapper/dists` 是各版本的 Gradle 本體，`~/.gradle/jdks` 是 Gradle toolchain 自動下載的 JDK，判斷方式見〈並存的工具鏈版本〉。

`~/Library/Caches` 以外，`~/Library` 底下屬於 App 的資料（`Application Support`、`Containers`）多半是狀態資料，刪除後 App 會回到初次安裝的狀態，判斷方式不同。表格裡的 `vm_bundles` 雖然放在 `Application Support`，內容是 Claude 桌面版下載的虛擬機映像、沒有使用者資料，App 會自己重新佈建，所以歸在快取；`~/Library` 各位置裡快取與狀態資料的分界，見 [macOS App 聚合佔用報告](../macos_app_footprint_report/)。

## 並存的工具鏈版本

並存版本是同一個工具的多個版本同時裝在機器上。它們累積的機制相同：每個專案各自指定要用的版本，建置工具照指定下載，而 NDK、Android SDK 元件、模擬器映像、iOS runtime、fvm 的 Flutter SDK 都沒有任何工具會在專案改用新版之後移除舊版。Gradle 本體與 Homebrew 的舊版套件同樣會累積，而兩者都有自動清理舊版的機制，只是清理要等工具本身執行過才會發生，各自的條件寫在下面對應的小節。

判斷一個版本是否可以刪除，要查目前是否還有設定指向它，而且指向它的專案是否還在開發：已經封存並驗證過、之後不會再 build 的專案，那個專案的設定不算數。指向它的設定依工具而不同：

| 版本                                  | 指向它的設定                                                         |
| ------------------------------------- | -------------------------------------------------------------------- |
| Gradle 本體                           | 各專案 `gradle-wrapper.properties` 的 `distributionUrl`              |
| Gradle toolchain 的 JDK               | 各專案建置設定裡的 `jvmToolchain` 或 `toolchain` 版本                |
| NDK                                   | 專案的 `ndkVersion`，Flutter 專案由 Flutter SDK 決定                 |
| Android SDK 的 platforms、build-tools | 專案的 `compileSdk` 與 Android Gradle Plugin 要求的 build-tools 版本 |
| Android 模擬器映像                    | 模擬器裝置（AVD）的設定檔                                            |
| iOS runtime                           | 是否還要在那個 iOS 版本上測試                                        |
| Flutter SDK                           | 各專案的 `.fvmrc` 與 fvm 的全域版本                                  |
| Homebrew 的舊版套件                   | 沒有設定指向舊版；Homebrew 每個套件只連結一個版本                    |

被刪的版本若仍被指向，Gradle 會在下次 build 時由 wrapper 重新下載，NDK 與 Android SDK 元件在符合〈Android NDK〉寫的條件時由 Android Gradle Plugin 重新下載；模擬器映像、iOS runtime 與 Flutter SDK 要由人手動裝回。

列出指向設定時，專案可能不只放在一個根目錄（Android Studio 預設建立在 `~/AndroidStudioProjects`），下列各節的 `find` 要對每個根目錄各跑一次。專案裡的巢狀 package（例如 `packages/` 底下的本地 plugin）可能有自己的 Gradle wrapper 與 `.fvmrc`，這兩項不決定 App 的建置，建置 App 時用的是 App 本身的設定；但 Android plugin 各自的 `compileSdk` 與 `ndkVersion` 在 build App 時同樣會用到，列 platforms 與 NDK 時要一起算。

### Gradle 本體與 toolchain 的 JDK

Gradle 的版本由每個專案的 `gradle/wrapper/gradle-wrapper.properties` 的 `distributionUrl` 指定，wrapper（專案裡的 `gradlew` 腳本，負責下載並啟動專案指定版本的 Gradle）照這個網址下載 Gradle 本體到 `~/.gradle/wrapper/dists/`。Gradle 執行時會在背景刪除閒置一段時間的舊版發行版（官方文件寫的預設是 30 天，以〈套件管理器、IDE 與 App 的快取〉引用的那份文件為準）。列出所有專案指定的版本：

```bash
# 引數 ~/project 換成存放專案的根目錄；-H 在每一行前面印出設定檔路徑，看得出是哪個專案指定的
find ~/project -name gradle-wrapper.properties -not -path '*/build/*' \
  -exec grep -H distributionUrl {} \;
```

`dists/` 裡不在這份清單上的版本可以刪。目錄名稱裡有一類要單獨辨識：目錄底下只有 `.zip.part` 與 `.zip.lck` 的，是下載中斷的殘檔；名稱像 `gradle-REPLACEME-all` 的，是某個專案範本的佔位字串沒有被替換，wrapper 照著字面去下載而留下的目錄。這兩類不會有專案能用，直接刪。

`~/.gradle/jdks` 底下每個 JDK 一個目錄，toolchain 是 Gradle 依專案建置設定指定的 JDK 版本自動下載並使用 JDK 的機制。對照各專案的 toolchain 版本，沒有專案指定的版本可以刪；目錄裡殘留的 `.tar.gz` 是下載後沒清掉的壓縮檔，直接刪：

```bash
# 引數 ~/project 換成存放專案的根目錄；列出各專案建置設定裡指定的 JDK 版本
find ~/project \( -name 'build.gradle*' -o -name 'gradle-daemon-jvm.properties' \) -not -path '*/build/*' \
  -exec grep -HE 'jvmToolchain|languageVersion|toolchainVersion' {} \;
```

### Android NDK

NDK 版本由專案的 `android/app/build.gradle`（新建的 Flutter 專案是 `build.gradle.kts`）的 `ndkVersion` 指定。Flutter 專案多半寫成 `ndkVersion = flutter.ndkVersion`，版本由使用中的 Flutter SDK 決定，值寫在 Flutter SDK 的 Gradle 外掛裡：

```bash
# 引數換成 Flutter SDK 的根目錄（fvm 管理的版本在 ~/fvm/versions/<版本> 底下）
# 新版 SDK 的值在 FlutterExtension.kt 的 val ndkVersion，舊版在 Groovy 檔的 String ndkVersion
grep -rnE 'val ndkVersion:|String ndkVersion =' <flutter-sdk>/packages/flutter_tools/gradle/

# 本機沒安裝的 Flutter 版本，從 fvm 的 git 快取查；<版本> 換成 Flutter 的版本 tag，例如 3.29.0
git -C ~/fvm/cache.git grep -nE 'val ndkVersion:|String ndkVersion =' <版本> -- packages/flutter_tools/gradle/
```

所以同一個專案換了 Flutter 版本，要的 NDK 也跟著換。對照各專案使用的 Flutter 版本（各專案的版本寫在 `.fvmrc`，列法見〈Flutter SDK〉）列出需要的 NDK，保留這些版本，其餘的刪除。專案指定的 Flutter 版本本機沒有安裝時，可以用上面第二條指令查出它要的 NDK；也可以不為那個專案保留 NDK：之後重新安裝那個 Flutter SDK、build 時，缺的 NDK 會自動下載。

自動下載的條件是 Android Gradle Plugin 4.2 以上、而且已經用 `sdkmanager --licenses` 接受過授權；授權沒接受過，build 會直接失敗。

比較 NDK 版本的新舊要看主版本號，版本號最後一段的 build 號只反映發行的先後：修補版可能在下一個主版本之後才發行，所以 `28.2.13676358` 的 build 號（13676358）比 `29.0.13599879` 的（13599879）大，而較新的仍是主版本號較大的 29.0。

NDK、platforms、build-tools、模擬器映像這類 Android SDK 元件用 `sdkmanager` 移除，它會同時更新 SDK 的安裝紀錄。套件名稱要完整寫出，先列出已安裝的套件取得正確名稱：

```bash
# 路徑為 Android Studio 的預設 SDK 位置；自訂過 ANDROID_HOME 的以該環境變數為準
# 沒有這個路徑時，在 Android Studio 的 SDK Manager > SDK Tools 勾選 Android SDK Command-line Tools
# 執行時回報找不到 Java 的，把 JAVA_HOME 指到 Android Studio 內建的 JDK
SDKMANAGER=~/Library/Android/sdk/cmdline-tools/latest/bin/sdkmanager
"$SDKMANAGER" --list_installed

# 引數是 --list_installed 輸出第一欄（Path）的值，逐字複製
"$SDKMANAGER" --uninstall "<--list_installed 第一欄的套件名稱>"
```

`--list_installed` 的版本欄標有 `rc` 的是預覽版。`--uninstall` 的套件名稱對不上時，`sdkmanager` 只印一行警告就結束、回傳值仍是成功，所以移除之後要回到 SDK 目錄確認資料夾已經消失。模擬器映像特別容易對不上，因為名稱包含 ABI（映像編譯成哪一種處理器指令集，Apple Silicon 是 `arm64-v8a`）：同一個 API 版本的 `arm64-v8a` 與 `x86` 是兩個套件，Apple Silicon 機器上留著的舊映像常是早年裝的 `x86` 版本。

### Android 模擬器映像

模擬器映像（system image，模擬器開機用的 Android 系統）與模擬器裝置（AVD，Android Virtual Device，一台模擬器的硬體設定與資料）分開存放：映像在 SDK 的 `system-images/` 底下，AVD 在 `~/.android/avd/`。刪除一台 AVD 只會刪掉它自己的資料，它使用的映像留在原處，所以 AVD 刪光之後，映像仍可能佔著十幾 GB。判斷映像是否可以刪除，看目前的 AVD 用到哪幾個：

```bash
# 列出目前所有 AVD；輸出為空代表沒有任何 AVD 在使用映像（SDK 路徑同 NDK 那一節）
~/Library/Android/sdk/emulator/emulator -list-avds

# 每台 AVD 的設定檔裡，image.sysdir.1 指向它使用的映像目錄
# 沒有任何 AVD 時，zsh 會回報 no matches found，代表沒有映像在使用
grep -h 'image.sysdir' ~/.android/avd/*.avd/config.ini
```

沒有被任何 AVD 指向的映像，同樣用 `sdkmanager --uninstall` 移除，套件名稱取自 `--list_installed` 的輸出。要保留一個映像以便日後建 AVD 時，保留最新 API 版本、符合測試需求的那一種：`google_apis_playstore` 與 `google_apis` 都有 Google Play 服務，測試登入、推播用任一種都可以；`google_apis_playstore` 另外內建 Play 商店、以正式金鑰簽章，不能取得 root 權限，要測試從 Play 商店安裝的流程時用它；`default` 是不含 Google 服務的原生 Android。名稱另外帶 `ps16k` 的是 16KB 記憶體分頁的測試版本，帶 `tablet` 的是平板預設組態，只在需要測試這兩種情境時才用得到。

### iOS 模擬器 runtime 與模擬器裝置

iOS 模擬器的 runtime 以磁碟映像的形式安裝，掛載成獨立的 APFS Container，裡面的卷掛在 `/Library/Developer/CoreSimulator/Volumes` 底下。`du` 量這個目錄會把掛載進來的內容算進去，量到的數字比實際佔用大；各 runtime 的實際佔用用 `simctl` 列出：

```bash
# 列出已安裝的 runtime；-v 才會逐項列出各自的映像大小（Size）、UUID 與最後使用時間（Last Used At）
xcrun simctl runtime list -v

# 部分 runtime 版本另有一份 Bundle DMG，存在這個目錄；不是 0B 時，佔用要加上它
du -sh /Library/Developer/CoreSimulator/Cryptex/Images/bundle
```

runtime 由哪幾個磁碟映像組成、各自存在哪裡，在 [iOS Simulator Runtime 架構](../macos_ios_simulator_runtime_architecture/)。判斷 runtime 是否可以刪除，依據是是否還要在那個 iOS 版本上測試；`Last Used At` 顯示這個 runtime 最後一次被模擬器使用的時間，很久沒用的版本是刪除的候選，最後仍以測試需求決定。

模擬器裝置是另一份佔用：每一台裝置一個目錄，存在 `~/Library/Developer/CoreSimulator/Devices`，裡面是裝進去的 App 與它們的資料，屬於狀態資料。裝置綁在某一個 runtime 上，刪除 runtime 時，先逐台刪除綁在它上面的裝置，再刪 runtime，最後清掉殘留的不可用裝置。先刪裝置的理由是逐台確認：裝置裡是狀態資料，逐台刪除時看得到刪的是哪一台；只刪 runtime 再一次清掉不可用裝置也能清乾淨，但不會經過這個確認：

```bash
# 引數換成要刪除的 iOS 版本名稱（與 runtime list 顯示的一致），列出綁在它上面的裝置與各自的 UUID
xcrun simctl list devices "iOS 18.5"

# 引數換成上一條列出的裝置 UUID，逐台刪除
xcrun simctl delete <device-uuid>

# 引數換成 runtime list -v 列出的 runtime UUID；狀態會先變成 Deleting，背景完成後才釋放空間
xcrun simctl runtime delete <runtime-uuid>

# 刪掉 runtime 已不存在、變成 unavailable 的殘留裝置
xcrun simctl delete unavailable
```

`xcrun simctl delete unavailable` 刪除的是目前的 Xcode 不再支援的裝置，包括 runtime 已經被刪掉的裝置；runtime 還裝著而且 Xcode 支援時，綁在它上面的裝置狀態是可用的，這條指令碰不到它們。要保留裝置、只清掉裡面的 App 與資料時，用 `xcrun simctl erase <device-uuid>`。

### Flutter SDK

用 fvm 管理 Flutter 版本時，每個版本是一份完整的 SDK，存在 `~/fvm/versions/`。專案用的版本寫在專案根目錄的 `.fvmrc`（舊版 fvm 是 `.fvm/fvm_config.json`），另外 fvm 的全域版本（`fvm global` 設定的那一個）是終端機裡 `flutter`、`dart` 指令實際指向的 SDK，刪除前要先用 `fvm global <版本>` 改指到要保留的版本。各專案的版本與全域版本這樣列出：

```bash
# 引數 ~/project 換成存放專案的根目錄；兩種設定檔都是 JSON，版本在 flutter 或 flutterSdkVersion 欄位
find ~/project \( -name .fvmrc -o -name fvm_config.json \) -not -path '*/build/*' -exec grep -H 'lutter' {} \;

# fvm 的全域版本：輸出的路徑最後一段就是版本號
readlink ~/fvm/default
```

仍在開發的專案與全域版本都沒用到的版本，用 `fvm remove <版本>` 移除。

### Homebrew 的舊版套件

Homebrew 每個套件只連結一個版本，升級之後舊版的檔案沒有任何設定指向它，下載過的安裝包也留在快取裡。Homebrew 在執行 `install`、`upgrade` 之後會自動清理剛處理的套件，每 30 天清理一次全部套件（設定了 `HOMEBREW_NO_INSTALL_CLEANUP` 時不會自動清理），所以累積量取決於上次清理之後的時間。

手動清理時，`brew cleanup -n` 預演會刪除哪些舊版與快取，確認後去掉 `-n` 執行；用 `brew pin` 固定的套件不在清理範圍內。cleanup 只清理最新版已經安裝的套件：預演輸出裡出現 `Skipping <套件>: most recent version ... not installed` 的，它的舊版要等 `brew upgrade <套件>` 裝上最新版之後才會被清掉。

## 容器與虛擬機的虛擬磁碟

OrbStack、Docker Desktop 這類容器工具把整台 Linux 虛擬機的磁碟存成主機上的一個虛擬磁碟檔，容器、image、volume，以及 OrbStack 建立的 Linux 機器，全部住在裡面。這個虛擬磁碟檔是 sparse file（稀疏檔）：`ls -l` 顯示的是它宣告的容量上限，`du` 量到的才是實際寫入的區塊，兩者可以差到數十倍。這個差距造成的誤判在 [macOS 磁碟空間被吃光的診斷流程](../macos_disk_space_diagnosis/) 的〈用實際佔用值找大戶，避開 sparse 假大小〉一節。

虛擬磁碟檔屬於狀態資料：刪除它等於刪掉虛擬機裡全部的容器、資料庫與 Linux 機器，沒有任何工具會重建。縮小它要從虛擬機裡面清，下列 `docker` 指令都要先啟動 OrbStack 或 Docker Desktop 才能執行。虛擬機裡的內容同樣依重建者區分：image 與 build cache 是可以重新拉取或重新 build 的快取，停止的容器的可寫層與 volume 是狀態資料：

```bash
# 列出 image、容器、volume 與 build cache 各佔多少，以及其中可回收的量
docker system df

# 只清快取類：沒有容器使用的 image 與 build cache
# 本機 build、沒推上 registry 的 image 也會被刪，刪除後只能重新 build；先用 docker images 確認
docker image prune -a
# 清掉未使用的 build cache；-a 的範圍依 Docker 版本而不同，用 --help 確認
docker builder prune

# 刪除停止的容器之前，先列出它們，逐一確認裡面沒有要留的資料
docker ps -a --filter status=exited
docker container prune

# 列出沒有容器使用的 volume，逐一確認裡面沒有要留的資料
docker volume ls --filter dangling=true

# --volumes 刪除沒有容器使用的匿名 volume（沒有名稱的 volume）
docker system prune -a --volumes

# volume prune 加上 -a 時，連有名稱的 volume（例如 compose 建立的資料庫 volume）也一起刪除；不加 -a 只刪匿名 volume
docker volume prune -a
```

加上 `-a` 時，`docker image prune` 也刪除沒有任何容器使用的 image，少了它只會刪除沒有標籤的懸空（dangling）image。`docker system prune` 碰不到 OrbStack 的 Linux 機器，那些用 `orbctl list` 列出、`orbctl delete <機器名稱>` 刪除，或在 OrbStack 視窗裡刪除。

虛擬機裡釋放的空間要經過虛擬化層才回到主機，回收的方式依工具而定。清完之後用 `du -sh` 量一次虛擬磁碟檔確認是否變小：Docker Desktop 的虛擬磁碟檔位置在它的 Settings 裡 Resources 的 Disk image location；OrbStack 的資料目錄在 `~/Library/Group Containers/` 底下名稱含 `dev.orbstack` 的目錄裡。OrbStack 會在容器內刪除資料後自動縮小檔案；Docker Desktop 沒有縮小時，它的文件提供一條 `docker run --privileged --pid=host docker/desktop-reclaim-space` 指令觸發回收。

## 自己開發的 App 的沙箱容器

自己開發的 App 在本機執行過 macOS 版本時，沙箱會在 `~/Library/Containers/<bundle-id>` 建立它的資料目錄。bundle id 是 Apple 平台上識別一個 App 的反向網域名稱，Flutter 專案預設是 `com.example.` 加上專案名轉成小駝峰的寫法（`flutter_balance` 變成 `com.example.flutterBalance`），改過的專案以 `macos/Runner/Configs/AppInfo.xcconfig` 的 `PRODUCT_BUNDLE_IDENTIFIER` 為準：

```bash
# 引數 ~/project 換成存放專案的根目錄；列出各專案 macOS 版的 bundle id，對照 ~/Library/Containers 底下的目錄名稱
find ~/project -path '*/macos/Runner/Configs/AppInfo.xcconfig' -exec grep -H PRODUCT_BUNDLE_IDENTIFIER {} \;
```

目錄裡是狀態資料，沒有重建者；專案停止開發之後，這些資料是開發時測試留下的，沒有人還需要，所以可以刪除。

目錄裡的 `Data/` 可以直接刪；目錄本身與根部的 `.com.apple.containermanagerd.metadata.plist` 受系統保護，一般權限執行 `rm` 會回報 `Operation not permitted`。那個檔案只有幾十 KB，留著只佔這一點空間；要清掉，到「系統設定 > 隱私權與安全性 > 完整磁碟取用權限」把終端機的開關打開，重新開啟終端機之後，再執行一次刪除整個目錄的 `rm`。沙箱容器的結構見 [App Sandbox 與 Containers 架構](../macos_app_sandbox_container/)。

## 定期檢查清單：各類佔用的清理方式與刪除前的查證

- **不再開發的專案的編譯產物**：在專案根目錄跑 `git -c core.quotePath=false clean -ndX` 預演，清單裡的目錄用 `find -type f` 看內容；全是產物時用 `git clean -fdX` 刪除，有金鑰、`.env`、文件、腳本或平台專案時逐個目錄刪除。已發佈版本的符號檔另外備份。
- **快取**：依快取表格的清理方式處理；刪除前確認 git 依賴的主機、私有 registry 與要人工重裝的工具，重建的來源都還在。
- **Gradle 本體與 toolchain 的 JDK**：用 `distributionUrl` 與 toolchain 設定列出仍在開發的專案指定的版本，刪除 `~/.gradle/wrapper/dists` 與 `~/.gradle/jdks` 裡不在清單上的版本與殘檔。
- **NDK 與 Android SDK 元件**：從仍在開發的專案使用的 Flutter 版本查出需要的 NDK，其餘用 `sdkmanager --uninstall` 移除，移除後確認資料夾已消失。
- **Android 模擬器映像**：`emulator -list-avds` 與 AVD 設定檔的 `image.sysdir.1` 查出使用中的映像，其餘移除。
- **iOS 模擬器 runtime 與裝置**：`xcrun simctl runtime list -v` 列出版本、大小與最後使用時間；不再測試的版本，先逐台刪除綁在它上面的裝置，再刪 runtime，最後 `xcrun simctl delete unavailable`。
- **Flutter SDK**：對照仍在開發的專案的 `.fvmrc` 與 fvm 的全域版本，`fvm remove` 移除兩者都沒用到的版本。
- **Homebrew 的舊版套件**：`brew cleanup -n` 預演後執行；出現 Skipping 的套件先 `brew upgrade`。
- **容器工具的虛擬磁碟**：啟動容器工具後 `docker system df` 看可回收量；先清 image 與 build cache，停止的容器與 volume 逐一確認沒有要留的資料再清。
- **自己開發的 App 的沙箱容器**：用 `AppInfo.xcconfig` 列出的 bundle id 對照 `~/Library/Containers`，確認專案已停止開發後刪除。

## 刪除之後可用空間的延遲：本地快照與 purgeable

刪除完成之後，`df` 回報的可用空間可能要過一段時間才會增加。啟用 Time Machine 的機器上，本地快照會保留快照建立時已經存在的資料，剛刪除的檔案在快照過期之前仍然佔著空間；加上系統可隨時回收的緩衝空間（purgeable）也在背景浮動，刪除的空間不會即時反映在可用空間上。這兩者的機制在 [macOS 磁碟空間被吃光的診斷流程](../macos_disk_space_diagnosis/) 的〈「空間掉了又回來」的根因：本地快照與 purgeable〉一節。

## 延伸閱讀：佔用的定位、App 層聚合與 APFS 的空間計算

這篇處理的是已經知道大戶在哪裡之後的判斷。大戶還沒定位時，從 APFS container 的可用空間、本地快照到逐層 `du` 的排查順序在 [macOS 磁碟空間被吃光的診斷流程](../macos_disk_space_diagnosis/)；想把 `~/Library` 底下散落的佔用聚合回各個 App、看出哪個 App 該清，用 [macOS App 聚合佔用報告](../macos_app_footprint_report/)。`du`、`df` 與 `diskutil` 對同一顆磁碟回報不同數字的原因，在 [APFS 卷結構與空間池](../macos_apfs_volume_structure/) 的〈du、df、diskutil 數字不同的原因〉一節。
