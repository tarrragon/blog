-- 領域乙（cloud-academy）：中規模決定性壓測資料（疊加於 seed.sql 之上）
-- ID 區段契約：手寫邊界反例佔 1..9999，本檔合成列一律自 100001 起跳，絕不撞號。
-- 設計重點：
-- 1. users 新增 5,000 列、subscriptions 新增 10,000 列、invoices 新增 50,000 列（驗證 Anti-Join 與時間區間索引）
-- 2. webhook_events 新增 20,010 列（含 1,500 筆熱點重送風暴 evt_storm_hot 與 10 筆 pending，驗證部分索引與重複稽核）

PRAGMA foreign_keys = ON;

WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < 5000
)
INSERT INTO users (user_id, display_name, email, country, joined_at)
SELECT
  100000 + i,
  '學員_' || i,
  CASE WHEN i <= 800 THEN 'dup_student@academy.io' ELSE 'student_' || i || '@academy.io' END,
  CASE i % 4 WHEN 0 THEN 'TW' WHEN 1 THEN 'JP' WHEN 2 THEN 'SG' ELSE NULL END,
  datetime('2025-01-01 00:00:00', '+' || (i * 7200) || ' seconds')
FROM seq;

WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < 10000
)
INSERT INTO subscriptions (sub_id, user_id, plan_code, status, started_at, ended_at)
SELECT
  100000 + i,
  100001 + ((i - 1) % 5000),
  CASE i % 5 WHEN 0 THEN 'team' WHEN 1 THEN 'free' ELSE 'pro' END,
  CASE i % 10 WHEN 0 THEN 'canceled' WHEN 1 THEN 'past_due' WHEN 2 THEN 'trialing' ELSE 'active' END,
  datetime('2025-01-01 00:00:00', '+' || (i * 3600) || ' seconds'),
  CASE WHEN i % 10 = 0 THEN datetime('2025-02-01 00:00:00', '+' || (i * 3600) || ' seconds') ELSE NULL END
FROM seq;

WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < 50000
)
INSERT INTO invoices (invoice_id, sub_id, amount, status, issued_at)
SELECT
  100000 + i,
  100001 + ((i - 1) % 9500), -- 刻意保留 500 筆 active/trialing 訂閱無任何帳單
  CASE i % 3 WHEN 0 THEN 2900 WHEN 1 THEN 990 ELSE 1490 END,
  CASE i % 20 WHEN 0 THEN 'void' WHEN 1 THEN 'refunded' WHEN 2 THEN 'open' ELSE 'paid' END,
  datetime('2025-01-01 00:00:00', '+' || (i * 750) || ' seconds')
FROM seq;

WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < 20010
)
INSERT INTO webhook_events (event_id, provider, external_id, status, received_at)
SELECT
  100000 + i,
  CASE i % 3 WHEN 0 THEN 'newebpay' ELSE 'stripe' END,
  CASE WHEN i <= 1500 THEN 'evt_storm_hot' ELSE 'evt_scale_' || i END,
  CASE WHEN i > 20000 THEN 'pending' ELSE 'done' END,
  datetime('2025-06-01 00:00:00', '+' || (i * 480) || ' seconds')
FROM seq;

ANALYZE;
