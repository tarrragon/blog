-- 領域丙（swift-logistics）：中規模決定性壓測資料（疊加於 seed.sql 之上）
-- ID 區段契約：手寫邊界反例佔 1..9999，本檔合成列一律自 100001 起跳，絕不撞號。
--
-- 規模參數：倍數存在暫存表 scale_params.mult（預設 1，上限 10），用法見 bookstore/seed_scale.sql 檔頭；倍數只改變密度，時間跨度固定。
--
-- 一致性契約（verify_domains.py 會檢查）：
-- - 每張運單有 1 至 3 件包裹與 1 列收件人 PII；子表 merchant_id 與父表一致（複合外鍵保證）。
-- - 掃描事件與運單狀態一致：created 無事件；in_transit 為 picked、hub_in；delivered 為 picked、signed；
--   returned 為 picked、exception。事件時間都晚於運單建立時間。
--   （每張運單只留 2 筆事件以控制瀏覽器記憶體：倍數 1 時記憶體資料庫約 26 MB，事件與其兩個索引是最大宗；手機建議倍數不超過 3）
-- - 2025-04-01 以前建立的運單已過收件人個資保存期限，PII 明文已抹除（erased_at 有值）。
-- - 非 created 的運單各有 1 筆 completed 調度任務；只有最後 10 筆 created 運單各有 1 筆 queued 任務。
--
-- 設計重點（倍數 1 時）：
-- 1. shipments 新增 50,000 列，35% 集中於大客戶 merchant_id = 1001（驗證資料傾斜與複合索引）
-- 2. dispatch_tasks 約 45,000 列，僅 10 列 queued（驗證部分索引 idx_dispatch_queued）
-- 3. shipment_events 約 9 萬列、shipment_packages 約 8.5 萬列（驗證多事件視窗函式、時間區間與子表租戶索引）

PRAGMA foreign_keys = ON;

CREATE TEMP TABLE IF NOT EXISTS scale_params (mult INTEGER NOT NULL);
INSERT INTO scale_params SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM scale_params);
CREATE TEMP TABLE scale_n AS
SELECT MIN(MAX(mult, 1), 10) * 50000 AS n_shipments FROM scale_params LIMIT 1;

-- 運單：2025-01-01 起平均分布到 2026-03-14（37,756,800 秒）
WITH RECURSIVE seq(i) AS (
  SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < (SELECT n_shipments FROM scale_n)
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
  datetime('2025-01-01 00:00:00', '+' || ((i * 37756800) / (SELECT n_shipments FROM scale_n)) || ' seconds')
FROM seq;

-- 包裹：第 1 件一律存在，第 2 件在偶數運單存在，第 3 件在 5 的倍數運單存在
WITH lines(line) AS (VALUES (1), (2), (3))
INSERT INTO shipment_packages (package_id, shipment_id, merchant_id, weight_grams, fragile)
SELECT
  100000 + (s.shipment_id - 100000) * 3 + lines.line,
  s.shipment_id,
  s.merchant_id,
  200 + ((s.shipment_id * 37 + lines.line * 101) % 4800),
  CASE WHEN (s.shipment_id + lines.line) % 7 = 0 THEN 1 ELSE 0 END
FROM shipments s
JOIN lines
  ON lines.line = 1
  OR (lines.line = 2 AND s.shipment_id % 2 = 0)
  OR (lines.line = 3 AND s.shipment_id % 5 = 0)
WHERE s.shipment_id > 100000;

-- 收件人 PII：2025-04-01 以前建立的運單已抹除
INSERT INTO shipment_recipient_pii (shipment_id, merchant_id, recipient_name, recipient_phone, delivery_address, erased_at)
SELECT
  shipment_id,
  merchant_id,
  CASE WHEN created_at < '2025-04-01 00:00:00' THEN NULL ELSE '收件人_' || (shipment_id - 100000) END,
  CASE WHEN created_at < '2025-04-01 00:00:00' THEN NULL ELSE '+8869' || printf('%08d', shipment_id - 100000) END,
  CASE WHEN created_at < '2025-04-01 00:00:00' THEN NULL ELSE '合成地址 ' || (shipment_id - 100000) || ' 號' END,
  CASE WHEN created_at < '2025-04-01 00:00:00' THEN '2025-10-01 00:00:00' END
FROM shipments
WHERE shipment_id > 100000;

-- 原始託運報文：每 10 張運單保留 1 份（冷資料）
INSERT INTO shipment_payloads (shipment_id, merchant_id, raw_waybill_json)
SELECT shipment_id, merchant_id, '{"carrier":"swift","batch":' || (shipment_id - 100000) || '}'
FROM shipments
WHERE shipment_id > 100000 AND shipment_id % 10 = 0;

-- 掃描事件：依運單狀態展開步驟，第 step 步發生在建立後 step * 6 小時
WITH steps(step, event_type) AS (
  VALUES (1, 'picked'), (2, 'hub_in'), (3, 'out_for_delivery'), (4, 'signed'), (5, 'exception')
)
INSERT INTO shipment_events (event_id, shipment_id, merchant_id, event_type, recorded_at)
SELECT
  100000 + (s.shipment_id - 100000) * 5 + steps.step,
  s.shipment_id,
  s.merchant_id,
  steps.event_type,
  CASE
    WHEN steps.step = 5 AND s.shipment_id % 97 = 0 THEN NULL -- 少量離線同步缺時間的 exception（NULL 排序反例）
    ELSE datetime(s.created_at, '+' || (CASE WHEN steps.step = 5 THEN 3 ELSE steps.step END * 6) || ' hours')
  END
FROM shipments s
JOIN steps
  ON (s.status = 'in_transit' AND steps.step IN (1, 2))
  OR (s.status = 'delivered'  AND steps.step IN (1, 4))
  OR (s.status = 'returned'   AND steps.step IN (1, 5))
WHERE s.shipment_id > 100000;

-- 調度任務：非 created 運單各 1 筆 completed；最後 10 筆 created 運單各 1 筆 queued
INSERT INTO dispatch_tasks (task_id, shipment_id, merchant_id, status, claimed_by, priority, created_at)
SELECT
  s.shipment_id,
  s.shipment_id,
  s.merchant_id,
  'completed',
  'disp-' || (s.shipment_id % 5 + 1),
  (s.shipment_id % 10) + 1,
  datetime(s.created_at, '+5 minutes')
FROM shipments s
WHERE s.shipment_id > 100000 AND s.status <> 'created';

INSERT INTO dispatch_tasks (task_id, shipment_id, merchant_id, status, claimed_by, priority, created_at)
SELECT
  s.shipment_id,
  s.shipment_id,
  s.merchant_id,
  'queued',
  NULL,
  (s.shipment_id % 10) + 1,
  datetime(s.created_at, '+5 minutes')
FROM shipments s
WHERE s.shipment_id > 100000 AND s.status = 'created'
ORDER BY s.shipment_id DESC
LIMIT 10;

DROP TABLE scale_n;

ANALYZE;
