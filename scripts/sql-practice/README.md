# SQL 練習題庫的三領域資料庫底座

本目錄存放 SQL 漸進式練習網站的三套真實商業領域 SQLite Schema 與基準測試資料（含所有刻意埋設的邊界反例列），以及自動化驗證腳本。設計規格見 [SQL 漸進式練習網站規格與題庫設計](../../content/backend/01-database/sql/practice/_index.md)。

## 目錄結構

| 路徑                       | 商業領域                               | 涵蓋資料表數 | 主要關聯與邊界設計                                                                                     |
| -------------------------- | -------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------ |
| `domains/bookstore/`       | 領域甲：紙頁書店（電商書城與門市）     | 13           | 顧客／分類樹／書籍／訂單／明細／評價／優惠券／用券／每日營收快照／匯出佇列／排班／冷資料詳情／瀏覽事件 |
| `domains/cloud-academy/`   | 領域乙：雲課堂（SaaS 訂閱制教學平台）  | 10           | 會員／先修課階層／訂閱／帳單／單元進度／Webhook 佇列／冷資料課綱／標籤多對多／證書                     |
| `domains/swift-logistics/` | 領域丙：捷配物流（B2B 倉儲與配送調度） | 9            | 轉運倉階層／商家／運單／掃描事件流／司機排班／派工佇列／包裹明細／電子託運單冷報文／月結對帳單         |
| `verify_domains.py`        | 自動化底座驗證腳本                     | —            | 載入三套 Schema 與 Seed、檢查外鍵與完整性，並實跑代表性邊界反例 SQL 確認差異如預期現形                 |

## 使用方式

執行全部三套領域的建庫、外鍵完整性與邊界反例驗證（純 Python 3 標準函式庫，無外部相依套件）：

```bash
python3 scripts/sql-practice/verify_domains.py
```

若要使用 `sqlite3` 命令列互動查詢任一領域（例如載入紙頁書店到記憶體或暫存檔）：

```bash
sqlite3 :memory: \
  -cmd ".read scripts/sql-practice/domains/bookstore/schema.sql" \
  -cmd ".read scripts/sql-practice/domains/bookstore/seed.sql" \
  "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name;"
```

`schema.sql` 與 `seed.sql` 皆採標準 SQLite SQL，後續可直接由靜態網站透過 SQLite WASM（`sql.js`）在瀏覽器端原樣載入。
