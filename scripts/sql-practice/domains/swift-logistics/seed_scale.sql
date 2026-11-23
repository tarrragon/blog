-- 領域丙（swift-logistics）：中規模決定性壓測資料（疊加於 seed.sql 之上）
-- ID 區段契約：手寫邊界反例佔 1..9999，本檔合成列一律自 100001 起跳，絕不撞號。
-- 設計重點：
-- 1. shipments 新增 50,000 列，35% 集中於大客戶 merchant_id = 1001（驗證資料傾斜與複合索引）
-- 2. dispatch_tasks 新增 30,010 列，99.97% 為 completed、僅 10 列為 queued（驗證部分索引 idx_dispatch_queued）
-- 3. shipment_events 新增 30,000 列（驗證時間區間與索引掃描）

PRAGMA foreign_keys = ON;

WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < 50000
)
INSERT INTO shipments (shipment_id, merchant_id, warehouse_id, status, fee_cents, created_at)
SELECT
  100000 + i,
  CASE
    WHEN i % 20 < 7 THEN 1001 -- 35% 資料傾斜集中在大客戶星海電商
    WHEN i % 20 < 14 THEN 1002
    ELSE 1004
  END,
  CASE i % 4 WHEN 0 THEN 11 WHEN 1 THEN 12 WHEN 2 THEN 21 ELSE 10 END,
  CASE i % 10 WHEN 0 THEN 'returned' WHEN 1 THEN 'in_transit' WHEN 2 THEN 'created' ELSE 'delivered' END,
  ((i * 29) % 40 + 5) * 500,
  datetime('2025-01-01 00:00:00', '+' || (i * 750) || ' seconds')
FROM seq;

WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < 30010
)
INSERT INTO dispatch_tasks (task_id, shipment_id, status, claimed_by, priority, created_at)
SELECT
  100000 + i,
  100001 + ((i - 1) % 50000),
  CASE WHEN i > 30000 THEN 'queued' ELSE 'completed' END,
  CASE WHEN i > 30000 THEN NULL ELSE 'disp-' || (i % 5 + 1) END,
  (i % 10) + 1,
  datetime('2025-06-01 00:00:00', '+' || (i * 420) || ' seconds')
FROM seq;

WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < 30000
)
INSERT INTO shipment_events (event_id, shipment_id, event_type, recorded_at)
SELECT
  100000 + i,
  100001 + ((i - 1) % 30000),
  CASE i % 5
    WHEN 0 THEN 'picked'
    WHEN 1 THEN 'hub_in'
    WHEN 2 THEN 'out_for_delivery'
    WHEN 3 THEN 'signed'
    ELSE 'exception'
  END,
  datetime('2025-06-01 00:00:00', '+' || (i * 420) || ' seconds')
FROM seq;

ANALYZE;
