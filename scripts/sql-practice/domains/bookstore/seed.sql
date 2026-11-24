-- 領域甲（bookstore）：紙頁書店基準資料與邊界反例列（含 RBAC、軟刪除、PII 分離與稽核軌跡）
-- 刻意埋設：
-- 1. 顧客 3（雅文）從未下單；顧客 4（志明）2 月有單、3 月無單；顧客 5（怡君）city 為 NULL；顧客 6 city 為空字串且已完成個資抹除（erased：name、email 已清為 NULL，訂單 108 保留供對帳）
-- 2. 大小寫混排與重複 email（Alice@Example.com / alice@example.com）
-- 3. 訂單 101 有兩則評價（5 星 + 3 星），驗證列數膨脹與 <> 5 錯誤；訂單 102 無評價；評價 9004 的 order_id 為 NULL 且 5 星，驗證 NOT IN 回空
-- 4. 2026-03-09 10:00:00 同秒三筆訂單，驗證排序鍵不唯一與分頁漂移
-- 5. 訂單 101 同時有 2 筆明細與 2 張優惠券，驗證雙重一對多膨脹
-- 6. 門市 TPE-01 缺 2026-03-03（公休日），驗證 LAG() 與日曆前一天差異
-- 7. 書籍 205 stock = 1 模擬搶購限量書；書籍 206 is_active = 0 模擬下架書；書籍 209 為分類 2 的上架書但定價 250（低於 300），讓漏加括號的 AND/OR 條件多撈出它
-- 9. 母體約定：customers 含已抹除顧客 6，題目需求須寫明查的是「全部帳號（含已註銷）」還是「目前有效會員」（題目 JSON 的 population 欄位）
-- 8. 資安反例：員工 10 同時具 store_manager 與 auditor（皆有 orders:export，驗證 RBAC JOIN 重複膨脹）；員工 13 已離職軟刪除卻留有未撤銷角色且發起了排隊匯出任務 505（Confused Deputy）

PRAGMA foreign_keys = ON;

INSERT INTO customers (customer_id, name, email, city, status, deleted_at, created_at) VALUES
  (1, '佳穎', 'Alice@Example.com', 'Taipei',   'active', NULL,                  '2026-01-05 09:00:00'),
  (2, '宗翰', 'bob@example.com',   'Taichung', 'active', NULL,                  '2026-01-12 14:30:00'),
  (3, '雅文', 'yawen@example.com', 'Taipei',   'active', NULL,                  '2026-01-20 11:15:00'),
  (4, '志明', 'ming@example.com',  'Taipei',   'active', NULL,                  '2026-01-25 16:40:00'),
  (5, '怡君', 'alice@example.com', NULL,       'active', NULL,                  '2026-02-02 08:20:00'),
  (6, NULL,   NULL,                '',         'erased', '2026-03-19 00:00:00', '2026-02-14 19:05:00'), -- 已抹除：姓名與信箱清為 NULL
  (7, '宗翰', 'bob2@example.com',  'Kaohsiung','active', NULL,                  '2026-02-18 10:00:00'); -- 同名顧客，測試 GROUP BY name 錯併

INSERT INTO customer_pii (customer_id, phone_e164, shipping_address, tax_id, updated_at, erased_at) VALUES
  (1, '+886912000001', '台北市中正區重慶南路一段 10 號', NULL,       '2026-01-05 09:00:00', NULL),
  (2, '+886912000002', '台中市西區公益路 88 號',         '12345678', '2026-01-12 14:30:00', NULL),
  (3, '+886912000003', '台北市大安區和平東路二段 5 號',  NULL,       '2026-01-20 11:15:00', NULL),
  (4, '+886912000004', '台北市信義區松高路 12 號',       NULL,       '2026-01-25 16:40:00', NULL),
  (5, '+886912000005', NULL,                             NULL,       '2026-02-02 08:20:00', NULL),
  (6, NULL,            NULL,                             NULL,       '2026-03-19 00:00:00', '2026-03-19 00:00:00'), -- 已完成個資抹除
  (7, '+886912000007', '高雄市鼓山區美術東二路 3 號',    NULL,       '2026-02-18 10:00:00', NULL);

INSERT INTO categories (category_id, name, parent_id) VALUES
  (1, '技術書籍', NULL),
  (2, '後端工程', 1),
  (3, '資料工程', 1),
  (4, '文學小說', NULL),
  (5, '資料庫系統', 2);

INSERT INTO books (book_id, title, category_id, price, stock, is_active) VALUES
  (201, '關聯式資料庫核心', 5, 580, 25, 1),
  (202, 'SQL 查詢計畫實戰', 5, 450, 12, 1),
  (203, '分散式系統設計',   2, 600, 18, 1),
  (204, '資料倉儲建模指南', 3, 300, 30, 1),
  (205, '簽名限量版：索引解剖', 5, 600, 1, 1), -- 同價 600 + 限量庫存 1
  (206, '舊版系統維運手冊', 2, 420, 0, 0),     -- 已下架書籍
  (207, '都市短篇選',       4, 280, 40, 1),
  (208, 'SQLite 嵌入式實作', 5, 450, 15, 1),   -- 同價 450，供平手排序驗證
  (209, '後端工程入門小冊', 2, 250, 50, 1);    -- 分類 2 上架但低於 300 元，AND/OR 漏括號時被多撈出

INSERT INTO orders (order_id, customer_id, status, total_amount, ordered_at) VALUES
  (101, 1, 'paid',      900,  '2026-03-02 10:00:00'),
  (102, 1, 'paid',      500,  '2026-03-09 10:00:00'), -- 與 103、104 同秒
  (103, 2, 'shipped',   500,  '2026-03-09 10:00:00'),
  (104, 1, 'refunded',  500,  '2026-03-09 10:00:00'),
  (105, 4, 'paid',      580,  '2026-02-15 15:20:00'), -- 2 月有單、3 月無單
  (106, 2, 'pending',   450,  '2026-03-01 08:00:00'), -- 逾時未付款
  (107, 5, 'paid',      300,  '2026-03-31 22:30:00'), -- 月底深夜，測試 BETWEEN '2026-03-31' 漏列
  (108, 6, 'cancelled', 600,  '2026-03-18 12:00:00'),
  (109, 7, 'paid',      300,  '2026-03-20 09:30:00'); -- 與 107 同金額 300

INSERT INTO order_items (order_item_id, order_id, book_id, quantity, unit_price) VALUES
  (1001, 101, 201, 1, 550), -- 歷史成交價 550（現價已調為 580）
  (1002, 101, 202, 1, 350), -- 同一訂單兩筆明細
  (1003, 102, 203, 1, 500),
  (1004, 103, 202, 1, 500),
  (1005, 104, 201, 1, 500),
  (1006, 105, 201, 1, 580),
  (1007, 106, 202, 1, 450),
  (1008, 107, 204, 1, 300),
  (1009, 108, 203, 1, 600),
  (1010, 109, 204, 1, 300);

INSERT INTO reviews (review_id, order_id, book_id, rating, created_at) VALUES
  (9001, 101,  201, 5, '2026-03-04 12:00:00'), -- 訂單 101 第一則：5 星
  (9002, 101,  202, 3, '2026-03-05 18:00:00'), -- 訂單 101 第二則：3 星（5 星與非 5 星並存）
  (9003, 105,  201, 5, '2026-03-06 09:00:00'), -- 2 月下單、3 月才評價
  (9004, NULL, 203, 5, '2026-03-10 14:00:00'), -- 異常匯入：order_id 為 NULL 且 5 星
  (9005, 103,  202, 4, '2026-03-12 20:00:00'); -- 僅有 4 星評價（沒有 5 星）

INSERT INTO coupons (coupon_id, code, discount_type, discount_val, expires_at, is_active) VALUES
  (301, 'SPRING100', 'fixed',   100, '2026-03-31 23:59:59', 1),
  (302, 'VIP10',     'percent', 10,  '2026-06-30 23:59:59', 1),
  (303, 'OLD2025',   'fixed',   50,  '2025-12-31 23:59:59', 1); -- 已過期仍標啟用，待批次停用

INSERT INTO order_coupons (order_id, coupon_id) VALUES
  (101, 301),
  (101, 302), -- 訂單 101 用兩張券 + 兩筆明細 = 雙重一對多膨脹
  (105, 303); -- 過期券仍有歷史關聯

INSERT INTO daily_sales_snapshots (snapshot_date, store_code, revenue) VALUES
  ('2026-03-01', 'TPE-01', 12000),
  ('2026-03-02', 'TPE-01', 15000),
  -- TPE-01 刻意缺 2026-03-03（週二公休）
  ('2026-03-04', 'TPE-01', 18000), -- 比 03-02 高，但日曆前一天 03-03 缺測
  ('2026-03-05', 'TPE-01', 16000),
  ('2026-03-01', 'TXG-01', 9000),
  ('2026-03-02', 'TXG-01', 8500),
  ('2026-03-03', 'TXG-01', 11000),
  ('2026-03-04', 'TXG-01', 10500);

-- 員工、RBAC 角色權限與唯附寫稽核紀錄

INSERT INTO staff_accounts (staff_id, email, display_name, store_code, status, created_at, deleted_at) VALUES
  (10, 'mgr.tpe@bookstore.tw',     '林店長',   'TPE-01', 'active',     '2025-01-10 09:00:00', NULL),
  (11, 'clerk.tpe@bookstore.tw',   '陳店員',   'TPE-01', 'active',     '2025-03-01 09:00:00', NULL),
  (12, 'analyst@bookstore.tw',     '黃分析',   'HQ',     'active',     '2025-06-15 09:00:00', NULL),
  (13, 'ex.mgr@bookstore.tw',      '周前主管', 'TPE-01', 'offboarded', '2024-05-01 09:00:00', '2026-03-10 00:00:00'), -- 已軟刪除離職員工
  (14, 'revoked.mgr@bookstore.tw', '許轉調',   'TXG-01', 'active',     '2025-02-01 09:00:00', NULL);

INSERT INTO roles (role_id, role_code, description) VALUES
  (1, 'store_clerk',   '門市店員：一般訂單查詢'),
  (2, 'store_manager', '門市主管：訂單匯出與退款核准'),
  (3, 'analyst',       '數據分析師：去識別化報表與匯出'),
  (4, 'auditor',       '稽核員：唯讀稽核軌跡與報表匯出');

INSERT INTO permissions (perm_id, perm_code, resource, action) VALUES
  (1, 'orders:read',   'orders', 'read'),
  (2, 'orders:export', 'orders', 'export'),
  (3, 'orders:refund', 'orders', 'refund'),
  (4, 'pii:read',      'pii',    'read'),
  (5, 'audit:read',    'audit',  'read');

INSERT INTO role_permissions (role_id, perm_id) VALUES
  (1, 1),
  (2, 1), (2, 2), (2, 3), (2, 4),
  (3, 1), (3, 2),
  (4, 1), (4, 2), (4, 5);

INSERT INTO staff_roles (staff_role_id, staff_id, role_id, store_scope, granted_at, expires_at, revoked_at) VALUES
  (1, 10, 2, 'TPE-01', '2025-01-10 09:00:00', NULL,                  NULL), -- 員工 10 同時具 store_manager 與 auditor
  (2, 10, 4, NULL,     '2025-09-01 09:00:00', NULL,                  NULL), -- 雙角色皆有 orders:export（測試 RBAC JOIN 重複膨脹）
  (3, 11, 1, 'TPE-01', '2025-03-01 09:00:00', NULL,                  NULL), -- 僅有 orders:read
  (4, 12, 3, NULL,     '2025-06-15 09:00:00', NULL,                  NULL),
  (5, 13, 2, 'TPE-01', '2024-05-01 09:00:00', NULL,                  NULL), -- 離職後漏撤銷角色列（經典離職治理缺口）
  (6, 14, 2, 'TXG-01', '2025-02-01 09:00:00', NULL,                  '2026-03-18 00:00:00'), -- 角色已被撤銷
  (7, 11, 2, 'TPE-01', '2026-03-01 09:00:00', '2026-03-14 23:59:59', NULL); -- 店員 11 的代理主管授權已到期但未撤銷（v_active_staff_permissions 不濾 expires_at 的反例）

INSERT INTO order_audit_logs (audit_id, order_id, actor_staff_id, actor_role, action, before_status, after_status, before_amount, after_amount, reason, created_at) VALUES
  (1, 101, 10, 'store_manager', 'status_change',   'pending', 'paid',     900, 900, '門市臨櫃確認入帳', '2026-03-02 10:05:00'),
  (2, 104, 10, 'store_manager', 'refund_approved', 'paid',    'refunded', 500, 500, '瑕疵退書核准全額退款', '2026-03-10 11:20:00');

INSERT INTO export_jobs (job_id, status, payload, claimed_by, requested_by_staff_id, scope_store_code, created_at) VALUES
  (501, 'done',    '{"report":"feb_sales"}', 'worker-1', 10, 'TPE-01', '2026-03-01 01:00:00'),
  (502, 'done',    '{"report":"feb_tax"}',   'worker-2', 12, NULL,     '2026-03-01 01:05:00'),
  (503, 'running', '{"report":"mar_mid"}',   'worker-1', 10, 'TPE-01', '2026-03-15 02:00:00'),
  (504, 'queued',  '{"report":"mar_sales"}', NULL,       10, 'TPE-01', '2026-03-20 03:00:00'), -- 合法在職主管（雙角色）請求
  (505, 'queued',  '{"report":"mar_audit"}', NULL,       13, 'TPE-01', '2026-03-20 03:01:00'), -- 已離職軟刪除員工請求（Confused Deputy 反例）
  (506, 'failed',  '{"report":"bad_range"}', 'worker-2', 14, 'TXG-01', '2026-03-19 04:00:00'); -- 已撤銷角色員工請求

INSERT INTO store_shifts (shift_id, staff_id, store_code, starts_at, ends_at) VALUES
  (601, 10, 'TPE-01', '2026-03-20 09:00:00', '2026-03-20 17:00:00'),
  (602, 10, 'TPE-01', '2026-03-21 09:00:00', '2026-03-21 17:00:00'),
  (603, 11, 'TPE-01', '2026-03-20 14:00:00', '2026-03-20 22:00:00');

INSERT INTO book_details (book_id, synopsis_md, specs_json) VALUES
  (201, '深入剖析關聯代數、儲存頁結構、MVCC 與交易隔離實作細節。', '{"pages":512,"binding":"paperback","isbn":"978-986-000-201-1"}'),
  (202, '從 EXPLAIN 輸出、基數估計到複合索引前導欄位的完整案例拆解。', '{"pages":368,"binding":"paperback","isbn":"978-986-000-202-8"}'),
  (203, '涵蓋複製、分區、共識演算法與跨區域一致性取捨。', '{"pages":624,"binding":"hardcover","isbn":"978-986-000-203-5"}'),
  (204, '星狀結構、緩慢變動維度與批次對帳管線設計。', '{"pages":410,"binding":"paperback","isbn":"978-986-000-204-2"}'),
  (205, '限量精裝附索引結構摺頁圖。', '{"pages":296,"binding":"hardcover","limited_edition":true}'),
  (206, '歷史系統維運與舊版工具整理。', '{"pages":320,"binding":"paperback","out_of_print":true}'),
  (207, '十二篇以台北捷運沿線為背景的短篇小說。', '{"pages":240,"binding":"paperback"}'),
  (208, '嵌入式單機資料庫 WAL 模式與連線池最佳實務。', '{"pages":310,"binding":"epub","drm":"none"}'),
  (209, 'HTTP、資料庫連線與部署的入門導覽。', '{"pages":96,"binding":"paperback"}');

INSERT INTO book_view_events (view_id, book_id, viewed_at) VALUES
  (8001, 201, '2026-03-20 10:00:01'),
  (8002, 201, '2026-03-20 10:00:01'),
  (8003, 201, '2026-03-20 10:00:02'),
  (8004, 202, '2026-03-20 10:01:10'),
  (8005, 205, '2026-03-20 10:02:00');
