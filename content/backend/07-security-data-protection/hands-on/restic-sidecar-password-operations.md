---
title: "restic sidecar 容器的密碼操作：啟動腳本依 exit code 判斷、換密碼、外洩後搬到新 repository 與唯讀還原演練"
date: 2026-11-03
description: "restic 以 Docker Compose 的 sidecar 容器做自架備份、要換密碼或密碼可能外洩時：啟動腳本怎麼分辨 repository 不存在與密碼錯誤、只改 .env 為什麼讓備份停擺、容器還在跑時換密碼的步驟、外洩後建新 repository 並用 restic copy 搬快照，以及唯讀掛載時 restore 重試十幾分鐘才失敗的成因"
tags: ["backend", "security", "backup", "restic", "docker", "hands-on"]
---

**事件說明**：2026-11-03 在 macOS 的 OrbStack（Docker 29.4.0）上，以 `restic/restic:0.19.1` 映像實測。情境來自一套自架在家用主機上的個人系統：Docker Compose 裡一個 restic 容器以唯讀方式掛載要備份的檔案資料夾，每小時備份、每天依保留規則清理，密碼經由 `.env` 的 `RESTIC_PASSWORD` 交給容器。實測用的 repository 都是暫時建立的 Docker volume。

這篇記錄 restic 以 sidecar 容器（跟主服務並排、在同一個 Compose 專案裡執行的輔助容器）做備份時，密碼這一段的操作與失敗形態。各節依序是：`restic cat config` 在 repository（restic 存放加密備份的位置）不存在、密碼錯誤、對已經存在的 repository 再 `init` 時各回傳什麼；只判斷成功或失敗的啟動腳本，在只改了 `.env` 的密碼時為什麼把密碼錯誤誤判成 repository 不存在、讓備份停擺，以及依 exit code 分支的寫法；容器還在跑、`.env` 還是舊密碼時換密碼的步驟，以及 `docker compose restart` 不會讓容器讀到新密碼；密碼可能外洩時建新 repository、用 `restic copy` 搬快照，並確認外流的舊 key 檔打不開新 repository；唯讀掛載 repository 做還原演練時 `restore` 重試十幾分鐘才失敗的成因與 `--no-lock`。密碼、key 檔與主金鑰的結構，以及什麼條件下只換密碼就足夠、什麼條件下要換主金鑰，在 [7.45 加密備份的密碼、key 檔與主金鑰：換密碼與換主金鑰的差別、密碼外洩與遺失的處置，以 restic 為例](/backend/07-security-data-protection/backup-encryption-password-and-master-key/)，這篇不重寫。

## 實驗的形狀：一個 helper 腳本、幾個暫時的 repository 與測試資料

實驗的每一次 restic 指令都在一個新的容器裡執行，repository 是一個 Docker named volume，密碼放在實驗目錄的檔案裡。實驗目錄是自己建的一個空資料夾，下文寫成 `<實驗目錄>`；它底下放：

- `data/`：要備份的測試資料，這次放了兩個小文字檔（`echo hello > data/a.txt`、`echo world > data/b.txt`）。
- 密碼檔 `pw-old`、`pw-new`、`pw-wrong`、`pw-fresh`：每個檔案一行密碼，內容自己定，四個互不相同。`pw-wrong` 代表「`.env` 被改成了 repository 沒有的密碼」。
- `stolen-keys/`：外洩情境用的空資料夾（`mkdir stolen-keys`）。

volume 名稱一律用 `rlab-` 開頭，清理時一條 `grep` 列得出來；`docker run -v rlab-xxx:/repo` 第一次用到某個名稱時，Docker 會自動建一個空的 named volume。為了讓指令短一點，用一支 helper 腳本把 volume、密碼檔與 restic 映像組起來，存成 `<實驗目錄>/r.sh`，`L=` 那一行填實驗目錄的絕對路徑：

```bash
#!/usr/bin/env bash
# r.sh <volume> <密碼檔名> <restic 的參數...>
L=<實驗目錄>
vol=$1; pw=$2; shift 2
docker run --rm -v "$vol":/repo -v "$L":/lab -e RESTIC_REPOSITORY=/repo \
  -e RESTIC_PASSWORD_FILE=/lab/"$pw" restic/restic:0.19.1 "$@"
```

存檔之後跑一次 `chmod +x r.sh`，沒有執行權限時 `./r.sh` 回傳 `permission denied`。`RESTIC_PASSWORD_FILE` 從檔案讀密碼，`RESTIC_PASSWORD` 從環境變數讀；正式的 sidecar 用 `RESTIC_PASSWORD`，實驗用 `RESTIC_PASSWORD_FILE` 是為了換一組密碼只要換檔名。下文的 `./r.sh` 都在實驗目錄執行。

## `restic cat config` 的 exit code：repository 不存在、密碼錯誤與重複 init

`restic cat config` 讀 repository 的設定檔，要先用密碼解開主金鑰才讀得到，所以它的 exit code 同時區分「repository 不存在」與「密碼錯誤」（[restic 的 scripting 文件](https://restic.readthedocs.io/en/stable/075_scripting.html) 列出全部的 exit code，10 從 0.17.0 起、12 從 0.17.1 起）：

```bash
./r.sh rlab-norepo pw-old cat config   # 空的 volume，還沒 init
# Is there a repository at the following location?
# exit 10
./r.sh rlab-repo pw-old init            # 建立 repository，之後的指令都對它跑
./r.sh rlab-repo pw-wrong cat config    # 用另一組密碼
# Fatal: wrong password or no key found
# exit 12
./r.sh rlab-repo pw-old cat config      # 正確的密碼
# exit 0
./r.sh rlab-repo pw-old init            # 對已經存在的 repository 再 init
# Fatal: Fatal: create repository at /repo failed: config file already exists
# exit 1
./r.sh rlab-repo pw-old backup --host lab /lab/data   # 外洩情境要用的第一個快照
# snapshot d46a3984 saved
```

`init` 碰到既有的 repository 時拒絕執行、回傳 exit 1，既有的資料不受影響。這一點讓「拿不準就 init」看起來無害，而只判斷成功或失敗的啟動腳本正是靠這個假設寫成的。

## 只判斷成功或失敗的啟動腳本：密碼錯誤被當成 repository 不存在

sidecar 容器的啟動腳本有一種直覺的寫法：`cat config` 失敗就 `init`，再進入備份迴圈。下面是精簡過的版本，備份迴圈換成一次 `backup`，存成 `<實驗目錄>/entry-before.sh`。存檔前把 `<主機名稱>` 換成一個固定的名稱（這次的實驗用 `lab`），留著尖括號的話 sh 會把 `<` 當成輸入重新導向而報錯；為什麼要固定，在這一節最後說明：

```sh
#!/bin/sh
set -e
# 只判斷成功或失敗
if ! restic cat config >/dev/null 2>&1; then
  restic init
fi
restic backup --host <主機名稱> /lab/data
```

`.env` 的 `RESTIC_PASSWORD` 被改成新密碼、而 repository 裡的 key 檔沒有換時，`cat config` 回傳 12，腳本把它當成 repository 不存在，接著 `init` 因為 config 已經存在而回傳 1，`set -e` 讓腳本當場結束。用 `pw-wrong` 代表被改過的 `.env`，以腳本取代映像的進入點執行：

```bash
docker run --rm --entrypoint /bin/sh -v rlab-repo:/repo -v <實驗目錄>:/lab \
  -e RESTIC_REPOSITORY=/repo -e RESTIC_PASSWORD_FILE=/lab/pw-wrong \
  restic/restic:0.19.1 /lab/entry-before.sh
# Fatal: Fatal: create repository at /repo failed: config file already exists
# exit 1
```

日誌裡唯一的錯誤是 init 失敗，密碼錯誤這個真正的原因被 `cat config` 的 `2>&1` 丟掉了。compose 檔的 `restart` 設成 `always`、`unless-stopped` 或 `on-failure` 時，容器會一次又一次重啟、每次都停在同一個位置（從 restart 政策推論，這次只用 `docker run` 跑，沒有實跑 compose 的重啟）：資料不會被破壞，但再也沒有新的備份，看日誌的人會往「config file already exists」的方向查。

依 exit code 分支之後，只有 10 才 init，12 直接報出密碼錯誤並結束，其他未預期的 exit code 再跑一次 `cat config`、不丟掉 stderr，讓 restic 原本的錯誤訊息印出來。存成 `<實驗目錄>/entry-after.sh`，`<主機名稱>` 同樣先換掉：

```sh
#!/bin/sh
set -e
log() { echo "$(date -u +%FT%TZ) $*"; }
rc=0
restic cat config >/dev/null 2>&1 || rc=$?   # set -e 底下取得 exit code 而不讓腳本當場結束
case "$rc" in
  0) ;;
  10)
    log "repository 不存在，建立於 $RESTIC_REPOSITORY"
    restic init
    ;;
  12)
    log "ERROR: 密碼打不開 $RESTIC_REPOSITORY"
    exit 1
    ;;
  *)
    log "ERROR: 無法開啟 $RESTIC_REPOSITORY（restic exit $rc），訊息如下："
    restic cat config >/dev/null || true
    exit 1
    ;;
esac
restic backup --host <主機名稱> /lab/data
```

執行方式跟上面相同，最後一個引數換成 `/lab/entry-after.sh`。用 `pw-wrong` 跑，它印出 `ERROR: 密碼打不開 /repo` 並以 exit 1 結束，沒有嘗試 init。對一個空的 volume（`rlab-fresh`）以 `pw-fresh` 跑，它印出 `repository 不存在，建立於 /repo`、`created restic repository …`，第一次備份 `snapshot d162a3e5 saved`；用同一組密碼再跑一次，它不 init，直接備份，`Added to the repository: 0 B` 表示內容跟上一次相同，沒有新增資料。

密碼錯誤時讓腳本結束，而不是記一筆日誌之後繼續迴圈：容器停止或反覆重啟時，`docker compose ps` 列出的狀態就看得出這個服務不正常；繼續迴圈的話，每一次備份都失敗、容器卻一直是 running，要等到哪一天需要還原才發現。`12` 那個分支的訊息可以再加一行，寫出處理步驟在哪裡（例如專案 README 裡換密碼那一節），看日誌的人不必猜。

`backup` 的 `--host` 填一個固定的名稱（`<主機名稱>`，例如這套系統的名字），理由在清理那一步：`restic forget` 依 `--group-by` 把快照分組之後才套保留規則，預設是 `host,paths`（`restic forget --help`）。compose 檔沒有設 `hostname:` 時，容器的主機名稱每次重建都不同，不固定 `--host` 的話，每一個容器的快照自成一組，保留規則各算各的；換了一台主機之後也一樣。固定成同一個名稱，換機之後的快照仍然跟舊主機的快照算在同一組。整台主機換機時資料庫與 replica 的搬遷順序，在 [SQLite 換機搬遷演練](/backend/01-database/vendors/sqlite/hands-on/host-migration-drill/)。

## 容器還在跑時換密碼：key passwd 與 .env 的先後

換密碼要改的是 repository 裡的 key 檔（`restic key passwd`），`.env` 只是讓容器之後拿到新密碼。順序反過來（先改 `.env`）就是上一節 `entry-before.sh` 量到的那種停擺。下面的步驟用一個最小的 Compose 專案實測，compose 檔與 `.env` 放在 `<實驗目錄>/compose/`。restic 容器只跑 `sleep infinity`，讓 `exec` 有一個執行中的容器可以進去；正式的 sidecar 在這個位置跑備份迴圈：

```yaml
# <實驗目錄>/compose/compose.yml
name: rlab
services:
  restic:
    image: restic/restic:0.19.1
    entrypoint: ["/bin/sh", "-c", "sleep infinity"]
    environment:
      RESTIC_REPOSITORY: /repo
      RESTIC_PASSWORD: ${RESTIC_PASSWORD}   # 由同目錄的 .env 帶入
    volumes:
      - repo:/repo
volumes:
  repo: {}
```

```bash
cd <實驗目錄>/compose
printf 'RESTIC_PASSWORD=old-pass\n' > .env
docker compose up -d
docker compose exec restic restic init
# 新密碼寫進主機上的暫時檔，複製進容器，在容器裡換掉 key 檔
openssl rand -base64 32 > /tmp/restic-new-pw
docker compose cp /tmp/restic-new-pw restic:/tmp/new-pw
docker compose exec restic restic key passwd --new-password-file /tmp/new-pw
# saved new key as <Key of root@…>
docker compose exec restic rm /tmp/new-pw
```

`key passwd` 用容器環境變數裡的舊密碼打開 repository，再用 `--new-password-file` 的內容包一份新的 key 檔、刪掉舊的。`docker compose cp` 與 `exec` 後面的第一個 `restic` 是 compose 檔裡的服務名稱，換成自己那一份的名稱；`exec` 的第二個 `restic` 才是指令。這次實測的新密碼是一個寫好固定字串的檔案，`openssl rand -base64 32` 那一行沒有實跑，它產生 32 位元組的隨機值、以 base64 印出，長度沒有和其他值比較過。

新密碼的交付方式有兩種替代做法：

- **走暫時檔（上面的做法）**：新密碼不出現在 shell 的歷史紀錄與 `exec` 的程序參數裡，可以寫進腳本；代價是主機的 `/tmp` 與容器的 `/tmp` 各留過一份，要記得刪掉，主機那一份在 `/tmp` 的權限照 umask，同一台主機的其他使用者可能讀得到。
- **不帶 `--new-password-file`**：`key passwd` 改成在終端機上互動詢問新密碼，不留暫時檔；代價是要用 `docker compose exec`（不加 `-T`）取得 TTY，寫不進非互動的腳本。這種做法沒有實跑，行為取自 `restic key passwd --help`。

密碼交給容器的方式本身也有替代做法，這次只實跑了 `.env` 帶入 `RESTIC_PASSWORD` 這一種，另外兩種的行為取自 restic 文件與 Compose 的設定方式，沒有實跑：

- **`.env` 的 `RESTIC_PASSWORD`（這次的做法）**：最直接；代價是密碼成了容器的環境變數，`docker inspect`、`docker compose config` 都印得出來，換密碼時要改 `.env` 再 `up -d` 重建容器。
- **`RESTIC_PASSWORD_FILE` 指向掛進容器的檔案**（Compose 的 `secrets:`，或唯讀掛載的檔案）：密碼不出現在環境變數裡，能讀它的範圍由檔案權限決定；換密碼時換掉那個檔案的內容，容器裡下一次執行 restic 就讀到新值，是否需要重建容器看檔案是怎麼掛進去的。
- **`RESTIC_PASSWORD_COMMAND` 從密碼管理器的命令列工具取**：密碼不落在主機的檔案裡；代價是容器裡要裝那個工具與它的登入憑證，密碼管理器連不上時備份就停。

密碼放在哪裡決定了哪些人或程序讀得到它，判斷方式在 [7.28 密碼學原語選型：金鑰位置決定威脅模型](/backend/07-security-data-protection/cryptographic-primitive-selection/)。

`key passwd` 完成之後、容器還沒拿到新密碼之前，容器裡的 `RESTIC_PASSWORD` 仍是舊的，實測這時 `docker compose exec restic restic cat config` 回傳 12：備份迴圈剛好在這段時間醒來的話，那一次備份會失敗。正式的 sidecar 跑的是上一節 `entry-after.sh` 這類 `set -e` 的腳本時，失敗的那一次備份會讓腳本結束、容器停下，restart 政策再用舊密碼把它帶起來，啟動檢查回傳 12、再結束；這時 `docker compose exec` 進不去正在重啟的容器（從前面量到的行為推論，沒有實跑）。所以改 `.env` 與 `up -d` 重建容器要緊接著做；要避開這段時間窗，也可以在 `key passwd` 之前先暫停備份迴圈（例如把排程改成換完才繼續）。

`.env` 用文字編輯器改，`RESTIC_PASSWORD=` 後面接 `/tmp/restic-new-pw` 的內容，不加引號：Compose 的 `.env` 以第一個 `=` 切開鍵與值，base64 裡的 `/`、`+`、`=` 都照字面帶入（實測 `RESTIC_PASSWORD=ab/cd+ef==` 在容器裡 `printenv` 印出 `ab/cd+ef==`）。值寫錯時，下一步的 `snapshots` 回傳 exit 12。

```bash
# .env 改好之後，刪掉主機上的暫時檔
rm /tmp/restic-new-pw
docker compose up -d restic          # 重建容器，讓它讀到新的 .env
docker compose exec restic restic snapshots --compact
```

`docker compose restart restic` 不會讓容器讀到新的 `.env`：實測改完 `.env` 之後 `restart`，`docker compose exec restic printenv RESTIC_PASSWORD` 印出的仍是舊密碼；`up -d` 重建容器之後才印出新密碼，`snapshots` 回傳 exit 0。Docker 的 `compose restart` 文件也寫明 compose 設定的變更不會在 restart 之後生效。最後把新密碼更新進密碼管理器，理由在 [7.45 加密備份的密碼、key 檔與主金鑰](/backend/07-security-data-protection/backup-encryption-password-and-master-key/) 的〈密碼遺失的後果與事先的準備〉。

已經先改了 `.env` 而備份停擺時，把 `.env` 改回舊密碼、`up -d`，等備份恢復，再照上面的順序換。舊密碼也想不起來時，只要 repository 還有另一份 key 檔（`restic key add` 加過的），可以用那一組密碼打開並執行 `key passwd`；沒有的話，這個 repository 就打不開了。這一段的補救順序是照前面量到的行為推出來的，沒有實跑。

## 密碼可能外洩時：建新 repository 並用 restic copy 搬快照

換密碼擋不住已經拿到舊 key 檔與舊密碼的人，這一點先實測一次。`rlab-repo` 在前面已經有一個快照 `d46a3984`：

```bash
# 換密碼之前，把 keys/ 底下的 key 檔另存一份，模擬它已經外流
docker run --rm -v rlab-repo:/repo -v <實驗目錄>:/lab alpine:3.22 sh -c "cp /repo/keys/* /lab/stolen-keys/"
./r.sh rlab-repo pw-old key passwd --new-password-file /lab/pw-new
./r.sh rlab-repo pw-old cat config     # exit 12：舊密碼打不開
./r.sh rlab-repo pw-new key list       # 只剩一份 key 檔，是新的那一份
echo later > data/c.txt
./r.sh rlab-repo pw-new backup --host lab /lab/data   # 換密碼之後的新快照 af2360cc
# 之後對方又取得一份 repository 副本：整個複製到 rlab-attacker，再把外流的舊 key 檔放回它的 keys/
docker run --rm -v rlab-repo:/src:ro -v rlab-attacker:/dst -v <實驗目錄>:/lab alpine:3.22 \
  sh -c "cp -a /src/. /dst/ && cp /lab/stolen-keys/* /dst/keys/"
./r.sh rlab-attacker pw-old snapshots --compact
# d46a3984  2026-11-03 10:08:48  lab  12 B
# af2360cc  2026-11-03 10:09:07  lab  18 B
```

舊密碼加舊 key 檔列得出換密碼之後才建立的 `af2360cc`。要讓之後的備份不再被讀到，就要換掉主金鑰：建一個新的 repository，再把快照搬過去：

```bash
# 新 repository 用新密碼 pw-fresh；--copy-chunker-params 沿用舊 repository 的切塊參數
docker run --rm -v rlab-repo:/old:ro -v rlab-repo2:/repo -v <實驗目錄>:/lab \
  -e RESTIC_REPOSITORY=/repo -e RESTIC_PASSWORD_FILE=/lab/pw-fresh restic/restic:0.19.1 \
  init --from-repo /old --from-password-file /lab/pw-new --copy-chunker-params
# 舊 repository 唯讀掛載，所以 copy 要加 --no-lock（原因在〈唯讀掛載的還原演練〉一節）
docker run --rm -v rlab-repo:/old:ro -v rlab-repo2:/repo -v <實驗目錄>:/lab \
  -e RESTIC_REPOSITORY=/repo -e RESTIC_PASSWORD_FILE=/lab/pw-fresh restic/restic:0.19.1 \
  copy --no-lock --from-repo /old --from-password-file /lab/pw-new
# snapshot 968bdb1a saved, copied from source snapshot d46a3984
# snapshot 269c1412 saved, copied from source snapshot af2360cc
```

`--from-repo` 是舊 repository 的位置，`--from-password-file` 是能打開它的密碼；`RESTIC_REPOSITORY` 與 `RESTIC_PASSWORD_FILE` 指的是新的那一個。`--copy-chunker-params` 讓之後直接備份到新 repository 的資料，能跟搬過來的快照做重複資料刪除；參數不同時，換過去之後第一次備份會把同樣的內容再存一次。舊 repository 以唯讀掛載，搬遷過程不會改到它；可寫掛載時 `--no-lock` 就不需要，這種掛法這次沒有實跑。快照在新 repository 裡拿到新的 ID，內容用新的主金鑰重新加密。

外流的舊 key 檔對新 repository 沒有用，這一點也實測一次：

```bash
# 把外流的舊 key 檔放進新 repository 的 keys/，再用舊密碼打開
docker run --rm -v rlab-repo2:/repo -v <實驗目錄>:/lab alpine:3.22 sh -c "cp /lab/stolen-keys/* /repo/keys/"
./r.sh rlab-repo2 pw-old cat config
# Fatal: config or key 6c1573d9… is damaged: ciphertext verification failed
# exit 1
```

舊 key 檔解出的是舊主金鑰，對新 repository 的設定檔驗證不過。這一步只是為了驗證，做完把那份舊 key 檔從新 repository 的 `keys/` 刪掉（`restic key list` 看得到它的 ID，用 `restic key remove <ID>`，或直接刪掉那個檔案）。

搬完之後，備份程式改指到新 repository、新密碼更新進密碼管理器，舊 repository 與它的每一份副本都要刪掉；舊的那一份只要還在某處，拿到它的人就讀得到搬遷之前的全部快照。

這次實驗第一次跑 `copy` 時沒有加 `--no-lock`，它幾分鐘內都沒有結果，日誌裡是不斷重試寫鎖檔的 `read-only file system`，原因跟〈唯讀掛載的還原演練〉一節的 restore 相同。

## 唯讀掛載的還原演練：restore 重試十幾分鐘才失敗與 --no-lock

還原演練時把 repository 以唯讀掛載，可以保證演練不會改到正式的備份。下面的 `rlab-repo2` 是前一節建的新 repository、`pw-fresh` 是它的密碼檔、`<實驗目錄>` 掛在容器的 `/lab`；在自己的環境裡，換成自己 repository 的 volume 或路徑，以及自己的密碼來源（`RESTIC_PASSWORD` 或 `RESTIC_PASSWORD_FILE`）。restic 的大多數指令在開始之前會在 repository 的 `locks/` 寫一個鎖檔，唯讀掛載寫不進去，restic 就把它當成暫時的錯誤、等一下再試：

```bash
docker run -d --name rlab-restore-ro -v rlab-repo2:/repo:ro -v <實驗目錄>:/lab \
  -e RESTIC_REPOSITORY=/repo -e RESTIC_PASSWORD_FILE=/lab/pw-fresh restic/restic:0.19.1 \
  restore latest --target /tmp/out
docker logs rlab-restore-ro
# Save(<lock/39f5ccb412>) returned error, retrying after 1.442488361s: open /repo/locks/…-tmp-…: read-only file system
# …
# Save(<lock/39f5ccb412>) returned error, retrying after 39.164765789s: …
```

這一次的兩分鐘內它重試了八次，間隔從 1 秒拉長到 39 秒；間隔是隨機的指數退避，另一次重做時前幾次的間隔是 1、2、5、27 秒，接著就超過一分鐘，次數每次都不同。restic 從 0.17.0 起，對儲存端的請求最多重試 15 分鐘（[0.17.0 的變更紀錄](https://github.com/restic/restic/releases/tag/v0.17.0)，#4627）；另一次重做讓它跑完，restore 在約 15 分鐘後以 exit 1 結束，最後印出 `unable to create lock in backend: … read-only file system`。這段期間容器一直是 running，錯誤訊息只印在 stderr（`docker logs` 看得到；restic 的 stdout 是空的）。腳本把 stderr 丟掉、或只看畫面最後一行的時候，看到的就是一個十幾分鐘沒有輸出的還原。

加上 `--no-lock` 之後 restic 不寫鎖檔，同一個唯讀掛載的還原在一秒內完成：

```bash
docker run --rm -v rlab-repo2:/repo:ro -v <實驗目錄>:/lab \
  -e RESTIC_REPOSITORY=/repo -e RESTIC_PASSWORD_FILE=/lab/pw-fresh restic/restic:0.19.1 \
  restore --no-lock latest --target /tmp/out
# Summary: Restored 5 files/dirs (18 B) in 0:00
```

`--target /tmp/out` 是容器裡的路徑，容器以 `--rm` 結束時還原出來的檔案跟著消失；演練要檢查還原出來的內容時，把它換成掛載進來的主機目錄（例如 `--target /lab/restored`）。

另一種做法是可寫掛載、不加 `--no-lock`：restore 照常寫鎖檔，跟正式的備份容器互相知道對方在做什麼；代價是演練會在正式的 repository 裡寫入鎖檔，掛載的權限也大到改得了備份，這種做法沒有實跑。

`--no-lock` 的代價是 restic 不再知道有沒有別的程序同時在改 repository：演練當下正式的備份容器剛好在跑 `forget --prune`（依保留規則刪除快照、並移除不再被任何快照引用的資料），被刪掉的資料區塊可能正是還原要讀的那幾塊（這是從鎖的用途推論的，沒有實跑）。唯讀掛載只擋得住演練去改 repository，擋不住別的程序改，所以演練排在備份與清理都不執行的時段，或先暫停備份容器。`copy` 的來源 repository 唯讀掛載時同樣要加 `--no-lock`，這次實測加了之後兩個快照都搬成功。

## 清理

實驗留下的容器、Compose 專案與 volume 移除之前，先列出名稱確認都是這次建的：

```bash
docker rm -f rlab-restore-ro                     # 還在跑的話
docker compose -f <實驗目錄>/compose/compose.yml down
docker volume ls -q | grep -E '^rlab[-_]'        # rlab- 是手動建的，rlab_ 是 Compose 專案 rlab 的
```

確認清單之後，用清單上的名稱逐一刪除（`docker volume rm rlab-repo rlab-repo2 rlab_repo …`）。實驗目錄裡的密碼檔、`r.sh`、兩支 entry 腳本與 `stolen-keys/` 一起刪掉。

## 未涵蓋的範圍：物件儲存的 repository、排程與離線保管的備援密碼

- **repository 放在物件儲存或 rest-server**：這次的 repository 都是本機的 Docker volume。append-only 的 rest-server 上 `key passwd` 刪不掉舊 key 檔、舊密碼仍然打得開（另外實測過），這會改變換密碼的判斷，寫在 [7.45 加密備份的密碼、key 檔與主金鑰](/backend/07-security-data-protection/backup-encryption-password-and-master-key/) 的適用條件表之後。物件儲存的存取憑證是否覆寫得了既有備份、append-only 的 rest-server，在 [7.43 兩個網路之間的連線安全](/backend/07-security-data-protection/cross-network-connection-security/) 的異地備份那一段。
- **每小時備份與每天清理的排程**：這次只跑單次的 `backup`，排程迴圈與 `forget --prune` 的保留參數沒有實測。
- **離線保管的備援密碼**：`restic key add` 以另一組密碼再包一份 key 檔、那組密碼離線保管，這次沒有實跑，判斷方式在 [7.45 加密備份的密碼、key 檔與主金鑰](/backend/07-security-data-protection/backup-encryption-password-and-master-key/) 的〈密碼遺失的後果與事先的準備〉。
