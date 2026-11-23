-- 領域甲（bookstore）：紙頁書店基準資料與邊界反例列
-- 刻意埋設：
-- 1. 顧客 3（雅文）從未下單；顧客 4（志明）2 月有單、3 月無單；顧客 5（怡君）city 為 NULL；顧客 6（冠宇）city 為空字串
-- 2. 大小寫混排與重複 email（Alice@Example.com / alice@example.com）
-- 3. 訂單 101 有兩則評價（5 星 + 3 星），驗證列數膨脹與 <> 5 錯誤；訂單 102 無評價；評價 9004 的 order_id 為 NULL 且 5 星，驗證 NOT IN 回空
-- 4. 2026-03-09 10:00:00 同秒三筆訂單，驗證排序鍵不唯一與分頁漂移
-- 5. 訂單 101 同時有 2 筆明細與 2 張優惠券，驗證雙重一對多膨脹
-- 6. 門市 TPE-01 缺 2026-03-03（公休日），驗證 LAG() 與日曆前一天差異
-- 7. 書籍 205 stock = 1 模擬搶購限量書；書籍 206 is_active = 0 模擬下架書

PRAGMA foreign_keys = ON;

INSERT INTO customers (customer_id, name, email, city, created_at) VALUES
  (1, '佳穎', 'Alice@Example.com', 'Taipei',   '2026-01-05 09:00:00'),
  (2, '宗翰', 'bob@example.com',   'Taichung', '2026-01-12 14:30:00'),
  (3, '雅文', 'yawen@example.com', 'Taipei',   '2026-01-20 11:15:00'),
  (4, '志明', 'ming@example.com',  'Taipei',   '2026-01-25 16:40:00'),
  (5, '怡君', 'alice@example.com', NULL,       '2026-02-02 08:20:00'),
  (6, '冠宇', 'kuanyu@example.com','',         '2026-02-14 19:05:00'),
  (7, '宗翰', 'bob2@example.com',  'Kaohsiung','2026-02-18 10:00:00'); -- 同名顧客，測試 GROUP BY name 錯併

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
  (208, 'SQLite 嵌入式實作', 5, 450, 15, 1);   -- 同價 450，供平手排序驗證

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

INSERT INTO export_jobs (job_id, status, payload, claimed_by, created_at) VALUES
  (501, 'done',    '{"report":"feb_sales"}', 'worker-1', '2026-03-01 01:00:00'),
  (502, 'done',    '{"report":"feb_tax"}',   'worker-2', '2026-03-01 01:05:00'),
  (503, 'running', '{"report":"mar_mid"}',   'worker-1', '2026-03-15 02:00:00'),
  (504, 'queued',  '{"report":"mar_sales"}', NULL,       '2026-03-20 03:00:00'),
  (505, 'queued',  '{"report":"mar_audit"}', NULL,       '2026-03-20 03:01:00'),
  (506, 'failed',  '{"report":"bad_range"}', 'worker-2', '2026-03-19 04:00:00');

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
  (208, '嵌入式單機資料庫 WAL 模式與連線池最佳實務。', '{"pages":310,"binding":"epub","drm":"none"}');

INSERT INTO book_view_events (view_id, book_id, viewed_at) VALUES
  (8001, 201, '2026-03-20 10:00:01'),
  (8002, 201, '2026-03-20 10:00:01'),
  (8003, 201, '2026-03-20 10:00:02'),
  (8004, 202, '2026-03-20 10:01:10'),
  (8005, 205, '2026-03-20 10:02:00');
