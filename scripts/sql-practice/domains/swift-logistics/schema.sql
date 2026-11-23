-- 領域丙（swift-logistics）：捷配物流 B2B 倉儲與配送調度平台
-- 引擎基準：SQLite 3.43+（相容 PostgreSQL 18 結構語意）

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
  account_key TEXT NOT NULL,
  tier        TEXT -- 允許 NULL 代表未分級新商家
);

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
  weight_grams INTEGER NOT NULL CHECK (weight_grams > 0),
  fragile      INTEGER NOT NULL DEFAULT 0 CHECK (fragile IN (0, 1))
);

CREATE TABLE shipment_payloads (
  shipment_id      INTEGER PRIMARY KEY REFERENCES shipments(shipment_id),
  raw_waybill_json TEXT NOT NULL -- 原始電子託運單大型報文（熱冷拆表對象）
);

CREATE TABLE shipment_events (
  event_id    INTEGER PRIMARY KEY,
  shipment_id INTEGER REFERENCES shipments(shipment_id), -- 刻意允許 NULL 模擬掃碼槍孤兒事件
  event_type  TEXT NOT NULL CHECK (event_type IN ('picked', 'hub_in', 'out_for_delivery', 'signed', 'exception')),
  recorded_at TEXT -- 刻意允許 NULL 模擬離線同步時間缺漏，觸發跨引擎 NULL 排序反例
);

CREATE TABLE driver_shifts (
  shift_id   INTEGER PRIMARY KEY,
  driver_id  INTEGER NOT NULL,
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

-- 基準索引（包含複合索引前導欄與部分索引示範）
CREATE INDEX idx_shipments_wh_status_created ON shipments(warehouse_id, status, created_at DESC, shipment_id ASC);
CREATE INDEX idx_events_shipment_recorded ON shipment_events(shipment_id, recorded_at DESC);
CREATE INDEX idx_dispatch_queued ON dispatch_tasks(priority DESC, created_at ASC) WHERE status = 'queued';
