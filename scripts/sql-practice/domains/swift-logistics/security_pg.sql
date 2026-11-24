-- 領域丙（swift-logistics）：PostgreSQL 18 正式環境角色、最小權限、多租戶 RLS 與唯附寫稽核參考腳本
-- 用途：對應 SEC02 / SEC03 / SEC06 / C08 / C12 的真實伺服器端資料庫安全邊界
-- 對照教材：1.21〈資安、權限與合規決定的資料表設計〉

-- 1. 收緊 public schema 預設權限（PG 15+ 新建資料庫預設已撤銷，舊版升級或還原 dump 仍須顯式執行）
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

-- 2. 依職責切分群組角色（NOLOGIN）與實際連線帳號（LOGIN）
CREATE ROLE logistics_migrator    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE logistics_app         NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE ROLE logistics_bi_readonly NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE ROLE logistics_audit_ro    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;

CREATE ROLE logistics_migrator_login LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE IN ROLE logistics_migrator;
CREATE ROLE logistics_app_login      LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS IN ROLE logistics_app;
CREATE ROLE logistics_bi_login       LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS IN ROLE logistics_bi_readonly;
CREATE ROLE logistics_audit_login    LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS IN ROLE logistics_audit_ro;

-- 備份專用唯讀帳號：因表啟用 FORCE ROW LEVEL SECURITY，預設 pg_dump（SET row_security = off）
-- 對 NOBYPASSRLS 角色（含表擁有者）會直接報錯中止，須以專用 BYPASSRLS 唯讀帳號執行備份
CREATE ROLE logistics_backup_ro      LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE BYPASSRLS;

-- 3. 依可登入角色（LOGIN）設定 SQL 層 DoS 執行逾時與交易閒置護欄
-- ALTER ROLE ... SET 僅於 LOGIN 角色建立新連線當下套用（NOLOGIN 群組不繼承、不影響既有池連線）
-- （以下秒數皆為示範值，正式環境須依服務 P99 延遲與報表長尾耗時量測決定）
ALTER ROLE logistics_app_login      SET statement_timeout                   = '3s';
ALTER ROLE logistics_app_login      SET lock_timeout                        = '1s';
ALTER ROLE logistics_app_login      SET idle_in_transaction_session_timeout = '10s';
ALTER ROLE logistics_bi_login       SET statement_timeout                   = '30s';
ALTER ROLE logistics_bi_login       SET lock_timeout                        = '2s';
ALTER ROLE logistics_migrator_login SET statement_timeout                   = '0';
ALTER ROLE logistics_migrator_login SET lock_timeout                        = '2s';

-- 4. 最小權限授權
GRANT USAGE ON SCHEMA public TO logistics_app, logistics_bi_readonly, logistics_audit_ro, logistics_backup_ro;

GRANT SELECT, INSERT, UPDATE, DELETE ON
  warehouses, merchants, merchant_users, merchant_api_keys, drivers,
  roles, permissions, role_permissions,
  shipments, shipment_packages, shipment_payloads, shipment_recipient_pii,
  shipment_events, driver_shifts, dispatch_tasks, billing_statements
TO logistics_app;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO logistics_app;

-- 帳單稽核軌跡嚴格唯附寫（搭配獨立備份憑證與雲端物件不可變保留鎖）
REVOKE UPDATE, DELETE, TRUNCATE ON billing_audit_logs FROM logistics_app;
GRANT SELECT, INSERT ON billing_audit_logs TO logistics_app;
GRANT SELECT ON billing_audit_logs TO logistics_audit_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO logistics_backup_ro;

-- 5. BI 角色嚴格隔離收件人個資表與 API 金鑰雜湊表，僅可讀去識別化檢視表
-- 含列過濾條件的受控檢視表加上 security_barrier = true，防止外層非 LEAKPROOF 條件下推側錄
REVOKE ALL ON shipment_recipient_pii, merchant_api_keys, merchant_users, shipment_payloads
FROM logistics_bi_readonly;
ALTER VIEW v_shipment_analytics       SET (security_barrier = true);
ALTER VIEW v_active_merchant_api_keys SET (security_barrier = true);
GRANT SELECT ON v_shipment_analytics, warehouses, billing_statements
TO logistics_bi_readonly;

-- 6. 新建物件預設權限（PG 18 TABLES 預設已對 PUBLIC 零權限；撤銷 FUNCTIONS 預設對 PUBLIC 開放的 EXECUTE）
ALTER DEFAULT PRIVILEGES FOR ROLE logistics_migrator_login IN SCHEMA public
  REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

-- 7. 多租戶列級安全（RLS）：shipments、shipment_packages、shipment_recipient_pii 與 billing_statements
-- 連線池環境中每次請求須於明確交易（BEGIN ... COMMIT）內執行 SET LOCAL app.current_merchant_id = '<verified_id>';
-- 注意：認證前依 key_hash 反查租戶所用的 merchant_api_keys 不直接套用依賴 app.current_merchant_id 的
-- FORCE RLS，避免尚未取得租戶編號前陷入認證死鎖（須由限定認證查詢函式或獨立政策處理）。
ALTER TABLE shipments ENABLE ROW LEVEL SECURITY;
ALTER TABLE shipments FORCE ROW LEVEL SECURITY;

CREATE POLICY p_shipments_merchant_isolation ON shipments
  FOR ALL TO logistics_app
  USING (merchant_id = NULLIF(current_setting('app.current_merchant_id', true), '')::integer)
  WITH CHECK (merchant_id = NULLIF(current_setting('app.current_merchant_id', true), '')::integer);

-- 子表透過冗餘 merchant_id + idx_packages_merchant_shipment 直接過濾，免去 RLS 內相關子查詢掃表
-- （PostgreSQL 正式環境另須對父表 shipments 宣告 UNIQUE (merchant_id, shipment_id) 並將子表
--  merchant_id 設為 NOT NULL 後建複合外鍵，避開預設 MATCH SIMPLE 在 NULL 時略過外鍵檢查）
ALTER TABLE shipment_packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE shipment_packages FORCE ROW LEVEL SECURITY;

CREATE POLICY p_packages_merchant_isolation ON shipment_packages
  FOR ALL TO logistics_app
  USING (merchant_id = NULLIF(current_setting('app.current_merchant_id', true), '')::integer)
  WITH CHECK (merchant_id = NULLIF(current_setting('app.current_merchant_id', true), '')::integer);

ALTER TABLE shipment_recipient_pii ENABLE ROW LEVEL SECURITY;
ALTER TABLE shipment_recipient_pii FORCE ROW LEVEL SECURITY;

CREATE POLICY p_recipient_pii_merchant_isolation ON shipment_recipient_pii
  FOR ALL TO logistics_app
  USING (merchant_id = NULLIF(current_setting('app.current_merchant_id', true), '')::integer)
  WITH CHECK (merchant_id = NULLIF(current_setting('app.current_merchant_id', true), '')::integer);

ALTER TABLE billing_statements ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_statements FORCE ROW LEVEL SECURITY;

CREATE POLICY p_billing_merchant_isolation ON billing_statements
  FOR ALL TO logistics_app
  USING (merchant_id = NULLIF(current_setting('app.current_merchant_id', true), '')::integer)
  WITH CHECK (merchant_id = NULLIF(current_setting('app.current_merchant_id', true), '')::integer);
