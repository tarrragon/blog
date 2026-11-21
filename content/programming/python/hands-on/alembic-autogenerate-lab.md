---
title: "Alembic autogenerate 的實測紀錄：改名與縮窄型別產生的 migration、交易回滾、alembic check、兩個 head 的合併與並行套用的建議鎖"
date: 2026-11-21
description: "要用 Alembic 從 SQLAlchemy model 產生 PostgreSQL 的 migration，想先知道它在欄位改名、縮窄型別、資料庫被手動改過、兩個分支各自新增 migration，以及多個程序同時套用時怎麼反應、要怎麼改寫時讀"
weight: 1
tags: ["python", "alembic", "sqlalchemy", "postgresql", "migration", "hands-on"]
slug: "alembic-autogenerate-lab"
---

實測日期是 2026-11-21，環境是 macOS 15 的筆電，PostgreSQL 17.12（Homebrew 的 `postgresql@17`，在專案目錄裡另外建一個只給這次用的資料庫 cluster），Python 3.14.4、SQLAlchemy 2.1.9、Alembic 1.20.1、psycopg 3.3.9，套件以 uv 安裝；這次的操作是從一張優惠券資料表開始，依序改 model、產生 migration、套用，並刻意製造改名、縮窄型別、手動變更、分支合併與並行套用的情形。

這篇記錄用 Alembic 從 SQLAlchemy 的 model 產生 migration 的完整操作：建一個只給這次用的 PostgreSQL；`alembic init` 產生的檔案與 `env.py` 裡要指定的 model；第一份 migration 建表；把欄位 `rate` 改名成 `discount`、把 `code` 從 `varchar(50)` 縮成 `varchar(20)` 時 autogenerate 產生了什麼、`--sql` 印出的 SQL、原樣套用時的失敗與另一種會默默丟資料的情形；把產生的 migration 改寫成改名之後，縮窄型別遇到過長的資料時整份隨交易回滾（transaction rollback，資料庫撤銷交易裡做過的變更）；`alembic check` 偵測 model 與資料庫的差異，以及它比對與不比對的項目；兩個分支各自新增 migration 之後的兩個 head 與 `alembic merge`；兩個程序同時 `alembic upgrade head` 的結果，以及在 `env.py` 加上 PostgreSQL 建議鎖之後的結果；最後是清理。四種 schema 變更做法的比較、為什麼比對 model 推不出改名與資料轉換、表鎖與 `lock_timeout` 的機制，寫在 [1.20 Schema 變更由誰寫出、何時套用](/backend/01-database/schema-change-management/)；同樣的情形在手寫 migration 的工具上的樣子，見 [goose 管理 PostgreSQL migration 的實測紀錄](/programming/go/basic/10-database-access/hands-on/goose-migration-lab/)。Django 的 `makemigrations`、Alembic 的 branch label 與多資料庫設定不在這次的實測裡。

## 只給這次用的 PostgreSQL

這次在專案目錄底下用 `initdb` 建一個新的資料庫 cluster，用完整個目錄刪掉，不動系統上已有的 PostgreSQL。Homebrew 的 `postgresql@17` 是 keg-only，指令不在 `PATH` 上，下面用完整路徑：

```bash
brew install postgresql@17
P=/opt/homebrew/opt/postgresql@17/bin
mkdir alembic-lab && cd alembic-lab
$P/initdb -D "$PWD/pgdata" -U postgres --auth=trust -E UTF8 --locale=C
$P/pg_ctl -D "$PWD/pgdata" -o "-p 55432 -k '' -c listen_addresses=127.0.0.1" -l "$PWD/pg.log" start
$P/createdb -h 127.0.0.1 -p 55432 -U postgres shop
```

`mkdir alembic-lab` 的目錄名是這次取的，沒有比較其他值。`initdb` 的幾個參數：`-U postgres` 指定超級使用者的名稱（預設是執行 `initdb` 的作業系統使用者），這次固定成 `postgres`，後面的連線字串才通用；`-E UTF8 --locale=C` 指定編碼與排序規則，不給時取環境變數 `LC_*` 的值，這次用 `C` 讓排序不受這台機器的語系影響，沒有比較其他值；`--auth=trust` 讓本機連線不用密碼。`--auth` 不給時預設也是 trust，PostgreSQL 的 `initdb` 文件說這個預設是為了安裝方便，並提醒除非信任這台機器上的所有使用者，否則不要用；這次明寫出來，讓指令自己交代驗證方式。建正式的 cluster 時改成 `--auth=scram-sha-256` 並用 `--pwprompt` 設密碼。`pg_ctl` 的 `-l` 是 server log 的路徑，`-o` 把參數傳給 server：`-p 55432` 避開預設的 5432，讓系統上已有的 PostgreSQL 不受影響；`-k ''` 不建 Unix socket、`listen_addresses=127.0.0.1` 只聽本機的 TCP。這次不建 socket 的原因是第一次啟動時把 socket 指定建在工作目錄裡，而這台機器的工作目錄路徑太長，server 在 log 寫下 `Unix-domain socket path ... is too long (maximum 103 bytes)`，接著以 `FATAL:  could not create any Unix-domain sockets` 結束、沒有啟動；路徑短的讀者可以拿掉 `-k ''`，之後的連線字串照樣用 TCP。`shop` 是這次的資料庫名稱。

下面用 `psql` 查資料表時都寫成這個形式，`LANG=C` 讓 `psql` 印英文訊息，方便對照文中的輸出：

```bash
LANG=C $P/psql -h 127.0.0.1 -p 55432 -U postgres shop -c '<SQL>'
```

## 安裝套件與 alembic init

```bash
uv init --bare --python 3.13
uv add sqlalchemy==2.1.9 alembic==1.20.1 'psycopg[binary]==3.3.9'
uv run alembic init migrations
```

這次實際跑的是不帶版本的 `uv add sqlalchemy alembic 'psycopg[binary]'`，當天解析到的就是上面這三個版本；上面寫死版本，讓讀者重做時拿到同一版，文中的輸出與行為才對得上。

`uv init --bare` 只建 `pyproject.toml`；`--python 3.13` 寫進的是 `requires-python = ">=3.13"` 這個下限，是這次訂的，沒有比較其他值，uv 實際挑了這台機器上較新的 3.14.4 建虛擬環境（`uv run python -V` 查得到）。`psycopg[binary]` 是附帶編譯好的 libpq 的 psycopg 3，這台機器不必另外裝 PostgreSQL 的開發標頭。`alembic init migrations` 用預設的 `generic` 範本建出 `alembic.ini` 與 `migrations/`（`env.py`、`script.py.mako`、`versions/`）；目錄名 `migrations` 是這次取的，`alembic.ini` 的 `script_location` 會記下它。範本可以用 `-t` 換：`-t pyproject` 把大部分設定放進 `pyproject.toml` 的 `[tool.alembic]`，連線字串仍留在 `alembic.ini`；`-t async` 產生用非同步 engine 的 `env.py`，後面加鎖的那一段寫法要跟著改（照 Alembic 的〈Tutorial〉，這兩種範本這次都沒有實跑）。

要改兩個地方。`alembic.ini` 的連線字串，`postgresql+psycopg` 指定用 psycopg 3 的驅動（只寫 `postgresql://` 時 SQLAlchemy 找的是 psycopg2）：

```ini
sqlalchemy.url = postgresql+psycopg://postgres@127.0.0.1:55432/shop
```

`migrations/env.py` 裡的 `target_metadata = None` 換成 model 的 metadata，autogenerate 拿它跟資料庫比對；不換的話 autogenerate 沒有比對的對象，產生的 migration 是空的：

```python
from models import Base
target_metadata = Base.metadata
```

`env.py` 能 `import models`，是因為 Alembic 1.20 的 `alembic.ini` 預設有 `prepend_sys_path = .`，把執行指令的目錄加進 `sys.path`；在專案根目錄執行 `alembic` 時不必自己改 `sys.path`。

## 第一份 migration：建表

`models.py` 的第一版：

```python
from sqlalchemy import String, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Coupon(Base):
    __tablename__ = "coupons"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    rate: Mapped[int] = mapped_column(Integer)
```

```bash
uv run alembic revision --autogenerate -m "create coupons"
uv run alembic upgrade head
```

`revision --autogenerate` 印出 `Detected added table 'coupons'`，在 `migrations/versions/` 產生 `899a0e09dbf7_create_coupons.py`（前綴是隨機的 revision id，讀者那邊會不同）。`upgrade()` 裡是一個 `op.create_table`，`code` 的唯一約束寫成沒有名字的 `sa.UniqueConstraint('code')`，PostgreSQL 建表時替它取名 `coupons_code_key`。Alembic 的文件把沒有名字的約束列在 autogenerate 偵測不到的項目，之後改它時比對不出來；要讓約束的變更比對得到，在 `MetaData(naming_convention=...)` 定好命名規則，這次沒有設定。

`upgrade head` 印出 `Will assume transactional DDL.`，代表 Alembic 把這次的 migration 包在一個交易裡執行（PostgreSQL 的 DDL 可以放進交易）。套用之後放兩列資料，第二列的 `code` 有 27 個字元，後面縮窄型別時會用到：

```sql
INSERT INTO coupons (code, rate) VALUES ('SPRING10', 10), ('WELCOME-NEW-MEMBER-2026-NOV', 15);
```

`TABLE alembic_version` 只有一列 `899a0e09dbf7`：Alembic 在這張表記的是目前的版本，不是套用過的清單。

## 改名與縮窄：autogenerate 產生的 migration

把 model 的 `rate` 改名成 `discount`，`code` 的長度從 50 改成 20：

```python
    code: Mapped[str] = mapped_column(String(20), unique=True)
    discount: Mapped[int] = mapped_column(Integer)
```

```bash
uv run alembic revision --autogenerate -m "rename rate shorten code"
```

輸出裡另外有幾行 `setting up autogenerate plugin` 與一行 `Detected sequence named 'coupons_id_seq' ... assuming SERIAL and omitting`（說明它把主鍵的 sequence 當成 `SERIAL` 自動建的、不另外產生操作），下面只列 `Detected` 欄位變更的那幾行：

```text
INFO  [alembic.autogenerate.compare.tables] Detected added column 'coupons.discount'
INFO  [alembic.autogenerate.compare.types] Detected type change from VARCHAR(length=50) to String(length=20) on 'coupons.code'
INFO  [alembic.autogenerate.compare.tables] Detected removed column 'coupons.rate'
```

產生的 `upgrade()` 是新增 `discount`、改 `code` 的型別、刪除 `rate` 三個操作。改名在比對裡只看得到「少一欄、多一欄」，Alembic 文件把它列在偵測不到的項目（「detected as a column add/drop pair」）。型別的變更比對得到，因為 `compare_type` 從 Alembic 1.12 起預設開啟。

套用之前先看它會送出的 SQL。`--sql` 是離線模式，不連資料庫，只把 SQL 印出來；`899a0e09dbf7:head` 指定從哪一版印到哪一版，離線模式讀不到資料庫目前的版本，所以起點要自己給。`899a0e09dbf7` 換成讀者自己第一份 migration 的 revision id，`uv run alembic history` 列得出來；下文出現的其他 revision id（`06d4867969ab` 這類）同樣換成讀者那邊產生的值：

```bash
uv run alembic upgrade 899a0e09dbf7:head --sql
```

```sql
BEGIN;
-- Running upgrade 899a0e09dbf7 -> 06d4867969ab
ALTER TABLE coupons ADD COLUMN discount INTEGER NOT NULL;
ALTER TABLE coupons ALTER COLUMN code TYPE VARCHAR(20);
ALTER TABLE coupons DROP COLUMN rate;
UPDATE alembic_version SET version_num='06d4867969ab' WHERE alembic_version.version_num = '899a0e09dbf7';
COMMIT;
```

審查時要讀的就是這一段：`DROP COLUMN rate` 會連同資料刪掉，`ALTER COLUMN code TYPE VARCHAR(20)` 沒有 `USING`，遇到過長的值時 PostgreSQL 會拒絕。

這次刻意不改，原樣套用：

```bash
uv run alembic upgrade head
```

```text
psycopg.errors.NotNullViolation: column "discount" of relation "coupons" contains null values
```

`ADD COLUMN discount INTEGER NOT NULL` 沒有預設值，既有的兩列在新欄位上是 NULL，違反 `NOT NULL`。交易回滾，`alembic_version` 仍是 `899a0e09dbf7`，`coupons` 的欄位仍是 `id, code, rate`。

這次是 `NOT NULL` 剛好擋下來。新欄位可以為空時（model 寫成 `Mapped[int | None]`），同樣的新增加刪除會成功。在交易裡跑一次、最後 `ROLLBACK`，看結果：

```bash
LANG=C $P/psql -h 127.0.0.1 -p 55432 -U postgres shop \
  -c 'BEGIN' -c 'ALTER TABLE coupons ADD COLUMN discount INTEGER' \
  -c 'ALTER TABLE coupons DROP COLUMN rate' -c 'SELECT * FROM coupons' -c 'ROLLBACK'
```

```text
 id |            code             | discount
----+-----------------------------+----------
  1 | SPRING10                    |
  2 | WELCOME-NEW-MEMBER-2026-NOV |
```

兩個 `ALTER` 都成功，`rate` 的 10 與 15 跟著欄位消失，`discount` 全是 NULL，沒有任何錯誤或警告。最後的 `ROLLBACK` 把這兩個變更撤回，這一步只是為了看結果。

## 把產生的 migration 改寫成改名

打開 `06d4867969ab_rename_rate_shorten_code.py`，`upgrade()` 與 `downgrade()` 改成：

```python
def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("coupons", "rate", new_column_name="discount")
    op.alter_column("coupons", "code",
               existing_type=sa.VARCHAR(length=50),
               type_=sa.String(length=20),
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("coupons", "code",
               existing_type=sa.String(length=20),
               type_=sa.VARCHAR(length=50),
               existing_nullable=False)
    op.alter_column("coupons", "discount", new_column_name="rate")
```

`alter_column` 的 `new_column_name` 產生 `ALTER TABLE coupons RENAME rate TO discount`，資料留在原本的欄位裡。`existing_type` 與 `existing_nullable` 是 autogenerate 帶進來的、這一欄目前的型別與可空性：Alembic 的 `alter_column` 文件寫明，有些資料庫（MySQL）改欄位時要整個重述欄位定義，要靠這兩個參數補齊；PostgreSQL 的 `ALTER COLUMN TYPE` 用不到它們，這次保留產生出來的寫法，沒有比較拿掉之後的結果。`downgrade()` 的順序跟 `upgrade()` 相反，先把型別放寬再改回原名。`--sql` 印出的 SQL 換成 `RENAME` 與 `ALTER COLUMN code TYPE VARCHAR(20)` 兩句。套用：

```bash
uv run alembic upgrade head
```

```text
sqlalchemy.exc.DataError: (psycopg.errors.StringDataRightTruncation) value too long for type character varying(20)
```

第二列的 `code` 有 27 個字元。這一句失敗時，同一個交易裡已經做完的 `RENAME` 一起隨交易回滾：`alembic_version` 仍是 `899a0e09dbf7`，欄位仍是 `id, code, rate`。

同一個型別變更加上明確的轉型時，結果不同。在交易裡試一次、最後 `ROLLBACK`：

```bash
LANG=C $P/psql -h 127.0.0.1 -p 55432 -U postgres shop -c 'BEGIN' \
  -c 'ALTER TABLE coupons ALTER COLUMN code TYPE VARCHAR(20) USING code::varchar(20)' \
  -c 'SELECT code FROM coupons' -c 'ROLLBACK'
```

```text
         code
----------------------
 SPRING10
 WELCOME-NEW-MEMBER-2
```

`USING code::varchar(20)` 是寫在語句裡、指定要轉成哪個型別的轉換（explicit cast），PostgreSQL 用 explicit cast 轉成較短的 `varchar` 時把超出的字元截掉而不報錯；GORM 的 `AutoMigrate` 送出的就是這種寫法（見 [10.5 GORM 的〈AutoMigrate 在正式環境的限制〉](/programming/go/basic/10-database-access/gorm/)）。Alembic 產生的語句沒有 `USING`，PostgreSQL 用的是會檢查長度的轉型，所以拒絕。

過長的那幾列要變成什麼是業務的決定，這次把它改成較短的代碼，再套用：

```bash
LANG=C $P/psql -h 127.0.0.1 -p 55432 -U postgres shop -c "UPDATE coupons SET code = 'WELCOME-NOV26' WHERE id = 2"
uv run alembic upgrade head
```

這次印出 `Running upgrade 899a0e09dbf7 -> 06d4867969ab`，`TABLE coupons` 是 `1 | SPRING10 | 10` 與 `2 | WELCOME-NOV26 | 15`：`rate` 的值留在改名後的 `discount` 裡。

一句 `RENAME` 加原地改型別的寫法，前提是同一時間只有一版程式在讀寫這張表（單一實例、或部署時先停掉舊版）。滾動部署時舊版實例還在用 `rate`，改名那一刻起它的查詢就失敗；這時候要照 expand-contract 拆成幾份 migration、隔著程式部署分次套用，拆法見 [1.20 的〈比對 model 與資料庫推不出的三件事〉](/backend/01-database/schema-change-management/) 的變更順序那一段與 [1.6 的〈Expand-Contract 模式〉](/backend/01-database/database-migration-playbook/)。正式環境上，資料的修正也寫成一份 migration（或寫在這份 migration 的開頭），讓每個環境照同一個順序做；這次直接下 `UPDATE` 是為了把資料修正與型別變更分開觀察。

## alembic check：model 與資料庫的差異

`alembic check` 用 autogenerate 的同一套比對，比較 model 與資料庫，有差異時以非零的 exit code 結束，不產生檔案。它要求資料庫已經套用到最新版，否則直接回 `Target database is not up to date.`。

在資料庫上手動建一個 model 裡沒有的 index，再跑一次：

```bash
LANG=C $P/psql -h 127.0.0.1 -p 55432 -U postgres shop -c 'CREATE INDEX coupons_discount_idx ON coupons (discount)'
uv run alembic check; echo "exit=$?"
```

```text
INFO  [alembic.autogenerate.compare.constraints] Detected removed index 'coupons_discount_idx' on 'coupons'
FAILED: New upgrade operations detected: [('remove_index', Index('coupons_discount_idx', ...))]
exit=255
```

Alembic 以 model 為準，所以資料庫多出來的 index 被報成「要刪除」；這時候跑 `revision --autogenerate`，產生的 migration 會有 `op.drop_index`。手動在正式環境建過的 index 要補進 model（或補一份 migration），否則下一次產生的 migration 會把它刪掉。確認完把 index 刪掉：`DROP INDEX coupons_discount_idx`。

model 新增一個欄位（`note: Mapped[str | None] = mapped_column(String(200))`）而沒有產生 migration 時，`alembic check` 同樣以 `Detected added column 'coupons.note'` 失敗。這個 `note` 欄位留在 model 裡，下一節的第一份 migration 就是替它產生的。放在 CI 裡，它擋得下「model 改了、忘了產生 migration」與「資料庫被手動改過」兩種情形，前提是 CI 連得到一個套用到最新版的資料庫。

`alembic check` 不比對欄位的預設值：model 的 `discount` 加上 `server_default="0"` 時，它回 `No new upgrade operations detected.`。欄位的預設值由 `compare_server_default` 控制，預設關閉；Alembic 的〈Autogenerate〉文件只寫「The feature is off by default」，沒有說明這個預設值服務的情境。要比對的話在 `env.py` 的 `context.configure(...)` 加上 `compare_server_default=True`，這次沒有開啟，也沒有比較開啟之後的結果。

## 兩個分支各自新增 migration：兩個 head 與 alembic merge

Alembic 的每一份 migration 用 `down_revision` 指向前一份。兩位開發者從同一版各自產生 migration，兩份的 `down_revision` 相同，合併之後就有兩個 head。這次在同一個工作目錄模擬：先照常產生加 `note` 欄位的 migration，再從前一版另外產生一份加 `expires_at` 的：

```bash
uv run alembic revision --autogenerate -m "add note"
uv run alembic upgrade head
uv run alembic revision -m "add expires_at" --head 06d4867969ab --splice
```

`--head 06d4867969ab` 指定新 migration 接在哪一版之後；從不是 head 的版本建新的 migration 時，Alembic 要求加 `--splice`，否則回 `FAILED: Revision 06d4867969ab is not a head revision; please specify --splice to create a new branch from this revision`。實際的兩個 git 分支合併時不需要這個參數，兩份檔案各自在自己的分支上產生，合併之後自然有兩個 head。`revision` 沒有 `--autogenerate` 時產生空的 `upgrade()`，這次在裡面寫 `op.add_column("coupons", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))`，`downgrade()` 寫對應的 `op.drop_column`。

```bash
uv run alembic heads
uv run alembic upgrade head
```

```text
2243a713ab81 (head)
b09ee421ee9c (head)
FAILED: Multiple head revisions are present for given argument 'head'; please specify a specific target revision, '<branchname>@head' to narrow to a specific head, or 'heads' for all heads
```

有兩個 head 時，`head` 這個目標對不到唯一的一版，`upgrade` 以錯誤結束。錯誤訊息提到的 `upgrade heads` 會兩支都套用（照錯誤訊息與 Alembic 文件，這次沒有實跑），但之後新產生的 migration 仍要指定接在哪一個 head 之後，所以這次把兩支接起來：

```bash
uv run alembic merge -m "merge note and expires_at" heads
uv run alembic upgrade head
```

```text
INFO  [alembic.runtime.migration] Running upgrade 06d4867969ab -> b09ee421ee9c, add expires_at
INFO  [alembic.runtime.migration] Running upgrade 2243a713ab81, b09ee421ee9c -> 57df8d65ef0f, merge note and expires_at
```

`merge` 產生的 `57df8d65ef0f` 的 `down_revision` 是兩個 head 的 tuple，`upgrade()` 是空的，作用只是把兩支接成一支。兩份 migration 改到同一個物件時，哪一支先跑會影響結果，合併的人要在 merge 之前確認兩份的內容；merge 本身不檢查衝突。

## 兩個程序同時套用與 env.py 的建議鎖

多個應用程式實例在啟動時各自跑 `alembic upgrade head` 時，Alembic 本身沒有鎖。這次先用 `uv run alembic downgrade base` 把資料庫降回沒有套用任何 migration 的狀態，再在第一份 migration 的 `upgrade()` 開頭暫時加一行 `op.execute("SELECT pg_sleep(3)")`，讓兩個程序的套用時間重疊，然後同時啟動兩個：

```bash
uv run alembic upgrade head > a1.log 2>&1 &
uv run alembic upgrade head > a2.log 2>&1
wait
```

兩個程序哪一個先建表，每次執行不一定；這次是 `a1.log` 依序套用了五份 migration、`a2.log` 在建表時失敗，另一次重做時兩者相反，結果的形態相同。失敗的那一份：

```text
INFO  [alembic.runtime.migration] Running upgrade  -> 899a0e09dbf7, create coupons
psycopg.errors.UniqueViolation: duplicate key value violates unique constraint "pg_class_relname_nsp_index"
DETAIL:  Key (relname, relnamespace)=(coupons_id_seq, 2200) already exists.
```

兩個程序都讀到「目前沒有版本」，都去建 `coupons`；PostgreSQL 的系統目錄 `pg_class` 對同一個 schema 裡的關聯名稱（表、sequence、index 都算）有唯一約束，第二個程序的 `CREATE TABLE` 等第一個提交之後撞上這個約束。DETAIL 指出先撞上的是 `coupons_id_seq`：`id` 是整數主鍵，SQLAlchemy 在 PostgreSQL 上把它建成 `SERIAL`，建表時先建這個 sequence，所以撞名發生在 sequence，而不是表名本身。`2200` 是 `public` 這個 schema 的 OID。它的交易回滾，資料庫裡沒有留下建了一半的表，結果是那個程序以錯誤結束；在應用程式啟動時套用 migration 的話，就是那個實例啟動失敗。

在 `env.py` 的 `run_migrations_online()` 裡，套用之前先取一個交易層級的[建議鎖（advisory lock）](/backend/knowledge-cards/advisory-lock/)：

```python
from sqlalchemy import pool, text

# ...

        with context.begin_transaction():
            # 同一時間只讓一個程序套用 migration；交易結束時自動釋放
            connection.execute(text("SELECT pg_advisory_xact_lock(726, 1)"))
            context.run_migrations()
```

`pg_advisory_xact_lock` 取得的鎖在交易提交或回滾時自動釋放。鎖的鍵用兩個整數，`726` 是這次取的應用程式代號、`1` 是「套用 migration」這個功能的代號；照 Advisory Lock 卡的建議，自訂的鍵用兩個 int 的形式，跟 migration 工具這類套件常用的單一 bigint 鍵分開（goose、golang-migrate 的鎖用的是單一鍵），同一個應用程式的排程要用建議鎖時換另一個功能代號。PostgreSQL 另外兩個寫法的結果不同：`pg_try_advisory_xact_lock` 拿不到鎖時立刻回 false、不等待，程序要自己決定重試或結束；session 層級的 `pg_advisory_lock` 不隨交易結束釋放，要另外呼叫 `pg_advisory_unlock`（照 PostgreSQL 的〈Advisory Lock Functions〉文件，這兩種這次沒有實跑）。這次要的是「等前一個做完」，所以用會等待、隨交易釋放的 `pg_advisory_xact_lock`。拿不到鎖的程序在這一行等，等到前一個提交之後，`run_migrations()` 才讀 `alembic_version`，讀到的已經是最新版。鎖要取在 `begin_transaction()` 裡面：Alembic 預設把整批 migration 放在同一個交易，鎖跟著這個交易一直持有到全部套用完。`env.py` 裡 `context.configure` 設了 `transaction_per_migration=True` 時，每一份 migration 各自提交，這個寫法的鎖只持有到第一份結束，這次沒有實測那種設定。

再把資料庫降回沒有套用任何 migration 的狀態，一樣同時啟動兩個：

```bash
uv run alembic downgrade base
uv run alembic upgrade head > b1.log 2>&1 &
uv run alembic upgrade head > b2.log 2>&1
wait
```

```text
== b1.log（只列出 Running 那幾行）
INFO  [alembic.runtime.migration] Running upgrade  -> 899a0e09dbf7, create coupons
INFO  [alembic.runtime.migration] Running upgrade 899a0e09dbf7 -> 06d4867969ab, rename rate shorten code
INFO  [alembic.runtime.migration] Running upgrade 06d4867969ab -> b09ee421ee9c, add expires_at
INFO  [alembic.runtime.migration] Running upgrade 06d4867969ab -> 2243a713ab81, add note
INFO  [alembic.runtime.migration] Running upgrade 2243a713ab81, b09ee421ee9c -> 57df8d65ef0f, merge note and expires_at
== b2.log（全文）
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

第二個程序等第一個做完，讀到最新版，什麼都沒套用就正常結束。上面的輸出是鎖鍵用單一整數 `7261001` 的那一次；改成兩個整數 `(726, 1)` 之後重跑一次，結果相同（第一個程序五行 `Running upgrade`，第二個只有那兩行 `INFO`）。實測完把 `pg_sleep(3)` 那一行拿掉。

這個鎖只保護在 `env.py` 裡走 `run_migrations_online()` 的套用；`--sql` 離線模式印出的 SQL 由人另外執行時不經過它。把 migration 放在部署流程裡只跑一次的步驟（而不是每個實例啟動時跑），是另一種避免並行的方式，兩者的取捨在 [1.20 Schema 變更由誰寫出、何時套用](/backend/01-database/schema-change-management/) 的〈套用的時機：應用程式啟動時與獨立的部署步驟〉。

## 清理

```bash
$P/pg_ctl -D "$PWD/pgdata" stop
```

停掉 server 之後，整個 `alembic-lab/` 目錄（含 `pgdata/`）都是這次建的，確認路徑之後用 `rm -r` 加完整路徑刪掉。Homebrew 的 `postgresql@17` 留著不影響其他服務；不再需要時用 `brew uninstall postgresql@17` 移除。uv 下載的套件留在它的全域快取（`uv cache dir` 印出的目錄），其他專案也會用到；要清時用 `uv cache clean`，之後的專案安裝套件時要重新下載。
