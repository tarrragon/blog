-- 領域丙（swift-logistics）：捷配物流 B2B 倉儲與配送調度平台（正式環境資安與權限完整模型）
-- 引擎基準：SQLite 3.43+（STRICT 表需 3.37+）。本檔使用 SQLite 專用語法（STRICT、RAISE(ABORT)），
-- 不能直接在 PostgreSQL 執行；PostgreSQL 18 對應 DDL 見 schema_pg.sql，角色、GRANT 與 RLS 見 security_pg.sql。
--
-- 全檔約定（與另外兩個領域一致）：
-- 1. 所有表宣告 STRICT，寫入型別不符時報錯，不靠 SQLite 型別親和性自動轉換。
-- 2. 時間欄位一律存 'YYYY-MM-DD HH:MM:SS'（UTC，無時區後綴）文字，並以 GLOB 檢查格式。
-- 3. 金額欄位以 _cents 結尾者單位為「分」（新台幣 1 元 = 100 分），因物流計費含小數元。
-- 4. 軟刪除欄位 deleted_at 與 status 以表級 CHECK 綁定。
-- 5. 多租戶：凡掛在運單底下的子表都冗餘 NOT NULL 的 merchant_id，並以複合外鍵 (merchant_id, shipment_id)
--    指向 shipments 的 UNIQUE (merchant_id, shipment_id)，資料庫層保證子表租戶與父表一致（1.21〈多租戶子表的租戶鍵〉）。

PRAGMA foreign_keys = ON;

CREATE TABLE warehouses (
  warehouse_id  INTEGER PRIMARY KEY,
  code          TEXT NOT NULL UNIQUE,
  region        TEXT NOT NULL,
  parent_hub_id INTEGER REFERENCES warehouses(warehouse_id)
) STRICT;

CREATE TABLE merchants (
  merchant_id INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  account_key TEXT NOT NULL, -- 舊版商業代碼（對帳與條碼前綴用）；API 認證金鑰獨立存放於 merchant_api_keys
  tier        TEXT, -- 允許 NULL 代表未分級新商家
  status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'offboarded')),
  deleted_at  TEXT CHECK (deleted_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  CHECK ((status = 'offboarded') = (deleted_at IS NOT NULL))
) STRICT;

-- 多租戶商家端帳號（商家內部角色以 role_code 固定四種，屬商家自管的租戶內權限）與 API 金鑰憑證

CREATE TABLE merchant_users (
  merchant_user_id INTEGER PRIMARY KEY,
  merchant_id      INTEGER NOT NULL REFERENCES merchants(merchant_id),
  email            TEXT NOT NULL,
  display_name     TEXT NOT NULL,
  role_code        TEXT NOT NULL CHECK (role_code IN ('owner', 'dispatcher', 'finance', 'readonly')),
  status           TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'offboarded')),
  created_at       TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  deleted_at       TEXT CHECK (deleted_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  CHECK ((status = 'offboarded') = (deleted_at IS NOT NULL))
) STRICT;

CREATE UNIQUE INDEX uq_merchant_user_active_email
  ON merchant_users (merchant_id, LOWER(email))
  WHERE deleted_at IS NULL;

CREATE TABLE merchant_api_keys (
  api_key_id   INTEGER PRIMARY KEY,
  merchant_id  INTEGER NOT NULL REFERENCES merchants(merchant_id),
  key_prefix   TEXT NOT NULL,        -- 明文前綴（供日誌識別與快速初篩）
  key_hash     TEXT NOT NULL UNIQUE, -- 不可逆雜湊值（系統不保存完整金鑰明文）
  scopes       TEXT NOT NULL,        -- 逗號分隔最小權限範圍（如 shipments:read）
  created_at   TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  expires_at   TEXT CHECK (expires_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'), -- NULL 代表無固定到期日（仍受 revoked_at 與 merchant.status 約束）
  revoked_at   TEXT CHECK (revoked_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  last_used_at TEXT CHECK (last_used_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]')
) STRICT;

CREATE TABLE drivers (
  driver_id         INTEGER PRIMARY KEY,
  name              TEXT NOT NULL,
  license_tier      TEXT NOT NULL CHECK (license_tier IN ('regular', 'heavy', 'hazmat')),
  home_warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id),
  status            TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended'))
) STRICT;

-- 平台內部員工 RBAC（員工 → 角色指派 → 角色權限，三個領域同一套形狀）

CREATE TABLE staff_accounts (
  staff_id     INTEGER PRIMARY KEY,
  email        TEXT NOT NULL,
  display_name TEXT NOT NULL,
  status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'offboarded')),
  created_at   TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  deleted_at   TEXT CHECK (deleted_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  CHECK ((status = 'offboarded') = (deleted_at IS NOT NULL))
) STRICT;

CREATE UNIQUE INDEX uq_logistics_staff_active_email
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

CREATE TABLE staff_roles (
  staff_role_id INTEGER PRIMARY KEY,
  staff_id      INTEGER NOT NULL REFERENCES staff_accounts(staff_id),
  role_id       INTEGER NOT NULL REFERENCES roles(role_id),
  warehouse_scope_id INTEGER REFERENCES warehouses(warehouse_id), -- NULL 代表全倉庫（全域角色）
  granted_at    TEXT NOT NULL CHECK (granted_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  expires_at    TEXT CHECK (expires_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  revoked_at    TEXT CHECK (revoked_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]')
) STRICT;

CREATE UNIQUE INDEX uq_logistics_staff_roles_active
  ON staff_roles (staff_id, role_id, COALESCE(warehouse_scope_id, 0))
  WHERE revoked_at IS NULL;

-- 運單、子表多租戶鍵、獨立收件人 PII 表與事件

CREATE TABLE shipments (
  shipment_id  INTEGER PRIMARY KEY,
  merchant_id  INTEGER NOT NULL REFERENCES merchants(merchant_id),
  warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id),
  status       TEXT NOT NULL CHECK (status IN ('created', 'in_transit', 'delivered', 'returned')),
  fee_cents    INTEGER NOT NULL CHECK (fee_cents >= 0),
  created_at   TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  UNIQUE (merchant_id, shipment_id) -- 供子表複合外鍵參照
) STRICT;

CREATE TABLE shipment_packages (
  package_id   INTEGER PRIMARY KEY,
  shipment_id  INTEGER NOT NULL,
  merchant_id  INTEGER NOT NULL, -- 冗餘租戶鍵供子表直走 RLS 與索引過濾
  weight_grams INTEGER NOT NULL CHECK (weight_grams > 0),
  fragile      INTEGER NOT NULL DEFAULT 0 CHECK (fragile IN (0, 1)),
  FOREIGN KEY (merchant_id, shipment_id) REFERENCES shipments(merchant_id, shipment_id)
) STRICT;

CREATE TABLE shipment_payloads (
  shipment_id      INTEGER PRIMARY KEY,
  merchant_id      INTEGER NOT NULL,
  raw_waybill_json TEXT NOT NULL, -- 原始電子託運單大型報文（熱冷拆表對象，不含明文收件人個資）
  FOREIGN KEY (merchant_id, shipment_id) REFERENCES shipments(merchant_id, shipment_id)
) STRICT;

CREATE TABLE shipment_recipient_pii (
  shipment_id      INTEGER PRIMARY KEY,
  merchant_id      INTEGER NOT NULL,
  recipient_name   TEXT,
  recipient_phone  TEXT,
  delivery_address TEXT,
  erased_at        TEXT CHECK (erased_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'), -- 超過法規保存期限後自動抹除明文個資
  FOREIGN KEY (merchant_id, shipment_id) REFERENCES shipments(merchant_id, shipment_id),
  CHECK (erased_at IS NULL OR (recipient_name IS NULL AND recipient_phone IS NULL AND delivery_address IS NULL))
) STRICT;

-- 掃描事件：shipment_id 刻意允許 NULL 模擬掃碼槍孤兒事件；孤兒事件沒有租戶，merchant_id 同為 NULL
-- （複合外鍵在任一欄為 NULL 時依 MATCH SIMPLE 略過檢查，所以另以 CHECK 綁定兩欄同為 NULL 或同為非 NULL）
CREATE TABLE shipment_events (
  event_id    INTEGER PRIMARY KEY,
  shipment_id INTEGER,
  merchant_id INTEGER,
  event_type  TEXT NOT NULL CHECK (event_type IN ('picked', 'hub_in', 'out_for_delivery', 'signed', 'exception')),
  recorded_at TEXT CHECK (recorded_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'), -- 刻意允許 NULL 模擬離線同步時間缺漏，觸發跨引擎 NULL 排序反例
  FOREIGN KEY (merchant_id, shipment_id) REFERENCES shipments(merchant_id, shipment_id),
  CHECK ((shipment_id IS NULL) = (merchant_id IS NULL))
) STRICT;

CREATE TABLE driver_shifts (
  shift_id   INTEGER PRIMARY KEY,
  driver_id  INTEGER NOT NULL REFERENCES drivers(driver_id),
  route_code TEXT NOT NULL,
  starts_at  TEXT NOT NULL CHECK (starts_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  ends_at    TEXT NOT NULL CHECK (ends_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  CHECK (ends_at > starts_at)
) STRICT;

CREATE TABLE dispatch_tasks (
  task_id     INTEGER PRIMARY KEY,
  shipment_id INTEGER NOT NULL,
  merchant_id INTEGER NOT NULL,
  status      TEXT NOT NULL CHECK (status IN ('queued', 'claimed', 'completed')),
  claimed_by  TEXT,
  priority    INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 10),
  created_at  TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  FOREIGN KEY (merchant_id, shipment_id) REFERENCES shipments(merchant_id, shipment_id),
  CHECK ((status = 'queued') = (claimed_by IS NULL))
) STRICT;

CREATE TABLE billing_statements (
  statement_id INTEGER PRIMARY KEY,
  merchant_id  INTEGER NOT NULL REFERENCES merchants(merchant_id),
  period_month TEXT NOT NULL CHECK (period_month GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]'),
  total_cents  INTEGER NOT NULL CHECK (total_cents >= 0),
  status       TEXT NOT NULL CHECK (status IN ('draft', 'issued', 'settled')),
  UNIQUE (merchant_id, period_month)
) STRICT;

-- 唯附寫月結帳單稽核軌跡（不存收件人 PII，防止與個資遺忘權衝突）
-- actor_id 依 actor_type 指向 staff_accounts、merchant_users 或系統排程（system 一律為 0），屬多型參照，無法以單一外鍵約束
CREATE TABLE billing_audit_logs (
  audit_id      INTEGER PRIMARY KEY,
  statement_id  INTEGER NOT NULL REFERENCES billing_statements(statement_id),
  merchant_id   INTEGER NOT NULL REFERENCES merchants(merchant_id),
  actor_type    TEXT NOT NULL CHECK (actor_type IN ('staff', 'merchant_user', 'system')),
  actor_id      INTEGER NOT NULL,
  action        TEXT NOT NULL CHECK (action IN ('issued', 'settled', 'adjusted', 'reopened')),
  before_status TEXT NOT NULL,
  after_status  TEXT NOT NULL,
  before_cents  INTEGER NOT NULL,
  after_cents   INTEGER NOT NULL,
  created_at    TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
  CHECK (actor_type <> 'system' OR actor_id = 0)
) STRICT;

CREATE TRIGGER trg_billing_audit_no_update
BEFORE UPDATE ON billing_audit_logs
BEGIN
  SELECT RAISE(ABORT, 'billing_audit_logs is append-only');
END;

CREATE TRIGGER trg_billing_audit_no_delete
BEFORE DELETE ON billing_audit_logs
BEGIN
  SELECT RAISE(ABORT, 'billing_audit_logs is append-only');
END;

-- 受控假名化分析檢視表（不含 shipment_recipient_pii 與原始託運報文）：保留 shipment_id 與 merchant_id 供對帳串接，
-- 屬假名化而非匿名化；建立時間只留到日期
CREATE VIEW v_shipment_analytics AS
SELECT
  s.shipment_id,
  s.merchant_id,
  s.warehouse_id,
  w.region,
  s.status,
  s.fee_cents,
  substr(s.created_at, 1, 10) AS created_date
FROM shipments s
JOIN warehouses w ON w.warehouse_id = s.warehouse_id;

-- 生效中商家 API 金鑰基礎檢視表（尚未檢查動態 expires_at，先切掉已撤銷金鑰與停權商家；呼叫端須再加
-- (expires_at IS NULL OR expires_at > :now)）
CREATE VIEW v_active_merchant_api_keys AS
SELECT
  k.api_key_id,
  k.merchant_id,
  k.key_prefix,
  k.key_hash,
  k.scopes,
  k.expires_at
FROM merchant_api_keys k
JOIN merchants m ON m.merchant_id = k.merchant_id
WHERE m.status = 'active'
  AND m.deleted_at IS NULL
  AND k.revoked_at IS NULL;

-- 基準索引（包含複合索引前導欄、部分索引與多租戶 RLS 覆蓋索引）
CREATE INDEX idx_shipments_wh_status_created ON shipments(warehouse_id, status, created_at DESC, shipment_id ASC);
CREATE INDEX idx_shipments_merchant_id ON shipments(merchant_id, shipment_id);
CREATE INDEX idx_packages_merchant_shipment ON shipment_packages(merchant_id, shipment_id);
CREATE INDEX idx_events_shipment_recorded ON shipment_events(shipment_id, recorded_at DESC);
CREATE INDEX idx_events_merchant_shipment ON shipment_events(merchant_id, shipment_id);
CREATE INDEX idx_dispatch_queued ON dispatch_tasks(priority DESC, created_at ASC) WHERE status = 'queued';
CREATE INDEX idx_api_keys_prefix ON merchant_api_keys(key_prefix) WHERE revoked_at IS NULL;
CREATE INDEX idx_billing_audit_stmt ON billing_audit_logs(statement_id, created_at DESC);
