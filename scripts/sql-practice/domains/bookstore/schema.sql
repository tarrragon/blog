-- 領域甲（bookstore）：紙頁書店線上書城與門市系統
-- 引擎基準：SQLite 3.43+（相容 PostgreSQL 18 結構語意；跨引擎差異見規格書）

PRAGMA foreign_keys = ON;

-- 營運初期：核心銷售與評價

CREATE TABLE customers (
  customer_id INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  email       TEXT NOT NULL,
  city        TEXT, -- 允許 NULL 供未填寫地址反例驗證
  created_at  TEXT NOT NULL
);

CREATE TABLE categories (
  category_id INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  parent_id   INTEGER REFERENCES categories(category_id)
);

CREATE TABLE books (
  book_id     INTEGER PRIMARY KEY,
  title       TEXT NOT NULL,
  category_id INTEGER NOT NULL REFERENCES categories(category_id),
  price       INTEGER NOT NULL CHECK (price >= 0),
  stock       INTEGER NOT NULL CHECK (stock >= 0),
  is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE orders (
  order_id     INTEGER PRIMARY KEY,
  customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),
  status       TEXT NOT NULL CHECK (status IN ('pending', 'paid', 'shipped', 'cancelled', 'refunded')),
  total_amount INTEGER NOT NULL CHECK (total_amount >= 0),
  ordered_at   TEXT NOT NULL
);

CREATE TABLE order_items (
  order_item_id INTEGER PRIMARY KEY,
  order_id      INTEGER NOT NULL REFERENCES orders(order_id),
  book_id       INTEGER NOT NULL REFERENCES books(book_id),
  quantity      INTEGER NOT NULL CHECK (quantity > 0),
  unit_price    INTEGER NOT NULL CHECK (unit_price >= 0)
);

CREATE TABLE reviews (
  review_id  INTEGER PRIMARY KEY,
  order_id   INTEGER REFERENCES orders(order_id), -- 刻意允許 NULL 模擬匯入缺漏資料
  book_id    INTEGER NOT NULL REFERENCES books(book_id),
  rating     INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
  created_at TEXT NOT NULL
);

-- 營運成長期：行銷、對帳與效能壓力

CREATE TABLE coupons (
  coupon_id     INTEGER PRIMARY KEY,
  code          TEXT NOT NULL,
  discount_type TEXT NOT NULL CHECK (discount_type IN ('fixed', 'percent')),
  discount_val  INTEGER NOT NULL CHECK (discount_val > 0),
  expires_at    TEXT NOT NULL,
  is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE order_coupons (
  order_id  INTEGER NOT NULL REFERENCES orders(order_id),
  coupon_id INTEGER NOT NULL REFERENCES coupons(coupon_id),
  PRIMARY KEY (order_id, coupon_id)
);

CREATE TABLE daily_sales_snapshots (
  snapshot_date TEXT NOT NULL,
  store_code    TEXT NOT NULL,
  revenue       INTEGER NOT NULL CHECK (revenue >= 0),
  PRIMARY KEY (snapshot_date, store_code)
);

-- 多實例高流量與 Schema 設計層：背景任務、排班、冷資料附屬表與高頻瀏覽事件

CREATE TABLE export_jobs (
  job_id     INTEGER PRIMARY KEY,
  status     TEXT NOT NULL CHECK (status IN ('queued', 'running', 'done', 'failed')),
  payload    TEXT NOT NULL,
  claimed_by TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE store_shifts (
  shift_id   INTEGER PRIMARY KEY,
  staff_id   INTEGER NOT NULL,
  store_code TEXT NOT NULL,
  starts_at  TEXT NOT NULL,
  ends_at    TEXT NOT NULL
);

CREATE TABLE book_details (
  book_id     INTEGER PRIMARY KEY REFERENCES books(book_id),
  synopsis_md TEXT NOT NULL, -- 數千字長介紹（熱冷拆表討論對象）
  specs_json  TEXT NOT NULL  -- 稀疏規格屬性（頁數、裝幀、譯者）
);

CREATE TABLE book_view_events (
  view_id   INTEGER PRIMARY KEY,
  book_id   INTEGER NOT NULL REFERENCES books(book_id),
  viewed_at TEXT NOT NULL
);

-- 基準索引（供執行計畫與部分索引對照）
CREATE INDEX idx_orders_customer_date ON orders(customer_id, ordered_at);
CREATE INDEX idx_orders_ordered_id ON orders(ordered_at DESC, order_id DESC);
CREATE INDEX idx_export_jobs_queued ON export_jobs(created_at ASC) WHERE status = 'queued';
