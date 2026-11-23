-- 領域乙（cloud-academy）：雲課堂線上訂閱制教學平台
-- 引擎基準：SQLite 3.43+（相容 PostgreSQL 18 結構語意）

PRAGMA foreign_keys = ON;

CREATE TABLE users (
  user_id      INTEGER PRIMARY KEY,
  display_name TEXT NOT NULL,
  email        TEXT NOT NULL,
  country      TEXT, -- 允許 NULL 供未填地區反例
  joined_at    TEXT NOT NULL
);

CREATE TABLE courses (
  course_id        INTEGER PRIMARY KEY,
  title            TEXT NOT NULL,
  track            TEXT NOT NULL CHECK (track IN ('backend', 'data', 'devops')),
  prerequisite_id  INTEGER REFERENCES courses(course_id),
  monthly_fee_tier INTEGER NOT NULL CHECK (monthly_fee_tier >= 0),
  is_published     INTEGER NOT NULL DEFAULT 1 CHECK (is_published IN (0, 1))
);

CREATE TABLE course_contents (
  course_id     INTEGER PRIMARY KEY REFERENCES courses(course_id),
  syllabus_md   TEXT NOT NULL, -- 大容量課綱與教材說明（熱冷拆表對象）
  metadata_json TEXT NOT NULL
);

CREATE TABLE tags (
  tag_id INTEGER PRIMARY KEY,
  name   TEXT NOT NULL UNIQUE
);

CREATE TABLE course_tags (
  course_id INTEGER NOT NULL REFERENCES courses(course_id),
  tag_id    INTEGER NOT NULL REFERENCES tags(tag_id),
  PRIMARY KEY (course_id, tag_id)
);

CREATE TABLE subscriptions (
  sub_id     INTEGER PRIMARY KEY,
  user_id    INTEGER NOT NULL REFERENCES users(user_id),
  plan_code  TEXT NOT NULL CHECK (plan_code IN ('free', 'pro', 'team')),
  status     TEXT NOT NULL CHECK (status IN ('trialing', 'active', 'past_due', 'canceled')),
  started_at TEXT NOT NULL,
  ended_at   TEXT
);

CREATE TABLE invoices (
  invoice_id INTEGER PRIMARY KEY,
  sub_id     INTEGER REFERENCES subscriptions(sub_id), -- 刻意允許 NULL 模擬手動補單匯入缺漏
  amount     INTEGER NOT NULL CHECK (amount >= 0),
  status     TEXT NOT NULL CHECK (status IN ('open', 'paid', 'void', 'refunded')),
  issued_at  TEXT NOT NULL
);

CREATE TABLE lesson_progress (
  progress_id   INTEGER PRIMARY KEY,
  user_id       INTEGER NOT NULL REFERENCES users(user_id),
  course_id     INTEGER NOT NULL REFERENCES courses(course_id),
  lesson_no     INTEGER NOT NULL CHECK (lesson_no > 0),
  completed_at  TEXT, -- NULL 代表已開始觀看但未完課
  watch_seconds INTEGER NOT NULL DEFAULT 0 CHECK (watch_seconds >= 0)
);

CREATE TABLE certificates (
  cert_id   INTEGER PRIMARY KEY,
  user_id   INTEGER NOT NULL REFERENCES users(user_id),
  course_id INTEGER NOT NULL REFERENCES courses(course_id),
  issued_at TEXT NOT NULL
);

CREATE TABLE webhook_events (
  event_id    INTEGER PRIMARY KEY,
  provider    TEXT NOT NULL CHECK (provider IN ('stripe', 'newebpay')),
  external_id TEXT NOT NULL,
  status      TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'done', 'dead')),
  received_at TEXT NOT NULL
);

-- 基準索引
CREATE INDEX idx_invoices_sub_status ON invoices(sub_id, status);
CREATE INDEX idx_progress_user_course ON lesson_progress(user_id, course_id);
CREATE INDEX idx_webhook_pending ON webhook_events(received_at ASC) WHERE status = 'pending';
