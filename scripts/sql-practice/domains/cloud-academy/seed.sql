-- 領域乙（cloud-academy）：雲課堂基準資料與邊界反例列
-- 刻意埋設：
-- 1. 學員 1（林欣）有兩筆訂閱（先 canceled 再 active）與多張帳單、多筆進度（雙重一對多膨脹）
-- 2. 學員 3（陳宇）從未訂閱；學員 4（周安）有訂閱但從未觀看任何課程；學員 5（吳琪）country 為 NULL
-- 3. 訂閱 2002 同時有一筆 paid 與一筆 void 帳單；訂閱 2003 從未開立任何帳單；帳單 3005 的 sub_id 為 NULL 且 paid（觸發 NOT IN 陷阱）
-- 4. 課程 104 未掛任何標籤；課程 105 未發布（is_published = 0）；課程階層 101 -> 102 -> 103
-- 5. lesson_progress 含 completed_at IS NULL（看一半未完課），驗證 NULL 排序與計數
-- 6. webhook_events 含重複的 (stripe, evt_dup_001) 模擬金流重送

PRAGMA foreign_keys = ON;

INSERT INTO users (user_id, display_name, email, country, joined_at) VALUES
  (1, '林欣', 'Xin@Academy.io',  'TW', '2026-01-02 09:00:00'),
  (2, '張哲', 'zhe@academy.io',  'JP', '2026-01-10 12:00:00'),
  (3, '陳宇', 'yu@academy.io',   'TW', '2026-01-18 15:00:00'), -- 從未訂閱
  (4, '周安', 'an@academy.io',   'SG', '2026-02-01 08:30:00'), -- 有訂閱無學習紀錄
  (5, '吳琪', 'xin@academy.io',  NULL, '2026-02-12 20:00:00'), -- 大小寫相異同信箱 + country IS NULL
  (6, '林欣', 'xin2@academy.io', 'TW', '2026-03-01 10:00:00'); -- 同名學員

INSERT INTO courses (course_id, title, track, prerequisite_id, monthly_fee_tier, is_published) VALUES
  (101, 'SQL 語意模型入門',     'backend', NULL, 1, 1),
  (102, 'PostgreSQL 效能調校',  'backend', 101,  2, 1),
  (103, '分散式交易與隔離等級', 'backend', 102,  3, 1),
  (104, '分析型查詢與視窗實戰', 'data',    101,  2, 1), -- 刻意不掛標籤
  (105, '草稿：雲端成本監控',   'devops',  NULL, 2, 0), -- 未發佈草稿課
  (106, '容器部署基礎',         'devops',  NULL, 1, 1);

INSERT INTO course_contents (course_id, syllabus_md, metadata_json) VALUES
  (101, '第一章：宣告式思維；第二章：連接與空值；第三章：分組與視窗。', '{"lessons":12,"subtitles":["zh-TW","en"]}'),
  (102, '第一章：執行計畫判讀；第二章：複合索引與部分索引；第三章：統計資訊。', '{"lessons":15,"subtitles":["zh-TW"]}'),
  (103, '第一章：MVCC 與鎖；第二章：SKIP LOCKED；第三章：排除約束。', '{"lessons":10,"subtitles":["zh-TW","en"]}'),
  (104, '第一章：LAG/LEAD 時間序列；第二章：分頁全序；第三章：對帳。', '{"lessons":8,"subtitles":["zh-TW"]}'),
  (105, '草稿規劃中。', '{"lessons":0,"subtitles":[]}'),
  (106, '第一章：映像建置；第二章：健康檢查；第三章：日誌收集。', '{"lessons":9,"subtitles":["zh-TW"]}');

INSERT INTO tags (tag_id, name) VALUES
  (1, 'sql'),
  (2, 'performance'),
  (3, 'concurrency'),
  (4, 'containers');

INSERT INTO course_tags (course_id, tag_id) VALUES
  (101, 1),
  (102, 1),
  (102, 2),
  (103, 1),
  (103, 3),
  (106, 4);

INSERT INTO subscriptions (sub_id, user_id, plan_code, status, started_at, ended_at) VALUES
  (2001, 1, 'pro',  'canceled', '2026-01-05 10:00:00', '2026-02-05 10:00:00'),
  (2002, 1, 'team', 'active',   '2026-02-10 10:00:00', NULL), -- 同一學員第二筆訂閱
  (2003, 2, 'pro',  'active',   '2026-03-01 09:00:00', NULL), -- 尚無任何帳單的 active 訂閱
  (2004, 4, 'pro',  'trialing', '2026-02-20 09:00:00', NULL), -- 逾時試用中
  (2005, 5, 'free', 'active',   '2026-02-15 11:00:00', NULL),
  (2006, 6, 'pro',  'past_due', '2026-02-01 11:00:00', NULL);

INSERT INTO invoices (invoice_id, sub_id, amount, status, issued_at) VALUES
  (3001, 2001, 990,  'paid',     '2026-01-05 10:00:00'),
  (3002, 2002, 2900, 'paid',     '2026-02-10 10:00:00'),
  (3003, 2002, 2900, 'void',     '2026-03-10 10:00:00'), -- 同一訂閱含 paid 與 void
  (3004, 2002, 2900, 'paid',     '2026-03-11 10:00:00'),
  (3005, NULL, 1500, 'paid',     '2026-03-12 09:00:00'), -- 歷史補單：sub_id IS NULL 且 paid
  (3006, 2006, 990,  'open',     '2026-03-01 11:00:00'),
  (3007, 2001, 990,  'refunded', '2026-02-06 10:00:00');

INSERT INTO lesson_progress (progress_id, user_id, course_id, lesson_no, completed_at, watch_seconds) VALUES
  (4001, 1, 101, 1, '2026-01-06 20:00:00', 1200),
  (4002, 1, 101, 2, '2026-01-07 20:00:00', 1500),
  (4003, 1, 102, 1, NULL,                  480),  -- 看一半未完課
  (4004, 2, 101, 1, '2026-03-02 21:00:00', 1200), -- 同 1200 秒，供平手驗證
  (4005, 2, 104, 1, NULL,                  300),
  (4006, 5, 106, 1, '2026-02-20 19:00:00', 900);

INSERT INTO certificates (cert_id, user_id, course_id, issued_at) VALUES
  (5001, 1, 101, '2026-01-20 12:00:00'),
  (5002, 5, 106, '2026-03-05 12:00:00');

INSERT INTO webhook_events (event_id, provider, external_id, status, received_at) VALUES
  (6001, 'stripe',   'evt_dup_001', 'done',       '2026-03-10 10:00:01'),
  (6002, 'stripe',   'evt_dup_001', 'pending',    '2026-03-10 10:00:03'), -- 重送事件
  (6003, 'newebpay', 'np_9001',     'processing', '2026-03-11 10:00:00'),
  (6004, 'stripe',   'evt_002',     'pending',    '2026-03-12 09:05:00'),
  (6005, 'stripe',   'evt_003',     'dead',       '2026-03-09 08:00:00');
