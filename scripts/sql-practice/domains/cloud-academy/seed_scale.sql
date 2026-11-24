-- 領域乙（cloud-academy）：中規模決定性壓測資料（疊加於 seed.sql 之上）
-- ID 區段契約：手寫邊界反例佔 1..9999，本檔合成列一律自 100001 起跳，絕不撞號。
--
-- 規模參數：倍數存在暫存表 scale_params.mult（預設 1，上限 10），用法見 bookstore/seed_scale.sql 檔頭；倍數只改變密度，時間跨度固定。
--
-- 時間線契約（verify_domains.py 會檢查）：
-- - 合成學員在 2024 年加入，合成訂閱在 2025-01-01 至 2026-02-28 開始，因此訂閱一律晚於學員加入。
-- - 帳單從訂閱開始日起每 30 天開 1 張，不早於訂閱開始、不晚於訂閱結束，也不晚於 2026-03-31。
-- - 已刪除學員（status = 'deleted'）的訂閱一律為 canceled；trialing 訂閱沒有帳單；free 方案沒有帳單。
--
-- 設計重點（倍數 1 時）：
-- 1. users 新增 5,000 列（800 列共用 dup_student@academy.io）、subscriptions 10,000 列、invoices 約 6 萬列
-- 2. 最後開始的 5% 訂閱尚未開立任何帳單（驗證 Anti-Join 與時間區間索引）
-- 3. webhook_events 新增 20,010 列（含 1,500 筆熱點重送風暴 evt_storm_hot 與 10 筆 pending，驗證部分索引與重複稽核）
-- 4. lesson_progress 新增 20,000 列（三分之一未完課，completed_at 為 NULL）

PRAGMA foreign_keys = ON;

CREATE TEMP TABLE IF NOT EXISTS scale_params (mult INTEGER NOT NULL);
INSERT INTO scale_params SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM scale_params);
CREATE TEMP TABLE scale_n AS
SELECT
  MIN(MAX(mult, 1), 10) * 5000  AS n_users,
  MIN(MAX(mult, 1), 10) * 800   AS n_dup,
  MIN(MAX(mult, 1), 10) * 10000 AS n_subs,
  MIN(MAX(mult, 1), 10) * 20000 AS n_webhooks,
  MIN(MAX(mult, 1), 10) * 1500  AS n_storm,
  MIN(MAX(mult, 1), 10) * 20000 AS n_progress
FROM scale_params LIMIT 1;

-- 學員：2024 年內平均加入；熱點重複信箱以外每 60 列 1 位已刪除（姓名與信箱清為 NULL）、每 45 列 1 位鎖定
WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < (SELECT n_users FROM scale_n)
),
u AS (
  SELECT i, (i % 60 = 0 AND i > (SELECT n_dup FROM scale_n)) AS is_deleted FROM seq
)
INSERT INTO users (user_id, display_name, email, country, status, deleted_at, joined_at)
SELECT
  100000 + i,
  CASE WHEN is_deleted THEN NULL ELSE '學員_' || i END,
  CASE
    WHEN is_deleted THEN NULL
    WHEN i <= (SELECT n_dup FROM scale_n) THEN 'dup_student@academy.io'
    ELSE 'student_' || i || '@academy.io'
  END,
  CASE i % 4 WHEN 0 THEN 'TW' WHEN 1 THEN 'JP' WHEN 2 THEN 'SG' ELSE NULL END,
  CASE WHEN is_deleted THEN 'deleted' WHEN i % 45 = 0 THEN 'locked' ELSE 'active' END,
  CASE WHEN is_deleted THEN '2026-02-01 00:00:00' END,
  datetime('2024-01-01 00:00:00', '+' || ((i * 31536000) / (SELECT n_users FROM scale_n)) || ' seconds')
FROM u;

INSERT INTO user_pii (user_id, legal_name, phone_e164, billing_address, erased_at)
SELECT
  user_id,
  CASE WHEN status = 'deleted' THEN NULL ELSE '合成姓名 ' || (user_id - 100000) END,
  CASE WHEN status = 'deleted' THEN NULL ELSE '+8869' || printf('%08d', user_id - 100000) END,
  NULL,
  deleted_at
FROM users
WHERE user_id > 100000;

INSERT INTO user_credentials (user_id, password_hash, mfa_enabled, failed_attempts, locked_until, password_changed_at)
SELECT
  user_id,
  '$argon2id$v=19$m=65536$mock_hash_' || user_id,
  (user_id % 3 = 0),
  CASE WHEN status = 'locked' THEN 6 ELSE 0 END,
  CASE WHEN status = 'locked' THEN '2026-03-25 12:00:00' END,
  joined_at
FROM users
WHERE user_id > 100000;

-- 訂閱：2025-01-01 起平均分布到 2026-02-28（36,547,200 秒）
WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < (SELECT n_subs FROM scale_n)
),
s AS (
  SELECT
    seq.i,
    100001 + ((seq.i - 1) % (SELECT n_users FROM scale_n)) AS user_id,
    datetime('2025-01-01 00:00:00', '+' || ((seq.i * 36547200) / (SELECT n_subs FROM scale_n)) || ' seconds') AS started_at
  FROM seq
)
INSERT INTO subscriptions (sub_id, user_id, org_id, plan_code, status, started_at, ended_at)
SELECT
  100000 + s.i,
  s.user_id,
  NULL,
  CASE s.i % 5 WHEN 0 THEN 'team' WHEN 1 THEN 'free' ELSE 'pro' END,
  CASE
    WHEN s.i % 10 = 0 OR u.status = 'deleted' THEN 'canceled'
    WHEN s.i % 10 = 1 THEN 'past_due'
    WHEN s.started_at >= '2026-02-14 00:00:00' THEN 'trialing'
    ELSE 'active'
  END,
  s.started_at,
  CASE WHEN s.i % 10 = 0 OR u.status = 'deleted' THEN datetime(s.started_at, '+45 days') END
FROM s
JOIN users u ON u.user_id = s.user_id;

-- 帳單：每 30 天 1 張（最多 15 期），最後開始的 5% 訂閱尚未開帳
WITH RECURSIVE k(n) AS (
  SELECT 0 UNION ALL SELECT n + 1 FROM k WHERE n < 14
)
INSERT INTO invoices (invoice_id, sub_id, amount, status, issued_at)
SELECT
  100000 + (s.sub_id - 100000) * 20 + k.n,
  s.sub_id,
  CASE s.plan_code WHEN 'team' THEN 2900 ELSE 990 END,
  CASE ((s.sub_id - 100000) + k.n) % 20 WHEN 0 THEN 'void' WHEN 1 THEN 'refunded' WHEN 2 THEN 'open' ELSE 'paid' END,
  datetime(s.started_at, '+' || (k.n * 30) || ' days')
FROM subscriptions s
JOIN k
WHERE s.sub_id > 100000
  AND s.sub_id - 100000 <= (SELECT n_subs FROM scale_n) * 95 / 100
  AND s.plan_code <> 'free'
  AND s.status <> 'trialing'
  AND datetime(s.started_at, '+' || (k.n * 30) || ' days') <= COALESCE(s.ended_at, '2026-03-31 23:59:59')
  AND datetime(s.started_at, '+' || (k.n * 30) || ' days') <= '2026-03-31 23:59:59';

-- 金流 Webhook：2025-06-01 起平均分布到 2026-03-14（24,105,600 秒）；前 n_storm 筆為同一事件的重送風暴，最後 10 筆待處理
WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < (SELECT n_webhooks FROM scale_n) + 10
)
INSERT INTO webhook_events (event_id, provider, external_id, status, signature_valid, source_ip, received_at)
SELECT
  100000 + i,
  CASE WHEN i <= (SELECT n_storm FROM scale_n) THEN 'stripe' WHEN i % 3 = 0 THEN 'newebpay' ELSE 'stripe' END,
  CASE WHEN i <= (SELECT n_storm FROM scale_n) THEN 'evt_storm_hot' ELSE 'evt_scale_' || i END,
  CASE
    WHEN i > (SELECT n_webhooks FROM scale_n) THEN 'pending'
    WHEN i % 400 = 0 THEN 'dead'
    ELSE 'done'
  END,
  CASE WHEN i % 400 = 0 AND i <= (SELECT n_webhooks FROM scale_n) THEN 0 ELSE 1 END,
  CASE WHEN i % 400 = 0 THEN '198.51.100.' || (i % 250) WHEN i % 3 = 0 THEN '211.72.249.10' ELSE '54.187.205.235' END,
  datetime('2025-06-01 00:00:00', '+' || ((i * 24105600) / ((SELECT n_webhooks FROM scale_n) + 10)) || ' seconds')
FROM seq;

-- 學習進度：2025-01-01 起平均分布到 2026-03-14，只落在已發布課程（101–104、106）
WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < (SELECT n_progress FROM scale_n)
)
INSERT INTO lesson_progress (progress_id, user_id, course_id, lesson_no, completed_at, watch_seconds)
SELECT
  100000 + i,
  100001 + ((i * 7) % (SELECT n_users FROM scale_n)),
  CASE i % 5 WHEN 0 THEN 101 WHEN 1 THEN 102 WHEN 2 THEN 103 WHEN 3 THEN 104 ELSE 106 END,
  1 + (i / 5) % 12,
  CASE WHEN i % 3 = 0 THEN NULL
       ELSE datetime('2025-01-01 00:00:00', '+' || ((i * 37756800) / (SELECT n_progress FROM scale_n)) || ' seconds') END,
  300 + (i % 20) * 60
FROM seq;

DROP TABLE scale_n;

ANALYZE;
