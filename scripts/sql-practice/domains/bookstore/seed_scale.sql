-- 領域甲（bookstore）：中規模決定性壓測資料（疊加於 seed.sql 之上）
-- ID 區段契約：手寫邊界反例佔 1..9999，本檔合成列一律自 100001 起跳，絕不撞號。
--
-- 規模參數：倍數存在暫存表 scale_params.mult（預設 1，上限 10）。前端要放大時，在執行本檔前先執行
--   CREATE TEMP TABLE scale_params (mult INTEGER NOT NULL); INSERT INTO scale_params VALUES (3);
-- 倍數只改變列數（密度），時間跨度固定，放大後的資料仍落在同一段營運期間內。
-- 記憶體：倍數 1 時本領域的記憶體資料庫約 14 MB，資料庫大小約隨倍數線性成長（實測見 README）；手機建議不超過 3。
--
-- 時間線契約（每一列都滿足，verify_domains.py 會檢查）：
-- - 合成顧客在 2024 年註冊，合成訂單落在 2025-01-01 至 2026-03-31，因此每筆訂單都晚於下單顧客的註冊時間。
-- - 每筆訂單有 1 至 3 筆明細，orders.total_amount 等於明細 quantity * unit_price 的總和。
-- - 每位合成顧客都有 customer_pii 列；已抹除顧客的姓名、信箱與 PII 欄位皆為 NULL。
--
-- 設計重點（倍數 1 時）：
-- 1. customers 新增 7,000 列，其中 2,000 列共用熱點重複信箱 hot@bookstore.tw（驗證 SQL.17 自連接平方退化）；熱點以外每 50 列 1 位已抹除、每 97 列 1 位停權
-- 2. orders 新增 50,000 列，30% 集中在顧客 100001（資料傾斜）；order_items 約 85,000 列；reviews 12,500 列
-- 3. export_jobs 新增 20,005 列：done 為主、5 列 queued（驗證部分索引 idx_export_jobs_queued），請求者與門市範圍皆有值，另有 cancelled / denied 終態
-- 4. book_view_events 新增 30,000 列，40% 集中在熱門書 201（驗證高頻計數與熱點傾斜）

PRAGMA foreign_keys = ON;

CREATE TEMP TABLE IF NOT EXISTS scale_params (mult INTEGER NOT NULL);
INSERT INTO scale_params SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM scale_params);
CREATE TEMP TABLE scale_n AS
SELECT
  MIN(MAX(mult, 1), 10) * 7000  AS n_customers,
  MIN(MAX(mult, 1), 10) * 2000  AS n_hot,
  MIN(MAX(mult, 1), 10) * 50000 AS n_orders,
  MIN(MAX(mult, 1), 10) * 20000 AS n_jobs,
  MIN(MAX(mult, 1), 10) * 30000 AS n_views
FROM scale_params LIMIT 1;

-- 顧客：2024-01-01 起平均分布在 2024 年內（31,536,000 秒）
WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < (SELECT n_customers FROM scale_n)
)
INSERT INTO customers (customer_id, name, email, city, status, deleted_at, created_at)
SELECT
  100000 + i,
  CASE WHEN i % 50 = 0 AND i > (SELECT n_hot FROM scale_n) THEN NULL ELSE '會員_' || i END,
  CASE
    WHEN i <= (SELECT n_hot FROM scale_n) THEN 'hot@bookstore.tw'
    WHEN i % 50 = 0 THEN NULL
    ELSE 'user_' || i || '@bookstore.tw'
  END,
  CASE i % 5 WHEN 0 THEN 'Taipei' WHEN 1 THEN 'Taichung' WHEN 2 THEN 'Kaohsiung' WHEN 3 THEN 'Tainan' ELSE NULL END,
  CASE WHEN i % 50 = 0 AND i > (SELECT n_hot FROM scale_n) THEN 'erased' WHEN i % 97 = 0 THEN 'suspended' ELSE 'active' END,
  CASE WHEN i % 50 = 0 AND i > (SELECT n_hot FROM scale_n) THEN '2026-02-01 00:00:00' END,
  datetime('2024-01-01 00:00:00', '+' || ((i * 31536000) / (SELECT n_customers FROM scale_n)) || ' seconds')
FROM seq;

INSERT INTO customer_pii (customer_id, phone_e164, shipping_address, tax_id, updated_at, erased_at)
SELECT
  customer_id,
  CASE WHEN status = 'erased' THEN NULL ELSE '+8869' || printf('%08d', customer_id - 100000) END,
  CASE WHEN status = 'erased' THEN NULL ELSE '合成地址 ' || (customer_id - 100000) || ' 號' END,
  NULL,
  COALESCE(deleted_at, created_at),
  deleted_at
FROM customers
WHERE customer_id > 100000;

-- 訂單：2025-01-01 起平均分布到 2026-03-31 23:59:59（39,311,999 秒）
-- 明細規則：第 1 行一律存在，第 2 行在 i 為偶數時存在，第 3 行在 i 為 5 的倍數時存在；
-- 書號 201 + ((i * 7 + line) % 9)，數量 1 + ((i + line) % 2)，單價取書籍現價
CREATE TEMP TABLE scale_order_lines AS
WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < (SELECT n_orders FROM scale_n)
),
lines(line) AS (VALUES (1), (2), (3))
SELECT
  seq.i,
  lines.line,
  201 + ((seq.i * 7 + lines.line) % 9) AS book_id,
  1 + ((seq.i + lines.line) % 2) AS quantity
FROM seq
JOIN lines
  ON lines.line = 1
  OR (lines.line = 2 AND seq.i % 2 = 0)
  OR (lines.line = 3 AND seq.i % 5 = 0);

WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < (SELECT n_orders FROM scale_n)
),
totals AS (
  SELECT l.i, SUM(l.quantity * b.price) AS total
  FROM scale_order_lines l
  JOIN books b ON b.book_id = l.book_id
  GROUP BY l.i
)
INSERT INTO orders (order_id, customer_id, status, total_amount, ordered_at)
SELECT
  100000 + seq.i,
  CASE WHEN seq.i % 10 < 3 THEN 100001 ELSE 100001 + (seq.i % (SELECT n_customers FROM scale_n)) END,
  CASE seq.i % 20
    WHEN 0 THEN 'pending'
    WHEN 1 THEN 'refunded'
    WHEN 2 THEN 'cancelled'
    WHEN 3 THEN 'shipped'
    ELSE 'paid'
  END,
  totals.total,
  datetime('2025-01-01 00:00:00', '+' || ((seq.i * 39311999) / (SELECT n_orders FROM scale_n)) || ' seconds')
FROM seq
JOIN totals ON totals.i = seq.i;

INSERT INTO order_items (order_item_id, order_id, book_id, quantity, unit_price)
SELECT
  100000 + l.i * 3 + l.line,
  100000 + l.i,
  l.book_id,
  l.quantity,
  b.price
FROM scale_order_lines l
JOIN books b ON b.book_id = l.book_id;

-- 評價：每 4 筆訂單 1 則，評第 1 行明細的書，評價時間為下單後 3 天
INSERT INTO reviews (review_id, order_id, book_id, rating, created_at)
SELECT
  100000 + l.i,
  100000 + l.i,
  l.book_id,
  1 + (l.i % 5),
  datetime(o.ordered_at, '+3 days')
FROM scale_order_lines l
JOIN orders o ON o.order_id = 100000 + l.i
WHERE l.line = 1 AND l.i % 4 = 0;

DROP TABLE scale_order_lines;

-- 匯出任務：2025-06-01 起平均分布到 2026-03-19（25,142,400 秒）
-- 已完成任務輪替在職主管 10（TPE-01）與 HQ 分析師 12（全域，scope 為 NULL）；
-- 每 1,000 筆有 1 筆 denied（只有 orders:read 的店員 11 請求）與 1 筆 cancelled（員工 13 離職時撤銷）
WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < (SELECT n_jobs FROM scale_n)
)
INSERT INTO export_jobs (job_id, status, payload, claimed_by, requested_by_staff_id, scope_store_code, status_reason, created_at)
SELECT
  100000 + i,
  CASE WHEN i % 1000 = 0 THEN 'cancelled' WHEN i % 1000 = 500 THEN 'denied' ELSE 'done' END,
  '{"batch":' || i || '}',
  CASE WHEN i % 1000 IN (0, 500) THEN NULL ELSE 'worker-' || (i % 4 + 1) END,
  CASE WHEN i % 1000 = 0 THEN 13 WHEN i % 1000 = 500 THEN 11 WHEN i % 2 = 0 THEN 10 ELSE 12 END,
  CASE WHEN i % 1000 IN (0, 500) OR i % 2 = 0 THEN 'TPE-01' END,
  CASE WHEN i % 1000 = 0 THEN 'requester_offboarded' WHEN i % 1000 = 500 THEN 'missing_orders_export_permission' END,
  datetime('2025-06-01 00:00:00', '+' || ((i * 25142400) / (SELECT n_jobs FROM scale_n)) || ' seconds')
FROM seq;

-- 5 筆排隊中任務（接在合成任務 ID 之後）：在職主管 10、HQ 分析師 12、離職員工 13、已撤銷角色的員工 14、只有 orders:read 的店員 11
INSERT INTO export_jobs (job_id, status, payload, claimed_by, requested_by_staff_id, scope_store_code, created_at)
SELECT 100000 + (SELECT n_jobs FROM scale_n) + t.k, 'queued', '{"batch":"tail_' || t.k || '"}', NULL, t.staff_id, t.scope, t.created_at
FROM (
            SELECT 1 AS k, 10 AS staff_id, 'TPE-01' AS scope, '2026-03-20 02:00:00' AS created_at
  UNION ALL SELECT 2, 12, NULL,     '2026-03-20 02:01:00'
  UNION ALL SELECT 3, 13, 'TPE-01', '2026-03-20 02:02:00'
  UNION ALL SELECT 4, 14, 'TXG-01', '2026-03-20 02:03:00'
  UNION ALL SELECT 5, 11, 'TPE-01', '2026-03-20 02:04:00'
) AS t;

-- 瀏覽事件：2026-03-01 起平均分布到 2026-03-21（1,728,000 秒），40% 集中在熱門書 201
WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < (SELECT n_views FROM scale_n)
)
INSERT INTO book_view_events (view_id, book_id, viewed_at)
SELECT
  100000 + i,
  CASE WHEN i % 10 < 4 THEN 201 ELSE 201 + (i % 9) END,
  datetime('2026-03-01 00:00:00', '+' || ((i * 1728000) / (SELECT n_views FROM scale_n)) || ' seconds')
FROM seq;

DROP TABLE scale_n;

ANALYZE;
