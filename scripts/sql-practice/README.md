# SQL 練習題庫的三領域資料庫底座、基準快照與驗證題庫

本目錄存放 SQL 漸進式練習網站的三層資料底座（語意反例 `seed.sql`、中規模壓測 `seed_scale.sql`、基準快照 `benchmarks/`）、結構化選擇題 JSON 題庫（`questions/`），以及全自動化驗證腳本。完整設計規格見 [SQL 漸進式練習網站規格與題庫設計](../../content/backend/01-database/sql/practice/_index.md)。

## 目錄結構

| 路徑                       | 用途                      | 說明                                                                                                                           |
| -------------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `domains/bookstore/`       | 領域甲：紙頁書店（13 表） | `schema.sql`、`seed.sql`（手寫反例 `1..9999`）、`seed_scale.sql`（決定性造數 `100001+`，含 5 萬訂單與 2,000 筆熱點重複 email） |
| `domains/cloud-academy/`   | 領域乙：雲課堂（10 表）   | `schema.sql`、`seed.sql`、`seed_scale.sql`（含 5 萬帳單與 1,500 筆 Webhook 重送風暴）                                          |
| `domains/swift-logistics/` | 領域丙：捷配物流（9 表）  | `schema.sql`、`seed.sql`、`seed_scale.sql`（含 5 萬運單 35% 客戶傾斜與 3 萬筆高比例 `completed` 任務）                         |
| `benchmarks/`              | 基準快照 JSON             | `sqlite-scale-snapshots.json`（實跑生成）、`postgres-and-concurrency-reference.json`（PG／多連線／分區參考快照）               |
| `questions/`               | 結構化題庫 JSON           | `manifest.json` 與七階段＋跨概念複合陷阱共 8 份題庫（首批 41 題、涵蓋 3 領域與 CRUD 多表路徑輪替）                             |
| `verify_domains.py`        | 資料庫底座驗證            | 載入三套基礎與壓測資料庫，驗外鍵、完整性、反例與執行計畫分岔                                                                   |
| `generate_benchmarks.py`   | 實測基準快照產生器        | 在三套壓測資料庫實跑關鍵查詢，輸出 `EXPLAIN QUERY PLAN` 與中位數耗時倍率                                                       |
| `verify_questions.py`      | 題庫自動化驗收            | 驗證 JSON 欄位、站內文章連結、基準參照，並在獨立記憶體 SQLite 實跑全部可執行選項與斷言                                         |

## 一鍵驗證指令（純 Python 3 標準函式庫，無外部套件）

```bash
# 1. 驗證三套領域基礎反例與中規模壓測資料
python3 scripts/sql-practice/verify_domains.py

# 2. 重新實跑並更新 SQLite 規模基準快照 JSON
python3 scripts/sql-practice/generate_benchmarks.py

# 3. 驗證全部題庫 JSON 結構、站內連結與 118 個 SQLite 實跑選項
python3 scripts/sql-practice/verify_questions.py
```

`schema.sql`、`seed.sql` 與 `seed_scale.sql` 皆為數 KB 純文字 SQLite SQL，零二進位膨脹，可直接推上 GitHub 並供未來靜態網站以 SQLite WASM（`sql.js`）在 Web Worker 端按需載入。
