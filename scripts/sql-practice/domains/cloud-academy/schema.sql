-- 領域乙（cloud-academy）：雲課堂線上訂閱制教學平台（正式環境資安與權限完整模型）
-- 引擎基準：SQLite 3.43+（STRICT 表需 3.37+）。本檔使用 SQLite 專用語法（STRICT、RAISE(ABORT)），
-- 不能直接在 PostgreSQL 執行；PostgreSQL 18 對應 DDL 見 schema_pg.sql，角色、GRANT 與 RLS 見 security_pg.sql。
--
-- 全檔約定（與另外兩個領域一致）：
-- 1. 所有表宣告 STRICT，寫入型別不符時報錯，不靠 SQLite 型別親和性自動轉換。
-- 2. 時間欄位一律存 'YYYY-MM-DD HH:MM:SS'（UTC，無時區後綴）文字，並以 GLOB 檢查格式。
-- 3. 金額欄位（invoices.amount）一律為新台幣整數元；courses.monthly_fee_tier 是價格級距代號，不是金額。
-- 4. 軟刪除欄位 deleted_at 與 status 以表級 CHECK 綁定。

PRAGMA foreign_keys = ON;

CREATE TABLE users (
  user_id      INTEGER PRIMARY KEY,
  display_name TEXT, -- 帳號刪除（status = 'deleted'）並完成個資抹除後清為 NULL，其餘狀態必填
  email        TEXT, -- 同上；刻意不設 UNIQUE，保留大小寫重複信箱反例
  country      TEXT, -- 允許 NULL 供未填地區反例
  status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'locked', 'suspended', 'deleted')),
  deleted_at   TEXT CHECK (deleted_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  joined_at    TEXT NOT NULL CHECK (joined_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  CHECK ((status = 'deleted') = (deleted_at IS NOT NULL)),
  CHECK (status = 'deleted' OR (display_name IS NOT NULL AND email IS NOT NULL)),
  CHECK (status <> 'deleted' OR (display_name IS NULL AND email IS NULL))
) STRICT;

CREATE TABLE user_pii (
  user_id         INTEGER PRIMARY KEY REFERENCES users(user_id),
  legal_name      TEXT,
  phone_e164      TEXT,
  billing_address TEXT,
  erased_at       TEXT CHECK (erased_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'), -- 個資遺忘權抹除後清空明文並保留抹除時間戳
  CHECK (erased_at IS NULL OR (legal_name IS NULL AND phone_e164 IS NULL AND billing_address IS NULL))
) STRICT;

CREATE TABLE user_credentials (
  user_id             INTEGER PRIMARY KEY REFERENCES users(user_id),
  password_hash       TEXT NOT NULL,
  mfa_enabled         INTEGER NOT NULL DEFAULT 0 CHECK (mfa_enabled IN (0, 1)),
  failed_attempts     INTEGER NOT NULL DEFAULT 0 CHECK (failed_attempts >= 0),
  locked_until        TEXT CHECK (locked_until GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  password_changed_at TEXT NOT NULL CHECK (password_changed_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]')
) STRICT;

CREATE TABLE user_sessions (
  session_id INTEGER PRIMARY KEY,
  user_id    INTEGER NOT NULL REFERENCES users(user_id),
  token_hash TEXT NOT NULL UNIQUE,
  ip_addr    TEXT NOT NULL,
  created_at TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  expires_at TEXT NOT NULL CHECK (expires_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  revoked_at TEXT CHECK (revoked_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  CHECK (expires_at > created_at)
) STRICT;

-- B2B 企業租戶與多租戶成員權限

CREATE TABLE organizations (
  org_id     INTEGER PRIMARY KEY,
  slug       TEXT NOT NULL UNIQUE,
  name       TEXT NOT NULL,
  status     TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended')),
  created_at TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]')
) STRICT;

CREATE TABLE org_memberships (
  org_id     INTEGER NOT NULL REFERENCES organizations(org_id),
  user_id    INTEGER NOT NULL REFERENCES users(user_id),
  org_role   TEXT NOT NULL CHECK (org_role IN ('owner', 'admin', 'member', 'billing_viewer')),
  status     TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'invited', 'suspended', 'revoked')),
  joined_at  TEXT NOT NULL CHECK (joined_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  revoked_at TEXT CHECK (revoked_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  PRIMARY KEY (org_id, user_id),
  CHECK ((status = 'revoked') = (revoked_at IS NOT NULL))
) STRICT;

-- 平台層 RBAC（使用者 → 角色指派 → 角色權限，三個領域同一套形狀）與唯附寫權限稽核

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

-- 角色指派採代理主鍵：撤銷後重新授權另起新列、保留歷史
CREATE TABLE user_roles (
  user_role_id INTEGER PRIMARY KEY,
  user_id      INTEGER NOT NULL REFERENCES users(user_id),
  role_id      INTEGER NOT NULL REFERENCES roles(role_id),
  granted_at   TEXT NOT NULL CHECK (granted_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  expires_at   TEXT CHECK (expires_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  revoked_at   TEXT CHECK (revoked_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]')
) STRICT;

CREATE UNIQUE INDEX uq_user_roles_active
  ON user_roles (user_id, role_id)
  WHERE revoked_at IS NULL;

CREATE TABLE permission_audit_logs (
  audit_id       INTEGER PRIMARY KEY,
  org_id         INTEGER REFERENCES organizations(org_id),
  actor_user_id  INTEGER NOT NULL REFERENCES users(user_id),
  target_user_id INTEGER NOT NULL REFERENCES users(user_id),
  event_action   TEXT NOT NULL CHECK (event_action IN ('role_granted', 'role_revoked', 'org_member_removed', 'password_reset')),
  before_role    TEXT,
  after_role     TEXT,
  created_at     TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]')
) STRICT;

CREATE TRIGGER trg_perm_audit_no_update
BEFORE UPDATE ON permission_audit_logs
BEGIN
  SELECT RAISE(ABORT, 'permission_audit_logs is append-only');
END;

CREATE TRIGGER trg_perm_audit_no_delete
BEFORE DELETE ON permission_audit_logs
BEGIN
  SELECT RAISE(ABORT, 'permission_audit_logs is append-only');
END;

-- 核心課程、訂閱、帳單、學習進度與金流事件

CREATE TABLE courses (
  course_id        INTEGER PRIMARY KEY,
  title            TEXT NOT NULL,
  track            TEXT NOT NULL CHECK (track IN ('backend', 'data', 'devops')),
  prerequisite_id  INTEGER REFERENCES courses(course_id),
  monthly_fee_tier INTEGER NOT NULL CHECK (monthly_fee_tier >= 0),
  is_published     INTEGER NOT NULL DEFAULT 1 CHECK (is_published IN (0, 1))
) STRICT;

CREATE TABLE course_contents (
  course_id     INTEGER PRIMARY KEY REFERENCES courses(course_id),
  syllabus_md   TEXT NOT NULL, -- 大容量課綱與教材說明（熱冷拆表對象）
  metadata_json TEXT NOT NULL
) STRICT;

CREATE TABLE tags (
  tag_id INTEGER PRIMARY KEY,
  name   TEXT NOT NULL UNIQUE
) STRICT;

CREATE TABLE course_tags (
  course_id INTEGER NOT NULL REFERENCES courses(course_id),
  tag_id    INTEGER NOT NULL REFERENCES tags(tag_id),
  PRIMARY KEY (course_id, tag_id)
) STRICT;

CREATE TABLE subscriptions (
  sub_id     INTEGER PRIMARY KEY,
  user_id    INTEGER NOT NULL REFERENCES users(user_id),
  org_id     INTEGER REFERENCES organizations(org_id), -- 企業方案 team 綁定組織租戶
  plan_code  TEXT NOT NULL CHECK (plan_code IN ('free', 'pro', 'team')),
  status     TEXT NOT NULL CHECK (status IN ('trialing', 'active', 'past_due', 'canceled')),
  started_at TEXT NOT NULL CHECK (started_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  ended_at   TEXT CHECK (ended_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  CHECK ((status = 'canceled') = (ended_at IS NOT NULL)),
  CHECK (ended_at IS NULL OR ended_at > started_at)
) STRICT;

CREATE TABLE invoices (
  invoice_id INTEGER PRIMARY KEY,
  sub_id     INTEGER REFERENCES subscriptions(sub_id), -- 刻意允許 NULL 模擬手動補單匯入缺漏
  amount     INTEGER NOT NULL CHECK (amount >= 0),
  status     TEXT NOT NULL CHECK (status IN ('open', 'paid', 'void', 'refunded')),
  issued_at  TEXT NOT NULL CHECK (issued_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]')
) STRICT;

CREATE TABLE lesson_progress (
  progress_id   INTEGER PRIMARY KEY,
  user_id       INTEGER NOT NULL REFERENCES users(user_id),
  course_id     INTEGER NOT NULL REFERENCES courses(course_id),
  lesson_no     INTEGER NOT NULL CHECK (lesson_no > 0),
  completed_at  TEXT CHECK (completed_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'), -- NULL 代表已開始觀看但未完課
  watch_seconds INTEGER NOT NULL DEFAULT 0 CHECK (watch_seconds >= 0)
) STRICT;

CREATE TABLE certificates (
  cert_id   INTEGER PRIMARY KEY,
  user_id   INTEGER NOT NULL REFERENCES users(user_id),
  course_id INTEGER NOT NULL REFERENCES courses(course_id),
  issued_at TEXT NOT NULL CHECK (issued_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  UNIQUE (user_id, course_id)
) STRICT;

-- 刻意不設 UNIQUE (provider, external_id)：保留重送事件供去重稽核；冪等處理的正確寫法由題目選項示範
CREATE TABLE webhook_events (
  event_id        INTEGER PRIMARY KEY,
  provider        TEXT NOT NULL CHECK (provider IN ('stripe', 'newebpay')),
  external_id     TEXT NOT NULL,
  status          TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'done', 'dead')),
  signature_valid INTEGER NOT NULL DEFAULT 1 CHECK (signature_valid IN (0, 1)),
  source_ip       TEXT,
  received_at     TEXT NOT NULL CHECK (received_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]')
) STRICT;

-- 受控假名化分析檢視表：不暴露 display_name、email 與 user_pii，但保留穩定的 user_id 供串接訂閱與帳單，
-- 屬假名化（pseudonymization）而非匿名化；加入時間只留到月份
CREATE VIEW v_learner_analytics AS
SELECT
  user_id,
  COALESCE(NULLIF(country, ''), '(未填寫)') AS country_bucket,
  status,
  substr(joined_at, 1, 7) AS joined_month
FROM users;

-- 有效 Session 基準檢視表（不含時間比較參數，先切掉非 active 帳號、已撤銷與密碼變更前簽發的舊 session；
-- 呼叫端須再加 expires_at > :now）
CREATE VIEW v_valid_sessions AS
SELECT
  s.session_id,
  s.user_id,
  s.token_hash,
  s.created_at,
  s.expires_at
FROM user_sessions s
JOIN users u ON u.user_id = s.user_id
JOIN user_credentials c ON c.user_id = s.user_id
WHERE u.status = 'active'
  AND u.deleted_at IS NULL
  AND s.revoked_at IS NULL
  AND s.created_at >= c.password_changed_at;

-- 基準索引
CREATE INDEX idx_invoices_sub_status ON invoices(sub_id, status);
CREATE INDEX idx_progress_user_course ON lesson_progress(user_id, course_id);
CREATE INDEX idx_webhook_pending ON webhook_events(received_at ASC) WHERE status = 'pending';
CREATE INDEX idx_sessions_user_active ON user_sessions(user_id, expires_at) WHERE revoked_at IS NULL;
CREATE INDEX idx_org_memberships_user ON org_memberships(user_id, org_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_subscriptions_org ON subscriptions(org_id, status) WHERE org_id IS NOT NULL;
CREATE INDEX idx_user_roles_active ON user_roles(user_id, role_id) WHERE revoked_at IS NULL;
