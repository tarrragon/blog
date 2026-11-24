-- 領域甲（bookstore）：紙頁書店線上書城與門市系統（正式環境資安與權限完整模型）
-- 引擎基準：SQLite 3.43+（STRICT 表需 3.37+）。本檔使用 SQLite 專用語法（STRICT、RAISE(ABORT)），
-- 不能直接在 PostgreSQL 執行；PostgreSQL 18 對應 DDL 見 schema_pg.sql，角色、GRANT 與 RLS 見 security_pg.sql。
--
-- 全檔約定：
-- 1. 所有表宣告 STRICT：SQLite 預設的型別親和性會讓 'abc' 通過 CHECK (price >= 0)（文字恆大於數字），STRICT 改為寫入時報錯，與 PostgreSQL 的型別檢查一致。
-- 2. 時間欄位一律存 'YYYY-MM-DD HH:MM:SS'（UTC，無時區後綴）文字，並以 GLOB 檢查格式；字串比較的正確性依賴固定格式。
-- 3. 金額欄位一律為新台幣整數元（無小數）。
-- 4. 軟刪除欄位 deleted_at 與 status 以表級 CHECK 綁定，兩欄不可漂移。

PRAGMA foreign_keys = ON;

-- 營運初期：核心銷售與評價

CREATE TABLE customers (
  customer_id INTEGER PRIMARY KEY,
  name        TEXT, -- 個資抹除（status = 'erased'）後清為 NULL，其餘狀態必填
  email       TEXT, -- 同上；刻意不設 UNIQUE，保留大小寫重複信箱反例
  city        TEXT, -- 允許 NULL 供未填寫地址反例驗證
  status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'erased')),
  deleted_at  TEXT CHECK (deleted_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  created_at  TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  CHECK ((status = 'erased') = (deleted_at IS NOT NULL)),
  CHECK (status = 'erased' OR (name IS NOT NULL AND email IS NOT NULL)),
  CHECK (status <> 'erased' OR (name IS NULL AND email IS NULL))
) STRICT;

CREATE TABLE customer_pii (
  customer_id      INTEGER PRIMARY KEY REFERENCES customers(customer_id),
  phone_e164       TEXT,
  shipping_address TEXT,
  tax_id           TEXT,
  updated_at       TEXT NOT NULL CHECK (updated_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  erased_at        TEXT CHECK (erased_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'), -- GDPR／個資刪除請求後抹除明文欄位並留下抹除時間
  CHECK (erased_at IS NULL OR (phone_e164 IS NULL AND shipping_address IS NULL AND tax_id IS NULL))
) STRICT;

CREATE TABLE categories (
  category_id INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  parent_id   INTEGER REFERENCES categories(category_id)
) STRICT;

CREATE TABLE books (
  book_id     INTEGER PRIMARY KEY,
  title       TEXT NOT NULL,
  category_id INTEGER NOT NULL REFERENCES categories(category_id),
  price       INTEGER NOT NULL CHECK (price >= 0),
  stock       INTEGER NOT NULL CHECK (stock >= 0),
  is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
) STRICT;

CREATE TABLE orders (
  order_id     INTEGER PRIMARY KEY,
  customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),
  status       TEXT NOT NULL CHECK (status IN ('pending', 'paid', 'shipped', 'cancelled', 'refunded')),
  total_amount INTEGER NOT NULL CHECK (total_amount >= 0),
  ordered_at   TEXT NOT NULL CHECK (ordered_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]')
) STRICT;

CREATE TABLE order_items (
  order_item_id INTEGER PRIMARY KEY,
  order_id      INTEGER NOT NULL REFERENCES orders(order_id),
  book_id       INTEGER NOT NULL REFERENCES books(book_id),
  quantity      INTEGER NOT NULL CHECK (quantity > 0),
  unit_price    INTEGER NOT NULL CHECK (unit_price >= 0)
) STRICT;

CREATE TABLE reviews (
  review_id  INTEGER PRIMARY KEY,
  order_id   INTEGER REFERENCES orders(order_id), -- 刻意允許 NULL 模擬匯入缺漏資料
  book_id    INTEGER NOT NULL REFERENCES books(book_id),
  rating     INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
  created_at TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]')
) STRICT;

-- 營運成長期：行銷、對帳與效能壓力

CREATE TABLE coupons (
  coupon_id     INTEGER PRIMARY KEY,
  code          TEXT NOT NULL,
  discount_type TEXT NOT NULL CHECK (discount_type IN ('fixed', 'percent')),
  discount_val  INTEGER NOT NULL CHECK (discount_val > 0),
  expires_at    TEXT NOT NULL CHECK (expires_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
) STRICT;

CREATE TABLE order_coupons (
  order_id  INTEGER NOT NULL REFERENCES orders(order_id),
  coupon_id INTEGER NOT NULL REFERENCES coupons(coupon_id),
  PRIMARY KEY (order_id, coupon_id)
) STRICT;

CREATE TABLE daily_sales_snapshots (
  snapshot_date TEXT NOT NULL CHECK (snapshot_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  store_code    TEXT NOT NULL,
  revenue       INTEGER NOT NULL CHECK (revenue >= 0),
  PRIMARY KEY (snapshot_date, store_code)
) STRICT;

-- 資安治理、RBAC 權限與稽核軌跡

CREATE TABLE staff_accounts (
  staff_id     INTEGER PRIMARY KEY,
  email        TEXT NOT NULL, -- 員工帳號屬勞雇紀錄，依人事保存期限保留（不同於顧客的遺忘權抹除）
  display_name TEXT NOT NULL,
  store_code   TEXT NOT NULL,
  status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'offboarded')),
  created_at   TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  deleted_at   TEXT CHECK (deleted_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  CHECK ((status = 'offboarded') = (deleted_at IS NOT NULL))
) STRICT;

-- 軟刪除下的部分唯一索引：僅對未刪除帳號強制不分大小寫信箱唯一，允許離職員工復職重註冊
CREATE UNIQUE INDEX uq_staff_active_email
  ON staff_accounts (LOWER(email))
  WHERE deleted_at IS NULL;

CREATE TABLE roles (
  role_id     INTEGER PRIMARY KEY,
  role_code   TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL
) STRICT;

CREATE TABLE permissions (
  perm_id   INTEGER PRIMARY KEY,
  perm_code TEXT NOT NULL UNIQUE,
  resource  TEXT NOT NULL,
  action    TEXT NOT NULL
) STRICT;

CREATE TABLE role_permissions (
  role_id INTEGER NOT NULL REFERENCES roles(role_id),
  perm_id INTEGER NOT NULL REFERENCES permissions(perm_id),
  PRIMARY KEY (role_id, perm_id)
) STRICT;

-- 角色指派採代理主鍵：同一員工可在不同門市各持同一角色，撤銷後重新授權另起新列、保留歷史
CREATE TABLE staff_roles (
  staff_role_id INTEGER PRIMARY KEY,
  staff_id      INTEGER NOT NULL REFERENCES staff_accounts(staff_id),
  role_id       INTEGER NOT NULL REFERENCES roles(role_id),
  store_scope   TEXT, -- NULL 代表全門市（總部全域角色），否則僅限單一門市代碼
  granted_at    TEXT NOT NULL CHECK (granted_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  expires_at    TEXT CHECK (expires_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  revoked_at    TEXT CHECK (revoked_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]')
) STRICT;

-- 未撤銷的指派在 (員工, 角色, 門市範圍) 上唯一；COALESCE 把 NULL 全域範圍視為同一值（等同 PostgreSQL 的 NULLS NOT DISTINCT）
CREATE UNIQUE INDEX uq_staff_roles_active
  ON staff_roles (staff_id, role_id, COALESCE(store_scope, '*'))
  WHERE revoked_at IS NULL;

CREATE TABLE order_audit_logs (
  audit_id       INTEGER PRIMARY KEY,
  order_id       INTEGER NOT NULL REFERENCES orders(order_id),
  actor_staff_id INTEGER REFERENCES staff_accounts(staff_id),
  actor_role     TEXT NOT NULL,
  action         TEXT NOT NULL CHECK (action IN ('status_change', 'refund_approved', 'manual_adjust')),
  before_status  TEXT NOT NULL,
  after_status   TEXT NOT NULL,
  before_amount  INTEGER NOT NULL,
  after_amount   INTEGER NOT NULL,
  reason         TEXT NOT NULL,
  created_at     TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]')
) STRICT;

CREATE TRIGGER trg_order_audit_no_update
BEFORE UPDATE ON order_audit_logs
BEGIN
  SELECT RAISE(ABORT, 'order_audit_logs is append-only');
END;

CREATE TRIGGER trg_order_audit_no_delete
BEFORE DELETE ON order_audit_logs
BEGIN
  SELECT RAISE(ABORT, 'order_audit_logs is append-only');
END;

-- 多實例高流量與 Schema 設計層：背景任務、排班、冷資料附屬表與高頻瀏覽事件

-- 匯出任務狀態機：queued → running → done / failed；複查請求者權限未通過寫 denied，
-- 請求者離職、停權或重設密碼時把尚在排隊的任務寫 cancelled（兩者皆為終態，不會被輪詢重新撿起）
CREATE TABLE export_jobs (
  job_id                INTEGER PRIMARY KEY,
  status                TEXT NOT NULL CHECK (status IN ('queued', 'running', 'done', 'failed', 'denied', 'cancelled')),
  payload               TEXT NOT NULL,
  claimed_by            TEXT,
  requested_by_staff_id INTEGER NOT NULL REFERENCES staff_accounts(staff_id),
  scope_store_code      TEXT, -- NULL 代表跨門市（全域）報表，只有全域角色可請求
  status_reason         TEXT, -- denied / cancelled 的稽核原因
  created_at            TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  CHECK (status NOT IN ('denied', 'cancelled') OR status_reason IS NOT NULL)
) STRICT;

CREATE TABLE store_shifts (
  shift_id   INTEGER PRIMARY KEY,
  staff_id   INTEGER NOT NULL REFERENCES staff_accounts(staff_id),
  store_code TEXT NOT NULL,
  starts_at  TEXT NOT NULL CHECK (starts_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  ends_at    TEXT NOT NULL CHECK (ends_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  CHECK (ends_at > starts_at)
) STRICT;

CREATE TABLE book_details (
  book_id     INTEGER PRIMARY KEY REFERENCES books(book_id),
  synopsis_md TEXT NOT NULL, -- 數千字長介紹（熱冷拆表討論對象）
  specs_json  TEXT NOT NULL  -- 稀疏規格屬性（頁數、裝幀、譯者）
) STRICT;

CREATE TABLE book_view_events (
  view_id   INTEGER PRIMARY KEY,
  book_id   INTEGER NOT NULL REFERENCES books(book_id),
  viewed_at TEXT NOT NULL CHECK (viewed_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]')
) STRICT;

-- 受控假名化檢視表（供分析角色查詢）：不含姓名、email 與 customer_pii，
-- 但保留穩定的 customer_id 供串接訂單，屬假名化（pseudonymization）而非匿名化；註冊時間只留到月份以降低再識別風險
CREATE VIEW v_customer_analytics AS
SELECT
  customer_id,
  COALESCE(NULLIF(city, ''), '(未填寫)') AS city_bucket,
  status,
  substr(created_at, 1, 7) AS created_month
FROM customers;

-- 未撤銷且帳號在職的員工權限基礎檢視表：不含時間參數，所以沒有排除 expires_at 已過期的指派；
-- 呼叫端須再加 (expires_at IS NULL OR expires_at > :now)，並自行比對 store_scope 與目標門市
CREATE VIEW v_active_staff_permissions AS
SELECT DISTINCT
  sa.staff_id,
  sa.store_code,
  sr.store_scope,
  sr.expires_at,
  r.role_code,
  p.perm_code
FROM staff_accounts sa
JOIN staff_roles sr ON sr.staff_id = sa.staff_id
JOIN roles r ON r.role_id = sr.role_id
JOIN role_permissions rp ON rp.role_id = r.role_id
JOIN permissions p ON p.perm_id = rp.perm_id
WHERE sa.status = 'active'
  AND sa.deleted_at IS NULL
  AND sr.revoked_at IS NULL;

-- 基準索引（供執行計畫、部分索引與資安查詢對照）
CREATE INDEX idx_orders_customer_date ON orders(customer_id, ordered_at);
CREATE INDEX idx_orders_ordered_id ON orders(ordered_at DESC, order_id DESC);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_export_jobs_queued ON export_jobs(created_at ASC) WHERE status = 'queued';
CREATE INDEX idx_staff_roles_active ON staff_roles(staff_id, role_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_order_audit_order_time ON order_audit_logs(order_id, created_at DESC);
