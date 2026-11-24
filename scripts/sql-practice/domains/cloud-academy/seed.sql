-- 領域乙（cloud-academy）：雲課堂基準資料與邊界反例列（含企業多租戶、憑證／Session 失效、PII 與稽核）
-- 刻意埋設：
-- 1. 學員 1（林欣）有兩筆訂閱（先 canceled 再 active 企業版 org 501）與多張帳單、多筆進度（雙重一對多膨脹）
-- 2. 學員 3（陳宇）從未訂閱；學員 4（周安）有訂閱無學習紀錄且帳號遭鎖定（locked）卻留有未過期 session 704；學員 5（吳琪）country 為 NULL
-- 3. 訂閱 2002 同時有一筆 paid 與一筆 void 帳單；訂閱 2003 從未開立任何帳單；帳單 3005 的 sub_id 為 NULL 且 paid（觸發 NOT IN 陷阱）
-- 4. 課程 104 未掛任何標籤；課程 105 未發布（is_published = 0）；課程階層 101 -> 102 -> 103
-- 5. lesson_progress 含 completed_at IS NULL（看一半未完課），驗證 NULL 排序與計數
-- 6. webhook_events 含重複的 (stripe, evt_dup_001) 與驗簽失敗的死信 6005（signature_valid = 0）
-- 7. 資安反例：學員 1 於 2026-03-10 12:00:00 變更密碼，但密碼變更前簽發的 session 701 尚未過期也未標記 revoked_at（驗證 Session 失效複合陷阱）

PRAGMA foreign_keys = ON;

INSERT INTO users (user_id, display_name, email, country, status, deleted_at, joined_at) VALUES
  (1, '林欣', 'Xin@Academy.io',  'TW', 'active', NULL, '2026-01-02 09:00:00'),
  (2, '張哲', 'zhe@academy.io',  'JP', 'active', NULL, '2026-01-10 12:00:00'),
  (3, '陳宇', 'yu@academy.io',   'TW', 'active', NULL, '2026-01-18 15:00:00'), -- 從未訂閱
  (4, '周安', 'an@academy.io',   'SG', 'locked', NULL, '2026-02-01 08:30:00'), -- 帳號鎖定且留有未過期 session
  (5, '吳琪', 'xin@academy.io',  NULL, 'active', NULL, '2026-02-12 20:00:00'), -- 大小寫相異同信箱 + country IS NULL
  (6, '林欣', 'xin2@academy.io', 'TW', 'active', NULL, '2026-01-25 10:00:00'); -- 同名學員（加入時間早於訂閱 2006 開始）

INSERT INTO user_pii (user_id, legal_name, phone_e164, billing_address, erased_at) VALUES
  (1, '林欣怡', '+886922000001', '台北市松山區南京東路四段 1 號', NULL),
  (2, '張哲維', '+819012340002', 'Tokyo Shibuya-ku 1-2-3',       NULL),
  (3, '陳宇軒', '+886922000003', NULL,                           NULL),
  (4, '周安平', '+6591230004',   'Singapore Marina Blvd 8',      NULL),
  (5, '吳琪芳', '+886922000005', NULL,                           NULL),
  (6, '林欣儒', '+886922000006', '新北市板橋區文化路一段 9 號',  NULL);

INSERT INTO user_credentials (user_id, password_hash, mfa_enabled, failed_attempts, locked_until, password_changed_at) VALUES
  (1, '$argon2id$v=19$m=65536$mock_hash_u1', 1, 0, NULL,                  '2026-03-10 12:00:00'), -- 曾重設密碼
  (2, '$argon2id$v=19$m=65536$mock_hash_u2', 1, 0, NULL,                  '2026-01-10 12:00:00'),
  (3, '$argon2id$v=19$m=65536$mock_hash_u3', 0, 0, NULL,                  '2026-01-18 15:00:00'),
  (4, '$argon2id$v=19$m=65536$mock_hash_u4', 0, 6, '2026-03-25 12:00:00', '2026-02-01 08:30:00'), -- 多次錯密碼遭鎖定
  (5, '$argon2id$v=19$m=65536$mock_hash_u5', 0, 0, NULL,                  '2026-02-12 20:00:00'),
  (6, '$argon2id$v=19$m=65536$mock_hash_u6', 0, 1, NULL,                  '2026-03-01 10:00:00');

-- 基準檢查時間點：2026-03-15 10:00:00
INSERT INTO user_sessions (session_id, user_id, token_hash, ip_addr, created_at, expires_at, revoked_at) VALUES
  (701, 1, 'sha256_sess_701_stolen',  '203.0.113.10', '2026-03-09 08:00:00', '2026-03-20 08:00:00', NULL),                  -- 密碼變更前簽發的舊 session（應失效）
  (702, 1, 'sha256_sess_702_valid',   '198.51.100.1', '2026-03-10 12:05:00', '2026-03-20 12:05:00', NULL),                  -- 唯一完全合法的有效 session
  (703, 2, 'sha256_sess_703_revoked', '198.51.100.2', '2026-03-05 10:00:00', '2026-03-20 10:00:00', '2026-03-11 09:00:00'), -- 已主動登出撤銷
  (704, 4, 'sha256_sess_704_locked',  '198.51.100.4', '2026-03-12 09:00:00', '2026-03-20 09:00:00', NULL),                  -- 帳號已被鎖定（users.status = 'locked'）
  (705, 5, 'sha256_sess_705_expired', '198.51.100.5', '2026-03-01 09:00:00', '2026-03-12 09:00:00', NULL);                  -- 已過期

INSERT INTO organizations (org_id, slug, name, status, created_at) VALUES
  (501, 'acme-corp', '艾克米科技股份有限公司', 'active', '2026-02-01 09:00:00'),
  (502, 'beta-labs', '貝塔實驗室有限公司',     'active', '2026-02-15 09:00:00');

INSERT INTO org_memberships (org_id, user_id, org_role, status, joined_at, revoked_at) VALUES
  (501, 1, 'admin',  'active',  '2026-02-01 09:00:00', NULL),
  (501, 2, 'member', 'revoked', '2026-02-05 09:00:00', '2026-03-08 00:00:00'), -- 已移出組織 501
  (502, 2, 'owner',  'active',  '2026-02-15 09:00:00', NULL),
  (502, 5, 'member', 'active',  '2026-02-16 09:00:00', NULL);

INSERT INTO roles (role_id, role_code, description) VALUES
  (1, 'learner',        '一般學員'),
  (2, 'instructor',     '課程講師'),
  (3, 'bi_analyst',     '數據分析師（僅讀假名化檢視表）'),
  (4, 'platform_admin', '平台維運管理員');

INSERT INTO permissions (perm_id, perm_code, resource, action) VALUES
  (1, 'courses:read',    'courses',  'read'),
  (2, 'courses:publish', 'courses',  'write'),
  (3, 'analytics:read',  'analytics','read'),
  (4, 'users:admin',     'users',    'admin'),
  (5, 'billing:refund',  'billing',  'write');

INSERT INTO role_permissions (role_id, perm_id) VALUES
  (1, 1),
  (2, 1), (2, 2),
  (3, 3),
  (4, 1), (4, 3), (4, 4), (4, 5);

INSERT INTO user_roles (user_role_id, user_id, role_id, granted_at, expires_at, revoked_at) VALUES
  (1, 1, 1, '2026-01-02 09:00:00', NULL, NULL),
  (2, 1, 2, '2026-02-01 09:00:00', NULL, NULL),
  (3, 2, 1, '2026-01-10 12:00:00', NULL, NULL),
  (4, 3, 3, '2026-01-18 15:00:00', NULL, NULL),
  (5, 6, 4, '2026-03-01 10:00:00', NULL, '2026-03-10 00:00:00'), -- 臨時管理員權限已撤銷
  (6, 2, 2, '2026-02-15 09:00:00', '2026-03-01 00:00:00', NULL); -- 客座講師授權已到期但未撤銷

INSERT INTO permission_audit_logs (audit_id, org_id, actor_user_id, target_user_id, event_action, before_role, after_role, created_at) VALUES
  (1, 501, 1, 2, 'org_member_removed', 'member', NULL, '2026-03-08 00:00:00'),
  (2, NULL, 1, 1, 'password_reset',    NULL,     NULL, '2026-03-10 12:00:00');

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

INSERT INTO subscriptions (sub_id, user_id, org_id, plan_code, status, started_at, ended_at) VALUES
  (2001, 1, NULL, 'pro',  'canceled', '2026-01-05 10:00:00', '2026-02-05 10:00:00'),
  (2002, 1, 501,  'team', 'active',   '2026-02-10 10:00:00', NULL), -- 企業版綁定 org 501
  (2003, 2, NULL, 'pro',  'active',   '2026-03-01 09:00:00', NULL), -- 尚無任何帳單的 active 訂閱
  (2004, 4, NULL, 'pro',  'trialing', '2026-02-20 09:00:00', NULL), -- 逾時試用中
  (2005, 5, NULL, 'free', 'active',   '2026-02-15 11:00:00', NULL),
  (2006, 6, NULL, 'pro',  'past_due', '2026-02-01 11:00:00', NULL);

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

INSERT INTO webhook_events (event_id, provider, external_id, status, signature_valid, source_ip, received_at) VALUES
  (6001, 'stripe',   'evt_dup_001', 'done',       1, '54.187.205.235', '2026-03-10 10:00:01'),
  (6002, 'stripe',   'evt_dup_001', 'pending',    1, '54.187.205.235', '2026-03-10 10:00:03'), -- 重送事件
  (6003, 'newebpay', 'np_9001',     'processing', 1, '211.72.249.10',  '2026-03-11 10:00:00'),
  (6004, 'stripe',   'evt_002',     'pending',    1, '54.187.205.235', '2026-03-12 09:05:00'),
  (6005, 'stripe',   'evt_003',     'dead',       0, '198.51.100.99',  '2026-03-09 08:00:00'); -- 偽造簽章死信
