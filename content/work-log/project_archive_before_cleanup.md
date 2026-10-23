---
title: "停止開發的專案封存：未提交修改、被忽略檔案、倉庫依賴、分支的收斂與遠端搬遷、還原驗證"
slug: "project_archive_before_cleanup"
date: 2026-10-23
draft: false
description: "專案要停止開發、把程式碼移到長期保存的遠端時讀。以「在另一台機器上還原得出來」為驗收條件，判斷未提交修改、被忽略檔案、機密檔、對其他倉庫的依賴與未合併分支各自該怎麼處理，以及搬遷遠端時哪些指令只影響本機。"
tags: ["git", "github", "flutter", "disk-space", "work-log"]
---

這篇整理一個專案停止開發、要把程式碼移到長期保存的遠端之前，需要盤點與收斂的事項，範圍從決定封存開始，到刪除本機的工作目錄為止。內容來自一次把幾個 Flutter 專案從自架的 Gitea 搬到 GitHub 私人倉庫的封存；git 的部分與語言無關，Flutter 出現在被忽略檔案、倉庫依賴與還原說明的例子裡。本篇的「封存」指把專案移到長期保存的遠端這整個流程，GitHub 上把倉庫設成唯讀的同名設定另稱「GitHub 的 Archive 設定」；「封存的人」指執行這些步驟的工程師，「專案負責人」指能決定修改與分支去留的人，兩者可以是同一個人。

## 封存的驗收條件：在另一台機器上還原得出來

封存完成的判斷標準是：一段時間之後，在另一台沒有這個專案的機器上 clone 下來，讀得懂它是什麼、裝好文件寫明的外部輸入之後 build 得起來。本機的工作目錄遲早會被清掉，所以只存在本機的檔案、分支與修改，在封存之後等同於不存在；同樣地，專案依賴的、只存在於即將停用的主機上的倉庫與套件，在主機停用之後也等同於不存在。

這個驗收條件把封存從「把程式碼推上去」擴大成三件事：遠端要包含還原所需的全部內容，還原不了的外部輸入（機密、後端服務）要寫成文件，以及推上去的內容要在乾淨的環境裡實際 clone 一次驗證。

## 未提交的修改

封存前的工作目錄常常停在某個開發中的狀態，`git status` 列出的修改要先決定 commit 或捨棄。這個決定屬於專案負責人：修改可能是完成一半的功能、也可能是實驗後放棄的嘗試，從 diff 判斷不出來。未追蹤的檔案裡常有該保存的設定，例如 fvm（Flutter 的版本管理工具）的版本設定檔 `.fvmrc` 新建之後沒有 commit，捨棄之前逐項看過。

處理未提交的修改排在盤點被忽略檔案之前。捨棄修改用的 `git restore` 會把工作目錄還原到最後一次 commit 的內容；已經 `git add`、還沒 commit 的新檔案也在還原範圍內，會從磁碟上被刪掉，而盤點被忽略檔案時納入版控的檔案，在 commit 之前正是這種狀態；先把未提交的修改處理乾淨，後面納入版控的檔案就不會被捲進來。

```bash
# 捨棄已追蹤檔案的修改：--staged 清掉已暫存的修改，--worktree 清掉工作目錄裡的修改
# 已經 git add、還沒 commit 的新檔案，也會從工作目錄刪除
git restore --staged --worktree .

# 新建、從未 git add 的檔案不在 restore 的範圍內；-n 預演、-d 包含目錄
git clean -nd

# 確認預演清單之後刪除
git clean -fd
```

## 被忽略檔案的歸屬

沒有被追蹤、又符合 `.gitignore` 規則的檔案不會被推上遠端（已經被追蹤的檔案不受忽略規則影響），所以盤點封存內容的起點是列出所有被忽略的檔案，逐項判斷它屬於哪一種：

```bash
# 在專案根目錄執行：列出被忽略的路徑與實際佔用，由大到小排序
# -z 讓中文、空白或引號的路徑原樣輸出；少了它，中文路徑會被轉成跳脫字串而從清單上消失
git status --ignored --porcelain -z | tr '\0' '\n' | grep '^!!' | sed 's/^!! //' \
  | tr '\n' '\0' | xargs -0 du -sh | sort -rh
```

被忽略的檔案依用途歸到以下幾種，處理方式各不相同：

| 歸屬               | 例子                                                              | 封存時的處理                                                       |
| ------------------ | ----------------------------------------------------------------- | ------------------------------------------------------------------ |
| 可重建的產物       | `build/`、`.dart_tool/`、`ios/Pods/`、產生的 `*.g.dart`、`.idea/` | 不推上遠端，clone 驗證通過後從本機刪除                             |
| 簽章金鑰           | Android 的 `*.jks`、`*.keystore`、`key.properties`                | 不推上遠端；依專案是否還會發版，決定備份或刪除                     |
| 已發佈版本的符號檔 | `--split-debug-info` 輸出的目錄、`app.*.map.json`                 | 不推上遠端；裝置上還有那個版本時，和簽章金鑰一起備份               |
| 環境變數與本機設定 | `.env`、`local.properties`                                        | 不推上遠端；欄位名稱寫進還原說明，值依是否還要在本機執行決定留或刪 |
| 版本釘選檔         | fvm 的 `.fvmrc`、`.fvm/fvm_config.json`                           | 納入版控（`.fvm/` 裡指向 SDK 的連結仍然忽略）                      |
| 誤被忽略的內容     | 設計文件、開發日誌、工具腳本、有客製內容的平台專案                | 修改 `.gitignore`、`git add` 之後立刻 commit                       |

被忽略清單之外，還要查建置設定參照到的、不在工作目錄裡的檔案。Flutter 官方文件的範例把 keystore 產生在家目錄，這種放在 repo 以外的金鑰既不會被追蹤、也不會出現在被忽略清單裡；`build.gradle` 裡讀取它的設定卻還在，fresh clone 之後 build 會因為找不到檔案而失敗：

```bash
# 在專案根目錄執行；列出 Android 建置設定讀取的金鑰與設定檔路徑
grep -rnE 'storeFile|rootProject\.file|keystoreProperties' android/app/build.gradle* android/build.gradle*
```

列出的檔案同樣要決定備份或刪除，並在還原說明裡寫明 build 需要它、它該放在哪裡。

### 誤被忽略的內容

誤被忽略的內容通常來自範圍過寬的忽略規則。規則寫下的當時有它的理由：`/scripts/` 被整個忽略，可能是因為目錄裡放了幾百 MB 的建置輸出 APK；`/doc/`、`**/TODO.md` 被忽略，可能是當時把開發文件當成個人筆記；`/macos/`、`web/` 被忽略，可能是當時只打算發佈 Android 版。專案還在開發時，這些內容存在工作目錄裡隨時讀得到，忽略規則的副作用看不出來；封存之後本機被清掉，它們就跟著消失。

判斷一個被忽略的目錄屬於哪一種，依據是目錄裡的檔案，目錄名稱提供不了這個資訊：

```bash
# 引數換成要檢查的目錄；排除 Xcode 的使用者狀態目錄與 Flutter 的暫存目錄，只看檔案本身
# find 會連已經被追蹤的檔案一起列出
find doc ios linux macos windows web -type f -not -path '*/xcuserdata/*' -not -path '*/ephemeral/*'

# 只列出這些目錄裡被忽略的檔案
git ls-files --others --ignored --exclude-standard -- doc ios linux macos windows web
```

Flutter 的平台目錄（`ios/`、`macos/`、`linux/`、`windows/`、`web/`）列出檔案之後分成兩種情形，判斷要分兩步：

- **只有自動產生的檔案**：目錄裡只有 `GeneratedPluginRegistrant`、`Generated.xcconfig`、`flutter_export_environment.sh` 這類 Flutter 工具在 build 時寫入的檔案，沒有平台專案本體。這是在那個平台上執行過一次 Flutter 留下的產物，忽略規則是對的。
- **有平台專案本體**：目錄裡有 `Runner.xcodeproj`、`AppDelegate.swift`、`CMakeLists.txt`、`runner/main.cc`、`index.html` 這類 `flutter create` 建立的檔案。這時要問專案是否要支援這個平台、檔案是否被客製過（entitlements、Info.plist、bundle id、App 圖示）。有客製的納入版控；沒有支援這個平台、也沒有客製的，可以維持忽略，日後需要時用 `flutter create --platforms=<平台> .` 重新產生，並在還原說明裡寫下這件事。

`doc/` 這類目錄裡的設計文件與開發日誌，屬於誤被忽略的內容。盤點的人列出檔案後，發現一個目錄同時有該保存的內容與大型產物時，把忽略規則從整個目錄縮小到產物的路徑。例如 `/scripts/` 裡的腳本要保存、APK 要排除，規則改成 `/scripts/apk/`，或者先刪掉 APK 再移除整條規則。

納入版控之前，對新加入的檔案掃一次機密。私人倉庫同樣是把內容交給一個外部服務，被忽略的目錄過去從未經過版控的審視，裡面寫死的 token 或內部網址不會有人發現：

```bash
# 引數換成要納入版控的目錄；命中的是候選，逐處讀過判斷是範例程式碼還是真實的值
grep -rnEi 'password|secret|token|api[_-]?key|BEGIN .*PRIVATE KEY|eyJ[A-Za-z0-9]{10,}' doc scripts

# 內部網址只有讀者自己知道網域；example\.internal 換成公司或自架服務的網域
grep -rnE 'example\.internal' doc scripts
```

`eyJ` 開頭的長字串是 JWT 的特徵：JWT 的 header 是 base64url 編碼的 JSON，以 `{"alg"` 這類 `{"` 加字母開頭，編碼之後幾乎都以 `eyJ` 起頭。

掃描通過之後，修改 `.gitignore`、`git add`，並且立刻 commit。納入版控的檔案在 commit 之前只存在暫存區，後續任何還原工作目錄的指令都會把它們刪掉。

### 簽章金鑰與環境變數

簽章金鑰的處理依專案未來是否還會發版而定。Android 安裝更新時會比對新舊 APK 的簽章，簽章不同就拒絕覆蓋安裝。所以不經過 Google Play、直接用 APK 檔安裝（側載）的 App，以及自己保管最終簽章金鑰的 App，金鑰遺失之後，已安裝的裝置就無法再更新。加入 Google Play App Signing 的 App（2021 年 8 月起新上架的 App 必須用 App Bundle 發佈，因此一定加入）不同：最終簽章由 Google 保管，本機那把只用來上傳新版本（上傳金鑰），遺失時可以向 Google Play 申請重設，已安裝的使用者不受影響。專案有可能恢復開發、或者要替已安裝的裝置推出修正版時，金鑰要備份到版控以外的地方（密碼管理器、離線儲存）；確定不會再發版時，金鑰可以和產物一起刪除。已發佈版本的符號檔跟著金鑰的決定走：還會有使用者回報那個版本的崩潰時，一起備份。

`.env` 這類環境變數檔的值不推上遠端，而欄位名稱要寫進還原說明。還原的人拿到程式碼之後，最先卡住的地方是不知道要準備哪些設定；欄位名稱加上用途說明，他才能向對應的服務重新申請。

### 已經提交進歷史的機密

被忽略檔案的盤點與納入版控前的機密掃描，檢查的都是工作目錄裡現在的檔案。機密若曾經在過去某個 commit 裡被提交、之後才被刪除或加進忽略規則，它仍然留在歷史裡，推上新遠端就跟著推上去：

```bash
# 引數換成要檢查的檔名樣式；--all 涵蓋所有分支，有輸出代表這些檔案曾經出現在歷史裡
# pathspec 不加 * 時只比對根目錄，'*key.properties' 才會比對到 android/key.properties
git log --all --oneline -- '*.jks' '*.keystore' '*key.properties' '*.env' '*.env.*'
```

有輸出時，在〈分支的收斂〉與〈遠端搬遷〉之前，先從整段歷史裡移除，做法在 [Git Filter-Repo 使用說明](../remove_git_content/)。filter-repo 會重寫所有 commit 的 SHA，並且移除 origin 遠端，所以它要排在記錄分支 SHA 與搬遷遠端之前。做完之後只推改寫過的歷史：要保留全部分支時，在 `git clone --mirror` 取得的副本上執行 filter-repo，再用 `git push --mirror` 推到新遠端；不要把舊遠端加回來再 fetch，那會把舊遠端上沒有改寫、仍帶著機密的歷史抓回本機，再一起推上新遠端。

做過 filter-repo 的專案，後續流程有兩處不同：〈分支的收斂〉的分支計數要在 filter-repo 之前、仍連得上舊遠端時完成；filter-repo 之後的所有推送都從改寫過的那份 repo 發出，原本的工作目錄不再推送，需要時從新遠端重新 clone。

## 對其他倉庫的依賴

被忽略檔案盤點的是這個倉庫裡的檔案；專案還可能依賴放在別的倉庫、別的主機上的程式碼與套件。驗收條件要的是在另一台機器上 build 得起來，所以依賴的來源同樣要還在。依賴分兩個方向：

- **這個專案依賴的倉庫**：`pubspec.yaml` 的 `git:` 依賴、`.gitmodules` 的 submodule、Gradle 的 `maven { url }`、`Podfile` 的 `source`。依賴放在即將停用的主機上時，主機一停用，clone 下來的專案就 build 不了。
- **依賴這個專案的倉庫**：別的專案用舊網址、分支名或 SHA 依賴這個倉庫。搬遷之後舊網址失效；filter-repo 改寫 SHA，會讓對方鎖檔裡記錄的 SHA 找不到；刪掉分支，會讓對方 `ref: <分支>` 的設定失效。

```bash
# 在專案根目錄執行；列出指向外部倉庫與套件來源的設定，逐一看主機是否還會在
grep -rnE 'git:|url:|maven|source ' pubspec.yaml .gitmodules android/*.gradle* android/app/*.gradle* ios/Podfile 2>/dev/null
```

指向即將停用主機的依賴，逐一決定處理方式：把依賴的倉庫也照本篇封存到新遠端，再把這個專案的設定改指新網址；把依賴的程式碼直接放進這個倉庫；或在還原說明裡寫明依賴的來源與當時的版本。改指新網址時，把依賴固定在原本鎖定的 commit SHA 上（`pubspec.yaml` 的 `ref:` 寫完整 SHA），還原出來的版本才會跟封存前一致。依賴這個專案的一方，要在搬遷前列出來並通知對方。

## 推上新遠端之前要處理的副作用

推上新遠端之前，有幾項副作用要先處理：

- **CI 設定**：GitHub 會執行倉庫裡 `.github/workflows` 的設定，而 Gitea Actions 在沒有 `.gitea/workflows` 時也會讀這個路徑；封存的倉庫不需要 CI 時，先移除或停用這些 workflow，避免推上去之後觸發建置或發佈。
- **Git LFS 的物件**：倉庫用 Git LFS 存放大型檔案時，`git push` 只推指向檔案的指標；`git push` 只會上傳本機已經下載的 LFS 物件，本機沒 checkout 過的版本只有指標；要在 origin 仍指向舊遠端時先 `git lfs fetch --all origin` 把舊遠端的物件全部抓下來，再 `git lfs push --all <新遠端>`（只涵蓋本機分支可達的物件，只存在遠端追蹤參照的分支要先建成本地分支），否則舊遠端停用之後，那些檔案就不見了。
- **單檔大小上限**：GitHub 拒絕超過 100MB 的單一檔案，歷史裡有這類檔案時推送會失敗，要改用 LFS 或從歷史裡移除。

## 分支的收斂

開發到一半沒有合併的分支只存在本機，或者只存在即將停用的舊遠端上。專案負責人做取捨之前，封存的人先數有多少分支帶著主線沒有的 commit。本地分支與遠端追蹤參照（remote-tracking ref，本機保存的「上次 fetch 時遠端分支指向哪個 commit」的快照，名稱是 `origin/<分支>`）各查一次，遠端那份拿掉 `origin/` 前綴之後與本地那份合併、去掉重複的分支名稱，就是只保留主線時會消失的分支。遠端追蹤參照是上次 fetch 時的狀態，其他人之後推上舊遠端的分支不在裡面，所以計數前先 fetch：

```bash
# 沒有做 filter-repo 的專案：此時 origin 仍指向舊遠端；更新遠端追蹤參照，並刪掉舊遠端已經不存在的分支
git fetch --prune origin

# main 換成主線分支的名稱；列出含有主線沒有的 commit 的本地分支
git branch --no-merged main

# 同一件事查遠端追蹤參照：只存在舊遠端、從沒 checkout 到本機的分支在這裡
git branch -r --no-merged main
```

分支的處理有三種做法，取捨在遠端的整潔、歷史的完整與操作的步數：

- **全部推上新遠端**：每個分支的歷史都保留在遠端上，代價是遠端上留著幾十上百個沒有人會再碰的分支。
- **轉成 tag 或另存備份**：分支名稱轉成 `archive/<分支>` 這類 tag 推上去，遠端的分支清單維持乾淨而 commit 都保留；或用 `git bundle create <專案名>.bundle --all` 把全部參照存成一個檔案，放在倉庫以外冷存。
- **只保留主線，其餘刪除**：遠端只有一條乾淨的主線，代價是沒有合併進主線的 commit 從遠端上消失。

### 全部推上新遠端

最少步驟的做法是鏡像複製：`git clone --mirror` 取得舊遠端的完整副本（所有分支與 tag），再用 `git push --mirror` 推到新遠端。它的前提是舊遠端還連得上，而且本機沒有任何沒推上舊遠端的 commit——包括只存在本機的分支，以及已有分支上本機領先舊遠端的 commit。`git log --branches --not --remotes --oneline` 沒有輸出時，這個前提才成立。

舊遠端連不上、或本機另有分支時，在 origin 仍指向舊遠端的狀態下，把新遠端加成第二個遠端，分兩次推送：本地分支一次，只存在舊遠端的分支一次。這兩次推送要在 origin 改指新遠端、執行 `git fetch --prune` 之前做，因為 prune 會把舊遠端的遠端追蹤參照從本機刪掉：

```bash
# owner/name 換成新倉庫的擁有者與名稱；new 是新遠端在本機的名稱
gh repo create owner/name --private --description "（已封存）"
git remote add new https://github.com/owner/name.git

# 推送所有本地分支與 tag；--all 只推分支，tag 要另外推
git push new --all
git push new --tags

# origin/HEAD 是一個符號參照（symbolic ref，本身不指向 commit、而是指向另一個參照），記錄舊遠端的預設分支
# 下一條指令的 refs/remotes/origin/* 也會比對到 refs/remotes/origin/HEAD，不刪掉它，新遠端會多出一個名為 HEAD 的分支
git remote set-head origin -d

# 把舊遠端的每個遠端追蹤參照推成新遠端上的同名分支
git push new 'refs/remotes/origin/*:refs/heads/*'
```

本機與舊遠端都有的同名分支，最後一條推送可能回報 `! [rejected] ... (non-fast-forward)`：本地分支在第一次推送時已經推上新遠端，舊遠端那份的 commit 若不在本地分支的歷史裡，推送就被拒絕。用 `git merge-base --is-ancestor origin/<分支> <分支>` 判斷：指令成功（回傳 0）代表本地分支已經包含舊遠端的內容，這個拒絕可以忽略；失敗代表兩邊分岔，把舊遠端那份另外推成新分支保存，例如 `git push new origin/<分支>:refs/heads/<分支>-old`。

推完之後，〈遠端搬遷〉的區塊裡 `gh repo create` 那一行可以跳過，因為倉庫已經建立了。

### 只保留主線

選擇只保留主線時，把要保留的開發分支用 `git merge --ff-only` 合進主線。快轉合併（fast-forward）是主線上沒有分支以外的新 commit 時，git 直接把主線的指標移到分支的最新 commit，不產生 merge commit；`--ff-only` 只允許這種合併，主線有分岔時指令直接失敗，封存版本的歷史因此維持成一條直線。要保留的分支有好幾條時，只有和主線成一直線的那一條能快轉，其餘的要先 rebase 到主線上，或改走全部推上新遠端、轉成 tag 的做法。

刪除其餘分支之前，把每個分支指向的 commit 記下來：

```bash
# 輸出每個本地分支與遠端追蹤參照的 commit SHA 與名稱
# 檔名帶上專案名稱，一次封存多個專案時才不會互相覆蓋；存到工作目錄以外、不會被一起清掉的位置
git for-each-ref --format='%(objectname) %(refname:short)' refs/heads refs/remotes > ~/archive-branches-<專案名>.txt
```

這份清單是保險，保險的期限取決於 git 何時清除沒有參照的 commit。reflog 是 git 在本機記錄的「每個參照曾經指向哪些 commit」的日誌，刪除分支時，git 會一起刪掉那個分支的 reflog，被刪分支上的 commit 依是否曾經 checkout 過分成兩種情形：

- **曾經 checkout 過的 commit**：還記在 HEAD 的 reflog 裡。從目前分支到達不了的 reflog 項目，預設保留 30 天（`gc.reflogExpireUnreachable`）。
- **從沒 checkout 過的 commit**：沒有任何參照指向它，`git gc` 會清除超過 `gc.pruneExpire`（預設兩週）的無參照物件。

兩個期限的起算點都不是刪除分支的那一刻：reflog 項目從它被寫入的時間起算，無參照物件從它的物件檔案最後一次被寫入的時間起算。開發了幾個月的舊分支，兩個期限早就過了，刪除之後的下一次 `git gc`（包括 git 在 commit、merge 這類一般操作之後自動觸發的 `gc --auto`）就可能把它的 commit 清掉，緩衝期可能是零。

所以在 gc 執行之前，用清單裡的 SHA 執行 `git branch <分支名> <SHA>` 能把分支建回來，不必翻 reflog；沒有清單時，`git fsck --lost-found` 能列出沒有參照指向的 commit 作為後備。要保留的分支，在刪除之前推上遠端，或轉成 tag。

## 遠端搬遷

搬遷遠端的動作分成兩種影響範圍：有些指令只改本機的設定，有些指令會寫入遠端。分清楚這兩種，才能確認舊遠端在搬遷過程中沒有被動到。

| 指令                              | 影響範圍                                                |
| --------------------------------- | ------------------------------------------------------- |
| `gh repo create <owner/name>`     | 在 GitHub 上建立倉庫                                    |
| `git remote set-url origin <url>` | 只改本機 `.git/config` 裡 origin 的網址，舊遠端不受影響 |
| `git push origin main`            | 寫入 origin 目前指向的遠端                              |
| `git branch -D <branch>`          | 只刪本機分支，任何遠端上的同名分支都還在                |
| `git fetch --prune origin`        | 刪除本機上 origin 已經沒有的遠端追蹤參照，遠端不受影響  |

`git fetch --prune` 在 `set-url` 之後執行時，連線的是新遠端。新遠端上沒有舊遠端的那些分支，所以 git 會把本機的 `origin/<分支>` 遠端追蹤參照逐一標為 `[deleted]`。輸出看起來像在刪除舊遠端的分支，實際被刪除的是本機那些記錄舊遠端狀態的參照，舊遠端上的分支都還在。

```bash
# owner/name 換成新倉庫的擁有者與名稱；--private 讓 gh 把倉庫建立成私人的
gh repo create owner/name --private --description "（已封存）"
git remote set-url origin https://github.com/owner/name.git

# main 換成主線分支的名稱
git push -u origin main

# git push 預設不推 tag，tag 要另外推
git push origin --tags

# 確認可見度與預設分支
gh repo view owner/name --json visibility,defaultBranchRef
```

tag 常常標記著已發佈的版本或某次大改之前的備份點，所以和分支一起推上去。

舊遠端要保留在本機設定裡作為對照時，不執行 `set-url` 那一行，改用 `git remote add github <url>` 新增第二個遠端，origin 維持指向舊遠端；這時兩條 `git push` 的 `origin` 都換成 `github`。

舊遠端本身在搬遷之後的去留，屬於舊主機管理者的決定：設成唯讀、留下指向新倉庫的說明、通知其他協作者，或維持原狀。

保存媒介的選擇另有取捨。私人倉庫的好處是隨時可以 clone、可以在網頁上瀏覽，代價是依賴單一服務與單一帳號；`git bundle` 或把整個工作目錄打包成 tar 檔，可以存到任何儲存空間，tar 檔還能連被忽略的檔案一起保存，代價是要另外管理備份的位置。兩者可以並用。

## 還原說明與 clone 驗證

遠端上的程式碼要搭配一段還原說明，才能達到驗收條件。還原說明寫在 README，內容是從程式碼本身推不出來的資訊：

- **工具鏈版本**：Flutter 版本（版本管理工具 fvm 的 `.fvmrc`）、JDK 版本限制、需要的 Android SDK 元件。一年後的最新版工具常常 build 不了舊專案。
- **產生程式碼的步驟**：`*.g.dart`、`*.freezed.dart` 這類產生檔被忽略時，clone 下來的專案缺少它們，要寫出產生的指令（例如 `dart run build_runner build`）以及執行時需要的旗標；維持忽略的平台目錄，寫出重新產生的指令。
- **外部輸入**：`.env` 的欄位名稱與用途、簽章設定與金鑰檔該放在哪裡、依賴的其他倉庫與它們的位置、依賴的後端服務與它們在封存時的狀態。
- **封存當時的狀態**：最後一個版本號、主線上沒有的功能分支清單、已知的未完成事項。

寫完之後實際 clone 一次，照 README 走到 build 成功為止。驗證要在乾淨的環境裡做：同一台機器上的 `~/.pub-cache`、`~/.gradle`、已安裝的 SDK、連得上舊主機的 SSH 金鑰、放在 repo 以外的 keystore，都會讓驗證通過，而另一台機器上沒有這些快取、SDK 與金鑰。最直接的做法是換一台機器、虛擬機或容器；在同一台機器上驗證時，至少把快取目錄指到空的臨時目錄：

```bash
# 引數換成新倉庫的網址；clone 到一個新建的臨時目錄，驗證結束後把這個目錄整個刪除
VERIFY=$(mktemp -d)
git clone https://github.com/owner/name.git "$VERIFY/repo"
cd "$VERIFY/repo"

# README 寫了產生程式碼的步驟時，先照做；用 fvm 的專案，flutter 指令改成 fvm flutter 才會用到專案指定的版本
# PUB_CACHE 與 GRADLE_USER_HOME 指到空的臨時目錄，依賴全部從原本的來源重新下載
# 依賴的主機已經停用或連不上時，這一步會失敗，正是要抓的情形
PUB_CACHE=$(mktemp -d) GRADLE_USER_HOME=$(mktemp -d) fvm flutter build apk
```

clone 驗證檢查的是遠端的內容，所以要在全新的 clone 上做：本機原本的工作目錄有被忽略的檔案與產生檔，在那裡 build 成功證明不了遠端完整。選擇全部推上新遠端的，另外把 `git ls-remote --heads <新遠端網址>` 的輸出，與〈分支的收斂〉列出的本地分支、遠端追蹤參照清單對照，確認分支都到齊了；build 成功驗不到分支有沒有缺。

GitHub 的 Archive 設定（介面上也譯作「封存」，和本篇的封存流程是兩件事），它把倉庫設成唯讀，之後不能 push、不能開 issue。是否設定，在 clone 驗證通過之後決定；設定方式是 `gh repo archive owner/name`，之後可以在倉庫設定裡取消。

## 清理本機

clone 驗證通過之後，本機的工作目錄只剩編譯產物、快取，以及已經備份或決定刪除的機密，可以清理。清理有兩種程度：只刪除工作目錄裡的產物，或刪除整個工作目錄。

保留工作目錄的話，它的版本設定仍然指向 Flutter SDK、Gradle、JDK 這些工具鏈版本，清理工具鏈時要把它當成已封存、不再 build 的專案，它的設定不算數。整個工作目錄刪除之後，需要時從遠端 clone 回來，照還原說明重建。專案目錄裡的產物、跨專案共用的快取、各專案指定而累積的工具鏈版本，各自的判斷依據與檢查指令在 [開發機的定期空間清理](/macos/macos_developer_periodic_cleanup/)。

清理順序放在最後，理由是清理之後本機的內容就無法再用來補救：盤點漏掉的被忽略檔、沒推上去的分支，在清理之前都還能從本機補推。

## 封存前檢查清單

- **未提交的修改**：由專案負責人決定 commit 或捨棄，在納入任何被忽略的內容之前處理完；未追蹤的 `.fvmrc` 這類設定檔先 commit。
- **被忽略的檔案**：`git status --ignored` 列出全部，逐項歸到產物、簽章金鑰、符號檔、環境變數與本機設定、版本釘選檔、誤被忽略的內容；被忽略的目錄先 `find -type f` 看檔案，平台目錄分辨產生檔與平台專案本體；掃過機密再 `git add` 並立刻 commit。
- **repo 以外的金鑰**：從建置設定的 `storeFile`、`rootProject.file` 找出讀取的檔案，決定備份或刪除。
- **簽章金鑰、符號檔與環境變數**：專案還可能發版時，簽章金鑰與已發佈版本的符號檔備份到版控以外；`.env` 的欄位名稱寫進 README。
- **歷史裡的機密**：`git log --all -- '*key.properties' '*.env' ...` 有輸出時，先完成分支計數，再用 filter-repo 移除，之後的推送都從改寫過的 repo 發出，不再從舊遠端 fetch。
- **對其他倉庫的依賴**：列出 `git:` 依賴、submodule 與私有套件來源，指向即將停用主機的一併封存並固定 SHA；依賴這個專案的一方先通知。
- **分支**：沒有做 filter-repo 的專案先 `git fetch --prune origin`，再用 `git branch --no-merged main` 與 `git branch -r --no-merged main` 查出帶有獨有 commit 的分支，決定全部推上、轉成 tag 或只留主線；要保留的分支在刪除前推上遠端，SHA 清單只當保險。
- **tag**：推到新遠端（走 `set-url` 的是 `git push origin --tags`，走第二個遠端的是 `git push new --tags`）。
- **新遠端**：推送前先處理 workflow、LFS 物件與超過 100MB 的檔案；建立時指定 `--private`，推送後用 `gh repo view` 確認可見度。
- **還原說明**：寫進 README：工具鏈版本、產生程式碼的步驟、外部輸入、封存時的狀態。
- **clone 驗證**：在乾淨的環境裡照 README build 成功；全部推上遠端的，對照分支清單。
- **清理本機**：驗證通過之後才刪除產物與快取，或刪除整個工作目錄。

## 延伸閱讀：本機清理與 git 歷史裡的機密

封存收尾的空間清理，判斷依據是刪除之後由誰重建，各類佔用的檢查指令在 [開發機的定期空間清理](/macos/macos_developer_periodic_cleanup/)。從整段 git 歷史裡移除檔案或替換敏感內容的完整做法，在 [Git Filter-Repo 使用說明](../remove_git_content/)。
