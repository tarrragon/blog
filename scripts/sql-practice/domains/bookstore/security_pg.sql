-- 領域甲（bookstore）：PostgreSQL 18 正式環境角色、最小權限、PII 隔離與 RLS 參考腳本
-- 用途：補足 SQLite 嵌入式引擎無法演示的資料庫層身分、GRANT、逾時護欄與列級安全政策
-- 對照教材：1.21〈資安、權限與合規決定的資料表設計〉

-- 1. 收緊 public schema 預設權限，防止一般登入角色任意建表
-- （PG 15+ 新建資料庫預設已撤銷 PUBLIC 的 CREATE，自舊版升級或還原 dump 仍須顯式撤銷）
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

-- 2. 依職責切分群組角色（NOLOGIN）與實際連線帳號（LOGIN）
-- 所有非遷移／非備份角色一律維持 NOBYPASSRLS（預設即為 NOBYPASSRLS，顯式寫出屬防禦性宣告）
CREATE ROLE bookstore_migrator    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE bookstore_app         NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE ROLE bookstore_bi_readonly NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE ROLE bookstore_audit_ro    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;

-- 實際連線帳號（LOGIN）：密碼或憑證於部署環境注入，此處省略 PASSWORD 子句
CREATE ROLE bookstore_migrator_login LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE IN ROLE bookstore_migrator;
CREATE ROLE bookstore_app_login      LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS IN ROLE bookstore_app;
CREATE ROLE bookstore_bi_login       LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS IN ROLE bookstore_bi_readonly;
CREATE ROLE bookstore_audit_login    LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS IN ROLE bookstore_audit_ro;

-- 備份專用唯讀帳號：因表啟用 FORCE ROW LEVEL SECURITY，預設 pg_dump（SET row_security = off）
-- 對 NOBYPASSRLS 角色（含表擁有者）會直接報錯中止，須以專用 BYPASSRLS 唯讀帳號執行備份
CREATE ROLE bookstore_backup_ro      LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE BYPASSRLS;

-- 3. 依可登入角色（LOGIN）設定 SQL 層 DoS 執行逾時與交易閒置護欄
-- 注意（PG 18〈ALTER ROLE〉）：ALTER ROLE ... SET 僅於 LOGIN 角色建立新連線當下套用，
-- 設在 NOLOGIN 群組角色上不會被成員繼承，也不影響連線池既有長連線；
-- 當 statement_timeout != 0 時須維持 lock_timeout < statement_timeout；
-- PgBouncer transaction 池單次放寬逾時須改用交易內 SET LOCAL statement_timeout。
-- （以下秒數皆為示範值，正式環境須依服務 P99 延遲與報表長尾耗時量測決定）
ALTER ROLE bookstore_app_login SET statement_timeout                   = '3s';
ALTER ROLE bookstore_app_login SET lock_timeout                        = '1s';
ALTER ROLE bookstore_app_login SET idle_in_transaction_session_timeout = '10s';
ALTER ROLE bookstore_bi_login  SET statement_timeout                   = '30s';
ALTER ROLE bookstore_bi_login  SET lock_timeout                        = '2s';

-- 遷移角色常維持 statement_timeout = 0 搭配短 lock_timeout，避免 DDL 等鎖阻塞線上流量
ALTER ROLE bookstore_migrator_login SET statement_timeout = '0';
ALTER ROLE bookstore_migrator_login SET lock_timeout      = '2s';

-- 4. 最小權限授權：應用角色僅操作業務表，對稽核表唯附寫（無 UPDATE / DELETE / TRUNCATE）
GRANT USAGE ON SCHEMA public TO bookstore_app, bookstore_bi_readonly, bookstore_audit_ro, bookstore_backup_ro;

GRANT SELECT, INSERT, UPDATE, DELETE ON
  customers, customer_pii, categories, books, book_details,
  orders, order_items, reviews, coupons, order_coupons,
  daily_sales_snapshots, export_jobs, store_shifts, book_view_events,
  staff_accounts, roles, permissions, role_permissions, staff_roles
TO bookstore_app;

-- 若使用 SERIAL / BIGSERIAL 主鍵，應用角色亦須對應序列的 USAGE, SELECT（或一律採 GENERATED AS IDENTITY）
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bookstore_app;

-- 唯附寫稽核表：應用層只能 INSERT 與 SELECT，即使主機失守也無法竄改或滅證
REVOKE UPDATE, DELETE, TRUNCATE ON order_audit_logs FROM bookstore_app;
GRANT SELECT, INSERT ON order_audit_logs TO bookstore_app;
GRANT SELECT ON order_audit_logs TO bookstore_audit_ro;

-- 備份帳號僅授唯讀查詢（不含寫入與 DDL）
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bookstore_backup_ro;

-- 5. BI 分析角色僅能讀受控去識別化檢視表，禁止接觸 customers 原表與 customer_pii
-- 凡含 WHERE 列過濾條件的受控檢視表須加上 security_barrier = true，防止非 LEAKPROOF 條件下推側錄
REVOKE ALL ON customers, customer_pii, staff_accounts FROM bookstore_bi_readonly;
ALTER VIEW v_customer_analytics SET (security_barrier = true);
ALTER VIEW v_active_staff       SET (security_barrier = true);
GRANT SELECT ON v_customer_analytics, books, categories, orders, order_items, daily_sales_snapshots
TO bookstore_bi_readonly;

-- 6. 新建物件預設權限防漏
-- PG 18 對新建 TABLES 預設僅授與建立者（PUBLIC 原即無權限）；對 FUNCTIONS 預設開放 PUBLIC EXECUTE，應先撤銷。
-- 後續遷移新增業務表可採：(a) 於版本化遷移檔顯式宣告最小 GRANT＋CI 檢查，或
-- (b) 將業務表移至獨立 business schema，先 GRANT USAGE ON SCHEMA 再對 migrator 設定
--     ALTER DEFAULT PRIVILEGES FOR ROLE bookstore_migrator_login IN SCHEMA business
--     GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES / GRANT USAGE, SELECT ON SEQUENCES TO bookstore_app
--     （注意 FOR ROLE 僅認建表當下的執行角色，不從 NOLOGIN 群組繼承）。
ALTER DEFAULT PRIVILEGES FOR ROLE bookstore_migrator_login IN SCHEMA public
  REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

-- 7. 列級安全（RLS）示範：門市查詢 export_jobs 時強制依門市上下文隔離
-- 連線池環境（如 PgBouncer transaction 模式）須於明確 BEGIN ... COMMIT 內執行：
--   SET LOCAL app.current_store_code = '<verified_store_code>';
-- 若資料模型將 scope_store_code IS NULL 定義為「尚未指派門市（無權限）」，
-- 不可於 USING / WITH CHECK 以 IS NULL 放行，須改用顯式布林欄位區分全域角色。
ALTER TABLE export_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE export_jobs FORCE ROW LEVEL SECURITY;

CREATE POLICY p_export_jobs_store_scope ON export_jobs
  FOR ALL TO bookstore_app
  USING (
    scope_store_code IS NULL
    OR scope_store_code = NULLIF(current_setting('app.current_store_code', true), '')
  )
  WITH CHECK (
    scope_store_code IS NULL
    OR scope_store_code = NULLIF(current_setting('app.current_store_code', true), '')
  );
