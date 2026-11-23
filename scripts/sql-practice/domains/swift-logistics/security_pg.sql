-- 領域丙（swift-logistics）：PostgreSQL 18 正式環境角色、最小權限、多租戶 RLS 與唯附寫稽核參考腳本
-- 用途：對應 SEC02 / SEC03 / SEC06 / C08 / C12 的真實伺服器端資料庫安全邊界

REVOKE CREATE ON SCHEMA public FROM PUBLIC;

CREATE ROLE logistics_migrator    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE logistics_app         NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE ROLE logistics_bi_readonly NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE ROLE logistics_audit_ro    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;

ALTER ROLE logistics_app         SET statement_timeout = '3s';
ALTER ROLE logistics_app         SET lock_timeout      = '1s';
ALTER ROLE logistics_bi_readonly SET statement_timeout = '30s';

GRANT USAGE ON SCHEMA public TO logistics_app, logistics_bi_readonly, logistics_audit_ro;

GRANT SELECT, INSERT, UPDATE, DELETE ON
  warehouses, merchants, merchant_users, merchant_api_keys, drivers,
  roles, permissions, role_permissions,
  shipments, shipment_packages, shipment_payloads, shipment_recipient_pii,
  shipment_events, driver_shifts, dispatch_tasks, billing_statements
TO logistics_app;

-- 帳單稽核軌跡嚴格唯附寫（搭配獨立備份憑證與雲端物件不可變保留鎖）
REVOKE UPDATE, DELETE, TRUNCATE ON billing_audit_logs FROM logistics_app;
GRANT SELECT, INSERT ON billing_audit_logs TO logistics_app;
GRANT SELECT ON billing_audit_logs TO logistics_audit_ro;

-- BI 角色嚴格隔離收件人個資表與 API 金鑰雜湊表，僅可讀去識別化檢視表
REVOKE ALL ON shipment_recipient_pii, merchant_api_keys, merchant_users, shipment_payloads
FROM logistics_bi_readonly;
GRANT SELECT ON v_shipment_analytics, warehouses, billing_statements
TO logistics_bi_readonly;

ALTER DEFAULT PRIVILEGES FOR ROLE logistics_migrator IN SCHEMA public
  REVOKE ALL ON TABLES FROM PUBLIC;

-- 多租戶列級安全（RLS）：shipments、shipment_packages、shipment_recipient_pii 與 billing_statements
-- 連線池環境中每次請求於交易內執行 SET LOCAL app.current_merchant_id = '<verified_id>';
ALTER TABLE shipments ENABLE ROW LEVEL SECURITY;
ALTER TABLE shipments FORCE ROW LEVEL SECURITY;

CREATE POLICY p_shipments_merchant_isolation ON shipments
  FOR ALL TO logistics_app
  USING (merchant_id = NULLIF(current_setting('app.current_merchant_id', true), '')::integer)
  WITH CHECK (merchant_id = NULLIF(current_setting('app.current_merchant_id', true), '')::integer);

-- 子表透過冗餘 merchant_id + idx_packages_merchant_shipment 直接過濾，免去 RLS 內相關子查詢掃表
ALTER TABLE shipment_packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE shipment_packages FORCE ROW LEVEL SECURITY;

CREATE POLICY p_packages_merchant_isolation ON shipment_packages
  FOR ALL TO logistics_app
  USING (merchant_id = NULLIF(current_setting('app.current_merchant_id', true), '')::integer)
  WITH CHECK (merchant_id = NULLIF(current_setting('app.current_merchant_id', true), '')::integer);

ALTER TABLE billing_statements ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_statements FORCE ROW LEVEL SECURITY;

CREATE POLICY p_billing_merchant_isolation ON billing_statements
  FOR SELECT TO logistics_app
  USING (merchant_id = NULLIF(current_setting('app.current_merchant_id', true), '')::integer);
