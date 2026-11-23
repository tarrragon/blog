-- 領域甲（bookstore）：PostgreSQL 18 正式環境角色、最小權限、PII 隔離與 RLS 參考腳本
-- 用途：補足 SQLite 嵌入式引擎無法演示的資料庫層身分、GRANT、逾時護欄與列級安全政策

-- 1. 收緊 public schema 預設權限，防止一般登入角色任意建表
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

-- 2. 依職責切分角色（所有非遷移角色一律不具 SUPERUSER / BYPASSRLS）
CREATE ROLE bookstore_migrator    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE bookstore_app         NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE ROLE bookstore_bi_readonly NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE ROLE bookstore_audit_ro    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;

-- 3. 依角色設定 SQL 層 DoS 執行逾時護欄
ALTER ROLE bookstore_app         SET statement_timeout = '3s';
ALTER ROLE bookstore_app         SET lock_timeout      = '1s';
ALTER ROLE bookstore_bi_readonly SET statement_timeout = '30s';

-- 4. 最小權限授權：應用角色僅操作業務表，對稽核表唯附寫（無 UPDATE / DELETE）
GRANT USAGE ON SCHEMA public TO bookstore_app, bookstore_bi_readonly, bookstore_audit_ro;

GRANT SELECT, INSERT, UPDATE, DELETE ON
  customers, customer_pii, categories, books, book_details,
  orders, order_items, reviews, coupons, order_coupons,
  daily_sales_snapshots, export_jobs, store_shifts, book_view_events,
  staff_accounts, roles, permissions, role_permissions, staff_roles
TO bookstore_app;

-- 唯附寫稽核表：應用層只能 INSERT 與 SELECT，即使主機失守也無法竄改或滅證
REVOKE UPDATE, DELETE, TRUNCATE ON order_audit_logs FROM bookstore_app;
GRANT SELECT, INSERT ON order_audit_logs TO bookstore_app;
GRANT SELECT ON order_audit_logs TO bookstore_audit_ro;

-- 5. BI 分析角色僅能讀受控去識別化檢視表，禁止接觸 customers 原表與 customer_pii
REVOKE ALL ON customers, customer_pii, staff_accounts FROM bookstore_bi_readonly;
GRANT SELECT ON v_customer_analytics, books, categories, orders, order_items, daily_sales_snapshots
TO bookstore_bi_readonly;

-- 6. 預設權限防漏：未來 migrator 新建表自動依規則套用，不需人工追補
ALTER DEFAULT PRIVILEGES FOR ROLE bookstore_migrator IN SCHEMA public
  REVOKE ALL ON TABLES FROM PUBLIC;

-- 7. 列級安全（RLS）示範：門市管理員查詢 export_jobs 時強制依門市或顧客上下文隔離
ALTER TABLE export_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE export_jobs FORCE ROW LEVEL SECURITY;

CREATE POLICY p_export_jobs_store_scope ON export_jobs
  FOR SELECT TO bookstore_app
  USING (
    scope_store_code IS NULL
    OR scope_store_code = current_setting('app.current_store_code', true)
  );
