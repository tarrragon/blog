-- 領域甲（bookstore）：中規模決定性壓測資料（疊加於 seed.sql 之上）
-- ID 區段契約：手寫邊界反例佔 1..9999，本檔合成列一律自 100001 起跳，絕不撞號。
-- 設計重點：
-- 1. customers 新增 7,000 列，其中 2,000 列共用熱點重複信箱 hot@bookstore.tw（驗證 SQL.17 自連接平方退化）
-- 2. orders 新增 50,000 列橫跨 2025-01 至 2026-03（驗證 Sargable 區間查詢、深頁 OFFSET vs Keyset）
-- 3. export_jobs 新增 20,000 列 done + 5 列 queued（驗證部分索引 idx_export_jobs_queued）
-- 4. book_view_events 新增 30,000 列，40% 集中在熱門書 201（驗證高頻計數與熱點傾斜）

PRAGMA foreign_keys = ON;

WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < 7000
)
INSERT INTO customers (customer_id, name, email, city, created_at)
SELECT
  100000 + i,
  '會員_' || i,
  CASE WHEN i <= 2000 THEN 'hot@bookstore.tw' ELSE 'user_' || i || '@bookstore.tw' END,
  CASE i % 5
    WHEN 0 THEN 'Taipei'
    WHEN 1 THEN 'Taichung'
    WHEN 2 THEN 'Kaohsiung'
    WHEN 3 THEN 'Tainan'
    ELSE NULL
  END,
  datetime('2025-01-01 00:00:00', '+' || (i * 5400) || ' seconds')
FROM seq;

WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < 50000
)
INSERT INTO orders (order_id, customer_id, status, total_amount, ordered_at)
SELECT
  100000 + i,
  CASE WHEN i % 10 < 3 THEN 100001 ELSE 100001 + (i % 7000) END,
  CASE i % 20
    WHEN 0 THEN 'pending'
    WHEN 1 THEN 'refunded'
    WHEN 2 THEN 'cancelled'
    WHEN 3 THEN 'shipped'
    ELSE 'paid'
  END,
  ((i * 37) % 25 + 1) * 100,
  datetime('2025-01-01 00:00:00', '+' || (i * 750) || ' seconds')
FROM seq;

WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < 20005
)
INSERT INTO export_jobs (job_id, status, payload, claimed_by, created_at)
SELECT
  100000 + i,
  CASE WHEN i > 20000 THEN 'queued' ELSE 'done' END,
  '{"batch":' || i || '}',
  CASE WHEN i > 20000 THEN NULL ELSE 'worker-' || (i % 4 + 1) END,
  datetime('2025-06-01 00:00:00', '+' || (i * 600) || ' seconds')
FROM seq;

WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < 30000
)
INSERT INTO book_view_events (view_id, book_id, viewed_at)
SELECT
  100000 + i,
  CASE WHEN i % 10 < 4 THEN 201 ELSE 201 + (i % 8) END,
  datetime('2026-03-01 00:00:00', '+' || (i * 60) || ' seconds')
FROM seq;

ANALYZE;
