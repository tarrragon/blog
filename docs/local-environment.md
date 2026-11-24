# 本機實驗環境的規格、Docker 物件名冊與實驗資料庫的開法

這份文件記錄跑本 repo 實驗用的那台 Mac：裝了哪些工具與版本、Docker 上有哪些物件屬於誰、實驗用的容器怎麼命名與佔哪個埠，以及開一個灌好 seed 的資料庫來做實驗的指令。要在本機做新實驗的人先查〈Docker 物件名冊〉避開名稱與埠的衝突；要在另一台機器重建同樣環境的人照〈在另一台機器照同樣規格配置〉安裝。版本與名冊是 2026-11-24 實查的結果，環境改動之後（升級工具、新增常駐容器）回來更新這兩節。

## 這台機器的規格

| 項目           | 值                                                                       |
| -------------- | ------------------------------------------------------------------------ |
| 硬體           | Apple M4、32 GB 記憶體、arm64                                            |
| 作業系統       | macOS 15.3.1（24D70）                                                    |
| 套件管理       | Homebrew 7.0.15                                                          |
| 容器執行環境   | OrbStack 2.2.1（cask），內含 Docker Engine 29.4.0、Docker Compose v5.1.2 |
| Docker context | `orbstack`（socket 在 `~/.orbstack/run/docker.sock`）                    |
| Docker Desktop | 已移除（2026-11-24），不要再裝：兩套同時在會搶 `docker` 指令與 context   |

工具鏈（`which` 與 `--version` 實查）：

| 工具                    | 版本                         | 路徑與備註                                                                                                                                                       |
| ----------------------- | ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Python                  | 3.15.2                       | `/opt/homebrew/bin/python3`；內建 `sqlite3` 模組連結 SQLite 3.54.1，`verify_*.py` 用的是這一份。`python@3.14` 留著，`mlx`、`ollama` 依賴它，用 `python3.14` 呼叫 |
| sqlite3 CLI（系統）     | 3.43.2                       | `/usr/bin/sqlite3`，PATH 上先找到的是這一支                                                                                                                      |
| sqlite3 CLI（Homebrew） | 3.54.1                       | `/opt/homebrew/opt/sqlite/bin/sqlite3`（keg-only，沒有 link 進 PATH）；要跟驗證腳本同版本時用這一支                                                              |
| PostgreSQL              | 17.12                        | `postgresql@17`（keg-only，已 `brew link --force`，所以 `initdb`、`pg_ctl`、`psql` 在 `/opt/homebrew/bin`）；服務沒有常駐                                        |
| PostgreSQL 18           | 18.7                         | 只在 `postgres:18` 容器裡，本機沒有裝 18 的執行檔                                                                                                                |
| Node.js                 | 24.4.1                       | `/opt/homebrew/bin/node`                                                                                                                                         |
| sql.js                  | 1.13.0（內建 SQLite 3.49.1） | 不在 repo 的 `package.json`，用到時裝到 repo 以外的目錄，見〈sql.js 載入量測〉                                                                                   |
| Hugo                    | 0.151.0 extended             | 建站用                                                                                                                                                           |
| Go                      | 1.27.3                       | 編 `bin/mdtools`、`bin/blogsearch`                                                                                                                               |
| Ollama                  | 0.23.2                       | `brew services` 常駐，聽 `127.0.0.1:11434`                                                                                                                       |

## Docker 物件名冊

**本 repo 的實驗物件**：用完即刪，不常駐。命名一律以 `sqlpractice-` 開頭，埠用 `55432`（避開 PostgreSQL 預設的 5432，讓本機的 `postgresql@17` 之後要常駐也不衝突）。

| 物件           | 名稱                                                                  | 用途                                                        |
| -------------- | --------------------------------------------------------------------- | ----------------------------------------------------------- |
| 映像           | `postgres:18`（18.7，digest `sha256:a47637053e65…`，2026-11-24 拉取） | 保留在本機，重開實驗不必重新下載（約 500 MB）               |
| 容器           | `sqlpractice-pg18`，`127.0.0.1:55432 → 5432`                          | 跑 `verify_pg.py` 或開實驗資料庫，用完 `docker rm -fv` 刪掉 |
| 容器裡的資料庫 | `bookstore`、`cloud_academy`、`swift_logistics`                       | 三個領域各一個                                              |
| 容器裡的角色   | `bookstore_*`、`academy_*`、`logistics_*`（各 10 個）                 | 由 `security_pg.sql` 建立，角色是整個叢集共用的物件         |

**別的專案的常駐物件**：不屬於本 repo，清理 Docker 時不要動。

| 物件    | 名稱                                                                                   | 備註                            |
| ------- | -------------------------------------------------------------------------------------- | ------------------------------- |
| 容器    | `personal-manager-api-1`、`personal-manager-litestream-1`、`personal-manager-restic-1` | api 佔 `127.0.0.1:8080`、`8081` |
| 映像    | `personal-manager-api:latest`、`litestream/litestream:0.5.17`、`restic/restic:0.19.1`  |                                 |
| volume  | `personal-manager_data`                                                                | 該專案的資料，刪了就沒有        |
| network | `personal-manager_default`                                                             |                                 |

**主機上已被佔用的埠**（選新實驗的埠時避開）：`8080`、`8081`（personal-manager）、`11434`（Ollama）、`9000`（php-fpm）、`5000`、`7000`（macOS 的 AirPlay 接收器）。

查目前狀態的指令：

```bash
docker ps -a --format '{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
docker images --format '{{.Repository}}:{{.Tag}}\t{{.Size}}'
docker volume ls
docker network ls
```

`docker volume ls` 出現一串 64 位十六進位名稱的 volume、又沒有容器掛著它（`docker ps -a --filter volume=<名稱>` 沒有輸出）時，多半是刪容器時漏了 `-v` 留下的匿名 volume，見〈用完就刪〉。

## 在另一台機器照同樣規格配置

前提是 Apple Silicon 的 Mac 與 Homebrew。版本號跟上表不同時多半照樣能跑；要重現 README 裡的量測數字，才需要對齊版本。

```bash
brew install --cask orbstack
brew install python@3.15 sqlite postgresql@17 node hugo go
brew link --force postgresql@17   # keg-only，不 link 的話 initdb、pg_ctl、psql 不在 PATH
docker context use orbstack
docker pull postgres:18
```

裝完確認：

```bash
python3 -c 'import sqlite3; print(sqlite3.sqlite_version)'   # 3.37 以上才支援 STRICT 表
psql --version
docker version --format '{{.Server.Version}}'
python3 scripts/sql-practice/verify_domains.py
python3 scripts/sql-practice/verify_questions.py
python3 scripts/sql-practice/verify_pg.py                     # 用本機的 PostgreSQL 17 開拋棄式叢集
```

## 開一個灌好 seed 的實驗資料庫

三個領域的資料都在 `scripts/sql-practice/domains/<領域>/`，各檔的分工見 [scripts/sql-practice/README.md](../scripts/sql-practice/README.md)。以下指令都在 repo 根目錄執行，都實跑過（2026-11-24）。

### SQLite：最快，適合試查詢與執行計畫

```bash
SQLITE=/opt/homebrew/opt/sqlite/bin/sqlite3   # 跟驗證腳本同為 3.54.1；用 /usr/bin/sqlite3 也能跑
D=scripts/sql-practice/domains/bookstore
mkdir -p ~/sqlpractice
$SQLITE ~/sqlpractice/bookstore.db \
  "PRAGMA foreign_keys = ON" \
  ".read $D/schema.sql" \
  ".read $D/seed.sql" \
  "CREATE TEMP TABLE scale_params (mult INTEGER NOT NULL)" \
  "INSERT INTO scale_params VALUES (2)" \
  ".read $D/seed_scale.sql"
$SQLITE ~/sqlpractice/bookstore.db "PRAGMA foreign_key_check" "SELECT count(*) FROM orders"
```

- **換領域**：把 `D` 換成 `cloud-academy` 或 `swift-logistics`，資料庫檔名跟著換。
- **只要語意反例、不要壓測資料**：拿掉 `CREATE TEMP TABLE`、`INSERT INTO scale_params` 與 `.read $D/seed_scale.sql` 三行。
- **倍數**：`VALUES (2)` 的 2 是壓測資料的密度倍數（1 到 10），時間跨度不變。`scale_params` 是暫存表，只活在這一次 `sqlite3` 連線裡，所以這幾個引數要在同一條指令裡給。bookstore 在倍數 2 時 `orders` 有 100009 列，檔案約 28 MB。
- **`~/sqlpractice/`** 是隨意選的 repo 外目錄，資料庫檔是衍生產物，不放進 repo。

### PostgreSQL 18 容器：要試角色、GRANT 與 RLS 時用

```bash
docker run -d --name sqlpractice-pg18 -e POSTGRES_HOST_AUTH_METHOD=trust \
  -p 127.0.0.1:55432:5432 postgres:18
export PGHOST=127.0.0.1 PGPORT=55432 PGUSER=postgres
until pg_isready -q; do sleep 1; done

for name in bookstore cloud-academy swift-logistics; do
  db=${name//-/_}
  D=scripts/sql-practice/domains/$name
  psql -X -q -v ON_ERROR_STOP=1 -d postgres -c "CREATE DATABASE $db" &&
  psql -X -q -v ON_ERROR_STOP=1 -d $db -f $D/schema_pg.sql &&
  grep -v '^PRAGMA' $D/seed.sql | psql -X -q -v ON_ERROR_STOP=1 -d $db &&
  psql -X -q -v ON_ERROR_STOP=1 -d $db -f $D/security_pg.sql &&
  echo "OK $db"
done
```

- **連線參數用環境變數**：`PGHOST`、`PGPORT`、`PGUSER` 讓之後的 `psql`、`pg_isready` 都不必再帶 `-h -p -U`。zsh 不會把 `P="psql -h ..."` 這種變數切成多個引數，所以不要把整條指令存進變數。
- **`grep -v '^PRAGMA'`**：`seed.sql` 是兩引擎共用的檔，開頭的 `PRAGMA foreign_keys` 只有 SQLite 認得，餵給 PostgreSQL 前濾掉。
- **`POSTGRES_HOST_AUTH_METHOD=trust`** 讓任何連線免密碼登入，只用在綁定 `127.0.0.1`、用完就刪的容器。
- **`seed_scale.sql` 只供 SQLite**，PostgreSQL 這邊只有基礎 seed 的資料量。
- **再灌一次要開新容器**：`security_pg.sql` 建的角色是叢集層級的物件，`DROP DATABASE` 不會刪掉它們，在同一個容器重跑會在 `CREATE ROLE` 報錯。

以應用程式角色、帶租戶設定查詢，看 RLS 的效果（`postgres` 是超級使用者，不受 RLS 限制）：

```bash
psql -X -q -At -d swift_logistics \
  -c "BEGIN" \
  -c "SET LOCAL ROLE logistics_app" \
  -c "SET LOCAL app.current_merchant_id = '1001'" \
  -c "SELECT count(*) FROM shipments" \
  -c "COMMIT"
# 印 5；用 postgres 直接查 shipments 是 8 列
```

各領域 RLS 讀的設定名：bookstore 是 `app.current_store_code` 與 `app.is_global_scope`，cloud_academy 是 `app.current_org_id` 與 `app.current_user_id`，swift_logistics 是 `app.current_merchant_id`。

跑自動驗證而不是手動實驗時，容器開好之後改跑 `python3 scripts/sql-practice/verify_pg.py --dsn-host 127.0.0.1 --dsn-port 55432 --dsn-user postgres`；它自己建資料庫與角色，所以要接在一個剛開、還沒灌過資料的容器上。

### sql.js 載入量測：要重現 README 的 WASM 載入成本表時用

```bash
SQLJS=~/sqlpractice/sqljs
npm install --prefix $SQLJS sql.js@1.13.0
node scripts/sql-practice/wasm_load_bench.mjs $SQLJS
```

`wasm_load_bench.mjs` 印出倍數 1、3、10 在三個領域灌入 `seed_scale.sql` 的耗時與資料庫大小，外鍵違規數不是 0 時 exit 1。sql.js 裝在 repo 以外，所以 repo 的 `package.json` 不變。大小每次都一樣；耗時隨機器負載浮動，在這台機器上重跑的差距約一成。

## 用完就刪

```bash
docker rm -fv sqlpractice-pg18
```

`-v` 連同容器的匿名 volume 一起刪。`postgres:18` 映像宣告了 `VOLUME /var/lib/postgresql`，所以每個容器啟動時 Docker 會替它建一個匿名 volume 放資料；只下 `docker rm -f` 時容器刪掉了，volume 留下來，沒有任何容器指向它。2026-11-24 清 Docker 時就找到一個這樣留下來的 volume。

要讓實驗資料跨容器保留時，改掛具名 volume，並把名稱登記進〈Docker 物件名冊〉：

```bash
docker run -d --name sqlpractice-pg18 -e POSTGRES_HOST_AUTH_METHOD=trust \
  -p 127.0.0.1:55432:5432 -v sqlpractice-pg18-data:/var/lib/postgresql postgres:18
```

具名 volume 不會被 `docker rm -fv` 刪掉，不再需要時用 `docker volume rm sqlpractice-pg18-data` 刪。PostgreSQL 18 的映像把資料目錄放在 `/var/lib/postgresql/18/docker`，掛載點是上一層的 `/var/lib/postgresql`；17 以前的映像掛 `/var/lib/postgresql/data`，兩者不能混用同一個 volume。
