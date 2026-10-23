---
title: "停止開發的專案封存：被忽略檔案的盤點、工作狀態的收斂與遠端搬遷"
slug: "project_archive_before_cleanup"
date: 2026-10-23
draft: false
description: "專案要停止開發、把程式碼移到長期保存的遠端時讀。以「在另一台機器上還原得出來」為驗收條件，判斷被忽略檔案、未提交修改、未合併分支與機密檔各自該怎麼處理，以及搬遷遠端時哪些指令只影響本機。"
tags: ["git", "github", "flutter", "disk-space", "work-log"]
---

這篇整理一個專案停止開發、要把程式碼移到長期保存的遠端之前，需要盤點與收斂的事項，範圍從決定封存開始，到刪除本機的編譯產物為止。內容來自一次把兩個 Flutter 專案從自架的 Gitea 搬到 GitHub 私人倉庫的封存；git 的部分與語言無關，Flutter 只出現在被忽略檔案的例子裡。

## 封存的驗收條件：在另一台機器上還原得出來

封存完成的判斷標準是：一段時間之後，在另一台沒有這個專案的機器上 clone 下來，讀得懂它是什麼、裝好文件寫明的外部輸入之後 build 得起來。本機的工作目錄遲早會被清掉，所以只存在本機的檔案、分支與修改，在封存之後等同於不存在。

這個驗收條件把封存從「把程式碼推上去」擴大成三件事：遠端要包含還原所需的全部內容，還原不了的外部輸入（機密、後端服務）要寫成文件，以及推上去的內容要實際 clone 一次驗證。

## 被忽略的檔案依用途分成三種歸屬

`.gitignore` 排除的檔案不會被推上遠端，所以盤點封存內容的起點是列出所有被忽略的檔案，逐項判斷它屬於哪一種：

```bash
# 在專案根目錄執行：列出被忽略的路徑與實際佔用，由大到小排序
git status --ignored --porcelain | grep '^!!' | sed 's/^!! //' \
  | xargs -I{} du -sh "{}" 2>/dev/null | sort -rh
```

被忽略的檔案依用途分成三種歸屬，處理方式各不相同：

| 歸屬           | 例子                                                    | 封存時的處理                                   |
| -------------- | ------------------------------------------------------- | ---------------------------------------------- |
| 可重建的產物   | `build/`、`.dart_tool/`、`ios/Pods/`、產生的 `*.g.dart` | 不推上遠端，封存完成後從本機刪除               |
| 機密           | Android 簽章金鑰、`key.properties`、`.env`              | 不推上遠端；依專案是否還會發版，決定備份或刪除 |
| 誤被忽略的內容 | 設計文件、開發日誌、工具腳本                            | 修改 `.gitignore` 納入版控                     |

### 誤被忽略的內容

誤被忽略的內容通常來自範圍過寬的忽略規則。規則寫下的當時有它的理由：`/scripts/` 被整個忽略，可能是因為目錄裡放了幾百 MB 的建置輸出 APK；`/doc/`、`**/TODO.md` 被忽略，可能是當時把開發文件當成個人筆記。專案還在開發時，這些內容存在工作目錄裡隨時讀得到，忽略規則的副作用看不出來；封存之後本機被清掉，它們就跟著消失。

判斷一個被忽略的目錄屬於哪一種，依據是目錄裡的檔案，目錄名稱提供不了這個資訊。同一次封存裡，`doc/` 與 `ios/`、`linux/`、`macos/` 都被整個忽略，名稱看起來都像該保存的內容，列出檔案之後結果相反：

```bash
# 引數換成要檢查的目錄；排除 Xcode 的使用者狀態目錄，只看檔案本身
find doc ios linux macos -type f -not -path '*/xcuserdata/*'
```

`doc/` 裡是設計文件與開發日誌，屬於誤被忽略的內容。平台目錄裡只有 `GeneratedPluginRegistrant`、`Generated.xcconfig`、`ephemeral/` 這類 Flutter 工具自動產生的檔案，沒有 `Runner.xcodeproj` 這類平台專案本體——它們是在那個平台上執行過一次 Flutter 留下的產物，專案本身沒有支援這個平台，忽略規則是對的。把它們納入版控只會讓遠端多出一批會隨 Flutter 版本變動的產生檔。

一個目錄裡同時有該保存的內容與大型產物時，把忽略規則從整個目錄縮小到產物的路徑。例如 `/scripts/` 裡的腳本要保存、APK 要排除，規則改成 `/scripts/apk/`，或者先刪掉 APK 再移除整條規則。

納入版控之前，對新加入的檔案掃一次機密。私人倉庫同樣是把內容交給一個外部服務，被忽略的目錄過去從未經過版控的審視，裡面寫死的 token 或內部網址不會有人發現：

```bash
# 引數換成要納入版控的目錄；命中的是候選，逐處讀過判斷是範例程式碼還是真實的值
grep -rnEi 'password|secret|token|api[_-]?key|BEGIN .*PRIVATE KEY|eyJ[A-Za-z0-9]{10,}' doc scripts
```

`eyJ` 開頭的長字串是 JWT 的特徵：JWT 的 header 是 base64 編碼的 JSON，`{"` 編碼之後固定是 `eyJ`。

### 機密

機密檔的處理依專案未來是否還會發版而定。Android 的簽章金鑰決定一個 App 是否能更新：用新金鑰簽出來的 APK 無法覆蓋安裝在用舊金鑰簽章的裝置上，在 Google Play 上則要經過上傳金鑰重設的流程。所以專案有可能恢復開發、或者要替已安裝的裝置推出修正版時，金鑰要備份到版控以外的地方（密碼管理器、離線儲存）；確定不會再發版時，金鑰可以和產物一起刪除。

`.env` 這類環境變數檔的值不推上遠端，而欄位名稱要寫進還原說明。還原的人拿到程式碼之後，最先卡住的地方是不知道要準備哪些設定；欄位名稱加上用途說明，他才能向對應的服務重新申請。

## 工作中的狀態：未提交的修改與分支

封存前的工作目錄常常停在某個開發中的狀態：有還沒 commit 的修改，有開發到一半沒有合併的分支。這些狀態只存在本機，或者只存在即將停用的舊遠端上，封存時要一項一項決定去向。

### 未提交的修改

`git status` 列出的修改要決定 commit 或捨棄，這個決定屬於專案負責人：修改可能是完成一半的功能、也可能是實驗後放棄的嘗試，從 diff 判斷不出來。決定捨棄時用 `git restore --staged --worktree .` 把已追蹤的檔案還原到最後一次 commit 的內容（兩個選項分別清掉已暫存與未暫存的修改）；新建的檔案（untracked）不在 `restore` 的範圍內，要另外用 `git clean -n` 預演、確認後刪除。

### 分支

分支的處理有兩種做法，取捨在遠端的整潔與歷史的完整：

- **全部推上新遠端**：每個分支的歷史都保留在遠端上，代價是遠端上留著幾十上百個沒有人會再碰的分支。
- **只保留主線，其餘刪除**：遠端只有一條乾淨的主線，代價是沒有合併進主線的 commit 從遠端上消失。

先查有多少分支帶著主線沒有的 commit，數量決定這個取捨的代價：

```bash
# 列出含有 main 沒有的 commit 的本地分支；這些分支刪除後，它們的 commit 不會出現在主線上
git branch --no-merged main
```

`git push origin --all` 只推本地分支。只存在舊遠端、從來沒有 checkout 到本機的分支，要先 `git fetch` 舊遠端，再把遠端追蹤參照推成新遠端的分支：

```bash
# old 與 new 換成兩個遠端的名稱；把 old 的每個遠端追蹤參照推成 new 上的同名分支
git push new 'refs/remotes/old/*:refs/heads/*'
```

選擇只保留主線時，把要保留的開發分支用 `git merge --ff-only` 合進主線。`--ff-only` 只允許快轉合併，主線有分岔時指令直接失敗，不會產生 merge commit；封存版本的歷史因此維持成一條直線。刪除其餘分支之前，把每個分支指向的 commit 記下來：

```bash
# 輸出每個本地分支的 commit SHA 與名稱；檔案存到工作目錄以外、不會被一起清掉的位置
git for-each-ref --format='%(objectname) %(refname:short)' refs/heads > ~/archive-branches.txt
```

刪除分支時 git 會一起刪掉那個分支的 reflog，被刪分支上的 commit 只剩兩種方式找得回來。曾經 checkout 過的 commit 還記在 HEAD 的 reflog 裡，這類從目前分支到達不了的項目預設保留 30 天（`gc.reflogExpireUnreachable`）；從沒 checkout 過的沒有任何參照指向，留在 `.git` 裡直到 `git gc` 清除超過 `gc.pruneExpire`（預設兩週）的無參照物件。兩種情形都要知道 SHA 才找得到，所以這份清單是刪除分支之後的復原入口：保留期限內執行 `git branch <分支名> <SHA>` 就能把分支建回來。過了期限、或者本機的 `.git` 被刪掉，沒有推上任何遠端的 commit 就無法復原——所以這份清單只能延長決定的時間，要永久保留的分支仍然要推上遠端。

## 遠端搬遷

搬遷遠端的動作分成兩種影響範圍：有些指令只改本機的設定，有些指令會寫入遠端。分清楚這兩種，才能確認舊遠端在搬遷過程中沒有被動到。

| 指令                              | 影響範圍                                                |
| --------------------------------- | ------------------------------------------------------- |
| `gh repo create <owner/name>`     | 在 GitHub 上建立倉庫                                    |
| `git remote set-url origin <url>` | 只改本機 `.git/config` 裡 origin 的網址，舊遠端不受影響 |
| `git push origin main`            | 寫入 origin 目前指向的遠端                              |
| `git branch -D <branch>`          | 只刪本機分支，任何遠端上的同名分支都還在                |
| `git fetch --prune origin`        | 刪除本機上 origin 已經沒有的遠端追蹤參照，遠端不受影響  |

`git fetch --prune` 在 `set-url` 之後執行時，連線的是新遠端。新遠端上沒有舊遠端的那些分支，所以 git 會把本機的 `origin/<分支>` 參照逐一標為 `[deleted]`；輸出看起來像在刪除舊遠端的分支，被刪除的對象是本機保存的舊遠端快照。

```bash
# owner/name 換成新倉庫的擁有者與名稱；--private 讓倉庫建立時就是私人的
gh repo create owner/name --private --description "（已封存）"
git remote set-url origin https://github.com/owner/name.git
git push -u origin main
git push origin --tags

# 確認可見度與預設分支
gh repo view owner/name --json visibility,defaultBranchRef
```

`--tags` 要另外推：`git push` 預設不推 tag，而 tag 常常標記著已發佈的版本或某次大改之前的備份點。舊遠端要保留作為對照時，改用 `git remote add github <url>` 新增第二個遠端，origin 維持指向舊遠端。

## 還原說明與 clone 驗證

遠端上的程式碼要搭配一段還原說明，才能達到驗收條件。還原說明寫在 README，內容是從程式碼本身推不出來的資訊：

- **工具鏈版本**：Flutter 版本（fvm 的 `.fvmrc`）、JDK 版本限制、需要的 Android SDK 元件。一年後的最新版工具常常 build 不了舊專案。
- **產生程式碼的步驟**：`*.g.dart`、`*.freezed.dart` 這類產生檔被忽略時，clone 下來的專案缺少它們，要寫出產生的指令（例如 `dart run build_runner build`）以及執行時需要的旗標。
- **外部輸入**：`.env` 的欄位名稱與用途、簽章設定的位置、依賴的後端服務與它們在封存時的狀態。
- **封存當時的狀態**：最後一個版本號、主線上沒有的功能分支清單、已知的未完成事項。

寫完之後在另一個目錄 clone 一次，照 README 走到 build 成功為止：

```bash
# 引數換成新倉庫的網址；clone 到臨時目錄，驗證完整個刪除
git clone https://github.com/owner/name.git /tmp/archive-verify
```

clone 驗證檢查的是遠端的內容，所以要在全新的 clone 上做：本機原本的工作目錄有被忽略的檔案與產生檔，在那裡 build 成功證明不了遠端完整。

## 清理本機

clone 驗證通過之後，本機的工作目錄只剩編譯產物與快取，可以清理。專案目錄裡的產物、跨專案共用的依賴快取、各專案指定而累積的工具鏈版本，各自的判斷依據與檢查指令在 [開發機的定期空間清理](/macos/macos_developer_periodic_cleanup/)。

清理順序放在最後，理由是清理之後本機的內容就無法再用來補救：盤點漏掉的被忽略檔、沒推上去的分支，在清理之前都還能從本機補推。

## 封存前檢查清單

- **被忽略的檔案**：`git status --ignored` 列出全部，逐項歸到可重建產物、機密或誤被忽略的內容；誤被忽略的目錄先 `find -type f` 看檔案，掃過機密再納入版控。
- **機密**：專案還可能發版時，簽章金鑰備份到版控以外；`.env` 的欄位名稱寫進 README。
- **未提交的修改**：由專案負責人決定 commit 或捨棄。
- **分支**：`git branch --no-merged main` 查出帶有獨有 commit 的分支，決定全部推上去或只留主線；只留主線時先存下各分支的 SHA 清單。
- **tag**：`git push origin --tags`。
- **新遠端**：建立時指定 `--private`，推送後用 `gh repo view` 確認可見度。
- **還原說明**：工具鏈版本、產生程式碼的步驟、外部輸入、封存時的狀態。
- **clone 驗證**：在全新的 clone 上照 README build 成功。
- **清理本機**：驗證通過之後才刪除產物與快取。

## 延伸閱讀：被忽略檔案的清理與 git 歷史裡的機密

封存收尾的空間清理，判斷依據是刪除之後由誰重建，各類佔用的檢查指令在 [開發機的定期空間清理](/macos/macos_developer_periodic_cleanup/)。盤點時發現機密已經在過去某個 commit 裡被提交過，推上新遠端之前要先從整段歷史裡移除，做法在 [Git Filter-Repo 使用說明](../remove_git_content/)。
