---
title: "SQLite 換機搬遷演練：Litestream restore、UID 對齊與停用舊主機的複製"
date: 2026-11-03
description: "家用主機要換新機、SQLite 資料庫由 Litestream 持續備份時，從 replica 把資料還原到新主機的步驟、只複製資料庫主檔會少掉的資料、還原後容器寫入時出現 attempt to write a readonly database 的成因，以及舊主機的複製沒停掉時 replica 裡會少掉哪些寫入"
tags: ["backend", "database", "sqlite", "hands-on", "litestream", "backup", "docker"]
---

**事件說明**：2026-11-03 在 macOS 的 OrbStack（Docker 29.4.0）上實測，Litestream 是 `litestream/litestream:0.5.17` 映像，SQLite CLI 是 Alpine 3.22 套件裡的 3.49.2。操作是把一個由 Litestream 持續備份的 SQLite 資料庫，從一台主機搬到另一台主機。

這篇記錄把 SQLite 資料庫從舊主機搬到新主機的完整過程。舊主機的資料庫由應用程式容器寫入，旁邊另有一個掛同一個資料 volume 的 Litestream 容器（sidecar 容器；SQLite 文件裡的 sidecar file 指的是 `-wal`、`-shm` 檔，是另一個所指）負責持續備份。搬遷的部分依序是：只複製資料庫主檔時拿到的資料與實際資料的差距；停止寫入、停止複製與停用舊主機服務的順序；在新主機以 `litestream restore` 還原並驗證筆數；還原出來的檔案擁有者跟應用程式容器的 UID 不一致時的寫入錯誤；新主機接手往同一個 replica 複製。最後兩節是舊主機的 Litestream 在搬遷之後又啟動時、兩台主機同時往同一個 replica 寫入的結果，以及資料庫放 named volume 還是 bind mount 的取捨。備份方法本身的比較（`.backup`、`VACUUM INTO`、Litestream）在 [SQLite file lifecycle 與 backup boundary](/backend/01-database/vendors/sqlite/file-lifecycle-backup-boundary/)，單機上的 `.backup` 還原演練在 [SQLite Backup Restore Drill](/backend/01-database/vendors/sqlite/hands-on/backup-restore-drill/)，Litestream 在 replication 光譜上承擔哪一種責任在 [SQLite Litestream / LiteFS Replication](/backend/01-database/vendors/sqlite/litestream-litefs-replication/)。

## 實驗的形狀：兩個 Compose 專案代表兩台主機

這次只有一台 Mac，兩台主機用兩個 Docker Compose 專案代表：`oldhost` 與 `newhost` 各有自己的 named volume 放資料庫，兩邊共用一個名為 `lab-replica` 的 volume 當 replica。Litestream 的 replica 類型用 `file`，寫進那個共用的 volume；它在這次實驗裡代表 NAS 上的共享資料夾或 S3 這類物件儲存。真正的兩台主機不會共用 Docker volume，replica 會放在兩台都連得到的物件儲存，還原與搬遷的順序相同，差在 `litestream.yml` 的 `replica` 區塊與憑證。下面這一段取自 [Litestream 的設定文件](https://litestream.io/reference/config/)，這次沒有實跑：

```yaml
dbs:
  - path: /data/app.db
    replica:
      type: s3
      bucket: <bucket 名稱>
      path: app
      endpoint: <S3 相容服務的端點，AWS S3 不必填>
```

憑證不寫進設定檔，以環境變數 `LITESTREAM_ACCESS_KEY_ID` 與 `LITESTREAM_SECRET_ACCESS_KEY` 交給 Litestream 容器（Compose 的 `environment`，或 `docker run -e`），兩台主機與執行 restore 的那一次 `docker run` 都要給。真實換機時，新主機上另外要準備 `lab-sqlite` 這類應用程式映像（重新 build 或從 registry 拉）、`litestream.yml`、應用程式的設定檔與 compose 檔；下文用 `sed` 從舊主機的 compose 檔產生新主機那一份，是因為這次兩個專案在同一台 Mac 上。

應用程式用一個每秒寫一筆的 shell 迴圈代表，寫入的那一列記下 `$HOSTNAME`，之後從資料庫就查得出每一列是哪一台主機寫的。Litestream 映像裡沒有 shell 也沒有 `sqlite3`，所以另外建一個裝了 SQLite CLI 的小映像，應用程式與所有查詢都用它：

```bash
# 實驗目錄：放這篇所有的設定檔；後面的指令都在這個目錄執行
mkdir -p ~/sqlite-migration-lab && cd ~/sqlite-migration-lab
printf 'FROM alpine:3.22\nRUN apk add --no-cache sqlite\n' > Dockerfile
docker build -q -t lab-sqlite:3.22 .
```

`litestream.yml` 指定要複製哪一個資料庫、複製到哪裡；兩台主機用同一份，`/replica/app` 是 replica 在共用 volume 裡的路徑：

```yaml
dbs:
  - path: /data/app.db
    replica:
      type: file
      path: /replica/app
```

`writer.sh` 是應用程式：建表之後每秒插入一列。`busy_timeout` 讓寫入遇到 Litestream 正在 checkpoint 時最多等 5000 毫秒，等不到才回傳 `SQLITE_BUSY`；這個值沒有和其他值比較過：

```sh
#!/bin/sh
sqlite3 /data/app.db "PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY, body TEXT NOT NULL, created_at TEXT NOT NULL) STRICT;"
while true; do
  sqlite3 /data/app.db "PRAGMA busy_timeout=5000; INSERT INTO notes(body, created_at) VALUES ('$HOSTNAME', datetime('now'));"
  sleep 1
done
```

## 舊主機：應用程式容器加 Litestream sidecar 容器

`compose.old.yml` 讓兩個容器掛同一個 named volume `data`，Litestream 另外掛 replica 的 volume。`hostname` 決定 `writer.sh` 寫進每一列的主機名稱：

```yaml
name: oldhost
services:
  app:
    image: lab-sqlite:3.22
    hostname: oldhost
    command: ["/lab/writer.sh"]
    volumes:
      - data:/data
      - ./writer.sh:/lab/writer.sh:ro
  litestream:
    image: litestream/litestream:0.5.17
    command: ["replicate", "-config", "/etc/litestream.yml"]
    volumes:
      - data:/data
      - replica:/replica
      - ./litestream.yml:/etc/litestream.yml:ro
volumes:
  data: {}
  replica:
    name: lab-replica   # 固定名稱，新主機的專案才掛得到同一個 volume
```

```bash
chmod +x writer.sh
docker compose -f compose.old.yml up -d
docker compose -f compose.old.yml logs litestream
```

日誌裡出現 `replicating to type=file sync-interval=1s path=/replica/app` 與 `snapshot complete` 之後，Litestream 開始每秒把新的寫入送進 replica。`sync-interval=1s` 是 0.5.17 的預設值，它決定主機在兩次同步之間故障時最多遺失幾秒的寫入；調大可以減少送往 replica 的請求數（物件儲存依請求數計費時省的是這一項），代價是遺失的時間範圍跟著變大。這次用預設值，沒有比較其他值。`litestream status` 列出資料庫的同步狀態：

```bash
docker compose -f compose.old.yml exec litestream litestream status -config /etc/litestream.yml
# database      status  local txid        wal size
# /data/app.db  ok      0000000000000014  103 kB
```

`local txid` 是 Litestream 替每一個寫入交易遞增的編號，以十六進位印出（`14` 是第 20 個）。它數的是交易，不是列：建表是一個交易，`writer.sh` 每插入一列也是一個交易，所以它跟 `notes` 的筆數接近而不相等，後文比對的是交易編號本身。

replica 目錄底下是 Litestream 的 `.ltx` 檔（LTX 是 Litestream 存交易變更的檔案格式），檔名是它涵蓋的第一個與最後一個交易編號。`ltx/0/` 是每次同步送出的檔（日誌裡的 L0），每個檔一個交易範圍；`ltx/1/` 以上是 Litestream 定期把小檔合併成大檔（日誌裡的 compaction）的結果，`ltx/9/` 放快照。列出 replica 目錄：

```bash
docker run --rm -v lab-replica:/replica:ro lab-sqlite:3.22 ls -R /replica/app
```

`/data` 底下的 `.app.db-litestream` 資料夾是 Litestream 放在資料庫旁邊的本機狀態，這次沒有細看內容。

## 只複製資料庫主檔拿到的資料

舊主機的資料庫在 named volume `oldhost_data` 裡：Compose 替 named volume 取的名稱是「專案名_volume 名」，`compose.old.yml` 的專案名是 `oldhost`、volume 名是 `data`，`docker volume ls` 列得出實際的名稱。舊主機運作中、寫入了 30 筆時，把 `app.db` 一個檔案複製出去再查，只查得到 1 筆：

```bash
docker volume create lab-naive
docker run --rm -v oldhost_data:/data:ro -v lab-naive:/out lab-sqlite:3.22 \
  sh -c 'cp /data/app.db /out/app.db && sqlite3 /out/app.db "SELECT COUNT(*) FROM notes;"'
# 1
docker compose -f compose.old.yml exec app sqlite3 /data/app.db "SELECT COUNT(*) FROM notes;"
# 30
```

`docker compose -f compose.old.yml exec app ls -la /data` 看得到差距的位置：`app.db` 只有 8192 位元組，`app.db-wal` 有 98912 位元組。WAL mode 下新的寫入先進 `-wal` 檔，checkpoint 才把它們合併回主檔；Litestream 的 How it works 文件說明它以一個長時間的讀取交易阻止其他程序做 checkpoint、由它自己決定 checkpoint 的時機，所以 WAL 裡常常累積著還沒合併的寫入（這次沒有另外驗證 0.5.17 是否仍用這個做法，觀察到的是主檔與 WAL 的大小差距）。直接複製整個資料夾（含 `-wal` 與 `-shm`）也一樣有風險：複製的那幾毫秒之間應用程式仍在寫，三個檔案可能不是同一個時間點的狀態（[SQLite file lifecycle 與 backup boundary](/backend/01-database/vendors/sqlite/file-lifecycle-backup-boundary/) 的 Backup boundary 一節）。換機時要拿的是 Litestream replica 裡依交易排好的資料，或在應用程式停止、WAL 合併之後的檔案。

## 停止寫入，再停止 Litestream

停應用程式要排在停 Litestream 之前。順序反過來時，Litestream 停下之後應用程式還寫了幾秒，那幾筆只在舊主機的 WAL 裡，不在 replica 裡，新主機還原出來的資料就少了這幾筆：

```bash
docker compose -f compose.old.yml stop app
# app 容器已經停止，另起一個一次性的容器查最後的筆數，等一下用來對照新主機
docker compose -f compose.old.yml run --rm --no-deps app \
  sqlite3 /data/app.db "SELECT COUNT(*), MAX(id) FROM notes;"
# 47|47
docker compose -f compose.old.yml exec litestream litestream status -config /etc/litestream.yml
# /data/app.db  ok      000000000000002e  206 kB
docker compose -f compose.old.yml stop litestream
```

`docker compose stop` 送出 SIGTERM，Litestream 的日誌記下 `signal received, litestream shutting down` 與 `litestream shut down`；停下之前它把最後一批寫入送進 replica，replica 的 `ltx/0/` 最後一個檔是 `000000000000002e-000000000000002e.ltx`，跟停止前 `status` 印的 local txid `000000000000002e` 相同。

舊主機的 Litestream 停下之後，還要讓它在舊主機重開機後也不會自己啟動，這一步排在新主機開始複製之前，理由在〈舊主機的 Litestream 未停用〉一節：兩台同時往同一個 replica 寫，replica 會少掉其中一台的寫入。compose 檔設了 `restart: always` 時，只用 `stop` 停下的容器會在 Docker daemon 重新啟動（例如重開機）之後被帶起來，`restart: unless-stopped` 則不會（Docker 文件的 restart policy 說明）。真實搬遷時依舊主機管理服務的方式擇一：

```bash
# Compose 管的服務：移除容器；named volume 留著，舊主機的資料庫仍在，可以當回頭的退路
docker compose -f compose.old.yml down
# systemd 管的服務：停止並取消開機啟動，<服務名> 填舊主機上 Litestream 那個 unit 的名稱
sudo systemctl disable --now <服務名>
```

這次的演練為了在〈舊主機的 Litestream 未停用〉一節把舊主機重新啟動，只用了上面的 `stop`；`down` 與 `disable` 這次沒有實跑。

`down` 之後留著的舊資料庫只在新主機開始往 replica 寫入之前算得上退路。新主機寫過之後，舊主機的資料庫已經比 replica 舊，直接把舊主機的服務帶起來，就是〈舊主機的 Litestream 未停用〉一節量到的情形：舊主機的 Litestream 接著往同一個 replica 寫，新主機的寫入從 replica 裡消失。這時要退回舊主機，先停用新主機的 Litestream，再在舊主機上用 `restore -force` 從 replica 重新還原一份，舊主機拿到的就是包含新主機寫入的資料；這條回退路徑是照兩台寫同一個 replica 的實測推論的，沒有實跑。

這篇走的是計畫中的換機，兩台主機同時開得了機。另外兩種情形用的是同一組步驟的一部分：

- **不經由 replica、直接搬檔案**：舊主機停掉應用程式之後，用 `sqlite3 /data/app.db ".backup /data/app-move.db"` 這類 SQLite 的備份方式產生一份一致的檔案，搬到新主機再啟動。換到的是搬遷不依賴 replica 與 Litestream 的版本；付出的是少了一次「從 replica 還原」的實際演練，而哪一天舊主機突然壞掉，要用的正是那條路。`.backup` 的做法在 [SQLite Backup Restore Drill](/backend/01-database/vendors/sqlite/hands-on/backup-restore-drill/)，搬檔這條路這次沒有實跑。
- **舊主機已經壞掉**：步驟從〈新主機：從 replica 還原〉開始，資料停在舊主機最後一次送進 replica 的那個交易，遺失範圍最多是一個 `sync-interval`。舊主機修好之後，開機之前先讓它的 Litestream 不會自動啟動（拔掉網路、或在救援模式裡停用服務），否則一開機就回到兩台寫同一個 replica 的情形。

`litestream sync` 也能在不停服務的情況下強制送出一次，`-wait` 等到送進 replica 才返回。它不讀設定檔，`litestream sync -config …` 回傳 `flag provided but not defined: -config`；它經由 Litestream 的控制 socket（預設 `/var/run/litestream.sock`）連到執行中的 `replicate` 程序，而這次的 `litestream.yml` 沒有設定這個 socket，所以搬遷用停止服務的方式，`sync` 這條路沒有實跑。換機時應用程式本來就要停，停止服務讓「最後一筆在哪裡」只有一個答案。

## 新主機：從 replica 還原

開始這一步之前，舊主機的 Litestream 已經用 `down` 或 `disable` 停用（查法在〈舊主機的 Litestream 未停用〉最後一段）。新主機先建一個空的 named volume，再用 `litestream restore` 從 replica 還原；應用程式容器以非 root 的使用者執行時，restore 那一行要加 `--user`，原因在下一節〈還原出來的檔案擁有者與應用程式容器的 UID〉。volume 的名稱要等於新主機的 Compose 專案稍後會掛的那一個：`compose.new.yml` 的專案名是 `newhost`，所以是 `newhost_data`。名稱打錯時 `docker run -v` 不報錯，會另外建一個空的 volume，資料還原進那一個，應用程式啟動時掛到的是另一個空的 volume，用空的資料庫開始寫。

新主機用的 Litestream 版本跟舊主機相同最單純，兩邊都跑 `litestream version` 就查得到。兩三年後換機時，新主機拉到的映像可能是更新的版本：Litestream 的 [restore 文件](https://litestream.io/reference/restore/)寫明 v0.5.7 以後的 `restore` 會自動辨識 v0.3.x 格式的舊備份並還原，[遷移說明](https://litestream.io/docs/migration/)另外寫明 v0.3.x 用 Age 加密的備份 v0.5 還原不了，要留著 v0.3 的執行檔還原。跨大版號換機時，先讀那一版的 release notes，再用新版本對 replica 做一次還原演練。`-o` 指定還原出來的檔案路徑，最後一個引數是 replica 的位置；物件儲存的 replica 這裡寫 `s3://<bucket>/<path>`，或給 `-config` 讓它從設定檔讀：

```bash
docker volume create newhost_data
docker run --rm -v lab-replica:/replica:ro -v newhost_data:/data \
  litestream/litestream:0.5.17 restore -o /data/app.db file:///replica/app
docker run --rm -v newhost_data:/data lab-sqlite:3.22 \
  sqlite3 /data/app.db "PRAGMA integrity_check; SELECT COUNT(*), MAX(id) FROM notes; PRAGMA journal_mode;"
# ok
# 47|47
# wal
```

驗收看三個值：`integrity_check` 回 `ok`、筆數與最大 id 跟停止寫入時記下的 `47|47` 相同、journal mode 仍是 `wal`。筆數比記下的少時，先查停止寫入與停止 Litestream 的順序：Litestream 先停的話，之後寫入的那幾筆不在 replica 裡。這次的資料庫只有 16 KB，`restore` 加上容器啟動在 0.15 秒內完成；還原時間隨 replica 裡的 `.ltx` 檔數與資料庫大小增加，要拿自己的資料量量一次，結果寫進 RTO 的估計（[SQLite Backup Restore Drill](/backend/01-database/vendors/sqlite/hands-on/backup-restore-drill/) 的 RPO / RTO Note）。

`restore` 不覆蓋已經存在的檔案：輸出路徑已經有 `app.db` 時，它回傳 exit 1 與 `cannot restore, output path already exists and is not empty: /data/app.db. Use -force to overwrite`。兩個旗標改變這個行為，各自用在不同的位置：

```bash
# 已經有資料庫就跳過、exit 0：放在容器啟動腳本裡，第一次啟動還原、之後的重啟不動既有的資料
litestream restore -if-db-not-exists -o /data/app.db file:///replica/app
# 覆蓋既有的資料庫與它的 -wal、-shm：只在確定要丟掉新主機上現有的資料時手動執行
litestream restore -force -o /data/app.db file:///replica/app
```

`-if-db-not-exists` 這次實跑過，它印出 `database already exists, skipping` 並回 exit 0；`-force` 的說明取自 `restore -h`，沒有實跑。

## 還原出來的檔案擁有者與應用程式容器的 UID

應用程式容器用非 root 的使用者執行時，還原出來的檔案擁有者要是同一個 UID。這次讓應用程式以 UID 1000 執行、`restore` 照預設以 root 執行，還原之後應用程式的第一筆寫入失敗：

```bash
docker volume create lab-uidrestore
docker run --rm -v lab-uidrestore:/data lab-sqlite:3.22 chown 1000:1000 /data
docker run --rm -v lab-replica:/replica:ro -v lab-uidrestore:/data \
  litestream/litestream:0.5.17 restore -o /data/app.db file:///replica/app
docker run --rm --user 1000:1000 -v lab-uidrestore:/data lab-sqlite:3.22 \
  sqlite3 /data/app.db "INSERT INTO notes(body, created_at) VALUES ('after-restore', datetime('now'));"
# Error: stepping, attempt to write a readonly database (8)
```

`ls -lan /data` 顯示 `app.db` 的擁有者是 `0 0`、權限 `-rw-r--r--`：資料夾是 UID 1000 的，檔案是 root 的，UID 1000 只讀得到它。錯誤碼 8 是 `SQLITE_READONLY`，訊息裡沒有提到擁有者，讀到這個錯誤時先看檔案與它所在資料夾的擁有者：另外試過把 `app.db` 改成 UID 1000 擁有、資料夾留給 root，寫入一樣回傳 `attempt to write a readonly database (8)`，SQLite 在寫入時要在同一個資料夾建 `-wal` 與 `-shm` 檔。named volume 的擁有者怎麼決定，在 [Docker Named Volume Ownership](/linux/dotfile/knowledge-cards/docker-named-volume-ownership/)。執行 restore 的那一行 `docker run` 加上 `--user 1000:1000`，`litestream restore` 就以同一個 UID 執行，還原出來的檔案擁有者是 `1000 1000`，同一筆寫入成功：

```bash
docker volume create lab-uidrestore2
docker run --rm -v lab-uidrestore2:/data lab-sqlite:3.22 chown 1000:1000 /data
docker run --rm --user 1000:1000 -v lab-replica:/replica:ro -v lab-uidrestore2:/data \
  litestream/litestream:0.5.17 restore -o /data/app.db file:///replica/app
docker run --rm --user 1000:1000 -v lab-uidrestore2:/data lab-sqlite:3.22 \
  sh -c "ls -lan /data/app.db; sqlite3 /data/app.db \"INSERT INTO notes(body, created_at) VALUES ('after-restore', datetime('now'));\""
# -rw-r--r--    1 1000     1000         24576 ... /data/app.db
# （INSERT 成功時沒有輸出，exit 0）
```

`1000` 換成自己應用程式容器實際的 UID：在舊主機上跑 `docker compose -f compose.old.yml exec app id -u`，或看 compose 檔的 `user:` 與映像的 `USER` 設定。`chown` 那一行不能省：`docker run -v` 自動建出來的 volume 擁有者是 root，UID 1000 寫不進去，restore 回傳 `Error: create temp database path: open /data/app.db.tmp: permission denied` 與 exit 1。另一種做法是照預設以 root 還原，再用一次性的容器 `chown 1000:1000 /data/app.db`：不必知道 restore 映像接不接受非 root 使用者，代價是多一步，漏掉時就是上面那個錯誤；這種做法沒有實跑。

日常複製的 Litestream sidecar 容器另外測了一組，Compose 專案名是 `uidlab`：先用一次性的容器把資料 volume 的擁有者改成 1000，應用程式容器設 `user: "1000:1000"`，Litestream 照映像預設以 root 執行，兩者掛同一個 volume。這組沒有出現權限錯誤：資料庫由應用程式建立，擁有者是 1000，Litestream 在 `/data` 底下建的 `.app.db-litestream` 資料夾擁有者也是 1000，跟資料庫檔案一致。所以 UID 的不一致出在搬遷時另外跑的那一次 `restore`，而不是日常複製的 sidecar。

## 新主機接手往同一個 replica 複製

新主機的 `compose.new.yml` 跟舊主機那一份只差專案名稱與 `hostname`，`replica` 仍是 `lab-replica`：

```bash
sed -e 's/name: oldhost/name: newhost/' -e 's/hostname: oldhost/hostname: newhost/' \
  compose.old.yml > compose.new.yml
docker compose -f compose.new.yml up -d
```

新主機的 Litestream 啟動時印出 `detected database behind replica db_txid=0000000000000000 replica_txid=000000000000002e` 與 `fetched latest L0 file from replica`：還原出來的檔案沒有 Litestream 自己的狀態，它從 replica 取得最後的交易編號，接著往後送。12 秒之後新主機的資料庫有 60 筆，`status` 的 local txid 是 `000000000000003a`，交易編號從舊主機停下的位置往後接。

接手同一個 replica 路徑的好處是 replica 只有一份，之後要還原時不必知道搬遷發生在哪一天。另一種做法是新主機改寫到新的 `path`（例如 `/replica/app-2026`），舊的 replica 原封不動留著當搬遷前的封存，代價是儲存空間多一份，以及要記得哪一份是現行的；這種做法這次沒有實跑，行為是從設定推論的。

## 舊主機的 Litestream 未停用：兩台主機寫同一個 replica

新主機接手之後，舊主機的兩個容器又被啟動（`docker compose -f compose.old.yml start`），模擬舊主機的服務沒有停用、開機後被 `restart: always` 帶起來的情形（這次的 compose 檔沒有設 restart，用 `start` 代替重開機）。兩台主機的應用程式各自寫入、兩個 Litestream 同時往 `lab-replica` 送；啟動之後約 25 秒時查兩邊的日誌與 `status`，約 35 秒時從 replica 還原到第三個 volume `lab-verify`，接著查兩台本機的筆數：

| 觀察的位置                     | 舊主機                                                                                          | 新主機                                                                           |
| ------------------------------ | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `litestream status`            | `ok`                                                                                            | `ok`                                                                             |
| 日誌裡層級最高的一行           | INFO：`detected database behind replica db_txid=000000000000002e replica_txid=0000000000000042` | ERROR：`compaction failed … rename …0000000000000043-0000000000000060.ltx.tmp` |
| 本機資料庫的內容（依主機分組） | `oldhost` 83 筆（id 1 到 83；48 到 83 是重新啟動之後寫的）                                      | `oldhost` 47 筆（id 1 到 47）、`newhost` 56 筆（id 48 到 103）                   |

還原出來的 `lab-verify` 裡，`integrity_check` 回 `ok`，內容是 `oldhost` 47 筆與 `newhost` 55 筆：replica 裡留下的是新主機寫入的那一串交易，舊主機重新啟動之後寫的 36 筆（id 48 到 83）不在 replica 裡。新主機本機比還原結果多一筆，從指令的先後推斷是還原之後才寫入的那一筆，沒有另外驗證。兩台本機的 id 48 到 83 是不同的列，各自寫在自己的資料庫裡。舊主機的 Litestream 啟動時偵測到自己的 `2e` 落後 replica 的 `42`，取回 replica 上最後一個 L0 檔之後照常往下送；兩台的交易編號因此在同一個範圍裡各自往後長，寫出同名的 `.ltx` 檔，後寫的蓋掉先寫的。Litestream 沒有把這件事當成錯誤，`status` 兩邊都是 `ok`，舊主機只在啟動時印了那一行 INFO，新主機有一次合併失敗的 ERROR。用同樣的設定第二次重做時，兩台的日誌都只有 INFO、沒有任何 ERROR，還原結果同樣少了舊主機重新啟動之後的全部寫入；ERROR 那一行出不出現，兩次執行的結果不同。哪一台的寫入留下來取決於兩邊寫檔的時間，換一次執行可能是另一台的資料留下來，也可能兩台的檔案交錯。

從 replica 的檔案分不出有沒有第二個寫入者：新主機接手之後本來就每秒寫新的 `.ltx`，檔案的修改時間一直在更新，兩台的 `status` 也都是 `ok`。所以確認舊主機沒有在寫，要查舊主機本身：`docker ps -a` 列不出它的 Litestream 容器（用 `down` 移除之後），或 systemd 的 `systemctl is-enabled <服務名>` 回 `disabled`。

## 資料庫放 named volume 還是 bind mount

這次的資料庫一律放在 named volume，原因在 SQLite 的 WAL 機制。依 SQLite 的 WAL 文件，WAL mode 用 `-shm` 檔當共享記憶體協調讀寫，所有使用同一個資料庫的程序必須在同一台機器上。macOS 上的 Docker 跑在一台 Linux 虛擬機裡，bind mount 的目錄經由虛擬機的檔案分享（OrbStack 是 virtiofs）掛進容器；容器裡的程序與 Mac 上的程序同時開同一個資料庫時，對 SQLite 來說它們在兩台機器上，`-shm` 的共享記憶體語意不保證成立。named volume 放在虛擬機自己的磁碟裡，Mac 上的程式碰不到那個檔案，資料庫只會被容器裡的程序打開。這個理由只適用於 Docker 跑在虛擬機裡的環境（macOS 與 Windows 上的 Docker Desktop、OrbStack）；Linux 主機上的 Docker 沒有虛擬機這一層，容器與主機的程序在同一個核心上，bind mount 不會跨機器，這是從架構推論的，這次沒有在 Linux 上實跑。

這次另外做了一次對照：把同一個 `writer.sh` 改用 bind mount 跑，Mac 上的 `/usr/bin/sqlite3`（3.43.2）同時讀了五次、寫了一筆，五次的筆數跟容器裡讀到的一致，`integrity_check` 回 `ok`。這只是一次十幾秒的實測，沒有出現錯誤不代表跨虛擬機的共享記憶體語意成立；SQLite 文件列出的是不保證成立的條件，損壞會在負載與時序湊上時才出現。要從 Mac 上查資料，從 replica 還原一份到別的路徑查，或用 `docker compose exec app sqlite3` 在容器裡查。

## 清理

實驗留下的容器與網路由 `docker compose down` 移除；volume 要另外刪，刪之前先列出名稱，確認清單裡都是這次建的：

```bash
docker compose -f compose.old.yml down
docker compose -f compose.new.yml down
# uidlab 專案的 compose 檔不在本文裡，照自己建的那一份 down
docker volume ls -q | grep -E '^(lab-|oldhost_|newhost_|uidlab_)'
```

還有容器在用的 volume，`docker volume rm` 回傳 `volume is in use` 並列出容器的 ID，先 `down` 那個專案再刪。

確認清單之後，用清單上的名稱逐一刪除（`docker volume rm lab-replica oldhost_data …`）。

## 未涵蓋的範圍：附件資料夾、物件儲存的 replica、入口切換與大型資料庫

- **附件資料夾**：應用程式把附件存成檔案、資料庫只記路徑時，Litestream 只複製資料庫，附件資料夾要用另一個工具備份與搬遷，還原後要比對資料庫裡的路徑與實際存在的檔案。
- **物件儲存的 replica**：存取憑證的權限與物件版本保留決定備份能不能被覆寫，失敗推演在 [7.43 兩個網路之間的連線安全](/backend/07-security-data-protection/cross-network-connection-security/) 的異地備份那一段。
- **兩台實體主機與網路入口的切換**：Tailscale 這類入口在換機時要把裝置名稱或 DNS 指到新主機，這次沒有涉及。
- **大型資料庫的還原時間**：這次的資料庫只有 16 KB。
