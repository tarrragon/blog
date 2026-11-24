# SQL 練習題庫的三領域資料庫底座、基準快照與驗證題庫

本目錄存放 SQL 漸進式練習網站的三層資料底座（語意反例 `seed.sql`、中規模壓測 `seed_scale.sql`、基準快照 `benchmarks/`）、結構化選擇題 JSON 題庫（`questions/`），以及全自動化驗證腳本。完整設計規格見 [SQL 漸進式練習網站規格與題庫設計](../../content/backend/01-database/sql/practice/_index.md)。

## 目錄結構

| 路徑                       | 用途                      | 說明                                                                                                                   |
| -------------------------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `domains/bookstore/`       | 領域甲：紙頁書店（20 表） | RBAC、軟刪除部分唯一索引、可抹除的顧客個資、匯出任務終態、唯附寫稽核與 2 檢視表                                        |
| `domains/cloud-academy/`   | 領域乙：雲課堂（20 表）   | 企業多租戶組織、RBAC（含 permissions）、憑證／Session 失效、可抹除的學員個資、唯附寫稽核與 2 檢視表                    |
| `domains/swift-logistics/` | 領域丙：捷配物流（19 表） | 商家帳號、API Key 雜湊撤銷、子表 NOT NULL 租戶鍵與複合外鍵、平台員工 RBAC、收件人 PII、唯附寫稽核與 2 檢視表           |
| `benchmarks/`              | 基準快照 JSON             | `sqlite-scale-snapshots.json`（實跑生成）、`postgres-and-concurrency-reference.json`（PG／多連線／分區參考快照）       |
| `questions/`               | 結構化題庫 JSON           | `manifest.json` 與八階段（含資安與權限）＋跨概念／資安複合陷阱共 9 份題庫（首批 53 題）                                |
| `verify_domains.py`        | SQLite 資料庫底座驗證     | 外鍵、完整性、語意／資安反例、約束回歸（STRICT、時間格式、狀態綁定、複合外鍵）、壓測層一致性契約與執行計畫分岔         |
| `verify_questions.py`      | 題庫自動化驗收            | JSON 欄位、`population` 母體宣告、站內文章連結、基準參照，並在獨立記憶體 SQLite 實跑全部可執行選項與斷言               |
| `verify_pg.py`             | PostgreSQL 驗證           | 在拋棄式叢集實跑 `schema_pg.sql` + `seed.sql` + `security_pg.sql`，以各角色身分檢查 RLS、GRANT、唯附寫稽核與跨引擎差異 |
| `generate_benchmarks.py`   | 實測基準快照產生器        | 在三套壓測資料庫實跑關鍵查詢，輸出 `EXPLAIN QUERY PLAN`、單次耗時（每樣本重複執行後平均）、倍率與絕對差                |
| `wasm_load_bench.mjs`      | sql.js 載入量測           | 在 sql.js 灌入三領域 × 倍數 1、3、10 的 `seed_scale.sql`，印耗時、資料庫大小與外鍵違規數（Node，sql.js 裝在 repo 外）  |

每個領域目錄有五份 SQL：`schema.sql`（SQLite，供網站與題庫實跑）、`schema_pg.sql`（同一套模型的 PostgreSQL 版 DDL）、`seed.sql`（兩引擎共用，PostgreSQL 執行時略過 `PRAGMA` 行）、`seed_scale.sql`（只供 SQLite）、`security_pg.sql`（PostgreSQL 角色、GRANT 與 RLS，需先執行 `schema_pg.sql`）。

## 驗證指令（純 Python 3 標準函式庫，無外部套件）

```bash
# 1. 驗證三套領域基礎反例與中規模壓測資料（SQLite）
python3 scripts/sql-practice/verify_domains.py

# 2. 驗證全部題庫 JSON 結構、母體宣告、站內連結與可執行 SQLite 選項
python3 scripts/sql-practice/verify_questions.py

# 3. 在暫存目錄建立拋棄式 PostgreSQL 叢集驗證角色與 RLS（需要 PATH 上有 initdb、pg_ctl、psql）
python3 scripts/sql-practice/verify_pg.py

# 4. 重新實跑並更新 SQLite 規模基準快照 JSON
python3 scripts/sql-practice/generate_benchmarks.py
```

`verify_pg.py` 在 PostgreSQL 17.12（本機拋棄式叢集）與 18.7（`postgres:18` 容器）都實跑通過。改連容器時，先啟動一個不帶資料的容器，再把連線參數交給腳本：

```bash
docker run -d --name sqlpractice-pg18 -e POSTGRES_HOST_AUTH_METHOD=trust -p 127.0.0.1:55432:5432 postgres:18
python3 scripts/sql-practice/verify_pg.py --dsn-host 127.0.0.1 --dsn-port 55432 --dsn-user postgres
docker rm -fv sqlpractice-pg18
```

`POSTGRES_HOST_AUTH_METHOD=trust` 讓任何連線免密碼登入，只用在綁定 `127.0.0.1`、驗證完就刪掉的容器；`55432` 是避開本機 5432 的任意空埠，換成別的埠時兩處一起改。腳本會在叢集裡建立三個領域的資料庫與它們的角色，角色是叢集層級的物件，所以每次驗證用一個新的容器。`docker rm` 的 `-v` 連同容器的匿名資料 volume 一起刪，少了它 volume 會留在本機。

不跑驗證、只想開一個灌好 seed 的資料庫做實驗時（SQLite 檔或 PostgreSQL 容器），指令、工具版本與本機 Docker 物件的名冊在 [本機實驗環境](../../docs/local-environment.md)。

## 母體約定（`population`）

`customers`、`users`、`merchants`、`staff_accounts`、`merchant_users` 同時存放有效列與已註銷、停權或離職的列。題目的 `tablePath` 碰到這些表時，必須在 JSON 宣告 `population`：

| 值               | 意思                               | `verify_questions.py` 的檢查                        |
| ---------------- | ---------------------------------- | --------------------------------------------------- |
| `all-records`    | 母體含任何狀態的列（對帳、稽核類） | 需求文字寫明母體，例如「不論帳號狀態」              |
| `active-only`    | 只算目前有效的列                   | 推薦的 SELECT 選項同時過濾 `status` 與 `deleted_at` |
| `specific-ids`   | 需求以明確 ID 指定對象             | 無                                                  |
| `not-applicable` | 概念題或設計題，不產生查詢結果集   | 無                                                  |

## 瀏覽器端載入（SQLite WASM）

- **外鍵要在交易外開啟**：sql.js 新建的資料庫 `PRAGMA foreign_keys` 預設為 0；在 `BEGIN ... COMMIT` 裡執行 `PRAGMA foreign_keys = ON` 不會生效（實測仍為 0）。前端若把灌資料包進交易加速，須在 `BEGIN` 之前先開外鍵。
- **規模參數**：在執行 `seed_scale.sql` 前建立 `CREATE TEMP TABLE scale_params (mult INTEGER NOT NULL)` 並寫入倍數（1 到 10），倍數只改變列數，時間跨度固定。
- **實測載入成本**（sql.js 1.13.0，內建 SQLite 3.49.1；Node 24、Apple Silicon，非手機實測；`wasm_load_bench.mjs` 產生，重跑方式見[本機實驗環境](../../docs/local-environment.md)〈sql.js 載入量測〉）：

| 倍數 | bookstore         | cloud-academy    | swift-logistics   |
| ---- | ----------------- | ---------------- | ----------------- |
| 1    | 0.40 秒、13.9 MB  | 0.24 秒、7.7 MB  | 0.58 秒、25.8 MB  |
| 3    | 1.18 秒、41.4 MB  | 0.73 秒、22.9 MB | 1.86 秒、77.4 MB  |
| 10   | 4.12 秒、137.7 MB | 2.54 秒、76.1 MB | 6.50 秒、258.6 MB |

  灌資料一律放在 Web Worker；手機建議倍數不超過 3，並只載入目前題目的領域。
- **版本對齊**：驗證腳本用 Python 內建的 SQLite（目前 3.53.0），sql.js 1.13.0 內建 3.49.1；`EXPLAIN QUERY PLAN` 的字串與執行計畫可能隨版本不同。前端鎖定 WASM 版本後，應在同一個 WASM build 上重跑題庫斷言。
- **時間差多半感覺不到**：`benchmarks/sqlite-scale-snapshots.json` 的變體單次差距多在幾毫秒以內（自連接那一題除外），網站應以執行計畫與倍率為主、時間為輔。

`schema.sql`、`seed.sql` 與 `seed_scale.sql` 皆為數 KB 純文字 SQL，零二進位膨脹，可直接推上 GitHub。
