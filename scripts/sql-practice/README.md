# SQL 練習題庫的三領域資料庫底座、基準快照與驗證題庫

本目錄存放 SQL 漸進式練習網站的三層資料底座（語意反例 `seed.sql`、中規模壓測 `seed_scale.sql`、基準快照 `benchmarks/`）、結構化選擇題 JSON 題庫（`questions/`），以及全自動化驗證腳本。完整設計規格見 [SQL 漸進式練習網站規格與題庫設計](../../content/backend/01-database/sql/practice/_index.md)。

## 目錄結構

| 路徑                       | 用途                      | 說明                                                                                                                                         |
| -------------------------- | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `domains/bookstore/`       | 領域甲：紙頁書店（20 表） | `schema.sql`（含 RBAC、軟刪除部分唯一索引、PII 分離、唯附寫稽核與 2 檢視表）、`seed.sql`、`seed_scale.sql`、`security_pg.sql`                |
| `domains/cloud-academy/`   | 領域乙：雲課堂（18 表）   | `schema.sql`（含企業多租戶組織、憑證／Session 失效、PII 分離、唯附寫稽核與 2 檢視表）、`seed.sql`、`seed_scale.sql`、`security_pg.sql`       |
| `domains/swift-logistics/` | 領域丙：捷配物流（17 表） | `schema.sql`（含商家帳號、API Key 雜湊撤銷、子表租戶鍵、收件人 PII、唯附寫稽核與 2 檢視表）、`seed.sql`、`seed_scale.sql`、`security_pg.sql` |
| `benchmarks/`              | 基準快照 JSON             | `sqlite-scale-snapshots.json`（實跑生成）、`postgres-and-concurrency-reference.json`（PG／多連線／分區參考快照）                             |
| `questions/`               | 結構化題庫 JSON           | `manifest.json` 與八階段（含資安與權限）＋跨概念／資安複合陷阱共 9 份題庫（首批 53 題、涵蓋 3 領域與 CRUD 多表路徑輪替）                     |
| `verify_domains.py`        | 資料庫底座驗證            | 載入三套基礎與壓測資料庫，驗外鍵、完整性、語意／資安反例、Trigger 防竄改與執行計畫分岔                                                       |
| `generate_benchmarks.py`   | 實測基準快照產生器        | 在三套壓測資料庫實跑關鍵查詢，輸出 `EXPLAIN QUERY PLAN` 與中位數耗時倍率                                                                     |
| `verify_questions.py`      | 題庫自動化驗收            | 驗證 JSON 欄位、站內文章連結、基準參照，並在獨立記憶體 SQLite 實跑全部可執行選項與斷言                                                       |

## 一鍵驗證指令（純 Python 3 標準函式庫，無外部套件）

```bash
# 1. 驗證三套領域基礎反例與中規模壓測資料
python3 scripts/sql-practice/verify_domains.py

# 2. 重新實跑並更新 SQLite 規模基準快照 JSON
python3 scripts/sql-practice/generate_benchmarks.py

# 3. 驗證全部題庫 JSON 結構、站內連結與可執行 SQLite 選項
python3 scripts/sql-practice/verify_questions.py
```

`schema.sql`、`seed.sql` 與 `seed_scale.sql` 皆為數 KB 純文字 SQLite SQL，零二進位膨脹，可直接推上 GitHub 並供未來靜態網站以 SQLite WASM（`sql.js`）在 Web Worker 端按需載入。
