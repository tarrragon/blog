-- 領域丙（swift-logistics）：捷配物流 B2B 倉儲與配送調度平台（正式環境資安與權限完整模型）
-- 引擎基準：SQLite 3.43+（相容 PostgreSQL 18 結構語意；角色、GRANT 與 RLS 見 security_pg.sql）

PRAGMA foreign_keys = ON;

CREATE TABLE warehouses (
  warehouse_id  INTEGER PRIMARY KEY,
  code          TEXT NOT NULL UNIQUE,
  region        TEXT NOT NULL,
  parent_hub_id INTEGER REFERENCES warehouses(warehouse_id)
);

CREATE TABLE merchants (
  merchant_id INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  account_key TEXT NOT NULL, -- 舊版商業代碼（對帳與條碼前綴用）；API 認證金鑰獨立存放於 merchant_api_keys
  tier        TEXT, -- 允許 NULL 代表未分級新商家
  status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'offboarded')),
  deleted_at  TEXT
);

-- 多租戶商家端帳號、API 金鑰憑證與平台內部 RBAC

CREATE TABLE merchant_users (
  merchant_user_id INTEGER PRIMARY KEY,
  merchant_id      INTEGER NOT NULL REFERENCES merchants(merchant_id),
  email            TEXT NOT NULL,
  display_name     TEXT NOT NULL,
  role_code        TEXT NOT NULL CHECK (role_code IN ('owner', 'dispatcher', 'finance', 'readonly')),
  status           TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'offboarded')),
  created_at       TEXT NOT NULL,
  deleted_at       TEXT
);

CREATE UNIQUE INDEX uq_merchant_user_active_email
  ON merchant_users (merchant_id, LOWER(email))
  WHERE deleted_at IS NULL;

CREATE TABLE merchant_api_keys (
  api_key_id   INTEGER PRIMARY KEY,
  merchant_id  INTEGER NOT NULL REFERENCES merchants(merchant_id),
  key_prefix   TEXT NOT NULL,        -- 明文前綴（供日誌識別與快速初篩）
  key_hash     TEXT NOT NULL UNIQUE, -- 不可逆雜湊值（系統不保存完整金鑰明文）
  scopes       TEXT NOT NULL,        -- 逗號分隔最小權限範圍（如 shipments:read）
  created_at   TEXT NOT NULL,
  expires_at   TEXT,                 -- NULL 代表無固定到期日（仍受 revoked_at 與 merchant.status 約束）
  revoked_at   TEXT,
  last_used_at TEXT
);

CREATE TABLE drivers (
  driver_id         INTEGER PRIMARY KEY,
  name              TEXT NOT NULL,
  license_tier      TEXT NOT NULL CHECK (license_tier IN ('regular', 'heavy', 'hazmat')),
  home_warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id),
  status            TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended'))
);

CREATE TABLE roles (
  role_id     INTEGER PRIMARY KEY,
  role_code   TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL
);

CREATE TABLE permissions (
  perm_id   INTEGER PRIMARY KEY,
  perm_code TEXT NOT NULL UNIQUE,
  resource  TEXT NOT NULL,
  action    TEXT NOT NULL
);

CREATE TABLE role_permissions (
  role_id INTEGER NOT NULL REFERENCES roles(role_id),
  perm_id INTEGER NOT NULL REFERENCES permissions(perm_id),
  PRIMARY KEY (role_id, perm_id)
);

-- 運單、子表多租戶鍵、獨立收件人 PII 表與事件

CREATE TABLE shipments (
  shipment_id  INTEGER PRIMARY KEY,
  merchant_id  INTEGER NOT NULL REFERENCES merchants(merchant_id),
  warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id),
  status       TEXT NOT NULL CHECK (status IN ('created', 'in_transit', 'delivered', 'returned')),
  fee_cents    INTEGER NOT NULL CHECK (fee_cents >= 0),
  created_at   TEXT NOT NULL
);

CREATE TABLE shipment_packages (
  package_id   INTEGER PRIMARY KEY,
  shipment_id  INTEGER NOT NULL REFERENCES shipments(shipment_id),
  merchant_id  INTEGER REFERENCES merchants(merchant_id), -- 冗餘租戶鍵供子表直走 RLS 與索引過濾
  weight_grams INTEGER NOT NULL CHECK (weight_grams > 0),
  fragile      INTEGER NOT NULL DEFAULT 0 CHECK (fragile IN (0, 1))
);

CREATE TABLE shipment_payloads (
  shipment_id      INTEGER PRIMARY KEY REFERENCES shipments(shipment_id),
  raw_waybill_json TEXT NOT NULL -- 原始電子託運單大型報文（熱冷拆表對象，不含明文收件人個資）
);

CREATE TABLE shipment_recipient_pii (
  shipment_id      INTEGER PRIMARY KEY REFERENCES shipments(shipment_id),
  merchant_id      INTEGER NOT NULL REFERENCES merchants(merchant_id),
  recipient_name   TEXT,
  recipient_phone  TEXT,
  delivery_address TEXT,
  erased_at        TEXT -- 超過法規保存期限後自動抹除明文個資
);

CREATE TABLE shipment_events (
  event_id    INTEGER PRIMARY KEY,
  shipment_id INTEGER REFERENCES shipments(shipment_id), -- 刻意允許 NULL 模擬掃碼槍孤兒事件
  event_type  TEXT NOT NULL CHECK (event_type IN ('picked', 'hub_in', 'out_for_delivery', 'signed', 'exception')),
  recorded_at TEXT -- 刻意允許 NULL 模擬離線同步時間缺漏，觸發跨引擎 NULL 排序反例
);

CREATE TABLE driver_shifts (
  shift_id   INTEGER PRIMARY KEY,
  driver_id  INTEGER NOT NULL REFERENCES drivers(driver_id),
  route_code TEXT NOT NULL,
  starts_at  TEXT NOT NULL,
  ends_at    TEXT NOT NULL
);

CREATE TABLE dispatch_tasks (
  task_id     INTEGER PRIMARY KEY,
  shipment_id INTEGER NOT NULL REFERENCES shipments(shipment_id),
  status      TEXT NOT NULL CHECK (status IN ('queued', 'claimed', 'completed')),
  claimed_by  TEXT,
  priority    INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 10),
  created_at  TEXT NOT NULL
);

CREATE TABLE billing_statements (
  statement_id INTEGER PRIMARY KEY,
  merchant_id  INTEGER NOT NULL REFERENCES merchants(merchant_id),
  period_month TEXT NOT NULL,
  total_cents  INTEGER NOT NULL CHECK (total_cents >= 0),
  status       TEXT NOT NULL CHECK (status IN ('draft', 'issued', 'settled'))
);

-- 唯附寫月結帳單稽核軌跡（不存收件人 PII，防止與個資遺忘權衝突）
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
  created_at    TEXT NOT NULL
);

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

-- 受控去識別化分析檢視表（不含 shipment_recipient_pii 與原始託運報文）
CREATE VIEW v_shipment_analytics AS
SELECT
  s.shipment_id,
  s.merchant_id,
  s.warehouse_id,
  w.region,
  s.status,
  s.fee_cents,
  s.created_at
FROM shipments s
JOIN warehouses w ON w.warehouse_id = s.warehouse_id;

-- 生效中商家 API 金鑰基礎檢視表（尚未檢查動態 expires_at，先切掉已撤銷金鑰與停權商家）
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
CREATE INDEX idx_dispatch_queued ON dispatch_tasks(priority DESC, created_at ASC) WHERE status = 'queued';
CREATE INDEX idx_api_keys_prefix ON merchant_api_keys(key_prefix) WHERE revoked_at IS NULL;
CREATE INDEX idx_billing_audit_stmt ON billing_audit_logs(statement_id, created_at DESC);
