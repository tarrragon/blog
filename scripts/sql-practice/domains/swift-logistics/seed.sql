-- 領域丙（swift-logistics）：捷配物流基準資料與邊界反例列（含多租戶子表鍵、API Key 撤銷、收件人 PII 與唯附寫稽核）
-- 刻意埋設：
-- 1. 倉庫階層：10（北區總倉）-> 11（桃園衛星倉）、12（新竹衛星倉）；20（中區總倉）-> 21（台中港倉）
-- 2. 商家 1001 貢獻多筆運單模擬資料傾斜；商家 1003 從未寄件且狀態為 suspended（留有一把未撤銷 API Key 4）；商家 1004 tier 為 NULL
-- 3. 運單 7001 同時有 2 件包裹與 3 筆掃描事件（雙重一對多膨脹），且同時含 exception 與 signed
-- 4. 運單 7002 有正常的 signed 事件與一筆 recorded_at IS NULL 的 exception 事件（C03 跨引擎 NULL 排序反例）
-- 5. 運單 7004 沒有任何掃描事件；事件 8008 的 shipment_id 與 merchant_id 皆為 NULL 且 event_type = 'exception'（孤兒掃碼事件，NOT IN 反例）
-- 6. 2026-03-15 14:00:00 同秒三筆運單（7005、7006、7007）測試混合升降冪 Keyset 分頁
-- 7. 司機 501 含跨午夜夜班（22:00 到隔日 06:00）；司機 503 已停權仍留有未來班表；dispatch_tasks 以 completed 為主、少量 queued
-- 8. 資安反例：merchant_api_keys 含已撤銷但未過期的 Key 2（驗證 AND/OR 優先序繞過）、已過期 Key 3、停權商家 Key 4、永不過期 Key 5；billing_audit_logs 掛載防竄改 Trigger
-- 9. 平台員工：301 為在職財務稽核員；302 已離職軟刪除卻留有未撤銷的倉儲主管角色（離職治理缺口，與書店員工 13 同型）
-- 10. 母體約定：merchants 含停權商家 1003，題目需求須寫明查的是「全部商家」還是「目前有效商家」（題目 JSON 的 population 欄位）

PRAGMA foreign_keys = ON;

INSERT INTO warehouses (warehouse_id, code, region, parent_hub_id) VALUES
  (10, 'TW-N-HUB', 'north',   NULL),
  (11, 'TW-N-TYN', 'north',   10),
  (12, 'TW-N-HSZ', 'north',   10),
  (20, 'TW-C-HUB', 'central', NULL),
  (21, 'TW-C-TXG', 'central', 20);

INSERT INTO merchants (merchant_id, name, account_key, tier, status, deleted_at) VALUES
  (1001, '星海電商', 'TW_STAR_01', 'enterprise', 'active',    NULL), -- 主力大客戶（資料傾斜來源）
  (1002, '山丘選物', 'tw_hill_02', 'growth',     'active',    NULL), -- 小寫 account_key 測試前綴比對
  (1003, '晨光烘焙', 'TW_MORN_03', 'starter',    'suspended', NULL), -- 從未寄件且已停權（測試停權商家金鑰攔截）
  (1004, '微風文創', 'TW_WIND_04', NULL,         'active',    NULL); -- tier IS NULL 新商家

INSERT INTO merchant_users (merchant_user_id, merchant_id, email, display_name, role_code, status, created_at, deleted_at) VALUES
  (201, 1001, 'ops@star.tw',      '星海倉管', 'owner',      'active',     '2025-02-01 09:00:00', NULL),
  (202, 1001, 'fin@star.tw',      '星海財務', 'finance',    'active',     '2025-03-01 09:00:00', NULL),
  (203, 1002, 'ops@hill.tw',      '山丘調度', 'dispatcher', 'active',     '2025-04-01 09:00:00', NULL),
  (204, 1002, 'former@hill.tw',   '山丘離職', 'readonly',   'offboarded', '2025-04-10 09:00:00', '2026-03-05 00:00:00');

-- API 金鑰基準檢查時間點：2026-03-15 10:00:00
INSERT INTO merchant_api_keys (api_key_id, merchant_id, key_prefix, key_hash, scopes, created_at, expires_at, revoked_at, last_used_at) VALUES
  (1, 1001, 'sw_live_star', 'sha256_key_1_star_valid',   'shipments:read,shipments:write', '2026-01-01 00:00:00', '2026-12-31 23:59:59', NULL,                  '2026-03-15 09:50:00'), -- 有效
  (2, 1001, 'sw_live_old1', 'sha256_key_2_star_revoked', 'shipments:read,shipments:write', '2025-06-01 00:00:00', '2026-12-31 23:59:59', '2026-03-01 00:00:00', '2026-02-28 23:00:00'), -- 已撤銷但 expires_at 仍在未來（抓 AND/OR 優先序繞過）
  (3, 1002, 'sw_live_hill', 'sha256_key_3_hill_expired', 'shipments:read',                 '2025-03-01 00:00:00', '2026-03-01 00:00:00', NULL,                  '2026-02-25 12:00:00'), -- 已過期
  (4, 1003, 'sw_live_morn', 'sha256_key_4_morn_susp',    'shipments:read',                 '2026-01-15 00:00:00', NULL,                  NULL,                  '2026-02-10 10:00:00'), -- 所屬商家 1003 已停權
  (5, 1002, 'sw_live_h2',   'sha256_key_5_hill_noexp',   'shipments:read,billing:read',    '2026-02-01 00:00:00', NULL,                  NULL,                  '2026-03-14 18:00:00'); -- 有效（expires_at IS NULL 永不過期）

INSERT INTO drivers (driver_id, name, license_tier, home_warehouse_id, status) VALUES
  (501, '王志強', 'heavy',   11, 'active'),
  (502, '李建宏', 'regular', 11, 'active'),
  (503, '張育誠', 'hazmat',  21, 'suspended'), -- 已停權但仍留有未來班表
  (504, '林佩君', 'regular', 12, 'active');

-- 平台內部員工與 RBAC

INSERT INTO staff_accounts (staff_id, email, display_name, status, created_at, deleted_at) VALUES
  (301, 'audit@swift.tw',     '財務稽核 陳', 'active',     '2025-01-05 09:00:00', NULL),
  (302, 'ex.lead@swift.tw',   '前倉儲主管 吳', 'offboarded', '2024-06-01 09:00:00', '2026-03-01 00:00:00'),
  (303, 'dispatch@swift.tw',  '調度員 黃',   'active',     '2025-05-01 09:00:00', NULL),
  (304, 'bi@swift.tw',        '報表分析 李', 'active',     '2025-08-01 09:00:00', NULL);

INSERT INTO roles (role_id, role_code, description) VALUES
  (1, 'ops_dispatcher',  '排程調度員'),
  (2, 'warehouse_lead',  '倉儲主管'),
  (3, 'finance_auditor', '財務稽核員'),
  (4, 'bi_readonly',     '外部報表唯讀角色');

INSERT INTO permissions (perm_id, perm_code, resource, action) VALUES
  (1, 'shipments:read', 'shipments', 'read'),
  (2, 'dispatch:claim', 'dispatch',  'write'),
  (3, 'billing:audit',  'billing',   'read'),
  (4, 'pii:read',       'pii',       'read');

INSERT INTO role_permissions (role_id, perm_id) VALUES
  (1, 1), (1, 2),
  (2, 1), (2, 2), (2, 4),
  (3, 1), (3, 3),
  (4, 1);

INSERT INTO staff_roles (staff_role_id, staff_id, role_id, warehouse_scope_id, granted_at, expires_at, revoked_at) VALUES
  (1, 301, 3, NULL, '2025-01-05 09:00:00', NULL, NULL),
  (2, 302, 2, 11,   '2024-06-01 09:00:00', NULL, NULL), -- 離職後漏撤銷（仍帶 pii:read）
  (3, 303, 1, 11,   '2025-05-01 09:00:00', NULL, NULL),
  (4, 303, 1, 12,   '2025-05-01 09:00:00', NULL, NULL), -- 同一員工在兩個倉庫各持調度角色
  (5, 304, 4, NULL, '2025-08-01 09:00:00', NULL, NULL);

INSERT INTO shipments (shipment_id, merchant_id, warehouse_id, status, fee_cents, created_at) VALUES
  (7001, 1001, 11, 'delivered',  18000, '2026-03-10 08:00:00'),
  (7002, 1001, 11, 'delivered',  12000, '2026-03-10 09:00:00'),
  (7003, 1001, 12, 'returned',   25000, '2026-03-11 10:30:00'),
  (7004, 1002, 21, 'created',     9500, '2026-03-12 11:00:00'), -- 尚無任何掃描事件
  (7005, 1001, 11, 'in_transit', 15000, '2026-03-15 14:00:00'), -- 與 7006、7007 同秒
  (7006, 1002, 11, 'in_transit', 15000, '2026-03-15 14:00:00'),
  (7007, 1004, 11, 'in_transit', 21000, '2026-03-15 14:00:00'),
  (7008, 1001, 11, 'in_transit', 11000, '2026-03-14 14:00:00');

INSERT INTO shipment_packages (package_id, shipment_id, merchant_id, weight_grams, fragile) VALUES
  (7101, 7001, 1001, 1200, 0),
  (7102, 7001, 1001, 2400, 1), -- 7001 兩件包裹
  (7103, 7002, 1001,  800, 0),
  (7104, 7003, 1001, 3500, 1),
  (7105, 7004, 1002,  500, 0), -- 商家 1002 第 1 件包裹
  (7106, 7005, 1001, 1800, 0),
  (7107, 7006, 1002, 1600, 0), -- 商家 1002 第 2 件包裹
  (7108, 7007, 1004, 2200, 1),
  (7109, 7008, 1001,  950, 0);

INSERT INTO shipment_payloads (shipment_id, merchant_id, raw_waybill_json) VALUES
  (7001, 1001, '{"carrier":"swift","customs":{"hs_code":"4901.99"},"recipient_note":"警衛室代收"}'),
  (7002, 1001, '{"carrier":"swift","recipient_note":"週一至週五收件"}'),
  (7003, 1001, '{"carrier":"swift","return_reason":"收件人拒收"}'),
  (7004, 1002, '{"carrier":"swift","cod_amount":0}'),
  (7005, 1001, '{"carrier":"swift","temperature":"ambient"}'),
  (7006, 1002, '{"carrier":"swift","temperature":"ambient"}'),
  (7007, 1004, '{"carrier":"swift","fragile_seal":true}'),
  (7008, 1001, '{"carrier":"swift","temperature":"ambient"}');

INSERT INTO shipment_recipient_pii (shipment_id, merchant_id, recipient_name, recipient_phone, delivery_address, erased_at) VALUES
  (7001, 1001, '張小華', '+886933000701', '桃園市蘆竹區南崁路 1 號', NULL),
  (7002, 1001, '陳美玲', '+886933000702', '桃園市中壢區中山路 8 號', NULL),
  (7003, 1001, '林建國', '+886933000703', '新竹市東區光復路二段 5 號', NULL),
  (7004, 1002, '劉淑芬', '+886933000704', '台中市梧棲區台灣大道八段 9 號', NULL),
  (7005, 1001, '黃俊傑', '+886933000705', '桃園市桃園區中正路 20 號', NULL),
  (7006, 1002, '吳佩珊', '+886933000706', '桃園市八德區介壽路一段 15 號', NULL),
  (7007, 1004, '蔡明憲', '+886933000707', '桃園市平鎮區延平路 66 號', NULL),
  (7008, 1001, '鄭雅婷', '+886933000708', '桃園市龜山區復興一路 30 號', NULL);

INSERT INTO shipment_events (event_id, shipment_id, merchant_id, event_type, recorded_at) VALUES
  (8001, 7001, 1001, 'picked',    '2026-03-10 08:30:00'),
  (8002, 7001, 1001, 'exception', '2026-03-10 15:00:00'), -- 7001 同時含 exception 與 signed
  (8003, 7001, 1001, 'signed',    '2026-03-11 11:00:00'),
  (8004, 7002, 1001, 'signed',    '2026-03-10 18:00:00'),
  (8005, 7002, 1001, 'exception', NULL),                  -- recorded_at IS NULL，觸發 C03 反例
  (8006, 7003, 1001, 'picked',    '2026-03-11 11:00:00'),
  (8007, 7005, 1001, 'hub_in',    '2026-03-15 16:00:00'),
  (8008, NULL, NULL, 'exception', '2026-03-15 17:00:00'); -- 孤兒掃碼事件：shipment_id 與 merchant_id 皆為 NULL

INSERT INTO driver_shifts (shift_id, driver_id, route_code, starts_at, ends_at) VALUES
  (9001, 501, 'N-NIGHT-01', '2026-03-15 22:00:00', '2026-03-16 06:00:00'), -- 跨午夜班表
  (9002, 502, 'N-DAY-02',   '2026-03-15 08:00:00', '2026-03-15 16:00:00'),
  (9003, 502, 'N-DAY-02',   '2026-03-16 08:00:00', '2026-03-16 16:00:00'),
  (9004, 503, 'C-HAZ-01',   '2026-03-20 08:00:00', '2026-03-20 18:00:00'), -- 已停權司機的未來班表
  (9005, 504, 'N-DAY-03',   '2026-03-15 09:00:00', '2026-03-15 17:00:00');

INSERT INTO dispatch_tasks (task_id, shipment_id, merchant_id, status, claimed_by, priority, created_at) VALUES
  (9501, 7001, 1001, 'completed', 'disp-a', 5, '2026-03-10 08:05:00'),
  (9502, 7002, 1001, 'completed', 'disp-b', 4, '2026-03-10 09:05:00'),
  (9503, 7003, 1001, 'completed', 'disp-a', 8, '2026-03-11 10:35:00'),
  (9504, 7005, 1001, 'claimed',   'disp-a', 9, '2026-03-15 14:05:00'),
  (9505, 7006, 1002, 'queued',    NULL,     7, '2026-03-15 14:06:00'),
  (9506, 7007, 1004, 'queued',    NULL,     9, '2026-03-15 14:07:00');

INSERT INTO billing_statements (statement_id, merchant_id, period_month, total_cents, status) VALUES
  (9801, 1001, '2026-02', 420000, 'settled'),
  (9802, 1001, '2026-03',  81000, 'draft'),
  (9803, 1002, '2026-03',  24500, 'issued'),
  (9804, 1002, '2026-02',  31000, 'settled'),
  (9805, 1004, '2026-03',  21000, 'draft');

INSERT INTO billing_audit_logs (audit_id, statement_id, merchant_id, actor_type, actor_id, action, before_status, after_status, before_cents, after_cents, created_at) VALUES
  (1, 9801, 1001, 'system', 0,   'issued',  'draft',  'issued',  420000, 420000, '2026-03-01 00:05:00'),
  (2, 9801, 1001, 'staff',  301, 'settled', 'issued', 'settled', 420000, 420000, '2026-03-05 14:30:00');
