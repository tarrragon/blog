-- 領域丙（swift-logistics）：捷配物流基準資料與邊界反例列
-- 刻意埋設：
-- 1. 倉庫階層：10（北區總倉）-> 11（桃園衛星倉）、12（新竹衛星倉）；20（中區總倉）-> 21（台中港倉）
-- 2. 商家 1001 貢獻多筆運單模擬資料傾斜；商家 1003 尚未寄出任何運單；商家 1004 tier 為 NULL
-- 3. 運單 7001 同時有 2 件包裹與 3 筆掃描事件（雙重一對多膨脹），且同時含 exception 與 signed
-- 4. 運單 7002 有正常的 signed 事件與一筆 recorded_at IS NULL 的 exception 事件（C03 跨引擎 NULL 排序反例）
-- 5. 運單 7004 沒有任何掃描事件；事件 8008 的 shipment_id IS NULL 且 event_type = 'exception'（NOT IN 反例）
-- 6. 2026-03-15 14:00:00 同秒三筆運單（7005、7006、7007）測試混合升降冪 Keyset 分頁
-- 7. 司機 501 含跨午夜夜班（22:00 到隔日 06:00）；dispatch_tasks 以 completed 為主、少量 queued

PRAGMA foreign_keys = ON;

INSERT INTO warehouses (warehouse_id, code, region, parent_hub_id) VALUES
  (10, 'TW-N-HUB', 'north',   NULL),
  (11, 'TW-N-TYN', 'north',   10),
  (12, 'TW-N-HSZ', 'north',   10),
  (20, 'TW-C-HUB', 'central', NULL),
  (21, 'TW-C-TXG', 'central', 20);

INSERT INTO merchants (merchant_id, name, account_key, tier) VALUES
  (1001, '星海電商', 'TW_STAR_01', 'enterprise'), -- 主力大客戶（資料傾斜來源）
  (1002, '山丘選物', 'tw_hill_02', 'growth'),     -- 小寫 account_key 測試前綴比對
  (1003, '晨光烘焙', 'TW_MORN_03', 'starter'),    -- 從未寄件商家
  (1004, '微風文創', 'TW_WIND_04', NULL);         -- tier IS NULL 新商家

INSERT INTO shipments (shipment_id, merchant_id, warehouse_id, status, fee_cents, created_at) VALUES
  (7001, 1001, 11, 'delivered',  18000, '2026-03-10 08:00:00'),
  (7002, 1001, 11, 'delivered',  12000, '2026-03-10 09:00:00'),
  (7003, 1001, 12, 'returned',   25000, '2026-03-11 10:30:00'),
  (7004, 1002, 21, 'created',     9500, '2026-03-12 11:00:00'), -- 尚無任何掃描事件
  (7005, 1001, 11, 'in_transit', 15000, '2026-03-15 14:00:00'), -- 與 7006、7007 同秒
  (7006, 1002, 11, 'in_transit', 15000, '2026-03-15 14:00:00'),
  (7007, 1004, 11, 'in_transit', 21000, '2026-03-15 14:00:00'),
  (7008, 1001, 11, 'in_transit', 11000, '2026-03-14 14:00:00');

INSERT INTO shipment_packages (package_id, shipment_id, weight_grams, fragile) VALUES
  (7101, 7001, 1200, 0),
  (7102, 7001, 2400, 1), -- 7001 兩件包裹
  (7103, 7002,  800, 0),
  (7104, 7003, 3500, 1),
  (7105, 7004,  500, 0),
  (7106, 7005, 1800, 0),
  (7107, 7006, 1600, 0),
  (7108, 7007, 2200, 1),
  (7109, 7008,  950, 0);

INSERT INTO shipment_payloads (shipment_id, raw_waybill_json) VALUES
  (7001, '{"carrier":"swift","customs":{"hs_code":"4901.99"},"recipient_note":"警衛室代收"}'),
  (7002, '{"carrier":"swift","recipient_note":"週一至週五收件"}'),
  (7003, '{"carrier":"swift","return_reason":"收件人拒收"}'),
  (7004, '{"carrier":"swift","cod_amount":0}'),
  (7005, '{"carrier":"swift","temperature":"ambient"}'),
  (7006, '{"carrier":"swift","temperature":"ambient"}'),
  (7007, '{"carrier":"swift","fragile_seal":true}'),
  (7008, '{"carrier":"swift","temperature":"ambient"}');

INSERT INTO shipment_events (event_id, shipment_id, event_type, recorded_at) VALUES
  (8001, 7001, 'picked',    '2026-03-10 08:30:00'),
  (8002, 7001, 'exception', '2026-03-10 15:00:00'), -- 7001 同時含 exception 與 signed
  (8003, 7001, 'signed',    '2026-03-11 11:00:00'),
  (8004, 7002, 'signed',    '2026-03-10 18:00:00'),
  (8005, 7002, 'exception', NULL),                  -- recorded_at IS NULL，觸發 C03 反例
  (8006, 7003, 'picked',    '2026-03-11 11:00:00'),
  (8007, 7005, 'hub_in',    '2026-03-15 16:00:00'),
  (8008, NULL, 'exception', '2026-03-15 17:00:00'); -- 孤兒掃碼事件：shipment_id IS NULL

INSERT INTO driver_shifts (shift_id, driver_id, route_code, starts_at, ends_at) VALUES
  (9001, 501, 'N-NIGHT-01', '2026-03-15 22:00:00', '2026-03-16 06:00:00'), -- 跨午夜班表
  (9002, 502, 'N-DAY-02',   '2026-03-15 08:00:00', '2026-03-15 16:00:00');

INSERT INTO dispatch_tasks (task_id, shipment_id, status, claimed_by, priority, created_at) VALUES
  (9501, 7001, 'completed', 'disp-a', 5, '2026-03-10 08:05:00'),
  (9502, 7002, 'completed', 'disp-b', 4, '2026-03-10 09:05:00'),
  (9503, 7003, 'completed', 'disp-a', 8, '2026-03-11 10:35:00'),
  (9504, 7005, 'claimed',   'disp-a', 9, '2026-03-15 14:05:00'),
  (9505, 7006, 'queued',    NULL,     7, '2026-03-15 14:06:00'),
  (9506, 7007, 'queued',    NULL,     9, '2026-03-15 14:07:00');

INSERT INTO billing_statements (statement_id, merchant_id, period_month, total_cents, status) VALUES
  (9801, 1001, '2026-02', 420000, 'settled'),
  (9802, 1001, '2026-03',  81000, 'draft'),
  (9803, 1002, '2026-03',  24500, 'issued');
